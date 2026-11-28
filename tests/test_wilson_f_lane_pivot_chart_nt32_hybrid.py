from __future__ import annotations

import numpy as np

from tasks.wilson_loop import f_lane_pivot_chart_fit_comparison as fit_comparison
from tasks.wilson_loop import f_lane_pivot_chart_nt32_hybrid_screen as hybrid
from tasks.wilson_loop import f_lane_three_static_two_vacuum_candidate as current
from tasks.wilson_loop import f_lane_two_sector_fit_candidate as two_state


def _fixed_start(target_operator0: float) -> np.ndarray:
    static = [np.asarray([0.2, 0.5, 0.8]), np.asarray([0.25, 0.55, 0.9])]
    overlaps = []
    for radius_index in range(len(two_state.R_VALUES)):
        values = np.asarray([
            [0.40 + 0j, 0.08 + 0.01j, -0.04 + 0.02j],
            [0.28 + 0j, 0.12 - 0.01j, 0.06 + 0.01j],
            [0.31 + 0j, 0.10 + 0.02j, -0.08 + 0.01j],
        ], dtype=np.complex128)
        if radius_index == 0:
            values[2] = [target_operator0 + 0j, 0.70 + 0.10j, -0.20 + 0.05j]
        overlaps.append(values)
    return current._initial_parameters(static, overlaps, epsilon=0.3, excited_scale=0.35)


def test_hybrid_chart_switches_only_transitions_outside_fixed_op0_domain():
    fixed = _fixed_start(1e-8)
    hybrid_start, pivot_map, details = hybrid.encode_hybrid_chart(fixed)
    lower, upper = fit_comparison._bounds()

    assert np.array_equal(pivot_map[0, 0], [0, 0, 1])
    assert np.array_equal(pivot_map[0, 1], [0, 0, 1])
    assert details["operator0_pivot_count"] == 10
    assert details["alternate_pivot_count"] == 2
    assert details["model_max_abs_difference"] < 1e-13
    assert np.all(hybrid_start >= lower)
    assert np.all(hybrid_start <= upper)
    np.testing.assert_allclose(
        current._model_vectors(fixed),
        hybrid.pivot.model_vectors(hybrid_start, pivot_map),
        rtol=0.0, atol=1e-13,
    )


def test_hybrid_keeps_fixed_op0_when_its_log_amplitude_is_on_valid_side_of_bound():
    # The excited-vacuum amplitude is scaled by 0.35, so use a 4x margin to
    # keep both vacuum-state copies inside the same fixed-chart domain.
    fixed = _fixed_start(4.0 * hybrid.AMPLITUDE_FLOOR)
    _, pivot_map, details = hybrid.encode_hybrid_chart(fixed)

    assert pivot_map[0, 0, 2] == 0
    assert pivot_map[0, 1, 2] == 0
    assert details["alternate_pivot_count"] == 0
