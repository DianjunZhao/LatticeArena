import numpy as np
import pytest

from tasks.wilson_loop.kernels import ape, build_kernel
from tasks.wilson_loop.measure import loops
from tasks.wilson_loop.statistics import blocks, bootstrap_indices, potential, risk


def random_su3(rng, shape):
    a = rng.normal(size=(*shape, 3, 3)) + 1j * rng.normal(size=(*shape, 3, 3))
    q, _ = np.linalg.qr(a)
    return q / np.linalg.det(q)[..., None, None] ** (1 / 3)


def cold(latt):
    links = np.broadcast_to(np.eye(3, dtype=complex), (3, *latt, 3, 3)).copy()
    return links, np.broadcast_to(np.eye(3, dtype=complex), (*latt, 3, 3)).copy()


P = {'r_values': [1, 2], 't_values': [1, 2, 3]}


def test_cold_field_gives_unit_loops():
    links, temporal = cold((4, 4, 4, 4))
    w = loops(links, temporal, P)
    np.testing.assert_allclose(w, 1.0, atol=1e-13)


def test_gauge_covariance():
    rng = np.random.default_rng(3)
    latt = (4, 4, 4, 4)
    links = random_su3(rng, (3, *latt))
    temporal = random_su3(rng, latt)
    g = random_su3(rng, latt)
    gp = [np.roll(g, -1, axis=axis) for axis in (0, 1, 2, 3)]
    gt = g.swapaxes(-1, -2).conj()
    links_g = np.stack([g @ links[d] @ np.roll(gt, -1, axis=3 - d) for d in range(3)])
    temporal_g = g @ temporal @ np.roll(gt, -1, axis=0)
    np.testing.assert_allclose(loops(links_g, temporal_g, P), loops(links, temporal, P), rtol=1e-12)


def brute(links, temporal, R, T, d):
    lt, lz, ly, lx = temporal.shape[:4]
    dims = [lx, ly, lz]
    total = 0.0
    for t0 in range(lt):
        for z in range(lz):
            for y in range(ly):
                for x in range(lx):
                    c = [x, y, z]
                    def prod(c0, tt):
                        out = np.eye(3, dtype=complex)
                        for r in range(R):
                            cc = list(c0)
                            cc[d] = (cc[d] + r) % dims[d]
                            out = out @ links[d][tt, cc[2], cc[1], cc[0]]
                        return out
                    def time_line(c0, tt):
                        out = np.eye(3, dtype=complex)
                        for t in range(T):
                            out = out @ temporal[(tt + t) % lt, c0[2], c0[1], c0[0]]
                        return out
                    cR = list(c)
                    cR[d] = (cR[d] + R) % dims[d]
                    w = prod(c, t0) @ time_line(cR, t0) @ prod(c, (t0 + T) % lt).conj().T @ time_line(c, t0).conj().T
                    total += np.trace(w).real
    return total / (3 * lt * lz * ly * lx)


def test_loops_match_brute_force():
    rng = np.random.default_rng(7)
    latt = (4, 4, 4, 4)
    links = random_su3(rng, (3, *latt))
    temporal = random_su3(rng, latt)
    w = loops(links, temporal, P)
    for i, R in enumerate(P['r_values']):
        for j, T in enumerate(P['t_values']):
            reference = sum(brute(links, temporal, R, T, d) for d in range(3)) / 3
            assert w[i, j] == pytest.approx(reference, rel=1e-12)


def test_ape_keeps_links_unitary():
    rng = np.random.default_rng(5)
    links = random_su3(rng, (3, 4, 4, 4, 4))
    smeared = ape(links, 0.5, 3)
    eye = np.einsum('...ij,...kj->...ik', smeared.conj(), smeared)
    np.testing.assert_allclose(eye, np.broadcast_to(np.eye(3), eye.shape), atol=1e-10)
    det = np.linalg.det(smeared)
    np.testing.assert_allclose(det, 1.0, atol=1e-10)


def test_ape_limits():
    rng = np.random.default_rng(11)
    links = random_su3(rng, (3, 4, 4, 4, 4))
    np.testing.assert_allclose(build_kernel(links, {'alpha': 0.5, 'steps': 0}), links)
    np.testing.assert_allclose(ape(links, 0.0, 3), links)


def test_potential_recovers_known_slopes():
    v = np.array([0.4, 0.55, 0.7])
    t = np.arange(0, 9)
    w = np.exp(-np.outer(v, t))[None]
    np.testing.assert_allclose(potential(w, [4, 5, 6, 7], list(t))[0], v, rtol=1e-12)


def test_risk_penalizes_bias_and_noise():
    v = np.array([0.5, 0.6, 0.7])
    t = np.arange(1, 9)
    exact = np.exp(-np.outer(v, t))
    data = np.repeat(exact[None], 12, axis=0)[:, None]
    idx = bootstrap_indices(6, 50, 1)
    b = blocks(data, 2)
    tv = list(range(1, 9))
    windows = [[4, 5, 6], [4, 5, 6, 7], [5, 6, 7, 8]]
    base = risk(b, idx, windows, tv, v)
    shift_t = np.exp(-0.02 * np.arange(8))
    worse = risk(b * shift_t, idx, windows, tv, v)
    assert base['risk'] < 1e-10
    assert worse['risk'] > base['risk']
