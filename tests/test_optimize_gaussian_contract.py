import hashlib
import json

from tasks.optimize_gaussian.contract import (
    COMPARISONS,
    _synthetic_complete_contract,
    build,
    empty_contract,
    inspect_contract,
)


def test_null_draft_keeps_both_user_selected_contrasts_not_ready():
    result = inspect_contract(empty_contract())
    assert result["schema_valid"]
    assert result["status"] == "NOT_READY"
    assert result["physical_score"] is None
    assert result["certified"] is False
    assert result["structurally_complete"] is False
    assert result["issues"]
    assert empty_contract()["comparison_family"] == list(COMPARISONS)


def test_synthetic_complete_contract_requires_human_review_and_never_scores():
    result = inspect_contract(_synthetic_complete_contract())
    assert result["status"] == "CONTRACT_COMPLETE_REQUIRES_HUMAN_REVIEW"
    assert result["structurally_complete"] is True
    assert result["certified"] is False
    assert result["physical_score"] is None


def test_missing_comparison_or_invalid_r_star_stays_not_ready():
    contract = _synthetic_complete_contract()
    contract["comparison_family"] = [COMPARISONS[0]]
    result = inspect_contract(contract)
    assert result["status"] == "NOT_READY"
    assert any("comparison_family" in issue for issue in result["issues"])

    contract = _synthetic_complete_contract()
    contract["D06_effect_threshold"]["r_star"] = True
    result = inspect_contract(contract)
    assert any("r_star: expected a positive finite value" in issue
               for issue in result["issues"])


def test_incomplete_chebyshev_contract_and_malformed_objects_fail_closed():
    contract = _synthetic_complete_contract()
    contract["D11_strong_spectral_operator"]["spectral_interval"] = [1.0, -1.0]
    result = inspect_contract(contract)
    assert any("spectral_interval" in issue for issue in result["issues"])

    contract["D04_reference"] = []
    contract["comparison_family"] = {}
    contract.pop("physical_score")
    result = inspect_contract(contract)
    assert result["status"] == "NOT_READY"
    assert any("D04_reference: expected an object" in issue
               for issue in result["issues"])
    assert any("comparison_family" in issue for issue in result["issues"])
    assert any("physical_score: field must exist and remain null" in issue
               for issue in result["issues"])


def test_contract_report_lists_text_flow_and_hashes_all_artifacts(tmp_path):
    output = tmp_path / "optimize-contract"
    summary = build(output)
    assert summary["physical_score"] is None
    assert summary["fixtures"]["current_null_draft"]["status"] == "NOT_READY"
    complete = summary["fixtures"]["synthetic_complete_requires_review"]
    assert complete["status"] == "CONTRACT_COMPLETE_REQUIRES_HUMAN_REVIEW"
    report = (output / "README.md").read_text()
    assert "Text decision flow" in report
    assert "D04" in report and "D06" in report and "D11" in report
    hashes = json.loads((output / "artifact_hashes.json").read_text())
    assert "snapshot_optimize_contract.py" in hashes
    for name, expected in hashes.items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == expected
