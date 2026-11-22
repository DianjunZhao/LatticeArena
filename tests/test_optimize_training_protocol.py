import hashlib
import json

import pytest

from tasks.optimize_gaussian import train


def test_protocol_loads_exact_hash_bound_file(tmp_path):
    protocol_path = tmp_path / 'frozen-protocol.json'
    raw = b'{"output":"diagnostic-run","seeds":[4]}'
    protocol_path.write_bytes(raw)
    expected = hashlib.sha256(raw).hexdigest()

    assert train.protocol(protocol_path, expected) == {
        'output': 'diagnostic-run', 'seeds': [4],
    }


def test_train_main_rejects_protocol_hash_drift_before_output_or_gpu(tmp_path, monkeypatch):
    protocol_path = tmp_path / 'frozen-protocol.json'
    protocol_path.write_text(json.dumps({'output': str(tmp_path / 'run')}))
    output = tmp_path / 'run'

    def gpu_must_not_start(_protocol):
        pytest.fail('GPU initialization must not occur before protocol verification')

    monkeypatch.setattr(train, 'init_quda', gpu_must_not_start)
    with pytest.raises(SystemExit) as exc:
        train.main([
            str(output), '--protocol', str(protocol_path), '--protocol-sha256', '0' * 64,
        ])

    assert exc.value.code == 2
    assert not output.exists()


def test_train_main_requires_solver_contract_for_explicit_protocol(tmp_path, monkeypatch):
    protocol_path = tmp_path / 'frozen-protocol.json'
    payload = {'output': str(tmp_path / 'run'), 'optimizer': {'maxiter': 4}}
    protocol_path.write_text(json.dumps(payload))
    expected = hashlib.sha256(protocol_path.read_bytes()).hexdigest()
    output = tmp_path / 'run'

    monkeypatch.setattr(
        train, 'init_quda',
        lambda _protocol: pytest.fail('GPU initialization must not precede policy validation'),
    )
    with pytest.raises(SystemExit) as exc:
        train.main([
            str(output), '--protocol', str(protocol_path), '--protocol-sha256', expected,
        ])

    assert exc.value.code == 2
    assert not output.exists()


def test_train_main_requires_protocol_path_and_hash_as_a_pair(tmp_path):
    protocol_path = tmp_path / 'frozen-protocol.json'
    protocol_path.write_text('{}')
    output = tmp_path / 'run'

    with pytest.raises(SystemExit) as exc:
        train.main([str(output), '--protocol', str(protocol_path)])

    assert exc.value.code == 2
    assert not output.exists()


@pytest.mark.parametrize('payload', ['[]', 'null', '"not-an-object"'])
def test_protocol_rejects_non_object_json_roots(tmp_path, payload):
    protocol_path = tmp_path / 'frozen-protocol.json'
    protocol_path.write_text(payload)
    expected = hashlib.sha256(protocol_path.read_bytes()).hexdigest()

    with pytest.raises(ValueError, match='root must be a JSON object'):
        train.protocol(protocol_path, expected)
