import hashlib
import json
from pathlib import Path
import sys

import pytest

from tasks.optimize_gaussian.runspec_builder import (
    SOURCE_PATHS,
    build_optimize_runspec,
    main,
    write_optimize_runspec,
)
from tasks.optimize_gaussian.worker_runspec import run_frozen_worker


def _write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if isinstance(value, bytes) else value.encode())
    return path


def _fixture(root, *, split_override=None, missing_cache_id=None):
    root = Path(root)
    for source in SOURCE_PATHS:
        _write(root / source, f'fixture source: {source}\n')
    ensemble = root / 'data' / 'S16T16-fixture'
    prop_dir = root / '.cache' / 'pion_projection' / 'propagators'
    dev_rows = [{'id': 0, 'cache_key': 'k0'}, {'id': 1, 'cache_key': 'k1'}]
    val_rows = [{'id': 2, 'cache_key': 'k2'}]
    if missing_cache_id is not None:
        dev_rows = [row for row in dev_rows if row['id'] != missing_cache_id]
        val_rows = [row for row in val_rows if row['id'] != missing_cache_id]
    cache_manifest = _write(
        root / 'inputs' / 'cache_manifest.json',
        json.dumps({'records': dev_rows}),
    )
    validation_manifest = _write(
        root / 'inputs' / 'validation_manifest.json',
        json.dumps({'records': val_rows}),
    )
    bootstrap = _write(root / 'inputs' / 'reference_bootstrap.npz', b'synthetic bootstrap')
    for cfg_id, key in ((0, 'k0'), (1, 'k1'), (2, 'k2')):
        _write(ensemble / f'wilson_b6.{cfg_id}', f'gauge fixture {cfg_id}\n')
        _write(prop_dir / f'{key}.npy', f'propagator fixture {cfg_id}\n')
        _write(prop_dir / f'{key}.json', json.dumps({'fixture_id': cfg_id}))

    protocol = {
        'version': 'synthetic-optimize-protocol-v1',
        'ensemble': str(ensemble),
        'fit': [0, 0],
        'dev_val': [1, 1],
        'test': [2, 2],
        'seeds': [11, 12],
        # Deliberately permissive synthetic policy for the CPU fixture only;
        # production thresholds remain research decisions.
        'optimizer': {
            'maxiter': 4,
            'solver_contract': {
                'objective_call_cap': 100,
                'walltime_cap_seconds': 60.0,
                'residual_field': 'kkt_residual',
                'residual_tolerance': 1.0,
                'require_solver_success': True,
            },
        },
        'cache_manifest': str(cache_manifest.relative_to(root)),
        'validation_manifest': str(validation_manifest.relative_to(root)),
        'reference_bootstrap': str(bootstrap.relative_to(root)),
    }
    if split_override:
        protocol.update(split_override)
    protocol_path = _write(root / 'protocols' / 'optimize.json',
                           json.dumps(protocol, sort_keys=True))
    receipts = root / 'results' / 'receipts'
    receipts.mkdir(parents=True)
    output = root / 'results' / 'runs' / 'run-001'
    return root, protocol_path, output, receipts


def test_builder_binds_protocol_sources_splits_and_all_consumed_inputs(tmp_path):
    root, protocol_path, output, receipts = _fixture(tmp_path / 'repo')

    spec = build_optimize_runspec(
        protocol_path,
        output_directory=output,
        receipt_directory=receipts,
        run_id='fixture-run-001',
        timeout_seconds=60,
        terminate_grace_seconds=2,
        environment={'PYTHONHASHSEED': '0'},
        repo_root=root,
    )

    assert spec['split_ids'] == {'fit': [0], 'dev_val': [1], 'test': [2]}
    protocol_binding = spec['files']['protocol']
    assert protocol_binding['sha256'] == hashlib.sha256(protocol_path.read_bytes()).hexdigest()
    assert {'--protocol', '--protocol-sha256'} <= set(spec['command'])
    assert str(output / 'results.json') == spec['outputs']['artifacts']['results']
    assert str(output / 'manifest.json') == spec['outputs']['artifacts']['manifest']
    assert str(output / 'data.npz') == spec['outputs']['artifacts']['data']
    assert str(output / 'basis_s11.npz') == spec['outputs']['artifacts']['basis_seed_11']
    assert str(output / 'basis_s12.npz') == spec['outputs']['artifacts']['basis_seed_12']
    assert spec['outputs']['diagnostics']['solver_contract_rejection'] == str(
        output / 'optimizer_contract_rejection.json')
    assert not output.exists()
    bound_paths = {entry['path'] for entry in spec['files'].values()}
    for cfg_id in (0, 1, 2):
        assert str(root / 'data' / 'S16T16-fixture' / f'wilson_b6.{cfg_id}') in bound_paths
        assert str(root / '.cache/pion_projection/propagators' / f'k{cfg_id}.npy') in bound_paths
        assert str(root / '.cache/pion_projection/propagators' / f'k{cfg_id}.json') in bound_paths
    assert any(path.endswith('/tasks/optimize_gaussian/solver_contract.py') for path in bound_paths)

    spec_path = write_optimize_runspec(receipts / 'fixture-run-001.runspec.json', spec)
    assert json.loads(spec_path.read_text()) == spec
    with pytest.raises(FileExistsError):
        write_optimize_runspec(spec_path, spec)


def test_builder_rejects_overlapping_protocol_splits_before_writing(tmp_path):
    root, protocol_path, output, receipts = _fixture(
        tmp_path / 'repo', split_override={'dev_val': [0, 1]})

    with pytest.raises(ValueError, match='overlaps'):
        build_optimize_runspec(
            protocol_path,
            output_directory=output,
            receipt_directory=receipts,
            run_id='fixture-run-overlap',
            timeout_seconds=60,
            terminate_grace_seconds=2,
            environment={'PYTHONHASHSEED': '0'},
            repo_root=root,
        )

    assert not any(receipts.iterdir())
    assert not output.exists()


def test_builder_requires_an_explicit_solver_policy_before_binding_inputs(tmp_path):
    root, protocol_path, output, receipts = _fixture(tmp_path / 'repo')
    protocol = json.loads(protocol_path.read_text())
    del protocol['optimizer']['solver_contract']
    protocol_path.write_text(json.dumps(protocol, sort_keys=True))

    with pytest.raises(ValueError, match='require an explicit optimizer.solver_contract'):
        build_optimize_runspec(
            protocol_path,
            output_directory=output,
            receipt_directory=receipts,
            run_id='fixture-run-no-solver-policy',
            timeout_seconds=60,
            terminate_grace_seconds=2,
            environment={'PYTHONHASHSEED': '0'},
            repo_root=root,
        )

    assert not any(receipts.iterdir())
    assert not output.exists()


def test_builder_rejects_manifest_missing_any_planned_configuration(tmp_path):
    root, protocol_path, output, receipts = _fixture(
        tmp_path / 'repo', missing_cache_id=1)

    with pytest.raises(ValueError, match=r'missing protocol configuration IDs: \[1\]'):
        build_optimize_runspec(
            protocol_path,
            output_directory=output,
            receipt_directory=receipts,
            run_id='fixture-run-missing-cache',
            timeout_seconds=60,
            terminate_grace_seconds=2,
            environment={'PYTHONHASHSEED': '0'},
            repo_root=root,
        )

    assert not any(receipts.iterdir())


def test_builder_cli_prepares_spec_without_starting_training(tmp_path, capsys):
    root, protocol_path, output, receipts = _fixture(tmp_path / 'repo')
    request = {
        'protocol_path': str(protocol_path),
        'output_directory': str(output),
        'receipt_directory': str(receipts),
        'run_id': 'fixture-cli-run',
        'timeout_seconds': 60,
        'terminate_grace_seconds': 2,
        'environment': {'PYTHONHASHSEED': '0'},
        'repo_root': str(root),
    }
    request_path = _write(root / 'requests' / 'prepare.json', json.dumps(request))
    spec_path = receipts / 'fixture-cli-run.runspec.json'

    assert main([str(request_path), str(spec_path)]) == 0

    result = json.loads(capsys.readouterr().out)
    assert result['status'] == 'prepared_not_executed'
    assert result['physical_score'] is None
    assert spec_path.is_file()
    assert not output.exists()


@pytest.mark.skipif(sys.platform == 'win32', reason='requires POSIX process groups')
def test_built_runspec_crosses_supervisor_boundary_and_hashes_cpu_fixture_outputs(tmp_path):
    """Exercise builder -> frozen supervisor with a CPU-only fake worker."""
    root, protocol_path, output, receipts = _fixture(tmp_path / 'repo')
    spec = build_optimize_runspec(
        protocol_path,
        output_directory=output,
        receipt_directory=receipts,
        run_id='fixture-e2e-run',
        timeout_seconds=10,
        terminate_grace_seconds=1,
        environment={'PYTHONHASHSEED': '0'},
        repo_root=root,
    )

    # Confirm the prepared production command targets train.main with a
    # byte-bound protocol. Replace only its argv in this isolated fixture so
    # no QUDA, data loading, training, or GPU setup can occur in this test.
    command = spec['command']
    assert command[:4] == [sys.executable, '-B', '-m', 'tasks.optimize_gaussian.train']
    protocol_index = command.index('--protocol')
    protocol_hash_index = command.index('--protocol-sha256')
    assert command[protocol_index + 1] == str(protocol_path.resolve())
    assert command[protocol_hash_index + 1] == hashlib.sha256(protocol_path.read_bytes()).hexdigest()

    artifacts = spec['outputs']['artifacts']
    artifact_names = [Path(path).name for path in artifacts.values()]
    worker_code = (
        'from pathlib import Path; import sys\n'
        'out = Path(sys.argv[1]); out.mkdir(parents=True)\n'
        'for name in sys.argv[2:]:\n'
        '    (out / name).write_text("cpu-fixture:" + name + "\\n")\n'
    )
    spec['command'] = [sys.executable, '-B', '-c', worker_code,
                       str(output), *artifact_names]
    spec_path = write_optimize_runspec(receipts / 'fixture-e2e-run.runspec.json', spec)

    receipt = run_frozen_worker(spec_path)

    assert receipt['status'] == 'completed'
    assert receipt['artifact_output_status'] == 'verified'
    assert receipt['failure_diagnostic_status'] == 'not_present'
    assert receipt['physical_score'] is None
    assert receipt['identity']['split_ids'] == {'fit': [0], 'dev_val': [1], 'test': [2]}
    for label, path in artifacts.items():
        artifact_path = Path(path)
        assert artifact_path.read_text() == f'cpu-fixture:{artifact_path.name}\n'
        assert receipt['artifact_outputs'][label]['sha256'] == hashlib.sha256(
            artifact_path.read_bytes()).hexdigest()
    assert json.loads(Path(spec['outputs']['receipt']).read_text()) == receipt


def test_builder_binds_optional_pion_measurement_and_provenance_receipt(tmp_path):
    root, protocol_path, output, receipts = _fixture(tmp_path / 'repo')
    measurement = _write(root / 'inputs' / 'pion_measurement.npz', b'measurement fixture')
    provenance = _write(root / 'inputs' / 'pion_provenance.json', '{"generation":"fixture"}')
    protocol = json.loads(protocol_path.read_text())
    protocol['propagator_measurement_receipt'] = {
        'measurement_path': str(measurement.relative_to(root)),
        'measurement_sha256': hashlib.sha256(measurement.read_bytes()).hexdigest(),
        'provenance_path': str(provenance.relative_to(root)),
        'provenance_sha256': hashlib.sha256(provenance.read_bytes()).hexdigest(),
        'generation': 'fixture-generation',
        'protocol_hash': 'fixture-protocol-hash',
    }
    protocol_path.write_text(json.dumps(protocol, sort_keys=True))

    spec = build_optimize_runspec(
        protocol_path,
        output_directory=output,
        receipt_directory=receipts,
        run_id='fixture-receipt-run',
        timeout_seconds=60,
        terminate_grace_seconds=2,
        environment={'PYTHONHASHSEED': '0'},
        repo_root=root,
    )

    bound_paths = {entry['path'] for entry in spec['files'].values()}
    assert str(measurement) in bound_paths
    assert str(provenance) in bound_paths


def test_runspec_writer_rejects_path_that_collides_with_worker_receipt(tmp_path):
    root, protocol_path, output, receipts = _fixture(tmp_path / 'repo')
    spec = build_optimize_runspec(
        protocol_path,
        output_directory=output,
        receipt_directory=receipts,
        run_id='fixture-collision-run',
        timeout_seconds=60,
        terminate_grace_seconds=2,
        environment={'PYTHONHASHSEED': '0'},
        repo_root=root,
    )

    with pytest.raises(ValueError, match='collides with a declared worker output'):
        write_optimize_runspec(spec['outputs']['receipt'], spec)

    assert not Path(spec['outputs']['receipt']).exists()


def test_builder_rejects_duplicate_protocol_keys(tmp_path):
    root, protocol_path, output, receipts = _fixture(tmp_path / 'repo')
    protocol_path.write_text('{"fit":[0,0],"fit":[1,1]}')

    with pytest.raises(ValueError, match='duplicate JSON key: fit'):
        build_optimize_runspec(
            protocol_path,
            output_directory=output,
            receipt_directory=receipts,
            run_id='fixture-duplicate-protocol',
            timeout_seconds=60,
            terminate_grace_seconds=2,
            environment={'PYTHONHASHSEED': '0'},
            repo_root=root,
        )

    assert not any(receipts.iterdir())


@pytest.mark.parametrize('seeds, message', [
    ([-1, 12], 'must be nonnegative'),
    ([11, 11], 'must not contain duplicate seeds'),
])
def test_builder_rejects_invalid_seed_lists(tmp_path, seeds, message):
    root, protocol_path, output, receipts = _fixture(tmp_path / 'repo')
    protocol = json.loads(protocol_path.read_text())
    protocol['seeds'] = seeds
    protocol_path.write_text(json.dumps(protocol, sort_keys=True))

    with pytest.raises(ValueError, match=message):
        build_optimize_runspec(
            protocol_path,
            output_directory=output,
            receipt_directory=receipts,
            run_id='fixture-invalid-seeds',
            timeout_seconds=60,
            terminate_grace_seconds=2,
            environment={'PYTHONHASHSEED': '0'},
            repo_root=root,
        )

    assert not any(receipts.iterdir())


def test_builder_rejects_non_object_extra_input_files(tmp_path):
    root, protocol_path, output, receipts = _fixture(tmp_path / 'repo')

    with pytest.raises(ValueError, match='extra_input_files must be an object'):
        build_optimize_runspec(
            protocol_path,
            output_directory=output,
            receipt_directory=receipts,
            run_id='fixture-invalid-extra-inputs',
            timeout_seconds=60,
            terminate_grace_seconds=2,
            environment={'PYTHONHASHSEED': '0'},
            repo_root=root,
            extra_input_files=['unexpected'],
        )

    assert not any(receipts.iterdir())
