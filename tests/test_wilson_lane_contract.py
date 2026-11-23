import hashlib
import json

from tasks.wilson_loop.lane_contract import (
    _synthetic_contract,
    build,
    empty_contract,
    inspect_contract,
)


def test_null_draft_stays_not_ready_with_two_separate_estimands():
    result = inspect_contract(empty_contract())
    assert result["schema_valid"]
    assert result["status"] == "DRAFT_NOT_READY"
    assert result["physical_score"] is None
    assert result["certified"] is False
    assert set(result["lanes"]) == {
        "finite_T_Creutz", "ground_state_discrete_static_force",
    }
    assert all(row["status"] == "NOT_READY" for row in result["lanes"].values())


def test_c_complete_does_not_make_f_ready_and_complete_fixture_is_not_certified():
    c_only = inspect_contract(_synthetic_contract(
        complete_creutz=True, complete_force=False,
    ))
    assert c_only["lanes"]["finite_T_Creutz"]["structurally_complete"]
    assert c_only["lanes"]["finite_T_Creutz"]["status"] == (
        "CONTRACT_COMPLETE_REQUIRES_HUMAN_REVIEW"
    )
    assert c_only["lanes"]["ground_state_discrete_static_force"]["status"] == "NOT_READY"
    both = inspect_contract(_synthetic_contract(
        complete_creutz=True, complete_force=True,
    ))
    for row in both["lanes"].values():
        assert row["status"] == "CONTRACT_COMPLETE_REQUIRES_HUMAN_REVIEW"
        assert row["certified"] is False
        assert row["physical_score"] is None


def test_invalid_temporal_extent_boolean_integer_and_stencil_are_rejected():
    contract = _synthetic_contract(complete_creutz=True, complete_force=True)
    contract["common"]["geometry"]["temporal_extent"] = 3
    contract["lanes"]["finite_T_Creutz"]["primary"]["R"] = True
    result = inspect_contract(contract)
    c = result["lanes"]["finite_T_Creutz"]
    assert not c["structurally_complete"]
    assert any("primary.T: T+1 exceeds" in message for message in c["issues"])
    assert any("primary.R: expected a positive integer" in message
               for message in c["issues"])


def test_missing_qhx_receipt_alpha_overflow_and_budget_overrun_are_rejected():
    contract = _synthetic_contract(complete_creutz=True, complete_force=True)
    force = contract["lanes"]["ground_state_discrete_static_force"]
    force["spectral_bounds"] = [row for row in force["spectral_bounds"]
                                 if row["component"] != "q"]
    force["systematic_bounds"][0]["bound"] = 0.02
    force["systematic_bounds"][0]["independent_review_receipt"] = ""
    force["inference"]["alpha_allocations"] = {"first": 0.04, "second": 0.02}
    result = inspect_contract(contract)
    issues = result["lanes"]["ground_state_discrete_static_force"]["issues"]
    assert any("spectral_bounds.q: missing required evidence" in message
               for message in issues)
    assert any("independent_review_receipt: missing" in message for message in issues)
    assert any("alpha_allocations: sum exceeds alpha_total" in message
               for message in issues)
    assert any("force-level systematic plus statistical budgets exceed total_tolerance" in message
               for message in issues)


def test_qhx_inputs_are_dimensionless_and_force_budget_is_in_force_units():
    contract = _synthetic_contract(complete_creutz=True, complete_force=True)
    force = contract["lanes"]["ground_state_discrete_static_force"]
    assert force["spectral_bounds"][0]["units"] == "dimensionless"
    assert all(row["units"] == force["units"] for row in force["systematic_bounds"])
    force["spectral_bounds"][0]["units"] = force["units"]
    result = inspect_contract(contract)
    issues = result["lanes"]["ground_state_discrete_static_force"]["issues"]
    assert any("spectral_bounds.q.units: missing or inconsistent" in message
               for message in issues)


def test_schema_mismatch_cannot_return_structural_completeness():
    contract = _synthetic_contract(complete_creutz=True, complete_force=True)
    contract["schema"] = "future-or-unknown-schema"
    result = inspect_contract(contract)
    assert result["schema_valid"] is False
    assert all(not row["structurally_complete"] for row in result["lanes"].values())
    assert all(any("contract.schema" in message for message in row["issues"])
               for row in result["lanes"].values())


def test_build_report_snapshots_source_and_hashes_every_artifact(tmp_path):
    output = tmp_path / "wilson-report"
    summary = build(output)
    manifest = json.loads((output / "artifact_hashes.json").read_text())
    assert "snapshot_lane_contract.py" in manifest
    assert summary["physical_score"] is None
    for name, expected in manifest.items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == expected
