import json
from pathlib import Path

import numpy as np
import pytest

from core.io import digest, fingerprint
from tasks.wilson_loop.identity import (loops_sha256, measurement_spec,
                                       write_marker)
from tasks.wilson_loop.reference_gate_runner import run_reference_gate_diagnostic


REPO = Path(__file__).resolve().parents[1]
TASK = REPO / 'tasks' / 'wilson_loop'
PROTOCOL_PATH = TASK / 'protocol_d_20261120.json'


def _synthetic_loops(n):
    rng = np.random.default_rng(7812)
    t = np.asarray([4, 5, 6, 7, 8], dtype=float)
    loops = np.empty((n, 7, 4, 5), dtype=np.float64)
    for cfg in range(n):
        for kernel in range(7):
            for r in range(4):
                slope = .22 + .025 * r + .002 * kernel
                curvature = .0008 * (r + 1)
                noise = rng.normal(0, .006, size=5)
                loops[cfg, kernel, r] = np.exp(-slope * t + curvature * t**2 + noise)
    return loops


def _write_transaction(root, n):
    root.mkdir()
    protocol = json.loads(PROTOCOL_PATH.read_text())
    spec = measurement_spec(protocol, 'development')
    ids = np.arange(n, dtype=np.int64)
    loops = _synthetic_loops(n)
    generation = fingerprint(spec)
    npz_path = root / 'development.npz'
    np.savez_compressed(npz_path, ids=ids, loops=loops,
                        protocol_hash=fingerprint(protocol), generation=generation)
    provenance = {
        'generation': generation,
        'kernel_sha256': spec['kernel_sha256'],
        'dependencies': spec['dependencies'],
        'input_manifest_sha256': protocol['input_manifest']['sha256'],
        'ensemble': protocol['ensemble'],
        'records': [{'id': int(cfg), 'loops_sha256': loops_sha256(loops[cfg:cfg + 1]),
                     'hmc_trajectory': 401 + 5 * int(cfg),
                     'gauge_sha256': f'{int(cfg) + 1:064x}'}
                    for cfg in ids],
    }
    provenance_path = root / 'development_provenance.json'
    provenance_path.write_text(json.dumps(provenance, sort_keys=True) + '\n')
    write_marker(root, 'development', npz_path, provenance_path, spec, loops)


def test_incomplete_development_prefix_fails_before_output(tmp_path):
    source = tmp_path / 'development'
    _write_transaction(source, 52)
    output = tmp_path / 'diagnostic'

    with pytest.raises(ValueError, match='incomplete development transaction: 52/100'):
        run_reference_gate_diagnostic(source, output, PROTOCOL_PATH)

    assert not output.exists()


def test_complete_development_writes_text_receipt_csv_and_figures(tmp_path):
    source = tmp_path / 'development'
    output = tmp_path / 'diagnostic'
    _write_transaction(source, 100)

    summary = run_reference_gate_diagnostic(source, output, PROTOCOL_PATH)
    receipt = json.loads((output / 'receipt.json').read_text())
    result = json.loads((output / 'results.json').read_text())

    assert summary['receipt']['scope'] == 'development_diagnostic_only'
    assert receipt['classification'] == 'development_diagnostic_only'
    assert receipt['status'] == 'PROPOSAL_NOT_FROZEN'
    assert receipt['production_score'] is None
    assert receipt['validation_accessed'] is False
    assert receipt['shared_holdout_accessed'] is False
    assert receipt['raw_gauge_bytes_read_by_runner'] is False
    assert receipt['bootstrap_indices_sha256'] == result['index_sha256_le_i8']
    assert len(receipt['ids']) == 100
    assert len(set(receipt['trajectory_ids'])) == 100
    assert all(len(value) == 64 for value in receipt['gauge_sha256_values'])
    for name in ('REFERENCE_REPORT.md', 'reference_window_rows.csv',
                 'reference_failures.csv', 'candidate_decisions.csv',
                 'reference_windows.png', 'reference_window_z.png',
                 'reference_joint_max.png', 'bootstrap_indices_le_i8.bin'):
        assert (output / name).is_file()
        assert (output / name).stat().st_size > 0
    assert 'production_score=null' in (output / 'REFERENCE_REPORT.md').read_text()


def test_existing_output_directory_is_never_overwritten(tmp_path):
    source = tmp_path / 'development'
    output = tmp_path / 'diagnostic'
    _write_transaction(source, 52)
    output.mkdir()
    sentinel = output / 'keep.txt'
    sentinel.write_text('keep')

    with pytest.raises(FileExistsError, match='refusing to overwrite'):
        run_reference_gate_diagnostic(source, output, PROTOCOL_PATH)

    assert sentinel.read_text() == 'keep'


def test_source_bytes_are_bound_in_receipt(tmp_path):
    source = tmp_path / 'development'
    output = tmp_path / 'diagnostic'
    _write_transaction(source, 100)

    run_reference_gate_diagnostic(source, output, PROTOCOL_PATH)
    receipt = json.loads((output / 'receipt.json').read_text())
    assert receipt['source_hashes']['reference_gate_runner.py'] == digest(
        TASK / 'reference_gate_runner.py')
    assert receipt['protocol_sha256'] == digest(PROTOCOL_PATH)
