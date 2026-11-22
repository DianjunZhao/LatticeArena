import numpy as np
from tasks.pion_projection.full_gate_mc import cp, generate, production_gate
from tasks.pion_projection.common import protocol


def test_exact_mc_intervals_and_production_gate():
    assert cp(0, 100)[0] == 0
    assert abs(cp(0, 100)[1] - .03621669264517641) < 1e-12
    p = protocol()
    p['bootstrap_samples'] = 16
    raw = generate(np.random.default_rng(7), 'reflection', p)
    result = production_gate(raw, p, 8)
    assert not result['passed']
    assert any('symmetry' in reason for reason in result['reasons'])
