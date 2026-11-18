# 运行状态、fold-local 统计与成本账本（F3 切片）

## 1. 状态机

`core/state.py`：

| 子状态 | 含义 |
| --- | --- |
| `operator` | 算子/核的数学正确性 |
| `reference` | 参考模型是否可识别 |
| `numerical` | 数值稳定性（条件数、floor、收敛） |
| `statistical` | 统计估计与区间 |
| `comparison` | 候选与基线的比较/证书 |

合法迁移：`not_run → draft → validated`，任意 `draft/validated → failed`。**不能跳过**，也不能从
`failed` 回到 `validated`。

`score_or_null()` 只在 `statistical` 与 `comparison` 都为 `validated` 时返回分数，否则返回 `None`——
这就是“分数可以为空”的实现。

## 2. 观察 validation 是永久的

`observe_validation(reference)` 记录一次观察；之后再声明“盲测”或“预注册”都无效。
泄漏反例：

1. 在 comparison 之前调 `observe_validation('v3')`；
2. 状态里 `validation_observed=True` 永久保留；
3. 任何基于该数据的“首次盲测”声明都只能标为历史诊断，不能当预注册证据。

## 3. fold-local 统计

`tasks/pion_projection/nested_cv.py` 的每个 outer fold：

- 重拟合参考（single cosh）；
- 重算通道标度、协方差（`ReferenceFit` 内部）；
- 重选 `tuned_gaussian` 的幂次；
- 重跑 SLSQP 超参数；
- 留出 fold 只评估。

`fold_plan.json` 的 `bindings` 记录：split、block_length、bootstrap_samples、参考 kind/window、
baseline、score spec、搜索预算、seed、`validation_observed=False`。

## 4. 成本账本

`core/ledger.py`：

- 阶段：`setup / solve / residual / kernel / io / analysis`；
- 环境：device、precision、parallel；
- 冷/热缓存分别累计；
- `merge` 拒绝混合不同 device/precision/parallel 的账本。

尚未接入 measure：需要 GPU 测量时手动调用。

## 5. 已接入的位置

- **wilson `develop`**：submission.json 现在带 `run_state`（operator/numerical/reference/
  statistical/comparison 五个状态 + evidence 引用）；reference gate 失败时 `reference`/`comparison`
  为 `failed`；
- **wilson `evaluate`**：从冻结的 run_state 继承前四个状态，评估后写 `comparison` 并永久记录
  `validation_observed`；
- **wilson `measure`**：provenance 现在带 `ledger`（setup/kernel 阶段、设备、精度、并行度）；
- **pion `nested_cv`**：`fold_plan.json` 的 bindings（split/block/bootstrap/reference/baseline/
  score spec/搜索预算/seed/validation 未观察）；
- **pion consistency**：`core/comparator` 与证书的 4 个下界逐位一致（same-draw 跨入口）。

测试：`test_develop_records_run_state`（临时 run 上 develop 写出的状态）、
`test_run_state_transitions_and_score_gating`、`test_cost_ledger_phases_and_environment`。

## 6. 未做（NOT_RUN）

- pion `evaluate`/`candidate` 的持久化 run_state（当前只有 wilson）；
- 真实 GPU 计时账本（device/cache/parallel 字段已就绪，但没有新测量）；
- 跨 task 的统一 same-draw 入口（pion 有 draw ID，wilson 用同一 block index，但未统一生成）。
