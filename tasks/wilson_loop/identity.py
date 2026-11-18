"""Measurement identity: generation ids, resume checks and trust derivation."""
import json
from pathlib import Path

import numpy as np

from core.io import digest, fingerprint


def measurement_spec(p, split):
    from .common import indices
    return {'split': split, 'ids': [int(x) for x in indices(split)],
            'protocol_hash': fingerprint(p),
            'kernel_sha256': digest(Path(__file__).with_name('kernels.py'))}


def generation(spec):
    return fingerprint(spec)


def check_resume(output, split, spec):
    """Return the number of completed rows that may be resumed, or refuse."""
    path = Path(output) / f'{split}.npz'
    if not path.exists():
        return 0
    with np.load(path, allow_pickle=False) as f:
        if 'generation' not in f:
            raise ValueError(f'{path}: legacy measurement without a generation id; treat as read-only')
        stored = str(f['generation'])
        ids = f['ids'].tolist()
    wanted = generation(spec)
    if stored != wanted:
        raise ValueError(f'{path}: measurement generation {stored[:12]} does not match {wanted[:12]}; '
                         'refusing to mix a new run into it')
    if ids != spec['ids'][:len(ids)]:
        raise ValueError(f'{path}: stored ids are not a prefix of the requested split')
    return len(ids)


def trust_status(run, p, submission, provenance):
    """Derive a trust label from identities, not from the protocol name."""
    reasons = []
    try:
        from .common import load_data
        load_data(run, 'validation')
    except (ValueError, FileNotFoundError) as exc:
        reasons.append(f'data validation failed: {exc}')
    kernel_sha = digest(Path(__file__).with_name('kernels.py'))
    if submission.get('kernel_sha256') != kernel_sha:
        reasons.append('submission kernel hash does not match the current kernels.py')
    if provenance.get('kernel_sha256') != submission.get('kernel_sha256'):
        reasons.append('measurement provenance kernel hash differs from the submission')
    if provenance.get('protocol', {}).get('version') != submission.get('protocol_version'):
        reasons.append('protocol version differs between provenance and submission')
    if not submission.get('identity'):
        reasons.append('no identity block in the submission')
    return {'status': 'physical' if not reasons else 'archived_diagnostic', 'reasons': reasons}
