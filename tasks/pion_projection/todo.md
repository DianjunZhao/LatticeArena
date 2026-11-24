# Pion projection: bounded block-risk calibration handoff

## 决策状态

- 用户接受 **bounded block-risk** 作为一个独立 estimand；它不等价于原 ensemble-risk，也尚未给出物理分数认证。
- 继续保持 `NOT_READY/UNCERTIFIED`、`physical_score=null` 和封存数据状态。不访问 E anchor、gap、validation、shared holdout；不启动 GPU/QUDA。
- 此文件给下一位 agent 的开工顺序。每项新诊断都要同时保留 planned/valid/failed/abstained 分母，并附图或可复查的文字流程图。

## 已完成且可复核的工作

1. [依赖图敏感度报告](../../results/pion_projection/bounded_score_dependence_sensitivity_20261123_v1/README.md) 给出有条件的图染色 Hoeffding 界、推导、输入假设和示意图。新版本 [bounded block-risk 校准报告](../../results/pion_projection/bounded_block_risk_calibration_20261123_v2/README.md) 补上总错误预算校验、anchor Lipschitz 条件、失败 block 的固定分母定义与替代稳健统计量的边界。
2. [独立 block/anchor receipt 审计](../../results/pion_projection/independent_block_anchor_receipt_audit_20261122/README.md) 核对了已有开发 receipts：100 个 D 配置可按 length-5 规则划成 20 个候选块；独立块数仍是 `NOT_ESTABLISHED`。trajectory 间距 5 和 block bootstrap 都不构成独立性证明。E anchor 只有计划，没有 correlator receipt，因此没有可用 anchor 值或 common-bias 界。
3. [`dependency_graph_bound.py`](dependency_graph_bound.py) 是纯解析 CPU 工具；[对应测试](../../tests/test_pion_dependency_graph_bound.py) 覆盖浓缩项、anchor/score alpha 总预算、失败编码和阈值反解。它不读取物理输入。
4. [`bounded_block_risk_score.py`](bounded_block_risk_score.py) 将每个计划 block 的配对平方误差差和显式成功掩码映射为 bounded score，失败 block 固定记为 `-1`，并按全部 planned block 计算条件 LCB；它不连物理 evaluator，始终返回 `physical_score=null`。测试见 [`test_pion_bounded_block_risk_score.py`](../../tests/test_pion_bounded_block_risk_score.py)。
5. [合成校准压力网格](../../results/pion_projection/bounded_block_risk_stress_20261123_v2/README.md) 横扫 `N, chi, alpha_s, alpha_A, B/R, failure_fraction, delta_star/R^2` 的 1,728 个情景，并输出分母表、失败/依赖/anchor 热图和 alpha 分配图。严格边界 `m_required >= 1` 被标成 `ABSTAIN`，没有裁剪成可行；这里的 “valid scenario” 仅指数学上可达，不是观测有效或物理认证。
6. [框架扩展点地图](../../doc/framework_extensibility.md) 总结 LatticeArena 可复用的 task/operator、measurement capability、search、score、state、ledger、artifact 接口及目前缺少的跨 task 集成层。
7. [bounded block-risk v1 合同草案](bounded_block_risk_contract_v1.md) 将 estimand、clipping/failure 变换、条件浓缩式、anchor Lipschitz 修正和缺失输入整理为独立版本化 handoff；所有需研究者冻结的物理与推断字段仍为 `null`，不会给出物理分数。
8. [v1/v2 Markov pseudo-gap reports](../../results/pion_projection/bounded_block_risk_markov_gap_20261124_v1/README.md) are retained as historical artifacts; their displayed Bernstein constants match the corrected statement, but their original theorem citation was stale. The current [v3 report](../../results/pion_projection/bounded_block_risk_markov_gap_20261124_v3/README.md) cites Paulin arXiv v5 Theorem 3.11 / Eq. (3.25), flags the author's correction to an incomplete earlier proof, and implements the Proposition 3.15 / Eq. (3.29) initial-law TV correction. It adds a 12-cell burn-in/TV what-if table and three fixed helper fixtures. The implemented route requires one fixed score function across blocks; Paulin Eq. (3.26) covers time-varying `f_i` with extra `V_sum` and `M/k_ps` terms, but this code does not implement that route. No report estimates the actual block-chain gap, post-burn-in TV, coverage, or physical score.
9. [合同结构检查器与报告](../../results/pion_projection/bounded_block_risk_contract_diagnostic_20261124_v6/README.md) 为当前 `DRAFT_NOT_READY` 评分草案提供 machine-readable JSON 与 fail-closed inspector。它检查图染色 Hoeffding 或固定-score Markov pseudo-gap 路线、stationary 起点或带 receipt 的 post-burn-in TV、`F*delta < alpha_score`、anchor 覆盖方法、总误差界 `B` 与共偏差子界 `C<=B`、`B >= random_coverage_radius + C`、`R` 与预测差界及独立 reference gate。合成的 Markov stationary/TV 形状只返回 `CONTRACT_COMPLETE_REQUIRES_HUMAN_REVIEW`；收据内容仍须人工审核。测试见 [`test_pion_bounded_block_risk_contract.py`](../../tests/test_pion_bounded_block_risk_contract.py)。

![依赖图染色与 block 数敏感度](../../results/pion_projection/bounded_block_risk_calibration_20261123_v2/dependence_sensitivity.png)

图中 `N=20`、`F=2`、`alpha_total=alpha_s=0.05`、`alpha_A=0`、无 anchor 偏差/阈值/失败只是乐观 what-if。色数界 `chi=1,2,3` 对应惩罚约 `0.607, 0.859, 1.052`；后者已超过 `[-1,1]` score 能达到的最大均值。该图没有估计实际 `chi` 或效果。

新增压力图将每个输入组合作为一个 planned synthetic scenario；1,728 个情景中 1,132 个数学上有可达均值、596 个因 `m_required >= 1` 应 `ABSTAIN`。场景加权的假设 block 汇总是 planned/valid/failed/abstained = `299520/269568/29952/0`；这些是假设分母，不是新的测量样本，也不代表独立块。测试覆盖严格等于 1 的边界与全 planned blocks 失败时的 abstention。

### 已知有限依赖图下的 Monte Carlo 覆盖诊断（合成，见 v2）

[Conditional coverage report](../../results/pion_projection/bounded_block_risk_coverage_mc_20261123_v2/README.md) 补上解析可行性网格没有回答的方法学问题：若依赖图已知，graph-color LCB 在有限样本下的覆盖/保守性，与错误使用 IID 惩罚相比如何。30 个 cell 横扫 `N={32,128,512}`、真实依赖范围 `m={0,1,3,7,15}`、失败率 `{0,0.1}`；每格 5,000 次 MC，`F=2`、`alpha_s=0.05`。有效 score 是 `0.2 + 0.8 tanh` 的对称滑窗噪声；`m+1` 个同余类使用互不重叠的高斯创新，故本合成过程的依赖图与色数界 `chi=m+1` 已知。paired failure mask 在两个 score family 间共享，失败 block 保留在 planned `N` 并编码为 `-1`。

![已知依赖范围下的家族覆盖率](../../results/pion_projection/bounded_block_risk_coverage_mc_20261123_v2/coverage_by_dependence.png)

正确 `chi=m+1` 的 graph-color LCB 在全部 30 个 cell 的实测 familywise coverage 均为 `1.0`（每格 5,000 次；最小 MC 95% Wilson 下界约 `0.9992`）。故意错误地用 `chi=1` 时，最差 cell `N=512,m=15,phi=0` 的 coverage 为 `0.8362`，MC 95% 区间约 `[0.8257,0.8462]`。这验证的是**已知合成 m-dependence**下公式的条件行为，绝不证明项目真实 `chi`。

![覆盖保证与正下界通过率的保守性权衡](../../results/pion_projection/bounded_block_risk_coverage_mc_20261123_v2/positive_certificate_rate.png)

graph-color LCB 在高 `m` 下虽保持覆盖，正下界通过率也可能降至 0（例如该模拟中 `m=15`），说明有限样本有效性与有用检出率是两项不同性质。MC denominator 分层保存：30/30 simulation cell 有效、150,000/150,000 replicate 完成；paired planned block events `33,600,000` 中 `1,679,993` 个假设失败并编码为最差分数，未删除。所有 replicate 下界/覆盖指示、种子规则、源快照和 SHA-256 都在报告目录。

此实验不含 anchor error（`alpha_A=0`）、不估计效应分布、没有物理阈值，并且用可证明的创新构造直接给定依赖图；真实流程仍须先证明 score-specific 图或带常数的 mixing bound。`IID`/`graph-color` 模拟差异不能用来替代那项证明，也不能把剪裁后 estimand 换回 ensemble-risk。

### 有限样本共同覆盖：依赖分数 + 独立 anchor（合成，见 v1）

[联合校准报告](../../results/pion_projection/bounded_block_risk_anchor_coverage_mc_20261123_v1/README.md) 补上上一版 `alpha_A=0` 的方法学缺口。16 个 cell 横扫 `N={128,512}`、已知依赖范围 `m={0,15}`、假设失败率 `{0,0.1}`、独立 anchor 样本数 `n_A={32,128}`；每 cell 5,000 个 replicate，共 80,000。`F=2` 的 score 误差预算为 `alpha_s=0.04`，anchor 双侧精确正态区间预算为 `alpha_A=0.01`，总计 `alpha_total=0.05`。score 生成器用已知 `m` 的滑窗高斯创新，anchor 误差与 score 独立；anchor 的 `sigma=0.05` 已知。这些都是明确的合成假设，不是从项目数据估得的参数。

![依赖分数与共享 anchor 的联合覆盖诊断](../../results/pion_projection/bounded_block_risk_anchor_coverage_mc_20261123_v1/coverage_and_utility.png)

在该生成器下，正确 `chi=m+1` 的 graph-color 规则 16/16 cell 均观测到零 false certificate；每格 5,000 次对应的最大 Monte Carlo 95% Wilson 上界为 `0.000768`。故意用 IID `chi=1` 时，最大误认证率为 `11.0%`（`N=128,m=15,phi=0,n_A=128`）；anchor 区间实测覆盖率跨 cell 为 `98.92%–99.22%`，标称 99%。图左下的正证书率展示效用损失：`N=512,m=0,phi=0,n_A=128` 为 `97.74%`，而 `m=15` 时为 0。零观测误认证只是有限次模拟结果，不是实际数据覆盖证明；正证书阈值 0 也只是演示值。

每 cell 保存分层分母：MC replicate、paired block event、family-block score、anchor estimate 和 anchor observation 的 planned/valid/failed/abstained 数。假设失败 block 留在计划分母并记 `-1`；all-failed replicate abstain。源码、随机种子、replicate 级结果、图、协议和哈希随报告保存。此诊断只验证**已知依赖图、独立且已知方差正态 anchor**下的联合校准路径；不估计真实 `chi`、anchor 覆盖、共同偏差、目标质量/物理效应，也不满足 reference gate。任务仍为 `NOT_READY/UNCERTIFIED`，`physical_score=null`，封存数据未访问。

### Anchor 分布稳健性：正态 z 区间 vs 有界样本 Hoeffding 区间（精确合成枚举）

[精确 coverage 报告](../../results/pion_projection/bounded_block_risk_anchor_robustness_exact_20261123_v1/README.md)补查前一项的正态模型假设。对三个均值为 0、方差同为 `sigma^2=0.05^2` 的二点分布（稀有上侧事件概率 `p={0.5,0.1,0.005}`）及 `n_A={16,32,128,512}`，枚举每格 `n_A+1` 个二项计数状态及其精确概率，不使用 Monte Carlo，也不读取 anchor/物理数据。

![有界非正态 anchor 的精确区间覆盖与宽度权衡](../../results/pion_projection/bounded_block_risk_anchor_robustness_exact_20261123_v1/coverage_and_radius_cost.png)

比较的正态 z 半径 `B_z=z_(1-alpha_A/2)*sigma/sqrt(n_A)` 使用生成器的 oracle 方差，但其 99% coverage 解释要求正态母体；有界独立样本 Hoeffding 半径为 `B_H=(U-L)*sqrt(log(2/alpha_A)/(2*n_A))`。稀有事件 case `p=0.005,n_A=16` 的 exact z coverage 只有 `92.2931%`，而 Hoeffding exact coverage 为 `99.9999999999%`；12 格内 Hoeffding 的最小 exact coverage 为 `99.8767%`，最大宽度代价 `B_H/B_z=8.959`。这说明可用分布无关界换覆盖保证，但 `2B/R` 可能变得很宽；它不证明项目 anchor 的支持范围或 iid 条件。

分母报告明确区分 2,064 个假设 anchor observations 与 2,076 个 exact count states；均为精确枚举的合成规划数量，不是物理样本或 MC replicates。Hoeffding 路径只有在 anchor observations 的独立性和事前已知有限支持均可证明时可用；支持未知、anchor 有系统偏差或配置间相关时，这个界不能认证。当前仍缺 E-anchor receipt、共同偏差界及其与 score 样本的独立性证据。正态和 Hoeffding 两条路都不能替代 reference gate；状态继续为 `NOT_READY/UNCERTIFIED`，`physical_score=null`。

### Planned-block 评分函数合同测试（CPU；未接入 evaluator）

`conditional_block_risk_lcb` 的数据流是：`D_i(A)=(A-y_ref)^2-(A-y_candidate)^2` → 对有效 block 计算 `clip(D_i/R^2,-1,1)` → 失败 block 记 `-1` → 以完整 planned `N` 计算均值与 graph-color LCB。四块测试例的原始差为 `[8,-8,2,NaN]`、`R=2`、掩码为 `[valid,valid,valid,failed]`，因此 bounded scores 为 `[1,-1,0.5,-1]`；block 分母 planned/valid/failed/abstained=`4/3/1/0`，单个比较结果的分母=`1/1/0/0`。全失败时 block 分母=`2/0/2/0`，单个比较结果分母=`1/0/0/1`，状态为 `ABSTAIN_NO_VALID_BLOCKS` 且不输出 LCB。这样区分了 block failure 与 panel-level abstention。

函数只实现合同算术；`chi`、anchor 覆盖和 `|y_candidate-y_reference|<=R` 都是调用方必须提供的条件，代码不会验证它们。函数对所有调用固定返回 `physical_score=null`；这项测试不访问任何 correlator/ensemble，也不证明依赖结构、anchor 或物理 reference。

### 颜色类 empirical-Bernstein 备选界（合成条件诊断，新增）

为判断 Hoeffding 是否能在低方差时减少保守性，增加了 [`bounded_block_risk_empirical_bernstein.py`](bounded_block_risk_empirical_bernstein.py) 和 [30-cell 对照报告](../../results/pion_projection/bounded_block_risk_empirical_bernstein_20261123_v4/README.md)。对事前固定的 dependency-graph coloring，在每个颜色类内应用 Maurer–Pontil Theorem 11 的有界独立样本 empirical-Bernstein 界，再以 `n_c/N` 加权；候选族与 `chi` 个颜色类用 `alpha_s/(F*chi)` 做 Bonferroni。颜色类只有一个 block 时退回 Hoeffding。原论文定理允许独立但不同分布的变量；仍要求类内联合独立，方差自适应不能推断或修复错误依赖图。

沿用已知 `m`-dependent 合成生成器，30 格、每格 5,000 个 paired replicate，graph-color Hoeffding 与 empirical-Bernstein 实测 familywise coverage 都是 `1.0`；每格 Wilson Monte Carlo 95% 下界最小 `0.9992`。功效并未普遍改善：`N=512, phi=0, m=0` 的正 LCB 率仅由 `0.9996` 到 `1.0000`；`m=1` 则由 `0.6994` 降为 `0.3550`；`m>=3` 两者接近零，EB 不优。颜色数增大后类样本缩小，EB 的加性项主导。全网格 replicate planned/valid/failed/abstained=`150000/150000/0/0`；失败 block 留在计划分母并记 `-1`。

因此目前保留 graph-color Hoeffding 作为主校准路线，只把 empirical-Bernstein 留作有已证明着色且颜色类足够大时的敏感度选项。该结果不证明真实图、anchor 覆盖、支持范围、common-bias 或物理目标；没有图色数来源时两者都必须 abstain。函数测试见 [`test_pion_bounded_block_risk_empirical_bernstein.py`](../../tests/test_pion_bounded_block_risk_empirical_bernstein.py)；图、分母、源码快照和 hash 在报告目录。

### Markov block-chain pseudo-spectral-gap 备选界（解析敏感度，新增）

[v3 敏感度报告](../../results/pion_projection/bounded_block_risk_markov_gap_20261124_v3/README.md)依据 Paulin 的 corrected arXiv v5 Theorem 3.11 / Eq. (3.25) 实现 non-reversible Markov-chain Bernstein 路径。把一个预先固定、非重叠的 score block 作为 block-chain 状态；依 Assumption 3.1，该齐次链需为 `phi`-irreducible、aperiodic、state space 为 Polish 且有唯一 stationary law，定理主体针对 stationary chain。对 `Z_i in [-1,1]` 可取 `C=2`、`V_f<=1`。令 `L=log(2F/alpha_s)`，用 worst-case `V_f=1` 解定理指数，得到

```text
epsilon_ps = [20*C*L + sqrt((20*C*L)^2 + 32*gamma_ps*L*(N + 1/gamma_ps)*V_f)] / (2*gamma_ps*N)
```

再以 `LCB = zbar - epsilon_ps - 2B/R` 接入现有 squared-error anchor correction；`alpha_s/alpha_A` 和原物理 reference gate 仍独立保留。这里必须用 block chain 自身的、可审阅的 `gamma_ps` 正下界；采样间隔、block bootstrap 或 empirical ESS 都不能替代。初始分布非 stationary 时还须单独加入 burn-in/初始律修正。全失败的 panel 继续按当前 helper 规则 abstain。

图比较 `N={20,50,100,200,500}` 与假设 `gamma_ps={0.005,...,1}`，固定 illustrative `F=2, alpha_s=0.05`，并以 `chi={1,2,4}` graph-color Hoeffding 惩罚作不同假设下的背景。scenario 分母 planned/valid/failed/abstained=`40/2/0/38`；valid 仅指在假设全部成立且所有样本分数取最大值 1 时，零阈值 LCB 才数学上可达。physical block-score 分母 `0/0/0/0`，没有测量。`N=20,gamma_ps=1` 的最优乐观半径仍为 `8.969`；`N=500,gamma_ps=1` 为 `0.493`。这是定理与 worst-case range term 的保守度，不是项目 mixing rate 或功效估计。

**来源支持的内容：**Paulin 当前 arXiv v5 的 Assumption 3.1 列出齐次、`phi`-irreducible、aperiodic、Polish state space 和唯一 stationary law；Theorem 3.11 / Eq. (3.25) 对 stationary chain 的同一固定 `f` 给出 pseudo-gap Bernstein 界，Proposition 3.15 / Eq. (3.29) 给出初始 law TV 扰动。作者说明此前版本（包括发表版）的一般状态 Bernstein 证明论证不完整，v5 作了修正。原文也给出时间变化的 `f_i` 路线 Eq. (3.26)，分母含 `V_sum` 和额外 `M/k_ps`，本 helper 未实现。见[原文](https://arxiv.org/html/1212.2015v5)。**本项目推论：**只有一个固定 score 函数应用于 block-chain 状态，且 receipts 支持链假设，才进入当前实现；若每块的函数改变，当前 inspector/helper 必须拒绝或 abstain，后续需另建 Eq. (3.26) 合同。

**初始分布修正：**设 burn-in 后第一个 scored state 的 law `q_t` 满足 receipt 所支持的 `d_TV(q_t,pi)<=delta`。Prop. 3.15 Eq. (3.29) 使每个比较的事件概率额外至多 `delta`；`F` 个比较占用 `F*delta`，要求 `F*delta<alpha_s`，剩余 stationary score alpha 为 `alpha_s-F*delta`。score 在 `[-1,1]` 时，helper 对 operational finite-plan mean 再保守扣除 `2delta`。v6 contract inspector 已要求 stationary 模式的 `burn_in_blocks=0, delta=0` 或 post-burn-in TV、receipt 与 alpha 条件；它不验证 receipt 真伪。项目仍无 burn-in/TV receipt，不能用任意示意值替代。

## 可审阅的 estimand 与校准合同草案

令 `D_i(A)` 为预先限定的配对平方误差差，并定义 `Z_i=clip(D_i(A)/R^2,-1,1)`。bounded block-risk 是有限计划的 `theta_N=(1/N) sum_i E[Z_i | protocol, anchor]`；若有平稳性可简化为共同期望，但有界浓缩推导本身不要求同分布。它只针对这个 block 级 estimand，不替代 ensemble-risk 或物理真值。剪裁界限和剪裁前后的解释必须在看确认数据前冻结，因为 clipping 会改变 estimand。

若 planned block 数为 `N`，候选确认族为 `F`，score dependency graph 的一个可证明色数上界为 `chi`，且每个颜色类内部的 block score 在给定共享 anchor/protocol 后联合独立，则单侧惩罚为

```text
epsilon = sqrt(2 * chi * log(F / alpha_s) / N)
```

失败 block 不删除：记 planned 样本失败比例为 `phi_hat`，有效块观测均值为 `zbar_valid`，并把每个失败编码成最差改善 `-1`，则 `zbar=(1-phi_hat)*zbar_valid-phi_hat`。浓缩项仍使用全部 planned `N`，图也必须包含失败状态。若这类失败编码不符合科学问题，应改成单独、事前定义的 failure-augmented estimand，而不能只分析成功样本。

对平方误差差 `D(A)=(A-y_ref)^2-(A-y_candidate)^2`，有精确恒等式

```text
D(A)-D(m*) = 2 (A-m*) (y_candidate-y_ref)
```

所以 `|A-m*|<=B` 只能推出 `2B/R` 归一化偏差项，前提是预测差事前满足 `|y_candidate-y_ref|<=R`，且实际评分只有该平方误差差项。若加入拟合不确定性、方差惩罚或其他非线性组件，需逐项推导 Lipschitz 上界；不允许自动沿用 `2B/R`。

总不覆盖率须预先拆成 score 误差 `alpha_s` 与 anchor 覆盖误差 `alpha_A`，校准 API 要求显式传入全部 alpha 且检查 `alpha_s + alpha_A <= alpha_total`，避免把图示默认值误当物理设定。相应 lower bound 和规划边界为

```text
LCB/R^2 = zbar - epsilon - 2B/R
zbar_valid > (delta_star/R^2 + epsilon + 2B/R + phi_hat) / (1-phi_hat)
```

报告中的 `alpha_total=0.05, alpha_A=0` 仅是依赖图敏感度图的乐观演示，不是用户冻结的校准值。`N/chi` 只是代数记号，不是估计的 ESS。

块有界可阻止极端观测支配 Hoeffding 项，但剪裁不制造独立性。Paired block bootstrap、HAC/ESS、median-of-means 可作为敏感度检查；如果依赖结构/混合率未获证明，它们不能单独认证有限样本覆盖。trajectory 间距、RHS 数和 bootstrap 重抽样都不能当作独立 block 数。

## 下一位 agent 的工作顺序

1. **版本化评分合同及结构检查器已整理**：人类可读草案见 [`bounded_block_risk_contract_v1.md`](bounded_block_risk_contract_v1.md)，当前 null JSON 为 [`bounded_block_risk_contract_v1.json`](bounded_block_risk_contract_v1.json)，检查器见 [`bounded_block_risk_contract.py`](bounded_block_risk_contract.py)。下一步仍需研究者冻结 `m*` 单位/范围、`R`、剪裁函数、失败编码、目标 `delta_star`、`F` 和总 alpha 分配；现阶段不从 toy 或开发误差反推物理阈值。
2. **合成规划/覆盖诊断已完成：**1,728 点解析可行性网格、30-cell 已知 `m`-dependence MC、16-cell 共同 score+anchor MC、12-cell exact anchor-distribution 枚举，以及 30-cell color-class empirical-Bernstein vs graph-Hoeffding MC 均有图/表、明确分母和可复现输入。它们只检验已知合成图、正态或有界 iid anchor 条件下的公式/效用；不估计真实覆盖、支持或依赖。经验方差界没有显示对高色数网格的普遍功效改进，故不替代 Hoeffding 基线。
3. **替代理论界已具体化，评分 helper 与结构门已接通，但项目依赖证据仍未完成：**下一位 agent 若获得授权，只能先核对未封存 receipt 是否证实固定 score block map、齐次链假设、block-chain `gamma_ps` lower bound，以及 stationary-start receipt 或 post-burn-in TV receipt；同时核对 `F*delta<alpha_s` 与 anchor 条件/联合界。不要读取封存 E/gap/validation/holdout，也不得用 trajectory spacing、bootstrap 或 ESS 替代这些证据。时变 `f_i` 目前未实现，不能走当前 Markov helper；需要新增、独立审查 Eq. (3.26) 的 `k_ps/V_sum/M` 合同和算术测试。没有 review 通过的 graph `chi` 或 Markov gap/initial-law 证据时保持 `ABSTAIN/NOT_READY`。
4. anchor 路径需要独立、匹配的 E correlator receipt，以及总误差界 `B` 的来源、显式 common-bias 子界 `C<=B`、两者的合并规则和与 score 样本的条件独立说明。v1 保守结构要求 `B >= random_coverage_radius + C`：正态区间需支持正态/已知方差；Hoeffding 需事前证明有限支持和 iid anchor 单位。两者都要给 coverage receipt，并报告 `2B/R` 的效用代价。多个待覆盖 anchor 时事前分配 `alpha_A`；同一个共享 anchor 供候选族复用不因 `F` 自动重复分配。现有 `n_A/sigma/alpha_A` 仅为合成设计值；尚无此证据时不要读取封存 E/gap/validation/holdout。
5. 通过独立审阅并获数据授权后，才进行确认测量；冻结候选族后报告全量 paired block 原始 score、planned/valid/failed/abstained、剪裁前后诊断、图色数来源、alpha 分配和 `LCB`。即使统计门通过，也必须单独通过原先失败的 reference/model-identification gate 才能产生物理分数。

停止规则：没有可审阅的 dependence bound、anchor bias 覆盖界或通过的物理 reference 时，输出 `ABSTAIN/NOT_READY` 并保持 `physical_score=null`；不以更窄的 bootstrap 区间代替缺失假设。

## 2026-11-24 本轮复核记录

- 对 Pion 依赖图、bounded block-risk、anchor 稳健性与经验 Bernstein 的 7 个 CPU 测试模块重跑：**54 passed**。这是公式/实现与合成诊断的验证，不是物理校准或 coverage 证明。
- 当前 PR #5 中，7 份已跟踪报告 manifest 的 **60 个**文件哈希全部匹配；三份 task TODO 中的 26 个本地 Markdown 引用均解析到已跟踪文件；三份 TODO 的 21 个 GitHub commit URLs 已通过 GitHub Git-tree API 核对，所有目标存在；7 个 README 文件的 /tree/ 链接已更正为 /blob/。
- 未读取封存 E/gap/validation/holdout，也未做 GPU/QUDA 测量；NOT_READY/UNCERTIFIED 与 physical_score=null 保持不变。
- 下一步仍需研究者提供 score-specific dependence receipt（或 block-chain gamma_ps 下界）、独立 anchor/common-bias 覆盖依据及物理 reference；没有这些证据时，后续 agent 应停止在 ABSTAIN/NOT_READY，不要重跑相同合成网格来替代缺失输入。

## 2026-11-24 跨任务复核同步

- companion PR #6 新增 Optimize degree-4 Chebyshev 系数在连续区间 `[-1,1]` 上的正性诊断，含报告图、区间最小值表、协议、分母和哈希；结果仅针对三个 synthetic fit，不能作为任意配置或物理算符的 PSD 证明。
- PR #6 源码/测试提交 `f25acababd490729328af1189a5934f56bde7f89` 上，9 个 Optimize/Wilson 专项 CPU 测试模块共 **65 passed**；后续报告提交为 `337bc99b87952c4c866c6f55ea000427c00273b5`。这不是完整仓库测试，也未运行 GPU/QUDA。
- 在后续 v5 inspector 与 Markov LCB follow-up 之前，复核 PR #5 的 Pion 报告为 7 个 tracked manifest / 60 个 payload 文件，PR #6 的 Optimize/Wilson 合计 10 个 manifest / 70 个 payload 文件，所有 SHA-256 匹配；三份 TODO 中 26 个相对链接均解析，28 个 GitHub commit/tree 链接均解析，带文件路径的目标均存在。
- Pion 的 bounded block-risk 合同及其 `NOT_READY/UNCERTIFIED`、`physical_score=null` 状态没有变化；仍需 score-specific dependence receipt（或 block-chain `gamma_ps` 下界）、独立 anchor/common-bias 覆盖证据和物理 reference。未读取 sealed 输入。

## 2026-11-24 Pion contract inspector follow-up

- 增加 machine-readable null contract 和纯结构检查器；`graph_color_hoeffding` 与 `markov_pseudo_gap_bernstein` 两个条件路线都能进入结构完整分支，但输出仅为 `CONTRACT_COMPLETE_REQUIRES_HUMAN_REVIEW`，始终 `certified=false`、`physical_score=null`、`data_access=none`。
- 检查器要求 anchor 的 total error bound `B`、common-bias 子界 `C<=B`、合并规则及各自 receipt；并按 normal/Hoeffding 路线检查已知 sigma/分布假设或有限支持/iid 单位字段。v5 进一步计算相应随机覆盖半径，并要求 `B >= random_coverage_radius + C`。当前合同所有物理与证据输入仍为 null。
- 合成报告为 6 个合同形状检查，planned/valid/failed/abstained=`6/2/4/0`；valid 只表示字段形状完整。v5 inspector 13 项测试通过；合计 8 个 Pion bounded-risk/dependence 专项模块 **67 passed**。
- 当前未访问 E/gap/validation/holdout、未运行 GPU/QUDA。真实 dependence receipt、anchor 覆盖/共偏差证据、`m*`/`R`/阈值与独立 reference 仍是外部输入；本诊断不关闭 Pion 物理门。
- 截至 v5 contract diagnostic 的当时复核，9 份 tracked Pion report manifest / 74 个 payload 文件通过 SHA-256；三份 TODO 的 34 个相对链接均解析到 tracked 文件，28 个 GitHub commit/tree 链接跨 7 个 commit tree 均有目标。该项保留为历史快照；当前报告/链接数量见下方 Markov LCB follow-up。

## 2026-11-24 Markov LCB software integration follow-up

- 将 `conditional_block_risk_markov_lcb` 接入 corrected Theorem 3.11；完整 planned block 数进入 Bernstein 半径与均值；有效 block 先按 `R^2` 缩放并裁剪至 `[-1,1]`，失败 block 记为 `-1`；all-failed panel abstain。helper 明确 anchor 条件假设，并实现 burn-in 后 initial-law TV 的 `F*delta` 概率预算和 `2*delta` finite-plan mean shift；始终 `certified=false`、`data_access=none`、`physical_score=null`。
- 新增 [v3 文字/图报告](../../results/pion_projection/bounded_block_risk_markov_gap_20261124_v3/README.md)：校正 theorem version/citation，保留旧报告及其历史 source snapshots，新增 12-cell TV 敏感度图/表、protocol、源码快照、哈希和三种 helper fixtures。synthetic comparison 分母=`3/2/0/1`，block-slot 分母=`10/6/4/0`；这些是固定输入算术，不检验理论覆盖率，也不提供项目 gap、TV 或 anchor 证据。
- [`test_pion_bounded_block_risk_markov_score.py`](../../tests/test_pion_bounded_block_risk_markov_score.py) 有 18 项测试，覆盖 corrected radius、TV 概率预算及均值修正、失败编码、全失败 abstention、anchor/fixed-score 条件说明和不合法输入。
- 实际 `gamma_ps` lower-bound receipt、score-specific Markov/stationarity 条件、anchor 覆盖/共偏差、用户冻结阈值和独立物理 reference 仍缺；不访问 sealed 数据、不运行 GPU/QUDA，状态不变。
- 本轮 Pion 相关 CPU suite 与报告/链接复核结果更新见下方最新记录；当前 Markov v3、contract v6 和测试文件需一起纳入 PR #5。

## 2026-11-24 Markov theorem-contract closure

- 按 arXiv v5 原文补齐合同边界：Markov route 必须声明固定 score function；要求 stationary initial law（zero burn-in/zero TV）或带 receipt 的 post-burn-in TV bound，并对 `F*delta < alpha_score` fail closed。测试 fixture 覆盖缺 receipt、alpha 被 TV 用尽、时变 score function 三类失败。
- contract v6 文本诊断共 10 个结构 fixture：planned/valid/failed/abstained=`10/3/7/0`；stationary 与 post-burn-in TV synthetic shape 均标为须人工审阅，物理输入仍 null。Markov v3 报告保留固定函数限制，并将 Paulin Eq. (3.26) 时变函数路线列为未来可实现项：需 `k_ps`、`V_sum`、逐项范围和 `M` 上界合同；当前不接受它。
- Markov LCB 测试新增 theorem exponent 独立代数核对及 malformed-input fail-closed 检查；生成的两张敏感度图只使用固定分析网格。最终复核：9 个 Pion bounded-risk/dependence CPU test modules 为 **93 passed**；12 份已跟踪 Pion report manifest 覆盖 99 个 payload 文件，SHA-256 全匹配；三份 task TODO 的 43 个相对 Markdown 链接均指向 tracked 文件；`git diff --check` 通过。旧的 28 个 GitHub commit/tree 链接未在本轮更改，仍沿用前一轮已通过 Git-tree API 的检查结果。
