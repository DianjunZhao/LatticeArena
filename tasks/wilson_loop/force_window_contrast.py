"""Paired window contrasts on opened Wilson development data; descriptive only."""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import numpy as np
from .development_force_diagnostic import force_diagnostic
from .reference_gate_runner import _load_complete_development


def contrasts(point, draws):
    """All three ordered later-minus-earlier differences, keeping paired draws."""
    point, draws = np.asarray(point), np.asarray(draws)
    if point.ndim != 3 or point.shape[1] != 3 or draws.shape[1:] != point.shape:
        raise ValueError('expected point(kernel,3,R) and draws(draw,kernel,3,R)')
    if not np.isfinite(point).all() or not np.isfinite(draws).all():
        raise ValueError('nonfinite input; use an explicitly recorded complete-draw mask')
    pairs = [(0, 1), (1, 2), (0, 2)]
    p = np.stack([point[:, b] - point[:, a] for a, b in pairs], axis=1)
    d = np.stack([draws[:, :, b] - draws[:, :, a] for a, b in pairs], axis=2)
    return p, d, pairs


def self_check():
    # Shared additive fluctuations cancel; unpaired resampling would fail this.
    p = np.arange(18.).reshape(2, 3, 3)
    d = p[None] + np.arange(5.)[:, None, None, None]
    cp, cd, pairs = contrasts(p, d)
    np.testing.assert_allclose(cd, np.broadcast_to(cp, cd.shape))
    # An R-dependent offset common to all windows leaves every contrast intact.
    cp2, cd2, _ = contrasts(p + np.array([2., 4., 8.]),
                            d + np.array([2., 4., 8.]))
    np.testing.assert_allclose(cp2, cp)
    np.testing.assert_allclose(cd2, cd)
    # Known kernel-dependent late-window contamination survives, including DoD.
    altered = p.copy()
    altered[1, 2] += np.array([.1, .2, .3])
    ap, _, _ = contrasts(altered, np.broadcast_to(altered, (5,) + altered.shape))
    np.testing.assert_allclose(ap[1, 2] - cp[1, 2], [.1, .2, .3])
    assert pairs == [(0, 1), (1, 2), (0, 2)]
    for bad in [np.full_like(p, np.nan), p[:, :2]]:
        try:
            contrasts(bad, d)
        except ValueError:
            pass
        else:
            raise AssertionError('bad input accepted')
    return {'checks': 5, 'status': 'PASS'}


def run(output):
    root = Path(__file__).resolve().parents[2]
    protocol_path = root / 'tasks/wilson_loop/protocol_d_20261120.json'
    protocol_bytes = protocol_path.read_bytes()
    protocol = json.loads(protocol_bytes)
    previous = root / 'results/wilson_loop/development_force_diagnostic_20261121_v1'
    metadata = json.loads((previous / 'summary.json').read_text())
    sample = _load_complete_development(root / 'results/wilson_loop/s16t16d_development_20261120', protocol)
    hashes = {name: hashlib.sha256(value).hexdigest() for name, value in sample['payloads'].items()}
    if hashes != metadata['transaction_sha256']:
        raise ValueError('transaction changed since prior diagnostic')
    if hashlib.sha256(protocol_bytes).hexdigest() != metadata['analysis_protocol_sha256']:
        raise ValueError('protocol changed since prior diagnostic')
    with np.load(io.BytesIO(sample['payloads']['development.npz']), allow_pickle=False) as data:
        loops = data['loops'].copy()
    result = force_diagnostic(loops, protocol, bootstrap_samples=metadata['bootstrap_samples'], seed=metadata['seed'])
    with np.load(previous / 'bootstrap_indices.npz', allow_pickle=False) as saved:
        np.testing.assert_array_equal(result['bootstrap_index'], saved['indices'])
    if result['invalid_draws']:
        raise ValueError('current replay has invalid complete draws; stop and inspect')
    # Exact replay of all old force point estimates before deriving new quantities.
    for current, prior in zip(result['window_rows'], metadata['window_rows'], strict=True):
        if current != prior:
            raise ValueError('force replay differs from previous receipt')
    point, draws, pairs = contrasts(result['window_point'], result['window_draws'])
    dod_point, dod_draws = point[1:] - point[0], draws[:, 1:] - draws[:, :1]
    rows = []
    for kind, pts, ds, names in [
        ('window_drift', point, draws, result['kernel_names']),
        ('candidate_minus_identity_drift', dod_point, dod_draws, result['kernel_names'][1:]),
    ]:
        for k, name in enumerate(names):
            for j, (a, b) in enumerate(pairs):
                for r, midpoint in enumerate(result['r_midpoints']):
                    values = ds[:, k, j, r]
                    low, high = np.quantile(values, [.025, .975])
                    rows.append({'kind': kind, 'kernel': name,
                        'earlier_window': result['window_labels'][a],
                        'later_window': result['window_labels'][b], 'R_midpoint': midpoint,
                        'point': float(pts[k, j, r]), 'paired_sd': float(values.std(ddof=1)),
                        'pointwise_ci95_low': float(low), 'pointwise_ci95_high': float(high),
                        'planned_draws': result['bootstrap_samples'], 'valid_draws': result['valid_draws'],
                        'failed_draws': result['invalid_draws']})
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    with (output / 'contrasts.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    np.savez_compressed(output / 'paired_draws.npz', window_point=result['window_point'],
        window_draws=result['window_draws'], drift_point=point, drift_draws=draws,
        difference_of_differences_point=dod_point, difference_of_differences_draws=dod_draws,
        bootstrap_indices=result['bootstrap_index'])
    receipt = {'status': 'DEVELOPMENT_DESCRIPTIVE_ONLY', 'physical_score': None,
        'input_ids': sample['ids'].tolist() if hasattr(sample['ids'], 'tolist') else sample['ids'],
        'generation': sample['generation'], 'transaction_sha256': hashes,
        'protocol_sha256': hashlib.sha256(protocol_bytes).hexdigest(),
        'source_sha256': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in [Path(__file__), root / 'tasks/wilson_loop/development_force_diagnostic.py',
                                     root / 'tasks/wilson_loop/statistics.py']},
        'previous_summary_sha256': hashlib.sha256((previous / 'summary.json').read_bytes()).hexdigest(),
        'replay': 'exact force rows and bootstrap indices match previous receipt',
        'seed': result['seed'], 'block_count': result['block_count'], 'block_length': result['block_length'],
        'planned_draws': result['bootstrap_samples'], 'valid_draws': result['valid_draws'],
        'failed_draws': result['invalid_draws'], 'self_check': self_check(),
        'interval': 'pointwise percentile 95%; no simultaneous calibration',
        'contrast_count': len(rows), 'kernel_window_R_drift_count': 63,
        'difference_of_differences_count': 54, 'sealed_splits_accessed': False}
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(14, 5.5), sharey=True)
    names = result['kernel_names']
    for r, ax in enumerate(axes):
        for k, name in enumerate(names):
            row = next(row for row in rows if row['kind'] == 'window_drift'
                and row['kernel'] == name and row['earlier_window'] == result['window_labels'][0]
                and row['later_window'] == result['window_labels'][2]
                and row['R_midpoint'] == result['r_midpoints'][r])
            ax.hlines(k, row['pointwise_ci95_low'], row['pointwise_ci95_high'], color='C0')
            ax.plot(row['point'], k, 'o', color='C0')
        ax.axvline(0, color='black', linewidth=.8)
        ax.set_title(f"R midpoint = {result['r_midpoints'][r]}")
        ax.set_xlabel('late minus early force; lattice units')
        ax.grid(alpha=.25, axis='x')
    axes[0].set_yticks(range(len(names)), names, fontsize=8)
    axes[0].invert_yaxis()
    fig.suptitle('D0–99 development: paired pointwise 95% intervals; no ground-state certificate')
    fig.tight_layout()
    fig.savefig(output / 'late_minus_early.png', dpi=160)
    plt.close(fig)
    lines = ['# Wilson D0–99: paired force window drift', '',
        '**Status: DEVELOPMENT_DESCRIPTIVE_ONLY; physical_score=null.**', '',
        'The previous force receipt supplied per-window intervals. This replay forms the window differences on the same resampling row, preserving covariance between overlapping windows. No new gauge data or independent synthetic datasets were generated.', '',
        '`D(k,w_b,w_a,R) = f(k,w_b,R) - f(k,w_a,R)`; candidate difference of drifts is `D(k)-D(identity)`. All three later-minus-earlier pairs are retained: nominal−early, late−nominal, late−early. There are 63 drift contrasts and 54 candidate-minus-identity contrasts; intervals are pointwise and exploratory. No multiplicity control or equivalence margin has been supplied.', '',
        'Source: complete D0–99 development transaction, protocol_d_20261120.json, 20 contiguous length-5 blocks, original 5,000 shared draws and seed. Transaction hashes, original protocol hash, all old window-force rows and saved resampling indices match exactly before deriving these contrasts. Full identity and code hashes are in receipt.json. Draw denominator: 5,000 planned, 5,000 valid, 0 failed. These are bootstrap draws over 20 blocks, not 5,000 independent configurations.', '',
        '## Identity early/late contrast', '',
        '| R midpoint | late−early force | paired SD | pointwise 95% interval |',
        '|---|---:|---:|---:|']
    for row in rows:
        if row['kind'] == 'window_drift' and row['kernel'] == 'identity' and row['earlier_window'] == result['window_labels'][0] and row['later_window'] == result['window_labels'][2]:
            lines.append(f"| {row['R_midpoint']} | {row['point']:.6f} | {row['paired_sd']:.6f} | [{row['pointwise_ci95_low']:.6f}, {row['pointwise_ci95_high']:.6f}] |")
    lines += ['', '![Late minus early force](late_minus_early.png)', '',
        '## What changes in the decision', '',
        'The paired table quantifies window sensitivity directly; overlapping individual window error bars do not substitute for this contrast. A small or zero-compatible drift cannot bound a bias shared by all windows. Candidate drift closer to zero can reflect altered overlap, cancellation, or loss of sensitivity; it cannot identify ground-state accuracy. The CSV contains every contrast, including all failures in the denominator, rather than selecting a winning kernel.', '',
        'The current development evidence therefore supports planning finite-T controls, but cannot certify ground-state force. If the chosen target is finite-T Creutz χ, T is part of the estimand and a force plateau is unnecessary; the research question and simultaneous comparison family must still be frozen before new confirmation data. If the chosen target is absolute potential, independent zero-point and shape-bias evidence remains necessary. These distinctions cannot be decided from this exploratory drift plot.', '',
        '## Reproduce and verify', '',
        'Run from the repository root, selecting a new output directory (existing outputs are refused):', '',
        '```text',
        'PYTHONDONTWRITEBYTECODE=1 python3 -B -m tasks.wilson_loop.force_window_contrast --self-check',
        'PYTHONDONTWRITEBYTECODE=1 python3 -B -m tasks.wilson_loop.force_window_contrast --output-dir tasks/wilson_loop/force_window_contrast_20261121_v1',
        '```', '',
        'Five analytic/input checks pass: exact cancellation of shared fluctuations; invariance to window-common R-dependent shifts; known late-window contamination; pair order; nonfinite/wrong-shape refusal. Existing force tests should also be run when modifying the estimator. No validation, gap or holdout input was accessed.']
    (output / 'README.md').write_text('\n'.join(lines) + '\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', default='tasks/wilson_loop/force_window_contrast_20261121_v1')
    parser.add_argument('--self-check', action='store_true')
    args = parser.parse_args()
    print(json.dumps(self_check() if args.self_check else run(args.output_dir), indent=2))
