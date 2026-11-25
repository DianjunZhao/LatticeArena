"""Development-only optimization followed by frozen held-out evaluation."""
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from core.candidates import validate_weights
from core.source_integrity import SourceByteSnapshot

from .common import digest, fingerprint, load_data, protocol, write_json
from .statistics import (ReferenceFit, blocks, bootstrap_indices, fold, inverse_covariance, risk)
from .spec import bundle_for


def late_metric(data, weights, p):
    return inverse_covariance(np.einsum('nbt,b->nt', data, weights)[:, p['amplitude_window']],
                              p['covariance_shrinkage'])


def optimize_mixture(data, scales, m, mb, index, p):
    normalized = data/scales[None, :, None]

    def objective(u):
        try:
            return risk(normalized, u, m, mb, index, p)['risk'] + p['optimizer_ridge']*float(u @ u)
        except (ValueError, np.linalg.LinAlgError, FloatingPointError):
            return 1e10

    basis = np.eye(len(scales))
    starts = [*basis, np.ones(len(basis))/len(basis)]
    outcomes = []
    evaluations = 0
    for start in starts[:p['optimizer_starts']]:
        fit = minimize(objective, start, method='SLSQP', bounds=[(-p['optimizer_l1_bound'], p['optimizer_l1_bound'])]*len(basis),
                       constraints=[{'type': 'eq', 'fun': lambda u: u.sum()-1},
                                    {'type': 'ineq', 'fun': lambda u: p['optimizer_l1_bound']-abs(u).sum()}],
                       options={'maxiter': p['optimizer_max_iterations'], 'ftol': 1e-11})
        evaluations += int(fit.nfev)
        feasible, _ = validate_weights(fit.x, len(basis), p['optimizer_l1_bound'])
        if fit.success and feasible and fit.fun < 1e9:
            outcomes.append(fit)
    if not outcomes:
        raise ValueError('No optimizer start converged to a valid candidate')
    fit = min(outcomes, key=lambda f: f.fun)
    return fit, len(outcomes), evaluations


def develop(output, *, source_snapshot=None, source_names=None):
    output = Path(output)
    if source_snapshot is not None:
        if not isinstance(source_snapshot, SourceByteSnapshot):
            raise ValueError('source_snapshot must be a verified SourceByteSnapshot')
        if (not isinstance(source_names, dict)
                or set(source_names) != {
                    'development_provenance', 'development_measurements'
                }):
            raise ValueError(
                'source_names must map development_provenance and '
                'development_measurements only'
            )
        if output.exists():
            raise FileExistsError('snapshot development output must use a new directory')
        output_abs, snapshot_root = output.resolve(), Path(source_snapshot.root).resolve()
        if (output_abs == snapshot_root or output_abs in snapshot_root.parents
                or snapshot_root in output_abs.parents):
            raise ValueError('snapshot development output must be outside the source tree')
        captured_provenance = json.loads(
            source_snapshot.read_bytes(source_names['development_provenance'])
        )
        p = captured_provenance.get('protocol') if isinstance(captured_provenance, dict) else None
        if not isinstance(p, dict) or p != protocol():
            raise ValueError('captured development protocol differs from the checked-out protocol')
        measurement_bundle = bundle_for(
            source_snapshot=source_snapshot, source_names=source_names,
        )
        raw = measurement_bundle['arrays']['development']
        development_sha = measurement_bundle['manifest']['source_files'][
            'development_measurements'
        ]['sha256']
        source_hashes = {
            role: entry['sha256']
            for role, entry in measurement_bundle['manifest']['source_files'].items()
        }
        source_read_mode = 'immutable_snapshot'
    else:
        if source_names is not None:
            raise ValueError('source_names is only valid with source_snapshot')
        if (output / 'submission.json').exists() or (output / 'validation.npz').exists():
            raise ValueError('Development is closed for this run; use a new run and disclose prior validation access')
        p = protocol()
        raw = load_data(output, 'development')
        development_sha = digest(output / 'development.npz')
        source_hashes = {'development_measurements': development_sha}
        provenance = output / 'development_provenance.json'
        if provenance.is_file():
            source_hashes['development_provenance'] = digest(provenance)
        source_read_mode = 'path'

    data = blocks(fold(raw), p['block_length'])
    index = bootstrap_indices(len(data), p['bootstrap_samples'], p['seed'])
    windows, masses = [], []
    for window in p['reference_windows']:
        model = ReferenceFit(data, p, window)
        result, boot = model.bootstrap(index)
        windows.append(result)
        masses.append(boot)
    nominal = p['reference_nominal_window']
    reference = windows[nominal]
    m, mb = reference['mass'], masses[nominal]
    failures = []
    if reference['se']/m > p['reference_max_relative_error']:
        failures.append('Reference mass relative uncertainty exceeds 5%')
    if reference['p_approx'] < p['reference_min_fit_p']:
        failures.append('Nominal correlated reference fit fails the approximate goodness-of-fit gate')
    for j, window in enumerate(windows):
        if j != nominal:
            se = float((masses[j]-mb).std(ddof=1))
            z = abs(window['mass']-m)/se if se > 0 else 1e300
            window['paired_shift_z'] = z
            if z > p['reference_max_window_z']:
                failures.append(f'Reference window {window["window"]} shifts by {z:.2f} paired standard errors')
    if np.any(mb <= p['mass_bounds'][0]+1e-4) or np.any(mb >= p['mass_bounds'][1]-1e-4):
        failures.append('Reference bootstrap reaches mass bounds')
    odd = raw[..., 1:8]-raw[..., 15:8:-1]
    odd_blocks = blocks(odd, p['block_length'])
    odd_se = odd_blocks.std(axis=0, ddof=1)/np.sqrt(len(odd_blocks))
    reflection_z = float(np.max(abs(odd_blocks.mean(axis=0))/odd_se))
    if reflection_z > p['reflection_max_z']:
        failures.append('Forward/backward symmetry check exceeds the fixed z threshold')
    sensitivity = {}
    for length in [1, 2, 3, 5]:
        bs = blocks(fold(raw), length)
        sensitivity[str(length)] = (bs.std(axis=0, ddof=1)/np.sqrt(len(bs)))[:, 6].tolist()
    calibration = {'reference': reference, 'windows': windows, 'reference_passed': not failures,
                   'failure_reasons': failures, 'reflection_max_z': reflection_z,
                   'block_length_sensitivity_C6_se': sensitivity,
                   'independence_status': 'Trajectory spacing unknown; five-configuration blocks are a conservative pilot choice, not established decorrelation.',
                   'n_development_blocks': len(data)}
    print('CALIBRATION', json.dumps(calibration), flush=True)
    basis = np.eye(len(p['powers']))
    baseline_results = [risk(data, w, m, mb, index, p) for w in basis]
    best = min(range(len(basis)), key=lambda j: baseline_results[j]['risk'])
    scales = np.array([r['amplitude'] for r in baseline_results])
    fit, converged, _ = optimize_mixture(data, scales, m, mb, index, p)
    weights = fit.x/scales
    candidate_result = risk(data, weights, m, mb, index, p)
    submissions = {'local': basis[0].tolist(), 'tuned_gaussian': basis[best].tolist(),
                   'agent_signed_mixture': weights.tolist()}
    metrics = {name: late_metric(data, w, p).tolist() for name, w in submissions.items()}
    frozen = {'protocol_hash': fingerprint(p), 'development_sha256': development_sha,
              'statistics_sha256': digest(Path(__file__).with_name('statistics.py')),
              'kernel_sha256': digest(Path(__file__).with_name('kernels.py')),
              'development_source_read_mode': source_read_mode,
              'development_source_hashes': source_hashes,
              'powers': p['powers'], 'alpha': p['alpha'], 'submissions': submissions,
              'normalized_mixture_weights': fit.x.tolist(), 'basis_amplitude_scales': scales.tolist(),
              'late_inverse_covariances': metrics, 'selected_gaussian_power': p['powers'][best],
              'optimizer': {'converged_starts': converged, 'objective': float(fit.fun),
                            'iterations': int(fit.nit), 'l1': float(abs(fit.x).sum())},
              'calibration': calibration}
    if source_snapshot is not None:
        output.mkdir(parents=True, exist_ok=False)
    write_json(output/'development_results.json', {'basis': baseline_results, 'agent': candidate_result})
    write_json(output/'submission.json', frozen)
    np.savez_compressed(output/'reference_bootstrap.npz', masses=mb, indices=index)
    print('FROZEN_SUBMISSION', json.dumps(frozen), flush=True)


def nested_intervals(development, validation, frozen, p):
    """Resample the entire conditional risk statistic, including its variance.

    Fit metrics are frozen at development, not re-estimated on validation or
    inside resamples. Shared reference and paired validation draws preserve
    correlations between all candidates. No replicate is silently discarded.
    """
    rng = np.random.default_rng(p['seed']+2)
    model = ReferenceFit(development, p, p['reference_windows'][p['reference_nominal_window']])
    names = list(frozen['submissions'])
    draws = []
    for outer in range(p['outer_samples']):
        rd = rng.integers(0, len(development), len(development))
        rv = rng.integers(0, len(validation), len(validation))
        ref_samples = model.samples[rd]
        mass = model.fit(ref_samples.mean(axis=0))[0]
        di = rng.integers(0, len(development), (p['inner_samples'], len(development)))
        vi = rng.integers(0, len(validation), (p['inner_samples'], len(validation)))
        masses = np.array([model.fit(mean)[0] for mean in ref_samples[di].mean(axis=1)])
        losses = []
        for name in names:
            value = risk(validation[rv], frozen['submissions'][name], mass, masses, vi, p,
                         require_valid=False, late_inverse=np.array(frozen['late_inverse_covariances'][name]))
            losses.append(value['risk'])
        draws.append(losses)
        if (outer+1) % 50 == 0:
            print(f'Nested bootstrap {outer+1}/{p["outer_samples"]}', flush=True)
    return np.asarray(draws), names


def pion_mass_check(val, weights, ref_mass, ref_draws, val_indices, p, calibration):
    """Fit a free sink mass on validation and compare it to the development target."""
    reasons = list(calibration['failure_reasons'])
    if not calibration['reference_passed'] and not reasons:
        reasons.append('Development reference failed')
    # Resampling is paired across validation windows. Development and validation
    # indices are drawn independently, as in the conditional risk calculation.
    nominal = p['reference_windows'][p['reference_nominal_window']]
    windows = [nominal, *(w for w in p['reference_windows'] if w[0] > nominal[0])]
    results = []
    central = None
    def check_shift(label, difference, draws):
        error = float(draws.std(ddof=1))
        if abs(difference) > p['reference_max_window_z'] * error:
            reasons.append(label)
        return {'mass_difference': difference, 'bootstrap_se': error}

    try:
        channel = np.einsum('nbt,b->nt', val, weights)[:, None, :]
        for window in windows:
            fit = ReferenceFit(channel, dict(p, reference_basis=[0]), window)
            item, draws = fit.bootstrap(val_indices)
            results.append(item)
            lo, hi = p['mass_bounds']
            if (not np.isfinite(item['p_approx']) or item['p_approx'] < p['reference_min_fit_p']
                    or item['se'] > item['mass'] * p['reference_max_relative_error']
                    or np.any(draws <= lo + 1e-4) or np.any(draws >= hi - 1e-4)):
                reasons.append(f'Free-mass fit unresolved on {window}')
            item['vs_reference'] = check_shift(f'Free mass disagrees with development reference on {window}',
                                               item['mass'] - ref_mass, draws - ref_draws)
            if central is None:
                central = item['mass'], draws
            else:
                item['vs_nominal'] = check_shift(f'Free mass changes with fit window {window}',
                                                 item['mass'] - central[0], draws - central[1])
    except (ValueError, np.linalg.LinAlgError) as exc:
        reasons.append(f'Free-mass fit failed: {exc}')
    return {'status': 'unresolved' if reasons else 'consistent_with_reference',
            'development_reference_mass': ref_mass, 'fits': results, 'reasons': reasons}


def evaluate(output):
    output = Path(output)
    p = protocol()
    frozen = json.loads((output/'submission.json').read_text())
    if frozen.get('development_source_read_mode') == 'immutable_snapshot' and not (output/'development.npz').is_file():
        raise ValueError(
            'Snapshot-only development has no colocated NPZ for validation evaluation; '
            'supply an explicitly authorized, hash-matching development/validation transaction'
        )
    if frozen['protocol_hash'] != fingerprint(p) or frozen['development_sha256'] != digest(output/'development.npz'):
        raise ValueError('Frozen protocol or development data changed')
    if frozen['statistics_sha256'] != digest(Path(__file__).with_name('statistics.py')) or frozen['kernel_sha256'] != digest(Path(__file__).with_name('kernels.py')):
        raise ValueError('Frozen scoring/kernel implementation changed')
    dev = blocks(fold(load_data(output, 'development')), p['block_length'])
    raw = load_data(output, 'validation')
    val = blocks(fold(raw), p['block_length'])
    model = ReferenceFit(dev, p, p['reference_windows'][p['reference_nominal_window']])
    reference, mb = model.bootstrap(bootstrap_indices(len(dev), p['bootstrap_samples'], p['seed']))
    vi = bootstrap_indices(len(val), p['bootstrap_samples'], p['seed']+1)
    report = {'protocol': p, 'submission_sha256': digest(output/'submission.json'),
              'validation_sha256': digest(output/'validation.npz'), 'reference': reference,
              'reference_passed': frozen['calibration']['reference_passed'],
              'reference_failure_reasons': frozen['calibration']['failure_reasons'],
              'n_validation_configurations': len(raw), 'n_validation_blocks': len(val),
              'results': {}, 'score_status': 'pilot_only' if frozen['calibration']['reference_passed'] else 'unscored_reference_failed'}
    for name, weights in frozen['submissions'].items():
        try:
            report['results'][name] = risk(val, weights, reference['mass'], mb, vi, p,
                                           late_inverse=np.array(frozen['late_inverse_covariances'][name]))
        except ValueError as exc:
            report['results'][name] = {'invalid_reason': str(exc), 'score': None}
    valid = all('risk' in value for value in report['results'].values())
    if valid:
        eps = p['score_epsilon']
        baseline = report['results']['local']['risk']
        for name, value in report['results'].items():
            state = pion_mass_check(val, frozen['submissions'][name], reference['mass'], mb, vi, p, frozen['calibration'])
            value['pion_mass_check'] = state
            value['diagnostic_loss_ratio_vs_local'] = (baseline+eps)/(value['risk']+eps)
            value['score'] = 100*value['diagnostic_loss_ratio_vs_local'] if state['status'] == 'consistent_with_reference' else None
        draws, names = nested_intervals(dev, val, frozen, p)
        np.savez_compressed(output/'nested_bootstrap.npz', risks=draws, names=np.array(names))
        for j, name in enumerate(names):
            ratios = (draws[:, 0]+eps)/(draws[:, j]+eps)
            report['results'][name]['diagnostic_loss_ratio_95_interval'] = np.quantile(ratios, [.025, .975]).tolist()
            report['results'][name]['risk_95_interval'] = np.quantile(draws[:, j], [.025, .975]).tolist()
        j, k = names.index('agent_signed_mixture'), names.index('tuned_gaussian')
        report['agent_vs_tuned_gaussian'] = {
            'risk_ratio': report['results']['tuned_gaussian']['risk']/report['results']['agent_signed_mixture']['risk'],
            'risk_ratio_95_interval': np.quantile((draws[:, k]+eps)/(draws[:, j]+eps), [.025, .975]).tolist()}
    write_json(output/'validation_results.json', report)
    print('VALIDATION', json.dumps(report), flush=True)
