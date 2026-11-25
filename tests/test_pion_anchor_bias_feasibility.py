import csv

import pytest

from tasks.pion_projection.anchor_bias_feasibility_diagnostic import build, selected_inputs


def test_selected_anchor_bridge_is_inside_the_necessary_best_case_ceiling():
    inputs = selected_inputs()
    assert inputs["selected_C_over_R"] < inputs["C_over_R_max_for_any_best_case_pass"]
    assert inputs["best_case_lcb_before_C"] - 2 * inputs["selected_C_over_R"] > (
        inputs["delta_star_over_R2"]
    )


def test_range_only_common_bias_bound_cannot_reach_positive_effect_threshold():
    inputs = selected_inputs()
    best_case = inputs["best_case_lcb_before_C"] - 2 * inputs["trivial_range_only_C_over_R"]
    assert best_case < inputs["delta_star_over_R2"]
    assert inputs["trivial_range_only_C_over_R"] == pytest.approx(1.0)


def test_report_is_analytic_only_and_keeps_physical_gate_abstained(tmp_path):
    output = tmp_path / "bias-report"
    protocol = build(output)
    assert protocol["physical_score"] is None
    assert protocol["physical_evidence_denominator"] == {
        "planned": 1, "valid": 0, "failed": 0, "abstained": 1,
        "reason": "no anchor scalar-map, common-bias, independence, reference, or chain receipts",
    }
    with (output / "bias_sensitivity.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 101
    assert all(int(row["planned"]) == 1 and int(row["valid"]) == 1 for row in rows)
