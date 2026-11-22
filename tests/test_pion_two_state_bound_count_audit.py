"""Focused CPU tests: inclusive counting, invalid draws, and receipt refusal."""
import hashlib
import json

import numpy as np
import pytest

from tasks.pion_projection.two_state_bound_count_audit import (
    ARCHIVE, PROTOCOL, SOURCE, TOLERANCE, audit, count_bounds,
)


def test_counts_keep_joint_valid_denominator_and_inclusive_edges():
    lo, hi = 0.1, 3.0
    values = np.array([
        [lo + TOLERANCE, 1.0], [1.0, hi - TOLERANCE],
        [hi - TOLERANCE, lo + TOLERANCE], [1.0, 2.0],
        [np.nan, hi], [lo, np.inf],
    ])
    assert count_bounds(values, [lo, hi]) == {
        'total': 6, 'valid': 4, 'invalid': 2,
        'm0_lower_hits': 1, 'm0_upper_hits': 1,
        'm1_lower_hits': 1, 'm1_upper_hits': 1, 'any_hit': 3,
    }


def fixture_archive(root):
    """Hand-authored archive; no fit, random sampling, or restricted inputs."""
    directory = root / ARCHIVE
    directory.mkdir(parents=True)
    (root / PROTOCOL).parent.mkdir(parents=True)
    (root / PROTOCOL).write_text(json.dumps({
        'development': [0, 99], 'reference_windows': [[4, 5, 6]],
        'mass_bounds': [0.1, 3.0],
    }))
    (root / SOURCE).write_text('# fixture source identity\n')
    (directory / 'development_provenance.json').write_text('{}')
    np.savez(directory / 'development.npz', ids=np.arange(100))
    index = np.array([[0, 1], [1, 1], [0, 0]])
    np.savez(directory / 'reference_bootstrap.npz', indices=index)
    np.savez(directory / 'two_state_bootstrap.npz', indices=index,
             masses=np.array([[[1., 2.], [1., 3.], [np.nan, 3.]]]),
             windows=np.array(json.dumps([[4, 5, 6]])))

    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    receipt = {
        'schema': 'pion-two-state-development-diagnostic-provenance-v1',
        'protocol_sha256': digest(root / PROTOCOL),
        'analysis_source_sha256': digest(root / SOURCE),
        'measurement_sha256': digest(directory / 'development.npz'),
        'measurement_provenance_sha256': digest(directory / 'development_provenance.json'),
        'bootstrap_indices_sha256': digest(directory / 'reference_bootstrap.npz'),
    }
    diagnostic = {
        'schema': 'pion-two-state-development-diagnostic-v1',
        'n_development_configurations': 100, 'bootstrap_draws': 3,
        'n_development_blocks': 2,
        'two_state_windows': [{'window': [4, 5, 6], 'bootstrap_total': 3,
                               'bootstrap_valid': 2, 'mass_bounds_reached': True,
                               'at_boundary': False}],
        **{k: receipt[k] for k in ('protocol_sha256', 'measurement_sha256',
                                   'bootstrap_indices_sha256')},
        'analysis_amendment_sha256': receipt['analysis_source_sha256'],
    }
    (directory / 'two_state_diagnostic.json').write_text(json.dumps(diagnostic))
    receipt['outputs_sha256'] = {name: digest(directory / name) for name in (
        'two_state_diagnostic.json', 'two_state_bootstrap.npz')}
    path = directory / 'two_state_diagnostic_provenance.json'
    path.write_text(json.dumps(receipt))
    return digest(path)


def test_verified_fixture_counts(tmp_path):
    pin = fixture_archive(tmp_path)
    result = audit(tmp_path, trusted_provenance_sha256=pin)
    row = result['windows'][0]
    assert (row['total'], row['valid'], row['invalid']) == (3, 2, 1)
    assert row['any_hit'] == row['m1_upper_hits'] == 1
    assert row['full_sample_at_boundary'] is False
    assert len(result['verified_sha256']) == 8


@pytest.mark.parametrize('relative', [
    ARCHIVE / 'two_state_diagnostic_provenance.json', PROTOCOL,
    ARCHIVE / 'two_state_diagnostic.json', ARCHIVE / 'two_state_bootstrap.npz',
    ARCHIVE / 'development_provenance.json', ARCHIVE / 'development.npz',
    ARCHIVE / 'reference_bootstrap.npz', SOURCE,
])
def test_changed_archived_bytes_are_refused(tmp_path, relative):
    pin = fixture_archive(tmp_path)
    path = tmp_path / relative
    path.write_bytes(path.read_bytes() + b'\n')
    with pytest.raises(ValueError, match='SHA-256 mismatch'):
        audit(tmp_path, trusted_provenance_sha256=pin)
