"""Durable, resumable JSONL checkpoints for diagnostic two-state bootstraps.

The journal records every planned draw in order. A draw is acknowledged only
after its hash-chained JSON row has been written and fsynced. A trailing
partial row from an interrupted write is discarded on explicit resume; any
complete but invalid row is treated as corruption and stops the run.
"""
import fcntl
import hashlib
import json
import os
import tempfile
import uuid
from pathlib import Path

import numpy as np


def _json_safe(value):
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if np.isnan(number):
            return 'NaN'
        if np.isposinf(number):
            return 'Infinity'
        if np.isneginf(number):
            return '-Infinity'
        return number
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def _canonical(value):
    return json.dumps(
        _json_safe(value), sort_keys=True, separators=(',', ':'), allow_nan=False,
    ).encode('utf-8')


def _sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def _fsync_directory(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _publish_new_file(path, payload):
    """Publish bytes without replacing an existing file."""
    path = Path(path)
    temporary = path.with_name(f'.{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view = memoryview(payload)
        offset = 0
        while offset < len(view):
            written = os.write(fd, view[offset:])
            if written <= 0:
                raise OSError('short write while publishing checkpoint file')
            offset += written
        os.fsync(fd)
    except BaseException:
        os.close(fd)
        temporary.unlink(missing_ok=True)
        raise
    else:
        os.close(fd)
    try:
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    _fsync_directory(path.parent)


class BootstrapCheckpoint:
    """No-clobber, hash-verified checkpoint journal for planned bootstrap draws."""

    def __init__(self, path, manifest, *, resume=False):
        self.path = Path(path)
        self.manifest = _json_safe(manifest)
        if not isinstance(self.manifest, dict):
            raise ValueError('manifest must be a JSON object')
        if self.manifest.get('record_type') != 'run_manifest':
            raise ValueError('manifest must have record_type=run_manifest')
        planned = self.manifest.get('planned_draws')
        if isinstance(planned, bool) or not isinstance(planned, int) or planned <= 0:
            raise ValueError('manifest planned_draws must be a positive integer')
        self.planned_draws = planned
        self.manifest_bytes = _canonical(self.manifest)
        self.manifest_sha256 = _sha256(self.manifest_bytes)
        self.manifest_path = self.path / 'manifest.json'
        self.draws_path = self.path / 'draws.jsonl'
        self.status_path = self.path / 'status.json'
        self._lock_fd = None
        self._closed = False
        self._draw_hashes = []
        self._last_hash = None

        if resume:
            if not self.path.is_dir():
                raise FileNotFoundError(f'checkpoint directory does not exist: {self.path}')
        else:
            self.path.mkdir(parents=False, exist_ok=False)

        try:
            self._acquire_lock()
            if resume:
                self._load_existing_manifest()
                self._load_and_repair_draws()
                self._verify_or_recover_status()
            else:
                envelope = {
                    'manifest': self.manifest,
                    'manifest_sha256': self.manifest_sha256,
                }
                _publish_new_file(self.manifest_path, _canonical(envelope) + b'\n')
                fd = os.open(self.draws_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                os.fsync(fd)
                os.close(fd)
                _fsync_directory(self.path)
                self.completed_draws = 0
                self.complete = False
        except BaseException:
            self.close()
            raise

    def _acquire_lock(self):
        lock_path = self.path / '.writer.lock'
        self._lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(self._lock_fd)
            self._lock_fd = None
            raise RuntimeError(f'checkpoint already has an active writer: {self.path}') from exc

    def _load_existing_manifest(self):
        try:
            envelope = json.loads(self.manifest_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError('checkpoint manifest is missing or invalid') from exc
        stored = envelope.get('manifest')
        stored_bytes = _canonical(stored)
        stored_hash = _sha256(stored_bytes)
        if envelope.get('manifest_sha256') != stored_hash:
            raise ValueError('checkpoint manifest hash mismatch')
        if stored_hash != self.manifest_sha256:
            raise ValueError('resume manifest does not match checkpoint identity')

    def _load_and_repair_draws(self):
        try:
            raw = self.draws_path.read_bytes()
        except OSError as exc:
            raise ValueError('checkpoint draw journal is missing') from exc
        if raw and not raw.endswith(b'\n'):
            complete_end = raw.rfind(b'\n') + 1
            fd = os.open(self.draws_path, os.O_WRONLY)
            try:
                os.ftruncate(fd, complete_end)
                os.fsync(fd)
            finally:
                os.close(fd)
            raw = raw[:complete_end]

        previous = None
        rows = []
        for expected_id, line in enumerate(raw.splitlines()):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f'complete journal row {expected_id} is invalid JSON') from exc
            if row.get('record_type') != 'bootstrap_draw':
                raise ValueError(f'journal row {expected_id} has unexpected record_type')
            if row.get('draw_id') != expected_id:
                raise ValueError(f'journal draw IDs are not contiguous at row {expected_id}')
            supplied_hash = row.pop('record_sha256', None)
            if row.get('previous_record_sha256') != previous:
                raise ValueError(f'journal hash chain is broken at draw {expected_id}')
            computed_hash = _sha256(_canonical(row))
            if supplied_hash != computed_hash:
                raise ValueError(f'journal row hash mismatch at draw {expected_id}')
            previous = supplied_hash
            rows.append(supplied_hash)

        if len(rows) > self.planned_draws:
            raise ValueError('journal contains more draws than the manifest planned')
        self._draw_hashes = rows
        self._last_hash = previous
        self.completed_draws = len(rows)
        self.complete = self.completed_draws == self.planned_draws

    def _expected_status(self):
        return {
            'schema': 'pion-bootstrap-checkpoint-status-v1',
            'classification': 'diagnostic_only',
            'physical_score': None,
            'status': 'complete',
            'manifest_sha256': self.manifest_sha256,
            'planned_draws': self.planned_draws,
            'completed_draws': self.completed_draws,
            'last_record_sha256': self._last_hash,
        }

    def _verify_or_recover_status(self):
        if not self.complete:
            if self.status_path.exists():
                raise ValueError('checkpoint has a completion status but an incomplete journal')
            return
        expected = self._expected_status()
        if self.status_path.exists():
            try:
                observed = json.loads(self.status_path.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError('checkpoint completion status is invalid') from exc
            if observed != expected:
                raise ValueError('checkpoint completion status does not match the journal')
        else:
            _publish_new_file(self.status_path, _canonical(expected) + b'\n')

    def append(self, record):
        if self._closed:
            raise RuntimeError('checkpoint is closed')
        if self.complete:
            raise ValueError('all planned bootstrap draws are already committed')
        row = _json_safe(record)
        if not isinstance(row, dict) or row.get('record_type') != 'bootstrap_draw':
            raise ValueError('record must have record_type=bootstrap_draw')
        if row.get('draw_id') != self.completed_draws:
            raise ValueError(f'expected draw_id={self.completed_draws}')
        row['previous_record_sha256'] = self._last_hash
        record_hash = _sha256(_canonical(row))
        stored = dict(row, record_sha256=record_hash)
        payload = _canonical(stored) + b'\n'
        fd = os.open(self.draws_path, os.O_WRONLY | os.O_APPEND)
        try:
            view = memoryview(payload)
            offset = 0
            while offset < len(view):
                written = os.write(fd, view[offset:])
                if written <= 0:
                    raise OSError('short write while appending checkpoint draw')
                offset += written
            os.fsync(fd)
        finally:
            os.close(fd)
        self._last_hash = record_hash
        self._draw_hashes.append(record_hash)
        self.completed_draws += 1
        self.complete = self.completed_draws == self.planned_draws
        if self.complete:
            _publish_new_file(self.status_path, _canonical(self._expected_status()) + b'\n')
        return record_hash

    def receipt(self):
        return {
            'classification': 'diagnostic_only',
            'physical_score': None,
            'manifest_sha256': self.manifest_sha256,
            'planned_draws': self.planned_draws,
            'completed_draws': self.completed_draws,
            'status': 'complete' if self.complete else 'incomplete_resumable',
            'last_record_sha256': self._last_hash,
        }

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._lock_fd is not None:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
            finally:
                os.close(self._lock_fd)
                self._lock_fd = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()


def run_checkpointed_bootstrap(fit, indices, starts, path, *, block_configuration_ids,
                               resume=False,
                               maxiter=500, ftol=1e-10, boundary_tolerance=1e-5,
                               feasibility_tolerance=1e-8):
    """Run the stable multi-start iterator into a durable checkpoint journal."""
    from .reference_twostate import TwoStateFit

    if not isinstance(fit, TwoStateFit):
        raise TypeError('fit must be a TwoStateFit instance')
    block_ids = _json_safe(block_configuration_ids)
    if (not isinstance(block_ids, list) or len(block_ids) != len(fit.samples)
            or any(not isinstance(group, list) or not group for group in block_ids)):
        raise ValueError('block_configuration_ids must list the nonempty IDs in every fitted block')
    flattened_ids = [item for group in block_ids for item in group]
    if any(isinstance(item, bool) or not isinstance(item, (int, str)) for item in flattened_ids):
        raise ValueError('configuration IDs must be integers or strings')
    if len(set(flattened_ids)) != len(flattened_ids):
        raise ValueError('configuration IDs must be unique across blocks')
    controls = {
        'maxiter': maxiter,
        'ftol': ftol,
        'boundary_tolerance': boundary_tolerance,
        'feasibility_tolerance': feasibility_tolerance,
    }
    probe = fit.iter_bootstrap_multistart(indices, starts, **controls)
    base_manifest = next(probe)
    manifest = dict(base_manifest)
    manifest['block_configuration_ids'] = block_ids
    manifest['block_configuration_ids_sha256'] = _sha256(_canonical(block_ids))
    sample_matrix = np.ascontiguousarray(fit.samples, dtype='<f8')
    sample_payload = np.asarray(sample_matrix.shape, dtype='<i8').tobytes()
    sample_payload += sample_matrix.tobytes(order='C')
    manifest['fit_samples_shape'] = list(sample_matrix.shape)
    manifest['fit_samples_sha256'] = _sha256(sample_payload)
    channel_scales = np.ascontiguousarray(fit.scales, dtype='<f8')
    manifest['fit_channel_scales'] = channel_scales.tolist()
    manifest['fit_channel_scales_sha256'] = _sha256(channel_scales.tobytes(order='C'))
    manifest['checkpoint_executor_source_sha256'] = _sha256(Path(__file__).read_bytes())
    with BootstrapCheckpoint(path, manifest, resume=resume) as checkpoint:
        if not checkpoint.complete:
            stream = fit.iter_bootstrap_multistart(
                indices, starts, start_draw=checkpoint.completed_draws, **controls,
            )
            replay_manifest = next(stream)
            if _canonical(replay_manifest) != _canonical(base_manifest):
                raise ValueError('bootstrap manifest changed between validation and execution')
            for record in stream:
                checkpoint.append(record)
        receipt = checkpoint.receipt()
    return receipt
