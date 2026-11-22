# Pion robust-score synthetic calibration

生成命令：`python -m tasks.pion_projection.robust_score_diagnostic`。该实验仅校准 paired score 启发式，不改变生产物理分数。

## 设计

每个 cell 有 400 个独立合成 dataset，每个 dataset 含 64 个共同 paired risk draws。图中区间是以独立 dataset 为试验单位的 95% Clopper–Pearson Monte Carlo 区间。风险 draw 是合成扰动，不是实测格点 bootstrap。

风险比较包括 median-only 描述分、当前形式的 paired log lower order statistic，以及对冻结 reference/window 分支取最差 lower bound。用 inverted-CDF order statistic 时，正风险下 log lower bound 与原风险比 lower bound 是单调变换的同一排序量；二者不能被宣传为独立稳健方法。median-only 只作排名诊断。

## 认证/接受频率

| 场景 | 方法 | 次数 | 比率 | MC 95% 区间 |
| --- | --- | ---: | ---: | ---: |
| null | median_only | 0/400 | 0.000 | [0.000, 0.009] |
| null | paired_lower_bound | 0/400 | 0.000 | [0.000, 0.009] |
| null | worst_case_reference_window | 0/400 | 0.000 | [0.000, 0.009] |
| null | abstain | 0/400 | 0.000 | [0.000, 0.009] |
| known_improvement | median_only | 400/400 | 1.000 | [0.991, 1.000] |
| known_improvement | paired_lower_bound | 400/400 | 1.000 | [0.991, 1.000] |
| known_improvement | worst_case_reference_window | 400/400 | 1.000 | [0.991, 1.000] |
| known_improvement | abstain | 0/400 | 0.000 | [0.000, 0.009] |
| heavy_tail_null | median_only | 0/400 | 0.000 | [0.000, 0.009] |
| heavy_tail_null | paired_lower_bound | 0/400 | 0.000 | [0.000, 0.009] |
| heavy_tail_null | worst_case_reference_window | 0/400 | 0.000 | [0.000, 0.009] |
| heavy_tail_null | abstain | 0/400 | 0.000 | [0.000, 0.009] |
| single_extreme_draw_null | median_only | 0/400 | 0.000 | [0.000, 0.009] |
| single_extreme_draw_null | paired_lower_bound | 0/400 | 0.000 | [0.000, 0.009] |
| single_extreme_draw_null | worst_case_reference_window | 0/400 | 0.000 | [0.000, 0.009] |
| single_extreme_draw_null | abstain | 0/400 | 0.000 | [0.000, 0.009] |
| near_zero_baseline | median_only | 0/400 | 0.000 | [0.000, 0.009] |
| near_zero_baseline | paired_lower_bound | 0/400 | 0.000 | [0.000, 0.009] |
| near_zero_baseline | worst_case_reference_window | 0/400 | 0.000 | [0.000, 0.009] |
| near_zero_baseline | abstain | 400/400 | 1.000 | [0.991, 1.000] |
| reference_window_conflict | median_only | 0/400 | 0.000 | [0.000, 0.009] |
| reference_window_conflict | paired_lower_bound | 0/400 | 0.000 | [0.000, 0.009] |
| reference_window_conflict | worst_case_reference_window | 0/400 | 0.000 | [0.000, 0.009] |
| reference_window_conflict | abstain | 0/400 | 0.000 | [0.000, 0.009] |
| single_two_state_reference_conflict | median_only | 0/400 | 0.000 | [0.000, 0.009] |
| single_two_state_reference_conflict | paired_lower_bound | 0/400 | 0.000 | [0.000, 0.009] |
| single_two_state_reference_conflict | worst_case_reference_window | 0/400 | 0.000 | [0.000, 0.009] |
| single_two_state_reference_conflict | abstain | 0/400 | 0.000 | [0.000, 0.009] |

![不同 paired 规则的接受频率与 MC 区间](robust_score_rates.png)

## 排名翻转与 sensitivity

Window 1 和 Window 2 被有意设置为不同 candidate 排名；逐窗 winner 概率和 worst-case 下界的均值/MC 标准误保存在 `robust_score_diagnostic.json`，图见下。这个例子说明 worst-case 会对所冻结的分支集合敏感；它不能发现所有模型共同的偏差。

![reference/window 排名翻转](robust_score_sensitivity.png)

共同乘法尺度变化的最大 paired log lower-bound 差为 `1.318e-15`（400 个合成 dataset）。`near_zero_baseline` 按固定 `min_baseline_risk=1e-06` abstain。单个极端 draw 对 median-only 与 lower-quantile 规则的区别见频率表。

## 解释边界

这些结果是方法学合成试验，不构成校准保证，也不能修复错误 reference 或共同模型偏差。只有独立 anchor、冻结 score spec 与真实 paired data 才能支持物理评分；当前 production score 仍不因本结果升级。
