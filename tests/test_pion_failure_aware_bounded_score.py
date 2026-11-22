"""Tests for analytic planned-failure handling; no physics data or MC."""
import math

import numpy as np
import pytest

from tasks.pion_projection.failure_aware_bounded_score import (
    lower_bound_with_failures,
    required_valid_mean,
)


def test_complete_case_matches_existing_bounded_bound():
    deltas = np.array([0.1, 0.2, 0.3, 0.4])
    result = lower_bound_with_failures(
        deltas, planned_blocks=4, range_width=1.0, family=2,
        alpha_s=0.05, anchor_bound=0.1,
    )
    expected = deltas.mean() - math.sqrt(2 * math.log(40) / 4) - 0.2
    assert result["status"] == "CONDITIONAL_BOUND"
    assert result["planned_blocks"] == 4
    assert result["valid_blocks"] == 4
    assert result["failed_blocks"] == 0
    assert result["lower_bound"] == pytest.approx(expected)


def test_worst_case_failure_keeps_planned_denominator():
    result = lower_bound_with_failures(
        [0.2, 0.4, 0.1], planned_blocks=4, range_width=1.0,
        family=1, alpha_s=0.05,
    )
    assert result["valid_blocks"] == 3
    assert result["failed_blocks"] == 1
    assert result["mean_improvement_all_planned"] == pytest.approx(-0.075)


def test_hard_abstention_returns_no_bound_if_any_block_is_missing():
    result = lower_bound_with_failures(
        [0.2, 0.4], planned_blocks=3, range_width=1.0,
        family=1, alpha_s=0.05, failure_policy="abstain",
    )
    assert result["status"] == "ABSTAIN_MISSING_BLOCKS"
    assert result["abstained"] is True
    assert result["planned_blocks"] == 3
    assert result["failed_blocks"] == 1
    assert result["lower_bound"] is None


def test_more_failures_or_anchor_bias_cannot_raise_the_bound():
    complete = lower_bound_with_failures(
        [0.5] * 8, planned_blocks=8, range_width=1.0,
        family=2, alpha_s=0.05,
    )["lower_bound"]
    one_failure = lower_bound_with_failures(
        [0.5] * 7, planned_blocks=8, range_width=1.0,
        family=2, alpha_s=0.05,
    )["lower_bound"]
    two_failures = lower_bound_with_failures(
        [0.5] * 6, planned_blocks=8, range_width=1.0,
        family=2, alpha_s=0.05,
    )["lower_bound"]
    anchor_bound = lower_bound_with_failures(
        [0.5] * 8, planned_blocks=8, range_width=1.0,
        family=2, alpha_s=0.05, anchor_bound=0.1,
    )["lower_bound"]
    assert complete > one_failure > two_failures
    assert anchor_bound < complete


def test_planning_boundary_increases_with_failures_and_other_penalties():
    zero = required_valid_mean(0.0, blocks=24, family=2, alpha_s=0.05)
    ten_percent = required_valid_mean(0.1, blocks=24, family=2, alpha_s=0.05)
    with_bias = required_valid_mean(
        0.1, blocks=24, family=2, alpha_s=0.05,
        relative_anchor_bound=0.05, normalized_threshold=0.1,
    )
    assert zero < ten_percent < with_bias


@pytest.mark.parametrize("kwargs", [
    {"planned_blocks": 0},
    {"range_width": 0.0},
    {"family": 0},
    {"alpha_s": 1.0},
    {"anchor_bound": -0.1},
])
def test_invalid_bound_inputs_reject(kwargs):
    args = dict(planned_blocks=2, range_width=1.0, family=1,
                alpha_s=0.05, anchor_bound=0.0)
    args.update(kwargs)
    with pytest.raises(ValueError):
        lower_bound_with_failures([0.2], **args)


@pytest.mark.parametrize("deltas, planned, policy", [
    ([0.0, 0.1], 1, "worst_case"),
    ([1.1], 1, "worst_case"),
    ([float("nan")], 1, "worst_case"),
    ([0.1], 2, "unknown"),
])
def test_invalid_observations_and_policy_reject(deltas, planned, policy):
    with pytest.raises(ValueError):
        lower_bound_with_failures(
            deltas, planned_blocks=planned, range_width=1.0,
            family=1, alpha_s=0.05, failure_policy=policy,
        )
