import numpy as np

from tasks.wilson_loop.f_lane_finite_time_ground_force_nonidentifiability import (
    HIDDEN_AMPLITUDE,
    _build_witness,
)


def test_positive_spectra_match_all_frozen_matrix_points_but_change_force():
    result = _build_witness()
    assert result["base_matrices"].shape == (2, 5, 3, 3)
    assert np.all(result["alt_weights_by_radius"] > 0.0)
    assert result["minimum_base_weight_after_adjustment"] > 0.0
    assert result["max_matrix_relative_residual"] < 1e-14
    assert result["base_ground_force"] == 0.0
    assert np.isclose(result["alt_ground_force"], 0.05, rtol=0.0, atol=1e-14)
    assert abs(result["finite_time_force"]) < 1e-14
    assert HIDDEN_AMPLITUDE > 0.0


def test_all_constructed_correlator_matrices_are_hermitian_positive_definite():
    result = _build_witness()
    for collection in (result["base_matrices"], result["alt_matrices"]):
        for matrix in collection.reshape(-1, 3, 3):
            assert np.allclose(matrix, matrix.conj().T, rtol=0.0, atol=0.0)
            assert np.linalg.eigvalsh(matrix)[0] > 0.0


def test_all_measured_effective_energies_are_indistinguishable():
    result = _build_witness()
    assert np.allclose(
        result["base_effective_energies"],
        result["alt_effective_energies"],
        rtol=1e-14,
        atol=1e-14,
    )
