"""Fail-closed launcher for Optimize workers bound to a frozen execution spec.

This layer binds execution inputs and outputs before starting a child process.
It does not choose statistical thresholds, validate a physics reference, or
turn a successful worker receipt into a physical score.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from numbers import Real
from pathlib import Path
import re
import time

from .hard_timeout import run_command_with_hard_timeout


SCHEMA = 'optgauss-worker-runspec-v2'
_TOP_LEVEL = {
    'schema', 'command', 'cwd', 'timeout_seconds', 'terminate_grace_seconds',
    'files', 'run_id', 'split_ids', 'outputs', 'environment',
}
_OUTPUT_KEYS = {'receipt', 'stdout', 'stderr', 'checkpoint', 'artifacts', 'diagnostics'}


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON key: {key}')
        result[key] = value
    return result


def _read_spec(path):
    path = Path(path)
    raw = path.read_bytes()
    try:
        spec = json.loads(raw, object_pairs_hook=_reject_duplicate_keys,
                          parse_constant=lambda value: (_ for _ in ()).throw(
                              ValueError(f'non-finite JSON value: {value}')))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f'RunSpec is not valid UTF-8 JSON: {path}') from exc
    if not isinstance(spec, dict):
        raise ValueError('RunSpec root must be an object')
    return spec, hashlib.sha256(raw).hexdigest()


def _digest_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_hash(value, where):
    if (not isinstance(value, str) or len(value) != 64
            or any(char not in '0123456789abcdef' for char in value)):
        raise ValueError(f'{where} must be a lowercase SHA-256 hex digest')


def _duration(value, where, *, allow_zero=False):
    if (isinstance(value, bool) or not isinstance(value, Real)
            or not math.isfinite(float(value))):
        raise ValueError(f'{where} must be finite')
    value = float(value)
    if value < 0 if allow_zero else value <= 0:
        relation = 'nonnegative' if allow_zero else 'positive'
        raise ValueError(f'{where} must be {relation}')
    return value


def _validate_split_ids(value):
    if value is None:
        return {}
    if not isinstance(value, dict) or not value:
        raise ValueError('split_ids must be a nonempty object when supplied')
    seen = {}
    normalized = {}
    for split, ids in value.items():
        if not isinstance(split, str) or not split:
            raise ValueError('split names must be nonempty strings')
        if not isinstance(ids, list) or not ids:
            raise ValueError(f'split {split!r} must contain a nonempty ID list')
        current = set()
        for cfg_id in ids:
            if isinstance(cfg_id, bool) or not isinstance(cfg_id, int):
                raise ValueError(f'split {split!r} contains a non-integer ID')
            if cfg_id in current:
                raise ValueError(f'split {split!r} repeats ID {cfg_id}')
            current.add(cfg_id)
            if cfg_id in seen:
                raise ValueError(
                    f'ID {cfg_id} overlaps splits {seen[cfg_id]!r} and {split!r}')
            seen[cfg_id] = split
        normalized[split] = list(ids)
    return normalized


def _validate_spec(spec, source_path):
    missing = _TOP_LEVEL - spec.keys()
    extra = spec.keys() - _TOP_LEVEL
    if missing or extra:
        raise ValueError(f'RunSpec keys mismatch; missing={sorted(missing)}, extra={sorted(extra)}')
    if spec.get('schema') != SCHEMA:
        raise ValueError(f'RunSpec schema must be {SCHEMA!r}')
    if not isinstance(spec.get('run_id'), str) or not spec['run_id'].strip():
        raise ValueError('run_id must be a nonempty string')

    command = spec.get('command')
    if (not isinstance(command, list) or not command
            or any(not isinstance(part, str) or not part or '\x00' in part
                   for part in command)):
        raise ValueError('command must be a nonempty argv list of NUL-free strings')
    cwd = Path(spec.get('cwd', ''))
    if not cwd.is_absolute() or not cwd.is_dir():
        raise ValueError('cwd must be an existing absolute directory')
    timeout = _duration(spec.get('timeout_seconds'), 'timeout_seconds')
    grace = _duration(spec.get('terminate_grace_seconds'),
                      'terminate_grace_seconds', allow_zero=True)

    raw_environment = spec.get('environment')
    if not isinstance(raw_environment, dict):
        raise ValueError('environment must be an explicit object; inherited environment is disabled')
    environment = {}
    for name, value in raw_environment.items():
        if (not isinstance(name, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name)
                or not isinstance(value, str) or '\x00' in value):
            raise ValueError('environment names and values must be valid NUL-free strings')
        environment[name] = value
    environment_json = json.dumps(environment, sort_keys=True, separators=(',', ':'),
                                  ensure_ascii=False, allow_nan=False)
    environment_sha256 = hashlib.sha256(environment_json.encode()).hexdigest()

    files = spec.get('files')
    if not isinstance(files, dict) or not files:
        raise ValueError('files must bind at least the protocol and source files')
    roles = set()
    verified_files = {}
    for label, entry in files.items():
        if not isinstance(label, str) or not label:
            raise ValueError('file binding labels must be nonempty strings')
        if (not isinstance(entry, dict)
                or set(entry) != {'path', 'sha256', 'role'}):
            raise ValueError(f'file binding {label!r} needs path, sha256, and role')
        file_path = Path(entry['path'])
        if not file_path.is_absolute() or not file_path.is_file():
            raise ValueError(f'file binding {label!r} must name an existing absolute file')
        if entry['role'] not in {'protocol', 'source', 'input'}:
            raise ValueError(f'file binding {label!r} has an unsupported role')
        roles.add(entry['role'])
        _validate_hash(entry['sha256'], f'files[{label!r}].sha256')
        actual = _digest_file(file_path)
        if actual != entry['sha256']:
            raise ValueError(
                f'file binding {label!r} hash mismatch: expected {entry["sha256"]}, got {actual}')
        verified_files[label] = {
            'path': str(file_path.resolve()), 'sha256': actual, 'role': entry['role']}
    if 'protocol' not in roles or 'source' not in roles:
        raise ValueError('files must include at least one protocol and one source binding')

    split_ids = _validate_split_ids(spec.get('split_ids'))
    outputs = spec.get('outputs')
    if not isinstance(outputs, dict) or not {'receipt', 'stdout', 'stderr'} <= outputs.keys():
        raise ValueError('outputs must include receipt, stdout, and stderr paths')
    if outputs.keys() - _OUTPUT_KEYS:
        raise ValueError(f'unsupported output keys: {sorted(outputs.keys() - _OUTPUT_KEYS)}')
    output_paths = {}
    for name, raw_path in outputs.items():
        if name in {'artifacts', 'diagnostics'}:
            continue
        output = Path(raw_path)
        if not output.is_absolute():
            raise ValueError(f'outputs.{name} must be an absolute path')
        output_paths[name] = output
    artifact_outputs = outputs.get('artifacts', {})
    if (not isinstance(artifact_outputs, dict)
            or any(not isinstance(label, str) or not label
                   for label in artifact_outputs)):
        raise ValueError('outputs.artifacts must map nonempty labels to absolute paths')
    normalized_artifacts = {}
    for label, raw_path in artifact_outputs.items():
        artifact = Path(raw_path)
        if not artifact.is_absolute():
            raise ValueError(f'outputs.artifacts.{label} must be an absolute path')
        parent = artifact.parent
        while not parent.exists() and parent.parent != parent:
            parent = parent.parent
        if not parent.is_dir():
            raise FileNotFoundError(
                f'artifact {label!r} has no existing directory ancestor: {artifact.parent}')
        if artifact.exists():
            raise FileExistsError(
                f'refusing to overwrite artifact output {label!r}: {artifact}')
        normalized_artifacts[label] = artifact
    diagnostic_outputs = outputs.get('diagnostics', {})
    if (not isinstance(diagnostic_outputs, dict)
            or any(not isinstance(label, str) or not label
                   for label in diagnostic_outputs)):
        raise ValueError('outputs.diagnostics must map nonempty labels to absolute paths')
    normalized_diagnostics = {}
    for label, raw_path in diagnostic_outputs.items():
        diagnostic = Path(raw_path)
        if not diagnostic.is_absolute():
            raise ValueError(f'outputs.diagnostics.{label} must be an absolute path')
        parent = diagnostic.parent
        while not parent.exists() and parent.parent != parent:
            parent = parent.parent
        if not parent.is_dir():
            raise FileNotFoundError(
                f'diagnostic output {label!r} has no existing directory ancestor: {diagnostic.parent}')
        if diagnostic.exists():
            raise FileExistsError(
                f'refusing to overwrite diagnostic output {label!r}: {diagnostic}')
        normalized_diagnostics[label] = diagnostic
    all_paths = [path.resolve() for path in output_paths.values()]
    all_paths.extend(path.resolve() for path in normalized_artifacts.values())
    all_paths.extend(path.resolve() for path in normalized_diagnostics.values())
    if len(set(all_paths)) != len(all_paths):
        raise ValueError('receipt, logs, and checkpoint paths must be distinct')
    if source_path.resolve() in all_paths:
        raise ValueError('RunSpec cannot also be an output')
    for name in ('receipt', 'stdout', 'stderr'):
        if not output_paths[name].parent.is_dir():
            raise FileNotFoundError(
                f'output parent for {name} does not exist: {output_paths[name].parent}')
        if output_paths[name].exists():
            raise FileExistsError(f'refusing to overwrite {name}: {output_paths[name]}')
    if 'checkpoint' in output_paths and output_paths['checkpoint'].exists():
        raise FileExistsError(
            f'refusing to overwrite checkpoint: {output_paths["checkpoint"]}')

    protected_files = {Path(info['path']).resolve() for info in verified_files.values()}
    if set(all_paths) & protected_files:
        raise ValueError('an output path collides with a protocol, source, or input file')
    return {
        'command': command,
        'cwd': str(cwd.resolve()),
        'timeout_seconds': timeout,
        'terminate_grace_seconds': grace,
        'environment': environment,
        'environment_sha256': environment_sha256,
        'files': verified_files,
        'run_id': spec['run_id'],
        'split_ids': split_ids,
        'outputs': output_paths,
        'artifact_outputs': normalized_artifacts,
        'diagnostic_outputs': normalized_diagnostics,
    }


def run_frozen_worker(spec_path):
    """Verify a frozen execution spec, then run its child process under a hard cap."""
    started = time.perf_counter()
    spec_path = Path(spec_path).resolve()
    spec, spec_sha256 = _read_spec(spec_path)
    checked = _validate_spec(spec, spec_path)
    preflight_seconds = max(0.0, time.perf_counter() - started)
    identity = {
        'run_spec_schema': SCHEMA,
        'run_spec_sha256': spec_sha256,
        'run_id': checked['run_id'],
        'files': checked['files'],
        'split_ids': checked['split_ids'],
        'environment_sha256': checked['environment_sha256'],
        'environment_keys': sorted(checked['environment']),
        'preflight': {
            'status': 'verified', 'file_count': len(checked['files']),
            'elapsed_seconds': preflight_seconds,
        },
    }
    outputs = checked['outputs']
    return run_command_with_hard_timeout(
        checked['command'],
        timeout_seconds=checked['timeout_seconds'],
        terminate_grace_seconds=checked['terminate_grace_seconds'],
        cwd=checked['cwd'], identity=identity,
        receipt_path=outputs['receipt'], stdout_path=outputs['stdout'],
        stderr_path=outputs['stderr'], checkpoint_path=outputs.get('checkpoint'),
        artifact_outputs=checked['artifact_outputs'],
        failure_diagnostic_outputs=checked['diagnostic_outputs'],
        environment=checked['environment'],
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Verify an Optimize worker RunSpec and supervise its command')
    parser.add_argument('runspec', help='path to optgauss-worker-runspec-v2 JSON')
    args = parser.parse_args(argv)
    receipt = run_frozen_worker(args.runspec)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    artifacts_verified = (
        receipt.get('artifact_output_status') == 'verified'
        if receipt.get('artifact_output_status') != 'not_declared' else True)
    return 0 if receipt['status'] == 'completed' and artifacts_verified else 1


if __name__ == '__main__':
    raise SystemExit(main())
