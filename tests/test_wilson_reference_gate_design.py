"""Synthetic algebra checks for PROPOSAL_NOT_FROZEN; no production gate wiring."""
import numpy as np
import pytest

from core.stats import bootstrap_indices
from tasks.wilson_loop.statistics import potential


def proposal_nominal_max(point, boot, nominal=1, threshold=2.5):
    """Test-local candidate A; not an executable production gate."""
    point = np.asarray(point, dtype=np.float64)
    boot = np.asarray(boot, dtype=np.float64)
    if point.ndim != 2 or boot.ndim != 3 or boot.shape[1:] != point.shape:
        raise ValueError('shape')
    if len(boot) < 2 or not 0 <= nominal < point.shape[1]:
        raise ValueError('bootstrap count or nominal')
    if not np.isfinite(point).all() or not np.isfinite(boot).all():
        raise ValueError('non-finite estimator')
    others = np.arange(point.shape[1]) != nominal
    delta = point[:, others] - point[:, [nominal]]
    draws = boot[:, :, others] - boot[:, :, [nominal]]
    se = draws.std(axis=0, ddof=1)
    scale = np.maximum(1.0, np.maximum(np.max(np.abs(boot[:, :, others]), axis=0),
                                     np.max(np.abs(boot[:, :, [nominal]]), axis=0)))
    scale = np.maximum(scale, np.maximum(np.abs(point[:, others]),
                                        np.abs(point[:, [nominal]])))
    floor = 64 * np.finfo(np.float64).eps * scale
    if np.any(se <= floor):
        raise ValueError('degenerate paired SE')
    z = delta / se
    maximum = np.max(np.abs(z))
    centered_max = np.max(np.abs((draws - draws.mean(axis=0)) / se), axis=(1, 2))
    return maximum <= threshold, z, se, centered_max


def arrays(value):
    # Three contrast draws have exactly sample SD=1; nominal noise is shared.
    common = np.array([-10.0, 0.0, 10.0])
    residual = np.array([-1.0, 0.0, 1.0])
    boot = np.zeros((3, 4, 3))
    boot[:] = common[:, None, None]
    boot[:, :, 0] += residual[:, None]
    boot[:, :, 2] -= residual[:, None]
    point = np.zeros((4, 3))
    point[3, 2] = value
    return point, boot


@pytest.mark.parametrize('value,passed', [(0.2, True), (2.5, True), (2.5001, False), (-3, False)])
def test_point_max_worst_r_and_boundary(value, passed):
    result, z, se, _ = proposal_nominal_max(*arrays(value))
    assert bool(result) is passed
    assert z.shape == (4, 2)  # excludes structural nominal; covers all four R.
    np.testing.assert_array_equal(se, 1)
    assert np.max(np.abs(z)) == abs(value)


def test_pairing_changes_denominator_and_joint_max_keeps_draws():
    point, boot = arrays(3)
    passed, _, paired_se, joint_max = proposal_nominal_max(point, boot)
    assert not passed
    naive_se = np.sqrt(boot[:, :, 0].std(axis=0, ddof=1) ** 2 +
                       boot[:, :, 1].std(axis=0, ddof=1) ** 2)
    assert (naive_se > 10 * paired_se[:, 0]).all()
    np.testing.assert_array_equal(joint_max, [1, 0, 1])
    # Cross-coordinate opposite excursions are two large maxima, not a canceling mean.
    assert joint_max.mean() == pytest.approx(2 / 3)


@pytest.mark.parametrize('scale', [0.0, 1e-16])
def test_degenerate_se_abstains_even_when_point_difference_zero(scale):
    point, boot = arrays(0)
    boot *= scale
    with pytest.raises(ValueError, match='degenerate'):
        proposal_nominal_max(point, boot)


def test_nonfinite_draw_not_silently_deleted():
    point, boot = arrays(0)
    boot[1, 2, 0] = np.nan
    with pytest.raises(ValueError, match='non-finite'):
        proposal_nominal_max(point, boot)


def test_synthetic_block_loops_share_one_index_matrix():
    rng = np.random.default_rng(2026112021)
    t = np.array([4, 5, 6, 7, 8])
    windows = [[4, 5, 6], [4, 5, 6, 7], [5, 6, 7, 8]]
    # Pair each block with its opposite perturbation: the sample mean is exactly
    # exp(-Et), while bootstrap draws retain T-dependent shape fluctuations.
    noise = rng.uniform(-0.02, 0.02, size=(10, 4, 5))
    blocks = np.exp(-np.arange(0.4, 0.8, 0.1)[None, :, None] * t)
    blocks = blocks * (1 + np.concatenate([noise, -noise], axis=0))
    index = bootstrap_indices(20, 5000, 2026112021)
    np.testing.assert_array_equal(index, bootstrap_indices(20, 5000, 2026112021))
    mean = blocks.mean(axis=0)
    boot_mean = blocks[index].mean(axis=1)
    assert (boot_mean > 0).all()
    point = np.stack([potential(mean, w, t) for w in windows], axis=-1)
    boot = np.stack([potential(boot_mean, w, t) for w in windows], axis=-1)
    passed, z, _, maxima = proposal_nominal_max(point, boot)
    assert passed
    assert np.max(np.abs(z)) < 1e-8
    assert maxima.shape == (5000,)
    # A deterministic curvature generates a visible window drift with low noise.
    curve = np.exp(0.03 * (t - 6) ** 2)
    bent_point = np.stack([potential(mean * curve, w, t) for w in windows], axis=-1)
    bent_boot = np.stack([potential(boot_mean * curve, w, t) for w in windows], axis=-1)
    assert not proposal_nominal_max(bent_point, bent_boot)[0]
