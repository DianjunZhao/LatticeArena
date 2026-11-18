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

## 5. 未做（NOT_RUN）

- 把 `RunState` 接入 evaluate/candidate 的持久化（当前只在库/测试层）；
- 真实的 GPU 计时账本（设备/缓存/并行度）；
- 跨入口的 same-draw 一致性报告（pion joint 已有 draw ID，wilson 的 paired 用同一 block index，
  但没有统一入口生成）。
