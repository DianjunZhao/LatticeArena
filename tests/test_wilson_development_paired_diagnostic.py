import numpy as np

from tasks.wilson_loop.development_paired_diagnostic import paired_risk_diagnostic


def _protocol():
    return {
        'kernels': [{'name': name} for name in ('identity', 'ape', 'stout')],
        'r_values': [1, 2],
        't_values': [1, 2, 3],
        'block_length': 2,
        'reference_windows': [[1, 2], [2, 3], [1, 3]],
    }


def test_paired_development_risk_is_finite_and_retains_shared_draws():
    rng = np.random.default_rng(54)
    ncfg = 12
    signal = np.exp(-0.4 * np.outer(np.array([1.0, 2.0]), np.array([1.0, 2.0, 3.0])))
    loops = np.empty((ncfg, 3, 2, 3))
    for cfg in range(ncfg):
        noise = rng.normal(0, 0.025, size=(3, 2, 3))
        loops[cfg] = signal[None, :, :] * np.exp(noise)

    result = paired_risk_diagnostic(
        loops, _protocol(), outer_samples=30, inner_samples=40, seed=181)

    assert result['blocks'] == ncfg // 2
    assert result['ratios'].shape == (30, 3, 2)
    assert np.isfinite(result['ratios']).all()
    assert len(result['summary_rows']) == 3 * 2
    assert all(row['valid_outer_draws'] == 30 for row in result['summary_rows'])
    assert len(result['inner_index']) == 40
    assert len(result['outer_index']) == 30


def test_paired_development_rejects_inadequate_inner_bootstrap_count():
    with np.testing.assert_raises_regex(ValueError, 'at least two'):
        paired_risk_diagnostic(np.ones((12, 3, 2, 3)), _protocol(), inner_samples=1)
