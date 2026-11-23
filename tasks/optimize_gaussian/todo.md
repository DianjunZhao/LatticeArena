# optimize_gaussian: trainable-W smear 对照研究 handoff

## 决策状态与问题

- 用户要求同时比较学习型 smear 对同预算 SLSQP 与强谱基线；确认族为 `F=2`。
- 保留“学习型 smear 是否有机会优于 SLSQP”作为研究问题。当前维持 `NOT_READY/UNCERTIFIED`、`physical_score=null` 和数据封存；不读取 gap、validation、shared holdout，也不运行生产 GPU/QUDA。
- trainable-W 是算符参数化；SLSQP/L-BFGS-B 是求解器。确认分析须分别回答“可学习 W 是否增加有限预算下的搜索能力”和“是否优于已固定强谱算符”，不可将二者混成一个结论。

## 已完成的 CPU 诊断

主产物是 [2026-11-23 source-closed replay](trainable_w_operator_cpu_replay_20261123_v1/README.md)，包含协议、独立合成输入、逐调用原始 trace、代码快照和图。旧的 [`trainable_w_operator_cpu_20261121_final`](trainable_w_operator_cpu_20261121_final/README.md) 保留为历史结果：其 `trainable_w.py` 哈希与同目录源不一致且漏掉导入的 SU(3) fixture helper，因此不能作为闭合 provenance 的主收据。新 replay 修复 source hash 缺口，但不增加独立样本。

| 确认维度 | CPU 诊断内容 | 直接观察到的结果 | 可支持的结论 |
|---|---|---|---|
| 同预算局部搜索 | 三个独立合成 panel；每 panel 3 fit + 3 heldout SU(3)-like links；固定 W 与 joint trainable-W；SLSQP/L-BFGS-B；每次 40/160 次 objective+gradient 调用上限 | 36/36 planned solver runs 有返回，4 次触预算/非成功，0 样本排除。cap=160 的 joint-W SLSQP heldout loss 分别约 `0.00614590, 0.00600509, 0.00601227`；固定 W width-2 SLSQP 分别约 `0.00614590, 0.00600511, 0.00601227` | 这个构造目标上 joint W 的增益至多约 `2.5e-8` 量级；没有稳定、实用的学习 W 优势。三个 panel 不足以给总体区间。 |
| 强谱算符 | 同一固定热核目标上的 degree-1/degree-4 Chebyshev 直接最小二乘；不调 heldout | degree-4 heldout loss 为 `2.40e-7, 3.34e-8, 1.11e-7`，比一跳学习参数化约低四至五个数量级 | 该 fixture 的目标按定义就是 `exp(tau H)` 谱函数，因此强谱基占优是结构性负诊断；不能外推为所有物理 smearing 都由谱基胜出。 |
| 数值正确性 | 压缩二次 loss 对照 dense operator loss；W/v/c 梯度对有限差分；在独立 heldout links 复查 | 最大梯度差约 `1.3e-11`，压缩/dense loss 差低于 `2e-16` | 验证此 CPU 实现和 fixture 的代数一致性，不验证 GPU、物理风险或实现耗时优势。 |

![Trainable-W 与固定谱算符对照](trainable_w_operator_cpu_replay_20261123_v1/operator_comparison.png)

文字数据流：`protocol + 固定 seed -> 3 个独立合成 link panel -> 每 panel 切分 3 fit / 3 heldout -> 同一初始化/参数边界/调用上限拟合 -> 仅 fit 选择 -> heldout + KKT/梯度残差作诊断`。优化秒数不含算符/目标构造和后检；因此它是 call-budget 对照，不是 walltime 或训练摊销基准。

## 理论上学习型 smear 可能获益的情形

1. **有限预算搜索：**在同一目标和同一函数族下，精确全局优化器不会被另一个方法理论保证优于；学习器可以通过 warm start、低成本代理、预条件或 proposal policy 更快接近可行解，但需在冻结的 call 与 walltime 预算下实测。
2. **跨任务摊销：**如果一个训练好的 proposal 在多组独立 gauge/operator 实例复用，可摊销训练成本。至少应报告训练总成本、每任务推理成本，并比较 `K*(C_SLSQP-C_infer) > C_train` 是否成立；只有 `C_SLSQP>C_infer` 时才有 break-even 区间。
3. **表达能力与物理约束：**若物理目标依赖非谱局域结构、配置依赖系数、Gaussian sandwich、正定性或可实现的测量风险，learning parameterization 可能以更适合的 inductive bias 优于当前固定 Chebyshev 族。但这需要证明 gauge/cubic covariance、Hermiticity、positivity、归一化和真实 measurement gradients；现有代码没有这些生产合同。

这些是可检验假设。热核合成结果只说明：对谱目标，若不增加谱域/阶数或匹配生产约束，增加同一 synthetic generator 的样本不会改变问题的识别缺口。

## 下一位 agent 的工作顺序

1. **D04 reference：**写明独立物理目标、单位、关联量、数据来源与通过门。原有 reference gate 未通过时，所有对照只能写 diagnostic；不能把 proxy loss 改名为物理 improvement。
2. **D06 `r_star`：**由研究者预先给出最小有意义效应及物理单位/解释；不得根据这三个合成 panel、标准误或 optimizer 残差反推。
3. **D11 强谱基合同：**冻结 degree-4 Chebyshev 的 operator `H`、谱区间/缩放映射、恒等项和归一化、系数约束、正性/投影约束、失败处理，以及它与学习族之间允许不同的参数维数。当前 artifact 的 degree-4 系数是无约束实数最小二乘，只适用于诊断目标。
4. 冻结完整公平预算：同一 objective、输入实例、fit/heldout ID、初始化规则、候选/重启数；分别计训练、setup、objective/gradient calls、求解、推理、I/O、失败恢复与总 walltime。训练数据不能与确认 panel 重叠。
5. 先开展公开/合成方法学扩展：独立生成器族、非纯谱目标、不同噪声/condition number 和预算曲线；输出每个 panel 的 paired loss、调用/时间收敛图、KKT/residual、planned/success/non-success/cap-stop 分母。不使用 production/sealed IDs。
6. 物理合同与阈值通过审阅并另行授权后，再用独立配置/ensemble 做 `F=2` paired confirmation：trainable-W 对同预算 SLSQP；trainable-W 对固定 strong spectral baseline。两条对照都要报告多重性调整的单侧区间、失败/abstain 和训练摊销；只有两条均越过事前效应阈值才支持双重优势。

## 停止规则与扩展接口

若 trainable-W 只优于同预算 SLSQP、没有优于固定谱基，应表述为有限预算优化/摊销结果，不能称为更优物理 smear；若差异低于事前 `r_star` 或跨独立 panel 不稳定，停止扩大同一 fixture。当前任务还没有专属 `TaskSpec` / operator contract / evaluator，框架侧扩展顺序见[可扩展部分地图](../../doc/framework_extensibility.md)。

任何物理结论前都需要保留 `NOT_READY/UNCERTIFIED` 与 `physical_score=null`，直到 reference、效应阈值、operator contract、两条比较预算及数据/GPU 授权全部闭合。
