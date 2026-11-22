# P2a：invalid 候选与 evaluate 闭环

## 修复

- `evaluate` 对 `risk=None` 的候选不再做 `risk+eps`：`loss_ratio_vs_identity` 与 `score` 置 null，
  保留 `invalid_reason`；合法候选仍照常打分；
- identity 无效时**受控拒绝**（`identity risk is invalid; refusing to score`），不产生分数；
- `statistics.risk` 增加 Vref 零/近零/非有限检查（`v_ref is zero or near-zero` / `v_ref is non-finite`）；
- `paired_ratios` 显式传协议 `reference_nominal_window`，不再默认 1；
- 打印路径也不对 None 调用 `round()`。

## 回归（`test_evaluate_reports_invalid_candidate_without_crash`）

1. 正常评估 → identity score=100；
2. 把某个候选 kernel 的 validation W 改为负 → 该候选 `risk/score/loss_ratio` 全 null、
   `invalid_reason` 为 non-positive W；identity 仍 100；
3. 把 identity kernel 改为负 → `evaluate` 抛 `identity risk is invalid`。

## 语义

- 坏候选可审计、不崩溃；坏 identity 受控拒绝；
- 无效计数现在来自实际 outer/inner 路径的异常，不是另一个 seed 的 audit 计数。
