# pion 身份审计矩阵（A1/A2/A5）

生成：`python -m tasks.pion_projection.identity_audit`；数值：`joint_identity_audit.json`。

## 检查项（`verify_run_identity`）

- submission：protocol hash、development 内容 SHA、kernel/statistics 实现 hash；
- report：submission SHA、validation 内容 SHA、完整 protocol、reference kind、
  reference verdict/spec 与 submission 一致、候选集合一致；
- 两个 split 的 IDs 等于 RunSpec 范围（行数由 `load_data` 在 joint 前再校验）；
- late metric：键集合等于候选集合、形状 `(len(amplitude_window), len(amplitude_window))`、有限。

## 矩阵

| 用例 | 结果 |
| --- | --- |
| legal | 通过 |
| stale_report（改 report submission_sha256） | 拒绝 |
| validation_reordered | 拒绝 |
| source_changed（改 statistics hash） | 拒绝 |
| report_verdict_changed | 拒绝（verdict 不一致） |
| missing_artifact_spec | joint abstain（`gate_artifact_missing`、`score_spec_missing`） |
| same_seed_reproducible | 两次 joint 的 draws/risk 数组逐位相同 |

## 语义

- `missing_artifact_spec` 是**历史 run** 的预期状态：不伪造 artifact/spec，只诊断；
- 身份相符 ≠ physical 认证：physical 需要 execution receipts，当前两任务为 conditional-only。
