"""Synthetic-testable F4 receipt preflight; never certifies HMC physics quality."""
import hashlib
import json

import numpy as np

from core.receipts import verify


def trajectory_hash(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, allow_nan=False).encode()).hexdigest()


def preflight(receipt, rows, expected_code, expected_inputs):
    """Validate binding and minimal trajectory schema against external identities.

    Passing means schema-ready, not production validated. Thermalization and
    autocorrelation quality require separate diagnostics and acceptance criteria.
    """
    verify(receipt)
    if receipt['kind'] != 'wilson_hmc_production':
        raise ValueError('wrong receipt kind')
    if not expected_code or receipt['code'] != expected_code:
        raise ValueError('code hash mismatch')
    if not expected_inputs or receipt['inputs'] != expected_inputs:
        raise ValueError('input hash mismatch')
    result = receipt['result']
    required = ('trajectory_sha256', 'n_trajectories', 'thermalization_cut',
                'tau_int_rule', 'environment', 'parameters')
    if not isinstance(result, dict) or any(k not in result for k in required):
        raise ValueError('missing production schema fields')
    if not result['environment'] or not result['parameters'] or not result['tau_int_rule']:
        raise ValueError('empty production metadata')
    if not isinstance(rows, list) or len(rows) < 2:
        raise ValueError('trajectory data missing or too short')
    ids = []
    for row in rows:
        if not isinstance(row, dict) or any(k not in row for k in
                                          ('trajectory_id', 'delta_h', 'accepted', 'plaquette')):
            raise ValueError('trajectory fields missing')
        if type(row['trajectory_id']) is not int or type(row['accepted']) is not bool:
            raise ValueError('trajectory id/acceptance type invalid')
        if not np.all(np.isfinite([row['delta_h'], row['plaquette']])):
            raise ValueError('trajectory values nonfinite')
        ids.append(row['trajectory_id'])
    if any(b <= a for a, b in zip(ids, ids[1:])):
        raise ValueError('trajectory IDs duplicate or unordered')
    if result['n_trajectories'] != len(rows):
        raise ValueError('trajectory count mismatch')
    cut = result['thermalization_cut']
    if type(cut) is not int or not 0 <= cut < len(rows):
        raise ValueError('thermalization cut invalid')
    if result['trajectory_sha256'] != trajectory_hash(rows):
        raise ValueError('trajectory content hash mismatch')
    return {'status': 'schema_ready', 'physical_status': 'NOT_RUN',
            'n_trajectories': len(rows), 'note': 'identity/schema only; not a production-quality certificate'}
