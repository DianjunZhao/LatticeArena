"""Spatial link kernels for the static-potential pilot.

Links have shape (3, t, z, y, x, 3, 3); spatial axes are 1, 2, 3.
`build_kernel` is the submission interface: same rule for every time slice and
configuration, gauge covariant, no temporal links.
"""
import numpy as np


def _lib(a):
    if type(a).__module__.startswith('cupy'):
        import cupy
        return cupy
    return np


def shift(a, k, axis):
    """a[x + k] along axis (positive k moves up)."""
    return _lib(a).roll(a, -k, axis=axis)


def dagger(a):
    return a.swapaxes(-1, -2).conj()


def project(m):
    """Bidirectional polar projection onto SU(3): Q = M (M^dag M)^(-1/2), det -> 1.

    Gram-Schmidt only preserves left unitary transformations; the polar factor
    satisfies P(g M h) = g P(M) h for independent SU(3) g, h, which is the
    covariance the APE staple needs.
    """
    xp = _lib(m)
    m = xp.asarray(m, dtype=xp.complex128)
    herm = dagger(m) @ m
    ev, vec = xp.linalg.eigh(herm)
    scale = xp.max(ev)
    if not xp.isfinite(scale) or scale <= 0:
        raise ValueError('project: non-positive or non-finite metric')
    if xp.any(ev <= scale * 1e-12):
        raise ValueError('project: singular or near-singular link matrix')
    inv_sqrt = (vec * (1.0 / xp.sqrt(ev))[..., None, :]) @ dagger(vec)
    q = m @ inv_sqrt
    det = xp.linalg.det(q)
    return q * xp.exp(-1j * xp.arctan2(det.imag, det.real) / 3.0)[..., None, None]


def ape(links, alpha, steps):
    """APE smearing: F = Proj[(1-a)U + a/4 * sum(four staples)].

    With three spatial directions each link has four staples (two planes times
    two orientations), so the normalisation is 1/4, not 1/6. This changes the
    numeric meaning of ``alpha`` relative to the old pilot (v1); the old
    weight corresponds to alpha_new = 2*alpha/(3-alpha).
    """
    xp = _lib(links)
    u = links.copy()
    for _ in range(steps):
        new = xp.empty_like(u)
        for mu in range(3):
            staple = 0
            for nu in range(3):
                if nu == mu:
                    continue
                staple = staple + u[nu] @ shift(u[mu], 1, 3 - nu) @ dagger(shift(u[nu], 1, 3 - mu))
                staple = staple + dagger(shift(u[nu], -1, 3 - nu)) @ shift(u[mu], -1, 3 - nu) @ shift(shift(u[nu], 1, 3 - mu), -1, 3 - nu)
            new[mu] = project((1 - alpha) * u[mu] + alpha / 4 * staple)
        u = new
    return u


def build_kernel(spatial_links, parameters):
    return ape(spatial_links, parameters['alpha'], parameters['steps'])
