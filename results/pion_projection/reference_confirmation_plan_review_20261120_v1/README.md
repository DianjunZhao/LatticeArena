# Pion reference-confirmation 草案：独立审查备忘录

**审查结论：维持 `ABSTAIN / NOT_READY`；当前草案不应进入 E correlator 测量。** 这不是“证明两态模型错误”，而是现有 D 可行性诊断已经违反草案自己的拟议筛查，数值实现和 M2 全流程校准也尚未闭合。当前 `physical_score=null`，不能读取 E IDs 0–59、D validation 或共享 holdout。

本备忘录只审查了当前草案、公开的 D0–99 结果、固定输入的 gap-profile / multi-start 诊断、Pion measurement/statistics 源码和 D/E HMC protocol / chain-comparison 报告。没有读取 E pion correlator、D gap、validation 或共享 holdout；没有重拟合、重采样、改 protocol 或启动 GPU。

## 决策摘要

```text
D single-cosh reference gate = FAIL
        ↓
公开 D 上的 M2 可行性筛查也未过（晚窗条件数、bootstrap 触界）
        ↓
multi-start 有 gap=0 退化终点与 SLSQP 非成功，旧搜索还漏掉更低目标点
        ↓
12 个主 block 估计 15 维协方差，M2 的拟合优度与弃权规则尚未校准
        ↓
维持 DRAFT / NOT_READY；不测 E，不计分
```

草案有多处做得正确：M2 是唯一确认模型、M1 只作诊断；E 看前冻结窗口/通道/算法；失败后不以 M1 救活；D–E 不 pooled；共同 holdout 不在本方案读取范围；即使拟议门通过，也不宣称证明 QCD 基态或自动产生 candidate score。这些约束应保留。

## 直接证据与分母

| 项目 | 当前证据 | 审查含义 |
|---|---|---|
| 冻结的 single-cosh gate | D0–99：质量 `1.09618 ± 0.00305`；近似拟合 p=`1.081×10⁻¹⁵`；两种窗口漂移 `20.41σ`、`15.78σ` | 原 reference gate 是 FAIL；不能用 post-hoc M2 诊断覆写。 |
| D 两态拟议筛查 | 三窗口参数分别见下表；拟议 amplitude-condition ceiling=`1×10⁵`；晚窗为 `299317`，且旧 bootstrap 有 `2/1000` 个有效 draw 的激发态质量触界 | 按草案自己的 `condition` 与“任一触界即弃权”规则，当前全窗口 M2 为 ABSTAIN。`2/1000` 是同一 D 样本上的 resample 计数，不是物理事件率或 coverage。 |
| 搜索路径 | 每窗 `29` 个确定起点中 `24/29` 为 SLSQP 正常终止；每窗另有 `5/29` status 4，15 个非成功端点全部在 `gap=0`；端点簇数为 `6 / 7 / 8` | 多起点结果不是 global-minimum certificate。`gap=0` 时两态设计列重合，是 M2 向 M1 退化的边界，应单独分类为“未解析/嵌套一态”，不能将其当作收敛的两态解。 |
| 独立 E 链身份 | HMC manifests 记录 D/E 均为 `16⁴`、`β=6.0`、周期 gauge 边界、独立随机起点和不同 seed；E 链完成 400 热化轨迹、496 生产轨迹、100 个保存配置。Pion 只拟议使用 E0–59，E60–99 是未用 reserve | 这是独立链的测量来源，不是 E pion anchor 已测或 reference 已通过。HMC plaquette 交叉比较仍是描述性检查，不证明平衡或 pion correlator 自相关尺度。 |
| block 与链自相关 | 每 5 条 HMC trajectory 保存一次 gauge；按 Pion 拟议 block length=5，约覆盖 25 条 trajectory 的区段。D/E plaquette `τ_int≈3.8/4.0` trajectory；均值差相对 block SE 随 block 长度从 `3.29σ`（length 1）降至 `1.01σ`（length 50） | 这些 plaquette 诊断使 block5 可作为待检查起点，但不能证明 pion correlator 的 decorrelation。应在获批测量后检查 reference correlator / mass trace；若 12 个块不足，更多 bootstrap draw 不会增加独立样本。 |

M2 的三窗口 D 表来自草案引用的已存归档，拟议门值仍是草案值而非用户批准阈值：

| 窗口 | `m0 ± SE` | `m1 ± SE` | amplitude normal-matrix condition | bootstrap mass-bound draws / valid |
|---|---:|---:|---:|---:|
| `[4,5,6,7,8]` | `1.0490 ± 0.00894` | `1.712 ± 0.0640` | `7.39×10³` | `0/1000` |
| `[5,6,7,8]` | `1.0400 ± 0.0129` | `1.596 ± 0.1196` | `1.46×10⁴` | `0/1000` |
| `[6,7,8]` | `1.0630 ± 0.00964` | `1.844 ± 0.2787` | `2.99×10⁵` | `2/1000` |

在同一 covariance metric 下，gap-profile 另找到了低于旧坐标搜索的目标点；晚窗 amplitude condition 从约 `2.99×10⁵` 增至约 `1.46×10⁶`。这说明现有点值与旧搜索过程不够稳定，不能把“找到有限点”或 `p_approx` 较高当作可靠识别。profile cost 差没有被校准成 likelihood-ratio、p 值或物理显著性。

![D0–99 两态 gap profile；这是固定 covariance metric 的描述性目标曲线](../two_state_gap_profile_d_20261120_v1/two_state_gap_profile.png)

![D0–99 的 29 起点 SLSQP 端点；失败点集中在 gap=0](../two_state_multistart_d_20261120_v1/two_state_multistart.png)

逐起点状态、对应分母与方法限制见[gap-profile 报告](../two_state_gap_profile_d_20261120_v1/README.md)和[multi-start 报告](../two_state_multistart_d_20261120_v1/README.md)。

## 方法与可辨识性审查

### 1. M2 与一态零假设在 `gap=0` 非正则

当 `m1=m0` 时，三个通道的两条设计列重合，预测只依赖 `A_k+B_k`；`m1` 和振幅分解本身不再可辨识。这同时导致 amplitude normal matrix 退化，也令通常基于常规内部点假设的 likelihood-ratio / chi-square 近似不能未经模拟直接套用。现有 `gap=0` SLSQP 失败与此几何退化相伴，但不能仅凭本诊断判定它是唯一数值原因。

建议新 runner 明确把 `gap=0` 作为嵌套 M1 边界单独计算/分类；M2 只有在 gap 有数据驱动分辨、`B_k` 及 profile 对 gap 的信息足够、不同起点收敛到同一有效区域时，才谈 M2 的数值可辨识。不能因参数化强制 `m0<m1`、bootstrap gap 自动为正，就认为第二态已被识别。

### 2. 12 个 block 不足以把近似拟合优度升级为确认门

主 M2 数据向量是 3 个通道 × 5 个时间点，共 15 维；E 拟议 N=60、block=5 只产生 12 个 block vectors，样本协方差秩至多 11。25% diagonal shrinkage 与 eigen-floor 可使逆矩阵数值上存在，却不会创造缺失的独立协方差信息。M2 有两质量和每通道两振幅，共 8 个拟合参数；由该 regularized covariance 得到的 `p_approx` 不能照搬普通已知协方差的卡方解释。

草案正确把 `p_approx` 标为描述性并将未校准时最高状态限制为 `INCONCLUSIVE`。在测 E 前仍需用完整 M2 pipeline 做有限 DGP 校准：至少含 ground-state null、可分辨双态、近零 gap/弱激发振幅、wrong-state / common-bias、真实量级的跨通道/跨时间协方差与自相关。每个世界需报告计划数、valid、solver failure、边界、abstain、假通过/功效以及 Monte Carlo 区间。已有单态 C2 χ² subgate 和 `J=2/K=2` 合成家族结果不能直接代替这项 M2、N=12-block 校准。

另外，“2000 个 bootstrap draws 中任一个失败/触界即弃权”是明确但非常严格的规则，其触发机会会随 draws 数增加；它把数值 solver failure、数据不足与物理质量边界混成一个全否决事件。若坚持固定 2000 和零容忍，须在 DGP 校准中展示其可用率/假弃权率；更稳妥的设计是分别报告数值失败率、质量边界比例和 profile 可辨识性，并在 E 未查看前冻结可接受范围与分母。不能看 E 后从零容忍改成 1%。

### 3. 线性振幅求解应冻结为稳定实现

当前 `reference_twostate.py` 对每一组质量使用 `solve(XᵀWX, XᵀWy)`，即正规方程，并把 `cond(XᵀWX)` 作为条件数。正规方程会放大设计矩阵病态性；gap-profile 诊断改用 whitened SVD 消去振幅后才得到其报告的目标曲线。新确认执行器应冻结同一套 whitened QR/SVD、秩阈值、channel scaling 和 residual 定义；阈值 `1e5` 必须绑定具体缩放与矩阵定义，不能当作尺度无关常数。

### 4. D–E 相容不是等效性，独立 HMC 链也不是完整独立复现

拟议 `|m_E-m_D| ≤ 2.5 SE` 是一个预设的相容性筛查，不是等效性证明。若科学文字要声称两链“在物理容差内相等”，需先定义 lattice-unit 的实际允许差值，并报告等效区间；否则只说“该相容性检查未拒绝差异”。D 已参与设计，所以 P2 只能是复现性辅助检查，不能作无选择偏差的原假设检验。

独立随机起点和 seed 支持 E 与 D 的链身份独立；相同 `β`、体积、periodic gauge 边界也支持其为同一目标系综的拟议复现。但一条链的 plaquette 接受率、自相关和两链均值相似不证明充分热化、拓扑穿越、Pion reference 的独立性或完整物理正确性。结论必须限定在“同一已声明离散设置下的统计复现”。

Pion 侧 `t_boundary=-1`、`T=16`、原点 point source 与 even Wuppertal sink powers 写在 protocol/measurement 中；拟议 M2 cosh 对应周期 meson correlator 是合理方向，但获批执行前仍要把源/汇指标、时间轴、折叠、零动量与 γ5-hermiticity 的数据流核对为可审计 contract。即使这些约定全正确，也不自动保证拟合最低参数就是 continuum/无限体积的 QCD ground state。

## 建议的下一步

1. **当前计划保持 `DRAFT / NOT_APPROVED / NOT_FROZEN / NOT_RUN`。** 不测 E0–59、不打开其他 split。按草案拟议门，D 已显示 `ABSTAIN`；应把它视为当前设计停止条件，不通过事后放宽阈值或删窗救活计划。
2. 在未触碰的 E correlator 之外，先完成 M2 全流程 CPU 数值与 gate 校准；公开 D 只用于失败/可行性审查，不能以“D 上成功”为目标调门。报告多起点盆地、gap=0 一态边界、SVD/正规方程对照、协方差敏感性，以及全部计划 draw 的失败/弃权分母。
3. 若 D 校准和可辨识性仍不支持固定 60 配置设计，则结论应是“当前 D 信息/该 M2 实现不足”，选择另一个有物理依据的观测方案，例如新增线性独立 source/sink overlaps 的 variational basis 或更多独立配置；这需要新的方案审查、未触碰验证数据和单独授权，不可借用 E60–99 reserve 或 shared holdout。
4. 若只修改纯数值实现，冻结新的 executor/source hashes 和拟议准则后再送审；若改变物理模型、channel/window、有效样本或接受率，必须解释为什么仍回答原 P1，并把旧 E 保持未查看，或转用全新的独立链。
5. 分开报告拟合最低参数的复现、实际 ground-state 识别、candidate score 与共享 blind test。即使未来 M2 reference gate 通过，仍需独立的基态/共同偏差论证与 anchor/score 审查；不得自动给出 `physical_score`。

## 依据文件

- 拟议主张、窗口、block/covariance/弃权规则与来源绑定：[`reference_confirmation_plan_draft.md`](../../../tasks/pion_projection/reference_confirmation_plan_draft.md)。
- 原 gate 失败及 D0–99 reference/有效质量诊断：[`s16t16d_closure_20261120/README.md`](../s16t16d_closure_20261120/README.md)。
- 交叉链 HMC 诊断：[`hmc_chain_comparison_20261120/README.md`](../../wilson_loop/hmc_chain_comparison_20261120/README.md)。该诊断只支持描述性的 gauge plaquette 对照。
- 相关代码：`tasks/pion_projection/reference_twostate.py`、`statistics.py`、`measure.py`；相关拟议 protocol：`tasks/pion_projection/protocol_fresh_20261120.json`。

**最终判定**：保留 reference-confirmation TODO；本备忘录关闭“是否继续测 E”这一独立方案审查工作，答案为**暂不继续**。它不批准测量、不更改旧 single-cosh FAIL、不构成物理 score，也不替代用户对新方案的审批。
