import hashlib
import json

import pytest

from tasks.optimize_gaussian.candidate_contract import (
    build_report,
    candidate_spec_for,
    operator_contract_for,
)


def test_optimize_candidate_contract_is_registered_but_explicitly_diagnostic():
    operator = operator_contract_for()
    candidate = candidate_spec_for()

    assert operator["name"] == "optimize-chebyshev-diagnostic-v1"
    assert operator["constraints"]["physical_contract_frozen"] is False
    assert operator["constraints"]["production_evaluator_connected"] is False
    assert candidate["builder"] == (
        "tasks.optimize_gaussian.chebyshev_baseline:apply_hopping_filter_cpu"
    )
    assert candidate["parameters"]["control_points"] == [0.0, 0.25, 0.5, 0.75, 1.0]


def test_optimize_candidate_contract_rejects_invalid_controls():
    with pytest.raises(ValueError, match="nondecreasing"):
        candidate_spec_for([0.0, 0.6, 0.4, 0.8, 1.0])
    with pytest.raises(ValueError, match="fixed to 1"):
        candidate_spec_for([0.0, 0.25, 0.5, 0.75, 0.9])


def test_candidate_contract_report_is_hashed_and_has_text_flow(tmp_path):
    output = tmp_path / "candidate-contract"
    report = build_report(output)
    manifest = json.loads((output / "artifact_hashes.json").read_text())

    assert report["status"] == "DIAGNOSTIC_SCHEMA_ONLY"
    assert report["physical_score"] is None
    assert report["data_access"] == "none"
    assert report["denominators"]["coefficient_fit"]["planned"] == 0
    assert "versioned diagnostic contract" in (output / "README.md").read_text()
    assert set(manifest) == {
        "README.md", "contract.json", "snapshot_candidate_contract.py",
        "snapshot_chebyshev_baseline.py", "snapshot_core_specs.py",
        "snapshot_kernels.py",
    }
    for name, expected in manifest.items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == expected
