"""Build a hash-bound Optimize worker RunSpec from a frozen protocol.

The builder only prepares and validates an execution description. It never
starts training, initializes CUDA/QUDA, or decides whether a physics reference
is valid. Production execution still requires separate review and authorization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from .worker_runspec import SCHEMA, _validate_spec
from .solver_contract import solver_policy_from_mapping


SOURCE_PATHS = (
    'tasks/optimize_gaussian/train.py',
    'tasks/optimize_gaussian/features.py',
    'tasks/optimize_gaussian/kernels.py',
    'tasks/optimize_gaussian/submission.py',
    'tasks/optimize_gaussian/artifacts.py',
    'tasks/optimize_gaussian/solver_contract.py',
    'tasks/optimize_gaussian/worker_runspec.py',
    'tasks/optimize_gaussian/hard_timeout.py',
    'tasks/optimize_gaussian/runspec_builder.py',
    'tasks/pion_projection/common.py',
    'tasks/pion_projection/statistics.py',
    'core/stats.py',
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve(root: Path, value) -> Path:
    path = Path(value)
    return (path if path.is_absolute() else root / path).resolve()


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON key: {key}')
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f'non-finite JSON constant: {value}')


def _read_object_and_hash(path: Path, label: str) -> tuple[dict, str]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw, object_pairs_hook=_reject_duplicate_keys,
                           parse_constant=_reject_constant)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f'{label} is not readable JSON: {path}') from exc
    if not isinstance(value, dict):
        raise ValueError(f'{label} must have a JSON object root: {path}')
    return value, hashlib.sha256(raw).hexdigest()


def _read_object(path: Path, label: str) -> dict:
    return _read_object_and_hash(path, label)[0]


def _ids_from_protocol(protocol: dict) -> dict[str, list[int]]:
    splits = {}
    seen = {}
    for name in ('fit', 'dev_val', 'test'):
        bounds = protocol.get(name)
        if (not isinstance(bounds, list) or len(bounds) != 2
                or any(isinstance(x, bool) or not isinstance(x, int) for x in bounds)):
            raise ValueError(f'protocol.{name} must be a two-integer inclusive range')
        first, last = bounds
        if first < 0 or last < first:
            raise ValueError(f'protocol.{name} has invalid inclusive bounds {bounds}')
        ids = list(range(first, last + 1))
        for cfg_id in ids:
            if cfg_id in seen:
                raise ValueError(
                    f'configuration ID {cfg_id} overlaps {seen[cfg_id]} and {name}')
            seen[cfg_id] = name
        splits[name] = ids
    return splits


def _seeds_from_protocol(protocol: dict) -> list[int]:
    seeds = protocol.get('seeds')
    if (not isinstance(seeds, list) or not seeds
            or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds)):
        raise ValueError('protocol.seeds must be a nonempty list of integer seeds')
    if any(seed < 0 for seed in seeds):
        raise ValueError('protocol.seeds must be nonnegative')
    if len(set(seeds)) != len(seeds):
        raise ValueError('protocol.seeds must not contain duplicate seeds')
    return seeds


def _record_cache_keys(
    root: Path, protocol: dict
) -> tuple[dict[int, str], dict[str, Path], dict[Path, str]]:
    paths = {}
    cache_keys = {}
    input_hashes = {}
    for protocol_key, label in (('cache_manifest', 'cache_manifest'),
                                ('validation_manifest', 'validation_manifest')):
        if not protocol.get(protocol_key):
            raise ValueError(f'protocol.{protocol_key} is required')
        path = _resolve(root, protocol[protocol_key])
        paths[label] = path
        manifest, manifest_hash = _read_object_and_hash(path, label)
        input_hashes[path] = manifest_hash
        records = manifest.get('records')
        if not isinstance(records, list):
            raise ValueError(f'{label}.records must be a list')
        for row in records:
            if not isinstance(row, dict):
                raise ValueError(f'{label}.records contains a non-object row')
            cfg_id, key = row.get('id'), row.get('cache_key')
            if isinstance(cfg_id, bool) or not isinstance(cfg_id, int):
                raise ValueError(f'{label}.records contains a non-integer ID')
            if not isinstance(key, str) or not key:
                raise ValueError(f'{label}.records[{cfg_id}] lacks cache_key')
            if cfg_id in cache_keys:
                raise ValueError(f'configuration ID {cfg_id} is duplicated across cache manifests')
            cache_keys[cfg_id] = key
    return cache_keys, paths, input_hashes


def build_optimize_runspec(
    protocol_path,
    *,
    output_directory,
    receipt_directory,
    run_id,
    timeout_seconds,
    terminate_grace_seconds,
    environment,
    repo_root=None,
    extra_input_files=None,
):
    """Return an optgauss-worker-runspec-v2 dict without writing or launching it.

    Paths used by train.py are resolved relative to ``repo_root`` (the worker
    cwd). Every fit/dev/test gauge, propagator cache, sidecar, reference file,
    protocol, and training dependency is hashed into ``files``.
    """
    root = Path(repo_root or Path(__file__).resolve().parents[2]).resolve()
    protocol_file = _resolve(root, protocol_path)
    protocol, protocol_hash = _read_object_and_hash(protocol_file, 'Optimize protocol')
    optimizer = protocol.get('optimizer')
    if not isinstance(optimizer, dict) or optimizer.get('solver_contract') is None:
        raise ValueError('Optimize RunSpecs require an explicit optimizer.solver_contract policy')
    try:
        solver_policy = solver_policy_from_mapping(optimizer['solver_contract'])
    except ValueError as exc:
        raise ValueError(f'invalid protocol.optimizer.solver_contract: {exc}') from exc
    if solver_policy.residual_field != 'kkt_residual':
        raise ValueError('Optimize solver contract residual_field must be "kkt_residual"')
    snapshot_hashes = {protocol_file: protocol_hash}
    splits = _ids_from_protocol(protocol)
    seeds = _seeds_from_protocol(protocol)
    all_ids = [cfg_id for values in splits.values() for cfg_id in values]

    cache_keys, input_paths, manifest_hashes = _record_cache_keys(root, protocol)
    snapshot_hashes.update(manifest_hashes)
    missing = sorted(set(all_ids) - cache_keys.keys())
    if missing:
        raise ValueError(f'cache manifests are missing protocol configuration IDs: {missing}')

    if not protocol.get('reference_bootstrap'):
        raise ValueError('protocol.reference_bootstrap is required')
    input_paths['reference_bootstrap'] = _resolve(root, protocol['reference_bootstrap'])
    if protocol.get('reference_path'):
        input_paths['reference_path'] = _resolve(root, protocol['reference_path'])

    receipt_binding = protocol.get('propagator_measurement_receipt')
    if receipt_binding is not None:
        if not isinstance(receipt_binding, dict):
            raise ValueError('protocol.propagator_measurement_receipt must be an object')
        for key in ('measurement_path', 'provenance_path'):
            if not receipt_binding.get(key):
                raise ValueError(f'propagator_measurement_receipt.{key} is required')
            input_paths[f'pion_{key}'] = _resolve(root, receipt_binding[key])
        for path_key, hash_key in (('measurement_path', 'measurement_sha256'),
                                   ('provenance_path', 'provenance_sha256')):
            expected = receipt_binding.get(hash_key)
            if expected != _sha256(input_paths[f'pion_{path_key}']):
                raise ValueError(f'propagator_measurement_receipt.{hash_key} mismatch')
            snapshot_hashes[input_paths[f'pion_{path_key}']] = expected

    ensemble = protocol.get('ensemble')
    if not isinstance(ensemble, str) or not ensemble:
        raise ValueError('protocol.ensemble is required to bind gauge inputs')
    ensemble_path = _resolve(root, ensemble)
    propagator_root = root / '.cache/pion_projection/propagators'
    for cfg_id in all_ids:
        gauge = ensemble_path / f'wilson_b6.{cfg_id}'
        cache_base = propagator_root / cache_keys[cfg_id]
        input_paths[f'gauge_{cfg_id}'] = gauge
        input_paths[f'propagator_{cfg_id}'] = cache_base.with_suffix('.npy')
        input_paths[f'propagator_meta_{cfg_id}'] = cache_base.with_suffix('.json')

    if extra_input_files is not None and not isinstance(extra_input_files, dict):
        raise ValueError('extra_input_files must be an object mapping labels to paths')
    for label, value in (extra_input_files or {}).items():
        if not isinstance(label, str) or not label:
            raise ValueError('extra input labels must be nonempty strings')
        if label in input_paths:
            raise ValueError(f'extra input label duplicates protocol input {label!r}')
        input_paths[label] = _resolve(root, value)

    files = {
        'protocol': {'path': str(protocol_file), 'sha256': protocol_hash, 'role': 'protocol'}
    }
    for relative in SOURCE_PATHS:
        path = root / relative
        files[f'source_{relative}'] = {
            'path': str(path), 'sha256': _sha256(path), 'role': 'source'}
    seen_paths = {protocol_file}
    for index, (label, path) in enumerate(input_paths.items()):
        path = path.resolve()
        if path in seen_paths:
            continue
        seen_paths.add(path)
        input_hash = snapshot_hashes.get(path)
        if input_hash is None:
            input_hash = _sha256(path)
        files[f'input_{index:04d}_{label}'] = {
            'path': str(path), 'sha256': input_hash, 'role': 'input'}

    if not isinstance(run_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', run_id):
        raise ValueError('run_id must be a safe, nonempty filename component')
    if not isinstance(environment, dict) or not environment:
        raise ValueError('an explicit nonempty child environment is required')

    training_output = _resolve(root, output_directory)
    receipt_dir = _resolve(root, receipt_directory)
    if training_output.exists():
        raise FileExistsError(f'refusing existing Optimize output directory: {training_output}')
    if not receipt_dir.is_dir():
        raise FileNotFoundError(f'receipt directory must already exist: {receipt_dir}')
    receipt_file = receipt_dir / f'{run_id}.receipt.json'
    stdout_file = receipt_dir / f'{run_id}.stdout.log'
    stderr_file = receipt_dir / f'{run_id}.stderr.log'
    runspec = {
        'schema': SCHEMA,
        'run_id': run_id,
        'command': [
            sys.executable, '-B', '-m', 'tasks.optimize_gaussian.train',
            str(training_output), '--protocol', str(protocol_file),
            '--protocol-sha256', protocol_hash,
        ],
        'cwd': str(root),
        'timeout_seconds': timeout_seconds,
        'terminate_grace_seconds': terminate_grace_seconds,
        'environment': environment,
        'files': files,
        'split_ids': splits,
        'outputs': {
            'receipt': str(receipt_file),
            'stdout': str(stdout_file),
            'stderr': str(stderr_file),
            'artifacts': {
                'results': str(training_output / 'results.json'),
                'manifest': str(training_output / 'manifest.json'),
                'data': str(training_output / 'data.npz'),
                **{
                    f'basis_seed_{seed}': str(training_output / f'basis_s{seed}.npz')
                    for seed in seeds
                },
            },
            # Optional on successful runs; a rejected solver writes this
            # diagnostic before train.main exits nonzero.
            'diagnostics': {
                'solver_contract_rejection': str(
                    training_output / 'optimizer_contract_rejection.json'),
            },
        },
    }
    # Run the generic no-launch verifier so a draft cannot silently omit a file
    # binding or point to an existing output.
    probe_path = receipt_dir / f'.{run_id}.preflight-probe.json'
    _validate_spec(runspec, probe_path)
    return runspec


def write_optimize_runspec(path, runspec):
    """Write a prepared RunSpec once; never replace an existing file."""
    path = Path(path).resolve()
    if not path.parent.is_dir():
        raise FileNotFoundError(f'RunSpec parent directory does not exist: {path.parent}')
    protected = {
        Path(entry['path']).resolve() for entry in runspec.get('files', {}).values()
        if isinstance(entry, dict) and isinstance(entry.get('path'), str)
    }
    outputs = runspec.get('outputs', {})
    output_paths = {
        Path(value).resolve() for name, value in outputs.items()
        if name not in {'artifacts', 'diagnostics'}
        and isinstance(value, str)
    }
    for kind in ('artifacts', 'diagnostics'):
        declared = outputs.get(kind, {})
        if isinstance(declared, dict):
            output_paths.update(Path(value).resolve() for value in declared.values()
                               if isinstance(value, str))
    if path in protected:
        raise ValueError('RunSpec path collides with a bound protocol, source, or input')
    if path in output_paths:
        raise ValueError('RunSpec path collides with a declared worker output')
    payload = json.dumps(runspec, indent=2, sort_keys=True, allow_nan=False) + '\n'
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Prepare, but do not execute, a hash-bound Optimize worker RunSpec')
    parser.add_argument('request', help='JSON request describing protocol, inputs, and outputs')
    parser.add_argument('output', help='new RunSpec JSON path; existing files are preserved')
    args = parser.parse_args(argv)
    request_path = Path(args.request).resolve()
    request = _read_object(request_path, 'RunSpec builder request')
    allowed = {
        'protocol_path', 'output_directory', 'receipt_directory', 'run_id',
        'timeout_seconds', 'terminate_grace_seconds', 'environment', 'repo_root',
        'extra_input_files',
    }
    if request.keys() - allowed or allowed - request.keys() - {'repo_root', 'extra_input_files'}:
        raise ValueError(
            f'builder request keys mismatch; missing={sorted(allowed - request.keys() - {"repo_root", "extra_input_files"})}, '
            f'extra={sorted(request.keys() - allowed)}')
    runspec = build_optimize_runspec(**request)
    written = write_optimize_runspec(args.output, runspec)
    print(json.dumps({
        'status': 'prepared_not_executed',
        'runspec': str(written),
        'run_id': runspec['run_id'],
        'bound_files': len(runspec['files']),
        'split_counts': {name: len(ids) for name, ids in runspec['split_ids'].items()},
        'physical_score': None,
    }, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
