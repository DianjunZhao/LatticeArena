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
    """Gram-Schmidt reunitarization of the columns, then det -> 1 (analytic 3x3)."""
    xp = _lib(m)
    q = []
    for i in range(3):
        v = m[..., :, i]
        for u in q:
            v = v - (u.conj() * v).sum(-1)[..., None] * u
        v = v / xp.sqrt((v.conj() * v).real.sum(-1))[..., None]
        q.append(v)
    x = xp.stack(q, axis=-1)
    det = (x[..., 0, 0] * (x[..., 1, 1] * x[..., 2, 2] - x[..., 1, 2] * x[..., 2, 1])
           - x[..., 0, 1] * (x[..., 1, 0] * x[..., 2, 2] - x[..., 1, 2] * x[..., 2, 0])
           + x[..., 0, 2] * (x[..., 1, 0] * x[..., 2, 1] - x[..., 1, 1] * x[..., 2, 0]))
    return x / (det ** (1 / 3))[..., None, None]


def ape(links, alpha, steps):
    """APE smearing with projection: F = Proj[(1-a)U + a/6 * sum(staple)]."""
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
            new[mu] = project((1 - alpha) * u[mu] + alpha / 6 * staple)
        u = new
    return u


def build_kernel(spatial_links, parameters):
    return ape(spatial_links, parameters['alpha'], parameters['steps'])
