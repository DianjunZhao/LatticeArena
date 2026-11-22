import math

import pytest

from tasks.pion_projection.bounded_score_planning import (
    minimum_blocks,
    required_normalized_effect,
)


def test_statistical_penalty_decreases_with_blocks_and_increases_with_family():
    values = [required_normalized_effect(n, 1, 0.05, 0.0) for n in (12, 24, 100, 400)]
    assert values[0] > values[1] > values[2] > values[3]
    assert required_normalized_effect(100, 4, 0.05, 0.0) > values[2]


def test_anchor_penalty_is_an_exact_linear_floor():
    base = required_normalized_effect(100, 2, 0.04, 0.0)
    for beta in (0.001, 0.05, 0.25):
        assert required_normalized_effect(100, 2, 0.04, beta) == pytest.approx(base + 2 * beta)


def test_minimum_blocks_uses_strict_crossing_and_anchor_floor():
    f, alpha, beta = 2, 0.04, 0.02
    signal = 0.30
    n = minimum_blocks(signal, f, alpha, beta)
    assert n is not None
    assert required_normalized_effect(n, f, alpha, beta) < signal
    assert required_normalized_effect(n - 1, f, alpha, beta) >= signal
    assert minimum_blocks(0.04, f, alpha, beta) is None


@pytest.mark.parametrize("args", [
    (0, 1, 0.05, 0.0), (10, 0, 0.05, 0.0), (10, 1, 1.0, 0.0),
    (10, 1, 0.05, -0.1),
])
def test_invalid_planning_inputs_are_rejected(args):
    with pytest.raises(ValueError):
        required_normalized_effect(*args)
