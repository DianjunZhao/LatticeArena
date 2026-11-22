from types import SimpleNamespace

import pytest

from tasks.optimize_gaussian.solver_contract import (
    SolverPolicy,
    run_solver_with_contract,
    search_gated_receipts,
    validate_paired_configuration_ids,
)


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def policy(*, calls=8, seconds=10.0, residual=0.1):
    return SolverPolicy(calls, seconds, 'kkt_residual', residual)


def test_policy_requires_finite_positive_budgets_and_residual_tolerance():
    with pytest.raises(ValueError, match='objective_call_cap'):
        SolverPolicy(True, 1.0, 'residual', 0.1)
    with pytest.raises(ValueError, match='walltime_cap_seconds'):
        SolverPolicy(2, float('inf'), 'residual', 0.1)
    with pytest.raises(ValueError, match='residual_tolerance'):
        SolverPolicy(2, 1.0, 'residual', float('nan'))
    with pytest.raises(ValueError, match='require_solver_success'):
        SolverPolicy(2, 1.0, 'residual', 0.1, require_solver_success='yes')


def test_accepted_receipt_rechecks_final_x_and_keeps_best_so_far():
    clock = FakeClock()

    def objective(x):
        clock.advance(0.2)
        return (float(x[0]) - 1.0) ** 2

    def solver(fun):
        fun([3.0])
        fun([2.0])
        return SimpleNamespace(x=[1.0], success=True, status=0, message='converged',
                               kkt_residual=0.01, fun=999.0)

    receipt = run_solver_with_contract('cfg-0', objective, solver, policy(), clock=clock)

    assert receipt['gate_status'] == 'contract_accepted'
    assert receipt['physical_score'] is None
    assert receipt['objective_calls'] == receipt['completed_objective_calls'] == 3
    assert receipt['final_objective'] == 0.0  # independently evaluated; cached fun=999 is ignored
    assert [row['best_so_far'] for row in receipt['objective_trace']] == [4.0, 1.0, 0.0]
    assert receipt['objective_trace'][-1]['elapsed_seconds'] == pytest.approx(0.6)


def test_residual_probes_consume_budget_without_improving_solver_best():
    clock = FakeClock()

    def objective(x):
        clock.advance(0.1)
        return float(x[0]) ** 2

    def solver(fun):
        fun([1.0])
        return SimpleNamespace(x=[0.5], success=True, kkt_residual=0.01)

    def residual_probe(guarded_objective, point, _result):
        guarded_objective([-10.0])  # deliberately worse than the solver's candidate
        return {'kkt_residual': 0.01, 'probe_point': list(point)}

    receipt = run_solver_with_contract(
        'cfg-residual-probe', objective, solver, policy(),
        residual_evaluator=residual_probe, clock=clock,
    )

    assert receipt['gate_status'] == 'contract_accepted'
    assert receipt['objective_calls'] == 3
    assert [row['phase'] for row in receipt['objective_trace']] == [
        'solver', 'solver', 'residual_diagnostic',
    ]
    assert [row['best_so_far'] for row in receipt['objective_trace']] == [1.0, 0.25, 0.25]


def test_residual_probe_budget_exhaustion_is_preserved_as_rejection():
    clock = FakeClock()

    def objective(x):
        clock.advance(0.1)
        return float(x[0]) ** 2

    def solver(fun):
        fun([1.0])
        return SimpleNamespace(x=[0.5], success=True)

    receipt = run_solver_with_contract(
        'cfg-residual-budget', objective, solver, policy(calls=2),
        residual_evaluator=lambda guarded, _point, _result: {
            'kkt_residual': guarded([-10.0]),
        },
        clock=clock,
    )

    assert receipt['gate_status'] == 'contract_rejected'
    assert receipt['objective_calls'] == 2
    assert receipt['stop_reason'] == 'objective_call_budget_exhausted'
    assert 'objective_call_budget_exhausted' in receipt['rejection_reasons']


def test_objective_call_budget_truncates_and_rejects_without_exceeding_cap():
    clock = FakeClock()

    def objective(x):
        clock.advance(0.1)
        return float(x[0]) ** 2

    def solver(fun):
        for x in (3.0, 2.0, 1.0):
            fun([x])

    receipt = run_solver_with_contract('cfg-budget', objective, solver,
                                       policy(calls=2), clock=clock)

    assert receipt['gate_status'] == 'contract_rejected'
    assert receipt['stop_reason'] == 'objective_call_budget_exhausted'
    assert receipt['objective_calls'] == 2
    assert 'missing_finite_final_objective' in receipt['rejection_reasons']
    assert receipt['best_so_far'] == 4.0


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf')])
def test_nonfinite_objective_is_recorded_and_rejected(value):
    clock = FakeClock()

    def objective(_x):
        clock.advance(0.1)
        return value

    receipt = run_solver_with_contract(
        'cfg-nonfinite', objective,
        lambda fun: fun([0.0]), policy(), clock=clock,
    )

    assert receipt['gate_status'] == 'contract_rejected'
    assert receipt['stop_reason'] == 'non_finite_objective'
    assert receipt['objective_trace'][0]['finite'] is False
    assert receipt['objective_trace'][0]['best_so_far'] is None
    assert 'non_finite_objective' in receipt['rejection_reasons']


def test_walltime_overrun_during_objective_is_recorded_and_rejected():
    clock = FakeClock()

    def objective(_x):
        clock.advance(1.25)
        return 0.5

    receipt = run_solver_with_contract(
        'cfg-walltime', objective,
        lambda fun: fun([0.0]), policy(seconds=1.0), clock=clock,
    )

    assert receipt['gate_status'] == 'contract_rejected'
    assert receipt['stop_reason'] == 'walltime_exceeded_during_objective'
    assert receipt['elapsed_seconds'] == pytest.approx(1.25)
    assert receipt['objective_trace'][0]['eligible_within_budget'] is False
    assert 'walltime_exceeded_during_objective' in receipt['rejection_reasons']


def test_residual_threshold_and_solver_success_are_independent_gates():
    clock = FakeClock()

    def objective(_x):
        clock.advance(0.1)
        return 1.0

    high_residual = run_solver_with_contract(
        'cfg-residual', objective,
        lambda fun: (fun([0.0]) and SimpleNamespace(
            x=[0.0], success=True, kkt_residual=0.2)),
        policy(), clock=clock,
    )
    assert high_residual['gate_status'] == 'contract_rejected'
    assert 'residual_exceeds_tolerance' in high_residual['rejection_reasons']

    clock = FakeClock()
    nonconverged = run_solver_with_contract(
        'cfg-not-converged', objective,
        lambda fun: (fun([0.0]) and SimpleNamespace(
            x=[0.0], success=False, status=9, kkt_residual=0.01)),
        policy(), clock=clock,
    )
    assert nonconverged['gate_status'] == 'contract_rejected'
    assert 'solver_non_success' in nonconverged['rejection_reasons']
    assert 'residual_exceeds_tolerance' not in nonconverged['rejection_reasons']


def test_paired_ids_require_same_unique_ordered_configuration_sequence():
    ids = ['cfg-0', 'cfg-1', 'cfg-2']
    paired = validate_paired_configuration_ids({'SLSQP': ids, 'learned': list(ids)})
    assert paired['count'] == 3
    assert paired['ordered_ids'] == ids
    assert len(paired['sha256']) == 64

    with pytest.raises(ValueError, match='do not match'):
        validate_paired_configuration_ids({'SLSQP': ids, 'learned': ['cfg-1', 'cfg-0', 'cfg-2']})
    with pytest.raises(ValueError, match='duplicates'):
        validate_paired_configuration_ids({'SLSQP': ['cfg-0', 'cfg-0'], 'learned': ['cfg-0', 'cfg-1']})
    with pytest.raises(ValueError, match='not a string'):
        validate_paired_configuration_ids({'SLSQP': 'cfg-0', 'learned': ['cfg-0']})


def test_search_only_evaluates_accepted_receipts_and_records_proposal_truncation():
    receipts = [
        {'config_id': f'cfg-{index}', 'gate_status': 'contract_accepted',
         'rejection_reasons': [], 'final_objective': 1.0 + index}
        if index == 0 else
        {'config_id': f'cfg-{index}', 'gate_status': 'contract_rejected',
         'rejection_reasons': ['solver_non_success'], 'final_objective': None}
        for index in range(4)
    ]
    result = search_gated_receipts(receipts, proposal_cap=3)

    assert len(result.accepted) == result.evaluations == 1
    assert len(result.rejected) == 2
    assert result.budget_exhausted is True
    assert result.best('risk')['risk'] == 1.0


def test_contract_inputs_reject_unstable_ids_and_duplicate_receipts():
    with pytest.raises(ValueError, match='config_id'):
        run_solver_with_contract(float('nan'), lambda _x: 1.0, lambda _fun: None,
                                 policy(), clock=FakeClock())
    with pytest.raises(ValueError, match='JSON-serializable'):
        validate_paired_configuration_ids({'left': ['cfg-0', float('nan')],
                                            'right': ['cfg-0', 'cfg-1']})
    duplicate = {'config_id': 'cfg-0', 'gate_status': 'contract_accepted',
                 'rejection_reasons': [], 'final_objective': 1.0}
    with pytest.raises(ValueError, match='unique'):
        search_gated_receipts([duplicate, duplicate], proposal_cap=2)
