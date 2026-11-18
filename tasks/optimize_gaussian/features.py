"""Gauge-invariant, time-local features, arranged in the A1+ cubic channel."""
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
    """links: (3, z, y, x, 3, 3) -> (z, y, x, 3) real traces of xy, xz, yz."""
    xp = _lib(links)
    out = []
    for mu, nu in ((0, 1), (0, 2), (1, 2)):
        loop = links[mu] @ shift(links[nu], 1, mu) @ dagger(shift(links[mu], 1, nu)) @ dagger(links[nu])
        out.append(xp.trace(loop, axis1=-2, axis2=-1).real / 3)
    return xp.stack(out, axis=-1)


def directional_features(links):
    """For direction mu, symmetric combinations of the two plaquettes containing mu.

    x -> (P_xy, P_xz), y -> (P_xy, P_yz), z -> (P_xz, P_yz), then (sum, product).
    The sum/product pair is invariant under exchanging the two transverse
    directions, which is what a 90-degree rotation about mu does; sharing one
    function across the three directions then makes the kernel A1+.
    """
    p = plaquettes(links)
    pairs = [p[..., [0, 1]], p[..., [0, 2]], p[..., [1, 2]]]
    return _lib(links).stack([_lib(links).stack([q[..., 0] + q[..., 1], q[..., 0] * q[..., 1]], axis=-1)
                              for q in pairs], axis=0)
