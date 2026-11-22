"""Analytic edge and contract tests; no ensemble or stochastic calibration."""
import math
import numpy as np
import pytest

from tasks.pion_projection.bounded_score_calibration import bounded_lower, generate, run, cp


def call(b=.5, b2=.5, c=.5, c2=.5, a=0., **kwargs):
    return bounded_lower(np.array([[b]]),np.array([[b2]]),np.array([[c]]),np.array([[c2]]),np.array([[a]]),n=100,family=1,**kwargs)


def test_equal_and_arm_swap():
    low,d,pen=call()
    assert d.item()==0 and low.item()==-pen
    _,first,_=call(b=.8,b2=.8,c=.2,c2=.2,a=.1)
    _,second,_=call(b=.2,b2=.2,c=.8,c2=.8,a=.1)
    assert first.item()==pytest.approx(-second.item())


def test_unit_scale_and_anchor_penalty():
    low,d,pen=call(b=.8,b2=.8,c=.2,c2=.2,a=.1,anchor_bound=.04)
    # Transform masses x -> 2+3*x, so MSE differences and all penalties multiply by 9.
    b=.8;c=.2
    result=bounded_lower(np.array([[2+3*b]]),np.array([[4+12*b+9*b]]),
        np.array([[2+3*c]]),np.array([[4+12*c+9*c]]),np.array([[2.3]]),
        n=100,family=1,lower=2,upper=5,anchor_bound=.12)
    assert result[0].item()==pytest.approx(9*low.item())
    assert result[1].item()==pytest.approx(9*d.item())
    assert result[2]==pytest.approx(9*pen)


def test_penalty_family_and_n():
    _,_,p=call()
    _,_,p4=bounded_lower(np.array([[.5]]),np.array([[.5]]),np.full((1,4),.5),np.full((1,4),.5),np.zeros((1,1)),n=100,family=4)
    _,_,p400=bounded_lower(np.array([[.5]]),np.array([[.5]]),np.full((1,1),.5),np.full((1,1),.5),np.zeros((1,1)),n=400,family=1)
    assert p4>p and p400==p/2


def test_anchor_correction_uniform_endpoints():
    for b in (0.,.3,1.):
        for c in (0.,.7,1.):
            for true in (.2,.8):
                for a in (true-.1,true+.1):
                    low,d,pen=call(b=b,b2=b*b,c=c,c2=c*c,a=a,anchor_bound=.1)
                    truth=(b-true)**2-(c-true)**2
                    assert (low+pen).item()<=truth+1e-12


@pytest.mark.parametrize('kwargs',[dict(alpha_s=0),dict(anchor_bound=-1),dict(lower=1,upper=0)])
def test_invalid_scalar_contract(kwargs):
    with pytest.raises(ValueError):call(**kwargs)


@pytest.mark.parametrize('kwargs',[dict(b=float('nan')),dict(c=1.1,c2=1.21),dict(b=.5,b2=.1)])
def test_reject_nonfinite_unbounded_inconsistent(kwargs):
    with pytest.raises(ValueError):call(**kwargs)


def test_endpoint_truth_and_seed_replay():
    spec=dict(world='max_variance_null',anchor='exact',n=1,family=4,dependence='iid')
    a=generate(spec,100);b=generate(spec,100)
    for x,y in zip(a,b):np.testing.assert_array_equal(x,y)
    low,d,_=bounded_lower(*a[:5],n=1,family=4)
    assert set(np.unique(d))=={-1.,1.}
    assert a[5]==0.
    assert np.array_equal(d[:,0],d[:,3])


def test_no_clobber_and_cp_edges(tmp_path):
    with pytest.raises(FileExistsError):run(tmp_path,1)
    assert list(tmp_path.iterdir())==[]
    assert cp(0,3000)[0]==0 and cp(3000,3000)[1]==1
    assert cp(0,0)==[None,None]
