"""Small-field stout contract; no ensemble physics claims."""
import numpy as np
import pytest

from tasks.wilson_loop.stout import stout
from tasks.wilson_loop.kernels import dagger
from tasks.wilson_loop.measure import loops
from tests.test_wilson_loop import random_su3


def diagnostics(rho, steps):
    rng = np.random.default_rng(20261119)
    lattice = (3,2,3,4)
    u = random_su3(rng,(3,*lattice))
    temporal = random_su3(rng,lattice)
    saved = u.copy(); saved_t = temporal.copy()
    g = random_su3(rng,lattice)
    transform = lambda a: np.stack([g@a[d]@np.roll(dagger(g),-1,axis=3-d) for d in range(3)])
    out=stout(u,rho,steps)
    changed=u.copy();changed[:,1]=random_su3(rng,(3,*lattice[1:]))
    local=stout(changed,rho,steps)
    transformed_t=g@temporal@np.roll(dagger(g),-1,axis=0)
    p={'r_values':[1,2],'t_values':[1,2]}
    return {'covariance':float(np.max(abs(stout(transform(u),rho,steps)-transform(out)))),
            'unitarity':float(np.max(abs(dagger(out)@out-np.eye(3)))),
            'determinant':float(np.max(abs(np.linalg.det(out)-1))),
            'time_locality':float(np.max(abs(out[:,[0,2]]-local[:,[0,2]]))),
            'input_mutation':float(np.max(abs(u-saved))),
            'temporal_mutation':float(np.max(abs(temporal-saved_t))),
            'loop_gauge':float(np.max(abs(loops(out,temporal,p)-loops(stout(transform(u),rho,steps),transformed_t,p))))}


@pytest.mark.parametrize('rho,steps',[(0.,3),(.05,1),(.1,3),(.2,2)])
def test_stout_contract(rho,steps):
    assert max(diagnostics(rho,steps).values()) < 1e-11


def test_stout_identity_limit():
    rng=np.random.default_rng(7);u=random_su3(rng,(3,2,2,2,2))
    np.testing.assert_array_equal(stout(u,.1,0),u)
    np.testing.assert_array_equal(stout(u,0.,3),u)
    errors=[np.max(abs(stout(u,e,1)-u)) for e in (1e-3,1e-4,1e-5)]
    assert .09 < errors[1]/errors[0] < .11
    assert .09 < errors[2]/errors[1] < .11
    cold=np.broadcast_to(np.eye(3),(3,2,2,2,2,3,3)).copy()
    np.testing.assert_allclose(stout(cold,.1,3),cold,atol=1e-14)


def test_stout_rejects_invalid():
    with pytest.raises(ValueError): stout(np.eye(3))
    u=np.broadcast_to(np.eye(3),(3,2,2,2,2,3,3))
    with pytest.raises(ValueError): stout(u,-.1)
    with pytest.raises(ValueError): stout(u,.1,-1)


def test_stout_cupy_backend_when_available():
    cp = pytest.importorskip('cupy')
    try:
        if cp.cuda.runtime.getDeviceCount() < 1:
            pytest.skip('CuPy has no visible CUDA device')
    except cp.cuda.runtime.CUDARuntimeError as exc:
        pytest.skip(f'CuPy runtime unavailable: {exc}')
    rng = np.random.default_rng(27)
    links = random_su3(rng, (3, 2, 2, 2, 2))
    got = stout(cp.asarray(links), .1, 2)
    assert isinstance(got, cp.ndarray)
    np.testing.assert_allclose(cp.asnumpy(got), stout(links, .1, 2), atol=1e-11)
