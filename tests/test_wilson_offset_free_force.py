"""Synthetic controls for the candidate offset-free Wilson-force estimand."""

import numpy as np
import pytest

from tasks.wilson_loop.offset_free_force_diagnostic import (
    DELTA_COMMON,
    DELTA_R,
    analyze,
    apply_common_potential_shift,
    synthetic_loops,
)


def test_common_potential_offset_cancels_in_force_with_shared_bootstrap():
    summary, _, boot_v, boot_f = analyze(seed=2026112121, n_boot=64)

    assert summary['scope'] == 'synthetic_method_diagnostic_only'
    assert summary['physical_score'] is None
    assert summary['production_gate_modified'] is False
    assert summary['max_abs_common_potential_shift_error'] < 1e-13
    assert summary['max_abs_common_force_shift'] < 1e-13
    np.testing.assert_allclose(
        boot_v['common_offset'] - boot_v['baseline'],
        DELTA_COMMON,
        rtol=0,
        atol=1e-13,
    )
    np.testing.assert_allclose(
        boot_f['common_offset'] - boot_f['baseline'], 0.0, rtol=0, atol=1e-13
    )


def test_r_dependent_offset_is_visible_as_expected_force_shift():
    summary, _, _, boot_f = analyze(seed=2026112121, n_boot=64)
    expected = np.diff(DELTA_R)

    np.testing.assert_allclose(summary['r_dependent_force_shift'], expected, atol=1e-13)
    np.testing.assert_allclose(
        boot_f['r_dependent_offset'] - boot_f['baseline'],
        np.broadcast_to(expected, boot_f['baseline'].shape),
        rtol=0,
        atol=1e-13,
    )


def test_shift_rejects_invalid_loop_arrays():
    loops = synthetic_loops()
    with pytest.raises(ValueError, match='positive and finite'):
        apply_common_potential_shift(loops * 0.0, (4, 5, 6, 7, 8), 0.03)
