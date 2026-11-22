# 实际 BCB—response—core search 闭环（D）

生成：`python -m tasks.optimize_gaussian.adapt_v2`；数值：`adapt_v2.json`。

**管线演示（不是 surrogate 精度验证）**：搜索用的评价器就是精确 BCB，因此“差值为 0”是
同一函数的构造结果，不是近似模型的精度。

## 内容

- 用 v9 submission 的 W（8×2）与 θ（9 维）在 4³ 小格点上构建实际 `LearnedSmear`；
- 固定 links/field；`response(θ)=Re⟨f,K_θ f⟩` 是**实际 BCB**，不是 toy roll；
- 该 response 直接作为 `core.search.search` 的评价函数（每次提案都调用真实 kernel）；
  4 个提案（base、±0.1 shift、畸形 theta）→ 3 accepted、1 rejected（malformed）；
- 最佳 θ 重新评价：`best_exact` 与搜索值相同（差 0.0），因为评价器就是精确 BCB；
- OperatorContract 在**实际对象**上：线性残差 5.0e−16、Hermitian 残差 2.5e−16；
- MeasurementBundle 用 field/response 数组与能力声明；请求 `cross_matrix` 抛
  `UnsupportedCapability`，不静默回退。

## 结果

| 项 | 值 |
| --- | --- |
| base response | 1203.62 |
| best θ 的精确 response | −1192.14 |
| 搜索/精确差 | 0.0（同一评价器） |
| accepted / rejected / evaluations | 3 / 1 / 3 |
| linearity / Hermitian | 5.0e−16 / 2.5e−16 |

## 诚实说明

- “合成响应”与“精确 BCB”在本实现中是同一个函数，因此差值为 0 是**构造结果**；
  该实验证明的是管线接通与算子属性，不是 surrogate 精度；
- 若需要 surrogate vs 精确的误差，应另建近似模型（不在本包）；
- 未使用真实 GPU C_fit；未训练新网络。
