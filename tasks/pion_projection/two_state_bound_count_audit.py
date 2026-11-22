"""Read-only mass-bound counts for the public D0-99 two-state archive.

Run ``python -B -m tasks.pion_projection.two_state_bound_count_audit``.
Only the fixed public-development allowlist is read. No fitting, RNG, GPU,
environment-selected protocol, result writes, or split discovery is performed.
The pinned receipt authenticates archived bytes, not physical correctness.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = Path('results/pion_projection/s16t16d_closure_20261120')
PROTOCOL = Path('tasks/pion_projection/protocol_fresh_20261120.json')
SOURCE = Path('tasks/pion_projection/two_state_development_diagnostic.py')
PROVENANCE_SHA256 = 'a3a39cdd17e3dae1482ae1757d1f41ddb30508202617151d6874afe9a7b1ae4b'
TOLERANCE = 1e-4


def count_bounds(masses, bounds):
    """Apply the original joint-valid mask and inclusive mass-bound rule."""
    masses = np.asarray(masses)
    bounds = np.asarray(bounds, dtype=float)
    if (masses.ndim != 2 or masses.shape[1] != 2
            or bounds.shape != (2,) or not np.isfinite(bounds).all()
            or bounds[0] >= bounds[1]):
        raise ValueError('Expected draws x 2 masses and ordered finite bounds')
    valid = np.isfinite(masses).all(axis=1)
    lower = masses[valid] <= bounds[0] + TOLERANCE
    upper = masses[valid] >= bounds[1] - TOLERANCE
    return {
        'total': len(masses), 'valid': int(valid.sum()),
        'invalid': int((~valid).sum()),
        'm0_lower_hits': int(lower[:, 0].sum()),
        'm0_upper_hits': int(upper[:, 0].sum()),
        'm1_lower_hits': int(lower[:, 1].sum()),
        'm1_upper_hits': int(upper[:, 1].sum()),
        'any_hit': int(np.any(lower | upper, axis=1).sum()),
    }


def audit(root=ROOT, *, trusted_provenance_sha256=PROVENANCE_SHA256):
    """Verify the pinned receipt chain, then count only existing mass draws.

    ``root`` and the trust pin are injectable for isolated fixture tests; the
    command-line entry point always uses the fixed repository and archive pin.
    All paths below are literal allowlisted paths, never receipt-supplied paths.
    """
    root = Path(root).resolve()
    verified = {}

    def read(relative, expected):
        path = root / relative
        # Reject symlinks rather than following one into another split.
        if any(part.is_symlink() for part in [path, *path.parents] if part != root):
            raise ValueError(f'Symlink refused: {relative}')
        payload = path.read_bytes()
        actual = hashlib.sha256(payload).hexdigest()
        if actual != expected:
            raise ValueError(f'SHA-256 mismatch: {relative}')
        verified[str(relative)] = actual
        return payload

    receipt_bytes = read(ARCHIVE / 'two_state_diagnostic_provenance.json',
                         trusted_provenance_sha256)
    receipt = json.loads(receipt_bytes)
    if receipt['schema'] != 'pion-two-state-development-diagnostic-provenance-v1':
        raise ValueError('Unexpected provenance schema')
    protocol_bytes = read(PROTOCOL, receipt['protocol_sha256'])
    diagnostic_bytes = read(ARCHIVE / 'two_state_diagnostic.json',
                            receipt['outputs_sha256']['two_state_diagnostic.json'])
    mass_bytes = read(ARCHIVE / 'two_state_bootstrap.npz',
                     receipt['outputs_sha256']['two_state_bootstrap.npz'])
    reference_bytes = read(ARCHIVE / 'reference_bootstrap.npz',
                          receipt['bootstrap_indices_sha256'])
    measurement_bytes = read(ARCHIVE / 'development.npz', receipt['measurement_sha256'])
    read(ARCHIVE / 'development_provenance.json', receipt['measurement_provenance_sha256'])
    read(SOURCE, receipt['analysis_source_sha256'])
    protocol, diagnostic = json.loads(protocol_bytes), json.loads(diagnostic_bytes)
    if (protocol['development'] != [0, 99]
            or diagnostic['schema'] != 'pion-two-state-development-diagnostic-v1'
            or diagnostic['n_development_configurations'] != 100):
        raise ValueError('Expected public D development IDs 0-99')
    for diagnostic_key, receipt_key in (
        ('protocol_sha256', 'protocol_sha256'),
        ('measurement_sha256', 'measurement_sha256'),
        ('bootstrap_indices_sha256', 'bootstrap_indices_sha256'),
        ('analysis_amendment_sha256', 'analysis_source_sha256'),
    ):
        if diagnostic[diagnostic_key] != receipt[receipt_key]:
            raise ValueError(f'Diagnostic/provenance mismatch: {diagnostic_key}')
    with np.load(io.BytesIO(measurement_bytes), allow_pickle=False) as data:
        if not np.array_equal(data['ids'], np.arange(100)):
            raise ValueError('Measurement IDs must be exactly D0-99')
    with np.load(io.BytesIO(mass_bytes), allow_pickle=False) as data:
        windows = json.loads(str(data['windows']))
        masses, indices = data['masses'], data['indices']
    with np.load(io.BytesIO(reference_bytes), allow_pickle=False) as data:
        if not np.array_equal(indices, data['indices']):
            raise ValueError('Bootstrap indices differ from original reference archive')
    rows = diagnostic['two_state_windows']
    nboot, nblocks = diagnostic['bootstrap_draws'], diagnostic['n_development_blocks']
    if (windows != protocol['reference_windows'] or windows != [r['window'] for r in rows]
            or masses.shape != (len(rows), nboot, 2)
            or indices.shape != (nboot, nblocks)
            or not np.issubdtype(indices.dtype, np.integer)
            or np.any(indices < 0) or np.any(indices >= nblocks)):
        raise ValueError('Window/draw/indices layout mismatch')
    counts = []
    for row, draws in zip(rows, masses):
        count = count_bounds(draws, protocol['mass_bounds'])
        if (count['total'] != row['bootstrap_total']
                or count['valid'] != row['bootstrap_valid']
                or (bool(count['any_hit']) if count['valid'] else None)
                != row['mass_bounds_reached']):
            raise ValueError(f'Diagnostic/count mismatch: window {row["window"]}')
        counts.append({'window': row['window'], **count,
                       'full_sample_at_boundary': row['at_boundary']})
    return {
        'schema': 'pion-d-development-two-state-bound-count-audit-v1',
        'status': 'READ_ONLY_COUNTS_VERIFIED',
        'scope': 'public D0-99 only; no refit, simulation, or physical calibration',
        'bounds': protocol['mass_bounds'], 'inclusive_tolerance': TOLERANCE,
        'valid_rule': 'both masses finite; boundary hits remain valid',
        'verified_sha256': verified, 'windows': counts,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        result = audit()
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(1, f'Audit refused: {exc}\n')
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
