"""Reproducible CPU micro-diagnostic for nested solver receipt contracts.

The cases are fixed software fixtures, not a statistical sample and not a
physical-risk benchmark. Outputs are written once to a new directory.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
from pathlib import Path
from types import SimpleNamespace

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt

from tasks.optimize_gaussian.solver_contract import (
    SolverPolicy,
    run_solver_with_contract,
    search_gated_receipts,
    validate_paired_configuration_ids,
)


class FixtureClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def policy(*, calls=8, seconds=10.0, residual=0.1):
    return SolverPolicy(calls, seconds, 'kkt_residual', residual)


def run_cases():
    cases = []

    clock = FixtureClock()

    def finite_objective(x):
        clock.advance(0.2)
        return (float(x[0]) - 1.0) ** 2

    def successful_solver(objective):
        objective([3.0])
        objective([2.0])
        return SimpleNamespace(x=[1.0], success=True, status=0,
                               message='controlled convergence', kkt_residual=0.01, fun=123.0)

    cases.append(run_solver_with_contract('cfg-accepted', finite_objective, successful_solver,
                                          policy(), clock=clock))

    clock = FixtureClock()

    def budget_objective(x):
        clock.advance(0.2)
        return float(x[0]) ** 2

    def budget_solver(objective):
        for x in (3.0, 2.0, 1.0):
            objective([x])

    cases.append(run_solver_with_contract('cfg-call-budget', budget_objective, budget_solver,
                                          policy(calls=2), clock=clock))

    clock = FixtureClock()

    def slow_objective(_x):
        clock.advance(1.25)
        return 0.5

    cases.append(run_solver_with_contract('cfg-walltime', slow_objective,
                                          lambda objective: objective([0.0]),
                                          policy(seconds=1.0), clock=clock))

    clock = FixtureClock()

    def nonfinite_objective(_x):
        clock.advance(0.2)
        return float('nan')

    cases.append(run_solver_with_contract('cfg-nonfinite', nonfinite_objective,
                                          lambda objective: objective([0.0]),
                                          policy(), clock=clock))

    clock = FixtureClock()

    def residual_objective(_x):
        clock.advance(0.2)
        return 0.25

    def residual_solver(objective):
        objective([0.0])
        return SimpleNamespace(x=[0.0], success=True, status=0,
                               message='controlled residual failure', kkt_residual=0.2)

    cases.append(run_solver_with_contract('cfg-residual', residual_objective, residual_solver,
                                          policy(), clock=clock))

    clock = FixtureClock()

    def failed_solver_objective(_x):
        clock.advance(0.2)
        return 0.25

    def failed_solver(objective):
        objective([0.0])
        return SimpleNamespace(x=[0.0], success=False, status=9,
                               message='controlled non-success', kkt_residual=0.01)

    cases.append(run_solver_with_contract('cfg-solver-failure', failed_solver_objective,
                                          failed_solver, policy(), clock=clock))
    return cases


def _reason(receipt):
    if receipt['gate_status'] == 'contract_accepted':
        return 'accepted'
    return ';'.join(receipt['rejection_reasons'])


def _short_label(receipt):
    if receipt['gate_status'] == 'contract_accepted':
        return 'accepted'
    reason = receipt.get('stop_reason')
    if reason == 'objective_call_budget_exhausted':
        return 'call budget'
    if reason == 'walltime_exceeded_during_objective':
        return 'walltime overrun'
    if reason == 'non_finite_objective':
        return 'non-finite objective'
    if 'residual_exceeds_tolerance' in receipt.get('rejection_reasons', []):
        return 'residual too large'
    if 'solver_non_success' in receipt.get('rejection_reasons', []):
        return 'solver non-success'
    return 'contract rejected'


def _write_json(path: Path, payload):
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + '\n')


def _plot_best_so_far(receipts, output: Path, *, x_field: str, xlabel: str):
    fig, ax = plt.subplots(figsize=(8.8, 5.2), constrained_layout=True)
    colors = plt.get_cmap('tab10')
    for index, receipt in enumerate(receipts):
        rows = [row for row in receipt['objective_trace'] if row['best_so_far'] is not None]
        label = f"{receipt['config_id']} [{_short_label(receipt)}]"
        if not rows:
            ax.plot([], [], color=colors(index), label=label)
            continue
        x = [row['call_index'] if x_field == 'call_index' else row['elapsed_seconds'] for row in rows]
        y = [row['best_so_far'] for row in rows]
        ax.step(x, y, where='post', marker='o', linewidth=1.7, markersize=4,
                color=colors(index), label=label)
    ax.set_xlabel(xlabel)
    ax.set_ylabel('best finite objective seen (fixture units)')
    ax.set_title('Fixed CPU fixtures: best-so-far objective')
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7, loc='best')
    if x_field == 'elapsed_seconds':
        ax.set_xlim(left=0)
    fig.savefig(output, dpi=170)
    plt.close(fig)


def _write_outcome_figure(receipts, output: Path):
    counts = {}
    for receipt in receipts:
        key = _short_label(receipt)
        counts[key] = counts.get(key, 0) + 1
    labels = list(counts)
    values = [counts[label] for label in labels]
    fig, ax = plt.subplots(figsize=(8.8, 4.4), constrained_layout=True)
    bars = ax.barh(labels, values, color=['#4c956c' if x == 'accepted' else '#bc4749' for x in labels])
    ax.bar_label(bars, padding=4)
    ax.set_xlabel('number of fixed fixture cases')
    ax.set_title('Contract outcomes (fixture counts, not failure probabilities)')
    ax.set_xlim(0, max(values, default=0) + 0.8)
    ax.grid(axis='x', alpha=0.25)
    fig.savefig(output, dpi=170)
    plt.close(fig)


def run(output_dir: Path):
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    receipts = run_cases()

    ordered_ids = [receipt['config_id'] for receipt in receipts]
    paired = validate_paired_configuration_ids({'baseline': ordered_ids,
                                                 'candidate': list(ordered_ids)})

    # Exercise the outer proposal budget separately from each nested solver's
    # objective-call budget. This replay does not run the solvers a second time.
    search_result = search_gated_receipts(receipts, proposal_cap=3)
    search_summary = {
        'proposal_cap': 3,
        'proposals_total': len(receipts),
        'proposals_consumed': len(search_result.accepted) + len(search_result.rejected),
        'evaluations': search_result.evaluations,
        'accepted': len(search_result.accepted),
        'rejected': len(search_result.rejected),
        'proposal_budget_exhausted': search_result.budget_exhausted,
        'proposals_not_reached': len(receipts) - len(search_result.accepted) - len(search_result.rejected),
    }

    rows = []
    for receipt in receipts:
        rows.append({
            'config_id': receipt['config_id'],
            'outcome': receipt['gate_status'],
            'reason': _reason(receipt),
            'objective_calls': receipt['objective_calls'],
            'objective_call_cap': receipt['policy']['objective_call_cap'],
            'elapsed_seconds': receipt['elapsed_seconds'],
            'walltime_cap_seconds': receipt['policy']['walltime_cap_seconds'],
            'solver_success': receipt['solver_success'],
            'residual': receipt['residual'],
            'residual_tolerance': receipt['residual_tolerance'],
            'trace_points': len(receipt['objective_trace']),
            'physical_score': receipt['physical_score'],
        })

    with (output_dir / 'failure_counts.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    _write_json(output_dir / 'case_receipts.json', receipts)
    _write_json(output_dir / 'paired_identity.json', {
        'classification': 'identity_check_only',
        **paired,
        'meaning': 'The same ordered IDs were supplied to both labels; no paired risk was measured.',
    })
    _write_json(output_dir / 'search_adapter_summary.json', search_summary)
    _plot_best_so_far(receipts, output_dir / 'best_so_far_by_calls.png',
                      x_field='call_index', xlabel='objective call index')
    _plot_best_so_far(receipts, output_dir / 'best_so_far_by_time.png',
                      x_field='elapsed_seconds', xlabel='elapsed seconds (controlled fixture clock)')
    _write_outcome_figure(receipts, output_dir / 'contract_outcomes.png')

    source_files = [Path(__file__), Path(__file__).with_name('solver_contract.py')]
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files}
    summary = {
        'schema': 'optgauss-solver-contract-diagnostic-v1',
        'classification': 'diagnostic_only',
        'python': platform.python_version(),
        'source_sha256': hashes,
        'fixture_count': len(receipts),
        'accepted_fixture_count': sum(row['gate_status'] == 'contract_accepted' for row in receipts),
        'rejected_fixture_count': sum(row['gate_status'] == 'contract_rejected' for row in receipts),
        'physical_score': None,
        'paired_identity_sha256': paired['sha256'],
        'outer_search': search_summary,
        'walltime_scope': (
            'Cooperative synchronous guard: checks before/after objective calls and before final-point evaluation. '
            'It cannot preempt a running objective or arbitrary solver/native-code work.'
        ),
        'fixture_scope': (
            'Six deterministic software fixtures exercise contract outcomes. Counts are not empirical rates, '
            'statistical estimates, or comparisons of physical smear methods.'
        ),
    }
    _write_json(output_dir / 'summary.json', summary)
    _write_readme(output_dir / 'README.md', rows, search_summary, paired, hashes)
    return summary


def _write_readme(path, rows, search_summary, paired, hashes):
    table = [
        '| 配置 fixture | 结果 / 拒绝原因 | calls / cap | elapsed / cap (s) | solver | residual / tolerance |',
        '|---|---|---:|---:|---|---:|',
    ]
    for row in rows:
        table.append(
            f"| `{row['config_id']}` | `{row['reason']}` | "
            f"{row['objective_calls']} / {row['objective_call_cap']} | "
            f"{row['elapsed_seconds']:.3f} / {row['walltime_cap_seconds']:.3f} | "
            f"{row['solver_success']} | {row['residual']} / {row['residual_tolerance']} |"
        )
    text = f"""# Nested solver contract：CPU 固定样例诊断

**状态：`diagnostic_only`。** 这里验证 contract adapter 对 solver 成功标记、最终点重评估、objective-call 预算、协作式 walltime、非有限目标、残差门与外层 proposal 预算的行为。六行是人为构造的确定性软件样例，不是随机样本、经验失败率、优化器 benchmark 或物理风险比较；所有 `physical_score` 都是 `null`。

## 收据与失败计数

{chr(10).join(table)}

![各固定 fixture 的 contract 收敛轨迹](best_so_far_by_calls.png)

![按耗时记录的各固定 fixture 最佳值](best_so_far_by_time.png)

![固定软件样例的通过和拒绝计数](contract_outcomes.png)

轨迹纵轴是 fixture objective，不能解释为 smear risk。budget fixture 在第 3 次调用请求处截断，最多只进入 2 次目标函数；非有限 fixture 没有有限 best-so-far 点；walltime fixture 的单次调用耗时超过 cap 后被记录并拒绝。接受 fixture 使用两次搜索点评估，再独立重算 solver 返回的 `x`，所以最终点重算也计入 objective-call 预算与 trace。

## paired ID 与 SearchAdapter

`paired_identity.json` 对两个标签提交了相同有序 ID 列，得到 count={paired['count']}、SHA-256 `{paired['sha256']}`。这是 ID 顺序身份检查，不是两臂配对风险测量。

独立重放已生成的收据后，外层 `core.search` 配额为 {search_summary['proposal_cap']} 个 proposal：消费 {search_summary['proposals_consumed']} 个，接受 {search_summary['accepted']} 个，拒绝 {search_summary['rejected']} 个，另有 {search_summary['proposals_not_reached']} 个未进入；`budget_exhausted={search_summary['proposal_budget_exhausted']}`。这与每个 solver 内部的 objective-call cap 是两层不同预算。

## 执行边界

- `walltime_cap_seconds` 是同步包装器的**协作式**限制：在目标函数开始前、目标函数返回后和最终点重评估前检查。它不能中断正在运行的函数、SciPy 内部原生计算或任意 solver 步骤；一次慢调用可能越界，越界结果会计入后拒收。若需要真正 hard timeout，需用可终止的子进程/作业级调度器并设计可审计的进程间收据。
- 残差字段名与阈值由调用方显式提供。本诊断使用玩具 `kkt_residual <= 0.1`，它不是经研究者批准的 Optimize 收敛阈值，也不等价于 QUDA inversion residual。
- solver 的 `success`、有限目标、最终点重评估、残差、objective-call 和 walltime 要同时满足 policy；这些规则仅验证接口 fail-closed 行为，不证明生产 RunSpec 已冻结。
- 没有加载 gauge、propagator、reference、盲测 ID 或 GPU；没有训练 learned-$W$、测量 smear 风险或声称其优于 SLSQP。

## 复现身份

- 脚本与 contract 源码 SHA-256：`{hashes[Path(__file__).name]}`、`{hashes['solver_contract.py']}`。
- 原始收据在 `case_receipts.json`，逐例计数在 `failure_counts.csv`，外层预算记于 `search_adapter_summary.json`。
- `summary.json` 记录 fixture 范围、paired identity hash 与 walltime 限制。
"""
    path.write_text(text)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=Path('results/optimize_gaussian/cpu_solver_contract_v1'))
    args = parser.parse_args(argv)
    summary = run(args.output)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
