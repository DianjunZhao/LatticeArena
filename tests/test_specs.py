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
