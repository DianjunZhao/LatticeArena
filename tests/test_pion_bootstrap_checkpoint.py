import json

import numpy as np
import pytest

from tasks.pion_projection.bootstrap_checkpoint import (
    BootstrapCheckpoint,
    run_checkpointed_bootstrap,
)
from tasks.pion_projection.common import protocol
from tasks.pion_projection.reference_twostate import TwoStateFit
from tasks.pion_projection.statistics import blocks, shape


def _fit():
    p = protocol()
    rng = np.random.default_rng(6120)
    times = np.arange(p['geometry'][3])
    data = np.empty((40, len(p['powers']), len(times)), dtype=float)
    for channel in range(len(p['powers'])):
        a0 = 0.8 + 0.07 * channel
        a1 = -0.2 + 0.025 * channel
        mean = a0 * shape(0.82, times) + a1 * shape(1.43, times)
        shared = rng.normal(0.0, 0.003, size=(40, 1))
        noise = rng.normal(0.0, 0.001, size=(40, len(times)))
        data[:, channel] = mean[None, :] * (1.0 + shared) + noise
    return TwoStateFit(blocks(data, 5), p, [4, 5, 6, 7, 8])


def _manifest(planned=2, label='fixture'):
    return {'record_type': 'run_manifest', 'schema': 'test-v1',
            'planned_draws': planned, 'label': label}


def test_checkpoint_repairs_only_torn_final_row_and_commits_completion(tmp_path):
    path = tmp_path / 'journal'
    manifest = _manifest()
    with BootstrapCheckpoint(path, manifest) as checkpoint:
        checkpoint.append({'record_type': 'bootstrap_draw', 'draw_id': 0,
                           'fit': {'cost': 1.25}})
        first_hash = checkpoint.receipt()['last_record_sha256']
        assert checkpoint.receipt()['status'] == 'incomplete_resumable'

    with (path / 'draws.jsonl').open('ab') as stream:
        stream.write(b'{"record_type":"bootstrap_draw","draw_id":1')

    with BootstrapCheckpoint(path, manifest, resume=True) as checkpoint:
        assert checkpoint.completed_draws == 1
        assert checkpoint.receipt()['last_record_sha256'] == first_hash
        checkpoint.append({'record_type': 'bootstrap_draw', 'draw_id': 1,
                           'fit': {'cost': 0.75}})
        assert checkpoint.receipt()['status'] == 'complete'
        assert checkpoint.receipt()['completed_draws'] == 2
        assert checkpoint.receipt()['physical_score'] is None

    rows = [json.loads(line) for line in (path / 'draws.jsonl').read_text().splitlines()]
    assert [row['draw_id'] for row in rows] == [0, 1]
    assert rows[0]['record_sha256'] == first_hash
    status = json.loads((path / 'status.json').read_text())
    assert status['status'] == 'complete'
    assert status['physical_score'] is None
    with pytest.raises(FileExistsError):
        BootstrapCheckpoint(path, manifest)


def test_checkpoint_refuses_manifest_mismatch_and_complete_corruption(tmp_path):
    path = tmp_path / 'journal'
    manifest = _manifest()
    with BootstrapCheckpoint(path, manifest) as checkpoint:
        checkpoint.append({'record_type': 'bootstrap_draw', 'draw_id': 0, 'fit': {}})
    original = (path / 'draws.jsonl').read_bytes()

    with pytest.raises(ValueError, match='identity'):
        BootstrapCheckpoint(path, _manifest(label='changed'), resume=True)
    assert (path / 'draws.jsonl').read_bytes() == original

    with (path / 'draws.jsonl').open('ab') as stream:
        stream.write(b'not-json\n')
    with pytest.raises(ValueError, match='invalid JSON'):
        BootstrapCheckpoint(path, manifest, resume=True)


def test_checkpoint_rejects_out_of_order_and_non_strict_json(tmp_path):
    path = tmp_path / 'journal'
    with BootstrapCheckpoint(path, _manifest()):
        pass
    with BootstrapCheckpoint(path, _manifest(), resume=True) as checkpoint:
        with pytest.raises(ValueError, match='expected draw_id=0'):
            checkpoint.append({'record_type': 'bootstrap_draw', 'draw_id': 1})
        with pytest.raises(TypeError, match='not JSON serializable'):
            checkpoint.append({'record_type': 'bootstrap_draw', 'draw_id': 0,
                               'unhandled': object()})


def test_checkpoint_allows_only_one_active_writer(tmp_path):
    path = tmp_path / 'journal'
    manifest = _manifest()
    with BootstrapCheckpoint(path, manifest):
        with pytest.raises(RuntimeError, match='active writer'):
            BootstrapCheckpoint(path, manifest, resume=True)


def test_runner_resumes_after_solver_interruption_and_retains_committed_draw(tmp_path, monkeypatch):
    fit = _fit()
    indices = np.asarray([
        np.arange(len(fit.samples)),
        np.arange(len(fit.samples))[::-1],
    ], dtype=np.int64)
    starts = [[0.82, 0.0], [0.78, 0.62]]
    block_ids = [[5 * block + offset for offset in range(5)]
                 for block in range(len(fit.samples))]
    path = tmp_path / 'run'
    original = fit.fit_full_multistart
    calls = {'count': 0}

    def fail_on_second_draw(mean, candidate_starts, **kwargs):
        calls['count'] += 1
        if calls['count'] == 2:
            raise RuntimeError('injected interruption after one committed draw')
        return original(mean, candidate_starts, **kwargs)

    monkeypatch.setattr(fit, 'fit_full_multistart', fail_on_second_draw)
    with pytest.raises(RuntimeError, match='injected interruption'):
        run_checkpointed_bootstrap(
            fit, indices, starts, path, block_configuration_ids=block_ids, maxiter=2,
        )

    stored = json.loads((path / 'manifest.json').read_text())['manifest']
    with BootstrapCheckpoint(path, stored, resume=True) as checkpoint:
        assert checkpoint.completed_draws == 1
        first_hash = checkpoint.receipt()['last_record_sha256']

    monkeypatch.setattr(fit, 'fit_full_multistart', original)
    receipt = run_checkpointed_bootstrap(
        fit, indices, starts, path, block_configuration_ids=block_ids,
        resume=True, maxiter=2,
    )
    assert receipt['status'] == 'complete'
    assert receipt['planned_draws'] == receipt['completed_draws'] == 2
    assert receipt['physical_score'] is None
    rows = [json.loads(line) for line in (path / 'draws.jsonl').read_text().splitlines()]
    assert [row['draw_id'] for row in rows] == [0, 1]
    assert rows[0]['record_sha256'] == first_hash
    stored_manifest = json.loads((path / 'manifest.json').read_text())['manifest']
    assert stored_manifest['block_configuration_ids'] == block_ids
    assert len(stored_manifest['block_configuration_ids_sha256']) == 64
    assert stored_manifest['fit_samples_shape'] == list(fit.samples.shape)
    assert len(stored_manifest['fit_samples_sha256']) == 64
    assert stored_manifest['fit_channel_scales'] == fit.scales.tolist()
    assert len(stored_manifest['fit_channel_scales_sha256']) == 64
    json.dumps(rows, allow_nan=False)
    assert all('solver_success' in item for row in rows for item in row['fit']['rows'])
