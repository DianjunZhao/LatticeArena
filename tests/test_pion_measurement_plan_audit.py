from tasks.pion_projection.measurement_plan_audit import build_audit, render_readme


def test_measurement_plan_audit_outcomes_match_expectations():
    result = build_audit()

    assert result['schema'] == 'pion-measurement-plan-audit-v2'
    assert result['all_expected'] is True
    assert result['physical_measurement'] == 'NOT_RUN'
    assert len(result['rows']) == 6
    assert all(row['passed'] for row in result['rows'])

    legal, *rejections, draft = result['rows']
    assert legal['case'] == 'legal_current_splits'
    assert legal['accepted'] is True and legal['expected_acceptance'] is True
    assert all(row['accepted'] is False and row['expected_acceptance'] is False
               for row in rejections)
    assert draft['operation'] == 'preflight'
    assert draft['accepted'] is False and draft['expected_acceptance'] is False


def test_measurement_plan_audit_explains_legacy_summary_bug():
    text = render_readme(build_audit())
    assert 'v1 summary-field bug' in text
    assert 'do not make the measurement plan `READY`' in text
    assert 'physical score' in text
