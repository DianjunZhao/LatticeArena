# 独立 reference 确认方案草案

状态：**DRAFT / NOT_APPROVED / NOT_FROZEN / NOT_RUN**。日期：2026-11-20。

本文件只提出下一轮确认方案，不是新 preregistration、测量授权或 production gate。文中所有拟议数值、模型角色和通过条件均为**待用户审批、待实现核验、待冻结**。旧 frozen single-cosh gate 仍 FAIL，`physical_score=null`。其后补充的 D-only gap-profile 与确定性 multi-start 是固定输入的开发诊断；没有修改测量代码、旧 protocol 或旧结果，也没有读取 E correlator、D gap、D validation 或共享 holdout。

## 1. 已公开证据与本轮能够确认的命题

D development IDs 0–99 的公开[分析报告](../../results/pion_projection/s16t16d_closure_20261120/README.md)给出 single-cosh mass **1.09618 ± 0.00305**、近似 p=1.081e-15，窗口漂移20.41σ与15.78σ；原门失败是当前事实。此处采用显式 ± 记号，避免旧文括号误差位数造成精度误读。

同一批 D 的[两态诊断](../../results/pion_projection/s16t16d_closure_20261120/two_state_diagnostic.md)给出较好的样本内拟合，但晚窗口激发态触及上界、条件数约3e5。[有效质量扫描](../../results/pion_projection/s16t16d_closure_20261120/effective_mass_diagnostic.md)显示时间及 sink-power 漂移。这些事实只支持“单态参考遗漏了可观测时间曲率、两态描述值得独立确认”的推断，尚未识别物理第二态或证明提取到真实基态。

**主确认命题 P1（有限命题）**：在未查看的独立 E-chain correlator 上，预先指定的共同两态 reference 能给出可辨识、无边界依赖、对预设窗口与 block 敏感性检验稳定的最低拟合能量。通过时只能写“该 reference 的独立链复现支持”，不能写“证明为物理基态”。

**辅助命题 P2**：冻结分析后的 E 最低拟合能量与 D 同模型、同窗口结果在声明的统计精度内相容。D 已参与方案选择，D–E 一致性是复现检查，不是无选择偏差的原始假设检验；不以 D+E pooled mass 充当独立 anchor。

**不由本方案确认的命题**：拟合最低态必然是 QCD 基态；两态是完整谱；共同 valence action、有限 T、相同 source/sink 引入的偏差已受控；candidate improvement 或 physical score 已校准。wrong-state 和 common-bias 负控已经说明独立统计重复也可能重复共同物理偏差。

E HMC 链已生成不等于 E pion correlator 已测量，更不等于 E reference 已通过。E 原始 gauge 字节、轨迹 receipt、12-RHS propagator 与 pion correlator 是不同证据层，须在未来获批运行中分别核验。

**测量流边界（新增复核）**：本 M2/P1–P2 草案针对 `protocol_fresh_20261120.json` 的 point-source correlators（sink powers `[0,2,4,8,16,32,64]`，D development IDs 0–99）；其独立 E anchor correlator 尚未测量。新 `protocol_multisource_matched_v2.json` 则用于另一条 source–sink cross-matrix 路径，包含 point/H4/H16 source labels，development 0–59、gap 60–69、validation 70–99。它的 CPU matched-smearing preflight 不会修复、验证或替代 M2 point-source correlators；M2 的点源数据也不认证该 cross-matrix 的 source/sink Hermiticity。两条流的 correlators、splits、generation 和 hashes 不得混池。未来执行任一流时都须为该流单独冻结 measurement contract 和 input manifest；matched-v2 的 CPU preflight 也不授权新测量。

## 2. 候选模型与避免模型选择偏差

拟议保留两个模型，但角色在看 E 前固定：

- **M2 为唯一主确认模型**：三个 reference channels 共用有序能量 m0<m1，每个通道有独立实振幅 A_k、B_k；模型为 C_k(t)=A_k f(t;m0)+B_k f(t;m1)，f(t;m)=exp(-mt)+exp[-m(T-t)]，T=16。质量均以 lattice units 报告。振幅允许带符号，不在没有 source/sink 谱正性证明时强行加正值先验。
- **M1 为诊断对照**：共同单质量与逐通道振幅，沿用原 single-cosh 定义。不得在看到 E 后因 M2 失败而用 M1 替代主模型，也不得择优报告最高 p-value 或最窄区间。

主 reference basis 拟议固定为通道下标[0,3,4]，对应 sink powers[0,8,16]；其余powers只作预先声明的形状诊断，不加入模型选择。空间周期、quark时间反周期、零动量 pseudoscalar channel 与 meson periodic-cosh 关系须由测量 contract 再核验；不能仅因模型写成 cosh 就认定实现约定正确。

M2的拟议名义窗口为[4,5,6,7,8]，预设敏感性窗口为[5,6,7,8]和[6,7,8]。这是看过D后提出的**新**名义窗口，不改写旧 nominal=[5,6,7,8] 的历史。若短窗口无法辨识两态，结论为ABSTAIN，不能事后删除短窗口并宣布通过。

拟议质量域0.1<m0<m1<3.0，沿用既有范围只为可比较性，不视为物理先验已验证。当前 TwoStateFit 的粗网格起点、局部搜索步长和 amplitude normal-equation 条件数都有实现依赖。最终程序必须明确质量排序、所有起点/步长、优化器容差、停止次数、无解口径及边界判断；既有 exploratory runner 不自动成为新确认程序。

选择偏差控制拟议如下：D只充当已看过的设计集；所有模型/窗口/通道/block/协方差/阈值和输出先冻结，E只分析一次；禁止 E 上增删模型、逐窗口挑结果、调 shrinkage、扩 mass bounds 或追加样本。若 E 失败，本轮确认失败或弃权；后续方案需要新的未查看独立证据，不能把同一E重新称为盲测。不得通过D–E合并压低区间、选择较有利的 E 子集或以M1/M2二选一提高通过概率。

执行前还须做**公开D上的可行性审查**，该审查不是独立确认：现有D的[6,7,8]两态boundary与约3e5条件数已经违反下面拟议的严格筛查，故本草案当前并无READY资格。若冻结前审查确认同一拟议方法必然对D弃权，先停在方案阶段，不能为“看看E会不会更好”消耗E。任何为解决可辨识性提出的新参数化/额外独立信息，必须说明物理依据与为何改变确认命题，再在E未看前重新送审；禁止只调整到D通过。现有代码不能直接执行本草案即获得确认结论。

<a id="d-development-feasibility"></a>

### D0–99 既有两态结果的可行性表（只读补充）

下表的拟合值与SE摘自公开的 [`two_state_diagnostic.json`](../../results/pion_projection/s16t16d_closure_20261120/two_state_diagnostic.json)；边界次数从既有 [`two_state_bootstrap.npz`](../../results/pion_projection/s16t16d_closure_20261120/two_state_bootstrap.npz) 只读计数，并与 [`two_state_diagnostic_provenance.json`](../../results/pion_projection/s16t16d_closure_20261120/two_state_diagnostic_provenance.json) 中输出 SHA-256 `e23d0781054adb5f035320c2b07494895fc76251bdf09f87b6d6b795d59eabcd` 核对。未运行新拟合或模拟；仍为原20个长度5块、1000个bootstrap draws，不是草案拟议2000draw流程的执行记录。边界按原诊断的质量域 `[0.1, 3.0]` 和 `1e-4` 容差逐draw复算，与 `two_state_development_diagnostic.py` 的判据一致。

| 时间窗口 | m0 ± SE | m1 ± SE | condition | full-sample boundary (`at_boundary`) | bootstrap mass-bound (`mass_bounds_reached`) | bootstrap触界 draws / valid |
|---|---:|---:|---:|:---:|:---:|---:|
| [4, 5, 6, 7, 8] | 1.049000 ± 0.008938 | 1.712000 ± 0.064018 | 7394.073828 | false | false | 0 / 1000 |
| [5, 6, 7, 8] | 1.040000 ± 0.012910 | 1.596000 ± 0.119630 | 14572.639994 | false | false | 0 / 1000 |
| [6, 7, 8] | 1.063000 ± 0.009642 | 1.844000 ± 0.278733 | 299317.164421 | false | true | 2 / 1000 |

**文字诊断：拟议M2全窗口门在现有D证据上为ABSTAIN。** [6,7,8]窗口condition=299317.164421超过草案拟议1e5筛查值；既有bootstrap数组进一步显示，1000个有效重采样中有2个的激发态质量触及上界（按原`1e-4`判据），已违反拟议“任一bootstrap触界即弃权”规则。三窗full-sample `at_boundary=false`，不能把bootstrap触界误写为全样本点估计触界；1000/1000 valid只表示有限/拟合成功，不表示无边界或可辨识。`2/1000`是固定D样本上的bootstrap resample计数，不是独立物理样本事件率、coverage或失败概率。高`p_approx`仍未校准，不能抵消边界和病态性。

可复现的只读复核脚本为 [`two_state_bound_count_audit.py`](two_state_bound_count_audit.py)，命令 `python3 -B -m tasks.pion_projection.two_state_bound_count_audit` 只向stdout输出计数并核验固定归档hash；其focused test [`test_pion_two_state_bound_count_audit.py`](../../tests/test_pion_two_state_bound_count_audit.py) 覆盖联合valid分母、含边界端点及hash变化拒绝。本次该测试 **10 passed**。脚本没有拟合、抽新样本或改写归档。

三窗`p_approx`依次为0.99671053、0.95493739、0.90157335，均为估计协方差与shrinkage下的近似值，**未经本M2/窗口/块数设计的size校准**；高p不抵消边界和病态性。上述ABSTAIN是把现有原始诊断数值与拟议门逐项比较，不是新方案已执行或获批。当前应停在可行性与方案审查，不启动E；保留TODO、旧single-cosh FAIL和`physical_score=null`。

### D-only gap profile 与现有搜索路径复核（2026-11-20）

为检查“bootstrap gap的正下界是否代表两个态可辨识”以及新确认程序是否能稳定找到拟合点，新增了只读、固定hash输入的[gap-profile诊断报告与图](../../results/pion_projection/two_state_gap_profile_d_20261120_v1/README.md)。脚本[`two_state_gap_profile.py`](two_state_gap_profile.py)先调用上述归档审计，只读取D0–99既有100配置、20个长度5块、旧两态诊断和旧bootstrap；它不抽新样本、不改写归档或score。

| 窗口 | 旧搜索gap | 本次profile找到的更低目标点gap | gap=0处Δ目标值 | 条件数：旧点 / 新点 | 同一目标的改进量 |
|---|---:|---:|---:|---:|---:|
| [4,5,6,7,8] | 0.663 | 0.684 | 423.24 | 7.39×10³ / 8.41×10³ | 0.07495 |
| [5,6,7,8] | 0.556 | 0.629 | 87.61 | 1.46×10⁴ / 2.64×10⁴ | 0.08212 |
| [6,7,8] | 0.781 | 0.926 | 14.18 | 2.99×10⁵ / 1.46×10⁶ | 0.01505 |

Profile使用与原拟合相同的固定shrinkage协方差metric，以whitened SVD消去线性振幅；mass0先用0.01网格扫描并局部精修，gap在粗扫外还围绕旧拟合用0.003步长加密，并精修已采到的局部谷。原拟合点用同一稳定求值复算后与旧cost仅有舍入差，但每窗当前坐标搜索给出的目标均高于本profile找到的点。这是**现有搜索路径可能漏掉较低目标盆地**的代码诊断，不代表新的物理质量；本profile只精修抽样到的局部谷，也不证明找到全局最小值，后续确认runner必须验证多起点、失败和盆地一致性。

旧bootstrap gap在三窗的2.5/50/97.5百分位均为正，但拟合参数化本身强制m0<m1，正gap量值不能单独作为第二态被辨识的证据。图中的gap=0目标差是同一估计metric下的原始目标差，未校准为likelihood-ratio分布、p值、coverage或physical significance。晚窗profile点的振幅法方程条件数升至1.46×10⁶，仍显著超过草案拟议的1e5数值筛查；故全窗口M2方案仍为ABSTAIN/NOT_READY。不能通过删窗或改阈值让D过门，也不据此启动E。

### D-only 确定性多起点与端点诊断（2026-11-20）

为落实上节提出的失败/多起点审计，新增[只读 D0–99 多起点图文报告](../../results/pion_projection/two_state_multistart_d_20261120_v1/README.md)及逐起点 CSV。脚本[`two_state_multistart_diagnostic.py`](two_state_multistart_diagnostic.py)从固定来源 hash 复核 D development，使用与旧两态 fit 相同的固定协方差目标、whitened SVD 消去线性振幅；每窗用29个确定性 `(m0,gap)` 起点（包含`gap=0`和旧坐标搜索端点），以 SLSQP 局部优化。合成单/双态恢复、上下边界、零gap退化与非法输入测试共 **9 passed**；它们不用于在 D 上调门槛。

| 窗口 | 起点 | 正常终止 | 有限终点 | 近似端点簇 | gap=0端点 | 最低目标 gap | 相对旧目标改善 |
|---|---:|---:|---:|---:|---:|---:|---:|
| [4,5,6,7,8] | 29 | 24/29 | 29/29 | 6 | 5 | 0.68376 | 0.07495 |
| [5,6,7,8] | 29 | 24/29 | 29/29 | 7 | 6 | 0.62887 | 0.08212 |
| [6,7,8] | 29 | 24/29 | 29/29 | 8 | 6 | 0.92645 | 0.01505 |

每窗5个非正常终止都记录为 SLSQP status 4，`Inequality constraints incompatible`；这15个返回点均有限、满足约束且落在`gap=0`。前两个窗口各5/5从零gap起步；晚窗4/5从零gap起步，另一个从`(m0,gap)=(0.187,1.305)`起步后也落到零gap。这里两列振幅设计退化为共线，和非成功终止相伴；仍保留为优化器非成功，不能计为收敛，也不能断言秩亏是唯一触发原因。端点簇按两个坐标最大差≤0.02的贪心描述性分组，不是数学盆地计数。最低端点目标与 gap-profile 的同一固定 covariance metric 数值一致，旧坐标点仍高于两者。多起点结果加固了“搜索路径有依赖”的数值诊断，也显示约束退化和终止状态需要在新 runner 中显式报告；但它不证明全局最小、不校准目标差、也不识别物理第二态。晚窗的 mass normal-matrix condition 约1.46×10⁶与2/1000既有bootstrap上界触碰仍在，提案依旧 `ABSTAIN / NOT_READY`。

## 3. 样本、协方差与 bootstrap（全部为拟议）

拟议 E 使用既有规划 IDs 0–59，共60配置，按轨迹顺序取连续、完整配置块。不得将 raw RHS、sink powers、时间点、bootstrap draws 或不同窗口计作独立 gauge 样本。D仅使用已公开0–99，不读取gap或validation。

主 block length=5，E有12块；敏感性 length=10有6块。全部配置必须完整分割，不丢尾部，不因结果有利更换长度。length=1/2仅可作附图诊断，不能用于挑选最小SE。长度5不是已验证去自相关尺度；报告轨迹间隔、可用采样历史和块数，若现有长度不能支持可靠不确定度则ABSTAIN，不以多抽bootstrap弥补独立块不足。

三通道×五时间点构成15维数据向量；12个块的样本协方差秩至多11，length=10时更低。**本设计必然依赖协方差正则化**。主metric拟议使用既有25% diagonal shrinkage与1e-10×最大特征值的floor，并冻结通道归一化与矩阵构造。不得因E结果改变lambda或floor。必须输出归一化方法、协方差谱、rank、floor命中数和条件数。shrinkage与floor敏感性可在获批冻结时列为诊断分支，不能通过挑分支绕过主门。

每条链各自从完整块生成共同indices，所有模型/窗口/通道共用该链的draw身份，拟议2000个bootstrap draws；主分析先固定该链full-sample metric再重采样均值，明确其区间条件于估计metric。D与E的indices相互独立；不得用相同draw编号暗示跨独立链有配置配对。拟议种子由新协议显式写入，建议使用独立SeedSequence streams [20261120, 101]用于D、[20261120, 102]用于E、[20261120, 103]用于预设D–E比较；这些种子尚未冻结。

同链窗口漂移用共同draw上的质量差分布；D–E差用独立draw的差分布，保留各自链与窗口ID。报告点估计、SE、16–84%及2.5–97.5%区间。区间先定义为拟议percentile诊断区间，**未声称真实coverage已校准**。不以bootstrap draws再除sqrt(Nboot)，不以bootstrap样本数充当统计分母。

每个draw均保存success、exception、finite、boundary、质量排序、gap和条件数；不静默丢弃失败draw。任何条件于valid的SE/区间必须同时报告all-planned失败率、失败原因及筛选影响。质量界、gap未分辨、sign/amplitude退化和多起点不一致必须分开诊断。

## 4. 拟议筛查门、停机与弃权

以下均为**待审批/待冻结的操作性筛查值**，不是已经预注册、也不是5%物理错误率保证：

1. 身份完整：60/60计划配置，输入/输出/代码hash及trajectory join全部通过；12-RHS显式残差最大值不超过既有1e-10标准，finite/shape及测量contract通过。任何缺失或不一致即STOP，失败配置留在60分母，不用其他ID补齐。原测量iteration limit=10000与预算须在新RunSpec中明确，不自行放宽。
2. 拟议每窗口full fit与全部2000draw无异常、无非finite、无mass boundary；边界近似容差1e-3 lattice mass units，另保留原诊断1e-4触界计数以便解释差异。任一失败draw或边界命中均ABSTAIN，不报“valid-only通过”。此规则刻意保守，必须在测E前评估其可行性，不能在E失败后改成容许1%失败。
3. 拟议各窗口m0相对bootstrap SE≤5%，mass gap的2.5th percentile>0且不由排序约束/数值步长挤出虚假分辨；同时以profile cost曲线或多起点稳定性检验确认可辨识。若profile区间触mass domain或gap=0端点，ABSTAIN。不能仅因gap始终被约束为正就判分辨。
4. 拟议amplitude normal-equation condition≤1e5；必须明确归一化、矩阵及norm定义。该数是数值筛查，非普适物理阈值。若无法验证阈值与识别能力的关系，保留诊断、整体ABSTAIN，不能靠重标度获得通过。
5. 拟议同链窗口paired shift≤2.5SE、length5→10的质量差≤2.5个paired SE；预设比较全部列出，作为联合保守门而非挑选p-value。D–E名义质量差拟议≤2.5独立SE（或明确独立bootstrap差分布等价定义）。D–E有差异则单独标记REPLICATION_FAIL；不能以两边SE变大解释为已成功确认。
6. reflection-odd max|z|拟议≤4，沿用原筛查口径，逐通道/时间点报告；通过不抵消模型或身份失败。
7. approximate chi-square p拟议0.01仅作**描述性报警线**。估计covariance、shrinkage、非线性与低块数使其非精确p；高p不能独立触发PASS。正式确认若要采用fit adequacy门，须在E测量前另行冻结其完整统计量、拟合metric与独立null/misspecification模拟评估、MC精度目标和校准失败的stop rule。当前已有single-state子门/conditional-bootstrap结果不能直接迁移至M2和本窗口。此项未闭合时最高状态只能INCONCLUSIVE，不能绕过后进入计分。

拟议全门通过状态为`REFERENCE_REPLICATED_CONDITIONAL`，限定于冻结模型和已声明统计近似。它不追溯修改旧gate FAIL，也不自动开放validation或产生physical_score。通过前仍须单独论证基态识别及共同偏差控制；不能将M2质量最低、残差小、独立链相容作为该论证的替代。

没有按E结果增加样本的sequential stopping。本轮一次固定N=60；执行中仅允许因身份/残差/硬件失败暂停并保存checkpoint，依原prefix和hash恢复，不改变样本或门槛。失败、invalid、abstain均保留；任何模型/阈值变动建立新amendment，当前E视为已查看。

## 5. 一次确认的文字决策表

| 条件/所见证据 | 状态与文字结论 | 后续允许事项 | 后续禁止事项 |
|---|---|---|---|
| 只有本草案或任一实现/校准/审批/冻结项未闭合 | DRAFT/BLOCKED，旧reference FAIL | 完成方案与CPU/合成核验的独立计划、送审 | 测E、打开gap/validation/holdout |
| 批准并冻结新协议、源码、输入清单与访问边界 | READY_FOR_E_CONFIRMATION（需单独明确测量授权） | 获授权后仅测固定E0–59并留receipt | 扩样、改模型、读取D gap/validation/holdout |
| E身份/残差/缺配置不通过 | STOP_IDENTITY_OR_MEASUREMENT；60分母保留 | 写失败receipt、图文与恢复条件 | 补别的ID、直接做物理解释 |
| M2边界、无解、未分辨、窗口/block不稳 | ABSTAIN_REFERENCE；不确认reference | 报全draw/失败/边界图文，提出另一次独立研究 | 换M1救活、删窗、调界/threshold重判通过 |
| M2筛查通过但adequacy校准未闭合或误差不能信赖 | INCONCLUSIVE | 报告受限复现线索 | 宣称5%受控或开validation |
| M2全部冻结门通过且D–E相容 | REFERENCE_REPLICATED_CONDITIONAL | 报条件复现；另行审查基态/共同偏差与共享盲测计划 | 自动物理计分、追溯修复旧gate、自动开holdout |
| D–E不相容 | REPLICATION_FAIL | 保留两链差异与系统误差诊断 | 合并两链掩盖差异或选择更有利链 |

共享D IDs140–199仍受Pion/Optimize/Wilson三方冻结与一次解盲约束，本方案没有申请其访问权；D gap100–139亦不在本方案可读范围。任何任务先看结果都会使共享盲测失去对应的未查看属性。

## 6. 执行前输入、源码与证据绑定

以下是本次对公开文件读取字节所得**当前快照**，仅用于草案来源定位，不是新执行版本冻结。最终获批时必须重新核验当前hash，并以一份canonical manifest绑定新protocol/RunSpec/executor/receipt，禁止出现高层preregistration与executor重复hash不一致。manifest自身hash和审批时间需在E首次读取/测量前记录。

| 公开输入/当前实现（仓库相对路径） | SHA-256 |
|---|---|
| `tasks/pion_projection/protocol_fresh_20261120.json` | `1568592a9263bc3bbedd2d9c50ad740e307aa02175736f4deb795defccefa5e7` |
| `tasks/pion_projection/measurement_plan_fresh_20261120.json` | `2058c1f6fec04a6ab4da6176207746a90436b49963a83a3490e86e4f20de5969` |
| `tasks/pion_projection/reference.py` | `153675ba921fda9f339342694ba7b84426a8a96f892b049a7bec060f85c0eb4a` |
| `tasks/pion_projection/reference_twostate.py` | `0986d05e05ae39b52f35a8f2a829aa54e25f68c23bfd10d8932d776701cac690` |
| `tasks/pion_projection/statistics.py` | `69cda40c0f997a29179f1941388a90ea68d7f059ec686226b37a87bffc77d0e5` |
| `tasks/pion_projection/measurement_plan.py` | `1bb6183c0f3bdf42b46f211ab71610049baec1a8ed34cd2b0808054d5313789b` |
| `tasks/pion_projection/measure.py` | `55a74467d14b8026a3af4194cb080859a27918ef6043c0da88f538a77ec4b6e8` |
| `tasks/pion_projection/two_state_development_diagnostic.py` | `72bbd0842adc95e14519cd8c08a0ef3648994a7e02c7bf2ea59b6a1618f33371` |
| `results/pion_projection/s16t16d_closure_20261120/development.npz` | `8a78947c8b4d1bec3b672ed57cd1406ed0bcccf6ec874747ece4d64078da7fe3` |
| `results/pion_projection/s16t16d_closure_20261120/development_provenance.json` | `c58a016943e211ab32d613dfa677bb20261c694e048cde9ae700c45f350bc785` |
| `results/pion_projection/s16t16d_closure_20261120/two_state_diagnostic.json` | `006e245ce34e71265c4407c101bb196d5e9daea684201885209df248e92dae80` |
| `results/pion_projection/s16t16d_closure_20261120/effective_mass_diagnostic.json` | `8b3639413e3d0d74b5d7c6af8e66251e7b62e7a00f5736a031d2e6fa97aaa6d1` |

本轮未来需要、但本次没有读取或取得的输入：E ensemble标识及trajectory manifest、固定0–59的raw-gauge逐配置SHA、generation绑定、生成器/action/ensemble参数及trajectory间隔；远端GPU/QUDA/PyQUDA/MPI/device/precision/build信息；每配置12-RHSpropagator hash、iteration/residual/time与correlator hash。不能用未来事后checksum替代采集时receipt。

未来新确认程序及其依赖需要单独冻结：measurement contract、new reference/model/optimizer、fold/block/covariance/bootstrap、fit-adequacy校准与summary/plot程序、软件版本与浮点精度、seed manifest。现有`measure.py`与旧protocol本轮保持原样；若后续确认流程无法在新文件中适配，须另提可审查改动，不得借本草案绕过旧reference failure的preflight。

## 7. 测量/分析后的必交图与文字表

本轮新增的D-only诊断图是gap profile与确定性multi-start端点轨迹；它们回答质量gap退化和搜索路径依赖，不是重复有效质量图或候选评分图。若未来获批测量，报告必须同时交以下结果，不能只交PASS或单张质量图：

- 逐配置identity/residual/iteration/time图与表；planned60、measured、missing、nonfinite、未收敛分母及原因；setup、solve、total时间分开。
- 三reference通道correlator与M1/M2拟合曲线、带协方差约定的残差图；所有窗口m0/m1/gap区间图、boundary频数、profile/multistart和amplitude/condition诊断；保留失败draw，说明条件区间的分母。
- E有效质量与sink-power图、固定窗口标识；与既有D图并列时明确独立链、各自配置/块数，禁止把同链多通道当独立重复。
- 协方差特征谱、rank/floor命中、block5/10质量/SE敏感性图；短块和近似p只作诊断，不用选出最好结果。
- D–E独立reference一致性及质量差区间图；描述性统计与新确认统计分别标记。图注明D已参与设计、不pool、共同偏差仍可能存在。
- 决策表逐行填入证据路径、hash、数值、阈值版本、FAIL/ABSTAIN/INCONCLUSIVE原因；解释哪些命题得到支持、哪些仍未建立。拟议adequacy模拟若开展，交逐DGP/cell size/power的MC区间图与失败/弃权表，不能冒充物理coverage。

本轮不搜索candidate、不算candidate score，因此不产出伪造的paired-risk/physical-score图。若未来另外授权candidate与盲validation，须在其新冻结计划中补齐paired risk、anchor偏差/一致性、失败/弃权和共享访问receipt；本方案不预先批准该阶段。

## 8. 方案局限与待用户批准的具体内容

60配置仅12个主块，M2有8个自由参数、名义窗口15观测分量且协方差秩亏；短窗口和block10很可能产生弃权。这里不以通过为目标放宽门槛，需用户判断该固定样本预算是否值得投入。独立E能减少数据驱动选择偏差，但不能修复共同测量/物理偏差、精确证明最低态身份，或为percentile/近似chi-square提供物理coverage。

请在任何E测量前明确批准：①有限确认命题而非基态认证；②唯一主M2、signed amplitudes及固定通道/窗口/质量域；③N=60、block5/10、固定metric/正则化、draw数与seeds；④上述保守筛查阈值和adequacy门的实现/独立MC核验要求；⑤失败即弃权、不救活/不补样、E只使用一次的规则；⑥canonical来源manifest、完整图文交付和只访问E0–59的单独测量授权。模型/数值方案审批与实际测量授权应分别记录，不能默认草案获批就允许集群执行。

若用户不接受某些筛查值或估计方法，应在E未看时修改并送审；只要实现、统计核验或授权尚缺一项，本文件保持DRAFT，`physical_score=null`，TODO继续保留。
