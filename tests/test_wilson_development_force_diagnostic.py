import numpy as np
import pytest

from tasks.wilson_loop.development_force_diagnostic import (
    _creutz_force,
    _window_slope_force,
    force_diagnostic,
)


def _protocol():
    return {
        'kernels': [{'name': name} for name in ('identity', 'candidate')],
        'r_values': [1, 2, 3, 4],
        't_values': [4, 5, 6, 7, 8],
        'reference_windows': [[4, 5, 6], [4, 5, 6, 7], [5, 6, 7, 8]],
        'block_length': 2,
    }


def _loops_for_potential(potential, t_values):
    r = np.arange(1, 5, dtype=float)
    t = np.asarray(t_values, dtype=float)
    return np.exp(-potential(r[:, None]) * t[None, :])


def test_window_force_and_creutz_cancel_common_additive_potential_offset():
    p = _protocol()
    t = p['t_values']
    base = 0.07 * np.arange(1, 5, dtype=float) + 0.3
    shifted = base + 0.41
    loops = np.stack([
        _loops_for_potential(lambda r: 0.07 * r + 0.3, t),
        _loops_for_potential(lambda r: 0.07 * r + 0.71, t),
    ])

    window_force = _window_slope_force(loops, p)
    creutz_force = _creutz_force(loops)

    np.testing.assert_allclose(window_force[0], 0.07, atol=1e-12)
    np.testing.assert_allclose(window_force[1], 0.07, atol=1e-12)
    np.testing.assert_allclose(creutz_force[0], 0.07, atol=1e-12)
    np.testing.assert_allclose(creutz_force[1], 0.07, atol=1e-12)
    np.testing.assert_allclose(shifted - base, 0.41)


def test_r_dependent_potential_bias_survives_force_difference():
    p = _protocol()
    loops = np.stack([
        _loops_for_potential(lambda r: 0.07 * r, p['t_values']),
        _loops_for_potential(lambda r: 0.07 * r + 0.01 * r**2, p['t_values']),
    ])
    force = _window_slope_force(loops, p)
    creutz = _creutz_force(loops)
    expected = 0.07 + 0.01 * (2 * np.arange(1, 4) + 1)
    np.testing.assert_allclose(force[1, 0] - force[0, 0], expected - 0.07, atol=1e-12)
    np.testing.assert_allclose(creutz[1, 0] - creutz[0, 0], expected - 0.07, atol=1e-12)


def test_force_diagnostic_uses_shared_draws_and_reports_invalid_draw_denominator():
    p = _protocol()
    ncfg = 12
    r = np.arange(1, 5, dtype=float)
    t = np.asarray(p['t_values'], dtype=float)
    identity = np.exp(-(0.1 * r[:, None] + 0.2) * t[None, :])
    candidate = np.exp(-(0.1 * r[:, None] + 0.61) * t[None, :])
    loops = np.repeat(np.stack([identity, candidate])[None, ...], ncfg, axis=0)

    result = force_diagnostic(loops, p, bootstrap_samples=30, seed=88)

    assert result['block_count'] == 6
    assert result['valid_draws'] == 30
    assert result['invalid_draws'] == 0
    assert result['bootstrap_index'].shape == (30, 6)
    assert len(result['window_rows']) == 2 * 3 * 3
    assert len(result['creutz_rows']) == 2 * 4 * 3
    for row in result['window_rows'] + result['creutz_rows']:
        assert row['valid_draws'] == 30
        assert row['invalid_draws'] == 0
        assert row['candidate_minus_identity_point'] == pytest.approx(0.0, abs=1e-12)
        assert row['paired_delta_ci95_low_pointwise'] == pytest.approx(0.0, abs=1e-12)
        assert row['paired_delta_ci95_high_pointwise'] == pytest.approx(0.0, abs=1e-12)


def test_force_diagnostic_rejects_nonpositive_point_means():
    p = _protocol()
    loops = np.ones((8, 2, 4, 5))
    loops[0, 0, 0, 0] = -20
    with pytest.raises(ValueError, match='point loop means'):
        force_diagnostic(loops, p, bootstrap_samples=10)
