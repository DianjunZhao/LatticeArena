# optimize_gaussian：学习型 smear 确认性比较

## 用户已确定

- 确认性比较族为 `F=2`：trainable-W 对同预算 SLSQP；trainable-W 对预先固定的强谱基线。
- 当前维持 `NOT_READY/UNCERTIFIED` 与数据封存；不生成 `physical_score`，不读取 gap、validation 或 sealed IDs，不启动 GPU/QUDA。

## 尚未闭合的研究边界

1. **D04 reference：**冻结一个独立、物理上可辩护的目标和数据来源；若 reference gate 未通过，候选差异只能标为诊断结果。
2. **D06 最小效应：**研究者需定义 `r_star` 与其物理单位/解释，不能从已有合成误差反推。
3. **两个对照的可比性：**SLSQP 与 trainable-W 使用同一函数族、目标、约束/正则、fit IDs 和起点规则；强谱基也须冻结算符、谱域、次数、归一化及系数约束。
4. **预算：**同时核算 objective/gradient calls 与总 walltime，并分列训练、选择、推理、求解、setup 和失败恢复成本。学习法的潜在优势应明确是单问题优化、跨问题泛化，还是训练摊销；不可把其中一种优势改写成另一种主张。
5. **生产比较：**待物理 contract 与阈值通过审阅且获得数据/GPU 授权后，再运行 paired comparison；报告 paired 区间、calls/time 收敛图、KKT/residual 及 planned/valid/failed/abstained 分母。

在上述研究选择和授权齐备前，不继续同一 synthetic generator 扩样，不训练生产 W，不打开任何封存 split。历史 CPU toy 只能说明该 toy 上的数值行为，不能证明 learned smear 优于 SLSQP 或强谱基。
