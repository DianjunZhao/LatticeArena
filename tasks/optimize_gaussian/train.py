"""v5: separate the uniform and site-adaptive parts of the learned correction.

a_mu(x) = c_mu + sum_h v_{mu h} phi_h(x),   phi zero-mean per time slice
K = C_hop(a) G^m,  b_mu(x) = a_mu(x-mu)

models: uniform (c only), spatial (v only), full (c + v)
"""
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from tasks.pion_projection.statistics import blocks, bootstrap_indices, risk

from .features import _lib, plaquettes
from .kernels import apply_kernel, correlator


def protocol():
    return json.loads((Path(__file__).parent / 'protocol.json').read_text())


def init_quda(p):
    import cupy as cp  # noqa: F401
    from pyquda_utils import core
    if not getattr(init_quda, 'done', False):
        core.init([1, 1, 1, 1], p['geometry'], resource_path='.cache/quda')
        init_quda.done = True


def model_space(p):
    rng = np.random.default_rng(p['seed'])
    return rng.normal(size=(p['hidden'], len(p['features']))) * 0.5


def gaussian(field, links, steps, a0):
    xp = _lib(field)
    a = xp.full((3, *field.shape[:3]), a0)
    for _ in range(steps):
        field = apply_kernel(field, links, a)
    return field


def features(links, W):
    import cupy as cp
    f = cp.tanh(plaquettes(links) @ cp.asarray(W.T))
    return f - f.mean(axis=(0, 1, 2), keepdims=True)


def collect(p, ids, cache, W, base_steps):
    import cupy as cp
    from pyquda_utils import core, io

    init_quda(p)
    latt = core.LatticeInfo(p['geometry'], -1, 1.0)
    H, nb = p['hidden'], 1 + 3 + 3 * p['hidden']
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
            base = gaussian(f, lk, base_steps, p['base_alpha'])
            C[i, 0, t] = cp.asnumpy(correlator(base, lk, cp.zeros((3, 16, 16, 16))))
            feat = features(lk, W)
            for mu in range(3):
                a = cp.zeros((3, 16, 16, 16))
                a[mu] = 1
                C[i, 1 + mu, t] = cp.asnumpy(correlator(base, lk, a)) - C[i, 0, t]
                for h in range(H):
                    a = cp.zeros((3, 16, 16, 16))
                    a[mu] = feat[..., h]
                    C[i, 1 + 3 + mu * H + h, t] = cp.asnumpy(correlator(base, lk, a)) - C[i, 0, t]
        print(f'collected cfg {cfg} ({i + 1}/{len(ids)})', flush=True)
    return C


def correlators(C, c, v, H):
    out = C[:, 0].copy()
    for mu in range(3):
        out += c[mu] * C[:, 1 + mu]
        for h in range(H):
            out += v[mu * H + h] * C[:, 1 + 3 + mu * H + h]
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


def split(theta, mode, H):
    if mode == 'uniform':
        return theta[:3], np.zeros(3 * H)
    if mode == 'spatial':
        return np.zeros(3), theta
    return theta[:3], theta[3:]


def optimize(C, p, masses, mode):
    H = p['hidden']

    def loss(theta):
        c, v = split(theta, mode, H)
        val = risk_of(p, correlators(C, c, v, H), masses)
        return val + p['l2'] * float(np.mean(v ** 2))

    n = {'uniform': 3, 'spatial': 3 * H, 'full': 3 + 3 * H}[mode]
    fit = minimize(loss, np.zeros(n), method='Powell', bounds=[(-p['v_max'], p['v_max'])] * n,
                   options={'maxiter': p['optimizer']['maxiter']})
    c, v = split(fit.x, mode, H)
    return {'risk': float(fit.fun), 'c': c.tolist(), 'v': v.tolist(), 'nfit': int(fit.nfev)}


def evaluate(p, ids, cache, W, c, v, base_steps):
    import cupy as cp
    from pyquda_utils import core, io

    init_quda(p)
    latt = core.LatticeInfo(p['geometry'], -1, 1.0)
    out = np.zeros((len(ids), 16))
    for i, cfg in enumerate(ids):
        gauge = io.readNERSCGauge(f"{p['ensemble']}/wilson_b6.{cfg}")
        links = cp.asarray(gauge.lexico())[:3]
        prop = core.LatticePropagator(
            latt, cp.asarray(np.load(f".cache/pion_projection/propagators/{cache[cfg]}.npy")))
        fields = cp.asarray(prop.lexico())
        for t in range(16):
            f = fields[t].transpose(0, 1, 2, 5, 3, 4, 6).reshape(16, 16, 16, 3, 48)
            lk = links[:, t]
            base = gaussian(f, lk, base_steps, p['base_alpha'])
            feat = features(lk, W)
            a = cp.asarray(np.repeat(np.asarray(c)[:, None, None, None], 16, axis=1).repeat(16, axis=2).repeat(16, axis=3))
            for mu in range(3):
                for h in range(p['hidden']):
                    a[mu] += v[mu * p['hidden'] + h] * feat[..., h]
            out[i, t] = cp.asnumpy(correlator(base, lk, a))
        print(f'evaluated cfg {cfg} ({i + 1}/{len(ids)})', flush=True)
    return out


def coefficient_map(p, cfg, cache, W, c, v, t=0):
    import cupy as cp
    from pyquda_utils import core, io

    init_quda(p)
    gauge = io.readNERSCGauge(f"{p['ensemble']}/wilson_b6.{cfg}")
    lk = cp.asarray(gauge.lexico())[:3, t]
    feat = features(lk, W)
    a = cp.asarray(np.repeat(np.asarray(c)[:, None, None, None], 16, axis=1).repeat(16, axis=2).repeat(16, axis=3))
    for mu in range(3):
        for h in range(p['hidden']):
            a[mu] += v[mu * p['hidden'] + h] * feat[..., h]
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
    W = model_space(p)
    H = p['hidden']
    steps = p['base_steps']

    if (out / 'basis.npz').exists():
        z = np.load(out / 'basis.npz')
        C_fit, C_dev = z['C_fit'], z['C_dev']
    else:
        C_fit = collect(p, fit_ids, cache, W, steps)
        C_dev = collect(p, devval_ids, cache, W, steps)
        np.savez_compressed(out / 'basis.npz', C_fit=C_fit, C_dev=C_dev)

    base_dev = risk_of(p, correlators(C_dev, np.zeros(3), np.zeros(3 * H), H), masses)
    results = {'base': {'dev_val': base_dev}}
    for mode in p['models']:
        fit = optimize(C_fit, p, masses, mode)
        dev = risk_of(p, correlators(C_dev, np.array(fit['c']), np.array(fit['v']), H), masses)
        results[mode] = {'dev_val': dev, 'c': fit['c'], 'v': fit['v'], 'nfit': fit['nfit']}
        print('MODEL', mode, json.dumps({'dev_val': dev}), flush=True)

    C_base = evaluate(p, test_ids, cache, W, np.zeros(3), np.zeros(3 * H), steps)
    results['base']['test'] = risk_of(p, C_base, masses)
    best_mode = min([m for m in p['models']], key=lambda m: results[m]['dev_val'])
    for mode in p['models']:
        C_test = evaluate(p, test_ids, cache, W, np.array(results[mode]['c']), np.array(results[mode]['v']), steps)
        results[mode]['test'] = risk_of(p, C_test, masses)
        print('TEST', mode, json.dumps({'dev_val': results[mode]['dev_val'],
                                        'test': results[mode]['test']}), flush=True)
        if mode == best_mode:
            np.savez_compressed(out / 'data.npz', C_test=C_test, C_base=C_base,
                                q_learned=q_curve(C_test, p), q_base=q_curve(C_base, p),
                                a_map=coefficient_map(p, test_ids[0], cache, W,
                                                      np.array(results[mode]['c']),
                                                      np.array(results[mode]['v'])),
                                W=W)

    summary = {'fit_ids': fit_ids, 'dev_val_ids': devval_ids, 'test_ids': test_ids,
               'hidden': H, 'base_steps': steps, 'v_max': p['v_max'], 'l2': p['l2'],
               'base': results['base'], 'models': {m: {k: results[m][k] for k in ('dev_val', 'test')}
                                                   for m in p['models']},
               'best_mode': best_mode,
               'test_ratio': results['base']['test'] / results[best_mode]['test']}
    (out / 'results.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('SUMMARY', json.dumps({'best_mode': best_mode, 'base_test': results['base']['test'],
                                 'best_test': results[best_mode]['test'],
                                 'ratio': summary['test_ratio']}), flush=True)


if __name__ == '__main__':
    main()
