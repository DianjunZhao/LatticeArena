"""Replay the stable two-state executor on the already audited public D0-99 data.

This is a same-input implementation check against the archived deterministic
multi-start rows.  It does not add statistical samples, select a physical
reference, or create a score.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from .reference_twostate import TwoStateFit
from .two_state_multistart_diagnostic import _load_pinned_data
from .two_state_bound_count_audit import ROOT


BASELINE = Path('results/pion_projection/two_state_multistart_d_20261120_v1')
OUTPUT = Path('results/pion_projection/two_state_executor_replay_20261120_v1')


def _read_baseline(root):
    report_dir = root / BASELINE
    receipt_path = report_dir / 'provenance.json'
    receipt_bytes = receipt_path.read_bytes()
    receipt = json.loads(receipt_bytes)
    for name, expected in receipt['outputs_sha256'].items():
        actual = hashlib.sha256((report_dir / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f'Archived multi-start output hash mismatch: {name}')
    with (report_dir / 'multistart_rows.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    grouped = defaultdict(list)
    for row in rows:
        grouped[tuple(json.loads(row['window']))].append(row)
    for window_rows in grouped.values():
        window_rows.sort(key=lambda row: int(row['start_id']))
    return receipt, hashlib.sha256(receipt_bytes).hexdigest(), grouped


def _plot(rows_by_window, path):
    windows = list(rows_by_window)
    fig, axes = plt.subplots(1, len(windows), figsize=(14, 4.5), constrained_layout=True)
    if len(windows) == 1:
        axes = [axes]
    for ax, (window, rows) in zip(axes, rows_by_window.items()):
        old = np.asarray([row['baseline_cost'] for row in rows], dtype=float)
        new = np.asarray([row['replay_cost'] for row in rows], dtype=float)
        success = np.asarray([row['replay_solver_success'] for row in rows], dtype=bool)
        for label, mask, color in (
            ('solver success', success, '#2678b2'),
            ('solver non-success', ~success, '#d95f02'),
        ):
            if np.any(mask):
                ax.scatter(old[mask], new[mask], label=label, color=color, s=28, alpha=0.8)
        lo = float(min(old.min(), new.min()))
        hi = float(max(old.max(), new.max()))
        span = max(hi - lo, 1e-8)
        ax.plot([lo - 0.03 * span, hi + 0.03 * span],
                [lo - 0.03 * span, hi + 0.03 * span], color='black', lw=1, ls='--')
        ax.set_title(f'window {list(window)}')
        ax.set_xlabel('Archived endpoint $C^2$')
        ax.set_ylabel('Stable executor endpoint $C^2$')
        ax.legend(fontsize=8)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def run(output=None, *, refresh_owned_output=False):
    root = ROOT.resolve()
    output = root / (Path(output) if output is not None else OUTPUT)
    if output.exists():
        if not refresh_owned_output:
            raise FileExistsError(f'refusing to overwrite replay output: {output}')
        receipt_path = output / 'provenance.json'
        if not receipt_path.is_file():
            raise FileExistsError(f'refusing to replace unverified output directory: {output}')
        receipt = json.loads(receipt_path.read_text())
        if receipt.get('schema') != 'pion-two-state-stable-executor-replay-provenance-v1':
            raise FileExistsError(f'refusing to replace output with unexpected provenance: {output}')
        for name, expected in receipt.get('outputs_sha256', {}).items():
            path = output / name
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise FileExistsError(f'refusing to replace modified output: {path}')

    protocol, data_blocks, input_audit = _load_pinned_data()
    baseline_receipt, baseline_receipt_sha, baseline_by_window = _read_baseline(root)
    windows = [tuple(window) for window in protocol['reference_windows']]
    if set(baseline_by_window) != set(windows):
        raise ValueError('Archived starts do not cover the frozen public-D windows')

    output.mkdir(parents=True, exist_ok=True)
    summaries = []
    rows_by_window = {}
    all_rows = []
    for window in windows:
        model = TwoStateFit(data_blocks, protocol, list(window))
        mean = model.samples.mean(axis=0)
        previous_rows = baseline_by_window[window]
        starts = np.asarray([
            [float(row['start_mass0']), float(row['start_gap'])]
            for row in previous_rows
        ])
        replay = model.fit_full_multistart(mean, starts)
        if len(replay['rows']) != len(previous_rows):
            raise ValueError(f'start count changed for window {window}')

        rows = []
        for previous, current in zip(previous_rows, replay['rows']):
            if int(previous['start_id']) != current['start_id']:
                raise ValueError(f'start ordering changed for window {window}')
            row = {
                'window': list(window),
                'start_id': current['start_id'],
                'baseline_mass0': float(previous['final_mass0']),
                'baseline_mass1': float(previous['final_mass1']),
                'baseline_gap': float(previous['final_gap']),
                'baseline_cost': float(previous['final_cost']),
                'baseline_solver_success': previous['solver_success'].lower() == 'true',
                'replay_mass0': current['mass0'],
                'replay_mass1': current['mass1'],
                'replay_gap': current['gap'],
                'replay_cost': current['cost'],
                'replay_solver_success': current['solver_success'],
                'replay_solver_status': current['solver_status'],
                'replay_status': current['endpoint_status'],
                'replay_rank': current['amplitude_rank'],
                'replay_condition': current['condition'],
                'replay_constraint_violation': current['constraint_violation'],
                'cost_abs_difference': abs(float(previous['final_cost']) - current['cost']),
                'mass0_abs_difference': abs(float(previous['final_mass0']) - current['mass0']),
                'mass1_abs_difference': abs(float(previous['final_mass1']) - current['mass1']),
            }
            rows.append(row)
            all_rows.append(row)
        rows_by_window[window] = rows
        old_cost = np.asarray([row['baseline_cost'] for row in rows])
        new_cost = np.asarray([row['replay_cost'] for row in rows])
        summaries.append({
            'window': list(window),
            'starts': len(rows),
            'baseline_solver_success': sum(row['baseline_solver_success'] for row in rows),
            'replay_solver_success': sum(row['replay_solver_success'] for row in rows),
            'replay_endpoint_status_counts': {
                status: sum(row['replay_status'] == status for row in rows)
                for status in sorted({row['replay_status'] for row in rows})
            },
            'max_abs_cost_difference': float(np.max(np.abs(old_cost - new_cost))),
            'max_abs_mass0_difference': max(row['mass0_abs_difference'] for row in rows),
            'max_abs_mass1_difference': max(row['mass1_abs_difference'] for row in rows),
            'best_replay_cost': float(np.min(new_cost)),
            'best_replay_gap': float(rows[int(np.argmin(new_cost))]['replay_gap']),
        })

    summary = {
        'schema': 'pion-two-state-stable-executor-replay-v1',
        'status': 'SAME_INPUT_PARITY_DIAGNOSTIC',
        'classification': 'diagnostic_only',
        'scope': 'public D0-99 only; same archived deterministic start set; no E, gap, validation, or shared holdout access',
        'input_audit_status': input_audit['status'],
        'verified_input_sha256': input_audit['verified_sha256'],
        'baseline_receipt_sha256': baseline_receipt_sha,
        'baseline_source_sha256': baseline_receipt.get('source_sha256'),
        'stable_executor_source_sha256': hashlib.sha256(
            (root / 'tasks/pion_projection/reference_twostate.py').read_bytes()
        ).hexdigest(),
        'window_summaries': summaries,
        'physical_score': None,
        'global_minimum_certified': False,
    }
    summary_path = output / 'summary.json'
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    csv_path = output / 'executor_replay_rows.csv'
    fieldnames = list(all_rows[0])
    with csv_path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    plot_path = output / 'executor_replay_parity.png'
    _plot(rows_by_window, plot_path)

    lines = [
        '# Stable two-state executor replay on public D0–99', '',
        '**Status: same-input numerical parity diagnostic only.** This run uses no new samples. It replays the exact archived deterministic starts on the already hash-audited D-development input, comparing the new `TwoStateFit.fit_full_multistart` implementation with the previous D-only multi-start rows.', '',
        f"Input audit: `{input_audit['status']}`. Baseline multi-start receipt SHA-256: `{baseline_receipt_sha}`. Stable executor source SHA-256: `{summary['stable_executor_source_sha256']}`.", '',
        '![Archived versus stable-executor endpoint costs](executor_replay_parity.png)', '',
        '| Window | Starts | Previous solver success | Replay solver success | Replay endpoint statuses | Max $|ΔC^2|$ | Max $|Δm_0|$ | Max $|Δm_1|$ | Best-found replay gap |',
        '|---|---:|---:|---:|---|---:|---:|---:|---:|',
    ]
    for row in summaries:
        statuses = ', '.join(f"{key}: {value}" for key, value in row['replay_endpoint_status_counts'].items())
        lines.append(
            f"| {row['window']} | {row['starts']} | {row['baseline_solver_success']}/{row['starts']} | "
            f"{row['replay_solver_success']}/{row['starts']} | {statuses} | "
            f"{row['max_abs_cost_difference']:.3g} | {row['max_abs_mass0_difference']:.3g} | "
            f"{row['max_abs_mass1_difference']:.3g} | {row['best_replay_gap']:.6g} |"
        )
    lines += [
        '',
        'The parity plot compares each archived endpoint objective to the replayed objective; the dashed line is equality. Non-success endpoints remain present and are colored separately. The CSV retains every start and both solver statuses.', '',
        '## Limits', '',
        '- Both analyses use the same D0–99 data, the same fixed covariance, the same SLSQP implementation, and the same starts; this is a code-path check, not an independent fit or Monte Carlo replication.',
        '- A finite lower endpoint is only the best found among these starts. It is not a global-minimum certificate.',
        '- `gap=0` is reported as the nested M1 boundary; failed SLSQP endpoints there remain nonconverged and cannot be called a two-state solution.',
        '- This does not reopen the frozen single-cosh FAIL, approve the draft M2 plan, authorize E measurement, or create a physical score. `physical_score=null`.',
        '- Reproduce with `PYTHONDONTWRITEBYTECODE=1 python3 -B -m tasks.pion_projection.two_state_executor_replay`; output includes the CSV, JSON summary, PNG and hash provenance. Existing output is refused unless `--refresh-owned-output` first verifies the script\'s own prior output hashes.',
        '',
    ]
    report_path = output / 'README.md'
    report_path.write_text('\n'.join(lines))
    outputs = ['summary.json', 'executor_replay_rows.csv', 'executor_replay_parity.png', 'README.md']
    provenance = {
        'schema': 'pion-two-state-stable-executor-replay-provenance-v1',
        'summary_sha256': hashlib.sha256(summary_path.read_bytes()).hexdigest(),
        'report_sha256': hashlib.sha256(report_path.read_bytes()).hexdigest(),
        'outputs_sha256': {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                           for name in outputs},
        'verified_input_sha256': input_audit['verified_sha256'],
        'baseline_receipt_sha256': baseline_receipt_sha,
    }
    (output / 'provenance.json').write_text(json.dumps(provenance, indent=2, sort_keys=True) + '\n')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=None, help='new output directory; existing outputs are refused')
    parser.add_argument('--refresh-owned-output', action='store_true',
                        help='refresh only this script schema after verifying its prior output hashes')
    args = parser.parse_args()
    summary = run(args.output, refresh_owned_output=args.refresh_owned_output)
    print(json.dumps({'status': summary['status'], 'windows': summary['window_summaries']}, indent=2))


if __name__ == '__main__':
    main()
