import json
from pathlib import Path

import numpy as np
import pytest

from core.specs import candidate_spec, operator_contract, task_spec


def test_task_spec_validation():
    with pytest.raises(ValueError, match='missing'):
        task_spec(name='x')
    good = dict(name='x', observable='y', geometry=[16, 16, 16, 16],
                boundary={'spatial': 'periodic'}, source={'kind': 'point'},
                splits={'development': [0, 9], 'validation': [10, 19]},
                reference={'kind': 'single'}, metric={'name': 'risk'},
                budget={'outer': 10}, dependencies={})
    task_spec(**good)
    with pytest.raises(ValueError, match='geometry'):
        task_spec(**dict(good, geometry=[16, 16]))
    with pytest.raises(ValueError, match='splits'):
        task_spec(**dict(good, splits={'development': [0, 9]}))


def test_operator_and_candidate_contracts():
    contract = operator_contract(name='pion-kernel-v1', axes='(z,y,x,3,nrhs)', dtype='complex128',
                                 transformation='spin_scalar', support='time_slice',
                                 parameters={}, dependencies={}, constraints={})
    with pytest.raises(ValueError, match='axes'):
        operator_contract(**dict(contract, axes='(bad)'))
    with pytest.raises(ValueError, match='transformation'):
        operator_contract(**dict(contract, transformation='nope'))
    spec = candidate_spec('tasks.pion_projection.kernels:build_kernel', {'alpha': 0.2}, contract, {})
    assert spec['contract'] == 'pion-kernel-v1'
    with pytest.raises(ValueError, match='builder'):
        candidate_spec('no-colon', {}, contract, {})


def test_task_adapters_match_protocols():
    from tasks.pion_projection.spec import operator_contract_for as pion_op
    from tasks.pion_projection.spec import task_spec_for as pion_spec
    from tasks.wilson_loop.spec import operator_contract_for as wilson_op
    from tasks.wilson_loop.spec import task_spec_for as wilson_spec
    p = json.loads(Path('tasks/pion_projection/protocol_gevp200.json').read_text())
    w = json.loads(Path('tasks/wilson_loop/protocol_v3.json').read_text())
    ps, ws = pion_spec(p), wilson_spec(w)
    assert ps['geometry'] == p['geometry'] and ws['geometry'] == w['geometry']
    assert ps['splits']['validation'] == p['validation']
    assert ws['splits']['validation'] == w['validation']
    assert pion_op()['axes'] == '(z,y,x,3,nrhs)'
    assert wilson_op()['axes'] == '(mu,t,z,y,x,3,3)'
    assert ps['dependencies']['kernels'] and ws['dependencies']['kernels']


def test_measurement_bundle_capabilities():
    from core.measurement import UnsupportedCapability, bundle, describe, require
    b = bundle('toy', {'x': np.ones((2, 3))}, {'splits': {'development': {}}},
               {'linear_response': True, 'cross_matrix': False, 'new_source': False})
    require(b, 'linear_response')
    with pytest.raises(UnsupportedCapability):
        require(b, 'cross_matrix')
    with pytest.raises(ValueError, match='capability'):
        bundle('toy', {'x': np.ones(3)}, {}, {'linear_response': True})
    assert describe(b)['shapes']['x'] == [2, 3]


def test_bundles_from_real_runs():
    from core.measurement import describe
    from tasks.pion_projection.spec import bundle_for as pion_bundle
    from tasks.wilson_loop.spec import bundle_for as wilson_bundle
    pb = pion_bundle('results/pion_projection/s16t16_gevp200')
    assert pb['arrays']['development'].ndim == 3
    assert describe(pb)['capabilities']['linear_response']
    wb = wilson_bundle('results/wilson_loop/s16t16_v3')
    assert wb['arrays']['validation'].ndim == 4
    assert not describe(wb)['capabilities']['linear_response']


def test_comparator_shares_draws():
    from core.comparator import check_draws, log_lower_bound, paired_ratio
    base = np.linspace(1.0, 2.0, 50)
    cand = np.linspace(0.5, 1.0, 50)
    result = paired_ratio(base, cand)
    assert result['median'] == pytest.approx(2.0) and result['draws'] == 50
    with pytest.raises(ValueError, match='different lengths'):
        check_draws({'a': np.ones(5), 'b': np.ones(6)})
    low, invalid = log_lower_bound(base, cand, 0.025)
    assert low > 0 and invalid == 0
