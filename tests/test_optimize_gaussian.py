import numpy as np
import pytest

from tasks.optimize_gaussian.features import dagger, directional_features, plaquettes, shift
from tasks.optimize_gaussian.kernels import apply_kernel, correlator
from tasks.optimize_gaussian.submission import build_kernel
from tasks.optimize_gaussian.train import features, gaussian


def su3(rng, shape):
    a = rng.normal(size=(*shape, 3, 3)) + 1j * rng.normal(size=(*shape, 3, 3))
    q, _ = np.linalg.qr(a)
    q[..., :, 0] /= np.linalg.det(q)[..., None]
    return q


def gauge_links(u, g):
    return np.stack([g @ u[d] @ dagger(shift(g, 1, d)) for d in range(3)])


def gauge_field(f, g):
    return np.einsum('...ij,...jn->...in', g, f)


def params(seed=0, steps=1, hidden=4):
    rng = np.random.default_rng(seed)
    return {'W': rng.normal(size=(hidden, 2)).tolist(),
            'theta': rng.normal(size=1 + hidden).tolist(),
            'steps': steps, 'alpha': 0.09090909}


def field(rng, latt=(4, 4, 4)):
    return rng.normal(size=(*latt, 3, 2)) + 1j * rng.normal(size=(*latt, 3, 2))


def test_shift_matches_roll_and_is_periodic():
    rng = np.random.default_rng(1)
    a = rng.normal(size=(4, 4, 4))
    for d, axis in ((0, 2), (1, 1), (2, 0)):
        np.testing.assert_array_equal(shift(a, 1, d), np.roll(a, -1, axis=axis))
        np.testing.assert_array_equal(shift(a, -1, d), np.roll(a, 1, axis=axis))
        np.testing.assert_array_equal(shift(shift(a, 1, d), -1, d), a)


def test_plaquettes_are_closed_and_gauge_invariant():
    rng = np.random.default_rng(2)
    latt = (4, 4, 4)
    u = su3(rng, (3, *latt))
    cold = np.broadcast_to(np.eye(3, dtype=complex), (3, *latt, 3, 3)).copy()
    np.testing.assert_allclose(plaquettes(cold), 1.0, atol=1e-13)
    g = su3(rng, latt)
    np.testing.assert_allclose(plaquettes(gauge_links(u, g)), plaquettes(u), atol=1e-12)
    # the loop must be closed: U_mu(x) U_nu(x+mu) U_mu^dag(x+nu) U_nu^dag(x)
    mu, nu = 0, 1
    loop = u[mu] @ shift(u[nu], 1, mu) @ dagger(shift(u[mu], 1, nu)) @ dagger(u[nu])
    np.testing.assert_allclose(plaquettes(u)[..., 0],
                               np.trace(loop, axis1=-2, axis2=-1).real / 3, atol=1e-12)


def test_kernel_is_hermitian_with_distinct_fields():
    rng = np.random.default_rng(3)
    u = su3(rng, (3, 4, 4, 4))
    f, g = field(rng), field(rng)
    a = rng.normal(size=(3, 4, 4, 4))
    np.testing.assert_allclose(np.vdot(g, apply_kernel(f, u, a)),
                               np.vdot(apply_kernel(g, u, a), f), atol=1e-12)


def test_kernel_is_gauge_covariant():
    rng = np.random.default_rng(4)
    latt = (4, 4, 4)
    u = su3(rng, (3, *latt))
    g = su3(rng, latt)
    f = field(rng)
    a = rng.normal(size=(3, *latt))
    np.testing.assert_allclose(apply_kernel(gauge_field(f, g), gauge_links(u, g), a),
                               gauge_field(apply_kernel(f, u, a), g), atol=1e-12)
    p = params(4, steps=2)
    np.testing.assert_allclose(build_kernel(gauge_links(u, g), p).apply(gauge_field(f, g)),
                               gauge_field(build_kernel(u, p).apply(f), g), atol=1e-12)


def test_kernel_cubic_symmetry():
    rng = np.random.default_rng(5)
    latt = (4, 4, 4)
    u = su3(rng, (3, *latt))
    f = field(rng)
    p = params(5, steps=1)
    swapped_u = u[[2, 1, 0]].transpose(0, 3, 2, 1, 4, 5)
    swapped_f = f.transpose(2, 1, 0, 3, 4)
    np.testing.assert_allclose(build_kernel(swapped_u, p).apply(swapped_f),
                               build_kernel(u, p).apply(f).transpose(2, 1, 0, 3, 4), atol=1e-12)


def test_linear_response_matches_direct_correlator():
    rng = np.random.default_rng(6)
    latt = (4, 4, 4)
    u = su3(rng, (3, *latt))
    f = field(rng)
    p = params(6, steps=2, hidden=4)
    W = np.asarray(p['W'])
    hidden = W.shape[0]
    base = gaussian(f, u, p['steps'], p['alpha'])
    zero = np.zeros((3, *latt))
    C0 = correlator(base, u, zero)
    Dc = correlator(base, u, np.ones((3, *latt))) - C0
    phi = features(u, W)
    Dh = [correlator(base, u, phi[:, ..., h]) - C0 for h in range(hidden)]
    theta = rng.normal(size=1 + hidden)
    a = np.full((3, *latt), theta[0])
    for h in range(hidden):
        a += theta[1 + h] * phi[:, ..., h]
    direct = correlator(base, u, a)
    linear = C0 + theta[0] * Dc + sum(theta[1 + h] * Dh[h] for h in range(hidden))
    np.testing.assert_allclose(linear, direct, atol=1e-11)


def test_features_are_gauge_invariant_and_zero_mean():
    rng = np.random.default_rng(7)
    latt = (4, 4, 4)
    u = su3(rng, (3, *latt))
    g = su3(rng, latt)
    W = np.asarray(params(7, hidden=3)['W'])
    np.testing.assert_allclose(features(gauge_links(u, g), W), features(u, W), atol=1e-11)
    phi = features(u, W)
    np.testing.assert_allclose(phi.mean(axis=(1, 2, 3)), 0.0, atol=1e-11)


def test_a1p_directional_pair_is_exchange_symmetric():
    rng = np.random.default_rng(8)
    latt = (4, 4, 4)
    u = su3(rng, (3, *latt))
    swapped = u[[0, 2, 1]].transpose(0, 2, 1, 3, 4, 5)
    f = directional_features(u).transpose(0, 2, 1, 3, 4)
    s = directional_features(swapped)
    # site axes are (z, y, x), so swapping y and z also transposes sites;
    # direction x sees (xy, xz), and the symmetric (sum, product) pair survives.
    np.testing.assert_allclose(f[0], s[0], atol=1e-12)
    np.testing.assert_allclose(f[1], s[2], atol=1e-12)
    np.testing.assert_allclose(f[2], s[1], atol=1e-12)


def test_invalid_shapes_are_rejected():
    with pytest.raises(Exception):
        apply_kernel(np.zeros((4, 4, 4, 3, 2)), np.zeros((2, 4, 4, 4, 3, 3)), np.zeros((3, 4, 4, 4)))


def test_basis_cache_rejects_identity_change(tmp_path):
    from tasks.optimize_gaussian.train import basis_key, load_basis, save_basis
    p = {'base_steps': 8, 'base_alpha': 0.09, 'hidden': 2}
    W = np.zeros((2, 2))
    key = basis_key(p, 7, W, [0, 1], [2, 3])
    save_basis(tmp_path / 'b.npz', key, np.zeros((2, 3, 4)), np.zeros((2, 3, 4)))
    load_basis(tmp_path / 'b.npz', key)
    for mutated in (basis_key(p, 8, W, [0, 1], [2, 3]),
                    basis_key(p, 7, W + 1, [0, 1], [2, 3]),
                    basis_key(p, 7, W, [0, 1], [2, 4]),
                    basis_key({**p, 'base_steps': 9}, 7, W, [0, 1], [2, 3])):
        with pytest.raises(ValueError, match='does not match'):
            load_basis(tmp_path / 'b.npz', mutated)
    np.savez(tmp_path / 'legacy.npz', C_fit=np.zeros(1), C_dev=np.zeros(1))
    with pytest.raises(ValueError, match='no identity record'):
        load_basis(tmp_path / 'legacy.npz', key)
