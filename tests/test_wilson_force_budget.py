import hashlib
import json
import math
from pathlib import Path

import pytest

from tasks.wilson_loop.force_budget import (
    COMPONENT_FRACTIONS,
    FORCE_CORNER_COUNT,
    propagate_force_budget,
    uniform_loop_cap,
)
from tasks.wilson_loop.force_budget_diagnostic import build as build_diagnostic


def _same_cap(q, h, x):
    return {"q": [[q] * 4] * 2, "h": [[h] * 4] * 2, "x": [[x] * 4] * 2}


def test_force_budget_report_binds_shared_numeric_conversion(tmp_path):
    output = tmp_path / "force-budget"
    result = build_diagnostic(output)
    protocol = json.loads((output / "protocol.json").read_text())
    assert result["physical_score"] is None
    assert "core/numerics.py" in protocol["input_hashes"]
    helper_bytes = (output / "snapshot_core_numerics.py").read_bytes()
    helper_digest = hashlib.sha256(helper_bytes).hexdigest()
    assert protocol["input_hashes"]["core/numerics.py"] == helper_digest
    assert helper_digest == hashlib.sha256(
        (Path(__file__).resolve().parents[1] / "core/numerics.py").read_bytes()
    ).hexdigest()
    manifest = json.loads((output / "artifact_hashes.json").read_text())
    for name, expected in manifest.items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == expected


def test_uniform_loop_cap_exactly_closes_component_force_budget():
    reference = 0.73
    bounds = {
        name: uniform_loop_cap(COMPONENT_FRACTIONS[name], reference)
        for name in ("q", "h", "x")
    }
    result = propagate_force_budget(
        _same_cap(bounds["q"], bounds["h"], bounds["x"]), reference,
        model_truncation_bound=0.01 * reference,
        statistical_halfwidth=0.05 * reference,
    )
    for name, budget in COMPONENT_FRACTIONS.items():
        assert result["component_relative_bounds"][name] == pytest.approx(budget)
    assert result["assumption_only_numeric_gate_pass"]
    assert result["physical_score"] is None
    assert result["certification_status"].startswith("NOT_CERTIFIED")


def test_exact_joint_log_bound_is_below_factorized_component_bound():
    bounds = {
        "q": [[0.01, 0.03, 0.02, 0.01], [0.02, 0.01, 0.04, 0.01]],
        "h": [[0.03, 0.02, 0.02, 0.01], [0.01, 0.02, 0.03, 0.02]],
        "x": [[0.005, 0.01, 0.02, 0.01], [0.01, 0.005, 0.01, 0.02]],
    }
    result = propagate_force_budget(bounds, 0.8)
    assert result["combined_log_corner_bound"] <= result["factorized_qhx_bound"]
    assert result["factorized_qhx_bound"] == pytest.approx(
        sum(result["component_force_bounds"].values())
    )
    assert result["force_corner_count"] == FORCE_CORNER_COUNT == 8


def test_raw_interpretation_of_current_percentages_exceeds_force_budgets():
    result = propagate_force_budget(_same_cap(0.015, 0.015, 0.01), 1.0)
    assert result["component_relative_bounds"]["q"] > 0.015
    assert result["component_relative_bounds"]["h"] > 0.015
    assert result["component_relative_bounds"]["x"] > 0.01
    assert result["assumption_only_numeric_gate_pass"] is False


@pytest.mark.parametrize("reference", [0, -1, math.inf, math.nan, True, "1.0", 2**53 + 1])
def test_reference_force_lower_bound_must_be_positive_finite(reference):
    with pytest.raises(ValueError, match="reference_force_lower"):
        propagate_force_budget(_same_cap(0, 0, 0), reference)


@pytest.mark.parametrize("bad", [-0.1, math.inf, math.nan])
def test_negative_or_nonfinite_loop_contamination_is_rejected(bad):
    with pytest.raises(ValueError):
        propagate_force_budget(_same_cap(bad, 0, 0), 1.0)


def test_corner_shape_and_component_names_are_fail_closed():
    with pytest.raises(ValueError, match="four loop corners"):
        propagate_force_budget({"q": [[0] * 3] * 2, "h": [[0] * 4] * 2,
                                "x": [[0] * 4] * 2}, 1.0)
    with pytest.raises(ValueError, match="exactly q, h, and x"):
        propagate_force_budget(_same_cap(0, 0, 0), 1.0,
                                component_fractions={"q": 0.01, "h": 0.01})


def test_qhx_bounds_reject_unregistered_components():
    bounds = _same_cap(0, 0, 0)
    bounds["unregistered_thermal_term"] = [[0.0] * 4] * 2

    with pytest.raises(ValueError, match="qhx_bounds must contain exactly q, h, and x"):
        propagate_force_budget(bounds, 1.0)
