import numpy as np
import pytest

from tasks.pion_projection.two_state_multistart_diagnostic import fit_two_state_multistart


class _MomentModel:
    """Well-conditioned enough moment design for deterministic optimizer tests."""

    def __init__(self, order=6):
        self.p = {'mass_bounds': [0.1, 2.0]}
        self.inv = np.eye(order)
        self.samples = np.zeros((8, order))

    def design(self, mass0, mass1):
        return np.asarray([[mass0 ** power, mass1 ** power]
                           for power in range(self.samples.shape[1])], dtype=float)


def _mean(model, mass0, mass1, amp=(0.7, 0.3)):
    return model.design(mass0, mass1) @ np.asarray(amp, dtype=float)


def test_multistart_recovers_known_separated_two_state_design():
    model = _MomentModel()
    mean = _mean(model, 0.5, 1.2)
    starts = np.asarray([
        [0.4, 0.8], [0.8, 0.4], [0.2, 1.2], [0.5, 0.0], [0.9, 0.2], [0.3, 0.1],
    ])
    rows = fit_two_state_multistart(model, mean, starts)
    best = min(rows, key=lambda row: row['final_cost'])
    assert best['solver_success']
    assert best['final_cost'] < 1e-10
    assert abs(best['final_mass0'] - 0.5) < 1e-4
    assert abs(best['final_gap'] - 0.7) < 1e-4
    assert all(row['finite_endpoint'] for row in rows)
    assert all(row['constraint_violation'] < 1e-7 for row in rows)


def test_multistart_records_rank_deficient_zero_gap_boundary():
    model = _MomentModel()
    mean = _mean(model, 0.9, 0.9, amp=(1.0, 0.0))
    row = fit_two_state_multistart(model, mean, [[0.9, 0.0]])[0]
    assert row['finite_endpoint']
    assert row['solver_success']
    assert row['final_cost'] < 1e-12
    assert row['final_gap'] == pytest.approx(0.0, abs=1e-8)
    assert 'gap_zero' in row['active_boundaries']
    assert row['amplitude_rank'] == 1
    assert np.isinf(row['amplitude_condition'])


@pytest.mark.parametrize(
    ('truth', 'start', 'boundary', 'expected_mass0', 'expected_gap'),
    [
        ((0.1, 1.0), (0.2, 0.6), 'mass0_lower', 0.1, 0.9),
        ((0.8, 2.0), (0.7, 1.0), 'mass1_upper', 0.8, 1.2),
    ],
)
def test_multistart_recovers_active_mass_boundaries(truth, start, boundary, expected_mass0, expected_gap):
    model = _MomentModel()
    row = min(
        fit_two_state_multistart(model, _mean(model, *truth), [start]),
        key=lambda item: item['final_cost'],
    )
    assert row['solver_success']
    assert row['final_cost'] < 1e-10
    assert row['final_mass0'] == pytest.approx(expected_mass0, abs=2e-4)
    assert row['final_gap'] == pytest.approx(expected_gap, abs=2e-4)
    assert boundary in row['active_boundaries']


@pytest.mark.parametrize(
    'starts',
    [[], [[0.2]], [[0.2, 0.1], [float('nan'), 0.2]], [[0.2, -0.1]], [[1.9, 0.2]]],
)
def test_multistart_rejects_invalid_start_sets(starts):
    with pytest.raises(ValueError):
        fit_two_state_multistart(_MomentModel(), np.ones(6), starts)
