import numpy as np
import pytest

from tasks.pion_projection.source_sink_hermiticity_diagnostic import relative_antihermitian_norm


def test_relative_antihermitian_norm_is_zero_for_hermitian_matrix():
    matrix = np.array([[2.0, 1.0 + 0.5j], [1.0 - 0.5j, 3.0]])
    assert relative_antihermitian_norm(matrix) == 0.0


def test_relative_antihermitian_norm_matches_max_norm_definition():
    matrix = np.array([[1.0, 0.0], [0.1j, 1.0]])
    assert relative_antihermitian_norm(matrix) == pytest.approx(0.1)


@pytest.mark.parametrize("matrix", [np.zeros((2, 2)), np.ones((2, 3)), np.array([[np.nan]])])
def test_relative_antihermitian_norm_rejects_invalid_normalization(matrix):
    with pytest.raises(ValueError):
        relative_antihermitian_norm(matrix)
