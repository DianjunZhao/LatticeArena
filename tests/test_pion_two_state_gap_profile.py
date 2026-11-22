import numpy as np
import pytest

from tasks.pion_projection.two_state_gap_profile import profile_gap_curve


class _MomentModel:
    """Small deterministic design used to test the profiling algebra only."""

    def __init__(self, truth=(0.5, 1.2)):
        self.p = {'mass_bounds': [0.1, 2.0]}
        self.inv = np.eye(3)
        self.samples = np.zeros((8, 3))
        self.truth = truth

    def design(self, m0, m1):
        return np.array([[1., 1.], [m0, m1], [m0 * m0, m1 * m1]])


def test_profile_gap_curve_handles_exact_one_state_boundary_with_svd():
    model = _MomentModel()
    mean = model.design(0.9, 0.9) @ np.array([0.7, 0.3])
    result = profile_gap_curve(model, mean, [0.0], mass_step=0.1)
    assert result['profile_cost'][0] < 1e-12
    assert np.isfinite(result['profile_mass0'][0])
    assert result['gaps'] == [0.0]
    assert 'SVD' in result['amplitude_solver']


def test_profile_gap_curve_recovers_separated_synthetic_design_gap():
    model = _MomentModel()
    expected_gap = model.truth[1] - model.truth[0]
    mean = model.design(*model.truth) @ np.array([0.7, 0.3])
    gaps = np.arange(0.0, 1.001, 0.02)
    result = profile_gap_curve(model, mean, gaps, mass_step=0.01)
    refined = result['refined_minimum']
    assert abs(refined['gap'] - expected_gap) <= 0.01
    assert refined['cost'] < 1e-10
    assert refined['cost'] <= min(result['profile_cost'])


@pytest.mark.parametrize('gaps', [[-0.01], [1.9], [float('nan')], []])
def test_profile_gap_curve_rejects_invalid_gap_domains(gaps):
    with pytest.raises(ValueError):
        profile_gap_curve(_MomentModel(), np.array([1., 0.9, 0.5]), gaps)
