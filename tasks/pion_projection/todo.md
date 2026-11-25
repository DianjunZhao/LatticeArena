# Pion projection: bounded block-risk calibration handoff

## 2026-11-25 我自行选定的 bounded block-risk 输入

用户已要求我自行给出方法输入。以下是可以直接作为下一版方案默认值的选择，**不是测量结果、收据或外部授权**。本节覆盖前文“等待用户选择 target、R、clipping、delta_star”的候选问题；经验量和状态仍按下文的封存/未认证规则处理。

| 输入 | 我选定的值 | 性质与理由 |
|---|---|---|
| 目标 | `m* = a_t m_{pi,0}`，S16T16 quenched Wilson ensemble、`kappa=0.14`、零动量、最低质量 valence isovector pseudoscalar 能级 | 目标定义取自 [Pion task specification](../../doc/pion_projection.md)；数值必须由独立 anchor 得到，不能从当前失败的单-cosh pilot 填入 |
| anchor/reference | 独立 E-chain 上的 candidate-blind 联合谱拟合：PP 的 `n=0,8,16` 三通道加局域 A4P；共享两态能量、各通道独立振幅，拟合 `t=3..8`，比较 `t_min=2,3,4` 及二态/三态模型；PP 偶折、A4P 奇折 | 这是新的参考协议选择；它不复用候选调参结果。协方差仍用冻结的 25% diagonal shrinkage 与 `1e-10` 特征值地板。通过门：`m0` 相对误差≤5%、拟合 `p>=0.01`、模型/窗口质量位移≤2.5 paired SE、PP/A4P 相容且无边界命中；任何一项失败即 reference unresolved |
| 预测域与归一化 | 两个预测质量都必须落在 `(0.1,3.0)` `a_t m_pi` 内；`R=2.9 a_t m_pi` | 取自当前固定拟合搜索域，只是保证 `|y_candidate-y_reference|<=R` 的合同域，不是物理质量先验 |
| score | `Z_i=clip(D_i/R^2,-1,1)`，其中 `D_i=(A-y_ref)^2-(A-y_candidate)^2`；失败 block 记 `-1`，全失败 comparison abstain | 预先固定 bounded estimand；不再对分数作随 block 变化的重标度 |
| 最小效应 | `delta_star=0.05 R^2=0.4205 (a_t m_pi)^2`；要求 familywise LCB `>0.05` | 把最大归一化损失差的 5% 选作最低有意义改善门槛；这是工程/研究判据，不是由旧 pilot 推出的物理常数 |
| 比较族与显著性 | `F=3`：候选对 local identity、tuned `H^32`、frozen signed-SLSQP；`alpha_total=0.05`, `alpha_score=0.04`, `alpha_anchor=0.01` | 三个比较均固定在 development 选择完成之后的 confirmation family 中；必须在报告里保留每个 comparison 的 planned denominator |
| score 依赖 | 主路选 fixed-score non-reversible block-Markov pseudo-gap Bernstein；block 是连续 5 个配置，固定同一个 score map。设计门槛：`N=4000` 个 scored blocks、`gamma_ps_lower>=0.20`、burn-in 8 blocks 后 `delta_TV<=0.001` | `F*delta=0.003<alpha_score`；按现有实现与剩余 `alpha=0.037` 计算，浓缩半径约 `0.3863`。这说明该证明路线很保守，旧 D receipt 的 20 个 length-5 blocks 远不足以给出非平凡 LCB。数值是下一版设计要求，不是现有 chain 的估计 |
| anchor 覆盖 | 选 bounded-IID Hoeffding：`n_A=1000` 个独立 stationary anchor 单位、每个输出限制在 `[0.1,3.0]`、双侧 `alpha_A=0.01` | 随机覆盖半径 `R*sqrt(log(2/alpha_A)/(2*n_A))=0.1493 a_t m_pi=0.05147R`；common-bias 预算定为 `C<=0.01R=0.029`，故 `B=radius+C<=0.1783 a_t m_pi=0.06147R`，score anchor correction `2B/R<=0.12294`。独立性、stationarity 和 C 上界都必须有单独收据；没有这些条件就不能调用 Hoeffding |

已有依赖敏感度和 coverage 模拟固定了 `F=2`，因此仍然只是旧方法的合成诊断；它们不能代替这里选定的 `F=3` 实际比较族。实现下一版时先按 `F=3` 重新生成纯公式敏感度和文字流程，不能把旧 `F=2` 覆盖率数字搬到项目合同。

**目前不能由我填造的证据：**实际 `m*` 数值、Markov chain 的 `gamma_ps` 下界、8-block 后 TV 界、1000 个独立 anchor 单位、common-bias `C` 证据和 E-chain correlator receipt。旧的 D0–99 receipt 只对应 20 个长度 5 的候选块，既不证明独立性也不支持上述覆盖。现有 S16T16 reference gate 已失败；所以这些设计数值不能把状态升级为 `READY`，合同的物理数据收据保持缺失，`physical_score=null`，sealed E/gap/validation/holdout 继续关闭。

文字流程：`独立 candidate-blind E 谱拟合 -> 通过 reference/model gate -> 单一 bounded score map 与三比较族 -> 证明 block-Markov gamma/TV -> 独立 anchor 的 99% Hoeffding 半径 + C -> 对完整 N=4000 计划块计算 LCB -> LCB>0.05 且所有门通过才可申请新 confirmation；否则 ABSTAIN`。

**交接规则：**本文件下方较早的“等待用户选择 target/R/clipping/delta_star”均为历史记录，现由本节默认值覆盖；不要再次向用户询问这些方法参数。下一位 agent 应把可冻结的方案字段写入 machine-readable contract，并按 `F=3` 生成新的纯分析半径图/表和文字数据流；`gamma_ps`、TV、anchor、C 与 reference 收据继续留空，合同仍应 `NOT_READY`。不要读取封存 split 或把 synthetic fixture 升格为实测证据。

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
8. [v1/v2 Markov pseudo-gap reports](../../results/pion_projection/bounded_block_risk_markov_gap_20261124_v1/README.md) are retained as historical artifacts; their displayed Bernstein constants match the corrected statement, but their original theorem citation was stale. The [v3 report](../../results/pion_projection/bounded_block_risk_markov_gap_20261124_v3/README.md) cites Paulin arXiv v5 Theorem 3.11 / Eq. (3.25), flags the author's correction to an incomplete earlier proof, and implements the Proposition 3.15 / Eq. (3.29) initial-law TV correction. It adds a 12-cell burn-in/TV what-if table and three fixed helper fixtures. That v3 implementation supported one fixed score function across blocks; the optional time-varying Eq. (3.26) route is now separately implemented and documented below. No report estimates the actual block-chain gap, post-burn-in TV, coverage, or physical score.
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

**来源支持的内容：**Paulin 当前 arXiv v5 的 Assumption 3.1 列出齐次、`phi`-irreducible、aperiodic、Polish state space 和唯一 stationary law；Theorem 3.11 / Eq. (3.25) 对 stationary chain 的同一固定 `f` 给出 pseudo-gap Bernstein 界，Proposition 3.15 / Eq. (3.29) 给出初始 law TV 扰动。作者说明此前版本（包括发表版）的一般状态 Bernstein 证明论证不完整，v5 作了修正。原文也给出时间变化的 `f_i` 路线 Eq. (3.26)，包含 `V_sum` 与 `M/k_ps`。固定函数与变时函数现由两个分开的 helper/合同分支实现；新的变时分支要求完整 score schedule、最小 maximizer `k_ps`、正的逐余数类方差和上界、anchor-score shift 界及对应 receipts，仍不替用户验证 receipts。见[原文](https://arxiv.org/html/1212.2015v5)。

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
3. **两条 Markov 路线均有独立代码，但项目依赖证据仍未完成：**固定 `f` 用 Eq. (3.25)；预先冻结的时变 `f_i` 用 Eq. (3.26)，并保留 `M/k_ps` 原项。两路均需核验未封存 receipt 是否支持 block-chain 条件、`gamma_ps` lower bound、stationarity 或 post-burn-in TV 修正、以及 anchor 条件/联合界。时变路线另需 `k_ps` 最小 maximizer 证明、每个 residue class 的严格正方差和上界、schedule/variance/anchor-shift receipts。不要读取封存 E/gap/validation/holdout，也不得用 trajectory spacing、bootstrap 或 ESS 替代这些证据。没有 review 通过的 graph `chi` 或 Markov gap/initial-law 证据时保持 `ABSTAIN/NOT_READY`。
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
- contract v6 文本诊断共 10 个结构 fixture：planned/valid/failed/abstained=`10/3/7/0`；stationary 与 post-burn-in TV synthetic shape 均标为须人工审阅，物理输入仍 null。此处为历史快照；下方 v7/varying-score 更新已补 Eq. (3.26) 路线。
- Markov LCB 测试新增 theorem exponent 独立代数核对及 malformed-input fail-closed 检查；生成的两张敏感度图只使用固定分析网格。最终复核：9 个 Pion bounded-risk/dependence CPU test modules 为 **93 passed**；12 份已跟踪 Pion report manifest 覆盖 99 个 payload 文件，SHA-256 全匹配；三份 task TODO 的 43 个相对 Markdown 链接均指向 tracked 文件；`git diff --check` 通过。旧的 28 个 GitHub commit/tree 链接未在本轮更改，仍沿用前一轮已通过 Git-tree API 的检查结果。

## 2026-11-24 Eq. (3.26) time-varying score route

- 原文依据是 [Paulin corrected arXiv v5, Theorem 3.11 / Eq. (3.26), Remark 3.12](https://arxiv.org/html/1212.2015v5)。固定-score 的 Eq. (3.25) helper 保持不变；新增 [`bounded_block_risk_markov_varying.py`](bounded_block_risk_markov_varying.py) 计算变时 `f_i(X_i)` 的 Bernstein 置信半径及条件 LCB。此路线估计 `theta_N=N^-1 sum_i E_pi[f_i(X_i)]`；若 `f_i` 改变了原先的目标/归一化，可能是不同 estimand，必须先由研究者冻结并审阅目标等价性。
- 变时路线使用每个 `k_ps` residue class 的正方差和上界 `V'_r>=V_r`，`V'_sum=ΣV'_r`，`M'=(Σ√V'_r)/min√V'_r`，并在指数中保留 `M'/k_ps`。原文明确称是否能把 `M/k_ps` 替换为 1 尚不确定；实现不作该替换。`k_ps>N`、缺少任何 residue class、零/非有限方差上界、缺 schedule/gap/variance/k_ps/TV/anchor-shift receipt，或 `F*delta>=alpha_score` 都 fail closed。
- [`bounded_block_risk_contract.py`](bounded_block_risk_contract.py) 的 Markov 合同现在区分 fixed-score 与 time-varying score route；变时合同额外需要完整 score schedule receipt、最小 pseudo-gap maximizer `k_ps` 及 receipt、每个 residue class 的严格正方差和上界及 receipt、以及以 normalized score units 表示且至少覆盖现有 paired-loss `2B/R` 的 anchor shift bound 与 receipt。synthetic complete 仍只到 `CONTRACT_COMPLETE_REQUIRES_HUMAN_REVIEW`，并要求人工确认 schedule 是否保留目标 estimand。
- [Eq. (3.26) 图/文字报告](../../results/pion_projection/bounded_block_risk_markov_varying_20261124_v1/README.md) 包含 72 个公式敏感度格、`N={20,100,500}`、`k_ps={1,2,4,8}`、三个假设 pseudo-gap 下界、balanced/imbalanced 方差上界图、TV-alpha 表、部分失败/全失败 fixtures 与 SHA-256。情景分母 planned/valid/failed/abstained=`72/5/0/67`；`valid` 只表示若均值达到最大 1 则有可能超过零阈值。helper fixture 的 block-slot 分母 `20/18/2/0`；全失败比较保留 `4/0/4/0` 并 abstain。没有做 coverage Monte Carlo，因为真实 gap、`k_ps`、方差和 anchor receipts 缺失。
- 更新后的 [contract v7 结构诊断](../../results/pion_projection/bounded_block_risk_contract_diagnostic_20261124_v7/README.md) 有 14 个 synthetic contract fixtures，分母 `14/4/10/0`；新的 Eq. (3.26) 完整形状仍要求人工审阅，缺 schedule receipt、零 class variance 或 anchor shift 低于 `2B/R` 会被拒绝。两份报告均含文本流程图；变时敏感度另有图。物理状态、reference gate、sealed data 与 `physical_score=null` 均未变。
- 本轮 Pion 三个 Markov/contract test modules **62 passed**；完整 `test_pion_bounded_block_risk_*.py` + `test_pion_dependency_graph_bound.py` 专项 suite **116 passed**。合并本次两份新报告后，PR #5 共 14 个 tracked report manifests / 116 个 payload files，PR #6 共 10/70；全部 SHA-256 匹配。三份 TODO 的 47 个相对 Markdown 链接均存在；`git diff --check` 与提交前复核完成。
- **下一步给其他 agent：**不要再实现 Eq. (3.26) 或重跑相同的 72-cell 网格。只在研究者提供并 review 真实 `gamma_ps`/`k_ps`、逐类方差上界、`f_i` schedule、初始 law/TV 和 anchor-score shift receipts 后，比较 Eq. (3.25)/(3.26) 的可用性与功效；同时继续等目标 `m*`/单位/`R`/`delta_star`、独立 anchor/common-bias 证据和 reference gate。缺任一项时保持 `ABSTAIN/NOT_READY`，不得从模拟补值。


## 2026-11-24 Astra 输入审阅：候选端点与授权边界

GPT-6.2-Astra 子代理完成的是只读协议审阅，随后已关闭。它没有数据所有者或集群授权能力；本记录继续服从用户此前的决定：保持 NOT_READY/UNCERTIFIED、physical_score=null，封存 split 不读。

**候选端点（历史草案，不能直接冻结）：**在本机历史审阅分支 codex/continue-research-todos-20261123 的提交 f9603b4 中，protocol_fresh_20261120.json（SHA-256 1568592a9263bc3bbedd2d9c50ad740e307aa02175736f4deb795defccefa5e7）记载拟合域 mass_bounds=[0.1,3.0]、block_length=5、anchor IDs=[0,59]；配套 M2 草案（SHA-256 338e01ce31c22e4d51f89ce1eef60ca16649919e40ee7157d18b541cba2d97d1）将 m0 用格点单位报告。该文件不在 PR #5 当前树中，协议的 target/reference 字段仍为空，所以它只支持“可以把格点单位的 m0 作为待确认候选”；若将 m0 记作 a_t E0，是对时间格距单位的记号映射解释。它不证明端点是 pion 基态质量，也不证明这个区间是物理先验。若用户确认两支模型的预测都必须留在 [0.1,3.0]，当前评分合同里的预测差上界可取 R_pred=3.0−0.1=2.9；这只界定两支预测的最大差，不界定真值 m*、anchor common bias 或独立性，也不能替代用户对 clipping/estimand 的批准。

当前 PR #5 的 receipt 审计仍只支持 100 个 D development 配置可切成 20 个 length-5 候选块；独立块数 NOT_ESTABLISHED。E[0,59] 只是历史计划，没有 correlator/anchor receipt。trajectory spacing 和 block bootstrap 均不能补成独立性证据。

**下一位 agent 的具体工作：**先把上面内容作为待答决策卡，而不是修改 null contract。请研究者确认或改写：(1) endpoint 是否为格点单位 a_t E0，还是另一个 observable；(2) 是否接受 [0.1,3.0] 的预测域和由此得出的 R_pred=2.9；(3) 目标 m*、score clipping 与 delta_star；(4) 提供未封存 D receipt 可支持的 score-specific dependency graph/color bound，或 block-chain gamma_ps、stationarity/post-burn-in TV 和时变 score schedule 收据；(5) 独立匹配 anchor receipt、覆盖方式及 common-bias C 的上界。收到这些后先更新 machine-readable contract 和诊断；不访问封存 E/gap/validation/shared holdout。任一关键收据缺失仍 ABSTAIN。

文字数据流：D correlator 与 block IDs → 冻结预测域/score → 证明 dependency 或 Markov 条件 → 独立 anchor 与 C 界 → 全 planned denominator 的 paired block-risk LCB → reference gate；任一缺口即 ABSTAIN。此轮没有新测量，新增诊断分母 planned/valid/failed/abstained=0/0/0/0。

## 2026-11-24 shared abstention-state follow-up

PR #6 [`710eeb2`](https://github.com/Greyyy-HJC/LatticeArena/commit/710eeb27b5d94de37a646ee52ec743be18894786) extends generic `RunState` with a terminal `abstained` status and a required human-readable reason. A run may move from `not_run` or `draft` to abstained; it cannot silently move from abstained to draft/validated, and `score_or_null()` remains null. This change is on the separate PR #6 branch: the current PR #5 `core/state.py` has not yet incorporated it, and the task-specific Pion evaluator/contract inspector is not connected to `RunState`. Pion's existing `ABSTAIN/NOT_READY` outputs and sealed-data boundary remain unchanged. After the PRs are integrated, a future adapter may record a task-specific no-certificate reason, but it must not mark any stage validated or change the user's `NOT_READY/UNCERTIFIED` and `physical_score=null` decision. The repository-wide `python3 -m pytest -q` run passed **134 tests** on PR #6 head [`710eeb2`](https://github.com/Greyyy-HJC/LatticeArena/commit/710eeb27b5d94de37a646ee52ec743be18894786); this is CPU/software validation, not GPU/MPI physics validation.

文字流程：`missing dependence/anchor/reference evidence -> abstained(reason) terminal -> physical_score=null`; only a new run after reviewed receipts can begin a fresh validation path. This is a status-model extension, not evidence that the Pion dependence or anchor requirements are met.

## 2026-11-24 shared TaskSpec split preflight

PR #6 head [`3b9c772`](https://github.com/Greyyy-HJC/LatticeArena/commit/3b9c77201be97d300dfce98b0c3e0d67dc57146f) strengthens `core.specs.task_spec`: split values must be inclusive integer `[start,end]` ranges, start must not exceed end, names must be nonempty strings, and declared ranges must not overlap. Pion's current development/gap/validation ranges pass this structural preflight. The full repository test suite passed **134 tests** on that head.

文字数据流：`protocol 的 split endpoints -> TaskSpec 检查格式/闭区间/不重叠 -> downstream data loader 再核对实际 IDs 与 protocol hash`。前半段只能排除合同中写明的区间重叠；它不核验文件内容、receipt、独立性、anchor 覆盖或 reference，因此 Pion 的 `NOT_READY/UNCERTIFIED`、`physical_score=null` 与 sealed-data gate 保持不变。

## 2026-11-24 shared ScenarioSpec/RunReceipt handoff

PR #6 head [`f209015`](https://github.com/Greyyy-HJC/LatticeArena/commit/f209015337b08f26e34b733771d56142a5288806) 新增 [`core/receipts.py`](https://github.com/Greyyy-HJC/LatticeArena/blob/f209015337b08f26e34b733771d56142a5288806/core/receipts.py)：`ScenarioSpec` 记录情景单位、假设、seed 与来源哈希；`RunReceipt` 记录按阶段拆分的 planned/valid/failed/abstained/not_run、失败/弃权/未运行原因、报告 payload 哈希和文字数据流。PR #5 纳入相同 API/测试后，Pion 的 [v8 bounded-risk contract report](../../results/pion_projection/bounded_block_risk_contract_diagnostic_20261124_v8/README.md) 成为合同检查消费者：14 个 fixture 为 `14/4/10/0/0`，10 个 blocker 均有原因，receipt 绑定 8 个 payload、外层 manifest 覆盖 9 项且哈希匹配。

另将已保存的 [known-graph coverage MC v2](../../results/pion_projection/bounded_block_risk_coverage_mc_20261123_v2/README.md) 只读包裹为 [shared-receipt overlay v1](../../results/pion_projection/bounded_block_risk_coverage_receipt_20261124_v1/README.md)：没有重跑 150,000 个 replicate；分别保留 scenario cells `30/30/0/0`、replicates `150000/150000/0/0`、paired block events `33600000/31920007/1679993/0` 和 family scores `67200000/63840014/3359986/0`（均按 planned/valid/failed/abstained）。后两种 failed 是预设的 synthetic Bernoulli 失败编码，不是测量失败；reason totals 与失败计数精确相等。receipt 覆盖 18 个 payload，外层 manifest 覆盖 19 项；原 v2 的 10 项 manifest 和报告副本也逐项核验。定向 contract+receipt tests 为 **35 passed**，coverage overlay 的 no-rerun/hash test 为 **1 passed**；当前 PR #5 全仓 suite 为 **164 passed**。

上述两个 saved-report receipt overlay 已在后续完成，见下节；不要重复构建 overlay 或重跑 Monte Carlo/公式网格。

## 2026-11-24 saved score/anchor 与 Eq. (3.26) receipt overlays

- [`joint score/anchor coverage receipt v1`](../../results/pion_projection/bounded_block_risk_anchor_coverage_receipt_20261124_v1/README.md) 只读验证并复制已保存的 80,000-replicate synthetic report，原图和源报告 manifest 保留；未重跑模拟。receipt 将 16 cells、80 cell-by-unit rows 展开为 replicate `80000/80000/0/0`、paired block event `25600000/24321134/1278866/0`、family block score `51200000/48642268/2557732/0`、anchor estimate `80000/80000/0/0`、anchor observation `6400000/6400000/0/0`。后两种 score failure 是假设 Bernoulli 编码，不是测量失败。receipt 绑定 21 个 payload，外层 manifest 覆盖 22 项，源 manifest 11 个 payload 均核验；图显示 synthetic known-graph 的 false-certificate rate 与 IID misspecification 对照，以及假设 known-sigma anchor coverage，不能支持项目 anchor 独立性、common-bias 或真实依赖图。
- [`Eq. (3.26) time-varying Markov receipt v1`](../../results/pion_projection/bounded_block_risk_markov_varying_receipt_20261124_v1/README.md) 只读复制并核验原 10-entry manifest；未重算 72 格公式网格或 coverage MC。receipt 分开记录 analytic cells `72/5/0/67`、TV what-if cells `6/0/0/6`、partial fixture block slots `20/18/2/0` 与 result `1/1/0/0`、all-failed block slots `4/0/4/0` 与 result `1/0/0/1`。它保留 Eq. (3.26) 半径与 `M/k_ps` 图，区分假设方差/gap/TV 输入和失败 fixture；这只是条件公式账本，不证明 theorem assumptions 或 coverage。receipt 绑定 20 个 payload，外层 manifest 覆盖 21 项。
- 两份 overlay 的 README 均有文字数据流，保留原图、源报告与分层分母；receipt `complete` 仅表示 planned 项均被记账，不能解释成物理有效或统计覆盖。anchor 与 Eq. (3.26) no-rerun/hash 定向测试共 **2 passed**；本轮 PR #5 完整 CPU suite 为 **166 passed**。receipt payload/外层/source manifest 核验结果分别为 anchor `21/22/11`、Eq. (3.26) `20/21/10`，SHA-256 全匹配；`git diff --check` 和四份项目说明中的本地相对链接检查通过。报告均保持 `physical_score=null`、sealed data closed。

**下一位 Pion agent 的工作：**CPU 侧已没有可通过重复 synthetic 网格解决的未决项。先让研究者审阅并冻结：目标 endpoint/单位、预测域与 `R`、score clipping 和 `delta_star`、family 与 alpha 分配；再接收未封存 D 数据对应的 score-specific dependency graph/color receipt，或固定/时变 Markov 所需 `gamma_ps`、stationarity/TV、schedule、`k_ps` 与 residue-class variance receipts；此外要有独立 anchor receipt、覆盖方式和 common-bias `C` 上界，以及 independent physical reference。按完整分母运行合同 inspector；缺一项就 `ABSTAIN/NOT_READY`。不得从这些 synthetic overlays 反推候选值、不得打开 sealed E/gap/validation/holdout、不得启动 GPU/QUDA 或把 receipt 完整性当成物理授权。

## 2026-11-24 GPT-6.2-Astra review and support-only Eq. (3.26) route

Astra 的只读结论没有提供可冻结的 Pion 物理输入或外部授权；它不能代替数据/资源 owner。Pion 继续 `NOT_READY/UNCERTIFIED`、`physical_score=null`，不读取 sealed inputs。

为减少对理论最大化点与逐类方差收据的依赖，新增候选 route `markov_time_varying_support_gap_bernstein`，见 [`bounded_block_risk_markov_varying.py`](bounded_block_risk_markov_varying.py) 与 [contract inspector v9](../../results/pion_projection/bounded_block_risk_contract_diagnostic_20261124_v9/README.md)。若所有已编码的时变分数满足 `f_i∈[-1,1]`，则 `Var_pi(f_i)≤1`。独立 gap 下界 `g≤gamma_ps` 给出 `k_ps≤1/g`；实现以输入浮点数的精确有理表示计算保守整数上界 `K=ceil(1/g)`。对任意真 `k_ps`，将每个 residue class 方差上界统一放宽到 `ceil(N/k_ps)`，则 `M/k_ps=1` 且 `V_sum≤k_ps*ceil(N/k_ps)≤N+k_ps−1≤N+K−1`。因此令 `V=N+K−1`、`L=log(2F/alpha_s)`，分数和的保守浓缩半径 `t` 解 `g*t^2−40*L*t−8*L*V=0`，均值半径为 `t/N`。这是条件公式候选，不是 gap 估计；`g`、block-chain 假设和 score schedule 仍须独立验证。

v9 合同诊断为 15 个结构 fixture，planned/valid/failed/abstained=`15/5/10/0`；support-gap synthetic fixture 只表明字段合同能进入 `CONTRACT_COMPLETE_REQUIRES_HUMAN_REVIEW`。定向 Markov/contract tests 为 **54 passed**，PR #5 全仓 CPU suite 为 **176 passed**；v9 receipt 绑定 9 个 payload、外层 manifest 覆盖 10 个文件，SHA-256 全部匹配。输出仍保持 `physical_score=null`。时变 route 仍需 schedule、initial-law/TV、anchor-score shift 与独立 reference；新方法只免除精确 `k_ps`/逐类方差收据，不免除真实 gap lower-bound receipt。

**下一位 Pion agent：**不再重复 Eq. (3.26) synthetic 网格。先让研究者确认评分目标与单位、预测域/`R`、clipping、`delta_star`、候选族和 alpha；然后只用未封存的 D provenance 审查 score-specific graph 或 block-chain/gap receipt，以及 stationarity/TV、完整 schedule 与 anchor 偏移。若使用 support-gap route，提供独立 `gamma_ps_lower` receipt 并审计是否足以让这个最坏界有用；若提供 `k_ps`/逐类方差证据，也可沿 exact-k route。两条路线均须独立 anchor 覆盖/common-bias 证据和 reference。输出保留公式、依赖流、planned/valid/failed/abstained 分母与失败原因；输入不全就 `ABSTAIN/NOT_READY`。不解封数据、不补示例值、不启动 GPU/QUDA。

## 2026-11-24 time-varying LCB 收据接口闭合

本轮复核发现旧文件尾部的第二个同名 `markov_time_varying_score_lcb` 会遮蔽共享核心入口；已删除重复实现，使精确 `k_ps`/逐类方差路线和 support-gap 路线分别只有一个定义。两条 helper 现在都要求 SHA-256 形状的 dependence-evidence、block-chain 和 `gamma_ps_lower` 收据；精确路线另外要求 variance、`k_ps`，support-gap 路线保留 schedule、initial-law/TV 与 anchor-shift 收据。合同检查器也对每条 Markov 路线检查 gamma 下界收据，且仅校验格式/存在，不读取或认可收据内容。

- [contract v11 结构诊断](../../results/pion_projection/bounded_block_risk_contract_diagnostic_20261124_v11/README.md) 有 16 个 synthetic checks，planned/valid/failed/abstained=`16/5/11/0`；新增缺失 Markov gamma 收据反例。报告含文字决策流，明确所有 Markov 路线都要 chain/gap/evidence receipts。
- [Eq. (3.26) v3 解析诊断](../../results/pion_projection/bounded_block_risk_markov_varying_20261124_v3/README.md) 保留图和文字流程；72 个假设解析格 planned/valid/failed/abstained=`72/5/0/67`，部分失败 fixture 为 `20/18/2/0`，全失败为 `4/0/4/0`。本次未做 coverage Monte Carlo，也未访问任何测量/封存输入。
- 定向合同/变时 helper tests **62 passed**；完整仓库 CPU suite **184 passed**。两份新报告的 payload manifest 均逐项通过 SHA-256 核验（各 10 个 payload）；helper 现在只剩两个预期入口定义。报告与测试仍只验证结构、算术和收据字符串格式，不建立真实链 gap、anchor 独立性、统计覆盖或物理 reference。

文字数据流：`planned bounded scores + valid mask -> shared LCB core -> require schedule/chain/gap/initial-law/anchor receipts -> retain failed slots at -1 and full N -> conditional bound or ABSTAIN -> physical_score=null`。用户对研究输入/外部授权的最新答复是继续保持 `NOT_READY/UNCERTIFIED` 与 sealed data closed，因此 Pion TODO **保留**。下一位 agent 不应再次询问相同授权或重跑 synthetic 网格；只有收到目标/单位/`R`/clipping/`delta_star`、依赖或 Markov receipts、独立 anchor/common-bias 界和 reference 后，才更新合同并运行新的诊断。缺一项继续 abstain；不访问封存 E/gap/validation/holdout，不启动 GPU/QUDA。

## 2026-11-25 当前 Pion 接手点

前文关于目标、单位、`R`、clipping、`delta_star`、family 与 alpha 的提问已由本轮选定默认值覆盖；不得再次向用户询问这些方法选择。下一位 agent 按顶部 defaults 实现合同字段，并重画 `F=3` 下 `N/gamma_ps/TV` 半径图。实际 gap/TV、独立 anchor 与 common-bias/reference receipts 仍未提供，故只可产出条件式公式诊断；不解封数据、不申领/假设授权、不输出物理分数。
