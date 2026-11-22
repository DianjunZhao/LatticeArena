"""Explicit opt-in path, legacy APE unchanged."""
import numpy as np
import pytest
from tasks.wilson_loop.kernels import build_kernel, ape, dagger
from tasks.wilson_loop.spec import operator_contract_for
from tests.test_wilson_loop import random_su3


def test_interface_contract():
    rng=np.random.default_rng(31);u=random_su3(rng,(3,3,2,3,4))
    g=random_su3(rng,(3,2,3,4))
    transform=lambda a:np.stack([g@a[d]@np.roll(dagger(g),-1,axis=3-d) for d in range(3)])
    p={'kind':'stout','rho':.1,'steps':2}
    out=build_kernel(u,p)
    np.testing.assert_allclose(build_kernel(transform(u),p),transform(out),atol=1e-11)
    changed=u.copy();changed[:,1]=random_su3(rng,(3,2,3,4))
    np.testing.assert_array_equal(build_kernel(changed,p)[:,[0,2]],out[:,[0,2]])
    np.testing.assert_array_equal(build_kernel(u,{'alpha':.4,'steps':2}),ape(u,.4,2))
    np.testing.assert_array_equal(build_kernel(u,{'alpha':0,'steps':0}),u)
    assert 'stout' in operator_contract_for('stout')['dependencies']
    assert operator_contract_for()['parameters']=={'alpha':'float','steps':'int'}


@pytest.mark.parametrize('p',[
 {'kind':'unknown'}, {'kind':'stout','rho':-.1,'steps':1},
 {'kind':'stout','rho':.1,'steps':-1}, {'kind':'stout','rho':.1,'steps':1,'alpha':.4}])
def test_interface_bad_parameters(p):
    with pytest.raises(ValueError):build_kernel(np.broadcast_to(np.eye(3),(3,2,2,2,2,3,3)),p)
