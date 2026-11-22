# 稳健分数的下一种可实现方案：已知有界损失与独立 anchor 区间

**状态：bounded block-MSE 已被用户接受为探索用的独立 estimand；本稿仍是 THEORY / DESIGN_ONLY，不是冻结的 production score。** 本稿补充的是一个有条件的有限样本方案及其计算成本，不改变现有 `single-cosh FAIL`、`M2 ABSTAIN / NOT_READY` 或 `physical_score=null`。当前输入没有满足下述条件的物理 block-loss/anchor contract，故本稿不能触发新测量或计分。下方数表由公式直接求值，不使用任何 correlator、受限 split 或新增随机样本。

## 为什么值得留下这个分支

[weak-null 诊断](../../results/pion_projection/weak_null_nonexchangeable_20261120_v1/README.md)已显示：相同 rare-tail 均值零 DGP 下，常见 t、sign-flip、wild 和 percentile-bootstrap 在24/48独立 blocks仍可过量认证；MoM 的保守保证需要一个当前物理数据没有的外部方差上界。继续同一生成器扩样不能补上该物理条件。本稿考虑另一种可审查的额外信息：**在读评价数据前固定损失范围，并提供独立、物理可信的 anchor 误差区间**。有界性允许给出不依赖尾形状的保守下界，但代价是较宽区间，并可能改变原任务的 estimand。

“有界”必须来自明确的估计量定义或可辩护的物理界。不能看完数据后以样本最大值充当总体范围；不能把代码质量域 `[0.1,3.0]` 自动当作基态质量的物理置信域。若采用 clipping，则分数描述的是 clipped estimator 的风险，必须同时报告 clipping 频率及失败/弃权，不能把该风险静默改称原始质量估计器风险。

## 可核查的推导与假设

在评价数据读取前，固定候选、baseline、训练结果、拟合/失败规则、块构造、质量域 `[l,u]`、主改善量及比较族。令 `R=u-l>0`。每个真正独立且同分布的评价块 `j=1,…,n` 上，得到 baseline 和 candidate 的有界质量估计 `b_j,c_j∈[l,u]`；同一块的两臂允许相关，跨块须满足独立条件。独立 anchor `A∈[l,u]` 来自评价块之外；设一个外部有效区间保证

\[
\Pr(|A-m_*|\le B_A)\ge1-\alpha_A,
\qquad m_*\in[l,u].
\]

该区间必须涵盖声明的 ground-state/model/systematic uncertainty；单一错误态上的小SE或独立链之间相容不能建立它。区间可由另一项已完成的物理分析提供，当前 E 尚未测量，且拟议 M2 本身尚未 READY。

定义每块的 anchor 风险改善与真实目标改善：

\[
d_j=(b_j-A)^2-(c_j-A)^2\in[-R^2,R^2],
\qquad
\Delta_*=\mathbb E[(b_j-m_*)^2-(c_j-m_*)^2].
\]

给定独立 `A`，有

\[
\Delta_*=\mathbb E[d_j\mid A]
 +2(A-m_*)\,\mathbb E[b_j-c_j],
\qquad |\mathbb E[b_j-c_j]|\le R.
\]

因而在 anchor 覆盖事件上，`Δ_* ≥ E[d_j|A]−2 B_A R`。对总计 `F=J×K` 个**预先固定**的 candidate/reference分支比较，取统计预算 `α_S`，Hoeffding 单侧界加 union bound 给出

\[
L_{jk}=\overline d_{jk}
 -R_{jk}^2\sqrt{\frac{2\log(F/\alpha_S)}{n_{jk}}}
 -2B_{A,k}R_{jk}.
\]

在各分支条件成立、anchor 全族覆盖失败概率总计不超过 `α_A` 时，

\[
\Pr(\exists(j,k):L_{jk}>\Delta_{*,jk})
 \le\alpha_S+\alpha_A.
\]

推导直接使用有界独立变量的指数尾界；各候选间/各分支间无需独立，Bonferroni 会保守。若要求某 candidate 在全部 K 个模型下改善，用 `min_k L_jk > δ_*` 认证该 candidate。`δ_*` 是事前声明、以 lattice-mass-squared 为单位的实用改善阈值；不能把 ratio threshold 直接代入。报告同时保留 point estimate、下界、全 planned 分母、失败/弃权、F、n及anchor预算。

这里的 `n` 是独立块数量，绝不是bootstrap draws、时间点、source数或RHS数。未证明独立时不能套公式或把估计的 effective sample size 直接代入。若块不独立，须另建有可验证混合条件/依赖界的理论 contract；更多bootstrap draws不会补上该假设。anchor或候选若由评价块挑选，条件化证明也不适用。这里给出的是本方案的直接推导，没有声称当前物理数据已满足任何前提。

## 小块数时的成本：解析表而非 MC

为只显示统计代价，下表暂置 `B_A=0`、`α_S=0.05`，将风险除以 `R²`。真实 anchor 有不确定性时必须另分配 `α_A`，减小 `α_S`，并加扣 `2B_A/R`；表中数字因此是较乐观的条件情形。

| 独立块 n | F=1 的归一化统计扣减 | F=4 的归一化统计扣减 |
|---:|---:|---:|
| 12 | 0.7066 | 0.8546 |
| 20 | 0.5473 | 0.6620 |
| 24 | 0.4996 | 0.6043 |
| 48 | 0.3533 | 0.4273 |
| 100 | 0.2448 | 0.2960 |
| 400 | 0.1224 | 0.1480 |

**文字诊断：**即使anchor精确、仅一个比较，12块也要从观测平均改善中扣去整个允许风险尺度的约71%。这不是“此方法能使现有60配置得到稳定高分”的依据，而是一个可量化的保守成本。当前60配置/12块只是草案的计数，尚没有独立性证明；表格不对其有效性背书。现有D0–99按长度5取20块，同样不能只凭块数采用该保证。

令观测归一化改善超过预设阈值及anchor扣减后的剩余量为
`η = mean(d)/R² − δ_*/R² − 2B_A/R > 0`。
使统计扣减严格小于该剩余量，需要

\[
n>2\log(F/\alpha_S)/\eta^2.
\]

| 剩余量 η | F=1 最小整数 n | F=4 最小整数 n |
|---:|---:|---:|
| 0.10 | 600 | 877 |
| 0.20 | 150 | 220 |
| 0.30 | 67 | 98 |

这是给定**观测**剩余量时下界可为正的代数条件，既不是预先保证的功效，也不是建议按结果不断加样本。固定样本量的功效规划还需要预声明 DGP/最小改善并留出观测均值波动；顺序查看和提前停止要另作alpha分配。若 `η≤0`，增大n也无法消除anchor/目标阈值造成的确定性扣减。

## 与原生产风险的区别必须先解决

原风险由整条ensemble质量估计的不确定性和相对reference偏差构成；本方案是**固定大小独立块上、指定估计器的期望平方误差差**。非线性拟合下，块估计器的MSE与全ensemble估计器的MSE通常不同。不能将现有bootstrap risk draws当作独立 `d_j`，也不能将ensemble风险重复n份后套此界。

用户已选择①：按 bounded block-MSE 作为不同于原 ensemble-risk 的 estimand 继续探索。这个选择允许 CPU 方法校准，**不等于**接受任意损失范围、clipping、block独立性、anchor覆盖或生产失败政策；这些仍要有物理依据。选项②若未来研究，属于另一个 estimand 分支，不是当前工作的前置项。当前不冻结 production 数值，也不因这一选择改变 Pion reference gate 或测量授权。

## 接手者可执行的文字流程与停止条件

```text
用户已接受 bounded per-block MSE 作为探索 estimand
  → 当前 reference FAIL / M2 NOT_READY
  → 保持 physical_score=null；不重跑已有 score grid
  → 整理范围/clipping、失败、独立块、anchor与比较族候选
      ├─ 物理界、独立性或anchor覆盖缺证据 → DESIGN_ONLY/ABSTAIN，不计认证分
      └─ 日后存在可审查证据 → 冻结单位/阈值/alpha/成本后再评估解析可行性
          → 若新校准会改变是否采用决策，再预注册独立DGP与size/power目标
          → 物理测量仍需单独授权；reference/identity也各自过门
```

若这个方案值得进入实现，下一个agent交付以下八项即可作为开工材料，避免没有决策目标的扩样：

1. 明确 `Δ_*` 的定义、单位、候选/训练范围、每块估计器与原ensemble风险的区别及选择理由。
2. 预设 `[l,u]` 的物理/算法依据、是否clipping、clipping及不可拟合块的全planned处理规则。若失败块不能产生有界损失，整个比较弃权；不能删除失败块后沿用n。
3. 独立anchor来源、误差区间构造、共同偏差项与 `α_A` 的全族预算；不得只填一个拟合SE。
4. block ID/trajectory映射、真实独立性依据、每臂共享块身份和不依赖评价块选择候选的证据；有依赖则先换理论contract。
5. `F、α_S、α_A、δ_*` 和成本上限；用上述公式给样本量/最低可见改善表，明确功效仍待验证。
6. CPU纯函数实现与解析边界用例：两臂相等、互换、anchor边界、F增加、n增加、单位缩放、缺失/非有限输入和失败块拒绝；无需先运行任何真实数据。
7. 条件性 bounded-score calibration 已在 [`bounded_score_calibration_20261121_v1`](../../results/pion_projection/bounded_score_calibration_20261121_v1/README.md) 完成；失败块解析敏感度见 [`bounded_score_failure_policy_20261122_v2`](../../results/pion_projection/bounded_score_failure_policy_20261122_v2/README.md)。不得重复上述固定DGP/MC。只有新的物理范围、block单位或anchor覆盖模型会改变当前方法结论时，才先提出新的独立校准问题、目标精度、size/power和全planned失败策略，再审阅是否值得新增计算；不得用MC替代物理界证据。
8. 最终诊断交 `mean(d)/R²`、统计扣减、anchor扣减、阈值与下界的分解图，范围/clipping/失败表、块/anchor身份流程和逐分支弃权原因。没有有效anchor或独立性证据时报告 `NOT_READY`，不生成physical score。

本稿完成推导、解析成本表和条件说明；不声称这一保守方案优于现有方法，不改变任何 reference 门，也不申请E/validation/shared-holdout访问。2026-11-22状态更新修正了 estimand 选择：下一步是为已接受的探索目标补足可审阅的物理范围/单位、独立评价块来源、anchor共同偏差覆盖和失败政策选项；这些均未冻结。该设计稿说明“方法何时有条件可用、需要何种额外信息、为何当前块数可能不够”。

## 2026-11-22 封存状态下的候选合同矩阵（不冻结）

用户已选择 bounded block-MSE 作为探索 estimand。下表把未决项拆为可审阅选项，不从旧 pilot、代码质量域或已观察 D 数据中代填值。

| 合同项 | 候选路径 | 必需的独立证据 | 当前停止条件 |
|---|---|---|---|
| 目标质量与单位 | 原始格点质量 `am`；或用独立尺度换算后的物理质量 `m`。若采用归一化 $q=(m-l)/(u-l)$，需保存逆映射及尺度不确定度 | 明确 `m*`、baseline/candidate estimator、质量单位、格距/尺度转换与比较方向 | `m*` 或单位未定义时不计算质量 MSE score |
| 范围与 clipping | 估计器/物理上界自然落入 $[l,u]$；或预先将输出 clip 到该范围 | 可辩护的参数域/物理界；若 clip，报告每臂逐块 clip 频率、边界命中和 clip 前后估计量 | 不以观测样本极值决定 $[l,u]$；若 clipping 改变目标，明确标成 clipped-risk estimand |
| evaluation block | 真正独立重复；或按自相关/混合假设给出依赖数据 concentration contract；独立链只说明链间来源不同 | 每个 block 的 trajectory IDs、chain、间隔、warm-up 和独立/混合假设；不得以 bootstrap draw 数当 block 数 | 只有非重叠切块、没有依赖界时不套 Hoeffding；block 身份或独立性不足时 `ABSTAIN/NOT_READY` |
| anchor | 独立物理 anchor 给出 `A` 与 coverage interval，显式分配 `alpha_A`；或暂不认证，仅报告 anchor-conditional 描述量 | anchor 与评价块来源分离；偏差界覆盖共同系统误差、reference/model 误差及尺度转换 | 仅有拟合 SE、独立链间相容或小 bootstrap error 时不宣称 `B_A` 已知 |
| 失败块 | 整个方法比较 `ABSTAIN`；或有有界 counterfactual 时以 `−R²` 按 planned 分母做 failure-augmented utility | 失败输出是否仍定义同一个有界损失；计划/有效/失败分母及原因 | 输入/hash/split/reference/identity 错误一律 run-wide abort；没有有界 counterfactual 不做最坏编码 |
| 测量流 identity | point-source M2 与 matched source–sink 各自独立通过自己的 reference/identity gate | protocol/source/sink/kernel、矩阵行列定义、逐配置与block identity、provenance hashes | point-source M2 仍 `ABSTAIN/NOT_READY`；旧 matched source–sink 5% Hermiticity 门失败。不得跨流借用 gate 或 score |

候选数据流：

```text
hash / split / stream identity preflight
  ├─ fail → run-wide ABORT；不删块、不impute、不出分
  └─ pass → 物理质量、单位、[l,u]及 clipping 规则可审阅？
       ├─ no → DESIGN_ONLY；physical_score=null
       └─ yes → anchor interval 与 evaluation-block 独立/依赖合同可审阅？
            ├─ no → 只保留 conditional diagnostic；不调用独立块界
            └─ yes → 对每个 planned block 产生 baseline/candidate 两臂质量与状态
                 ├─ block fail → hard abstain；或仅在有界反事实获批准时 worst-case code
                 └─ all required blocks valid → 可计算 paired d_j / lower bound 作为 diagnostic
                      → 当前 reference/identity gate 未过：M2 ABSTAIN/NOT_READY，physical_score=null
                      → 未来独立 gate 通过且全部合同成立：再进入独立审阅，不自动生成物理 PASS
```

本表没有新增 simulation/sample count，也没有生产阈值。当前 bounded-score 的 168×3000 合成校准和 2026-11-22 失败块解析图仍是条件性方法证据；下一次有价值的校准必须由新的依赖模型或 anchor-bias 结构驱动，并说明它能改变哪个决策。若没有这类可改变 `ABSTAIN/NOT_READY` 的新证据，停止该分支的模拟工作并保留 TODO。
