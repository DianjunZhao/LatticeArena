# Wilson estimand 决策记录：有限-T Creutz 与基态离散静态力

**目标选择：有限-T Creutz 与基态离散静态力两条独立 lane 已由用户选择；统计协议仍为 `PROPOSAL_NOT_FROZEN`，`physical_score=null`。**

用户当前决定同时研究有限-T Creutz 与基态离散静态力。两者共享 raw loops 和配对 draw，但拥有不同目标和认证条件；有限-T 数值精度不能替代基态污染控制。下面§0是当前开工依据；§1–§7保留此前绝对势/力选择的审阅推导，其中“待选择分支”的历史表述已由本次决定取代。绝对势不再是当前主目标，相关外锚推导保留作参考。此次更新仅编辑本文和TODO，没有新拟合、bootstrap、测量或未开放split访问。

## 0. 当前选择：两条 estimand lane 分开交付

**决定性约束：有限-T χ 是给定算符的观测量，基态 f₀ 是其可受控的大-T解释；前者获得高精度数值，不足以认证后者。** 两条lane均保留，尚未由用户指定整体primary claim的优先级，不把它们暗中合并为一个分数。

| 项目 | Lane C：有限-T Creutz | Lane F：ground-state discrete force |
|---|---|---|
| 选定的目标定义 | 对指定kernel k、格点几何/作用量与整数R,T，`χ_k(R,T)=−log[<W_k(R+1,T+1)><W_k(R,T)>/(<W_k(R+1,T)><W_k(R,T+1)>)]` | `f₀(R+1/2)=U₀(R+1)−U₀(R)`，`U₀=aV₀`；固定格距/体积/静态源作用量下的dimensionless基态差分 |
| lane内primary暂态 | 目标形式已定；确认性primary的R/T、kernel、比较族及容差尚未冻结。D0–99全网格只作development描述 | 科学目标形式已定；提取方法、primary窗口/谱模型、容差和污染控制尚未冻结，当前`GROUND_STATE_FORCE_UNCERTIFIED` |
| lane内secondary暂态 | window-slope差分、逐T变化、paired kernel差、成本与无效样本表为辅助诊断，不充当基态判定 | 各窗口斜率差分、有限-T χ、同draw窗口漂移与谱稳定性为支持诊断；无漂移不代表污染有界 |
| 可认证内容与条件 | 冻结k/R/T、边界与normalization、正值/log有效性、相关性/block规则、共同draw、比较族/多重性、容差/失败弃权，并有独立确认数据，可认证这个有限-T观测量或其预定义差值的统计精度 | 在左列统计条件之外，还要独立、可审核的激发态与热绕行污染界，或足以识别基态并量化截断误差的谱/多T证据；总误差达到冻结精度后，才能把相应估计认证为f₀ |
| 不可相互替代处 | spatial smearing改变有限T overlap，故一般`χ_k != χ_identity`；同配置差值首先是两个有限T观测量的差，不是对共同真值的误差差 | 要宣称不同spatial smear趋于共同f₀，须确认同一静态源/作用量、时间链约定及非零基态overlap，并控制各自有限T污染；不能从χ更平滑或误差更小直接推出 |

这里“认证”均限于当前固定格距/有限体积定义。把差分解释为`a²F`需要注明离散化条件；中点标记不等于tree-level改善。未冻结格距标定或continuum/无限体积外推，不宣称连续物理力、string tension或零温极限。

方法先例只支持把两条lane分开，并不替当前数据给出误差界：Cella、Mitrjushkin 与 Viceré 直接考察有限格上 Wilson-loop `V_W(T;R)` 的 T 依赖，并提醒中等 T 上的弱变化不能普遍证明 `T→∞` 已受控；其模型/格点结论不是本项目的阈值或覆盖保证（[arXiv:hep-lat/9412017](https://arxiv.org/abs/hep-lat/9412017)）。Sommer 以静态力定义尺度并做连续极限研究，为静态力作为目标量提供方法先例，但不认证本项目的有限-T 污染或单格距外推（[arXiv:hep-lat/9310022](https://arxiv.org/abs/hep-lat/9310022)）。

### 可审核的公式 / 数据流文本图（现有D0–99 development）

```text
冻结development事务：D IDs 0–99，W[cfg,k,R,T]，R=1…4，T=4…8
  → 校验三件套hash、逐cfg identity、kernel/边界/normalization
  → 20个连续length-5配置block；复用同一5000×20抽样index
  → 对每个draw d，先取同一批block的 ensemble mean Wbar_d[k,R,T]
  → 所有必需Wbar正且有限？
      否：登记原draw index、失败原因与原planned分母，按待冻结规则失败/弃权
      是：两条lane共享这一个Wbar_d，保留其全相关性
          ├─ C：χ_{k,d}(R,T) = −log交比
          │     → 有限-T曲线 / paired χ差 / 区间 / 失败表
          │     → 只能回答明确k,R,T下的observable及其统计精度
          └─ F：Uhat_{k,w,d}(R) = −slope_w log Wbar_d
                → fhat_{k,w,d} = Δ_R Uhat_{k,w,d}
                → 窗口漂移、χ的T变化 / 谱证据 / 污染界
                → 若独立有限-T及热污染控制未闭合：UNCERTIFIED，physical_score=null
```

这是对既有证据的可审核说明，没有新增抽样。现有force/χ图文见[原D诊断](../../results/wilson_loop/development_force_diagnostic_20261121_v1/README.md)，同draw窗口漂移见[补充报告](force_window_contrast_20261121_v1/README.md)。此数据已观察，不能从其R/T中挑一个最好点再标成确认性primary。

### 下一位agent的执行顺序与停止条件

1. 分别起草C/F的分析contract：各自目标、primary/secondary对比、算符身份、精度/系统误差预算、区间和失败/弃权规则；同一raw数据的两套结论需保留交叉相关性及跨lane多重性，不称两份独立验证。整体primary claim与数值门、样本量均待研究者审阅，不静默填入。
2. C先解决“比较什么”：若比较`χ_k−χ_identity`，就把它明确写为有限-T observable difference；若希望比较共同目标的误差/风险，则须额外定义共同reference和映射，不能直接用identity当真值。F先给出哪项独立谱/多T/热污染证据能将其从`UNCERTIFIED`改判，以及其可达到的系统误差界。
3. 先交公式、上述数据流、已有数据能/不能检验的失效模式和停止条件；不重复D窗口bootstrap或相同synthetic power-cost。新校准仅在协议审阅后、结果会改变独立验证决策时规划；新生产或验证仍须授权。D100–119 gap、D120–139 validation、D140–199 shared holdout均保持未读。
4. 两lane每份后续诊断都交图或带公式/误差口径的文本表，分别列measurement cfg、独立dataset、bootstrap draw的`planned/valid/failed/abstained`分母、原因和重叠关系；不可把5000 draw当5000独立cfg。本次仅文档更新：新增planned执行=0、valid=0、failed=0、abstained=0（无执行，不是0/N错误率）。既有5000-draw contrast为planned=5000/valid=5000/failed=0/abstained=0，仍只是development统计证据。


## 1. 两个分支的目标先写清楚

用 `U_R=a V_0(Ra;a,L)` 表示在**指定静态源作用量、零点/归一化与有限格距、体积**下的目标基态能量。绝对裸势含静态源自能，不能把本格距的裸零点直接当作连续极限的物理绝对能量；若改为减除或匹配方案，须写明其定义，这本身也是estimand变化。现有数据仅为16⁴、β=6、R=1–4、T=4–8，尚无本文可用的物理格距标定或多格距外推证据。

| 审阅项 | 分支A：保留已定义的绝对势 `U_R`，引入独立anchor | 分支B：离散静态力，或明确的有限T Creutz量 |
| --- | --- | --- |
| 科学问题 | 在指定方案下估计每个R的基态能量本身；需要绝对零点一致 | 比较相邻R的能量差；若真正目标是有限T的χ，则直接报告χ，不称基态力 |
| 主estimand | `U_R`；须指明bare lattice或经减除/匹配的方案 | `f_{R+1/2}=U_{R+1}-U_R`；或另选 `χ(R,T)` 为有限T observable。二者只在受控大T/单指数极限对应 |
| 现有估计量 | `Uhat_w(R)=-slope_w log mean(W(R,T))`，三个窗口；其共同偏差未识别 | 同窗相邻差 `fhat_w=Uhat_w(R+1)-Uhat_w(R)`；或相邻R/T的Creutz ratio，见下式 |
| 能消除什么 | 有同方案外锚及有效偏差界，才能识别锚定误差；窗口一致本身不够 | 严格消除对所有R相同的势加性常数；不能消除任意R依赖偏差 |
| 识别假设 | 外锚与目标在作用量、a/L、静态源/零点方案一致；锚偏差有独立论证；相对形状误差也有界 | 作为基态力时，有限T激发态/热效应必须受控；相邻R共用配置/draw/窗口；作为有限Tχ时只识别该observable，不外推基态 |
| 现有直接证据 | 完整D0–99与reference/window图已生成；A/B与C结论不同；没有提供独立物理外锚 | D0–99已有同draw force/Creutz图、点态区间与完整draw记录；大R/window/T敏感，尚无稳定plateau证明 |
| 仍缺的误差控制 | 外锚统计误差、其共享系统误差上界、R依赖形状误差、有限T/有限体积/格距误差、多重比较 | 有限T和R依赖共同误差、空间差分误差、有限体积/格距误差、window/Creutz方法差、多重比较 |
| 会改变选择的观察 | 研究问题需要绝对势且获得同方案独立锚与可审计偏差界；仅增加seed/窗口不构成此观察 | 研究问题确认只需势差，且后续预声明的有限T/离散化证据足以支持目标精度；若需绝对零点，则force不能回答 |
| 当前缺口的状态 | `REFERENCE_UNIDENTIFIABLE`：没有锚及误差界，停止physical score | `GROUND_STATE_FORCE_UNCERTIFIED`：可描述development曲线，不认证基态力或优胜核 |
| 当前允许做什么 | 审阅锚候选及其共享失效模式，定义误差预算；不测新链/validation | 审阅选定estimand、窗口或χ规则及误差预算；不从已看数据挑最稳定R/T作为盲验结果 |

## 2. 共同偏差示意：清楚说明分支能回答的范围

下表是解析示意，不是新增模拟或生产数值；依据[现有不可识别性推导](reference_gate_design.md#9-共同偏移的不可识别性解析诊断不是生产结论)。

| 偏差模式 | 绝对势曲线的变化 | 同窗相邻差的变化 | 可从现有window-z发现吗？ |
| --- | --- | --- | --- |
| `W'(R,T)=exp(-δT)W(R,T)` | 所有R、所有窗口同时竖直平移δ | `Δ_R δ=0`，力不变 | 不能；window差、其SD及z不变 |
| `W'(R,T)=exp(-g(R)T)W(R,T)` | 每个R的所有窗口同时移g(R) | 残留 `g(R+1)-g(R)` | 不能；即使力已偏，逐R窗口差仍不变 |
| `log W=log A_R-U_R T+ε_R(T)` | 有限T残差经斜率投影生成window-dependent或common bias | 残留相邻R的斜率偏差差值 | window漂移有时可见，但没有漂移不证明偏差为零 |

所以family-wise校准只能控制**已定义比较族中**统计错误率，不会识别上述共同模式。把2.5调小、增加bootstrap draws、同数据加一个拟合或更换smearing核，均不能充当缺失的物理锚。

## 3. 分支A：外锚需要交付的最短证据链

设未来独立方法给出同方案锚 `A_*`，估计 `U_{R_*}`。锚定估计可写为

\[
\widetilde U_R=\widehat U_w(R)-\widehat U_w(R_*)+A_*,\qquad
\widetilde U_R-U_R=[b_w(R)-b_w(R_*)]+b_A+\eta_R.
\]

这里 `b_A` 是锚系统误差，`b_w(R)-b_w(R_*)` 是原估计量的相对形状偏差，`η_R`代表需按联合相关性处理的统计波动。若有已论证界 `|b_A|<=B_A`、`|b_w(R)-b_w(R_*)|<=B_shape(R)`，则系统误差最多以 `B_A+B_shape(R)`相加；没有独立性证明，不把两界平方和当上界。相同ensemble或共用输入的统计协方差须保留，方法独立不等于样本统计独立。

单R锚只解决常数模式在该点的定位，**不会自动证明其余R的形状无偏**。若原偏差是任意g(R)，需要多R锚或可审计的形状假设/界。仅在方案中先定义 `U(R_*)=0` 是合法的减除势目标，但不是观测到了原来的绝对零点。

| 锚候选类型（仅供审阅） | 必须证实 | 共用/剩余失效模式；当前状态 |
| --- | --- | --- |
| 另一套可分辨低能谱的方法，如不同时间范围/算符基的可控谱分析 | 基态分离、截断/有限T上界、相同静态源与归一化；需证明能约束当前共同偏差 | 相同短T/模型/ensemble可共享污染；“第二方法一致”本身不提供偏差界；本轮未提供此锚 |
| 经受控匹配的外部理论/独立计算 | 同作用量/a/L/零点或有误差的转换，匹配域、截断和外推界 | 连续方案常数与裸格点零点不能直接等同；误差可能共享截断/尺度设定；本轮未提供可匹配锚 |
| 独立HMC链或APE/stout对照 | 只能首先证明新样本/新重叠结构 | D/E seed独立不保证有限T偏差独立；E HMC receipt不是Wilson基态锚；当前不接受为现成外锚 |

**改变该分支可行性的观察**：给出具体锚对象、原始来源、同方案映射、其统计协方差及`B_A/B_shape`的可审核来源，且总误差可达到研究者指定容差。没有这组材料时维持`REFERENCE_UNIDENTIFIABLE`，不能靠A/B窗口提案通过发分。

## 4. 分支B：离散力与有限T Creutz必须二次区分

对同一窗口/同一draw，定义

\[
\widehat f^{(w)}_{R+1/2}=\widehat U_w(R+1)-\widehat U_w(R),\quad
\chi(R,T)=-\log\frac{\overline W(R+1,T+1)\overline W(R,T)}
{\overline W(R+1,T)\overline W(R,T+1)}.
\]

所有loop先ensemble均值再取log/ratio，不先取逐配置势再平均。`f`与χ是dimensionless lattice quantities；用空间步长a解释时`Δ(aV)`对应`a²F`的差分估计，不是直接以物理单位给出的连续力。将差分标在中点`R+1/2`不等于做了tree-level改进或连续外推。只有在光滑势与受控a展开等假设下，才能分析中点差分相对连续导数的截断误差；本16⁴单格距结果没有证明该假设/误差界。

对上节的有限T残差，Creutz有

\[
\chi(R,T)=U_{R+1}-U_R-
[\epsilon_{R+1}(T+1)+\epsilon_R(T)-\epsilon_{R+1}(T)-\epsilon_R(T+1)].
\]

按当前用户选择，这两项作为两条独立 lane 同时保留并分别说明科学用途：**ground-state离散力**需要有限T偏差控制；**有限T χ**把T直接写入estimand，不宣称已经获得ground-state力、string tension或continuum结果。前者不能因后者可精确测量而自动成立；两者也不能混成一个共同的“smearing误差改善”分数。

现有D-development的直接证据（均为点态95% percentile区间，未做family-wise校准）：

| identity量 | 已有观察 | 对选择的含义 |
| --- | --- | --- |
| `f(1.5)`三窗 | 0.186242、0.188555、0.188589 | 可描述其相近；不能由一个R的近似稳定外推所有R |
| `f(2.5)`早/nominal/晚窗 | 0.117258、0.102391、0.088838 | 仍有明显窗口敏感性；差的显著性需同draw对比，不能由点值差单独裁决 |
| `f(3.5)`晚窗 | 0.141671，区间[0.045839,0.261250] | 不确定度宽；不支持用当前样本确证稳定plateau |
| `χ(3,7)`，即Rmid=3.5、T7→8 | 0.181479，区间[-0.063389,0.494814] | 零值在该点态区间内表示精度不足，不能把负下界截为0或称测得负物理力 |

数值来源：[force报告第20–32行](../../results/wilson_loop/development_force_diagnostic_20261121_v1/README.md#identity-kernel-t-window-sensitivity)、[Creutz原表identity/T7/Rmid3.5行](../../results/wilson_loop/development_force_diagnostic_20261121_v1/creutz_force_paired.csv)。已有[window-force图](../../results/wilson_loop/development_force_diagnostic_20261121_v1/identity_force_by_window.png)及[Creutz配对图](../../results/wilson_loop/development_force_diagnostic_20261121_v1/creutz_force_paired_deltas.png)可与本表一起审阅。本轮没有重算这些数值或重绘图。

**改变该分支可行性的观察**：研究者确认科学问题只依赖势差/明确有限T量；若目标为基态力，另有预声明的有限T污染界及足够精度的多窗口/谱证据，且R依赖偏差、格距/体积误差在目标容差内。现有相邻差消常数的负控和power-cost模拟已经完成，不再重复它们来充当上述观察。

## 5. 两分支共同的冻结清单与失败/弃权

| 待冻结内容 | 审阅时应写出的选择 | 失败/弃权边界（当前只列要求，不定数值） |
| --- | --- | --- |
| 精度目标 | 每个R的绝对容差`ε_R`及允许系统误差；力近零时优先绝对精度 | 只有宽区间或未界定系统偏差：`INCONCLUSIVE`；不能把未拒绝零差当等价性证明 |
| 比较族 | R、kernel、所有window/χ时间、锚和方法对比；明确primary与辅助 | 看结果后删除失败R/T或挑胜核：需新开发协议，不能沿用原盲验解释 |
| 多重性 | 定义联合零假设/等价区间；选择并冻结校准办法及其适用DGP/coverage证据 | 单项z<2.5或点态95%不代表联合coverage；无有效校准则只报descriptive |
| finite-T/格距/体积 | 目标是当前格点observable还是物理外推；每项偏差界/模型假设/停止条件 | 无偏差证据时不能把plateau或单格距值升级为基态/连续极限认证 |
| 相关性和block | 同一draw用于全部R、T、kernels及比较；block规则和有效独立样本数 | 现有20blocks不是5000独立样本；块长敏感性不足或独立块太少则弃权，不换块长追PASS |
| log/ratio有效性 | 所需点均值和每个draw均值均有限且为正 | 非正/非有限时保留失败索引、原因和原总draw分母；不得删除后只报“有效样本通过” |
| z/风险分母 | 拟用SD/anchor风险等分母定义、单位、近零floor | 任何必需分母非有限/<=冻结floor则`ABSTAIN_DEGENERATE_DENOMINATOR`；不能clip后给PASS。现有window提案64eps floor尚非生产规则 |
| 系统误差识别 | 锚偏差/相对形状界或force的R依赖残差界 | 缺识别：`REFERENCE_UNIDENTIFIABLE`或`GROUND_STATE_FORCE_UNCERTIFIED`；不以增加draws补救 |
| 停止与新增工作 | 先判断哪个观察会改变分支；再冻结可检验假设、样本量/MC精度、失败率与预算上限 | 无法改变选择则不追加固定toy；达到预算仍宽区间，停止并报`INCONCLUSIVE`，不自行开validation |

例如，若探索所有现有6个候选对identity的force差，三个Rmid×三个窗口已是54个对比；若同时探索四个相邻T的Creutz差，又有72个，共126个相关对比，尚未计入anchor或方法差。此处只是由已知维度计算比较族大小，**不是冻结126项为最终族**。如果primary只保留一种预声明估计量，必须在未来确认性数据前固定；D0–99已被观察，不能用于宣称事先选择。

误差条跨零不等于偏差受控；要证明稳定/等价应把预先规定容差与同时区间联系起来，而不是把“没有检测到窗口差”作为ground-state认证。后续若做新校准，需针对已选estimand和新失效模式，报告独立dataset数、MC误差区间、有效/失败/弃权数；本稿不启动校准、不许诺未计算的样本量/功效。

## 6. 已有证据与本轮范围

- [reference报告](../../results/wilson_loop/reference_gate_d_development_20261121/REFERENCE_REPORT.md#candidate-comparison)：A/B point-max=2.0965152，C centered=2.7408156、uncentered=4.0843804；候选门2.5下结论不同，尚未校准，不挑一个生产门。
- [APE/stout报告](../../results/wilson_loop/development_paired_diagnostic_20261121/PAIRED_REPORT.md#配对结果)：风险比下降仅对已观察development的precision+spread泛函；498/500有效outer draws，2个失败保留；与force报告的5000/5000不同实验分母不能混合。成本对比是同job顺序测量，不是matched-walltime物理优越性。
- [已有力/Creutz报告](../../results/wilson_loop/development_force_diagnostic_20261121_v1/README.md)：有同draw开发曲线与点态区间；没有finite-T上界、family-wise coverage或确认性比较协议。两条目标lane已由用户选择，但各自primary R/T、比较族及容差仍待冻结。
- D/E的F4 ΔH/接受率与P4 CPU controls已经完成；旧B receipt缺口不阻塞当前目标审阅。较早61行aggregate-loop-hash异常仍未解释；保留TODO的历史审计，不被最终100行identity通过自动抹去。

**研究者仍需决定的最小集合**：两条lane各自的 primary/secondary R/T或窗口、统计/系统误差容差、comparison family与跨lane多重性、失败/弃权规则；F lane另需可审核的有限-T激发态/热污染界或基态谱识别证据。lane目标形式已选，无需再问绝对势外锚；没有这些分析与物理误差条件之前，方案只供审阅，`physical_score=null`。

初版决策稿更新时只改了文档，没有测试或新图；后续增量见§8。所有这些本地审阅均未复制或读取D100–119、D120–139、D140–199，也未修改冻结protocol或生产实现。这里的清晰文字表与偏差示意不冒充新的物理证据。

## 7. 2026-11-21 补齐同draw窗口contrast后，决策缺口仍在

[配对窗口漂移报告](force_window_contrast_20261121_v1/README.md)及[图](force_window_contrast_20261121_v1/late_minus_early.png)已补齐§4所说的同draw差：identity Rmid=2.5的late−early为−0.028420，点态95%区间[−0.051845,−0.001723]。六个候选相对identity的漂移变化均为正，约0.00993–0.01371，但所有六个difference-of-differences区间均跨零。它支持“现有数据的窗口敏感性需要处理”，没有认证smearing改善，更没有识别共同R依赖偏差。其他R/窗口对均在CSV中，117项比较未经family-wise校准；这里提及R2.5是已经打开数据后的描述，不是新冻结primary。

原冻结development transaction、protocol和5000个draw身份逐项匹配后才构造差值；5000/5000 valid。原始逐draw force、漂移和DoD数组已保存。上述内容是本稿§6之后新增的CPU分析，与§6“本轮没有新图”的历史范围应按时间区分。目标选择现已完成；仍需冻结两条lane各自的容差、识别假设、primary/secondary比较族与下一份确认数据的方案。仅增加窗口draw精度无法把当前状态改为ground-state认证。

## 8. 解析污染界附记（2026-11-21）

基于正前向谱的有限-T Creutz—基态离散力偏差上界和 `Q`/能隙敏感度图已另存于[图文分析](../../results/wilson_loop/ground_state_bound_20261121_v1/README.md)。图中参数只作示意，脚本没有读取Wilson loops。该推导增加了F lane的可审阅误差模型，但有限 `Nt=16` 热绕行项仍需独立处理，且真实 `Q`/gap 不能从当前短时间窗直接认定。公式实现的定向测试7项通过；它不冻结R/T、family、容差或生产门。下一项仍是研究者审阅C/F两个analysis contract，而不是复跑现有bootstrap。

## 9. 2026-11-22 双 lane 候选协议表（维持未冻结）

用户要求维持 `NOT_READY/UNCERTIFIED` 与 data seal；本节将目标选择转成未来可审阅的两套统计路径，不选 R/T/kernel、不填精度阈值或多重性数值。D0–99 已观察，任何从这批数据挑出的 R/T 只可作 development 描述。

| 合同项 | Lane C：有限-$T$ Creutz | Lane F：基态离散静态力 |
|---|---|---|
| 目标 | 对明确 kernel/几何下的 `χ_k(R,T)` 作有限格 observable；paired `χ_k−χ_ref` 首先是两个 observable 的差 | `f₀(R+1/2)=E₀(R+1)−E₀(R)`，固定当前静态源/作用量/格距/体积 |
| 可审阅的比较对象 | 单 lane `χ` 的误差精度；candidate−identity 的有限-$T$ observable difference；或有独立共同目标时的误差改善。Identity 不能自动充当真值 | 谱提取器之间的 `f₀` 差、或 smearing estimator 相对独立共同谱目标的风险差。有限-$T$ `χ` 不能直接重命名为 `f₀` |
| 统计数据流 | 对每个共同 block draw 重新形成所需 `<W>` 均值，再算 Creutz ratio 与 log；同一 index 用于全部 k/R/T，保留相关性 | 每个 draw 内对所有 R/T/kernel 共用 block indices，重算完整谱/force estimator；不可把 5000 draws 当独立配置 |
| R/T/算符 | 未来预先指定主 R/T、spatial kernel identity及比较族；其余全记 secondary | 未来预先指定谱窗口/算符矩阵、R点和相邻差分；多 R 或多方法扩展须计入 family |
| 数值失败 | 任一必需 loop mean 非正/非有限，ratio 或 `log` 无定义：保留原draw index、原因与 planned denominator，状态按协议 ABSTAIN/INCONCLUSIVE | spectrum fit 未收敛、质量排序/mode tracking不稳定、Q/gap不可辨识：保留失败/边界/协方差信息，不能筛掉后只报告有效拟合 |
| 物理系统误差 | 作为有限-$T$ observable，不要求把它外推基态；若作基态解释，需另过 F lane | 要提供可审核 excited-state bound 或独立谱/多-$T$识别；`Q`/gap 和 `Nt=16` 热绕行分别有界；固定格距/体积结果不等于 continuum/infinite-volume force |
| 主要可选统计路径 | (C1) common-block paired bootstrap 作描述性/precision CI；(C2) family-wise max statistic或Bonferroni simultaneous intervals。使用哪个取决于未来 family/coverage 校准，不在本稿冻结 | (F1) 有共同 index 的相关多态/GEVP拟合并对 truncation做外部敏感度；(F2) 使用 `log(1+Qe^{-ΔT})` 型污染界，只有 Q/gap有独立上界才可收敛到 ground-state claim；另行加入 thermal bound |
| 通过不了时 | 若目标只要求 finite-T observable，可保留该 observable 的有限样本描述；没有冻结目标/family/正值规则时不作确认性声明 | 维持 `GROUND_STATE_FORCE_UNCERTIFIED`；无 Q/gap、thermal或多-$T$识别证据时不报基态物理分数 |

```text
冻结的 loop transaction + D0–99 identity（只作development）
  → 所有 kernel/R/T 的 planned rows 与相同 block-draw IDs
  → Wbar finite and positive?
       no → 保留失败draw/原因/分母；停止该draw，不挑剩余的有利比值
       yes
        ├─ C: 计算有限-T χ及预声明的observable contrast
        │    → 只作指定k/R/T的结果；family/precision未审阅则标development-only
        └─ F: 谱/多T/Q-gap分析 + 独立Nt热绕行界 + R相邻差
             → 任一污染项未被独立约束：GROUND_STATE_FORCE_UNCERTIFIED
             → 全部方案可审阅后再申请新确认数据；不能从D0–99回填独立认证
  → 汇报两lane共同draw协方差、planned/valid/failed/abstained及其重叠
```

候选图沿用[Q-gap污染敏感度图](../../results/wilson_loop/ground_state_bound_20261121_v1/contamination_sensitivity.png)；其参数是示意输入，不是 D 数据拟合。后续任何新图需同时区分有限-T统计区间与基态系统污染，不得把窄bootstrap CI当作污染界。当前不新增模拟/测量/GPU，不读D100–119、D120–139或D140–199；本节的方案量=0，planned/valid/failed/abstained 均为 0（无执行，并非错误率为0）。

## 10. 有限 `N_t=16` 热迹项：与 `Q/gap` 分开（2026-11-22）

已补 transfer-matrix 表达、污染分解和停止流程，完整表格见[独立热污染审阅报告](../../results/wilson_loop/finite_nt_thermal_bound_review_20261122/README.md)。设全周期长度为 `N_t a_t`，loop 时间为 `t a_t`。有限温度迹在无静态源 Hilbert 空间求和，并在中间插入静态 `Q\bar Q` 扇区：

\[
W_k(R,t;N_t)=Z_0^{-1}\sum_{n,m}
e^{-a_t(N_t-t)E_n^{(0)}}e^{-a_t t E_m^{(Q\bar Q,R)}}
|\langle n,0|O_{k,R}|m,Q\bar Q\rangle|^2.
\]

以真空/基态项归一化后，主要结构分别为静态源激发 `q\sim Q_k e^{-a_t\Delta_Q t}`、热迹无源态 `h\sim H_k e^{-a_t\Delta_0(N_t-t)}` 与二者的混合项 `x`。因此固定 `N_t` 增大 `t` 会减小 `Q/gap` 指数、却缩短热抑制区间；不能只用前向谱说明 ground-state plateau。`N_t=16`候选`t=4…8`对应补时间12…8，未提供能隙与kernel-dependent overlap，故不填污染数值。

若 `log W=log A_k(R)-a_tV_0(R)t+\delta_k(R,t;N_t)`，则有限时间 Creutz 满足

\[
\chi_k(R,t)=a_t[V_0(R+1)-V_0(R)]-\Delta_R\Delta_t\delta_k,
\]

其中 `\Delta_R\Delta_t\delta=\delta(R+1,t+1)+\delta(R,t)-\delta(R+1,t)-\delta(R,t+1)`。Lane C可将`\chi_k`作为有限时观测量；Lane F必须分别约束Q/gap、热迹和混合项在该双差层的贡献。缺任何一项的独立上界，就维持`GROUND_STATE_FORCE_UNCERTIFIED`。本轮无 loop 拟合/MC/GPU，也未打开 gap、validation 或 shared holdout。有限温度静态介子相关函数的迹分解见[Bala et al., Appendix A](https://arxiv.org/abs/2110.11659)；零温 Wilson-loop谱展开见[Brambilla et al., Eq. (3)](https://doi.org/10.1103/PhysRevD.105.054514)。

**零温 `Q/gap` 界与有限 `N_t` 的接合检查：**旧敏感度报告的 `|χ−f₀|≤log(1+Qe^{-Δ_min t})` 在正的零温前向谱下成立：`χ−f₀=g_{R+1}−g_R`，两个`g_R=log[(1+ρ_R(t))/(1+ρ_R(t+1))]`均非负，因此差的绝对值最多为其中较大的单点上界。有限`N_t`加入`h∝e^{-Δ_0(N_t−t)}`和混合项后，`δ=log(1+q+h+x)`不再保证随`t`单调，不能沿用该单点界。若未来有独立`Q,H,X,Δ_Q,Δ_0`上界，可令

\[
B_k(R,t)=\log\!\left[1+Q_k(R)e^{-t\Delta_Q(R)}+H_k(R)e^{-(N_t-t)\Delta_0}+X_k(R)e^{-t\Delta_Q(R)-(N_t-t)\Delta_0}\right]
\]

（所有能隙均以格点单位表示），再用四角和给出保守 force-level bound：

\[
|\chi_k-f_0|\le B_k(R+1,t+1)+B_k(R,t)+B_k(R+1,t)+B_k(R,t+1).
\]

完整推导和适用条件见[有限-Nt报告 §5](../../results/wilson_loop/finite_nt_thermal_bound_review_20261122/README.md)。此式只形成未来误差预算的充分条件；当前没有这些 envelope 数值，也不据此通过基态门。
