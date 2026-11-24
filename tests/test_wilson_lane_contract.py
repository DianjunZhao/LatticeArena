import csv
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


def test_global_sign_reversal_is_rejected_for_both_physical_conventions():
    contract = _synthetic_contract(complete_creutz=True, complete_force=True)
    creutz = contract["lanes"]["finite_T_Creutz"]
    for row in creutz["stencil"]:
        row["coefficient"] *= -1
    result = inspect_contract(contract)
    c_issues = result["lanes"]["finite_T_Creutz"]["issues"]
    assert any("prescribed signed four-point convention" in message
               for message in c_issues)
    assert not result["lanes"]["finite_T_Creutz"]["structurally_complete"]

    contract = _synthetic_contract(complete_creutz=True, complete_force=True)
    force = contract["lanes"]["ground_state_discrete_static_force"]
    for row in force["force_stencil"]:
        row["coefficient"] *= -1
    result = inspect_contract(contract)
    f_issues = result["lanes"]["ground_state_discrete_static_force"]["issues"]
    assert any("coefficients must encode candidate minus reference" in message
               for message in f_issues)
    assert not result["lanes"]["ground_state_discrete_static_force"]["structurally_complete"]


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


def test_force_precision_with_wrong_units_is_rejected_and_not_summed_as_force():
    contract = _synthetic_contract(complete_creutz=True, complete_force=True)
    force = contract["lanes"]["ground_state_discrete_static_force"]
    force["inference"]["statistical_precision_target"] = 100.0
    force["inference"]["precision_units"] = "dimensionless"
    result = inspect_contract(contract)
    issues = result["lanes"]["ground_state_discrete_static_force"]["issues"]
    assert any("precision_units: expected 'SYNTHETIC_ONLY_GeV'" in message
               for message in issues)
    assert not any("systematic plus statistical budgets exceed total_tolerance" in message
                   for message in issues)


def test_null_common_kernel_list_is_reported_without_crashing():
    contract = _synthetic_contract(complete_creutz=True, complete_force=True)
    contract["common"]["kernel_ids"] = None
    result = inspect_contract(contract)
    assert any("common.kernel_ids: expected unique nonempty identifiers" in message
               for message in result["common_issues"])
    assert all(not row["structurally_complete"]
               for row in result["lanes"].values())


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
    report = (output / "README.md").read_text()
    assert "|fixture|lane|planned|valid|failed|abstained|status|" in report
    with (output / "lane_summary.csv").open(newline="") as stream:
        denominator_rows = list(csv.DictReader(stream))
    assert sum(int(row["planned"]) for row in denominator_rows) == 14
    assert sum(int(row["valid"]) for row in denominator_rows) == 6
    assert sum(int(row["failed"]) for row in denominator_rows) == 8
    assert sum(int(row["abstained"]) for row in denominator_rows) == 0
    assert all(int(row["planned"]) == int(row["valid"]) + int(row["failed"])
               + int(row["abstained"]) for row in denominator_rows)
    c_reverse = summary["fixtures"]["synthetic_C_reversed_sign"]["lanes"][
        "finite_T_Creutz"]
    assert not c_reverse["structurally_complete"]
    f_reverse = summary["fixtures"]["synthetic_F_reversed_sign"]["lanes"][
        "ground_state_discrete_static_force"]
    assert not f_reverse["structurally_complete"]
    f_units = summary["fixtures"]["synthetic_F_wrong_precision_units"]["lanes"][
        "ground_state_discrete_static_force"]
    assert not f_units["structurally_complete"]
    assert any("precision_units: expected" in message for message in f_units["issues"])
    null_kernels = summary["fixtures"]["synthetic_null_common_kernel_ids"]["lanes"]
    assert all(not row["structurally_complete"] for row in null_kernels.values())
    for name, expected in manifest.items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == expected
