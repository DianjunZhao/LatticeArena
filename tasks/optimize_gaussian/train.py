"""Train a gauge-invariant learned smear on cached point propagators (smoke scale)."""
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from .features import plaquettes
from .kernels import correlator


def protocol():
    return json.loads((Path(__file__).parent / 'protocol.json').read_text())


def model_space(p):
    rng = np.random.default_rng(p['seed'])
    return rng.normal(size=(p['hidden'], len(p['features']))) * 0.5


def collect(p, ids, cache, W):
    import cupy as cp
    from pyquda_utils import core, io

    if not getattr(collect, 'ready', False):
        core.init([1, 1, 1, 1], p['geometry'], resource_path='.cache/quda')
        collect.ready = True
    latt = core.LatticeInfo(p['geometry'], -1, 1.0)
    H, n = p['hidden'], len(ids)
    C = np.zeros((n, 1 + 3 + 3 * H, 16))
    for i, cfg in enumerate(ids):
        gauge = io.readNERSCGauge(f"{p['ensemble']}/wilson_b6.{cfg}")
        links = cp.asarray(gauge.lexico())[:3]
        prop = core.LatticePropagator(
            latt, cp.asarray(np.load(f".cache/pion_projection/propagators/{cache[cfg]}.npy")))
        fields = cp.asarray(prop.lexico())
        for t in range(16):
            f = fields[t].transpose(0, 1, 2, 5, 3, 4, 6).reshape(16, 16, 16, 3, 48)
            lk = links[:, t]
            feat = cp.tanh(plaquettes(lk) @ cp.asarray(W.T))
            zero = cp.zeros((3, 16, 16, 16))
            C[i, 0, t] = cp.asnumpy(correlator(f, lk, zero))
            for mu in range(3):
                a = cp.zeros((3, 16, 16, 16))
                a[mu] = 1
                C[i, 1 + mu, t] = cp.asnumpy(correlator(f, lk, a)) - C[i, 0, t]
                for h in range(H):
                    a = cp.zeros((3, 16, 16, 16))
                    a[mu] = feat[..., h]
                    C[i, 1 + 3 + mu * H + h, t] = cp.asnumpy(correlator(f, lk, a)) - C[i, 0, t]
        print(f'collected cfg {cfg} ({i + 1}/{n})', flush=True)
    return C


def mean_correlator(C, v, alpha, H):
    out = C[:, 0].mean(0).copy()
    for mu in range(3):
        out += alpha * C[:, 1 + mu].mean(0)
        for h in range(H):
            out += v[mu * H + h] * C[:, 1 + 3 + mu * H + h].mean(0)
    return out


def loss(v, C, p):
    ref = p['reference']
    m0 = ref['m0']
    c = mean_correlator(C, v, p['alpha'], p['hidden'])
    t = np.arange(16, dtype=float)
    f0 = np.exp(-m0 * t) + np.exp(-m0 * (16 - t))
    late, early = ref['amplitude_window'], ref['score_window']
    A = c[late] @ f0[late] / (f0[late] @ f0[late])
    q = c[early] / (A * f0[early])
    return float(np.mean((q - 1) ** 2))


def main():
    import sys
    p = protocol()
    if len(sys.argv) > 1:
        p['train_configs'] = int(sys.argv[1])
    if len(sys.argv) > 2:
        p['output'] = sys.argv[2]
    if len(sys.argv) > 3:
        p['hidden'] = int(sys.argv[3])
    out = Path(p['output'])
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(Path(p['cache_manifest']).read_text())
    val_manifest = json.loads(Path(p['validation_manifest']).read_text())
    cache = {r['id']: r['cache_key'] for r in manifest['records'] + val_manifest['records']}
    train = list(range(p['development'][0], p['development'][0] + p['train_configs']))
    valid = list(range(p['validation'][0], p['validation'][0] + p['validation_configs']))
    W = model_space(p)

    C = collect(p, train, cache, W)
    np.savez_compressed(out / 'basis.npz', C=C, W=W, ids=train)
    curve = [loss(np.zeros(3 * p['hidden']), C, p)]
    print(f'initial loss {curve[0]:.6g}', flush=True)
    fit = minimize(loss, np.zeros(3 * p['hidden']), args=(C, p), method='Powell',
                   options={'maxiter': p['optimizer']['maxiter']})
    print(f'final loss {fit.fun:.6g}  nfev={fit.nfev}', flush=True)

    v = fit.x
    Cv = collect(p, valid, cache, W)
    summary = {'train_ids': train, 'validation_ids': valid, 'hidden': p['hidden'],
               'alpha': p['alpha'], 'initial_loss': curve[0], 'final_loss': float(fit.fun),
               'nfev': int(fit.nfev), 'weights': v.tolist(),
               'gaussian_validation_loss': loss(np.zeros(3 * p['hidden']), Cv, p),
               'learned_validation_loss': loss(v, Cv, p)}
    (out / 'model.json').write_text(json.dumps({
        'features': p['features'], 'hidden': p['hidden'], 'alpha': p['alpha'],
        'W': W.tolist(), 'v': v.tolist(), 'm0': p['reference']['m0']}, indent=2) + '\n')
    (out / 'smoke_results.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('SMOKE', json.dumps({k: summary[k] for k in
                               ('initial_loss', 'final_loss', 'gaussian_validation_loss',
                                'learned_validation_loss')}))


if __name__ == '__main__':
    main()
