"""Offset-insensitive force diagnostics on the opened D development bundle.

The analysis compares two lattice estimators (T-window slopes and Creutz
ratios) with shared configuration-block resampling across kernels. It is an
exploratory analysis of IDs 0--99 only; it does not select an estimand, gate,
reference, or physical score.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import platform
from pathlib import Path

import numpy as np

from core.io import digest
from core.stats import blocks, bootstrap_indices

from .reference_gate_runner import DEFAULT_PROTOCOL, _load_complete_development
from .statistics import potential


def _window_slope_force(loop_means, protocol):
    """Return F(R+1/2)=V(R+1)-V(R), shaped (kernel, window, R-1)."""
    potentials = np.stack([
        potential(loop_means, window, protocol['t_values'])
        for window in protocol['reference_windows']
    ], axis=-1)
    forces = np.diff(potentials, axis=-2)
    return np.moveaxis(forces, -1, -2)


def _creutz_force(loop_means):
    """Return adjacent-R, adjacent-T Creutz ratios, shaped (kernel,T-1,R-1)."""
    if np.any(loop_means <= 0) or not np.isfinite(loop_means).all():
        raise ValueError('Creutz estimator requires finite positive loop means')
    logw = np.log(loop_means)
    values = -(
        logw[..., 1:, 1:] + logw[..., :-1, :-1]
        - logw[..., 1:, :-1] - logw[..., :-1, 1:]
    )
    return np.moveaxis(values, -1, -2)


def _rows(estimator, labels, r_midpoints, point, draws, valid_draws, kernel_names):
    rows = []
    selected = draws[valid_draws]
    n_valid = int(valid_draws.sum())
    n_invalid = int(len(valid_draws) - n_valid)
    for label_index, label in enumerate(labels):
        for r_index, r_midpoint in enumerate(r_midpoints):
            reference_draw = selected[:, 0, label_index, r_index]
            for kernel_index, kernel_name in enumerate(kernel_names):
                sample = selected[:, kernel_index, label_index, r_index]
                paired_delta = sample - reference_draw
                value = float(point[kernel_index, label_index, r_index])
                delta = float(value - point[0, label_index, r_index])
                low, high = np.quantile(sample, [0.025, 0.975])
                delta_low, delta_high = np.quantile(paired_delta, [0.025, 0.975])
                rows.append({
                    'estimator': estimator,
                    'label': label,
                    'kernel': kernel_name,
                    'R_midpoint': float(r_midpoint),
                    'force_point': value,
                    'force_bootstrap_sd': float(sample.std(ddof=1)),
                    'force_ci95_low_pointwise': float(low),
                    'force_ci95_high_pointwise': float(high),
                    'candidate_minus_identity_point': delta,
                    'paired_delta_bootstrap_sd': float(paired_delta.std(ddof=1)),
                    'paired_delta_ci95_low_pointwise': float(delta_low),
                    'paired_delta_ci95_high_pointwise': float(delta_high),
                    'valid_draws': n_valid,
                    'invalid_draws': n_invalid,
                })
    return rows


def force_diagnostic(loops, protocol, *, bootstrap_samples=5000, seed=2026112121):
    """Compute paired force curves and finite-T sensitivity from block draws."""
    if (isinstance(bootstrap_samples, bool) or not isinstance(bootstrap_samples, int)
            or bootstrap_samples < 2):
        raise ValueError('bootstrap_samples must be an integer >= 2')
    raw = np.asarray(loops, dtype=float)
    r_values = protocol['r_values']
    t_values = protocol['t_values']
    expected = (len(protocol['kernels']), len(r_values), len(t_values))
    if raw.ndim != 4 or raw.shape[1:] != expected or not np.isfinite(raw).all():
        raise ValueError(f'expected finite loops with trailing shape {expected}, got {raw.shape}')
    if any(b - a != 1 for a, b in zip(r_values, r_values[1:])):
        raise ValueError('discrete force requires consecutive unit-spaced R values')
    if any(b - a != 1 for a, b in zip(t_values, t_values[1:])):
        raise ValueError('Creutz ratios require consecutive unit-spaced T values')

    block_length = int(protocol['block_length'])
    blocked = blocks(raw, block_length)
    if len(blocked) < 2:
        raise ValueError('at least two configuration blocks are required')
    index = bootstrap_indices(len(blocked), bootstrap_samples, seed)
    point_mean = blocked.mean(axis=0)
    bootstrap_means = blocked[index].mean(axis=1)
    point_valid = bool(np.isfinite(point_mean).all() and np.all(point_mean > 0))
    if not point_valid:
        raise ValueError('one or more point loop means are nonpositive or nonfinite')

    # A single complete-draw mask is shared across every kernel, R, T and
    # estimator. Invalid draws remain counted in the report; no arm-specific
    # resampling or silent per-observable deletion occurs.
    valid_draws = (np.isfinite(bootstrap_means).all(axis=(1, 2, 3))
                   & np.all(bootstrap_means > 0, axis=(1, 2, 3)))
    if int(valid_draws.sum()) < 2:
        raise ValueError('fewer than two complete positive block-bootstrap draws')

    window_point = _window_slope_force(point_mean, protocol)
    window_draws = np.stack([
        _window_slope_force(bootstrap_means[draw], protocol)
        for draw in range(bootstrap_samples)
    ])
    creutz_point = _creutz_force(point_mean)
    creutz_draws = np.stack([
        _creutz_force(bootstrap_means[draw])
        for draw in range(bootstrap_samples)
    ])

    kernel_names = [row['name'] for row in protocol['kernels']]
    if not kernel_names or kernel_names[0] != 'identity':
        raise ValueError('the first kernel must be the frozen identity comparator')
    r_midpoints = [(left + right) / 2 for left, right in zip(r_values, r_values[1:])]
    window_labels = ['-'.join(str(value) for value in window)
                     for window in protocol['reference_windows']]
    creutz_labels = [str(value) for value in t_values[:-1]]
    window_rows = _rows('T_window_slope', window_labels, r_midpoints,
                        window_point, window_draws, valid_draws, kernel_names)
    creutz_rows = _rows('Creutz_ratio', creutz_labels, r_midpoints,
                        creutz_point, creutz_draws, valid_draws, kernel_names)
    return {
        'block_count': int(len(blocked)),
        'block_length': block_length,
        'bootstrap_samples': int(bootstrap_samples),
        'seed': int(seed),
        'bootstrap_index': index,
        'valid_draws': int(valid_draws.sum()),
        'invalid_draws': int(len(valid_draws) - valid_draws.sum()),
        'invalid_draw_indices': np.flatnonzero(~valid_draws).tolist(),
        'window_rows': window_rows,
        'creutz_rows': creutz_rows,
        'window_point': window_point,
        'window_draws': window_draws,
        'creutz_point': creutz_point,
        'creutz_draws': creutz_draws,
        'window_labels': window_labels,
        'creutz_labels': creutz_labels,
        'r_midpoints': r_midpoints,
        'kernel_names': kernel_names,
    }


def _write_csv(path, rows):
    if not rows:
        path.write_text('', encoding='utf-8')
        return
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _plot_force_sensitivity(path, result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    rows = result['window_rows']
    labels = result['window_labels']
    r_values = result['r_midpoints']
    candidates = result['kernel_names'][1:]
    colors = plt.get_cmap('tab10').colors
    fig, axes = plt.subplots(1, len(labels), figsize=(15, 5), sharey=True)
    for label_index, (ax, label) in enumerate(zip(axes, labels)):
        for candidate_index, candidate in enumerate(candidates):
            selected = [row for row in rows
                        if row['label'] == label and row['kernel'] == candidate]
            selected.sort(key=lambda row: row['R_midpoint'])
            x = [row['R_midpoint'] for row in selected]
            y = [row['candidate_minus_identity_point'] for row in selected]
            low = [row['paired_delta_ci95_low_pointwise'] for row in selected]
            high = [row['paired_delta_ci95_high_pointwise'] for row in selected]
            color = colors[candidate_index % len(colors)]
            ax.plot(x, y, marker='o', color=color, label=candidate)
            ax.vlines(x, low, high, color=color, linewidth=1.2)
        ax.axhline(0, color='black', linewidth=.8)
        ax.set_title(f'T window {label}')
        ax.set_xlabel(r'$R+1/2$')
        ax.grid(alpha=.25)
    axes[0].set_ylabel(r'paired $F_{candidate}-F_{identity}$ (lattice units)')
    axes[-1].legend(fontsize=7, loc='best')
    fig.suptitle('D development IDs 0–99; pointwise paired block-bootstrap intervals; diagnostic only')
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _plot_identity_window_sensitivity(path, result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5))
    markers = ['o', 's', '^']
    colors = plt.get_cmap('tab10').colors
    for index, label in enumerate(result['window_labels']):
        selected = [row for row in result['window_rows']
                    if row['kernel'] == 'identity' and row['label'] == label]
        selected.sort(key=lambda row: row['R_midpoint'])
        x = [row['R_midpoint'] for row in selected]
        y = [row['force_point'] for row in selected]
        low = [row['force_ci95_low_pointwise'] for row in selected]
        high = [row['force_ci95_high_pointwise'] for row in selected]
        color = colors[index % len(colors)]
        ax.plot(x, y, marker=markers[index % len(markers)], color=color,
                label=f'T window {label}')
        ax.vlines(x, low, high, color=color, linewidth=1.2)
    ax.set_xlabel(r'$R+1/2$')
    ax.set_ylabel(r'$F(R+1/2)$ (lattice units)')
    ax.set_title('Identity-kernel force by T window; pointwise 95% block-bootstrap intervals')
    ax.grid(alpha=.25)
    ax.legend(fontsize=8)
    fig.suptitle('D development only; 20 blocks; no external force reference')
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _plot_creutz_sensitivity(path, result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    labels = result['creutz_labels']
    rows = result['creutz_rows']
    candidates = result['kernel_names'][1:]
    colors = plt.get_cmap('tab10').colors
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharey=True)
    for label_index, (ax, label) in enumerate(zip(axes.flat, labels)):
        for candidate_index, candidate in enumerate(candidates):
            selected = [row for row in rows
                        if row['label'] == label and row['kernel'] == candidate]
            selected.sort(key=lambda row: row['R_midpoint'])
            x = [row['R_midpoint'] for row in selected]
            y = [row['candidate_minus_identity_point'] for row in selected]
            low = [row['paired_delta_ci95_low_pointwise'] for row in selected]
            high = [row['paired_delta_ci95_high_pointwise'] for row in selected]
            color = colors[candidate_index % len(colors)]
            ax.plot(x, y, marker='o', color=color, label=candidate)
            ax.vlines(x, low, high, color=color, linewidth=1.2)
        ax.axhline(0, color='black', linewidth=.8)
        ax.set_title(f'Creutz T={label}→{int(label) + 1}')
        ax.set_xlabel(r'$R+1/2$')
        ax.grid(alpha=.25)
    axes[0, 0].set_ylabel(r'paired $\chi_{candidate}-\chi_{identity}$')
    axes[1, 0].set_ylabel(r'paired $\chi_{candidate}-\chi_{identity}$')
    axes[0, 1].legend(fontsize=7, loc='best')
    fig.suptitle('D development IDs 0–99; paired intervals; finite-T exploratory diagnostic')
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _render_report(output, result, sample, protocol_hash, analysis_hash):
    identity_rows = [row for row in result['window_rows'] if row['kernel'] == 'identity']
    lines = [
        '# Wilson D development: offset-insensitive force diagnostics',
        '',
        '**Status:** `development_diagnostic_only`; `physical_score=null`; no production gate or estimand was changed.',
        '',
        '## Data and frozen identity',
        '',
        '- Complete frozen D development transaction only: IDs 0–99; validation, gap, and shared holdout were not read.',
        f"- Generation: `{sample['generation']}`; measurement protocol SHA-256: `{sample['protocol_hash']}`.",
        f'- Protocol file SHA-256: `{protocol_hash}`; analysis source SHA-256: `{analysis_hash}`.',
        f"- Block design: {result['block_count']} contiguous blocks of {result['block_length']} configurations; {result['bootstrap_samples']} shared block-bootstrap draws; seed {result['seed']}.",
        f"- Complete positive draws: {result['valid_draws']}/{result['bootstrap_samples']}; invalid: {result['invalid_draws']} (indices `{result['invalid_draw_indices']}`).",
        '- The same resampling rows are used for every kernel, R, T window, and both estimators. Invalid draws are retained in the denominator and are not silently replaced.',
        '',
        '## Estimators',
        '',
        r'- T-window slope: $V_w(R)=-\mathrm{slope}_w[\log\langle W(R,T)\rangle]$, then $F(R+1/2)=V_w(R+1)-V_w(R)$ using the same window and draw.',
        r'- Creutz ratio: $\chi(R,T)=-\log\{W(R+1,T+1)W(R,T)/[W(R+1,T)W(R,T+1)]\}$, which approaches the same discrete force in the single-exponential limit.',
        '- Intervals are pointwise percentile intervals over 20 configuration blocks. The 5,000 draws reduce Monte Carlo noise in the bootstrap calculation; they do not create 5,000 independent gauge samples or provide family-wise coverage.',
        '',
        '## Identity-kernel T-window sensitivity',
        '',
        '| T window | R midpoint | F point | pointwise 95% interval |',
        '|---|---:|---:|---:|',
    ]
    for row in identity_rows:
        lines.append(
            f"| {row['label']} | {row['R_midpoint']:.1f} | {row['force_point']:.6f} | "
            f"[{row['force_ci95_low_pointwise']:.6f}, {row['force_ci95_high_pointwise']:.6f}] |"
        )
    lines.extend([
        '',
        '![Identity force and T-window sensitivity](identity_force_by_window.png)',
        '',
        '## Paired kernel differences',
        '',
        'The paired candidate-minus-identity curves and intervals are in `window_force_paired.csv` and `creutz_force_paired.csv`; figures show them by T window and Creutz time. These differences describe the opened development sample only. A shift in measured force does not identify which kernel is closer to the continuum or ground-state value.',
        '',
        '![Window-slope force shifts](window_force_paired_deltas.png)',
        '',
        '![Creutz force shifts by T](creutz_force_paired_deltas.png)',
        '',
        '## Interpretation and limits',
        '',
        'This diagnostic supplies actual-data evidence for reviewing the static-force branch. It demonstrates how much the candidate force estimates and the identity force depend on the selected T window / Creutz time on this D development sample. It does not establish a plateau, control finite-T excited states, remove R-dependent common bias, calibrate the many (kernel, R, T) comparisons, or provide an external force anchor. The current reference proposal remains unfrozen and D0–99 has already been used for development; therefore this analysis cannot authorize D120–139, open IDs 140–199, claim APE/stout superiority, or assign a physical score.',
        '',
        'If the research target is accepted as an additive-constant-insensitive force, freeze the estimator, T window or Creutz rule, finite-T control, multiplicity family, and failure/abstention policy before any new validation. If the target remains absolute V(R), this diagnostic does not supply the missing independent zero-point anchor.',
        '',
        'All raw point estimates, paired intervals, draw counts, and resampling indices are preserved beside this report.',
        '',
    ])
    (output / 'README.md').write_text('\n'.join(lines), encoding='utf-8')


def run(input_dir, output_dir, protocol_path=DEFAULT_PROTOCOL, *,
        bootstrap_samples=5000, seed=2026112121):
    protocol_path = Path(protocol_path).resolve()
    protocol_bytes = protocol_path.read_bytes()
    protocol = json.loads(protocol_bytes)
    sample = _load_complete_development(input_dir, protocol)
    with np.load(io.BytesIO(sample['payloads']['development.npz']), allow_pickle=False) as saved:
        loops = saved['loops'].copy()
    result = force_diagnostic(loops, protocol, bootstrap_samples=bootstrap_samples, seed=seed)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    protocol_hash = hashlib.sha256(protocol_bytes).hexdigest()
    analysis_hash = digest(Path(__file__))
    _write_csv(output / 'window_force_paired.csv', result['window_rows'])
    _write_csv(output / 'creutz_force_paired.csv', result['creutz_rows'])
    np.savez_compressed(output / 'bootstrap_indices.npz', indices=result['bootstrap_index'])
    _plot_identity_window_sensitivity(output / 'identity_force_by_window.png', result)
    _plot_force_sensitivity(output / 'window_force_paired_deltas.png', result)
    _plot_creutz_sensitivity(output / 'creutz_force_paired_deltas.png', result)
    metadata = {
        'schema': 'latticearena-wilson-development-force-diagnostic-v1',
        'status': 'development_diagnostic_only',
        'physical_score': None,
        'validation_accessed': False,
        'gap_accessed': False,
        'shared_holdout_accessed': False,
        'input_ids': [int(value) for value in sample['ids']],
        'generation': sample['generation'],
        'measurement_protocol_fingerprint': sample['protocol_hash'],
        'transaction_sha256': {name: hashlib.sha256(payload).hexdigest()
                               for name, payload in sample['payloads'].items()},
        'analysis_protocol_sha256': protocol_hash,
        'analysis_source_sha256': analysis_hash,
        'bootstrap_index_sha256': hashlib.sha256(
            np.asarray(result['bootstrap_index'], dtype='<i8').tobytes(order='C')).hexdigest(),
        'numpy_version': np.__version__,
        'python_version': platform.python_version(),
        'block_count': result['block_count'],
        'block_length': result['block_length'],
        'bootstrap_samples': result['bootstrap_samples'],
        'seed': result['seed'],
        'valid_draws': result['valid_draws'],
        'invalid_draws': result['invalid_draws'],
        'invalid_draw_indices': result['invalid_draw_indices'],
        'estimators': ['T_window_slope', 'Creutz_ratio'],
        'window_rows': result['window_rows'],
        'creutz_rows': result['creutz_rows'],
    }
    (output / 'summary.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    _render_report(output, result, sample, protocol_hash, analysis_hash)
    return metadata


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', default='results/wilson_loop/s16t16d_development_20261120')
    parser.add_argument('--protocol', default=str(DEFAULT_PROTOCOL))
    parser.add_argument('--output-dir', default='results/wilson_loop/development_force_diagnostic_20261121_v1')
    parser.add_argument('--bootstrap-samples', type=int, default=5000)
    parser.add_argument('--seed', type=int, default=2026112121)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.input_dir, args.output_dir, args.protocol,
                         bootstrap_samples=args.bootstrap_samples, seed=args.seed), indent=2))


if __name__ == '__main__':
    main()
