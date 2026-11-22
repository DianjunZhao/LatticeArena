"""CPU-side contract for nested optimizer receipts.

This task-specific adapter keeps solver status, objective-call/time budgets,
and residual checks together before a scalar risk is passed to ``core.search``.
It does not define production thresholds; each caller must supply an explicit
policy, and every emitted receipt remains diagnostic-only.
"""
from __future__ import annotations

import hashlib
import json
import math
from numbers import Integral, Real
import time
from dataclasses import asdict, dataclass

from core.search import Budget, search


class SolverContractBudgetStop(Exception):
    """Internal cooperative stop raised when the frozen policy is exhausted."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class SolverPolicy:
    objective_call_cap: int
    walltime_cap_seconds: float
    residual_field: str
    residual_tolerance: float
    require_solver_success: bool = True

    def __post_init__(self):
        if (isinstance(self.objective_call_cap, bool)
                or not isinstance(self.objective_call_cap, Integral)
                or self.objective_call_cap <= 0):
            raise ValueError('objective_call_cap must be a positive integer')
        if (isinstance(self.walltime_cap_seconds, bool)
                or not isinstance(self.walltime_cap_seconds, Real)
                or not math.isfinite(float(self.walltime_cap_seconds))
                or self.walltime_cap_seconds <= 0):
            raise ValueError('walltime_cap_seconds must be positive and finite')
        if not self.residual_field or not isinstance(self.residual_field, str):
            raise ValueError('residual_field must name the checked residual')
        if (isinstance(self.residual_tolerance, bool)
                or not isinstance(self.residual_tolerance, Real)
                or not math.isfinite(float(self.residual_tolerance))
                or self.residual_tolerance < 0):
            raise ValueError('residual_tolerance must be finite and nonnegative')
        if not isinstance(self.require_solver_success, bool):
            raise ValueError('require_solver_success must be boolean')

        # Canonicalize numpy scalar integers/reals and other Integral/Real
        # implementations before hashing or serializing the policy.
        object.__setattr__(self, 'objective_call_cap', int(self.objective_call_cap))
        object.__setattr__(self, 'walltime_cap_seconds', float(self.walltime_cap_seconds))
        object.__setattr__(self, 'residual_tolerance', float(self.residual_tolerance))

    def as_dict(self):
        return asdict(self)

    @property
    def sha256(self):
        payload = json.dumps(self.as_dict(), sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(payload.encode()).hexdigest()


def solver_policy_from_mapping(specification) -> SolverPolicy:
    """Validate the explicit policy fields shared by protocol and RunSpec code."""
    if not isinstance(specification, dict):
        raise ValueError('solver_contract must be an object')
    required_fields = {
        'objective_call_cap', 'walltime_cap_seconds', 'residual_field', 'residual_tolerance',
        'require_solver_success',
    }
    if set(specification) - required_fields:
        raise ValueError('solver_contract has unknown fields')
    missing = required_fields - specification.keys()
    if missing:
        raise ValueError(f'solver_contract is missing fields: {sorted(missing)}')
    try:
        return SolverPolicy(**specification)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'invalid solver_contract: {exc}') from exc


def _field(result, name, default=None):
    if isinstance(result, dict):
        return result.get(name, default)
    return getattr(result, name, default)


def _json_number(value):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric):
        return 'NaN'
    if math.isinf(numeric):
        return 'Infinity' if numeric > 0 else '-Infinity'
    return numeric


def run_solver_with_contract(
    config_id, objective, solver, policy: SolverPolicy, *,
    residual_evaluator=None, clock=time.perf_counter,
):
    """Run one solver with call and elapsed-time guards; retain every stop reason.

    A walltime cap is checked before and after each objective call. Since an
    objective call cannot be preempted by this synchronous wrapper, a slow call
    can overrun the cap once; that result is recorded and rejected, and no next
    call is allowed.
    """
    if policy is None or not isinstance(policy, SolverPolicy):
        raise TypeError('an explicit SolverPolicy is required')
    try:
        json.dumps(config_id, sort_keys=True, separators=(',', ':'), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError('config_id must be JSON-serializable without NaN or Infinity') from exc
    started = clock()
    objective_calls = 0
    completed_calls = 0
    best_so_far = None
    trace = []
    stop_reason = None
    solver_result = None
    solver_returned = False
    objective_exception = None

    def elapsed():
        return max(0.0, float(clock()) - float(started))

    def guarded_call(x, *, phase, update_best):
        nonlocal objective_calls, completed_calls, best_so_far, stop_reason, objective_exception
        if objective_calls >= policy.objective_call_cap:
            stop_reason = 'objective_call_budget_exhausted'
            raise SolverContractBudgetStop(stop_reason)
        if elapsed() >= policy.walltime_cap_seconds:
            stop_reason = 'walltime_budget_exhausted_before_objective'
            raise SolverContractBudgetStop(stop_reason)

        objective_calls += 1
        call_started = clock()
        try:
            raw_value = objective(x)
            completed_calls += 1
        except Exception as exc:  # keep optimizer and evaluator failures distinct
            objective_exception = {'type': type(exc).__name__, 'message': str(exc)}
            trace.append({
                'call_index': objective_calls,
                'phase': phase,
                'elapsed_seconds': elapsed(),
                'raw_value': None,
                'finite': False,
                'eligible_within_budget': False,
                'best_so_far': best_so_far,
                'exception_type': type(exc).__name__,
                'exception_message': str(exc),
            })
            stop_reason = 'objective_exception'
            raise SolverContractBudgetStop(stop_reason) from exc

        try:
            value = float(raw_value)
            finite = math.isfinite(value)
        except (TypeError, ValueError):
            value, finite = float('nan'), False
        call_elapsed = max(0.0, float(clock()) - float(call_started))
        within_walltime = elapsed() <= policy.walltime_cap_seconds
        eligible = finite and within_walltime
        if update_best and eligible and (best_so_far is None or value < best_so_far):
            best_so_far = value
        trace.append({
            'call_index': objective_calls,
            'phase': phase,
            'elapsed_seconds': elapsed(),
            'call_seconds': call_elapsed,
            'raw_value': _json_number(value),
            'finite': finite,
            'eligible_within_budget': eligible,
            'best_so_far': best_so_far,
        })
        if not finite:
            stop_reason = 'non_finite_objective'
            raise SolverContractBudgetStop(stop_reason)
        if not within_walltime:
            stop_reason = 'walltime_exceeded_during_objective'
            raise SolverContractBudgetStop(stop_reason)
        return value

    def guarded_objective(x):
        return guarded_call(x, phase='solver', update_best=True)

    def guarded_residual_objective(x):
        # Stationarity probes use the same objective-call and walltime limits,
        # but cannot improve the optimizer's best-so-far curve.
        return guarded_call(x, phase='residual_diagnostic', update_best=False)

    try:
        solver_result = solver(guarded_objective)
        solver_returned = True
    except SolverContractBudgetStop as exc:
        stop_reason = exc.reason
    except Exception as exc:
        stop_reason = 'solver_exception'
        solver_result = {'solver_exception': {'type': type(exc).__name__, 'message': str(exc)}}

    solver_success = _field(solver_result, 'success', None)
    solver_status = _field(solver_result, 'status', None)
    solver_message = _field(solver_result, 'message', None)
    final_x = _field(solver_result, 'x', None)
    final_objective = None
    residual_diagnostic = None
    residual_evaluation_exception = None
    residual_raw = _field(solver_result, policy.residual_field, None)
    if solver_returned and stop_reason is None:
        if final_x is None:
            stop_reason = 'missing_final_parameters'
        else:
            try:
                # Re-evaluate the returned point through the guarded path; do
                # not trust an optimizer's cached .fun as the final risk.
                final_objective = guarded_objective(final_x)
            except SolverContractBudgetStop as exc:
                stop_reason = exc.reason

    if (solver_returned and stop_reason is None and final_x is not None
            and residual_evaluator is not None):
        try:
            residual_diagnostic = residual_evaluator(
                guarded_residual_objective, final_x, solver_result,
            )
            residual_raw = _field(residual_diagnostic, policy.residual_field, None)
        except SolverContractBudgetStop as exc:
            stop_reason = exc.reason
        except Exception as exc:
            residual_evaluation_exception = {
                'type': f'{type(exc).__module__}.{type(exc).__qualname__}',
                'message': str(exc),
            }

    try:
        residual = float(residual_raw) if residual_raw is not None else None
    except (TypeError, ValueError):
        residual = None
    residual_finite = residual is not None and math.isfinite(residual)

    rejection_reasons = []
    if stop_reason is not None:
        rejection_reasons.append(stop_reason)
    if residual_evaluation_exception is not None:
        rejection_reasons.append('residual_evaluation_exception')
    if not solver_returned and stop_reason is None:
        rejection_reasons.append('solver_did_not_return')
    if policy.require_solver_success and solver_success is not True:
        rejection_reasons.append('solver_non_success')
    try:
        final_values = [float(value) for value in list(final_x)]
        parameters_finite = bool(final_values) and all(math.isfinite(value) for value in final_values)
        final_parameters = [_json_number(value) for value in final_values]
    except (TypeError, ValueError):
        final_values = None
        parameters_finite = False
        final_parameters = None
    if not parameters_finite:
        rejection_reasons.append('missing_or_non_finite_final_parameters')
    if final_objective is None or not math.isfinite(final_objective):
        rejection_reasons.append('missing_finite_final_objective')
    if not residual_finite:
        rejection_reasons.append('missing_or_non_finite_residual')
    elif residual > policy.residual_tolerance:
        rejection_reasons.append('residual_exceeds_tolerance')

    total_elapsed = elapsed()
    if total_elapsed > policy.walltime_cap_seconds and not any(
            reason.startswith('walltime_') for reason in rejection_reasons):
        rejection_reasons.append('walltime_budget_exceeded')
    if objective_calls > policy.objective_call_cap:
        rejection_reasons.append('objective_call_budget_exceeded')

    return {
        'schema': 'optgauss-nested-solver-contract-v1',
        'classification': 'diagnostic_only',
        'config_id': config_id,
        'policy': policy.as_dict(),
        'policy_sha256': policy.sha256,
        'objective_calls': objective_calls,
        'completed_objective_calls': completed_calls,
        'elapsed_seconds': total_elapsed,
        'best_so_far': best_so_far,
        'final_objective': final_objective,
        'solver_returned': solver_returned,
        'solver_success': solver_success if isinstance(solver_success, bool) else None,
        'solver_status': _json_scalar(solver_status),
        'solver_message': str(solver_message) if solver_message is not None else None,
        'solver_nfev': _json_scalar(_field(solver_result, 'nfev', None)),
        'solver_nit': _json_scalar(_field(solver_result, 'nit', None)),
        'final_parameters': final_parameters,
        'final_parameters_finite': parameters_finite,
        'residual_name': policy.residual_field,
        'residual': _json_number(residual) if residual is not None else None,
        'residual_tolerance': policy.residual_tolerance,
        'stop_reason': stop_reason,
        'objective_exception': objective_exception,
        'residual_diagnostic': residual_diagnostic,
        'residual_evaluation_exception': residual_evaluation_exception,
        'objective_trace': trace,
        'gate_status': 'contract_accepted' if not rejection_reasons else 'contract_rejected',
        'rejection_reasons': rejection_reasons,
        'physical_score': None,
    }


def _json_scalar(value):
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, Integral) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, Real):
        return _json_number(value)
    return str(value)


def validate_paired_configuration_ids(ids_by_method):
    """Require exact, ordered configuration identity across method arms."""
    if not isinstance(ids_by_method, dict) or len(ids_by_method) < 2:
        raise ValueError('at least two method ID lists are required')
    normalized = {}
    serialized_by_method = {}
    for method, ids in ids_by_method.items():
        if not isinstance(method, str) or not method:
            raise ValueError('method names must be nonempty strings')
        if isinstance(ids, (str, bytes)):
            raise ValueError(f'{method} configuration IDs must be a sequence, not a string')
        ids = list(ids)
        if not ids:
            raise ValueError(f'{method} configuration IDs are empty')
        try:
            serialized = [json.dumps(item, sort_keys=True, separators=(',', ':'), allow_nan=False)
                          for item in ids]
        except (TypeError, ValueError) as exc:
            raise ValueError(f'{method} configuration IDs must be JSON-serializable') from exc
        if len(set(serialized)) != len(serialized):
            raise ValueError(f'{method} configuration IDs contain duplicates')
        normalized[method] = ids
        serialized_by_method[method] = serialized
    first_method = next(iter(normalized))
    first_serialized = serialized_by_method[first_method]
    for method in list(normalized)[1:]:
        serialized = serialized_by_method[method]
        if serialized != first_serialized:
            raise ValueError(f'{method} configuration IDs/order do not match {first_method}')
    canonical = json.dumps(normalized[first_method], sort_keys=True, separators=(',', ':'), allow_nan=False)
    return {
        'ordered_ids': normalized[first_method],
        'count': len(first_serialized),
        'sha256': hashlib.sha256(canonical.encode()).hexdigest(),
        'methods': list(normalized),
    }


def search_gated_receipts(receipts, proposal_cap):
    """Pass only contract-accepted finite risks to the existing scalar search."""
    if isinstance(proposal_cap, bool) or not isinstance(proposal_cap, Integral) or proposal_cap < 0:
        raise ValueError('proposal_cap must be a nonnegative integer')
    proposals = []
    seen = set()
    for receipt in receipts:
        if not isinstance(receipt, dict) or 'config_id' not in receipt:
            raise ValueError('every receipt must be a mapping with config_id')
        try:
            identity = json.dumps(receipt['config_id'], sort_keys=True, separators=(',', ':'), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError('receipt config_id must be JSON-serializable') from exc
        if identity in seen:
            raise ValueError('receipt config_id values must be unique')
        seen.add(identity)
        proposals.append((receipt['config_id'], receipt))

    def validate(receipt):
        ok = receipt.get('gate_status') == 'contract_accepted'
        return ok, '; '.join(receipt.get('rejection_reasons', [])) or 'nested solver contract rejected'

    return search(
        proposals,
        evaluate=lambda receipt: receipt.get('final_objective'),
        validate=validate,
        budget=Budget(proposal_cap),
    )
