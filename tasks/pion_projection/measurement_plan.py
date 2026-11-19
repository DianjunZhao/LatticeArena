"""Pre-registration schema and preflight for a new pion measurement (todo §7)."""
import json
import re
from pathlib import Path

REQUIRED = ('schema', 'ensemble', 'geometry', 'sources', 'sink_powers', 'splits',
            'identity', 'checks', 'statistics', 'freeze', 'budget', 'stop_rules', 'status')
HEX = re.compile(r'^[0-9a-f]{64}$')


def _ranges(splits):
    rows = []
    for name, value in splits.items():
        if not (isinstance(value, list) and len(value) == 2 and all(isinstance(v, int) for v in value)):
            raise ValueError(f'split {name!r} must be [first, last]')
        first, last = value
        if last < first:
            raise ValueError(f'split {name!r} is empty')
        rows.append((name, first, last))
    for i, (name_a, a0, a1) in enumerate(rows):
        for name_b, b0, b1 in rows[i + 1:]:
            if not (a1 < b0 or b1 < a0):
                raise ValueError(f'splits {name_a!r} and {name_b!r} overlap')
    return rows


def validate_plan(plan):
    missing = [key for key in REQUIRED if key not in plan]
    if missing:
        raise ValueError(f'measurement plan is missing {missing}')
    if plan['schema'] != 'pion-measurement-plan-v1':
        raise ValueError(f'unsupported plan schema {plan["schema"]!r}')
    if not plan['sources'] or not plan['sink_powers']:
        raise ValueError('sources and sink_powers must be non-empty')
    for key in ('development', 'validation'):
        if key not in plan['splits']:
            raise ValueError(f'splits must declare {key}')
    _ranges(plan['splits'])
    available = plan.get('budget', {}).get('available_configurations')
    if available is not None:
        for name, (first, last) in plan['splits'].items():
            if last >= available:
                raise ValueError(f'split {name!r} exceeds the available configurations ({available})')
    geometry = plan['geometry']
    if not (isinstance(geometry, list) and len(geometry) == 4
            and all(isinstance(v, int) and v > 0 for v in geometry)):
        raise ValueError('geometry must be four positive integers')
    if geometry[3] % 2:
        raise ValueError('an even time extent is required for the cosh fold')
    for key in ('gauge_sha256', 'propagator_sha256', 'quda', 'device', 'precision',
                'trajectory_ids', 'generation'):
        if key not in plan['identity']:
            raise ValueError(f'identity must include {key}')
    if plan['status'] in ('RUNNING', 'DONE'):
        if plan['identity'].get('placeholder'):
            raise ValueError('a RUNNING/DONE plan cannot carry placeholder identity')
        for key in ('gauge_sha256', 'propagator_sha256', 'generation'):
            if not HEX.match(str(plan['identity'][key])):
                raise ValueError(f'identity {key!r} is not a real sha256 for status {plan["status"]}')
    if plan['status'] not in ('NOT_RUN', 'RUNNING', 'DONE'):
        raise ValueError(f'unsupported status {plan["status"]!r}')
    if not isinstance(plan['stop_rules'], list) or not plan['stop_rules']:
        raise ValueError('stop_rules must be a non-empty list')
    if not isinstance(plan['freeze'], dict) or not plan['freeze']:
        raise ValueError('freeze must be a non-empty mapping')
    return plan


def load_plan(path):
    return validate_plan(json.loads(Path(path).read_text()))


def preflight(plan_path, output, split='development'):
    """Validate the plan before any GPU import; refuse drafts and cross-identity resumes."""
    plan = load_plan(plan_path)
    if plan['status'] == 'NOT_RUN':
        raise ValueError('plan status is NOT_RUN (draft); refusing to start a measurement')
    if plan['status'] == 'DONE':
        raise ValueError('plan status is DONE; start a new plan for a new measurement')
    output = Path(output)
    expected_generation = str(plan['identity']['generation'])
    existing = output / f'{split}.npz'
    if output.exists() and any(output.iterdir()):
        if not existing.exists():
            raise ValueError('output directory already contains files but no resumable data')
        with np.load(existing, allow_pickle=False) as f:
            if 'generation' not in f:
                raise ValueError('existing measurement has no generation id')
            if str(f['generation']) != expected_generation:
                raise ValueError('existing measurement generation differs from the plan')
    return plan


import numpy as np  # noqa: E402  (kept after the pure-python validator)
