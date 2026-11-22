"""Synthetic only: no real split access and no production gate integration."""
import json

import numpy as np
import pytest

from tasks.wilson_loop.reference_gate_diagnostic import (
    _linear_q95, _summarize, window_gate_proposals,
)
from tasks.wilson_loop.statistics import potential


PARAMS = dict(windows=[[4, 5, 6], [4, 5, 6, 7], [5, 6, 7, 8]], t_values=[4, 5, 6, 7, 8])


def synthetic(curve=0):
    rng = np.random.default_rng(69)
    t = np.array(PARAMS['t_values'])
    noise = rng.uniform(-.02, .02, (10, 4, 5))
    data = np.exp(-np.array([.4, .5, .6, .7])[None, :, None] * t)
    data = data * (1 + np.concatenate([noise, -noise])) * np.exp(curve * (t - 6) ** 2)
    return np.repeat(data, 5, axis=0)


def test_loop_pipeline_pairing_reproducibility_and_json():
    result = window_gate_proposals(synthetic(), **PARAMS)
    assert result['scope'] == 'development_diagnostic_only'
    assert result['status'] == 'PROPOSAL_NOT_FROZEN'
    assert result['production_score'] is None
    assert result['A']['status'] == 'PROPOSAL_DIAGNOSTIC_PASS'
    assert result['B']['status'] == 'PROPOSAL_DIAGNOSTIC_PASS'
    assert len(result['A']['contrasts']) == 8
    assert len(result['B']['contrasts']) == 12
    assert result == window_gate_proposals(synthetic(), **PARAMS)
    index = np.asarray(result['bootstrap_index'])
    blocked = synthetic().reshape(20, 5, 4, 5).mean(axis=1)
    boot = blocked[index].mean(axis=1)
    vb = np.stack([potential(boot, w, PARAMS['t_values']) for w in PARAMS['windows']], axis=-1)
    delta = vb[:, :, [0, 2]] - vb[:, :, [1]]
    standardized = delta / delta.std(axis=0, ddof=1)
    expected = np.max(np.abs(standardized), axis=(1, 2))
    np.testing.assert_allclose(result['C']['uncentered']['draw_maxima'], expected)
    assert result['C']['uncentered']['q95'] == pytest.approx(np.quantile(expected, .95))
    json.dumps(result, allow_nan=False)
    assert window_gate_proposals(synthetic(.03), **PARAMS)['A']['status'] == 'REJECT_WINDOW_INSTABILITY'


def test_a_b_can_differ_with_shared_draw_correlations():
    # Both marginal contrasts vs nominal have SD=1; their *difference* has
    # small SD because they share nearly identical fluctuations.
    common = np.linspace(-1, 1, 100)
    residual = np.sin(np.arange(100)) * .01
    boot = np.stack([common, np.zeros(100), common + residual], axis=-1)[:, None, :]
    point = np.array([[.2, 0, -.2]])
    a, _ = _summarize(point, boot, [(0, 1), (2, 1)])
    b, _ = _summarize(point, boot, [(0, 1), (0, 2), (1, 2)])
    assert a['status'] == 'PROPOSAL_DIAGNOSTIC_PASS'
    assert b['status'] == 'REJECT_WINDOW_INSTABILITY'
    assert b['contrasts'][1]['paired_sd'] < .01


def test_c_can_differ_from_a_and_centers_before_joint_max():
    residual = np.array([-2., -1., 0., 1., 2.])
    boot = np.stack([residual + 2.5, np.zeros(5), -residual + 2.5], axis=-1)[:, None, :]
    a, vectors = _summarize(np.array([[2.5, 0, 2.5]]), boot, [(0, 1), (2, 1)])
    assert a['status'] == 'PROPOSAL_DIAGNOSTIC_PASS'
    u = np.max(np.abs(vectors), axis=1)
    c = np.max(np.abs(vectors - vectors.mean(axis=0)), axis=1)
    assert _linear_q95(u) > 2.5
    assert _linear_q95(c) < 2.5
    np.testing.assert_allclose(_linear_q95(u), np.quantile(u, .95))


@pytest.mark.parametrize('difference,decision', [(2.5, 'PROPOSAL_DIAGNOSTIC_PASS'),
                                                (2.50001, 'REJECT_WINDOW_INSTABILITY')])
def test_exact_boundary(difference, decision):
    boot = np.array([[[-1., 0]], [[0., 0]], [[1., 0]]])
    row, _ = _summarize(np.array([[difference, 0]]), boot, [(0, 1)])
    assert row['status'] == decision
    assert row['contrasts'][0]['paired_sd'] == 1


def test_zero_near_zero_and_invalid_draw_abstain():
    for scale in (0., 1e-16):
        boot = np.array([[[-1., 0]], [[0., 0]], [[1., 0]]]) * scale
        result, _ = _summarize(np.zeros((1, 2)), boot, [(0, 1)])
        assert result['status'] == 'ABSTAIN'
        assert result['contrasts'][0]['failure_reasons'] == ['ABSTAIN_DEGENERATE_SE']
    boot[1, 0, 0] = np.nan
    result, _ = _summarize(np.zeros((1, 2)), boot, [(0, 1)])
    assert result['contrasts'][0]['invalid_draw_indices'] == [1]
    assert result['contrasts'][0]['paired_sd'] is None


def test_nonpositive_bootstrap_mean_and_nonfinite_input_abstain():
    # Positive ensemble mean, but many resamples have a nonpositive mean.
    data = np.tile(np.exp(-.5 * np.arange(4, 9)), (15, 1, 1))
    data[:5] *= -1
    result = window_gate_proposals(data, bootstrap_samples=200, **PARAMS)
    assert result['comparison_status'] == 'ABSTAIN'
    assert any(r['invalid_draw_count'] for r in result['A']['contrasts'])
    assert any(r['nonpositive_mean_draw_indices'] for r in result['window_mean_diagnostics'])
    assert all(result[k]['status'] == 'ABSTAIN' for k in ('A', 'B', 'C'))
    data[0, 0, 0] = np.nan
    result = window_gate_proposals(data, bootstrap_samples=10, **PARAMS)
    assert result['input_failure_reasons'] == ['NONFINITE_INPUT_LOOPS']
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize('data,extra', [
    (np.ones((13, 1, 5)), {}),
    (np.ones((10, 1, 5)), {}),
    (np.ones((15, 1, 5), dtype=complex), {}),
    (np.ones((15, 1, 5)), {'nominal': 9}),
    (np.ones((15, 1, 5)), {'bootstrap_samples': 1}),
    (np.ones((15, 1, 5)), {'windows': [[4, 9], [4, 5]]}),
])
def test_schema_and_block_errors(data, extra):
    with pytest.raises(ValueError):
        window_gate_proposals(data, **(PARAMS | extra))
