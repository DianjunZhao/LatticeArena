"""v6: A1+ (cubically symmetric) learned smear.

a_mu(x) = c + sum_h v_h phi_h(mu, x),  phi shared across directions, zero mean over sites
phi_h(mu, x) = tanh(W_h . (P_{mu nu}(x), P_{mu rho}(x)))  -- the two plaquettes containing mu
K = C_hop(a) G^m,  b_mu(x) = a_mu(x - mu)
"""
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from tasks.pion_projection.statistics import blocks, bootstrap_indices, risk

from .features import _lib, directional_features
from .kernels import apply_kernel, correlator


def protocol():
    return json.loads((Path(__file__).parent / 'protocol.json').read_text())


def init_quda(p):
    import cupy as cp  # noqa: F401
    from pyquda_utils import core
    if not getattr(init_quda, 'done', False):
        core.init([1, 1, 1, 1], p['geometry'], resource_path='.cache/quda')
        init_quda.done = True


def model_space(p, seed):
    rng = np.random.default_rng(seed)
    return rng.normal(size=(p['hidden'], 2)) * 0.5


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


def optimize(C, p, masses, lam2):
    H = p['hidden']

    def loss(theta):
        val = risk_of(p, correlators(C, theta, H), masses)
        return val + lam2 * float(np.mean(theta[1:] ** 2))

    fit = minimize(loss, np.zeros(1 + H), method='Powell', bounds=[(-p['v_max'], p['v_max'])] * (1 + H),
                   options={'maxiter': p['optimizer']['maxiter']})
    return {'risk': float(fit.fun), 'theta': fit.x.tolist(), 'nfit': int(fit.nfev)}


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


def main():
    import sys
    p = protocol()
    if len(sys.argv) > 1:
        p['output'] = sys.argv[1]
    out = Path(p['output'])
    out.mkdir(parents=True, exist_ok=True)
    dev = json.loads(Path(p['cache_manifest']).read_text())
    val = json.loads(Path(p['validation_manifest']).read_text())
    cache = {r['id']: r['cache_key'] for r in dev['records'] + val['records']}
    masses = np.load(p['reference_bootstrap'])['masses']
    fit_ids = list(range(p['fit'][0], p['fit'][1] + 1))
    devval_ids = list(range(p['dev_val'][0], p['dev_val'][1] + 1))
    test_ids = list(range(p['test'][0], p['test'][1] + 1))
    H, steps = p['hidden'], p['base_steps']

    grid, best = [], None
    for seed in p['seeds']:
        W = model_space(p, seed)
        cache_file = out / f'basis_s{seed}.npz'
        if cache_file.exists():
            z = np.load(cache_file)
            C_fit, C_dev = z['C_fit'], z['C_dev']
        else:
            C_fit = collect(p, fit_ids, cache, W, steps)
            C_dev = collect(p, devval_ids, cache, W, steps)
            np.savez_compressed(cache_file, C_fit=C_fit, C_dev=C_dev)
        base_dev = risk_of(p, correlators(C_dev, np.zeros(1 + H), H), masses)
        for lam2 in p['l2_grid']:
            fit = optimize(C_fit, p, masses, lam2)
            dev_risk = risk_of(p, correlators(C_dev, np.array(fit['theta']), H), masses)
            grid.append({'seed': seed, 'lam2': lam2, 'dev_val': dev_risk,
                         'nfit': fit['nfit'], 'theta': fit['theta'], 'base_dev': base_dev})
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
               'grid': [{k: g[k] for k in ('seed', 'lam2', 'dev_val', 'nfit')} for g in grid],
               'best': {k: best[k] for k in ('seed', 'lam2', 'dev_val')},
               'theta': best['theta'],
               'test_risk_learned': risk_of(p, C_test, masses),
               'test_risk_base': risk_of(p, C_base, masses)}
    summary['test_ratio'] = summary['test_risk_base'] / summary['test_risk_learned']
    (out / 'results.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('SUMMARY', json.dumps({'best': summary['best'], 'test_ratio': summary['test_ratio']}), flush=True)


if __name__ == '__main__':
    main()
