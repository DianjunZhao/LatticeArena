import json

import numpy as np
import pytest

from agents import comparison
from core.io import digest, write_json
from tasks.pion_projection import common, experiment
from tasks.pion_projection.ranking import diagnose
from tasks.pion_projection.synthetic import synthetic_checks


def split(run, p, name):
    from tasks.pion_projection.statistics import shape

    ids = common.indices(name, p)
    rng = np.random.default_rng(int(ids[0]) + 18)
    mean = np.arange(1., 8.)[:, None] * shape(.8, np.arange(16))
    data = mean * (1 + .01 * rng.normal(size=(len(ids), *mean.shape)))
    np.savez(run / f'{name}.npz', ids=ids, correlators=data, protocol_hash=common.fingerprint(p))
    write_json(run / f'{name}_provenance.json', {'protocol': p})


def test_nominal_matches_evaluator_and_frozen_files_stay_intact(tmp_path, monkeypatch):
    p = dict(common.protocol(), bootstrap_samples=32, outer_samples=5, inner_samples=8)
    monkeypatch.setattr(common, 'protocol', lambda: p)
    monkeypatch.setattr(experiment, 'protocol', lambda: p)
    run = tmp_path / 'frozen'
    run.mkdir()
    split(run, p, 'development')
    experiment.develop(run)
    split(run, p, 'validation')
    experiment.evaluate(run)
    old = {path.name: digest(path) for path in run.iterdir()}
    report = diagnose(run, tmp_path / 'report')
    assert old == {path.name: digest(path) for path in run.iterdir()}
    assert report['nominal_reproduced'] and len(report['windows']) == 3
    assert len(set(w['reference']['mass'] for w in report['windows'])) == 3
    assert all(len(w['pairs']) == 3 for w in report['windows'])
    assert (tmp_path / 'report/ranking.md').is_file()
    with pytest.raises(FileExistsError):
        diagnose(run, tmp_path / 'report')
    # A stale reference or a modified frozen weight vector invalidates a replay.
    path = run / 'validation_results.json'
    archive = json.loads(path.read_text())
    archive['reference']['mass'] += .1
    write_json(path, archive)
    with pytest.raises(AssertionError):
        diagnose(run, tmp_path / 'stale')
    with (run / 'submission.json').open('a') as f:
        f.write(' ')
    with pytest.raises(ValueError, match='identity'):
        diagnose(run, tmp_path / 'stale')


def test_known_spectrum_controls_and_signed_counterexample():
    cases = synthetic_checks()['cases']
    single, quiet = (cases[k] for k in ('single', 'lower_noise'))
    assert quiet['variance'] < single['variance'] and quiet['energy']['bootstrap_se'] < single['energy']['bootstrap_se']
    excited, reduced, signed = (cases[k] for k in ('excited', 'reduced_excitation', 'signed_cancellation'))
    assert reduced['risk'] < excited['risk']
    assert abs(reduced['energy']['noiseless_bias']) < abs(excited['energy']['noiseless_bias'])
    assert signed['signed_excited_over_ground_early'][1] == pytest.approx(0, abs=1e-12)
    assert signed['unsigned_excited_over_ground_early'][1] > .5
    assert signed['risk'] < excited['risk']
    assert abs(signed['energy']['noiseless_bias']) > abs(excited['energy']['noiseless_bias'])
    assert cases['near_zero_overlap']['risk'] is None
    assert 'Amplitude' in cases['near_zero_overlap']['invalid_reason']


def test_comparison_budget_diagnostics_and_seed_use_dev_only(tmp_path, monkeypatch):
    p = dict(common.protocol(), bootstrap_samples=32)
    split(tmp_path, p, 'development')
    calls = []

    def reply(prompt, model):
        calls.append(prompt)
        for k in ('mean_folded', 'q_early', 'correlation_across_development_blocks_by_time', 'variance', 'departure_squared'):
            assert k in prompt
        return json.dumps({'candidates': [[1, 0, 0, 0, 0, 0, 0]] * 4})

    monkeypatch.setattr(comparison, 'chat', reply)
    left = comparison.compare(tmp_path, tmp_path / 'first', 'stub', 5)
    right = comparison.compare(tmp_path, tmp_path / 'second', 'stub', 5)
    assert len(calls) == 8
    assert left['validation_status'] == 'not_read' and left['llm']['accepted'] == 12
    assert all(row['over_budget'] for row in left['llm']['rounds'])
    assert left['random'] == right['random'] and len(left['random']['accepted']) == 12
    assert [r['slots_offered'] for r in left['best_including_basis']] == [3, 6, 9, 12]
    assert left['slsqp']['objective_calls'] > 12 and left['slsqp_raw_risk']['ridge'] == 0
