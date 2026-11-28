from __future__ import annotations

import numpy as np

from tasks.wilson_loop import f_lane_pivot_chart_exact_zero_screen as screen
from tasks.wilson_loop import f_lane_pivot_chart_exact_zero_multireplicate_screen as repeats
from tasks.wilson_loop import f_lane_three_static_pivot_chart as pivot
from tasks.wilson_loop import f_lane_three_static_two_vacuum_candidate as current


def test_exact_zero_panel_is_reproducible_and_hermitian():
    first, first_protocol = screen._generate_matrices()
    second, second_protocol = screen._generate_matrices()

    assert first.shape == (96, 2, 2, 5, 3, 3)
    assert first_protocol == second_protocol
    np.testing.assert_array_equal(first, second)
    np.testing.assert_allclose(first, first.conj().swapaxes(-1, -2), atol=1e-14)
    assert first_protocol["exact_zero_transition"]["operator_0_overlap"] == [0.0, 0.0]


def test_pivot_encodes_exact_zero_while_fixed_chart_hits_lower_bound():
    static, overlaps, epsilon = screen._truth()
    fixed, floor_indices = screen._fixed_encode(epsilon, static, overlaps)
    pivot_parameters, pivot_map = pivot.encode_components(epsilon, static, overlaps)

    decoded_fixed = current._decode(fixed)[2]
    decoded_pivot = pivot._decode(pivot_parameters, pivot_map)[2]
    target = screen.ZERO_TRANSITION

    assert len(floor_indices) == 1
    assert fixed[floor_indices[0]] == screen.FIXED_LOG_AMPLITUDE_FLOOR
    assert abs(decoded_fixed[target][0]) == np.exp(screen.FIXED_LOG_AMPLITUDE_FLOOR)
    assert decoded_pivot[target][0] == 0.0j
    assert int(pivot_map[target]) in (1, 2)

    expected_outer = np.einsum("...i,...j->...ij", overlaps, overlaps.conj())
    fixed_outer = np.einsum("...i,...j->...ij", decoded_fixed, decoded_fixed.conj())
    pivot_outer = np.einsum("...i,...j->...ij", decoded_pivot, decoded_pivot.conj())
    assert np.max(np.abs(pivot_outer - expected_outer)) < 1e-14
    assert np.max(np.abs(fixed_outer - expected_outer)) > 0.0


def test_multireplicate_noise_levels_scale_the_same_seeded_innovations():
    base, _ = screen._generate_matrices(seed=202611281129)
    means = repeats._mean_matrices()
    low = repeats._noise_scaled_panel(202611281129, 0.0003, base, means)
    high = repeats._noise_scaled_panel(202611281129, 0.01, base, means)

    np.testing.assert_allclose(
        high - means[None, ...],
        (low - means[None, ...]) * (0.01 / 0.0003),
        rtol=2e-13, atol=2e-15,
    )
