"""Matched cross-link operator-class diagnostic (optimize package C).

This is a constructive expressivity test, not a test of learning advantage:
the target contains BHB and class B contains that feature explicitly.
"""
import hashlib
import json
import time
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import lsq_linear, minimize

OUT = Path('results/optimize_gaussian/cpu_close_20261119_C_matched')
L = 3
POWERS = range(0, 8)
EPSILONS = (0.0, 0.01, 0.05, 0.1)
SEEDS = (0, 1, 2)
COEFFICIENT_BOUNDS = (-5.0, 5.0)


def su3(rng, shape):
    a = rng.normal(size=(*shape, 3, 3)) + 1j * rng.normal(size=(*shape, 3, 3))
    q, _ = np.linalg.qr(a)
    return q / np.linalg.det(q)[..., None, None] ** (1 / 3)


def links(rng):
    base = su3(rng, (L, L, L, 3))
    noise = su3(rng, (L, L, L, 3))
    out = np.empty_like(base)
    for d in range(3):
        out[..., d, :, :] = noise[..., d, :, :] @ base[..., d, :, :]
    return out


def _step(x, direction, sign):
    y = list(x)
    y[direction] = (y[direction] + sign) % L
    return tuple(y)


def _oriented_link(u, x, direction, sign):
    if sign > 0:
        return u[x][direction]
    return u[_step(x, direction, -1)][direction].conj().T


def B_of(u, x):
    """Traceless Hermitian clover scalar, averaged over all cubic orientations."""
    b = np.zeros((3, 3), dtype=complex)
    for d in range(3):
        for e in range(d + 1, 3):
            for sd in (-1, 1):
                for se in (-1, 1):
                    x1 = _step(x, d, sd)
                    x2 = _step(x1, e, se)
                    x3 = _step(x2, d, -sd)
                    loop = (_oriented_link(u, x, d, sd)
                            @ _oriented_link(u, x1, e, se)
                            @ _oriented_link(u, x2, d, -sd)
                            @ _oriented_link(u, x3, e, -se))
                    b += loop
    b /= 12.0
    b = (b + b.conj().T) / 2
    return b - np.trace(b) / 3 * np.eye(3)


def build_operators(u):
    """Build full spatial diffusion H and local clover multiplication B."""
    volume = L ** 3
    size = 3 * volume
    h = np.zeros((size, size), dtype=complex)
    b = np.zeros_like(h)
    for x in np.ndindex((L, L, L)):
        ix = np.ravel_multi_index(x, (L, L, L))
        rows = np.arange(3 * ix, 3 * ix + 3)
        for d in range(3):
            xp = _step(x, d, 1)
            xm = _step(x, d, -1)
            ip = np.ravel_multi_index(xp, (L, L, L))
            im = np.ravel_multi_index(xm, (L, L, L))
            cols_p = np.arange(3 * ip, 3 * ip + 3)
            cols_m = np.arange(3 * im, 3 * im + 3)
            h[np.ix_(rows, cols_p)] += u[x][d]
            h[np.ix_(rows, cols_m)] += u[xm][d].conj().T
            h[np.ix_(rows, rows)] -= 2 * np.eye(3)
        b[np.ix_(rows, rows)] = B_of(u, x)
    return h, b


def target(h, b, epsilon):
    g = b @ h @ b
    return h @ h + epsilon * (g + g.conj().T) / 2


def operator_basis(h, b, epsilon, augmented):
    g = b @ h @ b
    feats = [np.linalg.matrix_power(h, p) for p in POWERS]
    if augmented:
        feats += [g, (g @ h + h @ g) / 2]
    return feats, target(h, b, epsilon)


def _probe_matrix(indices):
    return np.eye(3 * L ** 3, dtype=complex)[:, np.asarray(indices, dtype=int)]


def design(h, b, epsilon, augmented, probe_indices):
    feats, q = operator_basis(h, b, epsilon, augmented)
    probes = _probe_matrix(probe_indices)
    projected = [probes.conj().T @ f @ probes for f in feats]
    x = np.stack([f.reshape(-1) for f in projected], axis=1)
    y = (probes.conj().T @ q @ probes).reshape(-1)
    return x, y


def design_ensembles(operators, epsilon, augmented, probes):
    samples = [design(h, b, epsilon, augmented, indices)
               for (h, b), indices in zip(operators, probes)]
    return (np.vstack([x for x, _ in samples]),
            np.concatenate([y for _, y in samples]))


def _real_system(X, Y):
    # Coefficients are real. Realifying the equations prevents a complex
    # least-squares oracle from solving a larger, inadmissible model.
    Xr = np.concatenate((X.real, X.imag), axis=0)
    Yr = np.concatenate((Y.real, Y.imag), axis=0)
    return Xr, Yr


def _relative_objective(X, Y, coefficients):
    residual = X @ coefficients - Y
    denominator = float(np.vdot(Y, Y).real)
    return float(np.vdot(residual, residual).real / max(denominator, np.finfo(float).tiny))


def fit(X, Y, method):
    scales = np.sqrt(np.mean(np.abs(X) ** 2, axis=0))
    scales = np.where(scales > 1e-12, scales, 1.0)
    Xs = X / scales
    Xr, Yr = _real_system(Xs, Y)
    lower, upper = COEFFICIENT_BOUNDS
    bounds = (lower * scales, upper * scales)
    target_norm = float(Yr @ Yr)
    target_norm = max(target_norm, np.finfo(float).tiny)
    if method == 'oracle':
        solution, *_ = np.linalg.lstsq(Xr, Yr, rcond=None)
        original = solution / scales
        if np.all(original >= lower - 1e-10) and np.all(original <= upper + 1e-10):
            return original, 1, True, (scales,)
        result = lsq_linear(Xr, Yr, bounds=bounds, tol=1e-12,
                            max_iter=10000, lsmr_tol='auto')
        return result.x / scales, int(result.nit or 0), bool(result.success), (scales,)

    def objective(theta):
        residual = Xr @ theta - Yr
        return float((residual @ residual) / target_norm)

    def gradient(theta):
        return 2 * Xr.T @ (Xr @ theta - Yr) / target_norm

    result = minimize(objective, np.zeros(Xr.shape[1]), method=method,
                      bounds=list(zip(*bounds)),
                      jac=gradient if method == 'SLSQP' else None,
                      options={'maxiter': 5000, 'ftol': 1e-12})
    return result.x / scales, int(result.nfev), bool(result.success), (scales,)


def run(seed, epsilon, n_train=20, n_test=12,
        n_train_configurations=3, n_test_configurations=2):
    rng = np.random.default_rng(seed)
    train_links = [links(rng) for _ in range(n_train_configurations)]
    test_links = [links(rng) for _ in range(n_test_configurations)]
    train_operators = [build_operators(u) for u in train_links]
    test_operators = [build_operators(u) for u in test_links]
    # Point-source/color basis probes retain both diagonal and off-diagonal
    # matrix elements. The same probe sets are evaluated for both classes.
    train_probes = [rng.choice(3 * L ** 3, size=n_train, replace=False).tolist()
                    for _ in range(n_train_configurations)]
    test_probes = [rng.choice(3 * L ** 3, size=n_test, replace=False).tolist()
                   for _ in range(n_test_configurations)]
    out = {'probe_hashes': {
                'train': [hashlib.sha256(np.asarray(x, dtype=np.int64).tobytes()).hexdigest()
                          for x in train_probes],
                'test': [hashlib.sha256(np.asarray(x, dtype=np.int64).tobytes()).hexdigest()
                         for x in test_probes]},
           'train_probe_indices': train_probes, 'test_probe_indices': test_probes,
           'train_link_hashes': [hashlib.sha256(u.tobytes()).hexdigest() for u in train_links],
           'test_link_hashes': [hashlib.sha256(u.tobytes()).hexdigest() for u in test_links],
           'n_train_configurations': n_train_configurations,
           'n_test_configurations': n_test_configurations,
           'classes': {}}
    for augmented in (False, True):
        X_train, Y_train = design_ensembles(train_operators, epsilon, augmented, train_probes)
        X_test, Y_test = design_ensembles(test_operators, epsilon, augmented, test_probes)
        rank = int(np.linalg.matrix_rank(_real_system(X_train, Y_train)[0]))
        klass = 'B_nested' if augmented else 'A_spectral'
        out['classes'][klass] = {}
        for method in ('SLSQP', 'Powell', 'oracle'):
            t0 = time.perf_counter()
            theta, nfev, success, prep = fit(X_train, Y_train, method)
            elapsed = time.perf_counter() - t0
            scales, = prep
            error = float(np.linalg.norm(X_test @ theta - Y_test) /
                          (np.linalg.norm(Y_test) + 1e-12))
            Xtr, Ytr = _real_system(X_train, Y_train)
            z = scales * theta
            # Match the variable scaling used by fit, and report the box
            # projected gradient mapping (a KKT residual) at the solution.
            Xtrain_scaled = X_train / scales
            Xr_scaled, Yr_scaled = _real_system(Xtrain_scaled, Y_train)
            grad_z = 2 * Xr_scaled.T @ (Xr_scaled @ z - Yr_scaled) / max(
                float(Yr_scaled @ Yr_scaled), np.finfo(float).tiny)
            lo, hi = COEFFICIENT_BOUNDS
            projected = z - np.clip(z - grad_z, lo * scales, hi * scales)
            out['classes'][klass][method] = {
                'test_error': error, 'nfev_or_iterations': nfev,
                'success': success, 'seconds': elapsed,
                'dimension': int(theta.size), 'rank_realified_design': rank,
                'projected_gradient_norm': float(np.linalg.norm(projected)),
                'relative_train_objective': _relative_objective(X_train, Y_train, theta),
                'feature_scales': [float(x) for x in scales],
                'coefficients': [float(x) for x in theta],
                'feasible': bool(np.all(np.abs(theta) <= max(abs(v) for v in COEFFICIENT_BOUNDS) + 1e-9)),
                'coefficient_domain': list(COEFFICIENT_BOUNDS),
            }
    return out


def gauge_transform(u, g):
    transformed = np.empty_like(u)
    for x in np.ndindex((L, L, L)):
        for d in range(3):
            transformed[x][d] = g[x] @ u[x][d] @ g[_step(x, d, 1)].conj().T
    return transformed


def attributes():
    rng = np.random.default_rng(1)
    u = links(rng)
    g = su3(rng, (L, L, L))
    ug = gauge_transform(u, g)
    h, b = build_operators(u)
    hg, bg = build_operators(ug)
    d = np.zeros_like(h)
    for x in np.ndindex((L, L, L)):
        ix = np.ravel_multi_index(x, (L, L, L))
        rows = np.arange(3 * ix, 3 * ix + 3)
        d[np.ix_(rows, rows)] = g[x]
    q, qg = target(h, b, 0.1), target(hg, bg, 0.1)
    return {
        'h_hermitian': float(np.linalg.norm(h - h.conj().T)),
        'b_hermitian': float(np.linalg.norm(b - b.conj().T)),
        'q_hermitian': float(np.linalg.norm(q - q.conj().T)),
        'link_su3_determinant_max': float(max(abs(np.linalg.det(u[x][direction]) - 1)
                                                for x in np.ndindex((L, L, L))
                                                for direction in range(3))),
        'gauge_covariance_h': float(np.linalg.norm(hg - d @ h @ d.conj().T)),
        'gauge_covariance_b': float(np.linalg.norm(bg - d @ b @ d.conj().T)),
        'gauge_covariance_q': float(np.linalg.norm(qg - d @ q @ d.conj().T)),
        'b_definition': 'traceless Hermitian clover scalar averaged over all six planes and four orientations',
        'h_definition': 'full spatial covariant Laplacian on the periodic color-position space',
        'target_definition': 'Q=H^2+epsilon*BHB',
    }


def _write_plot(result, path):
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    colors = {'A_spectral': '#315a8a', 'B_nested': '#b15b32'}
    markers = {'oracle': 'o', 'SLSQP': 's', 'Powell': '^'}
    for klass in ('A_spectral', 'B_nested'):
        for method in ('oracle', 'SLSQP', 'Powell'):
            means, errors = [], []
            for eps in EPSILONS:
                samples = [result['rows'][f'eps{eps}/seed{s}']['classes'][klass][method]['test_error']
                           for s in SEEDS]
                means.append(float(np.mean(samples)))
                errors.append(float(np.std(samples, ddof=1) / np.sqrt(len(samples))))
            ax.errorbar(EPSILONS, means, yerr=errors, marker=markers[method],
                        color=colors[klass], linestyle={'oracle': '-', 'SLSQP': '--', 'Powell': ':'}[method],
                        capsize=3, label=f'{klass} / {method}')
    ax.set(xlabel='epsilon in the constructed target', ylabel='relative error on independent test links',
           title='Matched point/color probes and real bounded coefficients; constructive expressivity test')
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main():
    if OUT.exists() and any(OUT.iterdir()):
        raise FileExistsError(f'{OUT} already contains results; choose a new output directory')
    OUT.mkdir(parents=True, exist_ok=True)
    result = {'schema': 'optgauss-crosslink-matched-v2', 'lattice': [L, L, L],
              'design': {'n_train_point_color_probes_per_configuration': 20,
                         'n_test_point_color_probes_per_configuration': 12,
                         'n_train_configurations': 3, 'n_test_configurations': 2,
                         'same_point_color_probes_across_classes': True,
                         'independent_train_test_links': True,
                         'coefficients': 'shared real scalars in [-5,5]',
                         'oracle': 'bounded real least squares on realified complex equations',
                         'operator': 'full 3D covariant diffusion matrix H and clover multiplication B',
                         'features_A': 'H^0,...,H^7',
                         'features_B': 'class A plus BHB and {BHB,H}/2'},
              'attributes': attributes(), 'rows': {}}
    for epsilon in EPSILONS:
        for seed in SEEDS:
            row = run(seed, epsilon)
            result['rows'][f'eps{epsilon}/seed{seed}'] = row
            print(f'eps={epsilon} seed={seed}', {
                klass: round(row['classes'][klass]['oracle']['test_error'], 6)
                for klass in ('A_spectral', 'B_nested')})
    (OUT / 'crosslink_fair.json').write_text(json.dumps(result, indent=2) + '\n')
    _write_plot(result, OUT / 'fig_crosslink_fair.png')
    print('wrote', OUT)


if __name__ == '__main__':
    main()
