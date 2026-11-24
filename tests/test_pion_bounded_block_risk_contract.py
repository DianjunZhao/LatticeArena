import hashlib
import json

import pytest

from tasks.pion_projection.bounded_block_risk_contract import (
    _synthetic_complete_contract,
    build_report,
    empty_contract,
    inspect_contract,
)


def test_current_null_contract_is_not_ready_and_keeps_physical_score_null():
    result = inspect_contract(empty_contract())

    assert result["status"] == "NOT_READY"
    assert result["structurally_complete"] is False
    assert result["certified"] is False
    assert result["physical_score"] is None
    assert any("dependence.method" in issue for issue in result["issues"])
    assert any("anchor.estimate_receipt_sha256" in issue for issue in result["issues"])
    assert any("estimand.reference_gate" in issue for issue in result["issues"])


@pytest.mark.parametrize(
    "method",
    [
        "graph_color_hoeffding",
        "markov_pseudo_gap_bernstein",
        "markov_time_varying_bernstein",
        "markov_time_varying_support_gap_bernstein",
    ],
)
def test_synthetic_complete_dependence_routes_only_request_human_review(method):
    result = inspect_contract(_synthetic_complete_contract(method))

    assert result["status"] == "CONTRACT_COMPLETE_REQUIRES_HUMAN_REVIEW"
    assert result["structurally_complete"] is True
    assert result["certified"] is False
    assert result["physical_score"] is None
    assert result["issues"] == []


def test_markov_route_requires_fixed_score_function_and_initial_law_receipt():
    contract = _synthetic_complete_contract("markov_pseudo_gap_bernstein")
    contract["dependence"]["score_function_time_homogeneous"] = False
    contract["dependence"]["initial_law_receipt_sha256"] = None

    result = inspect_contract(contract)

    assert result["status"] == "NOT_READY"
    assert any("score_function_time_homogeneous" in issue
               for issue in result["issues"])
    assert any("initial_law_receipt_sha256" in issue
               for issue in result["issues"])


@pytest.mark.parametrize(
    "field",
    ["evidence_receipt_sha256", "block_chain_receipt_sha256",
     "gamma_ps_lower_receipt_sha256"],
)
def test_every_markov_route_requires_chain_and_gap_evidence_receipts(field):
    contract = _synthetic_complete_contract("markov_pseudo_gap_bernstein")
    contract["dependence"][field] = None

    result = inspect_contract(contract)

    assert result["status"] == "NOT_READY"
    assert any(field in issue for issue in result["issues"])


def test_time_varying_markov_route_requires_kps_variances_and_schedule_receipts():
    contract = _synthetic_complete_contract("markov_time_varying_bernstein")
    result = inspect_contract(contract)
    assert result["status"] == "CONTRACT_COMPLETE_REQUIRES_HUMAN_REVIEW"
    assert result["physical_score"] is None

    contract["dependence"]["variance_upper_by_residue"] = [0.2]
    contract["dependence"]["score_schedule_receipt_sha256"] = None
    contract["dependence"]["pseudo_gap_k_ps_receipt_sha256"] = "bad"
    result = inspect_contract(contract)
    assert result["status"] == "NOT_READY"
    assert any("variance_upper_by_residue" in issue for issue in result["issues"])
    assert any("score_schedule_receipt_sha256" in issue for issue in result["issues"])
    assert any("pseudo_gap_k_ps_receipt_sha256" in issue for issue in result["issues"])


def test_support_gap_time_varying_route_needs_gap_but_not_k_or_variance_receipts():
    contract = _synthetic_complete_contract(
        "markov_time_varying_support_gap_bernstein",
    )
    dependence = contract["dependence"]
    assert dependence["pseudo_gap_k_ps"] is None
    assert dependence["variance_upper_by_residue"] is None
    assert inspect_contract(contract)["status"] == "CONTRACT_COMPLETE_REQUIRES_HUMAN_REVIEW"

    dependence["gamma_ps_lower_receipt_sha256"] = None
    result = inspect_contract(contract)
    assert result["status"] == "NOT_READY"
    assert any("gamma_ps_lower_receipt_sha256" in issue
               for issue in result["issues"])


def test_time_varying_markov_route_requires_anchor_score_shift_bound():
    contract = _synthetic_complete_contract("markov_time_varying_bernstein")
    contract["anchor"]["time_varying_score_shift_receipt_sha256"] = None
    result = inspect_contract(contract)
    assert result["status"] == "NOT_READY"
    assert any("time_varying_score_shift_receipt_sha256" in issue
               for issue in result["issues"])


def test_time_varying_markov_route_rejects_anchor_shift_below_fixed_score_floor():
    contract = _synthetic_complete_contract("markov_time_varying_bernstein")
    contract["anchor"]["time_varying_score_shift_bound"] = 0.1
    result = inspect_contract(contract)
    assert result["status"] == "NOT_READY"
    assert any("2B/R" in issue for issue in result["issues"])


@pytest.mark.parametrize("field,value", [
    ("pseudo_gap_k_ps", 0),
    ("pseudo_gap_k_ps", 21),
    ("score_function_time_homogeneous", True),
    ("variance_upper_by_residue", [0.2, 0]),
    ("variance_upper_receipt_sha256", None),
])
def test_time_varying_markov_route_fails_closed_on_malformed_variance_schedule(field, value):
    contract = _synthetic_complete_contract("markov_time_varying_bernstein")
    contract["dependence"][field] = value
    result = inspect_contract(contract)
    assert result["status"] == "NOT_READY"
    assert any(field in issue for issue in result["issues"])


def test_post_burn_in_tv_requires_audited_bound_and_preserves_score_alpha():
    contract = _synthetic_complete_contract("markov_pseudo_gap_bernstein")
    contract["dependence"].update({
        "initial_law_mode": "post_burn_in_tv",
        "burn_in_blocks": 8,
        "initial_law_tv_bound": 0.02,
    })

    result = inspect_contract(contract)

    assert result["status"] == "NOT_READY"
    assert any("F * delta must be smaller" in issue for issue in result["issues"])


@pytest.mark.parametrize("field,value", [
    ("burn_in_blocks", -1),
    ("initial_law_tv_bound", 1.01),
    ("initial_law_mode", "unspecified"),
    ("initial_law_mode", []),
    ("initial_law_tv_bound", 10**400),
])
def test_markov_initial_law_fields_are_range_checked(field, value):
    contract = _synthetic_complete_contract("markov_pseudo_gap_bernstein")
    contract["dependence"][field] = value

    result = inspect_contract(contract)

    assert result["status"] == "NOT_READY"
    assert any(field in issue for issue in result["issues"])


def test_unrepresentably_large_comparison_family_does_not_crash_markov_tv_check():
    contract = _synthetic_complete_contract("markov_pseudo_gap_bernstein")
    contract["inference"]["F"] = 10**400
    contract["dependence"].update({
        "initial_law_mode": "post_burn_in_tv",
        "burn_in_blocks": 8,
        "initial_law_tv_bound": 0.005,
    })

    result = inspect_contract(contract)

    assert result["status"] == "NOT_READY"
    assert any("F * delta must be smaller" in issue for issue in result["issues"])



def test_target_mstar_is_explicit_and_finite():
    contract = _synthetic_complete_contract()
    contract["estimand"]["target"]["m_star"] = float("nan")

    result = inspect_contract(contract)
    assert result["status"] == "NOT_READY"
    assert any("target.m_star" in issue for issue in result["issues"])

def test_alpha_budget_and_prediction_difference_bound_fail_closed():
    alpha_over = _synthetic_complete_contract()
    alpha_over["inference"]["alpha_score"] = 0.05
    assert inspect_contract(alpha_over)["status"] == "NOT_READY"
    assert any("alpha_score + alpha_anchor" in issue
               for issue in inspect_contract(alpha_over)["issues"])

    bound_over = _synthetic_complete_contract()
    bound_over["estimand"]["prediction_difference_abs_bound"] = 2.01
    assert any("exceeds score_scale_R" in issue
               for issue in inspect_contract(bound_over)["issues"])


def test_bad_receipt_and_mismatched_anchor_units_fail_closed():
    contract = _synthetic_complete_contract()
    contract["anchor"]["common_bias_coverage_receipt_sha256"] = "not-a-hash"
    contract["anchor"]["units"] = "SYNTHETIC_ONLY_other_unit"

    result = inspect_contract(contract)
    assert result["status"] == "NOT_READY"
    assert any("common_bias_coverage_receipt_sha256" in issue
               for issue in result["issues"])
    assert any("anchor.units" in issue for issue in result["issues"])



def test_anchor_coverage_methods_require_their_specific_assumptions():
    normal = _synthetic_complete_contract()
    normal["anchor"].update({
        "coverage_method": "known_sigma_normal_interval",
        "coverage_parameters": {
            "sample_count_n_A": 32,
            "known_sigma": 0.05,
            "normality_assumption": "SYNTHETIC_ONLY normal anchor observations",
            "parameter_receipt_sha256": hashlib.sha256(b"SYNTHETIC_ONLY normal parameters").hexdigest(),
        },
    })
    result = inspect_contract(normal)
    assert result["status"] == "CONTRACT_COMPLETE_REQUIRES_HUMAN_REVIEW"

    del normal["anchor"]["coverage_parameters"]["normality_assumption"]
    result = inspect_contract(normal)
    assert result["status"] == "NOT_READY"
    assert any("normality_assumption" in issue for issue in result["issues"])


def test_common_bias_bound_must_be_explicit_and_bounded_by_total_B():
    contract = _synthetic_complete_contract()
    contract["anchor"]["common_bias_bound_C"] = contract["anchor"]["total_error_bound_B"] + 0.01

    result = inspect_contract(contract)
    assert result["status"] == "NOT_READY"
    assert any("common_bias_bound_C: cannot exceed total_error_bound_B" in issue
               for issue in result["issues"])

    del contract["anchor"]["bound_combination_rule"]
    result = inspect_contract(contract)
    assert any("bound_combination_rule" in issue for issue in result["issues"])


def test_total_anchor_bound_must_cover_sampling_radius_plus_common_bias():
    contract = _synthetic_complete_contract()
    contract["anchor"]["total_error_bound_B"] = 0.20

    result = inspect_contract(contract)
    assert result["status"] == "NOT_READY"
    assert any("random radius plus common_bias_bound_C" in issue
               for issue in result["issues"])


def test_sampling_coverage_methods_require_positive_anchor_alpha():
    contract = _synthetic_complete_contract()
    contract["inference"]["alpha_anchor"] = 0.0
    contract["anchor"]["coverage_probability_lower_bound"] = 1.0

    result = inspect_contract(contract)
    assert result["status"] == "NOT_READY"
    assert any("alpha_anchor must be positive" in issue
               for issue in result["issues"])

def test_invalid_top_level_contract_returns_not_ready_without_raising():
    result = inspect_contract(None)

    assert result == {
        "schema_valid": False,
        "status": "NOT_READY",
        "structurally_complete": False,
        "certified": False,
        "physical_score": None,
        "issues": ["contract: expected an object"],
    }


def test_diagnostic_report_denominators_and_payload_hashes(tmp_path):
    output = tmp_path / "diagnostic"
    summary = build_report(output)

    assert summary["denominators"] == {
        "planned": 16, "valid": 5, "failed": 11, "abstained": 0,
    }
    assert summary["physical_score"] is None
    receipt = json.loads((output / "run_receipt.json").read_text())
    assert receipt["schema"] == "latticearena-run-receipt-v1"
    assert receipt["status"] == "complete"
    assert len(receipt["denominators"]) == 16
    assert sum(row["planned"] for row in receipt["denominators"].values()) == 16
    assert sum(row["valid"] for row in receipt["denominators"].values()) == 5
    assert sum(row["failed"] for row in receipt["denominators"].values()) == 11
    assert sum(row["abstained"] for row in receipt["denominators"].values()) == 0
    assert sum(row["not_run"] for row in receipt["denominators"].values()) == 0
    assert sum(row["count"] for row in receipt["reason_rows"]
               if row["state"] == "failed") == 11
    assert "not scientific success" in receipt["text_flow"]
    assert set(receipt["scenario"]["source_hashes"]) == {
        "tasks/pion_projection/bounded_block_risk_contract.py",
        "tasks/pion_projection/bounded_block_risk_contract_v1.json",
        "tasks/pion_projection/bounded_block_risk_score.py",
        "tasks/pion_projection/bounded_block_risk_markov_varying.py",
        "core/receipts.py",
    }
    assert len(receipt["artifact_hashes"]) == 9
    manifest = json.loads((output / "artifact_hashes.json").read_text())
    assert manifest["algorithm"] == "sha256"
    assert len(manifest["files"]) == 10
    for name, expected in manifest["files"].items():
        actual = hashlib.sha256((output / name).read_bytes()).hexdigest()
        assert actual == expected
    for name, expected in receipt["artifact_hashes"].items():
        actual = hashlib.sha256((output / name).read_bytes()).hexdigest()
        assert actual == expected

    report = (output / "README.md").read_text()
    assert "no correlator, anchor, gap, validation, holdout" in report
    assert "CONTRACT_COMPLETE_REQUIRES_HUMAN_REVIEW" in report
    assert "F*delta < alpha_score" in report
    assert "`M/k_ps`" in report
    assert "support-only" in report
    assert "physical_score remains null" in report
    assert "run_receipt.json" in report
    assert "not that any dependence, anchor, reference, coverage or physical claim succeeded" in report


def test_contract_json_and_python_draft_are_identical():
    from pathlib import Path

    contract_path = Path(__file__).parents[1] / "tasks/pion_projection/bounded_block_risk_contract_v1.json"
    assert json.loads(contract_path.read_text()) == empty_contract()
