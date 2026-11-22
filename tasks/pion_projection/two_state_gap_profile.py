"""D-development-only two-state gap-profile feasibility diagnostic.

This reads only the pinned public D0-99 archive. It does not refit an E chain,
run a bootstrap, write a score, or change any reference gate. The profile is a
numerical identifiability diagnostic; its objective differences are not a
calibrated likelihood-ratio test.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import minimize_scalar

from .reference_twostate import TwoStateFit
from .statistics import blocks, fold, shape
from .two_state_bound_count_audit import ARCHIVE, PROTOCOL, ROOT, audit


OUTPUT = Path('results/pion_projection/two_state_gap_profile_d_20261120_v1')
MASS_STEP = 0.01
GAP_STEP = 0.02
LOCAL_GAP_STEP = 0.003
LOCAL_GAP_HALF_WIDTH = 0.1


def _cost_at_m0(model, mean, gap, mass0, whitener, weighted_mean):
    """Evaluate the fixed-covariance quadratic with amplitudes profiled out."""
    mass1 = mass0 + gap
    design = model.design(float(mass0), float(mass1))
    weighted_design = whitener @ design
    amplitudes, *_ = np.linalg.lstsq(weighted_design, weighted_mean, rcond=None)
    residual = weighted_mean - weighted_design @ amplitudes
    return float(residual @ residual)


def _profile_one_gap(model, mean, gap, masses0, whitener, weighted_mean):
    """Minimize the fixed-covariance quadratic over m0 at one fixed gap.

    The coarse scan locates every sampled local minimum; bounded scalar
    refinements then reduce the chance that a narrow ill-conditioned basin is
    missed between adjacent m0 grid points.
    """
    lo, hi = model.p['mass_bounds']
    best_cost, best_mass0 = np.inf, None
    costs = []
    for mass0 in masses0:
        mass1 = mass0 + gap
        if mass0 < lo or not mass0 <= mass1 < hi:
            costs.append(np.inf)
            continue
        cost = _cost_at_m0(model, mean, gap, float(mass0), whitener, weighted_mean)
        costs.append(cost)
        if np.isfinite(cost) and cost < best_cost:
            best_cost, best_mass0 = cost, float(mass0)
    if best_mass0 is None:
        raise ValueError(f'No mass0 value is feasible for gap={gap}')

    costs = np.asarray(costs)
    minima = [i for i in range(len(costs))
              if np.isfinite(costs[i])
              and (i == 0 or costs[i] <= costs[i - 1])
              and (i == len(costs) - 1 or costs[i] <= costs[i + 1])]
    for index in minima:
        if index == 0 or index == len(costs) - 1:
            continue
        left, right = float(masses0[index - 1]), float(masses0[index + 1])
        if not left < right:
            continue
        result = minimize_scalar(
            lambda mass0: _cost_at_m0(model, mean, gap, mass0, whitener, weighted_mean),
            bounds=(left, right), method='bounded', options={'xatol': 1e-10},
        )
        if result.success and np.isfinite(result.fun) and result.fun < best_cost:
            best_cost, best_mass0 = float(result.fun), float(result.x)
    return best_cost, best_mass0


def profile_gap_curve(model, mean, gaps, *, mass_step=MASS_STEP):
    """Profile the same quadratic objective over ordered mass pairs.

    Gap zero is included as the nested one-state boundary. Amplitudes are
    solved by whitened least squares, which remains defined when the two design
    columns coincide at gap zero. The output is descriptive, not a calibrated
    test statistic.
    """
    lo, hi = map(float, model.p['mass_bounds'])
    gaps = np.asarray(gaps, dtype=float)
    if gaps.ndim != 1 or not len(gaps) or not np.isfinite(gaps).all():
        raise ValueError('gaps must be a nonempty finite vector')
    if np.any(gaps < 0) or np.any(gaps >= hi - lo):
        raise ValueError('gaps must satisfy 0 <= gap < mass-domain width')
    if not np.isfinite(mass_step) or mass_step <= 0:
        raise ValueError('mass_step must be positive and finite')

    precision = 0.5 * (model.inv + model.inv.T)
    whitener = np.linalg.cholesky(precision).T
    mean = np.asarray(mean, dtype=float)
    if mean.shape != (model.samples.shape[1],) or not np.isfinite(mean).all():
        raise ValueError('mean must be a finite vector matching the fitted data')
    weighted_mean = whitener @ mean

    costs, best_masses0 = [], []
    for gap in gaps:
        stop = hi - float(gap) - 1e-10
        masses0 = np.arange(lo + 1e-10, stop, mass_step)
        if len(masses0) == 0:
            raise ValueError(f'No mass0 grid points are feasible for gap={gap}')
        cost, mass0 = _profile_one_gap(model, mean, float(gap), masses0, whitener, weighted_mean)
        costs.append(cost)
        best_masses0.append(mass0)

    coarse_best = int(np.argmin(costs))
    best_gap, best_cost, best_mass0 = float(gaps[coarse_best]), float(costs[coarse_best]), float(best_masses0[coarse_best])
    costs_array = np.asarray(costs)
    gap_minima = [i for i in range(len(gaps))
                  if np.isfinite(costs_array[i])
                  and (i == 0 or costs_array[i] <= costs_array[i - 1])
                  and (i == len(gaps) - 1 or costs_array[i] <= costs_array[i + 1])]
    for index in gap_minima:
        if index == 0 or index == len(gaps) - 1:
            continue
        left, right = float(gaps[index - 1]), float(gaps[index + 1])
        if not left < right:
            continue

        def profiled_cost(gap):
            stop = hi - float(gap) - 1e-10
            masses0 = np.arange(lo + 1e-10, stop, mass_step)
            if not len(masses0):
                return np.inf
            return _profile_one_gap(model, mean, float(gap), masses0, whitener, weighted_mean)[0]

        result = minimize_scalar(profiled_cost, bounds=(left, right), method='bounded',
                                 options={'xatol': 1e-9})
        if result.success and np.isfinite(result.fun) and result.fun < best_cost:
            best_gap = float(result.x)
            best_cost = float(result.fun)
            stop = hi - best_gap - 1e-10
            masses0 = np.arange(lo + 1e-10, stop, mass_step)
            best_cost, best_mass0 = _profile_one_gap(
                model, mean, best_gap, masses0, whitener, weighted_mean,
            )
    return {
        'gaps': gaps.tolist(), 'profile_cost': costs,
        'profile_mass0': best_masses0,
        'refined_minimum': {'gap': best_gap, 'mass0': best_mass0, 'cost': best_cost},
        'mass_grid_step': float(mass_step),
        'gap_grid_step': float(GAP_STEP),
        'local_gap_refinement_step': float(LOCAL_GAP_STEP),
        'covariance_metric': 'same fixed shrinkage inverse covariance as TwoStateFit',
        'amplitude_solver': 'whitened least squares (SVD), with local bounded refinements in m0 and gap; includes the gap=0 rank-deficient boundary',
    }


def _load_pinned_data():
    receipt = audit()
    verified = receipt['verified_sha256']
    protocol_rel = str(PROTOCOL)
    protocol_bytes = (ROOT / PROTOCOL).read_bytes()
    if hashlib.sha256(protocol_bytes).hexdigest() != verified[protocol_rel]:
        raise ValueError('Protocol changed after the pinned archive audit')
    protocol = json.loads(protocol_bytes)

    measurement_rel = str(ARCHIVE / 'development.npz')
    measurement_bytes = (ROOT / ARCHIVE / 'development.npz').read_bytes()
    if hashlib.sha256(measurement_bytes).hexdigest() != verified[measurement_rel]:
        raise ValueError('D-development bytes changed after the pinned archive audit')
    with np.load(io.BytesIO(measurement_bytes), allow_pickle=False) as data:
        ids = np.asarray(data['ids'])
        raw = np.asarray(data['correlators'], dtype=float)
    if not np.array_equal(ids, np.arange(100)):
        raise ValueError('Only public D0-99 is allowed')
    if raw.shape != (100, len(protocol['powers']), protocol['geometry'][3]):
        raise ValueError('Unexpected D-development correlator shape')
    if not np.isfinite(raw).all():
        raise ValueError('Nonfinite D-development correlator')
    data_blocks = blocks(fold(raw), protocol['block_length'])

    bootstrap_rel = str(ARCHIVE / 'two_state_bootstrap.npz')
    bootstrap_bytes = (ROOT / ARCHIVE / 'two_state_bootstrap.npz').read_bytes()
    if hashlib.sha256(bootstrap_bytes).hexdigest() != verified[bootstrap_rel]:
        raise ValueError('Two-state bootstrap bytes changed after the pinned archive audit')
    with np.load(io.BytesIO(bootstrap_bytes), allow_pickle=False) as data:
        windows = json.loads(str(data['windows']))
        masses = np.asarray(data['masses'], dtype=float)
    return protocol, data_blocks, windows, masses, receipt


def run(output=None):
    output = ROOT / (Path(output) if output is not None else OUTPUT)
    if output.exists():
        raise FileExistsError(f'refusing to overwrite diagnostic output: {output}')
    protocol, data_blocks, windows, bootstrap_masses, audit_receipt = _load_pinned_data()
    if windows != protocol['reference_windows'] or bootstrap_masses.shape != (len(windows), 1000, 2):
        raise ValueError('Unexpected pinned two-state bootstrap layout')

    lo, hi = map(float, protocol['mass_bounds'])
    base_gaps = np.linspace(0.0, min(1.5, hi - lo - 0.01),
                            int(round(min(1.5, hi - lo - 0.01) / GAP_STEP)) + 1)
    rows = []
    figure, axes = plt.subplots(1, len(windows), figsize=(15, 4.8), constrained_layout=True)
    for i, window in enumerate(windows):
        model = TwoStateFit(data_blocks, protocol, window)
        mean = model.samples.mean(axis=0)
        full = model.fit_full(mean)
        local_low = max(0.0, full['gap'] - LOCAL_GAP_HALF_WIDTH)
        local_high = min(1.5, full['gap'] + LOCAL_GAP_HALF_WIDTH)
        local_gaps = np.arange(local_low, local_high + LOCAL_GAP_STEP / 2, LOCAL_GAP_STEP)
        gaps = np.unique(np.concatenate((base_gaps, local_gaps, [full['gap']])))
        profile = profile_gap_curve(model, mean, gaps)
        costs = np.asarray(profile['profile_cost'])
        refined = profile['refined_minimum']
        delta = np.maximum(0.0, costs - float(refined['cost']))
        profile_design = model.design(refined['mass0'], refined['mass0'] + refined['gap'])
        profile_normal_matrix = profile_design.T @ model.inv @ profile_design
        profile_condition = float(np.linalg.cond(profile_normal_matrix))
        precision = 0.5 * (model.inv + model.inv.T)
        whitener = np.linalg.cholesky(precision).T
        stable_existing_cost = _cost_at_m0(
            model, mean, full['gap'], full['mass'], whitener, whitener @ mean,
        )
        bootstrap_gap = bootstrap_masses[i, :, 1] - bootstrap_masses[i, :, 0]
        finite_gap = bootstrap_gap[np.isfinite(bootstrap_gap)]
        gap_quantiles = np.quantile(finite_gap, [0.025, 0.5, 0.975]).tolist()
        rows.append({
            'window': window,
            'fit_full_sample': {
                'mass0': full['mass'], 'mass1': full['mass2'], 'gap': full['gap'],
                'cost': full['cost'], 'amplitude_condition': full['condition'],
                'at_boundary': full['at_boundary'],
            },
            'profile_grid': {
                'best_found_gap': refined['gap'],
                'best_found_mass0': refined['mass0'],
                'best_found_cost': refined['cost'],
                'profile_amplitude_condition': profile_condition,
                'stable_cost_at_existing_fit': stable_existing_cost,
                'stable_objective_improvement_vs_existing': stable_existing_cost - refined['cost'],
                'delta_cost_at_gap_zero': float(costs[0] - refined['cost']),
                'mass_grid_step': profile['mass_grid_step'],
                'gap_grid_step': profile['gap_grid_step'],
                'local_gap_refinement_step': profile['local_gap_refinement_step'],
            },
            'existing_constrained_bootstrap_gap_quantiles_2p5_50_97p5': gap_quantiles,
            'existing_bootstrap_draw_count': int(len(finite_gap)),
            'interpretation': (
                'Gap draws are from the ordered two-state search (m0 < m1) and cannot by themselves '
                'establish that two states are resolved. Profile objective differences are uncalibrated '
                'descriptive diagnostics, not likelihood-ratio significance or physical coverage.'
            ),
        })

        ax = axes[i]
        ax.plot(gaps, delta, color='#155e75', lw=1.8)
        ax.axvline(0.0, color='#b91c1c', ls='--', lw=1.2, label='gap = 0 (one-state boundary)')
        ax.axvline(refined['gap'], color='#15803d', ls=':', lw=1.5,
                   label=f'best profile point {refined["gap"]:.3f}')
        ax.axvline(full['gap'], color='#7c3aed', ls='-.', lw=1.2,
                   label=f'existing fit {full["gap"]:.3f}')
        ax.set_title(
            f'window {window}\ncond(existing/profile)={full["condition"]:.2g}/{profile_condition:.2g}'
        )
        ax.set_xlabel(r'fixed mass gap $m_1-m_0$')
        ax.grid(alpha=.25)
        ax.set_yscale('symlog', linthresh=0.1)
        ax.set_ylim(bottom=0)
        if i == 0:
            ax.set_ylabel(r'profiled $\Delta$ objective (not a calibrated LR test)')
        ax.legend(fontsize=7, frameon=False)

    figure.suptitle('D0–99 feasibility only: two-state gap profile under a fixed covariance metric')
    image_path = output / 'two_state_gap_profile.png'
    # Output is new and isolated; create the directory only after all pinned
    # inputs and profile calculations have passed.
    output.mkdir(parents=True, exist_ok=False)
    figure.savefig(image_path, dpi=180)
    plt.close(figure)

    summary = {
        'schema': 'pion-two-state-gap-profile-feasibility-v1',
        'status': 'DEVELOPMENT_DIAGNOSTIC_ONLY',
        'physical_score': None,
        'scope': 'public D0-99 only; no E, gap, validation, embargo, or shared holdout access',
        'bootstrap_audit_status': audit_receipt['status'],
        'protocol_sha256': audit_receipt['verified_sha256'][str(PROTOCOL)],
        'verified_input_sha256': audit_receipt['verified_sha256'],
        'profile': {
            'coarse_gap_step': GAP_STEP, 'local_gap_step': LOCAL_GAP_STEP,
            'local_gap_half_width_around_existing_fit': LOCAL_GAP_HALF_WIDTH,
            'mass_grid_step': MASS_STEP,
            'objective': 'fixed shrinkage-inverse-covariance quadratic with amplitudes profiled by whitened SVD least squares',
            'reference_optimizer': 'existing ordered grid/coordinate-search result is reported separately; the diagnostic scans the stated grids and refines sampled local minima, but does not certify a global minimum',
            'limitation': 'uncalibrated profile differences and ordered bootstrap gap quantiles do not establish a physically resolved excited state',
        },
        'windows': rows,
        'plot': image_path.name,
        'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'numpy_version': np.__version__,
    }
    summary_path = output / 'summary.json'
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    lines = [
        '# Two-state gap-profile feasibility on D development', '',
        '**Status: development-only numerical diagnostic.** The frozen single-cosh gate remains failed; this report does not authorize E measurement, validation, shared-holdout access, or physical scoring.', '',
        'The plot profiles the existing fixed shrinkage-covariance quadratic over a fixed mass gap, solving channel amplitudes by whitened SVD least squares. A 0.01 coarse mass0 scan locates sampled basins, bounded scalar searches refine each sampled local minimum, and the gap scan adds a 0.003 grid around the existing fitted gap before local refinement. Gap zero is included as the one-state boundary. The reported curve is an uncalibrated objective difference, not a likelihood-ratio p-value or a coverage statement.', '',
        'The existing bootstrap mass pairs were generated by an optimizer that enforces `m0 < m1`. Their positive gap quantiles are therefore partly a consequence of the parameterization; they cannot alone show that the two states are identified. The gap profile is added as a separate numerical check, while the late-window bound and condition warnings remain in force.', '',
        f'Pinned input audit: `{audit_receipt["status"]}`; public D configurations 0–99; {len(data_blocks)} complete blocks of length {protocol["block_length"]}.', '',
        '![D-only profiled objective versus fixed mass gap](two_state_gap_profile.png)', '',
        '| Window | Existing fit gap | Best found profile gap | Δ objective at gap 0 | Condition (existing / best point) | Objective improvement vs existing | Constrained bootstrap gap q2.5/50/97.5 |',
        '|---|---:|---:|---:|---:|---:|---:|',
    ]
    for row in rows:
        q = row['existing_constrained_bootstrap_gap_quantiles_2p5_50_97p5']
        lines.append(
            f"| {row['window']} | {row['fit_full_sample']['gap']:.4g} | "
            f"{row['profile_grid']['best_found_gap']:.4g} | "
            f"{row['profile_grid']['delta_cost_at_gap_zero']:.4g} | "
            f"{row['fit_full_sample']['amplitude_condition']:.4g} / {row['profile_grid']['profile_amplitude_condition']:.4g} | "
            f"{row['profile_grid']['stable_objective_improvement_vs_existing']:.4g} | "
            f"{q[0]:.4g} / {q[1]:.4g} / {q[2]:.4g} |"
        )
    improvements = ', '.join(
        f"{row['profile_grid']['stable_objective_improvement_vs_existing']:.4g}"
        for row in rows
    )
    lines += [
        '', '## Interpretation boundary', '',
        '- D was used to choose and screen this diagnostic; results are not independent confirmation.',
        '- The gap quantiles inherit the ordered two-state constraint and the optimizer grid/refinement. They are not evidence of physical excitation-state identification.',
        f'- The best point found is below the existing coordinate-search objective by {improvements} for the three windows; stable evaluation at the old fit reproduces its reported cost to rounding. This exposes optimizer-path dependence in the existing diagnostic, not a physical effect. The local scan does not certify a global minimum.',
        '- The profile uses a fixed estimated covariance, bounded local refinement, and a discrete starting grid. Its raw objective difference has no calibrated null distribution; no significance threshold is applied.',
        '- The late `[6,7,8]` window still has condition number above the proposed `1e5` screen and two existing bootstrap upper-bound hits. This report does not waive those failures.',
        '- The result may inform a redesigned, pre-E confirmation plan, but any primary-window choice and adequacy rule must be justified and frozen before E is read. A plan revision requires review; do not tune until D passes.',
        '- No production score or measurement authorization is created. `physical_score=null` remains in force.', '',
    ]
    report_path = output / 'README.md'
    report_path.write_text('\n'.join(lines))
    provenance = {
        'schema': 'pion-two-state-gap-profile-provenance-v1',
        'summary_sha256': hashlib.sha256(summary_path.read_bytes()).hexdigest(),
        'report_sha256': hashlib.sha256(report_path.read_bytes()).hexdigest(),
        'plot_sha256': hashlib.sha256(image_path.read_bytes()).hexdigest(),
        'source_sha256': summary['source_sha256'],
        'verified_input_sha256': summary['verified_input_sha256'],
        'scope': summary['scope'],
    }
    (output / 'provenance.json').write_text(json.dumps(provenance, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': summary['status'], 'output': str(output),
                      'windows': rows}, indent=2))
    return summary


if __name__ == '__main__':
    run()
