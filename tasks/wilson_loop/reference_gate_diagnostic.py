"""CPU-only, unfrozen window-gate proposals; no file, split or score access.

The caller must establish development identity/completeness before supplying data.
This pure calculation cannot authorize validation or certify a production gate.
"""
import hashlib
from itertools import combinations

import numpy as np

from .statistics import blocks, bootstrap_indices, potential


THRESHOLD = 2.5


def _window_estimates(mean, boot_mean, windows, t_values):
    nr = mean.shape[0]
    point = np.full((nr, len(windows)), np.nan)
    boot = np.full((len(boot_mean), nr, len(windows)), np.nan)
    diagnostics = []
    for w, window in enumerate(windows):
        cols = [t_values.index(t) for t in window]
        for r in range(nr):
            p = mean[r, cols]
            if np.all(np.isfinite(p) & (p > 0)):
                point[r, w] = potential(mean[r:r + 1], window, t_values)[0]
            sample = boot_mean[:, r, :][:, cols]
            valid = np.all(np.isfinite(sample) & (sample > 0), axis=1)
            if valid.any():
                boot[valid, r, w] = potential(boot_mean[valid, r:r + 1], window, t_values)[:, 0]
            diagnostics.append({
                'r_index': r, 'window_index': w,
                'point_nonfinite_mean': bool(np.any(~np.isfinite(p))),
                'point_nonpositive_mean': bool(np.any(p <= 0)),
                'nonfinite_mean_draw_indices': np.flatnonzero(~np.isfinite(sample).all(axis=1)).tolist(),
                'nonpositive_mean_draw_indices': np.flatnonzero((sample <= 0).any(axis=1)).tolist(),
            })
    return point, boot, diagnostics


def _summarize(point, boot, pairs):
    """Keep one shared draw axis. Never discard failed draws to estimate an SD."""
    rows, draw_vectors = [], []
    for r in range(point.shape[0]):
        for i, j in pairs:
            p = point[r, i] - point[r, j]
            d = boot[:, r, i] - boot[:, r, j]
            valid = np.isfinite(d)
            failures = []
            if not np.isfinite(p):
                failures.append('INVALID_POINT_WINDOW_MEAN_OR_POTENTIAL')
            if not valid.all():
                failures.append('INVALID_BOOTSTRAP_WINDOW_MEAN_OR_POTENTIAL')
            sd = floor = z = None
            if not failures:
                with np.errstate(over='ignore', invalid='ignore'):
                    sd = float(d.std(ddof=1))
                scale = max(1., abs(float(point[r, i])), abs(float(point[r, j])),
                            float(np.max(np.abs(boot[:, r, i]))),
                            float(np.max(np.abs(boot[:, r, j]))))
                floor = float(64 * np.finfo(np.float64).eps * scale)
                if not np.isfinite(sd):
                    sd = None
                    failures.append('NONFINITE_PAIRED_SD')
                elif sd <= floor:
                    failures.append('ABSTAIN_DEGENERATE_SE')
                else:
                    z = float(p / sd)
                    draw_vectors.append(d / sd)
            rows.append({'r_index': r, 'window_i': i, 'window_j': j,
                         'point_difference': float(p) if np.isfinite(p) else None,
                         'paired_sd': sd, 'denominator_floor': floor, 'z': z,
                         'valid_draw_count': int(valid.sum()),
                         'invalid_draw_count': int((~valid).sum()),
                         'invalid_draw_indices': np.flatnonzero(~valid).tolist(),
                         'failure_reasons': failures})
    invalid = any(row['failure_reasons'] for row in rows)
    if invalid:
        return {'status': 'ABSTAIN', 'maximum': None, 'argmax': [], 'contrasts': rows}, None
    values = np.abs([row['z'] for row in rows])
    maximum = float(values.max())
    return {'status': _decision(maximum), 'maximum': maximum,
            'argmax': [i for i, v in enumerate(values) if v == maximum],
            'contrasts': rows}, np.stack(draw_vectors, axis=1)


def _decision(value):
    return 'PROPOSAL_DIAGNOSTIC_PASS' if value <= THRESHOLD else 'REJECT_WINDOW_INSTABILITY'


def _linear_q95(values):
    # Explicit NumPy linear quantile, also compatible with older NumPy runtimes.
    position = .95 * (len(values) - 1)
    low = int(np.floor(position))
    high = int(np.ceil(position))
    ordered = np.sort(values)
    return float(ordered[low] + (position - low) * (ordered[high] - ordered[low]))


def window_gate_proposals(identity_loops, *, windows, t_values, nominal=1,
                          block_length=5, bootstrap_samples=5000, seed=2026112021):
    """Return A/B/C development diagnostics from real loops (nconfig,nR,nT).

    No I/O or gate/RunSpec mutation. Shape/config errors raise ValueError; an
    undefined numerical estimator returns ABSTAIN, with contrast failure masks.
    The 64*eps denominator floor, equality rule and C quantile are proposals.
    """
    raw = np.asarray(identity_loops)
    if raw.ndim != 3 or any(n == 0 for n in raw.shape) or np.iscomplexobj(raw):
        raise ValueError('Expected nonempty real identity loops (nconfig,nR,nT)')
    if not all(isinstance(v, (int, np.integer)) and not isinstance(v, (bool, np.bool_))
               for v in (block_length, bootstrap_samples, seed, nominal)):
        raise ValueError('block/bootstrap/seed/nominal must be integers')
    if block_length <= 0 or bootstrap_samples < 2 or seed < 0:
        raise ValueError('Invalid block length, bootstrap count or seed')
    t_values = list(t_values)
    windows = [list(w) for w in windows]
    if (len(t_values) != raw.shape[2] or len(set(t_values)) != len(t_values)
            or not np.isfinite(np.asarray(t_values, dtype=float)).all()):
        raise ValueError('T labels must be finite, unique and match the T axis')
    if len(windows) < 2 or not 0 <= nominal < len(windows):
        raise ValueError('Need at least two windows and a valid nominal index')
    for w in windows:
        if len(w) < 2 or len(set(w)) != len(w) or any(t not in t_values for t in w):
            raise ValueError('Each window needs at least two unique available T labels')
    data = np.asarray(raw, dtype=np.float64)
    blocked = blocks(data, block_length)  # existing >=3 blocks / no dropped rows contract
    index = bootstrap_indices(len(blocked), bootstrap_samples, seed)
    with np.errstate(invalid='ignore', over='ignore'):
        mean = blocked.mean(axis=0)
        boot_mean = blocked[index].mean(axis=1)
    point, boot, window_diagnostics = _window_estimates(mean, boot_mean, windows, t_values)
    nominal_pairs = [(w, nominal) for w in range(len(windows)) if w != nominal]
    a, standardized = _summarize(point, boot, nominal_pairs)
    b, _ = _summarize(point, boot, list(combinations(range(len(windows)), 2)))
    input_invalid = not np.isfinite(data).all()
    if input_invalid:
        # A nonfinite input outside selected windows must also never earn a PASS.
        for proposal in (a, b):
            proposal['status'] = 'ABSTAIN'
            proposal['maximum'] = None
            proposal['argmax'] = []
        standardized = None
    c = {'status': 'ABSTAIN', 'centered': None, 'uncentered': None}
    if standardized is not None:
        uncentered = np.max(np.abs(standardized), axis=1)
        centered = np.max(np.abs(standardized - standardized.mean(axis=0)), axis=1)
        c = {'status': 'DIAGNOSTIC_ONLY', 'quantile': .95, 'quantile_method': 'linear',
             'centered': {'q95': _linear_q95(centered),
                          'candidate_decision': _decision(_linear_q95(centered)),
                          'draw_maxima': centered.tolist()},
             'uncentered': {'q95': _linear_q95(uncentered),
                            'candidate_decision': _decision(_linear_q95(uncentered)),
                            'draw_maxima': uncentered.tolist()}}
    # Any invalid draw/denominator in any required contrast abstains the whole
    # proposal comparison, retaining unaffected row diagnostics for inspection.
    all_valid = a['status'] != 'ABSTAIN' and b['status'] != 'ABSTAIN'
    if not all_valid:
        a['status'] = b['status'] = 'ABSTAIN'
        c = {'status': 'ABSTAIN', 'centered': None, 'uncentered': None}
    return {'status': 'PROPOSAL_NOT_FROZEN', 'scope': 'development_diagnostic_only',
            'production_score': None, 'threshold': THRESHOLD,
            'parameters': {'nconfig': len(data), 'nR': data.shape[1], 'nT': data.shape[2],
                           'windows': windows, 't_values': t_values, 'nominal': nominal,
                           'block_length': block_length, 'nblocks': len(blocked),
                           'bootstrap_samples': bootstrap_samples, 'seed': seed,
                           'ddof': 1, 'floor_factor': 64, 'equality_passes': True},
            'input_failure_reasons': ['NONFINITE_INPUT_LOOPS'] if input_invalid else [],
            'window_mean_diagnostics': window_diagnostics,
            'index_sha256_le_i8': hashlib.sha256(index.astype('<i8').tobytes()).hexdigest(),
            'bootstrap_index': index.tolist(),
            'point_potentials': [[float(x) if np.isfinite(x) else None for x in r] for r in point],
            'A': a, 'B': b, 'C': c,
            'comparison_status': 'VALID_DIAGNOSTIC' if all_valid else 'ABSTAIN',
            'limits': 'Unfrozen proposals; no family-wise calibration or ground-state accuracy certification.'}
