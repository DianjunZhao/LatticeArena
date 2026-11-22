"""Synthetic-only negative controls for a proposed offset-free Wilson force.

This diagnostic does not read production measurements, select an estimand, or
connect to the production gate. It checks exact invariance to an R-independent
additive potential shift and response to a constructed R-dependent shift.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import platform

import numpy as np

from core.io import digest
from core.stats import blocks, bootstrap_indices

from .statistics import potential


SEED = 2026112121
N_CONFIG = 100
BLOCK_LENGTH = 5
N_BOOT = 5000
DELTA_COMMON = 0.03
DELTA_R = np.array([0.0, 0.02, 0.05, 0.10])


def synthetic_loops(seed=SEED, n_config=N_CONFIG, r_values=(1, 2, 3, 4),
                    t_values=(4, 5, 6, 7, 8)):
    """Create positive block-correlated single-exponential loops for controls."""
    rng = np.random.default_rng(seed)
    r = np.asarray(r_values, dtype=float)
    t = np.asarray(t_values, dtype=float)
    n_blocks = n_config // BLOCK_LENGTH
    if n_config % BLOCK_LENGTH or n_blocks < 3:
        raise ValueError('n_config must contain at least three complete blocks')

    # A smooth, nonconstant potential and a time-independent overlap.
    v_true = 0.34 + 0.19 * r + 0.012 * r**2
    amplitude = np.exp(-0.08 * r)
    block_common = np.repeat(rng.normal(0.0, 0.012, (n_blocks, 1, 1)),
                             BLOCK_LENGTH, axis=0)
    block_by_r = np.repeat(rng.normal(0.0, 0.006, (n_blocks, len(r), 1)),
                          BLOCK_LENGTH, axis=0)
    cfg_noise = rng.normal(0.0, 0.004, (n_config, len(r), len(t)))
    log_w = (np.log(amplitude)[None, :, None]
             - v_true[None, :, None] * t[None, None, :]
             + block_common + block_by_r + cfg_noise)
    return np.exp(log_w)


def apply_common_potential_shift(loops, t_values, delta):
    loops = np.asarray(loops, dtype=float)
    t = np.asarray(t_values, dtype=float)
    if loops.ndim != 3 or loops.shape[-1] != len(t):
        raise ValueError('loops must have shape (configuration,R,T)')
    if not np.isfinite(loops).all() or np.any(loops <= 0):
        raise ValueError('loops must be positive and finite')
    return loops * np.exp(-float(delta) * t)[None, None, :]


def apply_r_dependent_potential_shift(loops, t_values, delta_r):
    loops = np.asarray(loops, dtype=float)
    t = np.asarray(t_values, dtype=float)
    delta_r = np.asarray(delta_r, dtype=float)
    if loops.ndim != 3 or loops.shape[-1] != len(t):
        raise ValueError('loops must have shape (configuration,R,T)')
    if delta_r.shape != (loops.shape[1],):
        raise ValueError('delta_r must contain one offset per R')
    if not np.isfinite(loops).all() or np.any(loops <= 0):
        raise ValueError('loops must be positive and finite')
    return loops * np.exp(-delta_r[None, :, None] * t[None, None, :])


def potential_and_force(loops, window, t_values):
    """Return ensemble-mean V(R) and its adjacent-R difference."""
    mean_loops = np.asarray(loops, dtype=float).mean(axis=0)
    v = np.asarray(potential(mean_loops, window, t_values), dtype=float)
    if v.ndim != 1 or len(v) < 2 or not np.isfinite(v).all():
        raise ValueError('the selected window must yield finite potentials for >=2 R')
    return v, np.diff(v)


def _bootstrap_potentials(loops, window, t_values, indices):
    block_means = blocks(np.asarray(loops, dtype=float), BLOCK_LENGTH)
    boot_means = block_means[indices].mean(axis=1)
    values = np.asarray(potential(boot_means, window, t_values), dtype=float)
    if values.ndim != 2 or not np.isfinite(values).all():
        raise ValueError('bootstrap potentials must have shape (draw,R) and be finite')
    return values


def analyze(seed=SEED, n_boot=N_BOOT):
    protocol_path = Path(__file__).with_name('protocol_d_20261120.json')
    protocol = json.loads(protocol_path.read_text())
    r_values = protocol['r_values']
    t_values = protocol['t_values']
    window = protocol['fit_window']
    raw = synthetic_loops(seed=seed, r_values=r_values, t_values=t_values)
    common = apply_common_potential_shift(raw, t_values, DELTA_COMMON)
    r_dependent = apply_r_dependent_potential_shift(raw, t_values, DELTA_R)
    if n_boot < 2:
        raise ValueError('n_boot must be at least 2')
    indices = bootstrap_indices(N_CONFIG // BLOCK_LENGTH, n_boot, seed + 2)
    worlds = {'baseline': raw, 'common_offset': common,
              'r_dependent_offset': r_dependent}

    point = {}
    boot_v = {}
    boot_f = {}
    for name, data in worlds.items():
        point[name] = potential_and_force(data, window, t_values)
        boot_v[name] = _bootstrap_potentials(data, window, t_values, indices)
        boot_f[name] = np.diff(boot_v[name], axis=1)

    r_midpoints = [(float(r_values[i]) + float(r_values[i + 1])) / 2
                   for i in range(len(r_values) - 1)]
    summary_rows = []
    for name in worlds:
        v, force = point[name]
        force_draws = boot_f[name]
        force_ci = np.quantile(force_draws, [0.025, 0.975], axis=0)
        paired_shift = boot_f[name] - boot_f['baseline']
        shift_ci = np.quantile(paired_shift, [0.025, 0.975], axis=0)
        point_shift = force - point['baseline'][1]
        for j, r_mid in enumerate(r_midpoints):
            if name == 'baseline':
                expected_shift = 0.0
            elif name == 'common_offset':
                expected_shift = 0.0
            else:
                expected_shift = float(DELTA_R[j + 1] - DELTA_R[j])
            summary_rows.append({
                'world': name,
                'R_midpoint': r_mid,
                'V_R': float(v[j]),
                'V_R_plus1': float(v[j + 1]),
                'force': float(force[j]),
                'force_bootstrap_sd': float(force_draws[:, j].std(ddof=1)),
                'force_ci95_low': float(force_ci[0, j]),
                'force_ci95_high': float(force_ci[1, j]),
                'paired_force_shift_vs_baseline': float(point_shift[j]),
                'paired_shift_ci95_low': float(shift_ci[0, j]),
                'paired_shift_ci95_high': float(shift_ci[1, j]),
                'expected_shift': expected_shift,
                'planned_bootstrap_draws': int(n_boot),
                'invalid_bootstrap_draws': 0,
            })

    common_v_delta = point['common_offset'][0] - point['baseline'][0]
    common_f_delta = point['common_offset'][1] - point['baseline'][1]
    rdep_f_delta = point['r_dependent_offset'][1] - point['baseline'][1]
    result = {
        'schema': 'wilson-offset-free-force-diagnostic-v1',
        'scope': 'synthetic_method_diagnostic_only',
        'physical_score': None,
        'production_gate_modified': False,
        'seed': int(seed), 'n_config': N_CONFIG, 'block_length': BLOCK_LENGTH,
        'n_blocks': N_CONFIG // BLOCK_LENGTH, 'n_bootstrap': int(n_boot),
        'r_values': r_values, 't_values': t_values, 'window': window,
        'delta_common': DELTA_COMMON, 'delta_r': DELTA_R.tolist(),
        'max_abs_common_potential_shift_error': float(
            np.max(np.abs(common_v_delta - DELTA_COMMON))),
        'max_abs_common_force_shift': float(np.max(np.abs(common_f_delta))),
        'r_dependent_force_shift': rdep_f_delta.tolist(),
        'expected_r_dependent_force_shift': np.diff(DELTA_R).tolist(),
        'summary_rows': summary_rows,
        'limitations': [
            'The loops are synthetic positive single-exponential data with constructed block noise.',
            'The R-dependent offset is known by construction; detecting its change is not evidence that real-data bias can be separated from physical force.',
            'Intervals are pointwise descriptive bootstrap intervals, not family-wise calibrated production bounds.',
            'The offset-free force is a candidate changed estimand and is not approved by this diagnostic.',
        ],
    }
    return result, point, boot_v, boot_f


def _write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_plot(path, result, point, boot_v, boot_f):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    r = np.asarray(result['r_values'], dtype=float)
    r_mid = np.asarray([(r[i] + r[i + 1]) / 2 for i in range(len(r) - 1)])
    names = ['baseline', 'common_offset', 'r_dependent_offset']
    labels = ['baseline', 'common +0.03', 'R-dependent offset']
    colors = ['black', '#2676b8', '#d35f2d']
    figure, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    ax = axes[0]
    for name, label, color in zip(names, labels, colors):
        v = point[name][0]
        se = boot_v[name].std(axis=0, ddof=1)
        ax.errorbar(r, v, yerr=se, marker='o', capsize=3, label=label, color=color)
    ax.set_title('Potential: common offset shifts every R')
    ax.set_xlabel('R (lattice units)')
    ax.set_ylabel('V_w(R) (lattice units)')
    ax.legend(fontsize=8)

    ax = axes[1]
    for name, label, color in zip(names[:2], labels[:2], colors[:2]):
        force = point[name][1]
        se = boot_f[name].std(axis=0, ddof=1)
        ax.errorbar(r_mid, force, yerr=se, marker='o', capsize=3,
                    label=label, color=color)
    ax.set_title('Discrete force: common offset cancels')
    ax.set_xlabel('R + 1/2')
    ax.set_ylabel('V(R+1) - V(R)')
    ax.legend(fontsize=8)

    ax = axes[2]
    for name, label, color in zip(names[1:], labels[1:], colors[1:]):
        shift = boot_f[name] - boot_f['baseline']
        ci = np.quantile(shift, [0.025, 0.975], axis=0)
        median = np.median(shift, axis=0)
        ax.errorbar(r_mid, median,
                    yerr=[median - ci[0], ci[1] - median], marker='o',
                    capsize=3, label=label, color=color)
    ax.axhline(0, color='black', linewidth=0.8)
    ax.plot(r_mid, np.diff(DELTA_R), linestyle='--', color=colors[2],
            label='constructed expected R-dependent shift')
    ax.set_title('Paired force shift vs baseline')
    ax.set_xlabel('R + 1/2')
    ax.set_ylabel('ΔF')
    ax.legend(fontsize=7)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def run(output, *, seed=SEED, n_boot=N_BOOT):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    result, point, boot_v, boot_f = analyze(seed=seed, n_boot=n_boot)
    _write_csv(output / 'force_rows.csv', result['summary_rows'])
    _write_plot(output / 'offset_free_force.png', result, point, boot_v, boot_f)
    result['source_sha256'] = digest(Path(__file__))
    result['protocol_sha256'] = digest(Path(__file__).with_name('protocol_d_20261120.json'))
    result['python'] = platform.python_version()
    result['numpy'] = np.__version__
    result['matplotlib'] = __import__('matplotlib').__version__
    (output / 'summary.json').write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n')
    common_force = result['max_abs_common_force_shift']
    common_v_error = result['max_abs_common_potential_shift_error']
    expected = np.asarray(result['expected_r_dependent_force_shift'])
    observed = np.asarray(result['r_dependent_force_shift'])
    report = [
        '# Synthetic offset-free Wilson-force diagnostic', '',
        '**Status:** `synthetic_method_diagnostic_only`; no production score or gate change.', '',
        '## Text result', '',
        f'- A common potential shift δ={result["delta_common"]:.3f} shifted every fitted V by δ; '
        f'maximum numerical discrepancy from δ was `{common_v_error:.3e}`.',
        f'- The corresponding discrete-force shift was unchanged to `{common_force:.3e}` '
        'maximum absolute difference.',
        '- The constructed R-dependent offset shifted adjacent-R force by '
        + ', '.join(f'{x:.3f}' for x in observed)
        + ' (expected '
        + ', '.join(f'{x:.3f}' for x in expected) + ').',
        '- The figure shows the potential translation, overlap of the baseline/common-shift '
        'force curves, and the known R-dependent negative control.', '',
        '![Synthetic offset-free force controls](offset_free_force.png)', '',
        '## Scope and limitations', '',
        'The data are 100 synthetic positive loops with 20 blocks of length 5 and '
        f'{n_boot} shared block-bootstrap draws. The pointwise percentile intervals are '
        'descriptive. The test verifies algebra and code behavior under constructed controls; '
        'it does not establish a real-data bias detector, validate ground-state extraction, '
        'calibrate family-wise error, or approve changing the frozen absolute-potential target. '
        'A real force comparison would still need shared block indices, a frozen estimator, '
        'finite-T controls, lattice-spacing interpretation, and independent evaluation.', '',
        'Raw per-R rows and hashes are in `force_rows.csv` and `summary.json`.', '',
    ]
    (output / 'README.md').write_text('\n'.join(report), encoding='utf-8')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--seed', type=int, default=SEED)
    parser.add_argument('--n-boot', type=int, default=N_BOOT)
    args = parser.parse_args(argv)
    summary = run(args.output, seed=args.seed, n_boot=args.n_boot)
    print(json.dumps({
        'status': summary['scope'],
        'max_abs_common_force_shift': summary['max_abs_common_force_shift'],
        'r_dependent_force_shift': summary['r_dependent_force_shift'],
        'physical_score': summary['physical_score'],
    }, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
