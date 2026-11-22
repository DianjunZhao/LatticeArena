import hashlib
import json
import sys

import pytest

from tasks.optimize_gaussian.worker_runspec import run_frozen_worker


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_spec(tmp_path, *, split_ids=None):
    protocol = tmp_path / 'protocol.json'
    protocol.write_text('{"protocol":"fixture-v1"}\n')
    source = tmp_path / 'worker_source.py'
    source.write_text('# fixture source identity\n')
    input_file = tmp_path / 'synthetic_input.dat'
    input_file.write_text('fixture input\n')
    outputs = {
        'receipt': tmp_path / 'receipt.json',
        'stdout': tmp_path / 'worker.stdout',
        'stderr': tmp_path / 'worker.stderr',
    }
    spec = {
        'schema': 'optgauss-worker-runspec-v2',
        'run_id': 'fixture-run-001',
        'command': [sys.executable, '-c', "print('worker-started', flush=True)"],
        'cwd': str(tmp_path),
        'timeout_seconds': 3.0,
        'terminate_grace_seconds': 0.1,
        'environment': {'RUNSPEC_MODE': 'frozen'},
        'files': {
            'protocol': {'path': str(protocol), 'sha256': _hash(protocol), 'role': 'protocol'},
            'worker_source': {'path': str(source), 'sha256': _hash(source), 'role': 'source'},
            'synthetic_input': {'path': str(input_file), 'sha256': _hash(input_file), 'role': 'input'},
        },
        'split_ids': split_ids,
        'outputs': {name: str(path) for name, path in outputs.items()},
    }
    spec_path = tmp_path / 'runspec.json'
    spec_path.write_text(json.dumps(spec, sort_keys=True, indent=2) + '\n')
    return spec_path, spec, protocol, source, input_file, outputs


def test_frozen_runspec_verifies_identity_before_supervised_launch(tmp_path):
    spec_path, spec, _, _, _, outputs = _make_spec(
        tmp_path, split_ids={'fit': [1, 2], 'development': [3], 'blind': [4]})

    receipt = run_frozen_worker(spec_path)

    assert receipt['status'] == 'completed'
    assert receipt['physical_score'] is None
    assert receipt['identity']['run_spec_schema'] == spec['schema']
    assert receipt['identity']['run_id'] == spec['run_id']
    assert receipt['identity']['split_ids'] == {
        'fit': [1, 2], 'development': [3], 'blind': [4]}
    assert receipt['identity']['preflight']['status'] == 'verified'
    assert receipt['identity']['files']['protocol']['sha256'] == spec['files']['protocol']['sha256']
    assert receipt['environment_sha256'] == receipt['identity']['environment_sha256']
    assert receipt['environment_keys'] == ['RUNSPEC_MODE']
    assert outputs['stdout'].read_text() == 'worker-started\n'


def test_frozen_runspec_does_not_inherit_unbound_parent_environment(tmp_path, monkeypatch):
    spec_path, spec, _, _, _, _ = _make_spec(tmp_path)
    monkeypatch.setenv('LATTICEARENA_UNBOUND_SENTINEL', 'ambient-value')
    spec['command'] = [
        sys.executable, '-c',
        "import os; print(os.getenv('RUNSPEC_MODE') + '|' + "
        "os.getenv('LATTICEARENA_UNBOUND_SENTINEL', 'missing'), flush=True)",
    ]
    spec_path.write_text(json.dumps(spec, sort_keys=True, indent=2) + '\n')

    receipt = run_frozen_worker(spec_path)

    assert receipt['status'] == 'completed'
    assert (tmp_path / 'worker.stdout').read_text() == 'frozen|missing\n'
    assert 'LATTICEARENA_UNBOUND_SENTINEL' not in receipt['environment_keys']


@pytest.mark.parametrize('binding', ['protocol', 'worker_source', 'synthetic_input'])
def test_frozen_runspec_refuses_changed_bound_file_before_launch(tmp_path, binding):
    spec_path, spec, protocol, source, input_file, outputs = _make_spec(tmp_path)
    target = {'protocol': protocol, 'worker_source': source,
              'synthetic_input': input_file}[binding]
    target.write_text(target.read_text() + '# changed after freeze\n')

    with pytest.raises(ValueError, match='hash mismatch'):
        run_frozen_worker(spec_path)

    assert not outputs['receipt'].exists()
    assert not outputs['stdout'].exists()
    assert not outputs['stderr'].exists()


def test_frozen_runspec_rejects_overlapping_split_ids_before_launch(tmp_path):
    spec_path, _, _, _, _, outputs = _make_spec(
        tmp_path, split_ids={'fit': [1, 2], 'test': [2, 3]})

    with pytest.raises(ValueError, match='overlaps splits'):
        run_frozen_worker(spec_path)

    assert not outputs['receipt'].exists()


def test_frozen_runspec_rejects_duplicate_json_keys(tmp_path):
    spec_path, _, _, _, _, outputs = _make_spec(tmp_path)
    spec_path.write_text('{"schema":"optgauss-worker-runspec-v2", "schema":"other"}')

    with pytest.raises(ValueError, match='duplicate JSON key'):
        run_frozen_worker(spec_path)

    assert not outputs['receipt'].exists()


def test_frozen_runspec_refuses_existing_output_without_running_worker(tmp_path):
    spec_path, _, _, _, _, outputs = _make_spec(tmp_path)
    outputs['stdout'].write_text('preserve me')

    with pytest.raises(FileExistsError, match='refusing to overwrite stdout'):
        run_frozen_worker(spec_path)

    assert outputs['stdout'].read_text() == 'preserve me'
    assert not outputs['receipt'].exists()


def test_frozen_runspec_hashes_declared_training_artifacts_into_parent_receipt(tmp_path):
    spec_path, spec, _, _, _, outputs = _make_spec(tmp_path)
    run_dir = tmp_path / 'new-training-output'
    results = run_dir / 'results.json'
    manifest = run_dir / 'manifest.json'
    assert not run_dir.exists()
    spec['outputs']['artifacts'] = {
        'results': str(results), 'manifest': str(manifest)}
    spec['command'] = [
        sys.executable, '-c',
        "from pathlib import Path; import sys; "
        "Path(sys.argv[1]).parent.mkdir(parents=True); "
        "Path(sys.argv[1]).write_bytes(b'{\\\"test_risk\\\":1}\\n'); "
        "Path(sys.argv[2]).write_bytes(b'{\\\"run\\\":\\\"fixture\\\"}\\n')",
        str(results), str(manifest),
    ]
    spec_path.write_text(json.dumps(spec, sort_keys=True, indent=2) + '\n')

    receipt = run_frozen_worker(spec_path)

    assert receipt['status'] == 'completed'
    assert receipt['artifact_output_status'] == 'verified'
    assert receipt['artifact_outputs']['results']['sha256'] == _hash(results)
    assert receipt['artifact_outputs']['manifest']['sha256'] == _hash(manifest)
    assert run_dir.is_dir()
    assert json.loads(outputs['receipt'].read_text()) == receipt


def test_frozen_runspec_does_not_accept_artifacts_from_failed_worker(tmp_path):
    spec_path, spec, _, _, _, outputs = _make_spec(tmp_path)
    partial = tmp_path / 'partial-results.json'
    spec['outputs']['artifacts'] = {'results': str(partial)}
    spec['command'] = [
        sys.executable, '-c',
        "from pathlib import Path; import sys; "
        "Path(sys.argv[1]).write_text('partial'); raise SystemExit(7)",
        str(partial),
    ]
    spec_path.write_text(json.dumps(spec, sort_keys=True, indent=2) + '\n')

    receipt = run_frozen_worker(spec_path)

    assert receipt['status'] == 'worker_failed'
    assert receipt['artifact_output_status'] == 'not_accepted'
    assert receipt['artifact_outputs']['results']['sha256'] is None
    assert receipt['artifact_outputs']['results']['error']['type'] == 'UnacceptedArtifact'
    assert partial.read_text() == 'partial'
    assert json.loads(outputs['receipt'].read_text()) == receipt


def test_frozen_runspec_hashes_failure_diagnostics_without_accepting_run(tmp_path):
    spec_path, spec, _, _, _, outputs = _make_spec(tmp_path)
    diagnostic = tmp_path / 'solver-rejection.json'
    payload = '{"classification":"diagnostic_only","physical_score":null}\n'
    spec['outputs']['diagnostics'] = {'solver_contract_rejection': str(diagnostic)}
    spec['command'] = [
        sys.executable, '-c',
        "from pathlib import Path; import sys; "
        "Path(sys.argv[1]).write_text(sys.argv[2]); raise SystemExit(2)",
        str(diagnostic), payload,
    ]
    spec_path.write_text(json.dumps(spec, sort_keys=True, indent=2) + '\n')

    receipt = run_frozen_worker(spec_path)

    assert receipt['status'] == 'worker_failed'
    assert receipt['physical_score'] is None
    assert receipt['artifact_output_status'] == 'not_declared'
    assert receipt['failure_diagnostic_status'] == 'observed'
    assert receipt['failure_diagnostic_outputs']['solver_contract_rejection']['sha256'] == _hash(diagnostic)
    assert receipt['failure_diagnostic_outputs']['solver_contract_rejection']['error'] is None
    assert diagnostic.read_text() == payload
    assert json.loads(outputs['receipt'].read_text()) == receipt


def test_frozen_runspec_marks_optional_missing_failure_diagnostic(tmp_path):
    spec_path, spec, _, _, _, outputs = _make_spec(tmp_path)
    diagnostic = tmp_path / 'not-produced.json'
    spec['outputs']['diagnostics'] = {'solver_contract_rejection': str(diagnostic)}
    spec_path.write_text(json.dumps(spec, sort_keys=True, indent=2) + '\n')

    receipt = run_frozen_worker(spec_path)

    assert receipt['status'] == 'completed'
    assert receipt['artifact_output_status'] == 'not_declared'
    assert receipt['failure_diagnostic_status'] == 'not_present'
    assert receipt['failure_diagnostic_outputs']['solver_contract_rejection']['sha256'] is None
    assert receipt['failure_diagnostic_outputs']['solver_contract_rejection']['error']['type'] == 'FileNotFoundError'
    assert json.loads(outputs['receipt'].read_text()) == receipt


def test_frozen_runspec_marks_missing_success_artifact_incomplete(tmp_path):
    spec_path, spec, _, _, _, outputs = _make_spec(tmp_path)
    missing = tmp_path / 'missing-results.json'
    spec['outputs']['artifacts'] = {'results': str(missing)}
    spec['command'] = [sys.executable, '-c', "print('worker-done')"]
    spec_path.write_text(json.dumps(spec, sort_keys=True, indent=2) + '\n')

    receipt = run_frozen_worker(spec_path)

    assert receipt['status'] == 'completed'
    assert receipt['artifact_output_status'] == 'incomplete_or_unreadable'
    assert receipt['artifact_outputs']['results']['sha256'] is None
    assert receipt['artifact_outputs']['results']['error']['type'] == 'FileNotFoundError'
    assert json.loads(outputs['receipt'].read_text()) == receipt


def test_frozen_runspec_refuses_preexisting_artifact_before_launch(tmp_path):
    spec_path, spec, _, _, _, outputs = _make_spec(tmp_path)
    artifact = tmp_path / 'existing-results.json'
    artifact.write_text('preserve')
    spec['outputs']['artifacts'] = {'results': str(artifact)}
    spec_path.write_text(json.dumps(spec, sort_keys=True, indent=2) + '\n')

    with pytest.raises(FileExistsError, match='artifact output'):
        run_frozen_worker(spec_path)

    assert artifact.read_text() == 'preserve'
    assert not outputs['receipt'].exists()
    assert not outputs['stdout'].exists()


@pytest.mark.skipif(sys.platform == 'win32', reason='requires POSIX process groups')
def test_frozen_runspec_rejects_artifacts_if_successful_leader_leaves_descendant(tmp_path):
    spec_path, spec, _, _, _, outputs = _make_spec(tmp_path)
    results = tmp_path / 'results.json'
    spec['outputs']['artifacts'] = {'results': str(results)}
    spec['command'] = [
        sys.executable, '-c',
        "import subprocess, sys; from pathlib import Path; "
        "Path(sys.argv[1]).write_text('result'); "
        "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)'])",
        str(results),
    ]
    spec_path.write_text(json.dumps(spec, sort_keys=True, indent=2) + '\n')

    receipt = run_frozen_worker(spec_path)

    assert receipt['worker_group_leaked'] is True
    assert receipt['termination']['complete'] is True
    assert receipt['status'] == 'worker_failed'
    assert receipt['artifact_output_status'] == 'not_accepted'
    assert receipt['artifact_outputs']['results']['sha256'] is None
    assert json.loads(outputs['receipt'].read_text()) == receipt


@pytest.mark.parametrize(
    ('artifact_status', 'expected_exit'),
    [('incomplete_or_unreadable', 1), ('not_declared', 0)],
)
def test_worker_cli_exit_status_reflects_declared_artifact_completeness(
        monkeypatch, artifact_status, expected_exit):
    from tasks.optimize_gaussian import worker_runspec

    monkeypatch.setattr(worker_runspec, 'run_frozen_worker', lambda _: {
        'status': 'completed', 'artifact_output_status': artifact_status,
        'physical_score': None,
    })

    assert worker_runspec.main(['synthetic-runspec.json']) == expected_exit
