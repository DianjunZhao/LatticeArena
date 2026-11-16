"""Gauge-invariant, time-local features used to modulate the hopping coefficients."""
import numpy as np


def _lib(a):
    if type(a).__module__.startswith('cupy'):
        import cupy
        return cupy
    return np


def shift(a, k, d):
    """a[x + k*mu_d] for links/fields whose spatial axes are (z, y, x) = (0, 1, 2)."""
    return _lib(a).roll(a, -k, axis=2 - d)


def dagger(a):
    return a.swapaxes(-1, -2).conj()


def plaquettes(links):
    """links: (3, z, y, x, 3, 3) -> (z, y, x, 3) real traces of the xy, xz, yz plaquettes."""
    xp = _lib(links)
    out = []
    for mu, nu in ((0, 1), (0, 2), (1, 2)):
        loop = links[mu] @ shift(links[nu], 1, nu) @ dagger(shift(links[mu], 1, mu)) @ dagger(links[nu])
        out.append(xp.trace(loop, axis1=-2, axis2=-1).real / 3)
    return xp.stack(out, axis=-1)
