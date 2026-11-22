"""F4 synthetic receipt failure matrix; no production execution."""
from copy import deepcopy

import pytest

from core.receipts import make
from tasks.wilson_loop.f4_preflight import preflight, trajectory_hash


def fixtures():
    rows = [{'trajectory_id': i, 'delta_h': .01 * i, 'accepted': bool(i % 2),
             'plaquette': .59 + i * .001} for i in range(4)]
    code, inputs = {'generator': 'a' * 64}, {'initial_gauge': 'b' * 64}
    result = {'trajectory_sha256': trajectory_hash(rows), 'n_trajectories': 4,
              'thermalization_cut': 1, 'tau_int_rule': 'synthetic-window-rule',
              'environment': {'backend': 'synthetic_CPU'}, 'parameters': {'beta': 6.0}}
    return rows, code, inputs, result


def cases():
    rows, code, inputs, result = fixtures()
    out = [('valid_synthetic', make('wilson_hmc_production', code, inputs, result), rows, True)]
    for field in result:
        bad = deepcopy(result); del bad[field]
        out.append(('missing_' + field, make('wilson_hmc_production', code, inputs, bad), rows, False))
    out.extend([
        ('code_mismatch', make('wilson_hmc_production', {'generator': 'c' * 64}, inputs, result), rows, False),
        ('input_mismatch', make('wilson_hmc_production', code, {'initial_gauge': 'c' * 64}, result), rows, False),
        ('trajectory_missing', make('wilson_hmc_production', code, inputs, result), [], False),
        ('trajectory_count', make('wilson_hmc_production', code, inputs, dict(result, n_trajectories=5)), rows, False),
        ('trajectory_hash', make('wilson_hmc_production', code, inputs, dict(result, trajectory_sha256='c'*64)), rows, False),
    ])
    for name, mutate in [('missing_delta_h', lambda r: r[0].pop('delta_h')),
                         ('duplicate_id', lambda r: r[1].update(trajectory_id=0)),
                         ('nonfinite', lambda r: r[0].update(delta_h=float('nan'))),
                         ('invalid_acceptance', lambda r: r[0].update(accepted=1))]:
        bad = deepcopy(rows); mutate(bad)
        out.append((name, make('wilson_hmc_production', code, inputs, result), bad, False))
    return out


@pytest.mark.parametrize('name,receipt,rows,valid', cases(), ids=lambda x: x if isinstance(x,str) else None)
def test_preflight(name, receipt, rows, valid):
    _, code, inputs, _ = fixtures()
    if valid:
        assert preflight(receipt, rows, code, inputs)['physical_status'] == 'NOT_RUN'
    else:
        with pytest.raises(ValueError):
            preflight(receipt, rows, code, inputs)
