"""Fair cross-link operator-class experiment (todo C).

Small spatial lattice, shared real scalar coefficients, one deterministic
gauge-conditioned O_h operator rule. Class A uses H powers, class B adds the
nested BHB block. The target is Q = tanh(H/0.5) + eps * B H B; eps=0 is inside
class A, eps>0 needs the nested block. Train on train links, evaluate on
independent test links with the same coefficients.
"""
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

OUT = Path('results/optimize_gaussian/cpu_close_20261119_C')
L = 4
POWERS = range(0, 8)
EPSILONS = (0.0, 0.01, 0.05, 0.1)
SEEDS = (0, 1, 2)


def su3(rng, shape):
    a = rng.normal(size=(*shape, 3, 3)) + 1j * rng.normal(size=(*shape, 3, 3))
    q, _ = np.linalg.qr(a)
    return q / np.linalg.det(q)[..., None, None] ** (1 / 3)


def links(rng, epsilon):
    base = su3(rng, (L, L, L, 3))
    noise = su3(rng, (L, L, L, 3))
    out = np.empty_like(base)
    for d in range(3):
        out[..., d, :, :] = noise[..., d, :, :] @ base[..., d, :, :]
    return out * np.exp(1j * epsilon)


def H_of(u, x):
    h = np.zeros((3, 3), dtype=complex)
    for d in range(3):
        xm = list(x); xm[d] = (x[d] - 1) % L
        h += u[x][d] + u[tuple(xm)][d].conj().T - 2 * np.eye(3)
    h = (h + h.conj().T) / 2
    return h - np.trace(h) / 3 * np.eye(3)


def B_of(u, x):
    b = np.zeros((3, 3), dtype=complex)
    for d in range(3):
        for e in range(d + 1, 3):
            xd = list(x); xd[d] = (x[d] + 1) % L
            xe = list(x); xe[e] = (x[e] + 1) % L
            p = u[x][d] @ u[tuple(xd)][e] @ u[tuple(xe)][d].conj().T @ u[x][e].conj().T
            b += p
    b = (b + b.conj().T) / 2
    return b - np.trace(b) / 3 * np.eye(3)


def target(h, b, epsilon):
    g = b @ h @ b
    return h @ h + epsilon * (g + g.conj().T) / 2


def features_at(u, x, epsilon, augmented):
    h, b = H_of(u, x), B_of(u, x)
    g = b @ h @ b
    feats = [np.linalg.matrix_power(h, p) for p in POWERS]
    if augmented:
        feats += [g, g @ h, h @ g]
    design = np.stack([f.reshape(-1) for f in feats], axis=1)   # (81, d)
    return design, target(h, b, epsilon).reshape(-1)


def design(rng, u, epsilon, augmented, n):
    rows, targets = [], []
    for _ in range(n):
        x = tuple(int(rng.integers(0, L)) for _ in range(3))
        design, y = features_at(u, x, epsilon, augmented)
        rows.append(design)
        targets.append(y)
    return np.vstack(rows), np.concatenate(targets)


def fit(X, Y, method):
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    keep = sd > 1e-10
    mu, sd = mu[keep], sd[keep]
    Xs = np.column_stack([(X[:, keep] - mu) / sd, np.ones(len(X))])
    def objective(theta):
        r = (Xs @ theta - Y).ravel()
        return float(np.real(np.vdot(r, r)))
    d = Xs.shape[1]
    if method == 'oracle':
        theta, *_ = np.linalg.lstsq(Xs, Y, rcond=None)
        return theta, 1, True, (keep, mu, sd)
    result = minimize(objective, np.zeros(d), method=method,
                      bounds=[(-5.0, 5.0)] * d, options={'maxiter': 500})
    return result.x, int(result.nfev), bool(result.success), (keep, mu, sd)


def run(seed, epsilon, n_train=60, n_test=40):
    rng = np.random.default_rng(seed)
    train_links, test_links = links(rng, epsilon), links(rng, epsilon)
    out = {}
    for augmented in (False, True):
        X_train, Y_train = design(rng, train_links, epsilon, augmented, n_train)
        X_test, Y_test = design(rng, test_links, epsilon, augmented, n_test)
        rank = int(np.linalg.matrix_rank(X_train))
        klass = 'B_nested' if augmented else 'A_spectral'
        for method in ('SLSQP', 'Powell', 'oracle'):
            t0 = time.perf_counter()
            theta, nfev, success, prep = fit(X_train, Y_train, method)
            elapsed = time.perf_counter() - t0
            keep, mu, sd = prep
            pred = np.column_stack([(X_test[:, keep] - mu) / sd, np.ones(len(X_test))]) @ theta
            error = float(np.linalg.norm(pred - Y_test) / (np.linalg.norm(Y_test) + 1e-12))
            Xs = np.column_stack([(X_train[:, prep[0]] - prep[1]) / prep[2],
                                  np.ones(len(X_train))])
            gradient = float(np.linalg.norm(2 * Xs.T @ (Xs @ theta - Y_train)))
            out[f'{klass}/{method}'] = {'test_error': error, 'nfev': nfev,
                                        'success': success, 'seconds': elapsed,
                                        'dimension': int(X_train.shape[1]), 'rank': rank,
                                        'gradient_norm': gradient,
                                        'feasible': bool(np.all(np.abs(theta) <= 5.0 + 1e-9))}
    return out


def attributes():
    rng = np.random.default_rng(1)
    u = links(rng, 0.1)
    h, b = H_of(u, (1, 2, 1)), B_of(u, (1, 2, 1))
    q = target(h, b, 0.1)
    return {'h_hermitian': float(np.linalg.norm(h - h.conj().T)),
            'b_hermitian': float(np.linalg.norm(b - b.conj().T)),
            'q_hermitian': float(np.linalg.norm(q - q.conj().T)),
            'note': 'the target Q=H^2+eps*BHB is Hermitian but not projected traceless'}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    result = {'schema': 'optgauss-crosslink-fair-v1', 'lattice': [L, L, L],
              'attributes': attributes(), 'rows': {}}
    for epsilon in EPSILONS:
        for seed in SEEDS:
            result['rows'][f'eps{epsilon}/seed{seed}'] = run(seed, epsilon)
            print(f'eps{epsilon} seed{seed}',
                  {k: round(v['test_error'], 6) for k, v in
                   result['rows'][f'eps{epsilon}/seed{seed}'].items()})
    (OUT / 'crosslink_fair.json').write_text(json.dumps(result, indent=2) + '\n')
    print('wrote', OUT)


if __name__ == '__main__':
    main()
