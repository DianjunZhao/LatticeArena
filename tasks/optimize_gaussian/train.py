"""v3: learned gauge-invariant correction on a Gaussian base, full risk, two bases.

K = C_hop(a) G^m,  G = I + a0 hop,  C_hop(a) = I + sum_mu [a_mu T_mu + b_mu T_mu^dag]
b_mu(x) = a_mu(x-mu),  a_mu(x) = sum_h v_{mu h} phi_h(x),  phi = tanh(W f), f = 1-plaquette
v in [0, v_max]  =>  a >= 0.
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
            feat = cp.tanh(plaquettes(lk) @ cp.asarray(W.T))
            for mu in range(3):
                a = cp.zeros((3, 16, 16, 16))
                a[mu] = 1
                C[i, 1 + mu, t] = cp.asnumpy(correlator(base, lk, a)) - C[i, 0, t]
                for h in range(H):
                    a = cp.zeros((3, 16, 16, 16))
                    a[mu] = feat[..., h]
                    C[i, 1 + 3 + mu * H + h, t] = cp.asnumpy(correlator(base, lk, a)) - C[i, 0, t]
        print(f'base {base_steps}: collected cfg {cfg} ({i + 1}/{len(ids)})', flush=True)
    return C


def correlators(C, v, alpha, H):
    out = C[:, 0].copy()
    for mu in range(3):
        out += alpha * C[:, 1 + mu]
        for h in range(H):
            out += v[mu * H + h] * C[:, 1 + 3 + mu * H + h]
    return out


def risk_of(p, C, masses):
    cfg = {'amplitude_window': p['reference']['amplitude_window'],
           'score_window': p['reference']['score_window'],
           'geometry': p['geometry'],
           'covariance_shrinkage': p['risk']['covariance_shrinkage'],
           'amplitude_z_min': p['risk']['amplitude_z_min']}
    data = C[:, None, :]
    b = blocks(data, p['risk']['block_length'])
    idx = bootstrap_indices(len(b), p['risk']['bootstrap_samples'], p['seed'])
    return risk(b, [1.0], p['reference']['m0'], masses, idx, cfg)['risk']


def make_loss(C, p, masses, lam2):
    def loss(v):
        data = correlators(C, v, p['alpha'], p['hidden'])[:, None, :]
        b = blocks(data, p['risk']['block_length'])
        idx = bootstrap_indices(len(b), p['risk']['bootstrap_samples'], p['seed'])
        cfg = {'amplitude_window': p['reference']['amplitude_window'],
               'score_window': p['reference']['score_window'],
               'geometry': p['geometry'],
               'covariance_shrinkage': p['risk']['covariance_shrinkage'],
               'amplitude_z_min': p['risk']['amplitude_z_min']}
        try:
            value = risk(b, [1.0], p['reference']['m0'], masses, idx, cfg)['risk']
        except ValueError:
            value = 1e6
        return value + lam2 * float(np.mean(v ** 2)) + p['pos_weight'] * float(np.mean(np.minimum(v, 0) ** 2))

    return loss


def evaluate(p, ids, cache, W, v, base_steps):
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
            feat = cp.tanh(plaquettes(lk) @ cp.asarray(W.T))
            a = cp.full((3, 16, 16, 16), p['alpha'])
            for mu in range(3):
                for h in range(p['hidden']):
                    a[mu] += v[mu * p['hidden'] + h] * feat[..., h]
            out[i, t] = cp.asnumpy(correlator(base, lk, a))
        print(f'evaluated cfg {cfg} ({i + 1}/{len(ids)})', flush=True)
    return out


def coefficient_map(p, cfg, cache, W, v, t=0):
    import cupy as cp
    from pyquda_utils import core, io

    init_quda(p)
    gauge = io.readNERSCGauge(f"{p['ensemble']}/wilson_b6.{cfg}")
    lk = cp.asarray(gauge.lexico())[:3, t]
    feat = cp.tanh(plaquettes(lk) @ cp.asarray(W.T))
    a = cp.full((3, 16, 16, 16), p['alpha'])
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
    H, V = p['hidden'], p['v_max']

    grid, best = [], None
    for steps in p['base_grid']:
        cache_file = out / f'basis_m{steps}.npz'
        if cache_file.exists():
            z = np.load(cache_file)
            C_fit, C_dev = z['C_fit'], z['C_dev']
        else:
            C_fit = collect(p, fit_ids, cache, W, steps)
            C_dev = collect(p, devval_ids, cache, W, steps)
            np.savez_compressed(cache_file, C_fit=C_fit, C_dev=C_dev)
        for lam2 in p['l2_grid']:
            fit = minimize(make_loss(C_fit, p, masses, lam2), np.zeros(3 * H), method='Powell',
                           bounds=[(-V, V)] * (3 * H),
                           options={'maxiter': p['optimizer']['maxiter']})
            dev_risk = risk_of(p, correlators(C_dev, fit.x, p['alpha'], H), masses)
            grid.append({'base_steps': steps, 'lam2': lam2, 'dev_val_risk': dev_risk,
                         'v_max': float(np.max(fit.x)), 'v': fit.x.tolist()})
            print('GRID', json.dumps({k: grid[-1][k] for k in
                                      ('base_steps', 'lam2', 'dev_val_risk', 'v_max')}), flush=True)
            if best is None or dev_risk < best['dev_val_risk']:
                best = dict(grid[-1])

    v = np.asarray(best['v'])
    C_test = evaluate(p, test_ids, cache, W, v, best['base_steps'])
    C_base = evaluate(p, test_ids, cache, W, np.zeros(3 * H), best['base_steps'])
    a_map = coefficient_map(p, test_ids[0], cache, W, v)
    np.savez_compressed(out / 'data.npz', C_test=C_test, C_base=C_base,
                        q_learned=q_curve(C_test, p), q_base=q_curve(C_base, p),
                        a_map=a_map, W=W, v=v)
    summary = {'fit_ids': fit_ids, 'dev_val_ids': devval_ids, 'test_ids': test_ids,
               'hidden': H, 'v_max': V, 'grid': [{k: g[k] for k in
                                                 ('base_steps', 'lam2', 'dev_val_risk', 'v_max')} for g in grid],
               'best': {k: best[k] for k in ('base_steps', 'lam2', 'dev_val_risk')},
               'test_risk_learned': risk_of(p, C_test, masses),
               'test_risk_base': risk_of(p, C_base, masses),
               'test_ratio': risk_of(p, C_base, masses) / risk_of(p, C_test, masses)}
    (out / 'model.json').write_text(json.dumps({
        'features': p['features'], 'hidden': H, 'alpha': p['alpha'], 'base_steps': best['base_steps'],
        'base_alpha': p['base_alpha'], 'W': W.tolist(), 'v': v.tolist(),
        'm0': p['reference']['m0']}, indent=2) + '\n')
    (out / 'results.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('SUMMARY', json.dumps({k: summary[k] for k in
                                 ('test_risk_learned', 'test_risk_base', 'test_ratio')}), flush=True)


if __name__ == '__main__':
    main()
