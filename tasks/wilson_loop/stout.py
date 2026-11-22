"""NumPy/CuPy pure-spatial stout, rho is the weight per staple (four per link)."""
import numpy as np

from .kernels import _lib, dagger, shift


def stout(spatial_links, rho=0.1, steps=1):
    """Return new links; input (3,t,z,y,x,3,3), periodic spatial boundaries.

    C_mu=rho sum(staples), Omega=C_mu U_mu^dagger,
    Q=(Omega-Omega^dagger)/(2i)-I Tr[(Omega-Omega^dagger)/(2i)]/3,
    U'_mu=exp(i Q) U_mu. All directions update synchronously.
    Under U_mu(x)->G(x)U_mu(x)G(x+mu)^dagger, Q transforms at x.
    No temporal links are accepted or modified; no time-axis shifts occur.
    Uses the input array backend (NumPy or CuPy) in complex128. ``rho`` is not
    the APE ``alpha`` parameter. For a weak field around the identity, the
    leading linearized update is matched to APE by ``rho ~= alpha/4``; this is
    a design approximation, not an exact equality of smoothing radii.
    """
    xp = _lib(spatial_links)
    u = xp.asarray(spatial_links, dtype=xp.complex128)
    if u.ndim != 7 or u.shape[0] != 3 or u.shape[-2:] != (3, 3):
        raise ValueError('expected (3,t,z,y,x,3,3) spatial links')
    if not xp.all(xp.isfinite(u)) or not np.isfinite(rho) or rho < 0:
        raise ValueError('finite links and finite nonnegative rho required')
    if type(steps) is not int or steps < 0:
        raise ValueError('steps must be a nonnegative integer')
    u = u.copy()
    if rho == 0:
        return u
    for _ in range(steps):
        new = xp.empty_like(u)
        for mu in range(3):
            c = xp.zeros_like(u[mu])
            for nu in range(3):
                if nu == mu:
                    continue
                c += u[nu] @ shift(u[mu], 1, 3-nu) @ dagger(shift(u[nu], 1, 3-mu))
                c += dagger(shift(u[nu], -1, 3-nu)) @ shift(u[mu], -1, 3-nu) @ shift(shift(u[nu], 1, 3-mu), -1, 3-nu)
            omega = rho*c @ dagger(u[mu])
            q = (omega-dagger(omega))/(2j)
            q -= xp.trace(q,axis1=-2,axis2=-1)[...,None,None]*xp.eye(3)/3
            values, vectors = xp.linalg.eigh(q)
            exponential = (vectors*xp.exp(1j*values)[...,None,:]) @ dagger(vectors)
            new[mu] = exponential @ u[mu]
        u = new
    return u
