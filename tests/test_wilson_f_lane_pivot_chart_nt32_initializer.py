from __future__ import annotations

import csv

import numpy as np

from tasks.wilson_loop import f_lane_pivot_chart_nt32_initializer_screen as screen
from tasks.wilson_loop import f_lane_pivot_chart_fit_comparison as fit_comparison
from tasks.wilson_loop import f_lane_two_sector_fit_candidate as two_state


def _initializer_components():
    static = [np.asarray([0.2, 0.5, 0.8]), np.asarray([0.25, 0.55, 0.9])]
    overlaps = []
    for radius_index in range(len(two_state.R_VALUES)):
        values = np.asarray([
            [0.35 + 0j, 0.08 + 0.01j, -0.04 + 0.02j],
            [0.28 + 0j, 0.12 - 0.01j, 0.06 + 0.01j],
            [0.31 + 0j, 0.10 + 0.02j, -0.08 + 0.01j],
        ], dtype=np.complex128)
        if radius_index == 0:
            values[2] = [1e-8 + 0j, 0.70 + 0.10j, -0.20 + 0.05j]
        overlaps.append(values)
    return static, overlaps


def test_nt32_block_extractor_ignores_nt16_data():
    matrices = np.zeros(
        (4, len(two_state.NT_VALUES), len(two_state.R_VALUES),
         len(two_state.T_VALUES), 3, 3), dtype=np.complex128,
    )
    nt16 = two_state.NT_VALUES.index(16)
    nt32 = two_state.NT_VALUES.index(32)
    for block in range(matrices.shape[0]):
        for radius in range(len(two_state.R_VALUES)):
            for time_index in range(len(two_state.T_VALUES)):
                matrices[block, nt32, radius, time_index] = (
                    block + radius + time_index + 1
                ) * np.eye(3)
    altered = matrices.copy()
    altered[:, nt16] = 1e6 * np.eye(3)

    for radius in range(len(two_state.R_VALUES)):
        first = screen._nt32_block_vectors(matrices, radius)
        second = screen._nt32_block_vectors(altered, radius)
        np.testing.assert_array_equal(first, second)
        assert first.shape == (4, 9 * len(two_state.T_VALUES))


def test_pivot_reencoding_preserves_initializer_start_when_fixed_chart_is_out_of_bounds():
    static, overlaps = _initializer_components()
    fixed, pivoted, pivot_map, model_difference = screen._paired_chart_starts(
        static, overlaps, epsilon=0.30, excited_scale=0.35,
    )
    lower, upper = fit_comparison._bounds()

    assert np.max(np.abs(
        screen.current._model_vectors(fixed)
        - screen.pivot.model_vectors(pivoted, pivot_map)
    )) < 1e-13
    assert model_difference < 1e-13
    assert np.any(fixed < lower)  # target operator-0 log amplitude is below -12
    assert np.all(pivoted >= lower)
    assert np.all(pivoted <= upper)
    assert pivot_map[0, 0, 2] in (1, 2)


def test_result_csv_preserves_optional_fields_across_outcome_types(tmp_path):
    path = tmp_path / "mixed_outcomes.csv"
    rows = [
        {"status": "ABSTAIN", "nfev": 0},
        {"status": "VALID", "nfev": 8, "optimizer_success": True},
    ]
    screen._write_csv(path, rows)

    with path.open(newline="", encoding="utf-8") as stream:
        saved = list(csv.DictReader(stream))
    assert len(saved) == 2
    assert saved[0]["optimizer_success"] == ""
    assert saved[1]["optimizer_success"] == "True"
