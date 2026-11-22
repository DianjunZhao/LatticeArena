"""v6: A1+ (cubically symmetric) learned smear.

a_mu(x) = c + sum_h v_h phi_h(mu, x),  phi shared across directions, zero mean over sites
phi_h(mu, x) = tanh(W_h . (P_{mu nu}(x), P_{mu rho}(x)))  -- the two plaquettes containing mu
K = C_hop(a) G^m,  b_mu(x) = a_mu(x - mu)
"""
import argparse
import json
import os
from pathlib import Path
import tempfile
import time

import numpy as np
from scipy.optimize import minimize

from tasks.pion_projection.common import digest, fingerprint
from tasks.pion_projection.statistics import blocks, bootstrap_indices, risk

from .features import FEATURE_VERSION, _lib, directional_features
from .kernels import apply_kernel, correlator
from .artifacts import prepare_output_directory
from .solver_contract import (
    SolverContractBudgetStop,
    SolverPolicy,
    run_solver_with_contract,
    solver_policy_from_mapping,
)


def protocol(path=None, expected_sha256=None):
    """Load the bundled protocol or a caller-frozen protocol file.

    Worker-launched runs pass both an explicit path and its RunSpec-bound
    SHA-256. The child rechecks the bytes immediately before parsing to close
    the gap between parent preflight and training startup.
    """
    protocol_path = Path(path) if path is not None else Path(__file__).parent / 'protocol.json'
    if expected_sha256 is not None:
        actual = digest(protocol_path)
        if actual != expected_sha256:
            raise ValueError(
                f'protocol SHA-256 mismatch: expected {expected_sha256}, got {actual}')
    payload = json.loads(protocol_path.read_text())
    if not isinstance(payload, dict):
        raise ValueError('Optimize protocol root must be a JSON object')
    return payload


def solver_policy_from_protocol(p, *, required=False):
    """Build the explicit production solver policy, with no hidden defaults."""
    optimizer = p.get('optimizer')
    if not isinstance(optimizer, dict):
        raise ValueError('protocol.optimizer must be an object')
    specification = optimizer.get('solver_contract')
    if specification is None:
        if required:
            raise ValueError('explicit Optimize protocols must define optimizer.solver_contract')
        return None
    try:
        policy = solver_policy_from_mapping(specification)
    except ValueError as exc:
        raise ValueError(f'invalid protocol.optimizer.solver_contract: {exc}') from exc
    if policy.residual_field != 'kkt_residual':
        raise ValueError('Optimize solver contract residual_field must be "kkt_residual"')
    return policy


class SolverContractRejected(RuntimeError):
    """A fit rejected by its explicitly frozen solver policy."""

    def __init__(self, receipt):
        self.receipt = receipt
        super().__init__('Optimize solver contract rejected candidate: '
                         + ', '.join(receipt.get('rejection_reasons', [])))


def init_quda(p):
    import cupy as cp  # noqa: F401
    from pyquda_utils import core
    if not getattr(init_quda, 'done', False):
        core.init([1, 1, 1, 1], p['geometry'], resource_path='.cache/quda')
        init_quda.done = True


def model_space(p, seed):
    rng = np.random.default_rng(seed)
    return rng.normal(size=(p['hidden'], 2)) * 0.5


def _input_summary(p, ids, cache):
    try:
        detail = validate_inputs(p, ids, cache)
    except ValueError as exc:
        return {'status': 'rejected', 'detail': str(exc)}
    statuses = [row['status'] for row in detail.values()]
    if statuses and all(status == 'verified' for status in statuses):
        status = 'verified'
    elif any(status == 'verified' for status in statuses):
        status = 'archived_diagnostic'
    else:
        status = 'unknown'
    return {'status': status, 'detail': detail}


def run_manifest(p, W, theta, fit_ids, devval_ids, test_ids, cache):
    here = Path(__file__).parent
    return {'schema': 'optgauss-run-v1', 'protocol': p, 'protocol_fingerprint': fingerprint(p),
            'features': FEATURE_VERSION, 'geometry': p['geometry'],
            'base_steps': p['base_steps'], 'base_alpha': p['base_alpha'],
            'W': np.asarray(W).tolist(), 'theta': [float(x) for x in np.asarray(theta).ravel()],
            'ids': {'fit': list(fit_ids), 'dev_val': list(devval_ids), 'test': list(test_ids)},
            'propagator_cache': {str(i): cache[i] for i in fit_ids + devval_ids + test_ids},
            'dependencies': {name: digest(here / name) for name in
                             ('features.py', 'kernels.py', 'submission.py', 'solver_contract.py', 'train.py')},
            'statistics_sha256': digest(here.parent / 'pion_projection' / 'statistics.py'),
            'inputs': _input_summary(p, list(fit_ids) + list(devval_ids) + list(test_ids), cache),
            'environment': {'software': 'unknown', 'hardware': 'unknown', 'timing': 'unknown'},
            'reference': reference_identity(p, fit_ids, cache)}


def _pion_propagator_receipt_rows(p):
    """Load a generation-bound Pion measurement receipt, when explicitly frozen.

    Pion's propagator cache metadata records input identity but not inversion
    residuals. A new Optimize protocol may bind the Pion development NPZ and
    provenance hashes and use its per-configuration residual receipt.
    """
    spec = p.get('propagator_measurement_receipt')
    if spec is None:
        return {}
    required = ('measurement_path', 'measurement_sha256', 'provenance_path',
                'provenance_sha256', 'generation', 'protocol_hash')
    missing = [name for name in required if not spec.get(name)]
    if missing:
        raise ValueError(f'propagator measurement receipt is missing {missing}')
    measurement_path = Path(spec['measurement_path'])
    provenance_path = Path(spec['provenance_path'])
    if digest(measurement_path) != spec['measurement_sha256']:
        raise ValueError('Pion measurement NPZ hash differs from Optimize protocol')
    if digest(provenance_path) != spec['provenance_sha256']:
        raise ValueError('Pion measurement provenance hash differs from Optimize protocol')
    with np.load(measurement_path, allow_pickle=False) as saved:
        if str(saved['generation']) != spec['generation']:
            raise ValueError('Pion measurement generation differs from Optimize protocol')
        if str(saved['protocol_hash']) != spec['protocol_hash']:
            raise ValueError('Pion measurement protocol hash differs from Optimize protocol')
        ids = np.asarray(saved['ids'], dtype=int).tolist()
    provenance = json.loads(provenance_path.read_text())
    if (provenance.get('generation') != spec['generation']
            or provenance.get('protocol_hash') != spec['protocol_hash']):
        raise ValueError('Pion measurement provenance identity differs from Optimize protocol')
    rows = provenance.get('records')
    if not isinstance(rows, list) or [row.get('id') for row in rows] != ids:
        raise ValueError('Pion measurement provenance IDs differ from the measurement NPZ')
    by_id = {int(row['id']): row for row in rows}
    if len(by_id) != len(rows):
        raise ValueError('Pion measurement provenance repeats a configuration ID')
    required_row_fields = ('cache_key', 'gauge_sha256', 'propagator_sha256',
                           'residual_max', 'trajectory_id')
    for cfg_id, row in by_id.items():
        missing = [name for name in required_row_fields if row.get(name) is None]
        if missing:
            raise ValueError(f'Pion measurement provenance cfg {cfg_id} is missing {missing}')
        try:
            residual = float(row['residual_max'])
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f'Pion measurement provenance cfg {cfg_id} has an invalid residual'
            ) from exc
        if not np.isfinite(residual) or residual < 0:
            raise ValueError(
                f'Pion measurement provenance cfg {cfg_id} has an invalid residual'
            )
    return by_id


def validate_inputs(p, ids, cache, trusted=True):
    """Check gauge/propagator content, metadata and inversion residual.

    Returns per-id status: verified only when the gauge digest, the propagator
    digest and the residual all match; missing metadata is archived_diagnostic;
    a mismatch is a hard refusal for the trusted entry.
    """
    rows = {}
    receipt_rows = _pion_propagator_receipt_rows(p)
    if not p.get('ensemble'):
        return {str(i): {'gauge': None, 'propagator': None, 'residual': None,
                         'status': 'unknown'} for i in ids}
    for i in ids:
        gauge = Path(f"{p['ensemble']}/wilson_b6.{i}")
        prop = Path('.cache/pion_projection/propagators') / f'{cache[i]}.npy'
        meta_path = prop.with_suffix('.json')
        row = {'gauge': None, 'propagator': None, 'residual': None, 'status': 'unknown'}
        receipt = receipt_rows.get(i)
        if p.get('propagator_measurement_receipt') is not None and receipt is None:
            raise ValueError(f'cfg {i}: missing from the bound Pion measurement receipt')
        if gauge.exists() and prop.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text())
            keydata = meta.get('keydata', {})
            gauge_sha = digest(gauge)
            propagator_sha = digest(prop)
            if receipt is not None:
                if receipt.get('cache_key') != cache[i]:
                    raise ValueError(f'cfg {i}: Pion receipt cache key differs from Optimize cache map')
                if receipt.get('gauge_sha256') != gauge_sha:
                    raise ValueError(f'cfg {i}: Pion receipt gauge hash differs from the gauge file')
                if receipt.get('propagator_sha256') != propagator_sha:
                    raise ValueError(f'cfg {i}: Pion receipt propagator hash differs from the cache file')
                row['trajectory_id'] = receipt.get('trajectory_id')
            row['gauge'] = keydata.get('gauge') == gauge_sha
            row['propagator'] = meta.get('array_sha256') == propagator_sha
            row['residual'] = (keydata.get('residual_max', meta.get('residual_max'))
                               if receipt is None else receipt.get('residual_max'))
            row['precision'] = np.load(prop, mmap_mode='r').dtype == np.complex128
            comparisons = {
                'geometry': (keydata.get('geometry'), p.get('geometry')),
                'boundary': (keydata.get('boundary'), p.get('t_boundary')),
                'tolerance': (keydata.get('tol'), p.get('tolerance')),
                'max_iterations': (keydata.get('maxiter'), p.get('max_iterations')),
            }
            if p.get('kappa') is not None:
                comparisons['kappa'] = (keydata.get('kappa'), p['kappa'])
            if p.get('source') is not None:
                comparisons['source'] = (keydata.get('source'), p['source'])
            mismatched = []
            for name, (actual, expected) in comparisons.items():
                if actual is not None and expected is not None and actual != expected:
                    mismatched.append(name)
                row[name] = (actual == expected) if (actual is not None and expected is not None) else None
            if not (row['gauge'] and row['propagator']):
                raise ValueError(f'cfg {i}: gauge/propagator metadata does not match the files')
            if mismatched:
                raise ValueError(f'cfg {i}: protocol mismatch in {mismatched}')
            tolerance = p.get('tolerance', 1e-10)
            residual_ok = row['residual'] is not None and row['residual'] <= tolerance
            if trusted and row['residual'] is not None and not residual_ok:
                raise ValueError(f'cfg {i}: inversion residual {row["residual"]:.3e} exceeds '
                                 f'tolerance {tolerance:.0e} at the trusted entry')
            complete = all(row[name] is True for name in
                           ('geometry', 'boundary', 'tolerance', 'max_iterations'))
            if p.get('kappa') is not None:
                complete = complete and row.get('kappa') is True
            if p.get('source') is not None:
                complete = complete and row.get('source') is True
            row['status'] = ('verified' if complete and residual_ok and row['precision']
                             else 'archived_diagnostic')
        rows[str(i)] = row
    return rows


def reference_identity(p, fit_ids, cache):
    """Digest the reference/bootstrap files actually consumed, not a default neighbour."""
    out = {'model': 'single-cosh', 'source_split': 'development'}
    consumed = []
    for key in ('reference_bootstrap', 'reference_path'):
        if p.get(key):
            path = Path(p[key])
            out[key] = str(path)
            out[f'{key}_digest'] = digest(path) if path.exists() else None
            consumed.append(key)
    out['consumed'] = consumed
    out['status'] = 'verified' if consumed and all(out.get(f'{key}_digest') for key in consumed)         else 'unknown'
    return out


def input_digests(p, ids, cache):
    """Content hashes of the gauge files and propagators a basis is built from."""
    return {'gauge': {str(i): digest(f"{p['ensemble']}/wilson_b6.{i}") for i in ids},
            'propagator': {str(i): digest(f".cache/pion_projection/propagators/{cache[i]}.npy")
                           for i in ids}}


def basis_key(p, seed, W, fit_ids, dev_ids, cache=None, inputs=None, dependencies=None):
    here = Path(__file__).parent
    key = {'protocol': fingerprint(p), 'seed': seed, 'W': np.asarray(W).tolist(),
           'steps': p['base_steps'], 'alpha': p['base_alpha'], 'hidden': p['hidden'],
           'fit_ids': list(fit_ids), 'dev_val_ids': list(dev_ids),
           'features': FEATURE_VERSION,
           'dependencies': dependencies if dependencies is not None else
           {name: digest(here / name) for name in
            ('features.py', 'kernels.py', 'submission.py', 'train.py')},
           'statistics': digest(here.parent / 'pion_projection' / 'statistics.py')}
    if inputs is not None:
        key['inputs'] = inputs
    elif cache is not None:
        key['inputs'] = input_digests(p, list(fit_ids) + list(dev_ids), cache)
    return key


def save_basis(path, key, C_fit, C_dev):
    np.savez_compressed(path, C_fit=C_fit, C_dev=C_dev, meta=np.array(json.dumps(key)))


def load_basis(path, key):
    z = np.load(path)
    if 'meta' not in z:
        raise ValueError(f'Cached basis at {path} has no identity record; use a new output directory')
    meta = json.loads(str(z['meta']))
    if meta != key:
        raise ValueError(f'Cached basis at {path} does not match this protocol/W/IDs; use a new output directory')
    return z['C_fit'], z['C_dev']


def gaussian(field, links, steps, a0):
    xp = _lib(field)
    a = xp.full((3, *field.shape[:3]), a0)
    for _ in range(steps):
        field = apply_kernel(field, links, a)
    return field


def features(links, W):
    xp = _lib(links)
    f = directional_features(links)
    W = xp.asarray(W)
    phi = xp.stack([xp.tanh(f[mu] @ W.T) for mu in range(3)], axis=0)
    return phi - phi.mean(axis=(1, 2, 3), keepdims=True)


def collect(p, ids, cache, W, steps):
    import cupy as cp
    from pyquda_utils import core, io

    init_quda(p)
    latt = core.LatticeInfo(p['geometry'], -1, 1.0)
    H, nb = p['hidden'], 2 + p['hidden']
    C = np.zeros((len(ids), nb, 16))
    for i, cfg in enumerate(ids):
        gauge = io.readNERSCGauge(f"{p['ensemble']}/wilson_b6.{cfg}")
        links = cp.asarray(gauge.lexico())[:3]
        prop = core.LatticePropagator(
            latt, cp.asarray(np.load(f".cache/pion_projection/propagators/{cache[cfg]}.npy")))
        fields = cp.asarray(prop.lexico())
        for t in range(16):
            f = fields[t].transpose(0, 1, 2, 5, 3, 4, 6).reshape(16, 16, 16, 3, 48)
            lk = links[:, t]
            base = gaussian(f, lk, steps, p['base_alpha'])
            C[i, 0, t] = cp.asnumpy(correlator(base, lk, cp.zeros((3, 16, 16, 16))))
            a = cp.ones((3, 16, 16, 16))
            C[i, 1, t] = cp.asnumpy(correlator(base, lk, a)) - C[i, 0, t]
            phi = features(lk, W)
            for h in range(H):
                a = cp.stack([phi[mu][..., h] for mu in range(3)], axis=0)
                C[i, 2 + h, t] = cp.asnumpy(correlator(base, lk, a)) - C[i, 0, t]
        print(f'collected cfg {cfg} ({i + 1}/{len(ids)})', flush=True)
    return C


def correlators(C, theta, H):
    out = C[:, 0] + theta[0] * C[:, 1]
    for h in range(H):
        out += theta[1 + h] * C[:, 2 + h]
    return out


def risk_of(p, C, masses):
    cfg = {'amplitude_window': p['reference']['amplitude_window'],
           'score_window': p['reference']['score_window'],
           'geometry': p['geometry'],
           'covariance_shrinkage': p['risk']['covariance_shrinkage'],
           'amplitude_z_min': p['risk']['amplitude_z_min']}
    b = blocks(C[:, None, :], p['risk']['block_length'])
    idx = bootstrap_indices(len(b), p['risk']['bootstrap_samples'], p['seed'])
    return risk(b, [1.0], p['reference']['m0'], masses, idx, cfg)['risk']


def _failure_json_values(value):
    """Encode nonfinite observations without silently dropping a failed sample."""
    if isinstance(value, dict):
        return {key: _failure_json_values(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_failure_json_values(item) for item in value]
    if isinstance(value, (float, np.floating)) and not np.isfinite(value):
        return str(float(value))
    return value


def box_kkt_diagnostic(objective, point, bounds, *, relative_step=1e-5):
    """Estimate box-constrained KKT stationarity without changing a fit.

    This is an observation only: it does not accept/reject a candidate. The
    finite-difference evaluations are counted and timed separately from the
    optimizer's objective trace so they cannot improve its best-so-far curve.
    """
    started = time.perf_counter()
    x = np.asarray(point, dtype=float)
    box = np.asarray(bounds, dtype=float)
    result = {
        'schema': 'optgauss-box-kkt-diagnostic-v1',
        'classification': 'diagnostic_only',
        'status': 'invalid_point',
        'relative_step': float(relative_step),
        'objective_evaluations_attempted': 0,
        'objective_evaluations_completed': 0,
    }
    if (x.ndim != 1 or box.shape != (len(x), 2) or not len(x)
            or not np.isfinite(x).all() or not np.isfinite(box).all()
            or np.any(box[:, 0] >= box[:, 1])
            or np.any(x < box[:, 0]) or np.any(x > box[:, 1])
            or not np.isfinite(relative_step) or relative_step <= 0):
        result['elapsed_seconds'] = time.perf_counter() - started
        return result

    steps = relative_step * np.maximum(1.0, np.abs(x))
    active_tolerances = 10.0 * steps
    result.update({
        'status': 'probe_exception',
        'finite_difference_steps': steps.tolist(),
        'active_tolerances': active_tolerances.tolist(),
    })

    def evaluate(values):
        result['objective_evaluations_attempted'] += 1
        try:
            value = float(objective(values))
        except SolverContractBudgetStop:
            raise
        except Exception as exc:
            result['exception'] = {
                'type': f'{type(exc).__module__}.{type(exc).__qualname__}',
                'message': str(exc),
            }
            return None
        result['objective_evaluations_completed'] += 1
        if not np.isfinite(value):
            result['status'] = 'nonfinite_probe'
            return None
        return value

    f0 = evaluate(x.copy())
    if f0 is None:
        result['elapsed_seconds'] = time.perf_counter() - started
        return result

    gradient = np.empty_like(x)
    methods = []
    for i, step in enumerate(steps):
        lower, upper = box[i]
        near_lower = x[i] - lower <= active_tolerances[i]
        near_upper = upper - x[i] <= active_tolerances[i]
        if near_lower and near_upper:
            result['status'] = 'degenerate_interval'
            result['elapsed_seconds'] = time.perf_counter() - started
            return result
        plus = min(float(x[i] + step), float(upper))
        minus = max(float(x[i] - step), float(lower))
        if near_lower or minus == x[i]:
            probe = x.copy()
            probe[i] = plus
            value = evaluate(probe)
            methods.append('forward')
            if value is None:
                result['elapsed_seconds'] = time.perf_counter() - started
                result['finite_difference_methods'] = methods
                return result
            gradient[i] = (value - f0) / (plus - x[i])
        elif near_upper or plus == x[i]:
            probe = x.copy()
            probe[i] = minus
            value = evaluate(probe)
            methods.append('backward')
            if value is None:
                result['elapsed_seconds'] = time.perf_counter() - started
                result['finite_difference_methods'] = methods
                return result
            gradient[i] = (f0 - value) / (x[i] - minus)
        else:
            plus_point, minus_point = x.copy(), x.copy()
            plus_point[i], minus_point[i] = plus, minus
            f_plus, f_minus = evaluate(plus_point), evaluate(minus_point)
            methods.append('central')
            if f_plus is None or f_minus is None:
                result['elapsed_seconds'] = time.perf_counter() - started
                result['finite_difference_methods'] = methods
                return result
            gradient[i] = (f_plus - f_minus) / (plus - minus)

    lower_active = x - box[:, 0] <= active_tolerances
    upper_active = box[:, 1] - x <= active_tolerances
    violations = np.abs(gradient)
    violations[lower_active] = np.maximum(0.0, -gradient[lower_active])
    violations[upper_active] = np.maximum(0.0, gradient[upper_active])
    result.update({
        'status': 'computed',
        'gradient': gradient.tolist(),
        'finite_difference_methods': methods,
        'lower_active_indices': np.flatnonzero(lower_active).tolist(),
        'upper_active_indices': np.flatnonzero(upper_active).tolist(),
        'kkt_violation_inf': float(np.max(violations)),
        'scaled_kkt_violation_inf': float(np.max(violations) / max(1.0, np.max(np.abs(gradient)))),
        'threshold': None,
    })
    result['elapsed_seconds'] = time.perf_counter() - started
    return result


def _write_optimizer_failure(context, exception, diagnostics):
    """Publish one failure atomically without replacing any existing receipt.

    main supplies context only after its output-directory protection. Completed
    output folders are also refused here; this helper never creates a run folder.
    """
    output = Path(context['output_directory'])
    if not output.is_dir() or any((output / name).exists() for name in ('results.json', 'manifest.json')):
        raise FileExistsError('failure receipts require a protected unfinished run directory')
    required = ('run_protocol', 'protocol_fingerprint', 'source_hashes', 'statistics_sha256',
                'seed', 'lam2', 'completed_grid')
    if any(name not in context for name in required):
        raise ValueError('failure receipt is missing its run identity')
    if fingerprint(context['run_protocol']) != context['protocol_fingerprint']:
        raise ValueError('failure receipt protocol identity differs')
    if (not context['source_hashes'].get('train.py')
            or any(len(value) != 64 for value in context['source_hashes'].values())
            or len(context['statistics_sha256']) != 64):
        raise ValueError('failure receipt source hashes are incomplete')
    target = output / 'optimizer_failure.json'
    receipt = {
        **context,
        'schema': 'optgauss-optimizer-failure-v1', 'classification': 'diagnostic_only',
        'status': 'optimizer_exception', 'physical_score': None,
        'exception': {'type': f'{type(exception).__module__}.{type(exception).__qualname__}',
                      'message': str(exception)},
        'optimizer_diagnostics': diagnostics,
    }
    payload = json.dumps(_failure_json_values(receipt), indent=2, allow_nan=False) + '\n'
    fd, temporary = tempfile.mkstemp(prefix='.optimizer_failure.', suffix='.tmp', dir=output)
    try:
        with os.fdopen(fd, 'w') as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        # A same-directory hard link is an atomic no-clobber publication.
        os.link(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return target


def _write_solver_contract_rejection(context, solver_receipt):
    """Publish a no-clobber receipt when policy rejects a returned fit."""
    output = Path(context['output_directory'])
    if not output.is_dir() or any((output / name).exists() for name in ('results.json', 'manifest.json')):
        raise FileExistsError('contract rejection receipts require a protected unfinished run directory')
    required = ('run_protocol', 'protocol_fingerprint', 'source_hashes', 'statistics_sha256',
                'seed', 'lam2', 'completed_grid')
    if any(name not in context for name in required):
        raise ValueError('contract rejection receipt is missing its run identity')
    if fingerprint(context['run_protocol']) != context['protocol_fingerprint']:
        raise ValueError('contract rejection protocol identity differs')
    if (not context['source_hashes'].get('train.py')
            or any(len(value) != 64 for value in context['source_hashes'].values())
            or len(context['statistics_sha256']) != 64):
        raise ValueError('contract rejection source hashes are incomplete')
    target = output / 'optimizer_contract_rejection.json'
    receipt = {
        **context,
        'schema': 'optgauss-solver-contract-rejection-v1',
        'classification': 'diagnostic_only',
        'status': 'solver_contract_rejected',
        'physical_score': None,
        'solver_contract': solver_receipt,
    }
    payload = json.dumps(_failure_json_values(receipt), indent=2, allow_nan=False) + '\n'
    fd, temporary = tempfile.mkstemp(prefix='.optimizer_contract_rejection.', suffix='.tmp', dir=output)
    try:
        with os.fdopen(fd, 'w') as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return target


def optimize(C, p, masses, lam2, *, failure_context=None, solver_policy=None, config_id=None):
    """Run Powell; an explicit solver policy gates which fit may be scored."""
    H = p['hidden']
    objective_calls = 0
    nonfinite_objective_calls = 0
    nonfinite_parameter_calls = 0
    objective_trace = []
    best_so_far = None
    lower, upper = -p['v_max'], p['v_max']
    bounds = [(lower, upper)] * (1 + H)

    def raw_objective(theta):
        val = risk_of(p, correlators(C, theta, H), masses)
        return val + lam2 * float(np.mean(theta[1:] ** 2))

    def loss(theta):
        nonlocal objective_calls, nonfinite_objective_calls, nonfinite_parameter_calls
        nonlocal best_so_far
        objective_calls += 1
        nonfinite_parameter_calls += int(not np.all(np.isfinite(theta)))
        value = raw_objective(theta)
        finite = bool(np.isfinite(value))
        nonfinite_objective_calls += int(not finite)
        if finite:
            best_so_far = float(value) if best_so_far is None else min(best_so_far, float(value))
        objective_trace.append({
            'index': objective_calls, 'phase': 'solver',
            'elapsed_seconds': time.perf_counter() - started,
            # String encoding preserves NaN/Inf observations in strict JSON.
            'value': float(value) if finite else str(float(value)),
            'finite': finite, 'best_so_far': best_so_far,
        })
        return value

    if solver_policy is None:
        started = time.perf_counter()
        try:
            fit = minimize(loss, np.zeros(1 + H), method='Powell', bounds=bounds,
                           options={'maxiter': p['optimizer']['maxiter']})
        except Exception as exc:
            if failure_context is not None:
                try:
                    diagnostics = {
                        'method': 'Powell', 'objective_calls': objective_calls,
                        'completed_objective_calls': len(objective_trace),
                        'objective_trace': objective_trace,
                        'nonfinite_objective_calls': nonfinite_objective_calls,
                        'nonfinite_parameter_calls': nonfinite_parameter_calls,
                        'elapsed_seconds': time.perf_counter() - started,
                        'maxiter': p['optimizer']['maxiter'],
                    }
                    _write_optimizer_failure(failure_context, exc, diagnostics)
                except Exception as receipt_exc:
                    # Preserve the numerical failure even if diagnostic storage fails.
                    exc.add_note(f'optimizer failure receipt was not written: {type(receipt_exc).__name__}: {receipt_exc}')
            raise
        elapsed_seconds = time.perf_counter() - started
        theta = np.asarray(fit.x)
        final_objective = float(fit.fun)
        fit_success = bool(fit.success)
        fit_status = int(fit.status) if getattr(fit, 'status', None) is not None else None
        fit_message = str(fit.message)
        fit_nfev = int(fit.nfev)
        fit_nit = int(fit.nit) if getattr(fit, 'nit', None) is not None else None
        kkt_diagnostic = box_kkt_diagnostic(raw_objective, theta, bounds)
        contract_receipt = None
    else:
        if not isinstance(solver_policy, SolverPolicy):
            raise TypeError('solver_policy must be an explicit SolverPolicy')

        def counted_contract_objective(theta):
            nonlocal nonfinite_parameter_calls
            theta = np.asarray(theta, dtype=float)
            nonfinite_parameter_calls += int(not np.all(np.isfinite(theta)))
            return raw_objective(theta)

        def run_powell(objective):
            return minimize(objective, np.zeros(1 + H), method='Powell', bounds=bounds,
                            options={'maxiter': p['optimizer']['maxiter']})

        def measure_kkt(guarded_objective, point, _solver_result):
            diagnostic = box_kkt_diagnostic(guarded_objective, point, bounds)
            return {
                'kkt_residual': diagnostic.get('scaled_kkt_violation_inf'),
                'box_kkt_diagnostic': diagnostic,
            }

        contract_receipt = run_solver_with_contract(
            config_id if config_id is not None else 'optimize',
            counted_contract_objective,
            run_powell,
            solver_policy,
            residual_evaluator=measure_kkt,
        )
        if contract_receipt['gate_status'] != 'contract_accepted':
            rejection = SolverContractRejected(contract_receipt)
            if failure_context is not None:
                try:
                    _write_solver_contract_rejection(failure_context, contract_receipt)
                except Exception as receipt_exc:
                    rejection.add_note(
                        'solver contract rejection receipt was not written: '
                        f'{type(receipt_exc).__name__}: {receipt_exc}')
            raise rejection

        theta = np.asarray(contract_receipt['final_parameters'], dtype=float)
        final_objective = float(contract_receipt['final_objective'])
        fit_success = bool(contract_receipt['solver_success'])
        fit_status = contract_receipt['solver_status']
        fit_message = contract_receipt['solver_message'] or ''
        fit_nfev = contract_receipt['solver_nfev']
        fit_nit = contract_receipt['solver_nit']
        elapsed_seconds = contract_receipt['elapsed_seconds']
        objective_calls = contract_receipt['objective_calls']
        objective_trace = contract_receipt['objective_trace']
        nonfinite_objective_calls = sum(not row.get('finite', False) for row in objective_trace)
        best_so_far = contract_receipt['best_so_far']
        kkt_diagnostic = (contract_receipt.get('residual_diagnostic') or {}).get('box_kkt_diagnostic', {
            'schema': 'optgauss-box-kkt-diagnostic-v1',
            'classification': 'diagnostic_only',
            'status': 'missing_from_solver_contract',
        })

    receipt = {
        'schema': 'optgauss-powell-diagnostic-v1', 'classification': 'diagnostic_only',
        'method': 'Powell', 'success': fit_success,
        'status': fit_status,
        'message': fit_message, 'nfev': fit_nfev,
        'nit': fit_nit,
        'objective_calls': objective_calls, 'elapsed_seconds': elapsed_seconds,
        'objective_trace': objective_trace,
        'maxiter': p['optimizer']['maxiter'],
        'nonfinite_objective_calls': nonfinite_objective_calls,
        'nonfinite_parameter_calls': nonfinite_parameter_calls,
        'final_objective_finite': bool(np.isfinite(final_objective)),
        'final_theta_finite': bool(np.all(np.isfinite(theta))),
        'bounds': [lower, upper],
        # Exact comparisons are observations, not a new feasibility tolerance.
        'lower_bound_hit_indices': np.flatnonzero(theta == lower).tolist(),
        'upper_bound_hit_indices': np.flatnonzero(theta == upper).tolist(),
        'out_of_bounds_indices': np.flatnonzero((theta < lower) | (theta > upper)).tolist(),
        'box_kkt_diagnostic': kkt_diagnostic,
    }
    if contract_receipt is not None:
        receipt['solver_contract'] = contract_receipt
    return {'risk': final_objective, 'theta': theta.tolist(), 'nfit': fit_nfev,
            'optimizer_receipt': receipt}


def evaluate(p, ids, cache, W, theta, steps):
    import cupy as cp
    from pyquda_utils import core, io

    init_quda(p)
    latt = core.LatticeInfo(p['geometry'], -1, 1.0)
    out = np.zeros((len(ids), 16))
    H = p['hidden']
    for i, cfg in enumerate(ids):
        gauge = io.readNERSCGauge(f"{p['ensemble']}/wilson_b6.{cfg}")
        links = cp.asarray(gauge.lexico())[:3]
        prop = core.LatticePropagator(
            latt, cp.asarray(np.load(f".cache/pion_projection/propagators/{cache[cfg]}.npy")))
        fields = cp.asarray(prop.lexico())
        for t in range(16):
            f = fields[t].transpose(0, 1, 2, 5, 3, 4, 6).reshape(16, 16, 16, 3, 48)
            lk = links[:, t]
            base = gaussian(f, lk, steps, p['base_alpha'])
            phi = features(lk, W)
            a = cp.full((3, 16, 16, 16), theta[0])
            for h in range(H):
                a += theta[1 + h] * cp.stack([phi[mu][..., h] for mu in range(3)], axis=0)
            out[i, t] = cp.asnumpy(correlator(base, lk, a))
        print(f'evaluated cfg {cfg} ({i + 1}/{len(ids)})', flush=True)
    return out


def coefficient_map(p, cfg, cache, W, theta, t=0):
    import cupy as cp
    from pyquda_utils import core, io

    init_quda(p)
    gauge = io.readNERSCGauge(f"{p['ensemble']}/wilson_b6.{cfg}")
    lk = cp.asarray(gauge.lexico())[:3, t]
    phi = features(lk, W)
    a = cp.full((3, 16, 16, 16), theta[0])
    for h in range(p['hidden']):
        a += theta[1 + h] * cp.stack([phi[mu][..., h] for mu in range(3)], axis=0)
    return cp.asnumpy(a)


def q_curve(C, p):
    m0 = p['reference']['m0']
    t = np.arange(16, dtype=float)
    f0 = np.exp(-m0 * t) + np.exp(-m0 * (16 - t))
    c = C.mean(0)
    late = p['reference']['amplitude_window']
    A = c[late] @ f0[late] / (f0[late] @ f0[late])
    return c / (A * f0)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Train and evaluate the Optimize Gaussian candidate")
    parser.add_argument("output", nargs="?", help="new run output directory (defaults to protocol output)")
    parser.add_argument("--resume", action="store_true",
                        help="resume only when the output directory contains basis caches and nothing else")
    parser.add_argument("--protocol", help="explicit frozen protocol JSON (requires --protocol-sha256)")
    parser.add_argument("--protocol-sha256", help="expected SHA-256 of the exact protocol file bytes")
    args = parser.parse_args(argv)
    if (args.protocol is None) != (args.protocol_sha256 is None):
        parser.error("--protocol and --protocol-sha256 must be supplied together")
    try:
        p = (protocol(args.protocol, args.protocol_sha256)
             if args.protocol is not None else protocol())
        solver_policy = solver_policy_from_protocol(p, required=args.protocol is not None)
    except (OSError, ValueError) as exc:
        parser.error(f"cannot load frozen Optimize protocol: {exc}")
    output_path = Path(args.output or p['output'])
    resumable_basis_names = {f"basis_s{seed}.npz" for seed in p['seeds']}
    try:
        out = prepare_output_directory(
            output_path,
            resume=args.resume,
            allowed_existing=lambda child: child.is_file() and child.name in resumable_basis_names,
        )
    except FileExistsError as exc:
        parser.error(str(exc))
    dev = json.loads(Path(p['cache_manifest']).read_text())
    val = json.loads(Path(p['validation_manifest']).read_text())
    cache = {r['id']: r['cache_key'] for r in dev['records'] + val['records']}
    masses = np.load(p['reference_bootstrap'])['masses']
    fit_ids = list(range(p['fit'][0], p['fit'][1] + 1))
    devval_ids = list(range(p['dev_val'][0], p['dev_val'][1] + 1))
    test_ids = list(range(p['test'][0], p['test'][1] + 1))
    H, steps = p['hidden'], p['base_steps']

    grid, best = [], None
    here = Path(__file__).parent
    failure_identity = {
        'output_directory': str(out), 'run_protocol': p, 'protocol_fingerprint': fingerprint(p),
        'source_hashes': {name: digest(here / name) for name in
                          ('train.py', 'features.py', 'kernels.py', 'submission.py', 'solver_contract.py')},
        'statistics_sha256': digest(here.parent / 'pion_projection' / 'statistics.py'),
    }
    for seed in p['seeds']:
        W = model_space(p, seed)
        cache_file = out / f'basis_s{seed}.npz'
        key = basis_key(p, seed, W, fit_ids, devval_ids, cache=cache)
        if cache_file.exists():
            C_fit, C_dev = load_basis(cache_file, key)
        else:
            C_fit = collect(p, fit_ids, cache, W, steps)
            C_dev = collect(p, devval_ids, cache, W, steps)
            save_basis(cache_file, key, C_fit, C_dev)
        base_dev = risk_of(p, correlators(C_dev, np.zeros(1 + H), H), masses)
        for lam2 in p['l2_grid']:
            optimize_kwargs = {'failure_context': {
                **failure_identity, 'seed': seed, 'lam2': lam2, 'completed_grid': list(grid),
            }}
            if solver_policy is not None:
                optimize_kwargs.update(
                    solver_policy=solver_policy,
                    config_id={'seed': int(seed), 'lam2': float(lam2)},
                )
            fit = optimize(C_fit, p, masses, lam2, **optimize_kwargs)
            dev_risk = risk_of(p, correlators(C_dev, np.array(fit['theta']), H), masses)
            grid.append({'seed': seed, 'lam2': lam2, 'dev_val': dev_risk,
                         'nfit': fit['nfit'], 'theta': fit['theta'], 'base_dev': base_dev,
                         'optimizer_receipt': fit['optimizer_receipt']})
            print('GRID', json.dumps({'seed': seed, 'lam2': lam2, 'dev_val': dev_risk}), flush=True)
            if best is None or dev_risk < best['dev_val']:
                best = dict(grid[-1])

    W = model_space(p, best['seed'])
    theta = np.array(best['theta'])
    C_base = evaluate(p, test_ids, cache, W, np.zeros(1 + H), steps)
    C_test = evaluate(p, test_ids, cache, W, theta, steps)
    np.savez_compressed(out / 'data.npz', C_test=C_test, C_base=C_base,
                        q_learned=q_curve(C_test, p), q_base=q_curve(C_base, p),
                        a_map=coefficient_map(p, test_ids[0], cache, W, theta), W=W)
    summary = {'fit_ids': fit_ids, 'dev_val_ids': devval_ids, 'test_ids': test_ids,
               'hidden': H, 'base_steps': steps, 'seeds': p['seeds'],
               'base': {'dev_val': best['base_dev'], 'test': risk_of(p, C_base, masses)},
               'grid': [{k: g[k] for k in ('seed', 'lam2', 'dev_val', 'nfit', 'optimizer_receipt')} for g in grid],
               'best': {k: best[k] for k in ('seed', 'lam2', 'dev_val', 'optimizer_receipt')},
               'theta': best['theta'],
               'test_risk_learned': risk_of(p, C_test, masses),
               'test_risk_base': risk_of(p, C_base, masses)}
    summary['test_ratio'] = summary['test_risk_base'] / summary['test_risk_learned']
    (out / 'results.json').write_text(json.dumps(summary, indent=2) + '\n')
    (out / 'manifest.json').write_text(json.dumps(
        run_manifest(p, W, theta, fit_ids, devval_ids, test_ids, cache), indent=2) + '\n')
    print('SUMMARY', json.dumps({'best': summary['best'], 'test_ratio': summary['test_ratio']}), flush=True)


if __name__ == '__main__':
    main()
