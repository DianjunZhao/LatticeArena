import math

import numpy as np
import pytest

from tasks.pion_projection.bounded_block_risk_markov_gap import (
    conditional_block_risk_markov_lcb,
    markov_gap_radius,
)


def calibration():
    return dict(
        score_scale_R=2.0,
        gamma_ps_lower=1.0,
        family=2,
        alpha_score=0.04,
        alpha_anchor=0.01,
        alpha_total=0.05,
        relative_anchor_bound_B_over_R=0.03,
    )


def test_markov_lcb_uses_gap_radius_and_keeps_failed_blocks_in_N():
    result = conditional_block_risk_markov_lcb(
        [8.0, -8.0, 2.0, np.nan],
        valid_blocks=np.array([True, True, True, False]),
        **calibration(),
    )

    expected_radius = markov_gap_radius(
        blocks=4, gamma_ps_lower=1.0, family=2, alpha_s=0.04,
    )
    assert result["status"] == "CONDITIONAL_MARKOV_PSEUDOGAP_BOUND_ONLY"
    assert result["physical_score"] is None
    assert result["certified"] is False
    assert result["data_access"] == "none"
    assert result["alpha_allocation"] == {
        "score": 0.04, "anchor": 0.01, "total": 0.05,
    }
    assert result["dependence_method"] == "markov_pseudo_gap_bernstein"
    assert result["normalized_block_scores"] == [1.0, -1.0, 0.5, -1.0]
    assert result["denominators"] == {
        "planned_blocks": 4,
        "valid_blocks": 3,
        "failed_blocks": 1,
        "abstained_blocks": 0,
    }
    assert result["result_denominators"] == {
        "planned": 1, "valid": 1, "failed": 0, "abstained": 0,
    }
    assert result["planned_block_mean"] == pytest.approx(-0.125)
    assert result["concentration_penalty"] == pytest.approx(expected_radius)
    assert result["normalized_lower_bound"] == pytest.approx(
        -0.125 - expected_radius - 2 * 0.03
    )


def test_all_failed_markov_panel_abstains_with_two_denominator_levels():
    result = conditional_block_risk_markov_lcb(
        [np.nan, np.nan],
        valid_blocks=np.array([False, False]),
        **calibration(),
    )

    assert result["status"] == "ABSTAIN_NO_VALID_BLOCKS"
    assert result["normalized_lower_bound"] is None
    assert result["denominators"] == {
        "planned_blocks": 2,
        "valid_blocks": 0,
        "failed_blocks": 2,
        "abstained_blocks": 0,
    }
    assert result["result_denominators"] == {
        "planned": 1, "valid": 0, "failed": 0, "abstained": 1,
    }
    assert result["physical_score"] is None


@pytest.mark.parametrize("kwargs", [
    {"gamma_ps_lower": 0.0},
    {"gamma_ps_lower": True},
    {"gamma_ps_lower": 1e-320},
    {"family": 0},
    {"relative_anchor_bound_B_over_R": -0.1},
    {"alpha_anchor": 0.02},
])
def test_invalid_markov_bound_inputs_fail_closed(kwargs):
    args = calibration()
    args.update(kwargs)
    with pytest.raises(ValueError):
        conditional_block_risk_markov_lcb(
            [1.0, -1.0], valid_blocks=np.array([True, True]), **args,
        )


def test_non_boolean_masks_fail_closed():
    with pytest.raises(ValueError, match="booleans"):
        conditional_block_risk_markov_lcb(
            [1.0, -1.0], valid_blocks=np.array([1, 0]), **calibration(),
        )


def test_unrepresentably_large_gap_bound_fails_closed():
    with pytest.raises(ValueError, match="gamma_ps_lower"):
        conditional_block_risk_markov_lcb(
            [1.0, -1.0],
            valid_blocks=np.array([True, True]),
            **{**calibration(), "gamma_ps_lower": 10**10000},
        )


def test_markov_radius_is_finite_for_useful_settings():
    radius = markov_gap_radius(
        blocks=20, gamma_ps_lower=1.0, family=2, alpha_s=0.05,
    )
    assert math.isfinite(radius)
    assert radius > 1.0
