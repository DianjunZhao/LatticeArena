from tasks.pion_projection.synthetic_adapter import execute


def test_file_entry_draw_and_identity_parity(tmp_path):
    result = execute(tmp_path/'synthetic')
    assert result['status'] == 'PASS'
    assert result['max_abs_draw_difference'] == 0
    assert result['gate_parity']
    assert result['n_draw_candidate_comparisons'] == 12
    assert all(x['rejected'] for x in result['mutations'].values())
    assert result['physical_score'] is None


def test_fixed_basis_candidate_production_adapter(tmp_path):
    import json
    result = execute(tmp_path/'fixed', scenario='null_equal_candidate')
    assert result['status'] == 'PASS'
    assert result['n_draw_candidate_comparisons'] == 8
    sub=json.loads((tmp_path/'fixed/run/submission.json').read_text())
    assert sub['synthetic_fixed_candidates']=={'baseline_channel':1,'candidate_channel':2}
    assert sub['submissions']['local'][1] == 1
    assert sub['submissions']['fixed_candidate'][2] == 1
    assert set(sub['submissions'])=={'local','fixed_candidate'}
    assert sub['smear_alpha'] == 0.2
    assert sub['score_spec']['alpha'] == 0.05
    metrics=json.loads((tmp_path/'fixed/joint/metric_results.json').read_text())
    assert metrics['level'] == 0.05


def test_score_alpha_is_independent_of_smear_alpha():
    from tasks.pion_projection.experiment import make_score_spec
    assert make_score_spec({'alpha': 0.2}, 1)['alpha'] == 0.05
    assert make_score_spec({'alpha': 0.2, 'score_alpha': 0.1}, 1)['alpha'] == 0.1


def test_expected_rejection_keeps_raw_input_and_stage(tmp_path):
    import numpy as np
    result=execute(tmp_path/'nonfinite', scenario='nonfinite', full_budget=True, seed=11)
    assert result['status']=='EXPECTED_REJECTION'
    assert result['failure'] and result['abstain']
    assert result['seed']==11 and result['stage']=='develop'
    assert not result['candidate_certified']
    with np.load(tmp_path/'nonfinite/raw_inputs.npz') as z:
        assert not np.isfinite(z['development']).all()
