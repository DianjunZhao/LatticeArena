import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

import tasks.wilson_loop.measure as measure_mod
from tasks.wilson_loop.measure import measurement_input_manifest


def _manifest(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    ensemble = tmp_path / 'ensemble'
    ensemble.mkdir()
    rows = []
    for cfg in range(4):
        path = ensemble / f'wilson_b6.{cfg}'
        payload = f'raw-config-{cfg}'.encode()
        path.write_bytes(payload)
        rows.append({'id': cfg, 'trajectory': 401 + 5 * cfg,
                     'sha256': hashlib.sha256(payload).hexdigest()})
    manifest = {'schema': 'hmc-manifest-test-v1', 'ensemble': 'S16T16D',
                'lattice': [16, 16, 16, 16], 'configs': rows}
    manifest_path = tmp_path / 'manifest.json'
    raw = json.dumps(manifest, sort_keys=True).encode()
    manifest_path.write_bytes(raw)
    protocol = {
        'ensemble': str(ensemble), 'geometry': [16, 16, 16, 16],
        'development': [0, 1], 'gap': [2, 2], 'validation': [3, 3],
        'measurement_splits': ['development', 'validation'],
        'source_hashes': {'measure.py': hashlib.sha256(
            Path(measure_mod.__file__).read_bytes()).hexdigest()},
        'input_manifest': {'path': str(manifest_path),
                           'sha256': hashlib.sha256(raw).hexdigest(),
                           'schema': manifest['schema'], 'ensemble': 'S16T16D'},
    }
    return protocol


def test_manifest_preflight_resolves_only_requested_split(tmp_path):
    p = _manifest(tmp_path)
    rows = measurement_input_manifest(p, 'development', [0, 1])
    assert list(rows) == [0, 1]
    assert rows[1]['trajectory'] == 406
    with pytest.raises(ValueError, match='not authorized'):
        measurement_input_manifest(p, 'shared_holdout', [2])
    with pytest.raises(ValueError, match='escape'):
        measurement_input_manifest(p, 'development', [0, 2])


def test_manifest_preflight_rejects_identity_and_missing_rows(tmp_path):
    p = _manifest(tmp_path)
    p['input_manifest']['sha256'] = '0' * 64
    with pytest.raises(ValueError, match='manifest hash mismatch'):
        measurement_input_manifest(p, 'development', [0])
    p = _manifest(tmp_path / 'source-hash')
    p['source_hashes'] = {'measure.py': '0' * 64}
    with pytest.raises(ValueError, match='task source hash mismatch'):
        measurement_input_manifest(p, 'development', [0])
    p = _manifest(tmp_path / 'again')
    p['validation'] = [3, 9]
    with pytest.raises(ValueError, match='does not contain requested IDs'):
        measurement_input_manifest(p, 'validation', [9])


def test_measurement_binds_raw_gauge_sha_before_transfer(tmp_path, monkeypatch):
    ensemble = tmp_path / 'ensemble'
    ensemble.mkdir()
    gauge = ensemble / 'wilson_b6.0'
    header = (b'BEGIN_HEADER\nDATATYPE=4D_SU3_GAUGE_3x3\n'
              b'DIMENSION_1=1\nDIMENSION_2=1\nDIMENSION_3=1\nDIMENSION_4=1\n'
              b'FLOATING_POINT=IEEE64LITTLE\nEND_HEADER\n')
    field = np.broadcast_to(np.eye(3, dtype='<c16'), (1, 1, 1, 1, 4, 3, 3)).copy()
    gauge_bytes = header + field.tobytes()
    gauge.write_bytes(gauge_bytes)
    manifest_path = tmp_path / 'manifest.json'
    manifest = {'schema': 'hmc-manifest-test-v1', 'ensemble': 'S16T16D',
                'lattice': [1, 1, 1, 1], 'beta': 6.0, 'seed': 20261120, 'configs': [
                    {'id': 0, 'trajectory': 401,
                     'sha256': hashlib.sha256(gauge_bytes).hexdigest()}]}

    def save_manifest():
        raw = json.dumps(manifest, sort_keys=True).encode()
        manifest_path.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    protocol = {
        'version': 'manifest-measure-test', 'ensemble': str(ensemble),
        'geometry': [1, 1, 1, 1], 'development': [0, 0], 'gap': [1, 1],
        'validation': [2, 2], 'measurement_splits': ['development'],
        'r_values': [1], 't_values': [1], 'fit_window': [1],
        'reference_windows': [[1]], 'reference_nominal_window': 0,
        'kernels': [{'name': 'identity', 'kind': 'ape', 'alpha': 0.0, 'steps': 0}],
        'reference_kernel': 0, 'block_length': 1, 'bootstrap_samples': 10, 'seed': 5,
        'reference_max_relative_se': 0.05, 'reference_max_window_z': 2.5,
        'score_epsilon': 1e-12,
        'source_hashes': {'measure.py': hashlib.sha256(
            Path(measure_mod.__file__).read_bytes()).hexdigest()},
        'input_manifest': {'path': str(manifest_path), 'sha256': save_manifest(),
                           'schema': manifest['schema'], 'ensemble': manifest['ensemble'],
                           'beta': 6.0, 'hmc_seed': 20261120},
    }
    monkeypatch.setattr(measure_mod, 'protocol', lambda: protocol)
    records = measure_mod.measure(tmp_path / 'matched', 'development')
    assert records[0]['gauge_sha256'] == manifest['configs'][0]['sha256']
    assert records[0]['hmc_trajectory'] == 401
    assert records[0]['kernel_seconds'] >= 0 and records[0]['loop_seconds'] >= 0

    manifest['configs'][0]['sha256'] = '0' * 64
    protocol['input_manifest']['sha256'] = save_manifest()
    with pytest.raises(ValueError, match='raw gauge SHA-256 differs'):
        measure_mod.measure(tmp_path / 'mismatched', 'development')
