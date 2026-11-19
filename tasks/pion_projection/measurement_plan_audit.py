"""Measurement-plan audit matrix (todo §5 CPU)."""
import copy
import json
from pathlib import Path

from .measurement_plan import preflight, validate_plan

OUT = Path('results/pion_projection/measurement_plan_audit_v1')
BASE = json.loads(Path(__file__).with_name('measurement_plan.example.json').read_text())


def legal_plan():
    plan = copy.deepcopy(BASE)
    plan['status'] = 'RUNNING'
    plan['identity'].update({'gauge_sha256': 'a' * 64, 'propagator_sha256': 'b' * 64,
                             'generation': 'c' * 64, 'placeholder': False})
    plan['budget']['available_configurations'] = 200
    plan['splits'] = {'development': [0, 119], 'validation': [140, 199], 'anchor': [120, 139]}
    return plan


def check(name, plan):
    try:
        validate_plan(plan)
        return {'case': name, 'ok': True}
    except ValueError as exc:
        return {'case': name, 'ok': False, 'reason': str(exc)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    legal = legal_plan()
    rows = [check('legal', legal)]
    overlapping = copy.deepcopy(legal)
    overlapping['splits']['validation'] = [100, 160]
    rows.append(check('overlapping_splits', overlapping))
    placeholder = copy.deepcopy(legal)
    placeholder['identity']['gauge_sha256'] = 'per-config file digest'
    rows.append(check('placeholder_identity_running', placeholder))
    missing_stop = copy.deepcopy(legal)
    missing_stop['stop_rules'] = []
    rows.append(check('missing_stop_rules', missing_stop))
    out_of_range = copy.deepcopy(legal)
    out_of_range['budget']['available_configurations'] = 100
    rows.append(check('source_out_of_range', out_of_range))
    draft = copy.deepcopy(BASE)
    draft['status'] = 'NOT_RUN'
    try:
        preflight(Path(__file__).with_name('measurement_plan.example.json'), OUT / 'never')
        draft_result = {'case': 'draft_preflight', 'ok': False, 'reason': 'preflight accepted a draft'}
    except ValueError as exc:
        draft_result = {'case': 'draft_preflight', 'ok': True, 'reason': str(exc)}
    rows.append(draft_result)
    result = {'schema': 'pion-measurement-plan-audit-v1', 'rows': rows,
              'all_expected': all(row['ok'] == (row['case'] == 'legal') for row in rows)}
    (OUT / 'measurement_plan_audit.json').write_text(json.dumps(result, indent=2) + '\n')
    for row in rows:
        print(row['case'], row['ok'], row.get('reason', ''))


if __name__ == '__main__':
    main()
