"""Process-group supervisor for diagnostic runs with a hard walltime cap.

The supervised command is launched as an argument vector (never through a
shell).  On POSIX the worker starts a new session so a timeout can terminate
its process group, including ordinary child processes.  This module records
execution status only; it does not decide solver acceptance or physical risk.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from numbers import Real
from pathlib import Path
import signal
import subprocess
import tempfile
import time


SCHEMA = 'optgauss-hard-timeout-v1'


def _validate_duration(value, name, *, allow_zero=False):
    if (isinstance(value, bool) or not isinstance(value, Real)
            or not math.isfinite(float(value))):
        raise ValueError(f'{name} must be a finite number')
    value = float(value)
    if value < 0 if allow_zero else value <= 0:
        relation = 'nonnegative' if allow_zero else 'positive'
        raise ValueError(f'{name} must be {relation}')
    return value


def _canonical_json(value, name):
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(',', ':'),
                             allow_nan=False)
        return encoded, json.loads(encoded)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{name} must be strict-JSON serializable') from exc


def _sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_record(path):
    if path is None:
        return {'path': None, 'sha256': None, 'error': None}
    path = Path(path)
    try:
        return {'path': str(path), 'sha256': _sha256_file(path), 'error': None}
    except OSError as exc:
        return {'path': str(path), 'sha256': None,
                'error': {'type': type(exc).__name__, 'message': str(exc)}}


def _fsync_directory(path):
    if os.name != 'posix':
        return
    flags = os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0)
    try:
        fd = os.open(str(path), flags)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _publish_json_noclobber(path, payload):
    path = Path(path)
    if not path.parent.is_dir():
        raise FileNotFoundError(f'receipt parent directory does not exist: {path.parent}')
    if path.exists():
        raise FileExistsError(f'refusing to overwrite receipt {path}')
    encoded = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    fd, temporary = tempfile.mkstemp(prefix=f'.{path.name}.', suffix='.tmp',
                                     dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        # Same-filesystem hard-link publication fails if another writer won.
        os.link(temporary, path)
        _fsync_directory(path.parent)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return path


def _signal_worker_group(process, sig):
    if os.name == 'posix':
        try:
            os.killpg(process.pid, sig)
            return True, None
        except ProcessLookupError:
            return False, None
        except PermissionError as exc:
            return False, {'type': type(exc).__name__, 'message': str(exc)}
    try:
        process.send_signal(sig)
        return True, None
    except ProcessLookupError:
        return False, None
    except PermissionError as exc:
        return False, {'type': type(exc).__name__, 'message': str(exc)}


def _worker_group_exists(process):
    if os.name != 'posix':
        return process.poll() is None
    try:
        os.killpg(process.pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _terminate_worker(process, grace_seconds):
    """Terminate the worker group, escalating to KILL after the grace period."""
    term_sent, term_error = _signal_worker_group(process, signal.SIGTERM)
    deadline = time.monotonic() + grace_seconds
    while time.monotonic() < deadline:
        # Reap a terminated leader before probing the process group. This avoids
        # treating the leader's zombie state as a reason to send SIGKILL.
        process.poll()
        if not _worker_group_exists(process):
            break
        time.sleep(min(0.01, max(0.0, deadline - time.monotonic())))

    process.poll()
    group_alive_before_kill = _worker_group_exists(process)
    kill_attempted = group_alive_before_kill
    kill_sent = False
    kill_error = None
    if kill_attempted:
        # On POSIX, also kill surviving descendants if the group leader exited.
        kill_sent, kill_error = _signal_worker_group(process, signal.SIGKILL)
    fallback_error = None
    fallback_sent = False
    if process.poll() is None:
        try:
            process.kill()
            fallback_sent = True
        except OSError as exc:
            fallback_error = {'type': type(exc).__name__, 'message': str(exc)}
    try:
        process.wait(timeout=max(grace_seconds, 0.1))
    except subprocess.TimeoutExpired:
        if process.poll() is None:
            try:
                process.kill()
                fallback_sent = True
            except OSError as exc:
                fallback_error = {'type': type(exc).__name__, 'message': str(exc)}
        try:
            process.wait(timeout=max(grace_seconds, 0.1))
        except subprocess.TimeoutExpired:
            pass

    # Do not claim stable worker outputs if a descendant remains after the
    # bounded cleanup window. The caller will publish a failure receipt with
    # hashes withheld rather than block forever or hash mutable files.
    post_kill_deadline = time.monotonic() + max(grace_seconds, 0.1)
    group_alive = _worker_group_exists(process)
    while group_alive and time.monotonic() < post_kill_deadline:
        process.poll()
        time.sleep(min(0.01, max(0.0, post_kill_deadline - time.monotonic())))
        group_alive = _worker_group_exists(process)
    complete = not group_alive and process.poll() is not None
    return {'term_sent': term_sent, 'kill_sent': kill_sent,
            'kill_attempted': kill_attempted,
            'leader_fallback_sent': fallback_sent,
            'complete': complete,
            'worker_group_alive_after_cleanup': group_alive,
            'scope': 'process_group' if os.name == 'posix' else 'process',
            'term_error': term_error, 'kill_error': kill_error,
            'leader_fallback_error': fallback_error}


def run_command_with_hard_timeout(command, *, timeout_seconds, receipt_path,
                                  stdout_path, stderr_path, identity,
                                  checkpoint_path=None,
                                  artifact_outputs=None,
                                  failure_diagnostic_outputs=None,
                                  terminate_grace_seconds=1.0,
                                  cwd=None, environment=None):
    """Run one command under a killable walltime deadline and publish a receipt.

    ``timeout_seconds`` includes process creation and worker startup.  Receipt
    and log paths must be new files in existing directories.  If the child is
    killed, an optional pre-existing checkpoint is hashed after the process
    group has been terminated.  Any checkpoint format is opaque here; callers
    must validate and interpret its contents separately. Optional
    ``artifact_outputs`` are accepted only after a zero-exit worker and clean
    process-group completion; failed, timed-out, or descendant-leaking workers
    never receive accepted artifact hashes.

    Optional ``failure_diagnostic_outputs`` are different: after the process
    group is confirmed stable, their observed file hashes are recorded even
    when the worker exits nonzero. They are never treated as successful
    artifacts or physical results.

    A hard timeout is an execution status only.  A timed-out result is never
    eligible for a risk or physical score, and cleanup may extend supervisor
    walltime beyond the worker deadline by the termination grace period.
    """
    timeout_seconds = _validate_duration(timeout_seconds, 'timeout_seconds')
    terminate_grace_seconds = _validate_duration(
        terminate_grace_seconds, 'terminate_grace_seconds', allow_zero=True)
    if isinstance(command, (str, bytes)):
        raise ValueError('command must be a nonempty sequence of strings')
    try:
        argv = list(command)
    except TypeError as exc:
        raise ValueError('command must be a nonempty sequence of strings') from exc
    if not argv or any(not isinstance(part, str) or not part or '\x00' in part
                       for part in argv):
        raise ValueError('command must contain nonempty, NUL-free strings')
    if cwd is not None and not Path(cwd).is_dir():
        raise FileNotFoundError(f'working directory does not exist: {cwd}')
    environment_value = None
    environment_sha256 = None
    environment_keys = None
    if environment is not None:
        if (not isinstance(environment, dict)
                or any(not isinstance(key, str) or not key
                       or not isinstance(value, str) or '\x00' in key or '\x00' in value
                       for key, value in environment.items())):
            raise ValueError('environment must map NUL-free string names to string values')
        environment_json, environment_value = _canonical_json(environment, 'environment')
        environment_sha256 = hashlib.sha256(environment_json.encode()).hexdigest()
        environment_keys = sorted(environment_value)

    identity_json, identity_value = _canonical_json(identity, 'identity')
    command_json = json.dumps(argv, separators=(',', ':'), ensure_ascii=False)
    if artifact_outputs is None:
        artifact_outputs = {}
    if (not isinstance(artifact_outputs, dict)
            or any(not isinstance(name, str) or not name
                   for name in artifact_outputs)):
        raise ValueError('artifact_outputs must map nonempty names to paths')
    if failure_diagnostic_outputs is None:
        failure_diagnostic_outputs = {}
    if (not isinstance(failure_diagnostic_outputs, dict)
            or any(not isinstance(name, str) or not name
                   for name in failure_diagnostic_outputs)):
        raise ValueError('failure_diagnostic_outputs must map nonempty names to paths')
    artifact_paths = {}
    for name, raw_path in artifact_outputs.items():
        path = Path(raw_path)
        if not path.is_absolute():
            raise ValueError(f'artifact_outputs[{name!r}] must be absolute')
        parent = path.parent
        while not parent.exists() and parent.parent != parent:
            parent = parent.parent
        if not parent.is_dir():
            raise FileNotFoundError(
                f'artifact output has no existing directory ancestor: {path.parent}')
        artifact_paths[name] = path
    diagnostic_paths = {}
    for name, raw_path in failure_diagnostic_outputs.items():
        path = Path(raw_path)
        if not path.is_absolute():
            raise ValueError(f'failure_diagnostic_outputs[{name!r}] must be absolute')
        parent = path.parent
        while not parent.exists() and parent.parent != parent:
            parent = parent.parent
        if not parent.is_dir():
            raise FileNotFoundError(
                f'failure diagnostic output has no existing directory ancestor: {path.parent}')
        diagnostic_paths[name] = path
    paths = [Path(receipt_path), Path(stdout_path), Path(stderr_path)]
    if checkpoint_path is not None:
        paths.append(Path(checkpoint_path))
    paths.extend(artifact_paths.values())
    paths.extend(diagnostic_paths.values())
    resolved = [path.resolve() for path in paths]
    if len(set(resolved)) != len(resolved):
        raise ValueError('receipt, logs, checkpoint, artifact, and diagnostic paths must be distinct')
    for path in paths[:3]:
        if not path.parent.is_dir():
            raise FileNotFoundError(f'output parent directory does not exist: {path.parent}')
    if paths[0].exists() or paths[1].exists() or paths[2].exists():
        raise FileExistsError('refusing to overwrite an existing receipt or log file')
    if any(path.exists() for path in artifact_paths.values()):
        raise FileExistsError('refusing to overwrite an existing artifact output')
    if any(path.exists() for path in diagnostic_paths.values()):
        raise FileExistsError('refusing to overwrite an existing failure diagnostic output')

    receipt_path, stdout_path, stderr_path = paths[:3]
    checkpoint_path = paths[3] if checkpoint_path is not None else None
    started = time.monotonic()
    termination = None
    return_code = None
    timed_out = False
    launch_error = None
    worker_group_leaked = False
    created_logs = []
    process = None
    try:
        stdout_handle = stdout_path.open('xb')
        created_logs.append(stdout_path)
        try:
            stderr_handle = stderr_path.open('xb')
            created_logs.append(stderr_path)
        except Exception:
            stdout_handle.close()
            raise
    except Exception:
        for path in created_logs:
            path.unlink(missing_ok=True)
        raise

    try:
        popen_kwargs = {
            'stdin': subprocess.DEVNULL,
            'stdout': stdout_handle,
            'stderr': stderr_handle,
            'cwd': cwd,
            'close_fds': True,
        }
        if environment_value is not None:
            # An explicit environment replaces inheritance from the supervisor.
            popen_kwargs['env'] = environment_value
        if os.name == 'posix':
            popen_kwargs['start_new_session'] = True
        elif os.name == 'nt':
            popen_kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
        try:
            process = subprocess.Popen(argv, **popen_kwargs)
        except OSError as exc:
            launch_error = {'type': type(exc).__name__, 'message': str(exc)}
        if process is not None:
            remaining = max(0.0, timeout_seconds - (time.monotonic() - started))
            try:
                return_code = process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                if process.poll() is None:
                    timed_out = True
                    termination = _terminate_worker(process, terminate_grace_seconds)
                return_code = process.returncode
    finally:
        stdout_handle.close()
        stderr_handle.close()

    # A successful group leader may leave descendants holding stdout, stderr,
    # checkpoints, or declared result files open. End that process group before
    # any file hash is treated as a stable receipt field.
    if (not timed_out and process is not None and return_code is not None
            and os.name == 'posix' and _worker_group_exists(process)):
        worker_group_leaked = True
        termination = _terminate_worker(process, terminate_grace_seconds)

    elapsed = max(0.0, time.monotonic() - started)
    cleanup_incomplete = bool(
        termination is not None and not termination['complete'])
    if cleanup_incomplete:
        unstable = {
            'type': 'UnstableOutput',
            'message': 'worker group termination was not confirmed; file may still change',
        }
        checkpoint = {'path': str(checkpoint_path) if checkpoint_path else None,
                      'sha256': None, 'error': unstable}
        stdout_record = {'path': str(stdout_path), 'sha256': None,
                         'error': unstable}
        stderr_record = {'path': str(stderr_path), 'sha256': None,
                         'error': unstable}
    else:
        checkpoint = _hash_record(checkpoint_path)
        stdout_record = _hash_record(stdout_path)
        stderr_record = _hash_record(stderr_path)
    if launch_error is not None:
        status = 'launch_failed'
    elif cleanup_incomplete:
        status = 'termination_failed'
    elif worker_group_leaked:
        status = 'worker_failed'
    elif timed_out:
        status = 'hard_timeout'
    elif return_code == 0:
        status = 'completed'
    else:
        status = 'worker_failed'
    if artifact_paths:
        if status == 'completed':
            artifact_records = {
                name: _hash_record(path) for name, path in artifact_paths.items()}
            artifact_output_status = (
                'verified' if all(row['sha256'] is not None
                                  for row in artifact_records.values())
                else 'incomplete_or_unreadable')
        else:
            reason = (
                {'type': 'UnstableOutput',
                 'message': 'worker group termination was not confirmed; artifact may still change'}
                if cleanup_incomplete else
                {'type': 'UnacceptedArtifact',
                 'message': f'worker status {status!r} is not eligible for artifact acceptance'})
            artifact_records = {
                name: {'path': str(path), 'sha256': None, 'error': reason}
                for name, path in artifact_paths.items()}
            artifact_output_status = 'not_accepted'
    else:
        artifact_records = {}
        artifact_output_status = 'not_declared'
    if diagnostic_paths:
        if cleanup_incomplete:
            diagnostic_records = {
                name: {'path': str(path), 'sha256': None,
                       'error': {'type': 'UnstableOutput',
                                 'message': 'worker group termination was not confirmed; diagnostic may still change'}}
                for name, path in diagnostic_paths.items()}
            diagnostic_output_status = 'unstable'
        else:
            diagnostic_records = {
                name: _hash_record(path) for name, path in diagnostic_paths.items()}
            present = sum(row['sha256'] is not None for row in diagnostic_records.values())
            if present == 0:
                diagnostic_output_status = 'not_present'
            elif present == len(diagnostic_records):
                diagnostic_output_status = 'observed'
            else:
                diagnostic_output_status = 'partial'
    else:
        diagnostic_records = {}
        diagnostic_output_status = 'not_declared'
    receipt = {
        'schema': SCHEMA,
        'evidence_class': 'execution_control_only',
        'status': status,
        'timed_out': timed_out,
        'physical_score': None,
        'command_sha256': hashlib.sha256(command_json.encode()).hexdigest(),
        'environment_sha256': environment_sha256,
        'environment_keys': environment_keys,
        'identity': identity_value,
        'identity_sha256': hashlib.sha256(identity_json.encode()).hexdigest(),
        'timeout_seconds': timeout_seconds,
        'terminate_grace_seconds': terminate_grace_seconds,
        'elapsed_seconds': elapsed,
        'deadline_overrun_seconds': max(0.0, elapsed - timeout_seconds),
        'return_code': return_code,
        'launch_error': launch_error,
        'worker_group_leaked': worker_group_leaked,
        'termination': termination,
        'checkpoint': checkpoint,
        'artifact_output_status': artifact_output_status,
        'artifact_outputs': artifact_records,
        'failure_diagnostic_status': diagnostic_output_status,
        'failure_diagnostic_outputs': diagnostic_records,
        'stdout': stdout_record,
        'stderr': stderr_record,
    }
    _publish_json_noclobber(receipt_path, receipt)
    return receipt
