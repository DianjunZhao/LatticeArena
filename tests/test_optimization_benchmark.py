import json

import numpy as np
import pytest

from agents import optimization_benchmark as bench
from core.candidates import validate_weights


def test_synthetic_controls_replay_and_freeze(tmp_path, monkeypatch):
    output = tmp_path / 'original'
    observed = []
    original = bench.sample_blocks

    def capture(*args):
        values = original(*args)
        if len(observed) % 2:
            folder = output / f'episode-{len(observed) // 2:03d}'
            assert (folder / 'selection.json').exists()
            assert not (folder / 'test.json').exists()
            assert not np.array_equal(observed[-1], values)
        observed.append(values)
        return values

    with monkeypatch.context() as patch:
        patch.setattr(bench, 'sample_blocks', capture)
        first = bench.benchmark(output, 17, 2)
    assert first == bench.benchmark(tmp_path / 'replay', 17, 2)
    assert not np.array_equal(observed[0], observed[2])
    for case in first['cases']:
        folder = output / f"episode-{case['episode']:03d}"
        selections = json.loads((folder / 'selection.json').read_text())
        assert set(selections) == {'basis', 'curve_fit', 'fixed_random', 'adaptive_random'}
        for name in ('curve_fit', 'fixed_random', 'adaptive_random'):
            trace = json.loads((folder / f'{name}.json').read_text())
            assert len(trace) == 4
            assert all(len(r['accepted']) + len(r['rejections']) == 3 for r in trace)
            assert validate_weights(selections[name]['candidate'], 7)[0]
            assert case['test'][name]['risk'] > 0
        fixed = json.loads((folder / 'fixed_random.json').read_text())
        adaptive = json.loads((folder / 'adaptive_random.json').read_text())
        assert fixed[0] == adaptive[0]
    with pytest.raises(FileExistsError):
        bench.benchmark(output, 17, 2)


def test_round_feedback_ablation_and_invalid_fallback(tmp_path):
    prompts = []
    def reply(prompt, model):
        prompts.append(prompt)
        return json.dumps({'candidates': [[1, 0, 0, 0, 0, 0, 0], [0], [0], [1]]})

    run = bench.benchmark(tmp_path / 'models', 42, 2, 'mock', responder=reply)
    assert len(prompts) == 2 * 2 * 4
    for i, prompt in enumerate(prompts):
        history = json.loads(prompt.split('Previous attempts, as (u, risk):\n')[1].split('\n\n')[0])
        if i % 4 == 0:
            assert history == []
        elif 'without their outcomes' in prompt:
            assert all(set(row) == {'proposed'} for row in history)
        else:
            assert any('risk' in row for row in history)
    for i, case in enumerate(run['cases']):
        folder = tmp_path / 'models' / f'episode-{i:03d}'
        rows = json.loads((folder / 'llm_feedback' / 'rounds.json').read_text())
        assert all(len(row['accepted']) == 1 and len(row['rejections']) == 2 and row['over_budget'] for row in rows)
        assert case['test']['llm_feedback'] == case['test']['llm_no_feedback']
    empty = bench.benchmark(tmp_path / 'invalid', 22, 1, 'bad', responder=lambda *_: 'bad JSON')
    scores = empty['cases'][0]['test']
    assert scores['llm_feedback'] == scores['llm_no_feedback'] == scores['basis']
    selection = json.loads((tmp_path / 'invalid/episode-000/selection.json').read_text())
    assert selection['llm_feedback']['accepted'] == 0


def test_invalid_pair_reported():
    report = bench.paired_summary([{'test': {'a': {'risk': None}, 'b': {'risk': 1}}}], 'a', 'b')
    assert report['cases'] == 1 and report['valid_pairs'] == 0 and report['median_ratio'] is None


def test_archived_proposals_are_selected_on_development(tmp_path):
    replies = tmp_path / 'replies.jsonl'
    replies.write_text((json.dumps({'candidates': [[1, 0, 0, 0, 0, 0, 0]] * 3}) + '\n') * 4)
    result = bench.benchmark(tmp_path / 'transfer', 7, 2, replay=replies)
    assert result['model'] is None and result['replay_sha256']
    for i, case in enumerate(result['cases']):
        folder = tmp_path / 'transfer' / f'episode-{i:03d}'
        selection = json.loads((folder / 'selection.json').read_text())
        assert selection['archived_proposals']['accepted'] == 12
        assert selection['basis']['candidate'] == selection['archived_proposals']['candidate']
        assert case['test']['archived_proposals'] == case['test']['basis']
    replies.write_text('{}\n')
    with pytest.raises(ValueError, match='4 lines'):
        bench.benchmark(tmp_path / 'short', 7, 2, replay=replies)
