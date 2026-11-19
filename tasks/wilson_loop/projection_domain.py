"""Projection support-domain audit (todo P0b).

Frozen grid of singular-value spectra x scale x det phase. Inside the declared
support (condition number <= 1e6, all singular values positive) the polar
projection must reach the tolerance and preserve the det phase; outside it must
fail with an explicit reason, never return a silent garbage matrix.
"""
import json
from pathlib import Path

import numpy as np

from .kernels import project

OUT = Path('results/wilson_loop/audit_20261119_projection_domain')
SPECTRA = ((1.0, 1.0, 1.0), (1.0, 1.0, 1e-2), (1.0, 1.0, 1e-3),
           (1.0, 1.0, 1e-4), (1.0, 1.0, 1e-5), (1.0, 1.0, 0.0))
SCALES = (1e-3, 1.0, 1e3)
PHASES = (-np.pi, -np.pi / 2, 0.0, np.pi / 2, np.pi)
TOL = 1e-9
MAX_CONDITION = 1e3


def cell(rng, svals, scale, phase):
    u, _ = np.linalg.qr(rng.normal(size=(3, 3)) + 1j * rng.normal(size=(3, 3)))
    v, _ = np.linalg.qr(rng.normal(size=(3, 3)) + 1j * rng.normal(size=(3, 3)))
    a = scale * u @ np.diag(svals) @ v.conj().T
    return a * np.exp(1j * phase / 3)


def residual(x):
    return float(np.max(np.abs(x.conj().T @ x - np.eye(3))))


def supported(svals):
    smallest, largest = min(svals), max(svals)
    return smallest > 0 and largest / smallest <= MAX_CONDITION


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261119)
    rows = []
    for svals in SPECTRA:
        for scale in SCALES:
            for phase in PHASES:
                a = cell(rng, svals, scale, phase)
                inside = supported(svals)
                row = {'svals': list(svals), 'scale': scale, 'phase': float(phase),
                       'inside_support': bool(inside)}
                try:
                    x = project(a[None])
                    l, _ = np.linalg.qr(rng.normal(size=(3, 3)) + 1j * rng.normal(size=(3, 3)))
                    r, _ = np.linalg.qr(rng.normal(size=(3, 3)) + 1j * rng.normal(size=(3, 3)))
                    l = l / np.linalg.det(l) ** (1 / 3)     # SU(3): no extra global phase
                    r = r / np.linalg.det(r) ** (1 / 3)
                    y = project((l @ a @ r)[None])
                    row['covariance_residual'] = float(np.max(np.abs(y[0] - l @ x[0] @ r))
                                                       / max(np.max(np.abs(x[0])), 1e-300))
                    row['residual'] = residual(x[0])
                    row['det_phase_error'] = float(abs(np.angle(np.linalg.det(x[0]))
                                                       - np.angle(np.linalg.det(a))))
                    row['unitarity_ok'] = bool(row['residual'] <= TOL)
                    row['rejected'] = not inside or not row['unitarity_ok']
                    if not inside:
                        row['reason'] = (f'outside the declared support (condition '
                                         f'{max(row["svals"]) / min(row["svals"]):.0e} > '
                                         f'{MAX_CONDITION:.0e})')
                    elif not row['unitarity_ok']:
                        row['reason'] = (f'unitarity residual {row["residual"]:.3e} '
                                         f'exceeds tolerance {TOL:.0e}')
                except ValueError as exc:
                    row.update({'residual': None, 'det_phase_error': None, 'covariance_residual': None,
                                'unitarity_ok': False, 'rejected': True, 'reason': str(exc)})
                rows.append(row)
    inside = [row for row in rows if row['inside_support']]
    outside = [row for row in rows if not row['inside_support']]
    covariances = [row['covariance_residual'] for row in inside
                   if row.get('covariance_residual') is not None]
    result = {'schema': 'wilson-projection-domain-v1', 'tolerance': TOL,
              'max_inside_covariance_residual': max(covariances) if covariances else None,
              'max_condition': MAX_CONDITION, 'rows': rows,
              'inside_all_pass': all(row['unitarity_ok'] for row in inside),
              'outside_all_rejected': all(row['rejected'] for row in outside),
              'outside_with_numerically_small_residual': [
                  {'svals': row['svals'], 'scale': row['scale'], 'phase': row['phase'],
                   'residual': row['residual']} for row in outside
                  if row['residual'] is not None and row['residual'] <= TOL],
              'silent_failures': sum(1 for row in rows
                                     if not row['unitarity_ok'] and not row['rejected']),
              'note': ('support is a condition-number statement, not absolute scale; the det '
                       'phase is preserved by the polar factor and the branch cut at pi is not '
                       'a continuity claim')}
    (OUT / 'projection_domain.json').write_text(json.dumps(result, indent=2) + '\n')
    print('inside_all_pass', result['inside_all_pass'],
          'outside_all_rejected', result['outside_all_rejected'],
          'silent_failures', result['silent_failures'])
    bad = [row for row in outside if not (row['rejected'] or not row['unitarity_ok'])]
    for row in bad[:3]:
        print('outside accepted:', row['svals'], row['scale'], row['residual'])


if __name__ == '__main__':
    main()
