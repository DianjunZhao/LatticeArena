"""Actual BCB-response-core search loop (todo D)."""
import json
import time
from pathlib import Path

import numpy as np

from core.io import digest_text
from core.measurement import bundle, describe, require
from core.operator_checks import hermiticity_residual, linearity_residual
from core.search import Budget, search

from .submission import build_kernel

OUT = Path('results/optimize_gaussian/cpu_close_20261119_D')
L = 4
BASE = json.loads(Path('results/optimize_gaussian/v9/submission.json').read_text())['parameters']


def su3(rng, shape):
    a = rng.normal(size=(*shape, 3, 3)) + 1j * rng.normal(size=(*shape, 3, 3))
    q, _ = np.linalg.qr(a)
    return q / np.linalg.det(q)[..., None, None] ** (1 / 3)


def response(theta, links, field, params):
    params = dict(params, theta=[float(x) for x in theta])
    kernel = build_kernel(links, params)
    out = kernel.apply(field)
    return float(np.real(np.vdot(field, out))), out


def operator_checks(links, field, params):
    theta = params['theta']
    op = lambda f: build_kernel(links, dict(params, theta=theta)).apply(f)
    rng = np.random.default_rng(2)
    other = rng.normal(size=field.shape) + 1j * rng.normal(size=field.shape)
    bilinear = lambda f, g: np.vdot(f, op(g))
    return {'linearity': linearity_residual(op, field, other),
            'hermitian': hermiticity_residual(bilinear, field, other)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261119)
    links = np.transpose(su3(rng, (L, L, L, 3)), (3, 0, 1, 2, 4, 5))
    field = rng.normal(size=(L, L, L, 3, 1)) + 1j * rng.normal(size=(L, L, L, 3, 1))
    params = dict(BASE)
    base_response, base_out = response(params['theta'], links, field, params)
    proposals = [('base', params['theta']),
                 ('shift1', [params['theta'][0] + 0.1] + params['theta'][1:]),
                 ('shift2', [params['theta'][0] - 0.1] + params['theta'][1:]),
                 ('bad', ['not-a-number', 0.0, 0.0]),
                 ('nan', [float('nan'), 0.0, 0.0])]
    budget = Budget(4)
    result = search(proposals, lambda theta: response(theta, links, field, params)[0],
                    validate=lambda u: (len(u) == len(params['theta'])
                                        and np.all(np.isfinite(np.asarray(u, dtype=float))),
                                        'malformed theta'),
                    budget=budget)
    best = min(result.accepted, key=lambda item: item['risk']) if result.accepted else None
    exact = None
    if best is not None:
        exact = response(best['candidate'], links, field, params)[0]
    checks = operator_checks(links, field, params)
    b = bundle('optimize_gaussian',
               {'field': field.reshape(-1), 'response': np.asarray([base_response])},
               {'protocol_hash': digest_text(json.dumps(params, sort_keys=True)),
                'splits': {'development': {'n': 1}}, 'code': {'submission.py': 'v9'}},
               {'linear_response': True, 'cross_matrix': False, 'new_source': False})
    refusal = None
    try:
        require(b, 'cross_matrix')
    except ValueError as exc:
        refusal = str(exc)
    rows = {'base_response': base_response,
            'best_theta': None if best is None else [float(x) for x in best['candidate']],
            'best_surrogate': None if best is None else best['risk'],
            'best_exact': exact,
            'surrogate_exact_difference': None if best is None or exact is None
            else abs(best['risk'] - exact),
            'accepted': len(result.accepted), 'rejected': len(result.rejected),
            'evaluations': result.evaluations, 'budget': 4,
            'rejection_reasons': [item['reason'] for item in result.rejected],
            'operator': checks, 'capability_refusal': refusal,
            'bundle': describe(b),
            'seconds': None}
    t0 = time.perf_counter()
    response(best['candidate'], links, field, params) if best else None
    rows['seconds'] = time.perf_counter() - t0
    result_json = {'schema': 'optgauss-adapt-v2', 'rows': rows}
    (OUT / 'adapt_v2.json').write_text(json.dumps(result_json, indent=2) + '\n')
    print(json.dumps(result_json, indent=2)[:1200])


if __name__ == '__main__':
    main()
