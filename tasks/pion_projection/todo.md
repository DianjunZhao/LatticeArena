# pion_projection：确认性评分的剩余边界

## 已确认的研究边界

- 用户接受 bounded block-MSE 作为独立于 ensemble-risk 的 estimand；这不等于已经认可其物理校准。
- 状态保持 `NOT_READY/UNCERTIFIED`，`physical_score=null`；E anchor、gap、validation 与 shared holdout 数据保持封存，不启动 GPU/QUDA。
- [依赖图敏感度报告](../../results/pion_projection/bounded_score_dependence_sensitivity_20261123_v1/README.md)给出有限依赖假设下的解析界和图；[receipt 审计](../../results/pion_projection/independent_block_anchor_receipt_audit_20261122/README.md)记录候选块数量及当前证据缺口。
- 纯函数与确定性产物生成在 [`dependency_graph_bound.py`](dependency_graph_bound.py)，解析输入/边界测试在 [`test_pion_dependency_graph_bound.py`](../../tests/test_pion_dependency_graph_bound.py)。

## 当前证据能支持什么

100 条 development 配置按冻结的 length-5 规则可重现地组成 20 个候选块。当前 receipt 不给出分数特异的自相关/混合上界，因此经认证的独立块数仍未建立。E anchor 尚无可用 correlator receipt，anchor 值及共同偏差界未知。依赖图报告中的 `chi` 是敏感度参数，不是由 trajectory 间距推得的量。

## 继续校准前必须冻结

1. 目标质量 `m*`、单位、允许范围与 clipping 规则。
2. 统计单位和可审计的依赖控制：可证明的依赖图/染色数上界，或另一条提供有限样本误差界的 score-specific mixing/spectral-gap 论证。
3. anchor 来源及共同偏差界 `B`，连同其独立性和覆盖概率依据。
4. 失败块是整项 abstain 还是另立 failure-augmented estimand；同时冻结实际阈值、候选 family，并将 score 预算 `alpha_s` 与 anchor 覆盖预算 `alpha_A` 分开分配。
5. 一个通过独立物理审阅的 reference/model-identification gate。当前失败的参考门不能靠更换稳健统计量或缩窄区间修复。

在这些项完成审阅前，不读取封存 split、不扩同一 synthetic Monte Carlo、不重新测量，也不生成物理分数。后续诊断须报告 planned/valid/failed/abstained 分母、失败原因、图或可复查文字及适用假设。
