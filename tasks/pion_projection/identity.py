"""Shared run-identity verification for joint/evaluate/candidate (A1)."""
import json
from pathlib import Path

import numpy as np

from .common import digest, fingerprint


def _ids(output, split):
    with np.load(output / f'{split}.npz', allow_pickle=False) as f:
        return f['ids'].tolist()


def verify_run_identity(output, models=None):
    """Return (frozen_kind, reasons); reasons empty means the identity is valid.

    Binds the submission, the validation report, both data files, the reference
    implementation, the candidate set and the late metric - not just the kind.
    """
    output = Path(output)
    p = json.loads((output / 'development_provenance.json').read_text())['protocol']
    sub = json.loads((output / 'submission.json').read_text())
    report_path = output / 'validation_results.json'
    report = json.loads(report_path.read_text()) if report_path.exists() else None
    reasons = []
    kind = sub.get('reference', {}).get('kind')
    if kind is None:
        return None, ['submission has no frozen reference kind']
    wanted = tuple(models) if models is not None else (kind,)
    if wanted != (kind,):
        reasons.append(f'requested models {wanted} differ from the frozen kind {kind!r}')
    if sub.get('protocol_hash') != fingerprint(p):
        reasons.append('submission protocol hash does not match the run protocol')
    if sub.get('development_sha256') != digest(output / 'development.npz'):
        reasons.append('development data hash does not match the submission')
    for split in ('development', 'validation'):
        expected = list(range(int(p[split][0]), int(p[split][1]) + 1))
        try:
            stored = _ids(output, split)
        except (OSError, KeyError) as exc:
            reasons.append(f'{split} data is unreadable: {exc}')
            continue
        if stored != expected:
            reasons.append(f'{split} ids do not equal the protocol range')
    spec = sub.get('reference') or {}
    if spec.get('statistics_sha256') != digest(Path(__file__).with_name('statistics.py')):
        reasons.append('reference statistics implementation changed since development')
    if spec.get('implementation_sha256') not in (None, spec.get('statistics_sha256'),
                                                  digest(Path(__file__).with_name('reference.py'))):
        reasons.append('reference implementation hash is inconsistent')
    if report is not None:
        if report.get('submission_sha256') != digest(output / 'submission.json'):
            reasons.append('validation report submission hash differs from the submission file')
        if report.get('validation_sha256') != digest(output / 'validation.npz'):
            reasons.append('validation report data hash differs from validation.npz')
        if report.get('reference_kind') not in (None, kind):
            reasons.append('validation report reference kind differs from the frozen submission')
        if report.get('protocol', {}) != p:
            reasons.append('validation report protocol differs from the run protocol')
        keys = set((report.get('results') or {}).keys())
        if keys and keys != set((sub.get('submissions') or {}).keys()):
            reasons.append('validation report candidate set differs from the submission')
    late = sub.get('late_inverse_covariances') or {}
    if set(late) != set((sub.get('submissions') or {})):
        reasons.append('late metric keys differ from the candidate set')
    expected_dim = len(p['amplitude_window'])
    for name, matrix in late.items():
        array = np.asarray(matrix)
        if array.ndim != 2 or not np.all(np.isfinite(array)):
            reasons.append(f'late metric {name!r} is not a finite matrix')
        elif array.shape != (expected_dim, expected_dim):
            reasons.append(f'late metric {name!r} has shape {array.shape}, '
                           f'expected {(expected_dim, expected_dim)}')
    return kind, reasons
