"""CPU measurement-plan acceptance audit (todo §5).

The audit distinguishes validator acceptance from whether that acceptance was
the expected result. It checks only synthetic plan metadata; it never measures
or reads gauge/propagator data.
"""
import copy
import json
from pathlib import Path

from .common import fingerprint, protocol
from .measurement_plan import preflight, validate_plan

OUT = Path('results/pion_projection/measurement_plan_audit_v2')
PLAN_PATH = Path(__file__).with_name('measurement_plan.example.json')
BASE = json.loads(PLAN_PATH.read_text())


def legal_plan():
    """A schema-level READY fixture using the current D/E split boundaries."""
    plan = copy.deepcopy(BASE)
    plan['status'] = 'READY'
    plan['ensemble'] = 'data/S16T16D'
    plan['identity'].update({'gauge_sha256': 'a' * 64, 'propagator_sha256': 'b' * 64,
                             'require_trajectory_manifest': True})
    plan['protocol_sha256'] = fingerprint(protocol())
    plan['freeze']['frozen_at_utc'] = '2026-11-20T00:00:00Z'
    plan['budget']['available_configurations'] = 200
    plan['splits'] = {'development': [0, 99], 'anchor': [0, 59],
                      'gap': [100, 139], 'validation': [140, 199]}
    plan['split_ensembles'] = {'anchor': 'data/S16T16E'}
    return plan


def _attempt_validation(name, plan, expected_acceptance):
    try:
        validate_plan(plan)
    except ValueError as exc:
        accepted = False
        reason = str(exc)
    else:
        accepted = True
        reason = ''
    return {'case': name, 'operation': 'validate_plan', 'accepted': accepted,
            'expected_acceptance': expected_acceptance,
            'passed': accepted == expected_acceptance, 'reason': reason}


def _attempt_draft_preflight():
    try:
        preflight(PLAN_PATH, OUT / 'draft_preflight_must_not_write')
    except ValueError as exc:
        return {'case': 'draft_preflight', 'operation': 'preflight', 'accepted': False,
                'expected_acceptance': False, 'passed': True, 'reason': str(exc)}
    return {'case': 'draft_preflight', 'operation': 'preflight', 'accepted': True,
            'expected_acceptance': False, 'passed': False,
            'reason': 'preflight accepted a NOT_RUN draft'}


def build_audit():
    legal = legal_plan()
    rows = [_attempt_validation('legal_current_splits', legal, True)]

    overlapping = copy.deepcopy(legal)
    overlapping['splits']['validation'] = [90, 160]
    rows.append(_attempt_validation('overlapping_splits', overlapping, False))

    bad_protocol = copy.deepcopy(legal)
    bad_protocol['protocol_sha256'] = 'not-a-sha256'
    rows.append(_attempt_validation('invalid_protocol_hash', bad_protocol, False))

    missing_stop = copy.deepcopy(legal)
    missing_stop['stop_rules'] = []
    rows.append(_attempt_validation('missing_stop_rules', missing_stop, False))

    out_of_range = copy.deepcopy(legal)
    out_of_range['budget']['available_configurations'] = 180
    rows.append(_attempt_validation('source_out_of_range', out_of_range, False))

    rows.append(_attempt_draft_preflight())
    return {'schema': 'pion-measurement-plan-audit-v2',
            'scope': 'CPU schema/control-flow audit with synthetic identities only',
            'split_fixture': legal['splits'],
            'split_ensembles': {'development': 'data/S16T16D',
                                'anchor': 'data/S16T16E',
                                'gap': 'data/S16T16D',
                                'validation': 'data/S16T16D'},
            'rows': rows,
            'all_expected': all(row['passed'] for row in rows),
            'physical_measurement': 'NOT_RUN'}


def render_readme(result):
    lines = [
        '# Pion measurement-plan audit v2',
        '',
        'This CPU-only audit corrects the v1 summary-field bug. In v1, `ok` meant validator acceptance for schema cases but meant expected refusal for the draft preflight case; the aggregate therefore reported `all_expected=false` even though the individual outcomes matched the intended behavior.',
        '',
        'The v2 report stores observed acceptance, expected acceptance, and per-case pass separately. It checks the current D/E split boundaries with synthetic hashes; it does not inspect remote manifests, gauge bytes, propagators, GPU execution, or physical score.',
        '',
        '| Case | Operation | Expected acceptance | Observed acceptance | Pass | Diagnostic |',
        '| --- | --- | ---: | ---: | ---: | --- |',
    ]
    for row in result['rows']:
        reason = row['reason'] or '—'
        lines.append(f"| `{row['case']}` | `{row['operation']}` | {row['expected_acceptance']} | {row['accepted']} | {row['passed']} | {reason} |")
    lines.extend([
        '',
        f"Overall expected outcomes: **{result['all_expected']}** ({sum(r['passed'] for r in result['rows'])}/{len(result['rows'])} cases).",
        '',
        'Interpretation: a valid current split shape is accepted; split overlap, an invalid protocol hash, missing stop rules, and out-of-range IDs are rejected; a `NOT_RUN` draft is rejected before measurement setup. These checks do not make the measurement plan `READY` and do not certify any physical result.',
        '',
        'The previous [v1 lifecycle report](../measurement_plan_audit_v1/README.md) is preserved as historical evidence. The new report fixes its aggregate interpretation without rewriting the old artifact.',
        '',
    ])
    return '\n'.join(lines)


def main():
    if OUT.exists():
        raise FileExistsError(f'refusing to overwrite existing audit output: {OUT}')
    result = build_audit()
    OUT.mkdir(parents=True)
    (OUT / 'measurement_plan_audit.json').write_text(json.dumps(result, indent=2) + '\n')
    (OUT / 'README.md').write_text(render_readme(result))
    for row in result['rows']:
        print(row['case'], row['accepted'], row['passed'], row.get('reason', ''))
    print('all_expected', result['all_expected'])


if __name__ == '__main__':
    main()
