"""D-development-only multistart audit for the two-state fit path.

This diagnostic compares the existing coordinate-search endpoint with a
deterministic grid of constrained SLSQP starts. Amplitudes are profiled by
whitened least squares, including the rank-deficient gap=0 boundary. The
result is a numerical stability audit, not a reference gate or physical score.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import minimize

from .reference_twostate import TwoStateFit
from .statistics import blocks, fold
from .two_state_bound_count_audit import ARCHIVE, PROTOCOL, ROOT, audit


OUTPUT = Path('results/pion_projection/two_state_multistart_d_20261120_v1')
ACTIVE_TOL = 1e-5
BASIN_TOL = 0.02


def _prepare_objective(model, mean):
    """Prepare fixed-covariance variable-projection objective components."""
    precision = 0.5 * (np.asarray(model.inv, dtype=float) + np.asarray(model.inv, dtype=float).T)
    whitener = np.linalg.cholesky(precision).T
    mean = np.asarray(mean, dtype=float)
    if mean.shape != (model.samples.shape[1],) or not np.isfinite(mean).all():
        raise ValueError('mean must be finite and match the fitted data dimension')
    weighted_mean = whitener @ mean

    def evaluate(mass0, gap):
        mass0, gap = float(mass0), float(gap)
        design = model.design(mass0, mass0 + gap)
        weighted_design = whitener @ design
        amplitudes, _, rank, singular_values = np.linalg.lstsq(
            weighted_design, weighted_mean, rcond=None,
        )
        residual = weighted_mean - weighted_design @ amplitudes
        cost = float(residual @ residual)
        condition = (float(singular_values[0] / singular_values[-1])
                     if rank == weighted_design.shape[1] and len(singular_values)
                     and singular_values[-1] > 0 else float('inf'))
        return cost, amplitudes, int(rank), condition

    return evaluate


def _constraint_violation(mass0, gap, lo, hi):
    return float(max(0.0, lo - mass0, -gap, mass0 + gap - hi))


def _active_boundaries(mass0, gap, lo, hi, tol=ACTIVE_TOL):
    active = []
    if abs(mass0 - lo) <= tol:
        active.append('mass0_lower')
    if abs(mass0 + gap - hi) <= tol:
        active.append('mass1_upper')
    if gap <= tol:
        active.append('gap_zero')
    return active


def _label_basins(rows, tolerance=BASIN_TOL):
    """Assign approximate endpoint clusters using a fixed max-coordinate radius."""
    centers = []
    for row in sorted(rows, key=lambda item: item['final_cost']):
        point = np.array([row['final_mass0'], row['final_gap']])
        matches = [i for i, center in enumerate(centers)
                   if np.max(np.abs(point - center)) <= tolerance]
        if matches:
            row['basin_id'] = matches[0]
        else:
            row['basin_id'] = len(centers)
            centers.append(point)
    return len(centers)


def fit_two_state_multistart(model, mean, starts, *, maxiter=500, ftol=1e-10):
    """Run an auditable constrained SLSQP fit from each supplied (m0, gap).

    The amplitudes are solved exactly at every objective call. Results are
    retained even when SLSQP reports failure; this function never applies a
    pass/fail gate or selects a physics score.
    """
    lo, hi = map(float, model.p['mass_bounds'])
    if not np.isfinite([lo, hi]).all() or hi <= lo:
        raise ValueError('invalid mass bounds')
    starts = np.asarray(starts, dtype=float)
    if starts.ndim != 2 or starts.shape[1] != 2 or len(starts) == 0:
        raise ValueError('starts must be a nonempty (n, 2) array of (mass0, gap)')
    if not np.isfinite(starts).all():
        raise ValueError('starts must be finite')
    for mass0, gap in starts:
        if mass0 < lo or gap < 0 or mass0 + gap > hi:
            raise ValueError(f'infeasible starting point {(mass0, gap)}')

    evaluate = _prepare_objective(model, mean)

    def objective(z):
        return evaluate(z[0], z[1])[0]

    rows = []
    for start_index, (mass0_start, gap_start) in enumerate(starts):
        result = minimize(
            objective,
            np.array([mass0_start, gap_start], dtype=float),
            method='SLSQP',
            bounds=[(lo, hi), (0.0, hi - lo)],
            constraints=[{'type': 'ineq', 'fun': lambda z: hi - z[0] - z[1]}],
            options={'maxiter': int(maxiter), 'ftol': float(ftol)},
        )
        final_mass0, final_gap = map(float, result.x)
        try:
            cost, amplitudes, rank, condition = evaluate(final_mass0, final_gap)
            finite = bool(np.isfinite(cost) and np.isfinite(amplitudes).all())
        except (ValueError, np.linalg.LinAlgError, FloatingPointError):
            cost, amplitudes, rank, condition, finite = float('inf'), np.array([]), 0, float('inf'), False
        rows.append({
            'start_id': int(start_index),
            'start_mass0': float(mass0_start),
            'start_gap': float(gap_start),
            'final_mass0': final_mass0,
            'final_mass1': final_mass0 + final_gap,
            'final_gap': final_gap,
            'final_cost': float(cost),
            'finite_endpoint': finite,
            'solver_success': bool(result.success),
            'solver_status': int(result.status),
            'solver_message': str(result.message),
            'nfev': int(getattr(result, 'nfev', 0)),
            'nit': int(getattr(result, 'nit', 0)),
            'constraint_violation': _constraint_violation(final_mass0, final_gap, lo, hi),
            'active_boundaries': _active_boundaries(final_mass0, final_gap, lo, hi),
            'amplitude_rank': rank,
            'amplitude_condition': condition,
            'amplitudes': np.asarray(amplitudes, dtype=float).tolist(),
        })
    basin_count = _label_basins(rows)
    for row in rows:
        row['approximate_basin_count'] = basin_count
    return rows


def _make_starts(lo, hi, legacy):
    width = hi - lo
    mass0s = np.linspace(lo + 0.03 * width, hi - 0.60 * width, 5)
    gaps = np.linspace(0.0, 0.90 * width, 7)
    starts = [(float(mass0), float(gap)) for mass0 in mass0s for gap in gaps
              if mass0 + gap <= hi - 1e-10]
    starts.append((float(legacy['mass']), float(legacy['gap'])))
    unique = []
    seen = set()
    for mass0, gap in starts:
        key = (round(mass0, 10), round(gap, 10))
        if key not in seen:
            unique.append((mass0, gap))
            seen.add(key)
    return np.asarray(unique, dtype=float)


def _load_pinned_data():
    receipt = audit()
    verified = receipt['verified_sha256']
    protocol_bytes = (ROOT / PROTOCOL).read_bytes()
    if hashlib.sha256(protocol_bytes).hexdigest() != verified[str(PROTOCOL)]:
        raise ValueError('protocol changed after pinned input audit')
    protocol = json.loads(protocol_bytes)
    measurement_bytes = (ROOT / ARCHIVE / 'development.npz').read_bytes()
    measurement_rel = str(ARCHIVE / 'development.npz')
    if hashlib.sha256(measurement_bytes).hexdigest() != verified[measurement_rel]:
        raise ValueError('D-development input changed after pinned input audit')
    with np.load(io.BytesIO(measurement_bytes), allow_pickle=False) as data:
        ids = np.asarray(data['ids'])
        raw = np.asarray(data['correlators'], dtype=float)
    if not np.array_equal(ids, np.arange(100)):
        raise ValueError('only public D0-99 is allowed')
    expected = (100, len(protocol['powers']), protocol['geometry'][3])
    if raw.shape != expected or not np.isfinite(raw).all():
        raise ValueError(f'unexpected/nonfinite D-development data shape: {raw.shape}')
    return protocol, blocks(fold(raw), protocol['block_length']), receipt


def _plot(rows_by_window, legacy_by_window, summary_path):
    figure, axes = plt.subplots(1, len(rows_by_window), figsize=(15, 5), constrained_layout=True)
    if len(rows_by_window) == 1:
        axes = [axes]
    scatter = None
    for ax, (window, rows), legacy in zip(axes, rows_by_window.items(), legacy_by_window):
        finite = [row for row in rows if row['finite_endpoint']]
        best = min(finite, key=lambda row: row['final_cost'])
        delta = np.asarray([max(0.0, row['final_cost'] - best['final_cost']) for row in rows])
        colors = np.log10(delta + 1e-10)
        for row, color in zip(rows, colors):
            ax.plot([row['start_mass0'], row['final_mass0']],
                    [row['start_gap'], row['final_gap']],
                    color=plt.cm.viridis((color - colors.min()) / max(np.ptp(colors), 1e-12)),
                    alpha=0.22, lw=0.8)
        scatter = ax.scatter([row['start_mass0'] for row in rows],
                             [row['start_gap'] for row in rows], c=colors,
                             cmap='viridis', s=35, edgecolors='white', linewidths=0.35)
        ax.scatter([legacy['mass']], [legacy['gap']], marker='D', s=65,
                   color='#7c3aed', edgecolors='white', linewidths=0.6,
                   label='existing coordinate-search fit')
        ax.scatter([best['final_mass0']], [best['final_gap']], marker='*', s=150,
                   color='#15803d', edgecolors='white', linewidths=0.6,
                   label='best multistart endpoint')
        ax.axhline(0, color='#b91c1c', ls='--', lw=1, label='gap=0 boundary')
        success_n = sum(row['solver_success'] for row in rows)
        basins = rows[0]['approximate_basin_count']
        ax.set_title(f'window {window}\nSLSQP success {success_n}/{len(rows)}; endpoint clusters {basins}')
        ax.set_xlabel(r'start / fitted ground mass $m_0$')
        ax.set_ylabel(r'start / fitted gap $m_1-m_0$')
        ax.grid(alpha=.22)
        ax.legend(fontsize=7, frameon=False)
    colorbar = figure.colorbar(scatter, ax=axes, shrink=0.85)
    colorbar.set_label(r'$log_{10}(Delta C^2+10^{-10})$ from best endpoint')
    figure.suptitle('D0–99 only: deterministic multistart basin diagnostic (not a gate)')
    figure.savefig(summary_path.parent / 'two_state_multistart.png', dpi=180)
    plt.close(figure)


def run(output=None):
    output = ROOT / (Path(output) if output is not None else OUTPUT)
    if output.exists():
        raise FileExistsError(f'refusing to overwrite diagnostic output: {output}')
    protocol, data_blocks, audit_receipt = _load_pinned_data()
    windows = protocol['reference_windows']
    lo, hi = map(float, protocol['mass_bounds'])
    rows_by_window = {}
    legacy_by_window = []
    summary_windows = []
    all_rows = []

    for window in windows:
        model = TwoStateFit(data_blocks, protocol, window)
        mean = model.samples.mean(axis=0)
        legacy = model.fit_full(mean)
        starts = _make_starts(lo, hi, legacy)
        rows = fit_two_state_multistart(model, mean, starts)
        rows_by_window[tuple(window)] = rows
        legacy_by_window.append(legacy)
        all_rows.extend({'window': json.dumps(list(window)), **row} for row in rows)
        finite = [row for row in rows if row['finite_endpoint']]
        if not finite:
            best = None
        else:
            best = min(finite, key=lambda row: row['final_cost'])
        summary_windows.append({
            'window': list(window),
            'start_count': len(starts),
            'solver_success_count': sum(row['solver_success'] for row in rows),
            'solver_failure_messages': {
                f"status={status}: {message}": count
                for (status, message), count in sorted(Counter(
                    (row['solver_status'], row['solver_message'])
                    for row in rows if not row['solver_success']
                ).items())
            },
            'finite_endpoint_count': len(finite),
            'approximate_endpoint_cluster_count': rows[0]['approximate_basin_count'],
            'boundary_endpoint_count': sum(bool(row['active_boundaries']) for row in rows),
            'gap_zero_endpoint_count': sum('gap_zero' in row['active_boundaries'] for row in rows),
            'non_success_endpoint_at_gap_zero_count': sum(
                not row['solver_success'] and 'gap_zero' in row['active_boundaries'] for row in rows
            ),
            'non_success_start_at_gap_zero_count': sum(
                not row['solver_success'] and row['start_gap'] <= ACTIVE_TOL for row in rows
            ),
            'legacy_coordinate_search': {
                'mass0': legacy['mass'], 'mass1': legacy['mass2'], 'gap': legacy['gap'],
                'cost': legacy['cost'], 'condition': legacy['condition'],
            },
            'best_multistart_endpoint': None if best is None else {
                key: best[key] for key in (
                    'final_mass0', 'final_mass1', 'final_gap', 'final_cost',
                    'solver_success', 'solver_status', 'solver_message', 'amplitude_rank',
                    'amplitude_condition', 'active_boundaries', 'basin_id',
                )
            },
            'cost_improvement_vs_legacy': None if best is None else float(legacy['cost'] - best['final_cost']),
            'interpretation': 'SLSQP success and endpoint clustering are numerical diagnostics only; neither certifies a global minimum or identifies a physical excited state.',
        })

    output.mkdir(parents=True, exist_ok=False)
    summary_path = output / 'summary.json'
    summary = {
        'schema': 'pion-two-state-multistart-diagnostic-v1',
        'status': 'DEVELOPMENT_DIAGNOSTIC_ONLY',
        'physical_score': None,
        'scope': 'public D0-99 only; no E, gap, validation, embargo, or shared holdout access',
        'input_audit_status': audit_receipt['status'],
        'verified_input_sha256': audit_receipt['verified_sha256'],
        'method': {
            'optimizer': 'SLSQP with deterministic mass0-gap grid and legacy endpoint start',
            'objective': 'fixed shrinkage-covariance quadratic; linear amplitudes profiled by whitened SVD least squares',
            'bounds': {'mass0': [lo, hi], 'gap': [0.0, hi - lo], 'mass1_max': hi},
            'ftol': 1e-10, 'maxiter': 500,
            'active_bound_tolerance': ACTIVE_TOL,
            'endpoint_cluster_tolerance_max_coordinate': BASIN_TOL,
            'cluster_count_limitation': 'greedy descriptive clustering of endpoints; not a mathematical basin count',
            'bootstrap': 'not run; same full-sample objective used for each start',
        },
        'windows': summary_windows,
        'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'numpy_version': np.__version__,
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    with (output / 'multistart_rows.csv').open('w', newline='') as stream:
        fields = ['window', 'start_id', 'start_mass0', 'start_gap', 'final_mass0',
                  'final_mass1', 'final_gap', 'final_cost', 'finite_endpoint',
                  'solver_success', 'solver_status', 'solver_message', 'nfev', 'nit',
                  'constraint_violation', 'active_boundaries', 'amplitude_rank',
                  'amplitude_condition', 'amplitudes', 'basin_id', 'approximate_basin_count']
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in all_rows:
            formatted = dict(row)
            for key in ('active_boundaries', 'amplitudes'):
                formatted[key] = json.dumps(formatted[key], separators=(',', ':'))
            writer.writerow(formatted)

    _plot(rows_by_window, legacy_by_window, summary_path)
    lines = [
        '# Two-state multistart search diagnostic on D development', '',
        '**Status: development-only numerical diagnostic; the frozen single-cosh reference gate remains failed.** This result does not authorize an E measurement, validation access, shared-holdout access, or physical score.', '',
        'The same pinned D0–99 samples and fixed covariance objective are evaluated from a deterministic grid of SLSQP starting points, plus the existing coordinate-search endpoint. At each objective call, amplitudes are profiled with whitened least squares. The scan includes the `gap=0` one-state boundary and records optimizer status, iterations, evaluations, active bounds, finite endpoints, and approximate endpoint clusters for every start.', '',
        '![D-only multistart trajectories and objective differences](two_state_multistart.png)', '',
        '| Window | Starts | SLSQP success | Non-success terminal status | Finite endpoints | Approx. endpoint clusters | Boundary endpoints | gap=0 endpoints | Best gap | Legacy gap | Legacy minus best $C^2$ |',
        '|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for row in summary_windows:
        best = row['best_multistart_endpoint']
        gap = 'none' if best is None else f"{best['final_gap']:.5g}"
        improvement = 'none' if row['cost_improvement_vs_legacy'] is None else f"{row['cost_improvement_vs_legacy']:.5g}"
        failures = '; '.join(f'{count} × {message}' for message, count in row['solver_failure_messages'].items()) or '0'
        lines.append(
            f"| {row['window']} | {row['start_count']} | {row['solver_success_count']}/{row['start_count']} | {failures} | "
            f"{row['finite_endpoint_count']}/{row['start_count']} | {row['approximate_endpoint_cluster_count']} | "
            f"{row['boundary_endpoint_count']} | {row['gap_zero_endpoint_count']} | {gap} | "
            f"{row['legacy_coordinate_search']['gap']:.5g} | {improvement} |"
        )
    lines += ['', '## Non-success termination details', '']
    for row in summary_windows:
        start_count = row['non_success_start_at_gap_zero_count']
        endpoint_count = row['non_success_endpoint_at_gap_zero_count']
        failure_summary = '; '.join(
            f'{count} × {message}' for message, count in row['solver_failure_messages'].items()
        ) or 'none'
        lines.append(
            f"- Window {row['window']}: {failure_summary}; {endpoint_count} non-success endpoints are at `gap=0`, "
            f"and {start_count} of them started there. At `gap=0`, the two design columns coincide and the amplitudes lose rank; "
            'this association is a numerical degeneracy warning, not proof that it is the only cause of the SLSQP status.'
        )
    lines += [
        '', '## Interpretation boundary', '',
        '- This compares deterministic local-search starts on the same D sample; it is not an independent validation or uncertainty estimate.',
        '- A lower endpoint objective shows sensitivity to initialization under this optimizer and objective. It does not show that the returned point is the global minimum.',
        '- Endpoint clusters use a descriptive greedy tolerance of 0.02 in both mass0 and gap. The cluster count is not a formal count of mathematical basins.',
        '- `gap=0` makes the two design columns identical. The SVD least-squares objective remains finite there, while the amplitudes are non-identifiable; boundary endpoints must therefore be read together with rank and condition fields.',
        '- Solver `success` is only the SLSQP termination flag. No solver result here reopens the frozen reference gate, changes the candidate score, or licenses reading E, validation, or holdout data.',
        '- The result can inform a new pre-E proposal. Any confirmation model, time window, covariance, adequacy threshold, and failure/abstention rule still need independent review and must be frozen before E is measured.', '',
    ]
    report_path = output / 'README.md'
    report_path.write_text('\n'.join(lines))
    output_files = ['summary.json', 'multistart_rows.csv', 'two_state_multistart.png', 'README.md']
    provenance = {
        'schema': 'pion-two-state-multistart-provenance-v1',
        'scope': summary['scope'],
        'source_sha256': summary['source_sha256'],
        'verified_input_sha256': audit_receipt['verified_sha256'],
        'outputs_sha256': {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                           for name in output_files},
    }
    (output / 'provenance.json').write_text(json.dumps(provenance, indent=2, sort_keys=True) + '\n')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = run(args.output)
    print(json.dumps({'status': result['status'], 'windows': result['windows']}, indent=2))
