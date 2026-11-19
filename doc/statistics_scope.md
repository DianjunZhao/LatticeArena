# 统计口径与已发表数字的适用范围

## 1. 点值、诊断 seed 与区间

wilson 的归档点值来自 measurement 时的 `validation_results.json`；`paired_audit` 用
seed 7/500 的**诊断重算**是另一列。两者不能混写：

| 口径 | 用途 |
| --- | --- |
| 归档点值（v2 0.967/1.033/1.055；v3 2.633/2.328/2.219；v4 6.633/7.458/8.080） | 冻结实证 |
| 诊断重算（seed 7、500 draws） | 流程检查，不能覆盖归档 |
| 外层 paired 区间 | 条件诊断，见下 |

## 2. coverage=0.983 的含义

`paired_audit_v2/` 的已知增益真值 4.0 是**噪声比平方近似**，不是有限样本 risk 的严格真值；
`coverage=0.983`（60 次模拟）是“近似目标覆盖”，不是“证明区间保守”。60 次模拟的
二项 MC 误差约 ±0.017；报告必须同时给出该不确定性。

## 3. block/τint 与多重比较

- 归档缺保存间隔与 τint，block 长度 5 是保守试点，不是由 τint 数据选出的；
- 多比较、最小有用增益、功效设计**本轮未设计**；现有区间只作探索，不宣称统计功效；
- exceedance fraction 不是 p 值，也不是 posterior；不得当作“改善概率”。

## 4. invalid 与 evaluate

`invalid_evaluate.json` 记录：坏候选的 ratio/score 为 null 且保留 reason；坏 identity 受控
拒绝。无效计数来自实际 outer/inner 路径（`paired` 的 `invalid_draws`），不是另一个 seed 的
静态 audit 计数。

## 5. 仍延期

P4 的 stout/GEVP/multilevel/多体积/新盲测：需新 cross loops 或新数据，明确延期，不阻止
CPU 结项。
