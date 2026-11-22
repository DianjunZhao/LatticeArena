import numpy as np
import pytest

from tasks.pion_projection.common import protocol
from tasks.pion_projection.reference_twostate import TwoStateFit
from tasks.pion_projection.statistics import blocks, shape


def _fit():
    p = protocol()
    rng = np.random.default_rng(6120)
    times = np.arange(p['geometry'][3])
    data = np.empty((40, len(p['powers']), len(times)), dtype=float)
    for channel in range(len(p['powers'])):
        a0 = 0.8 + 0.07 * channel
        a1 = -0.2 + 0.025 * channel
        mean = a0 * shape(0.82, times) + a1 * shape(1.43, times)
        shared = rng.normal(0.0, 0.003, size=(40, 1))
        noise = rng.normal(0.0, 0.001, size=(40, len(times)))
        data[:, channel] = mean[None, :] * (1.0 + shared) + noise
    data_blocks = blocks(data, 5)
    return TwoStateFit(data_blocks, p, [4, 5, 6, 7, 8])


def test_whitened_svd_matches_normal_equations_at_well_conditioned_point():
    fit = _fit()
    mean = fit.samples.mean(axis=0)
    result = fit.linear_fit(0.82, 1.43, mean)

    design = fit.design(0.82, 1.43)
    gram = design.T @ fit.inv @ design
    rhs = design.T @ fit.inv @ mean
    old_amplitudes = np.linalg.solve(gram, rhs)
    old_residual = mean - design @ old_amplitudes
    old_cost = old_residual @ fit.inv @ old_residual

    np.testing.assert_allclose(result['amplitudes'], old_amplitudes, rtol=2e-8, atol=2e-10)
    assert result['cost'] == pytest.approx(old_cost, rel=2e-9, abs=2e-11)
    assert result['fit_status'] == 'full_rank'
    assert result['rank'] == result['n_amplitudes']
    assert result['condition'] == pytest.approx(result['design_condition'] ** 2, rel=1e-12)


def test_equal_mass_is_explicitly_classified_as_nested_one_state_boundary():
    fit = _fit()
    result = fit.linear_fit(0.9, 0.9, fit.samples.mean(axis=0))

    assert result['fit_status'] == 'nested_m1_boundary'
    assert result['rank'] == len(fit.p['reference_basis'])
    assert result['rank'] < result['n_amplitudes']
    assert np.isinf(result['condition'])
    assert np.isfinite(result['cost'])
    assert np.isfinite(result['amplitudes']).all()


def test_near_degenerate_two_state_solution_stays_finite_and_reports_condition():
    fit = _fit()
    result = fit.linear_fit(0.9, 0.900001, fit.samples.mean(axis=0))

    assert result['fit_status'] in {'full_rank', 'rank_deficient'}
    assert np.isfinite(result['cost'])
    assert np.isfinite(result['amplitudes']).all()
    assert result['condition'] > 1e5 or np.isinf(result['condition'])


@pytest.mark.parametrize('mean', [np.array([np.nan]), np.array([np.inf])])
def test_nonfinite_or_wrong_shape_mean_is_rejected(mean):
    fit = _fit()
    with pytest.raises(ValueError, match='mean must be finite'):
        fit.linear_fit(0.8, 1.4, mean)


def test_fit_full_exposes_rank_and_condition_definitions():
    fit = _fit()
    result = fit.fit_full(fit.samples.mean(axis=0))

    assert result['fit_status'] == 'full_rank'
    assert result['amplitude_rank'] == result['amplitude_count']
    assert result['condition'] == pytest.approx(result['design_condition'] ** 2, rel=1e-12)


def test_multistart_mass_executor_retains_finite_endpoints_and_candidate_rows():
    fit = _fit()
    starts = [[0.78, 0.62], [0.90, 0.40], [1.10, 0.20], [0.70, 1.10], [0.82, 0.0]]
    result = fit.fit_full_multistart(fit.samples.mean(axis=0), starts, maxiter=500)

    assert result['classification'] == 'diagnostic_only'
    assert len(result['rows']) == len(starts)
    assert result['best_found'] is not None
    assert result['best_found']['solver_success']
    assert result['best_found']['endpoint_status'] in {
        'converged_full_rank', 'converged_mass_boundary', 'near_nested_m1_boundary',
    }
    assert np.isfinite([result['best_found']['mass0'], result['best_found']['mass1'],
                        result['best_found']['cost']]).all()
    assert all(row['finite_endpoint'] and row['feasible_endpoint'] for row in result['rows'])
    assert all('solver_message' in row and 'constraint_violation' in row for row in result['rows'])


def test_multistart_retains_failed_nested_boundary_endpoint(monkeypatch):
    from types import SimpleNamespace
    import tasks.pion_projection.reference_twostate as reference_twostate

    fit = _fit()

    def failed_minimize(objective, x0, **kwargs):
        return SimpleNamespace(
            x=np.asarray(x0), success=False, status=9, message='iteration limit', nfev=1, nit=1,
        )

    monkeypatch.setattr(reference_twostate, 'minimize', failed_minimize)
    result = fit.fit_full_multistart(fit.samples.mean(axis=0), [[0.9, 0.0]])
    row = result['rows'][0]

    assert row['solver_success'] is False
    assert row['finite_endpoint'] and row['feasible_endpoint']
    assert row['endpoint_status'] == 'nested_m1_boundary'
    assert result['status'] == 'best_found_at_nonconverged_nested_m1_boundary'
    assert result['best_found'] == row


def test_multistart_retains_optimizer_exception_as_failed_receipt(monkeypatch):
    import tasks.pion_projection.reference_twostate as reference_twostate

    fit = _fit()

    def failed_minimize(*args, **kwargs):
        raise RuntimeError('controlled solver failure')

    monkeypatch.setattr(reference_twostate, 'minimize', failed_minimize)
    result = fit.fit_full_multistart(fit.samples.mean(axis=0), [[0.9, 0.0]])
    row = result['rows'][0]

    assert row['finite_endpoint'] and row['feasible_endpoint']
    assert row['solver_success'] is False
    assert row['optimizer_exception'] == 'RuntimeError: controlled solver failure'
    assert row['nfev'] == 0 and row['nit'] == 0
    assert result['status'] == 'best_found_at_nonconverged_nested_m1_boundary'


def test_bootstrap_multistart_iterator_emits_hashed_manifest_and_every_draw():
    import json

    fit = _fit()
    indices = np.asarray([
        np.arange(len(fit.samples)),
        np.arange(len(fit.samples))[::-1],
    ], dtype=np.int64)
    starts = [[0.82, 0.0], [0.78, 0.62]]
    records = list(fit.iter_bootstrap_multistart(indices, starts, maxiter=2))

    assert len(records) == 3
    manifest = records[0]
    assert manifest['record_type'] == 'run_manifest'
    assert manifest['planned_draws'] == 2
    assert manifest['blocks_per_draw'] == len(fit.samples)
    assert manifest['starts_per_draw'] == len(starts)
    assert len(manifest['index_matrix_sha256']) == 64
    assert [row['draw_id'] for row in records[1:]] == [0, 1]
    assert all(len(row['fit']['rows']) == len(starts) for row in records[1:])
    json.dumps(records, allow_nan=False)


def test_bootstrap_multistart_rejects_noninteger_or_malformed_index_matrix():
    fit = _fit()
    with pytest.raises(ValueError, match='integer'):
        list(fit.iter_bootstrap_multistart(
            np.zeros((2, len(fit.samples))), [[0.8, 0.2]],
        ))
