# wilson_loop：CPU 验收结论与下一阶段

### 2026-11-22 最新交接：两条 lane 已选，维持 UNCERTIFIED 与封存

用户已选择同时保留有限-$T$ Creutz 与基态离散静态力两条不同 estimand lane，并要求当前 `NOT_READY/UNCERTIFIED` 与数据封存不变。不得再问二选一，也不把现有 D0–99 development 诊断升级为确认性 R/T 选择、基态认证或物理 score。已有[双 lane 决策稿](estimand_decision_review.md)§9和[正谱 Q-gap/有限-$T$ 污染敏感度图文报告](../../results/wilson_loop/ground_state_bound_20261121_v1/README.md)已列 Lane C/F 目标、候选统计路径、失败分母和文字数据流；不要重写协议或重跑窗口 bootstrap、force 图、power-cost 或同一 toy。对 D0–99 选择出的点一律标 development-only。不得启动 GPU、打开 D100–119、D120–139 或 D140–199；`GROUND_STATE_FORCE_UNCERTIFIED`、`physical_score=null` 和本 TODO 保留。

**2026-11-22 有限 `N_t=16` 理论审阅已完成：**见[谱分解、误差表与文字数据流](../../results/wilson_loop/finite_nt_thermal_bound_review_20261122/README.md)。transfer-matrix 展开将静态源激发项 `Q exp(−Δ_Q t)`、热迹无源激发项 `H exp(−Δ_0(N_t−t))` 和混合项分开；有限 `N_t` 下增大 `t` 会降低第一项的指数、同时缩短第二项的抑制区间。`N_t=16`、候选 `t=4…8` 的补时长是12…8，但缺少独立的谱间隙与 kernel-dependent overlaps，不能给出污染数值。Creutz lane可作为固定`k,R,t`的有限时观测量；ground-state force lane仍须将对数污染传播到`Δ_RΔ_t`层并满足事前误差预算。没有拟合、模拟或打开封存split。引用的有限温度迹表示与零温 Wilson-loop 谱表示分别来自原始论文[Appendix A](https://arxiv.org/abs/2110.11659)和[static-force spectral decomposition](https://doi.org/10.1103/PhysRevD.105.054514)。
**零温界的有限 `N_t` 接合审计也已完成：**已有 `|χ−f₀|≤log(1+Qe^{-Δt})` 仅在正的零温前向谱下成立；加入热迹与混合项后不能沿用单点 `Q/gap` bound。报告 §5 现在给出带独立 `Q/H/X/Δ` envelope 时的四角和 force-level 保守界。当前这些输入均未测得，所以它是未来认证合同，不构成当前 pass。

**当前可执行边界：**不再从 D0–99 做拟合或选择确认性 `R/T/kernel`，不重跑现有 `Q/gap` toy/窗口 bootstrap，不启动 GPU，也不打开 D100–119、D120–139 或 D140–199。后续工作应在研究者决定 lane 内 primary、精度/多重性以及 ground-state 的谱与热污染容差后，先完成独立谱方案和 matched-`N_t` 方案的可审阅设计；在界限未闭合时继续 `NOT_READY/UNCERTIFIED`、`GROUND_STATE_FORCE_UNCERTIFIED`、`physical_score=null`。

### 当前用户决定：有限-T Creutz 与基态离散静态力同时保留为两个 estimand lane

**目标选择已完成，确认协议尚未冻结；TODO保留，`physical_score=null`。** 用户选择有限-T `χ_k(R,T)` 与ground-state `f₀(R+1/2)=U₀(R+1)−U₀(R)`。以下历史段落中要求“选择绝对势或force/Creutz”的开工指令由本段取代；绝对势外锚不再是当前目标的前置项。两lane的新[定义、primary/secondary暂态、认证条件、公式/数据流文本图及开工顺序](estimand_decision_review.md#0-当前选择两条-estimand-lane-分开交付)已补齐。

**最新边界确认（2026-11-22）：**用户要求维持 `NOT_READY/UNCERTIFIED` 与数据封存状态。两条 lane 的目标形式保持已选，但确认性 R/T、kernel、比较族/多重性和基态谱/热污染误差界仍未冻结；不能把目标选择误写成物理认证或测量授权。有限-$N_t$解析已在文首链接报告中完成；当前没有新的数据内 CPU 工作可以弥补独立谱和热污染界。后续先等研究者审阅所需物理容差和确认方案，再决定是否申请新的谱/多-$T$证据。不得启动新 GPU、不打开 gap、validation 或 shared holdout。`GROUND_STATE_FORCE_UNCERTIFIED` 与 `physical_score=null` 保持，本 TODO 保留。

- **Lane C（有限-T Creutz）**：primary目标形式为指定kernel/R/T下的χ；确认性R/T、kernel、比较族、容差与数值门尚待审阅。window-slope force、T依赖及成本为secondary诊断。χ可以在无需基态解释时作为有限T observable，但不同smear一般改变其overlap与有限T值，故paired `χ_k−χ_identity`是观测量差，不能直接写成对共同真值的误差改善。冻结统计contract并有独立确认数据，才能认证其精度/预定义差值。
- **Lane F（基态离散静态力）**：primary目标为固定格距/体积/静态源约定下f₀；窗口估计、χ长T趋势、同draw漂移为secondary支持证据。目前`GROUND_STATE_FORCE_UNCERTIFIED`。需要独立激发态/热污染界或可辨识的谱/多T证据，不能把χ的高精度、窗口漂移小或误差条窄当作基态认证。未决定格距/continuum外推、样本量或数值阈值。

**历史接手指令（2026-11-21；lane contract 已在 §9 补齐）：**不再要求重交两套 analysis contract。当前唯一新增理论项见文首：补有限 `N_t` 热绕行边界的公式结构和所需独立输入。两lane仍可共用D0–99 draw作为development描述，但不能互相替代或称独立验证；不得从已看R/T挑确认性primary，亦不得访问D100–119/D120–139/D140–199。

### 2026-11-21 新增：同 draw 的窗口漂移与候选 difference-of-differences（CPU）

此前逐窗误差条不足以说明窗口差的精度；本轮补齐[同draw窗口contrast图文](force_window_contrast_20261121_v1/README.md)、[图](force_window_contrast_20261121_v1/late_minus_early.png)、[全部117行CSV](force_window_contrast_20261121_v1/contrasts.csv)与逐draw数组。只重放现有D0–99的5000个原block draw：冻结transaction三hash、protocol hash、原window-force逐项结果及保存的indices均完全匹配后才计算 `D=f_late−f_early` 和 `D_candidate−D_identity`。20个length-5 blocks，5000 planned/5000 valid/0 failed；5000不是独立gauge样本数。没有新生产或新模拟dataset。

identity late−early在Rmid=1.5/2.5/3.5分别为 `0.002348 / −0.028420 / 0.044858`，点态95% paired bootstrap区间为 `[−0.003148,0.007715] / [−0.051845,−0.001723] / [−0.048075,0.159858]`。Rmid=2.5给出实际窗口漂移警示；该区间未经多重性校准，不能升级为确认性拒绝。六个候选在此R的late−early漂移相对identity改变 `+0.00993…+0.01371`，六个paired区间均跨零；当前数据不能分辨“smearing减小窗口漂移”。Rmid=1.5六个候选各自漂移的点态区间不跨零，同样仅是开发期观察，不据此挑核或宣称物理偏差。

[脚本](force_window_contrast.py)拒绝覆盖已有输出；5项解析/输入self-check通过，既有force focused tests **4 passed**，图已视检。所有窗口对（nominal−early、late−nominal、late−early）、所有kernel/R和difference-of-differences均保留，不能只引用有利项。用户已选择有限-$T$ Creutz 与基态离散静态力两条独立 lane；目标选择不再是待办。**历史后续指令已由 2026-11-22 双 lane 审阅稿取代：**候选统计 contract、有限-$T$污染界、格距/体积误差项与文字数据流已经整理，不要重做。当前仍待审阅的是数值容差和确认性选择；未获审阅前，D0–99 contrast 只作开发诊断，`physical_score=null`，本 TODO 保留。

### 2026-11-21（Asia/Shanghai；2026-11-20 UTC）D 链 development 100/100 完成，A/B/C 与 APE/stout 图文诊断已运行

独立输出目录中的单配置 smoke job 128539204 已完成，D cfg 0 / HMC trajectory 401 的 NERSC checksum、raw SHA 和 loops/measurement receipt 均通过。图文诊断见 [smoke 报告](../../results/wilson_loop/s16t16d_smoke_20261120/README.md)及[候选成本图](../../results/wilson_loop/s16t16d_smoke_20261120/smoke_cost.png)：总计 463.45 s，其中 kernel 447.45 s；两种 10-step stout 候选分别耗时 173.34 s 与 176.38 s，APE 候选为 1.08–5.35 s。它只有一个配置，只能估算执行成本，不能比较物理效果。

历史稳定快照（2026-11-20 16:56 UTC，已被下列终态100/100复核取代）：98条连续记录 IDs 0–97、NPZ shape (98,7,4,5)，冻结 generation 与逐行 loops hash通过；冻结D manifest SHA=1ab67540cafe1ee12cafb3df653c47f30480e75b41b6b633dd7334c69cdd7f4d，raw gauge SHA / hmc_trajectory逐项匹配且trajectory 98/98唯一。未重读raw gauge。该时刻 scheduler仍RUNNING、elapsed 12:03:05，stdout到cfg97。

**终态与完整性（2026-11-20 17:08–17:14 UTC）**：既有 Slurm job **128540026** 以 `COMPLETED`、ExitCode `0:0` 结束，elapsed `12:15:58`（start 12:52:35 UTC，end 2026-11-21 01:08:33 集群本地时区）；日志最终到 cfg99。稳定三件套由 `check_resume(..., verify_gauge=False)` 返回100；IDs 0–99连续，NPZ shape `(100,7,4,5)`、loops全有限、generation=`dd38c39f21982307c5abc2d5093b93c2aa12ef8848d6f9136519b1f8054b619e`。最终 NPZ SHA=`da8cc5d72481475a8cd6d821692db2e21555c0bd5b1849747dc75a946dbd7209`，provenance SHA=`082ad7060e776f6e724ee02ac1de9c94e706332eb875019f3b9d1c45d4e9e82b`，marker SHA=`0ff2766e4550d0a687d051f44376af5528cb047b05c556912b50ad5c9833951a`；冻结manifest SHA仍为`1ab67540cafe1ee12cafb3df653c47f30480e75b41b6b633dd7334c69cdd7f4d`。逐配置 gauge SHA 与 `hmc_trajectory` 对照通过100/100，trajectory唯一100/100；没有重新读取raw gauge。仅将这三件套和 stdout/stderr 复制到[本地development副本](../../results/wilson_loop/s16t16d_development_20261120/)，没有复制raw gauge、gap、validation或holdout。

文件级 reference gate runner 已在完整事务上输出[development-only诊断](../../results/wilson_loop/reference_gate_d_development_20261121/REFERENCE_REPORT.md)、[窗口/配对差图](../../results/wilson_loop/reference_gate_d_development_20261121/reference_windows.png)、[signed-z图](../../results/wilson_loop/reference_gate_d_development_20261121/reference_window_z.png)和[joint-max敏感性图](../../results/wilson_loop/reference_gate_d_development_20261121/reference_joint_max.png)。在未冻结的阈值2.5下，A/B point-max提案统计量均为2.0965，显示 `PROPOSAL_DIAGNOSTIC_PASS`；C centered q95=2.7408、uncentered q95=4.0844，均显示 `REJECT_WINDOW_INSTABILITY`。三种提案给出不同结论，且未做family-wise calibration、无法发现所有窗口共有的偏移；runner状态仍为`PROPOSAL_NOT_FROZEN`，`production_score=null`，不能称reference物理认证。

新增[APE/stout配对风险与成本诊断](../../results/wilson_loop/development_paired_diagnostic_20261121/PAIRED_REPORT.md)与[风险—成本图](../../results/wilson_loop/development_paired_diagnostic_20261121/paired_risk_vs_cost.png)只使用相同D0–99开发样本、20个length-5 blocks和500×500共享draw。三个nominal T窗口下六个候选的 `risk(identity)/risk(candidate)` 点值约4.84–12.11，95% paired block-bootstrap区间下界约2.16–4.99；500次外层中498次有效、2次因identity bootstrap loop非正而保留为无效。该风险下降只是当前未认证reference上的开发样本统计量，不能证明物理势更准确或候选优于物理基线。实测每配置 `kernel+loop` 均值约：APE 5步0.75s、Stout 5步87.49s、APE 10步1.26s、Stout 10步174.79s；单GPU、同一顺序测量，不是 matched-walltime 比较。Stout约慢两个数量级而风险区间与相应APE接近；应将其作为实现效率/成本结论，不解释成物理不等价。

因此本任务仍未完成：窗口统计的解析复核已确认，同一数据上的 A/B/C 和其 family-wise 校准都无法排除跨所有窗口的共同势偏移；这是不可识别性，不是增加 bootstrap draws 或调阈值可解决的问题。推导与文本诊断见 [`reference_gate_design.md` §9](reference_gate_design.md)。候选离散静态力的 synthetic 负控现已完成：[`offset_free_force_diagnostic.py`](offset_free_force_diagnostic.py)、[图文报告与原始输出](../../results/wilson_loop/offset_free_force_synthetic_20261121_v1/README.md)显示对共同偏移的最大力差为 `6.66e-16`，人为的 R 依赖偏移产生预期相邻力差 `0.020/0.030/0.050`；聚焦测试 3 passed。该诊断只验证代数和代码，不检测真实数据的共同误差、不校验基态。用户现已选择有限-T Creutz 与基态离散静态力两条 lane；两 lane 的 estimand、比较路径、失败/弃权规则、有限-$T$污染公式和格距/体积边界已在[`estimand_decision_review.md`](estimand_decision_review.md)审阅稿中，不应再作为 CPU 待办重复起草。未完成的是确认性数值选择及独立污染证据；当前保持 `NOT_READY/UNCERTIFIED`、`GROUND_STATE_FORCE_UNCERTIFIED` 与 `physical_score=null`。D120–139 当前未获授权；D100–119保持 gap，D140–199 shared holdout继续封存。

### 2026-11-21 新增：D0–99 offset-insensitive force 数据探索（CPU，未改变 estimand）

用已完整核验、已公开的 D0–99 loops 完成了 T-window slope force 与 Creutz ratio 两种估计量的配对探索；没有读取 D100–119、D120–139 或 D140–199。脚本为 [`development_force_diagnostic.py`](development_force_diagnostic.py)，图文、CSV、原始 bootstrap 索引及输入 hashes 见[诊断报告](../../results/wilson_loop/development_force_diagnostic_20261121_v1/README.md)；聚焦 CPU tests **4 passed**。按长度5形成20个连续配置块，所有 kernel、R、T 与估计量共用5000个 block-bootstrap draws，5000/5000完整正值。identity 的 T-window force 在 $R+1/2=1.5$ 处约为0.186–0.189；在2.5处从早窗0.1173变到晚窗0.0888；在3.5处为0.0968/0.1097/0.1417，晚窗点态95%区间为[0.0458,0.2613]。identity Creutz force 在 $R+1/2=3.5,T=7\to8$ 为0.1815，点态区间[-0.0634,0.4948]。这些结果显示大R的 finite-T/window 敏感性和较宽不确定度，不支持当前样本建立稳定 plateau；APE/stout 配对差图只描述本 development 样本，不判定谁更接近真值。区间为未做 family-wise 校正的点态 bootstrap 区间，20个 blocks 而非5000个独立样本；分析没有产生 external anchor、ground-state 认证或 `physical_score`，也不授权 validation/holdout。

历史状态（约16:37 UTC，95/100；已由16:47 UTC核验更新）：约16:37 UTC对远端稳定提交三件套做只读核验：95条连续记录 IDs 0–94，NPZ shape (95,7,4,5)，generation=dd38c39f21982307c5abc2d5093b93c2aa12ef8848d6f9136519b1f8054b619e；NPZ SHA=d851226ed0681655a64ad8dcbadafc41a389b8f036b64827e6452acc3fecf406、provenance SHA=33c30c6879668619f61758854109ce07112c1fa6379fd86765a3f71908f26be5、marker SHA=2aabe784a34c5002312d1771266fb5526f564e5ee5f8ee58e72eee28b9dcb446。远端 check_resume(..., verify_gauge=False) 返回95；marker读前/读后文件hash稳定，IDs 0–94连续、loops有限、逐行loops hash及冻结generation通过；冻结D manifest SHA=1ab67540cafe1ee12cafb3df653c47f30480e75b41b6b633dd7334c69cdd7f4d，95条记录的raw gauge SHA与hmc_trajectory逐项匹配且trajectory 95/95唯一。未重读raw gauge；raw SHA和NERSC checksum来自测量时provenance。约16:34 UTC的squeue/sacct仍为RUNNING、elapsed 11:40:52，stdout最新为cfg94（441.06 s），End仍Unknown。文本进度：0–94已提交 | 95% | 5项待提交；未复制数据或运行统计分析。

历史快照（16:22 UTC bundle、16:23 UTC scheduler；当前终态与图文诊断见文首最新审计）：完整 D development IDs 0–99 作业 128540026 按冻结 RunSpec 运行（单 DCU，sbatch 请求 24 h）。16:22 UTC 只读核验远端稳定提交三件套：93 条连续记录 IDs 0–92，NPZ shape (93,7,4,5)，generation=dd38c39f21982307c5abc2d5093b93c2aa12ef8848d6f9136519b1f8054b619e；NPZ SHA=5bb5dbb0d3c96da98b8dfeb3f5c6e29f1b55d03d568017c796668209bc44d012、provenance SHA=8685438057d322f9f61758854109ce07112c1fa6379fd202cd51f90b56721261、marker SHA=a046d77f8eaef995d832e85edb14c0e5e9e921761af89b19075c8cf01752abe6、loops SHA=edf360c0dde75b63b436ec686591a8126f8c194ebd16124d7c76bc3d0879e2ce。远端 check_resume(..., verify_gauge=False) 返回93；marker读取前后稳定，IDs 0–92连续，loops全有限，逐行loops hash及冻结 generation 通过；读取冻结 D manifest 后，93条记录的 raw gauge SHA 与 hmc_trajectory 均逐项匹配，trajectory 93/93 唯一；manifest SHA=1ab67540cafe1ee12cafb3df653c47f30480e75b41b6b633dd7334c69cdd7f4d。没有重读raw gauge；raw SHA与NERSC checksum来自测量时的provenance。16:23 UTC 的 squeue/sacct 仍为 RUNNING、elapsed 11:31:08，stdout最新为cfg92（439.73 s），End仍Unknown。文本进度：0–92已提交 | 93% | 7项待提交；本轮只做状态和稳定事务/manifest 身份核验，没有复制数据或运行统计分析。

需保留的审计异常：较早两次61行快照的aggregate loops hash分别为ddcde900…与f0b7e961…。在较晚快照中，61/62行前缀 hash 与f0b7e961…及e42dfd1a…一致；差异仍集中在更早的ddcde900…快照。由于该快照没有逐行hash矩阵，无法区分早期结果被其他写入者替换与该次审计/快照错误。本地results/wilson_loop可见NPZ仅有旧版不同shape的development/validation数组和单配置smoke，没有当前D作业对应的61/62行备用bundle。16:22 UTC的93行历史bundle曾可由marker、逐行hash和check_resume独立验证；最终100行bundle也通过同类验证，但早期差异根因仍未知。作业结束后在最终报告中保留这一限制；若找到旧逐行收据或外部备份，再定位差异。完整100行终态核验前不运行reference/window、APE/stout score或统计分析。

**历史 RunSpec 分区（当前访问边界优先）：**D IDs 100–119保持 gap，D IDs 140–199继续封存；旧 RunSpec 曾把120–139列作内部验证候选，但该区间当前未获访问授权。Slurm脚本为 [wilson_d_development_20261120.sbatch](wilson_d_development_20261120.sbatch)。
### 2026-11-21 完整性复核：保留 TODO

Wilson-loop 生产测量、真实 APE/stout 配对和 physical score 尚未完成，本文件不能删除。若将“F4 的 ΔH / 接受率未做”理解为当前所有生产链，结论已过时：新 D/E 链的逐轨迹 ΔH、accept/reject、raw payload identity、自相关及图文诊断均已完成。仍缺的是旧 `protocol_v4` 所指 B 链的历史 receipt；它不阻塞当前 D 链测量，也不能用新链替代。P4 CPU synthetic gate / power-cost / nested-prefix 诊断已经完成；剩余 P4 工作是有 GPU 输入的 Wilson-loop 与 APE/stout 物理比较。

**历史完整 CPU/GPU-free suite（2026-11-21）**在当时工作树为 **385 passed, 1 skipped, 1 warning**；2026-11-22 随 Optimize matrix-free Chebyshev/sandwich CPU 增量重跑后为 **418 passed, 1 skipped, 1 warning**（命令和解释见 Optimize / Pion TODO）。唯一 skip 是缺少 CuPy 的 stout parity test；warning 是 Wilson projection rejection 测试的既有 `RuntimeWarning`。该 suite 不验证远端 QUDA、生产 APE/stout physics、reference 或 physical score。

**本次裁决与下一工作边界：**“F4 生产 ΔH/接受率未做”若指当前新链，则不正确；D/E 的 HMC receipt 和质量诊断已有图文。若特指旧 `protocol_v4`/B，则历史逐轨迹 receipt 仍缺，不能由 D/E 代替。P4 扩展控制也已有独立报告，不再重复同一 synthetic generator。用户已完成有限-T Creutz 与基态静态力的目标选择；[双 lane 决策记录](estimand_decision_review.md#0-当前选择两条-estimand-lane-分开交付)已包含候选估计量、比较族、有限-$T$/格距误差、失败/弃权规则及文字数据流，**下一位 agent 不再重交这份协议**。确认性数值仍未冻结；已读 D0–99 图只作开发证据，未获审阅和授权前不启动新 GPU、不打开 D120–139或shared holdout。

**后续指令（已由 2026-11-22 双 lane handoff 更新）：**两条 lane 的分析合同、统计路径、失败/弃权映射和有限-$N_t$ 热污染公式已形成可审阅文稿；不要重复起草，也不要从已查看的 D0–99 选择确认性 kernel/R/T。有限-T Creutz 的确认性 kernel/R/T、精度与多重性，以及基态力的谱/热污染容差和格距/体积误差仍需研究者审阅后才能冻结。当前维持 `NOT_READY/UNCERTIFIED` 与数据封存，不做拟合、bootstrap、GPU 或 split 读取。已有 force、window contrast 与 APE/stout 风险—成本结果都来自已观察的 D0–99 development 数据；未来若获准新增诊断，必须列 planned/valid/failed/abstained 分母、失败原因、图或可复查文字及适用边界。

**CPU 方法方案审阅稿已具备；不要重复起草。** [`reference_gate_design.md`](reference_gate_design.md) 已列共同数据流、A/B/C 窗口 gate 的定义差异和失败状态，给出共同偏移不可识别性的推导、离散静态力 / Creutz 的公式与有限-$T$/格距边界；双 lane 目标的具体分析合同现见 [`estimand_decision_review.md`](estimand_decision_review.md)。早期草案中的绝对势外锚是历史候选，不是当前两条 lane 的前置项。现有纯 CPU 测试和共同偏移负控均已完成；proposal 仍未冻结，没有 production score 或数据读取授权。参考文献只提供方法先例，不替本任务提供谱/热污染数值或认证当前数据。当前物理误差容差和确认性统计规则仍待研究者审阅，但不得因此重复同一 toy 或扩大 D0–99 诊断。

**历史接手指令（已完成）：**双 lane 的 estimand、候选统计路径、失败/弃权映射、文字数据流和有限 `N_t` 热绕行项审阅均已版本化；详见文首两份报告。不要重复起草或复算示意敏感度图。独立 gap/overlap、热态/混合项界仍无数据支持，所以 `GROUND_STATE_FORCE_UNCERTIFIED` 保持有效。

**历史执行指令（已完成，保留作审计记录）：**输入 manifest/raw hash preflight、单配置 GPU smoke、D IDs 0–99 development 测量、identity/receipt/失败审计、reference/window 图文及 APE/stout development 配对诊断均已完成；终态和限制见文首。不得再监控或提交旧作业，不得把旧的“reference gate 通过后测 D IDs 120–139”理解为当前授权。D IDs 100–119 保持 gap，120–139 未获授权，140–199 保持封存。未来若获准做独立确认，仍须报告逐配置 paired-risk 区间、reference/污染诊断、block-length 与 walltime 成本、失败/弃权表和解释文字；样本不足时标 `INCONCLUSIVE`。

### 2026-11-20 复核：新 D/E 链 F4 质量诊断已完成，物理 loop 对照仍未运行

本机没有 GPU/MPI 栈或本地 raw gauge 副本；远端 Kunshan 可运行 PyQUDA/DCU。本轮两条全新链已完成，并只把 receipt、逐轨迹日志、manifest 与诊断图文复制到本地，没有复制 raw gauge files。旧 live audit 已读取 S16T16/S16T16B/S16T16C 共500个 NERSC 文件，raw-file SHA 500/500匹配各自 manifest；三目录重叠 payload 相同，B/C还是同 seed replay，不能当独立 ensemble。图文与逐配置CSV见 [live archive audit](../../results/kunshan_logs/live_archive_audit_v1/README.md)。不要再索取这批 gauge bytes 或重做 ID/hash crosswalk；当前未完成的是 Wilson-loop 生产测量与 matched-cost stout/APE 配对，不是 HMC 全轨迹 receipt。

### 2026-11-20 新 HMC 生产 receipt 与诊断已完成

receipt-preserving runner [`hmc_production.py`](hmc_production.py) 与[诊断器](hmc_production_diagnostic.py)通过本地 synthetic receipt 图文验证与 Kunshan CLI / Slurm `--test-only`。主链 protocol [`hmc_chain_20261120.json`](hmc_chain_20261120.json) 为16⁴、β=6、seed20261120、热化400、BAB(120 steps, τ=0.5)；job **128526595** 完成1396条轨迹，其中996条生产、982次接受，保存200个配置，raw payload hash 200/200通过。接受率 0.98594，exact binomial CP95 [0.9765,0.9923]；ΔH 均值0.00117、SD0.06184；plaquette均值0.5936106、初正配对τint约3.76。receipt、逐轨迹表、自相关/block表与四张图见[主链诊断](../../results/wilson_loop/hmc_production_20261120/diagnostic/README.md)。

独立 anchor chain protocol [`hmc_anchor_20261121.json`](hmc_anchor_20261121.json) 使用seed20261121、另起随机SU(3) links、热化400；job **128528670** 完成896条轨迹，其中496条生产、483次接受，保存100个配置，payload hash 100/100通过。接受率0.97379，exact CP95 [0.9556,0.9860]；ΔH均值0.00320、SD0.05585；plaquette均值0.5937074、τint约4.03。见[独立链诊断](../../results/wilson_loop/hmc_anchor_20261121/diagnostic/README.md)。[跨链图文对照](../../results/wilson_loop/hmc_chain_comparison_20261120/README.md)显示 plaquette 均值差9.68×10⁻⁵；按 trajectory block length 1/2/5/10/20/50，其对 combined block SE 的比为3.29/2.59/1.97/1.60/1.30/1.01。block sensitivity 提示误差受自相关处理影响；两条单链的 acceptance/plaquette诊断不证明平衡、topological tunneling或物理正确性。`physical_status`仍为`NOT_RUN`。

本轮本机只读复核再次确认 D receipt/trajectory/manifest 的 200/200 和 E 的 100/100 行身份、trajectory 与记录 hash 一致；但本地副本中原始 NERSC 文件为 0/200 和 0/100，严格 `verify_inputs` 因缺失配置 0 的原始文件而不能在本机重算 payload SHA。逐字节 200/200、100/100 结论仍由 [Kunshan live archive audit](../../results/kunshan_logs/live_archive_audit_v1/README.md) 的远端 raw-file 检查支持；本机复核只覆盖 receipt / log / manifest 内部一致性。

审计基线：此前全套 CPU / GPU-free 测试为 **170 passed, 1 skipped, 1 warning**；新增 Optimize 异常收据和 Pion bound-count 审计后的历史快照为 **222 passed, 1 skipped, 1 warning**。加入 D-only gap-profile / multi-start 后为 **243 passed, 1 skipped, 1 warning**；加入 Optimize contract tests 后为 **254 passed, 1 skipped, 1 warning**；加入 Pion 稳定两态执行器和 bootstrap receipt 后曾为 **265 passed, 1 skipped, 1 warning**；加入 Wilson 文件级 reference runner 后，最新全仓复跑为 **274 passed, 1 skipped, 1 warning**（2026-11-20，`PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest -q -p no:cacheprovider -rs`）。唯一跳过项是本机缺少 CuPy 的 stout parity test；warning 是已知 Wilson projection rejection `RuntimeWarning`。F4 新 D/E 链逐轨迹 ΔH/接受率及 P4 CPU synthetic controls 已完成；本文件仍保留，因为 Wilson-loop D production measurement、真实 APE/stout paired physics result 与正式 physical score 尚未完成。

### 2026-11-20 CPU 续查（提交 D 链 GPU 作业前的状态截面）

新增 [D 链 RunSpec](protocol_d_20261120.json)，绑定 HMC 输入 manifest SHA-256 `1ab67540…7f4d` 与测量/APE/stout/统计/身份源码 hashes。Wilson split 固定为 D IDs 0–99 development、100–119 gap、120–139 internal validation；D IDs 140–199 继续封存为 Pion/Optimize/Wilson 共用 blind holdout，规格没有授权读取或测量该区间。manifest 中 ID 是零基保存配置序号，每行 trajectory 用于和 HMC 轨迹交叉核验。

`measure.py` 新增 `measurement_input_manifest`：在导入 CuPy 前检查允许的 split、冻结源码 hash、manifest bytes hash/schema、ensemble、geometry、目标 IDs 与文件存在性；NERSC parser 在同一次读取中计算完整 raw-file SHA，并在把数组传到 GPU 前对照 HMC manifest 的逐配置 SHA。provenance 写入 manifest hash 与对应 trajectory。新测量记录 host read、device transfer、每候选 kernel/loop 时间；CuPy 计时点同步当前 stream，避免异步执行使 walltime 偏小。`total_seconds`涵盖读取/传输/测量，但不含压缩结果写盘、receipt和画图时间；运行报告需另列完整 job walltime。旧 protocol 未声明 manifest 时保持原行为。`stout.py` 现在跟随输入 backend，在 NumPy/CuPy 上使用相同的空间局域公式；CPU 分析所用 leading-order 弱场配对为 `rho=alpha/4`，协议明确它不等价于非微扰平滑半径。新候选及各参数配对都列在 RunSpec 中。

针对性验证：`test_wilson_loop.py`、stout 两组接口测试及新增 manifest preflight 测试共 **56 passed, 1 skipped**。测试覆盖 manifest/hash/split/holdout 拒绝路径、逐配置 raw SHA 对照、kernel/loop 分项计时、stout covariance/locality/identity 与默认 APE 不变；GPU backend 因本机没有 CuPy/CUDA 未实测。规格中的 D 120–139 仅20个验证配置（名义4个长度5 block），若区间宽则必须报告 `INCONCLUSIVE`，不能打开共享 holdout。此状态截面对应 full D job 提交前；后续 GPU smoke 与 job 128540026 进度见文首。

## 1. 当前已完成的有限范围

| 项目 | 结论与证据 |
| --- | --- |
| P0 pending 恢复 | 同一 spec 中断 2/3 后续到 3；IDs、loop 数组、逐行 hash 与 clean run 相同；ledger 区分增量成本。见 [恢复诊断](../../results/wilson_loop/audit_20261119_resume/README.md)。 |
| P0b 投影域（有限范围完成） | 新的 126 格 determinant-phase 受控扫描中，支持域 63/63 通过，域外策略拒绝 63/63；输入相位控制误差最大 $8.2\times10^{-12}$，切口外双侧协变残差最大 $9.9\times10^{-11}$。精确切口端点 7 格出现中心分支协变跳变，已单列，未伪称全局连续。见 [受控相位图文诊断](../../results/wilson_loop/audit_20261119_projection_domain_v2/README.md)。 |
| stout 可选 kernel | `build_kernel(..., kind=stout)` 显式 opt-in；默认 APE 分支逐值未变。`operator_contract_for('stout')` 声明 per-staple $\rho$ 与源码身份。原有小场 response、covariance/locality/坏参数/identity CPU 诊断见[三方案小场 loop response](../../results/wilson_loop/audit_20261119_stout_interface/README.md)；NumPy/CuPy backend 已实现。桌面缺 CuPy 的 parity test 仍是 `SKIP`，Kunshan 单配置 GPU smoke 已通过；D0–99 全样本作业是否结束以文首最近可验证快照为准；尚无完整样本上的 APE/stout 物理比较。 |
| P1a 事务 | marker 原子替换；10 类缺文件/篡改故障均拒绝混拼。见 [事务矩阵](../../results/wilson_loop/audit_20261119_transaction/README.md)。 |
| P1b NERSC checksum | 支持声明格式的 header 32-bit word sum；冷场 checksum `ff400000`；错误 header checksum 即使附正确私有 MD5 仍拒绝。见 [checksum 诊断](../../results/wilson_loop/audit_20261119_nersc/README.md)。 |
| P2 invalid evaluate | 无效候选 score 为 null 并留 reason；坏 identity fail-closed；Vref 和 paired nominal 有检查。见 [invalid 诊断](../../results/wilson_loop/audit_20261119_invalid/README.md)。 |
| P2b 统计口径 | coverage=0.983 是 toy 下的近似目标覆盖诊断，不是保守性证明；block / $\tau_{int}$ 依据与多重比较仍待更大生产实验。 |
| P3 有限 $N_t$ | [谱说明](../../doc/finite_nt_scope.md)已澄清：有限周期热迹的正反传播项不是所有 Wilson 圈都可直接简化为等幅 cosh；窗口 paired z 按同 draw 差值计算，仍未进入 gate。 |
| F0–F3 框架 | receipts 绑定本次 code/input/run；缺 hash 不 PASS；比较器拒绝非正风险；proposal 有外部预算；RunState physical 与 conditional score 分离。当前 comparison 仍为 draft/failed，`physical_score=None`。 |
| Toy analytic force CPU audit | [新诊断](../../results/wilson_loop/audit_20261120_hmc_force_fd_v3/README.md)比较两个 $2^4$ SU(3) 场中全部512个 link-generator 分量与中心差分，五个步长共5120行；场依赖 action 的显式坐标核对残差 $2.56\times10^{-13}$；解析力 leapfrog 的 $|\Delta H|$ 步长减半比约3.98–4.00，可逆性约 $10^{-15}$。首轮严格式点零点比较发现常数偏移−288，已保留于[v2 run review](../../results/wilson_loop/audit_20261120_hmc_force_fd_v2/RUN_REVIEW.md)，v3 将其作为 gauge-independent 加法常数显式处理。该结果只关闭本地 toy action 的CPU导数检查，不验证production action或GPU/MPI。 |

## 2. 必须保留的负结果和状态边界

两态谱反例位于 [`spectral_physical_v1`](../../results/wilson_loop/spectral_physical_v1/README.md)：$c_1$ 增至 0.5 时，
spread/$V$ 仍约 0.0058、当前 gate 通过，但短窗 bias/SE 达 32.5。`window_paired_z` 最大约 16.65，较旧的 naive
口径更敏感，但仍只是诊断、没有进 gate。**这证明当前 gate 对共同偏差有盲点，不证明 E0 已认证。**

图示：

![有限窗两态污染反例](../../results/wilson_loop/spectral_physical_v1/spectral_physical.png)

历史 v3 APE 比值 263/233/222 是冻结诊断；execution receipts 状态仍为 conditional-only，不能称为 physical score。
旧 [Kunshan HMC 日志诊断](../../results/wilson_loop/hmc_log_archive_diagnostic_v1/README.md)记录 S16T16 的 DONE=900 planned、rounded acceptance=0.972 和45个稀疏 ΔH checkpoints；旧[source-assisted reconstruction](../../results/wilson_loop/hmc_acceptance_reconstruction_v2/README.md)只在历史运行使用当前脚本的条件下给875/896=97.656%，并保留分母敏感替代解释。新的 [live archive audit](../../results/kunshan_logs/live_archive_audit_v1/README.md)核验了 B/C 两批各200个 SAVED files：路径、ID、trajectory、plaquette、raw SHA 对应 manifest 均逐项相符；两批各有70个共享 checkpoint，accept flag、plaquette、ΔH、累计接受率70/70一致。B 的 DONE=0.977 / planned 1400 唯一对应1368次接受；源码和批处理参数支持在traj1396提前停止，故 source-assisted实际率为1368/1396=97.994%，但没有 run-specific source hash，也没有未记录轨迹上的逐次决定。500/500个raw-file SHA各自匹配manifest；三组重叠payload相同率为100/100、100/100、200/200，解释了跨目录SHA差异为header字节变化。B/C同seed输出不是独立ensemble。详见[身份矩阵与重复payload图](../../results/kunshan_logs/live_archive_audit_v1/identity_and_duplicate_payloads.png)及[稀疏HMC图](../../results/kunshan_logs/live_archive_audit_v1/hmc_b_sparse_diagnostics.png)。这些归档仍不是完整protocol_v4 F4 receipt：缺每条trajectory ΔH/accept-reject、预声明热化cut及已论证的τ_int/block rule。

### P0b 已关闭：SU(3) determinant-phase 有限边界

旧 90 格扫描用一般 U(3) QR 因子，scalar `phase` 未控制实际 $\arg\det M$。本轮改成左右奇异向量行列式受控的独立新目录，
生成 [126 格 JSON / 图 / 文字诊断](../../results/wilson_loop/audit_20261119_projection_domain_v2/README.md)。支持域 63/63
同时通过 unitarity 与 $SU(3)$ determinant 检查，域外 63/63 按策略拒绝；切口两侧与端点的 determinant 相位均已实际核验。
切口外协变通过，精确端点的 7 个协变 outlier 是 principal cube-root 的 $Z_3$ 分支敏感性，单独报告；不要求 branch cut
全局连续。范围仅覆盖条件数策略与声明的三个 scale，不外推到任意浮点范围。

## 3. F4：新 D/E 链质量诊断完成；旧 protocol_v4/B receipt 仍不完整

CPU schema 前置检查由 [F4 synthetic preflight](../../results/wilson_loop/audit_20261119_f4_preflight/README.md) 覆盖：合法 synthetic control 只返回 `schema_ready`，15类缺失/篡改输入均拒绝。旧 `protocol_v4` 指向 `S16T16B`，其稀疏旧日志不能补成逐轨迹 production receipt；不得用新 D/E receipt 改写 B 的历史身份。**新独立 HMC 链 D/E 的完整逐轨迹 receipt、manifest/raw payload hash、自相关和图文诊断已经完成**，见本文件开头链接。D 链被选作新版 Wilson 测量输入；因此当前 Wilson 研究不需要再等旧 B 的 trajectory log，也不需要新开 HMC 链。D/E 的 HMC质量诊断仍不认证平衡、拓扑采样、Wilson-loop estimator 或 physical score。

旧 `S16T16B` 的 protocol_v4 receipt 是一项独立历史缺档，不是当前 Wilson 测量的前置条件。只有研究问题明确要求重建旧 B 结果时才追索原 Slurm receipt；若无法恢复，任何新运行都只能作为单独的新证据，不能补写或替代旧 B 身份。届时才适用下列完整记录要求：

本地 toy action 的解析力有限差分与解析力 leapfrog 已由上表所链的独立 CPU 诊断完成，**不再列为待做项**。首轮 `FAIL_TOY_CPU_CHECKS` 来自向量化 action 与标准 $6V$ 显式 action 的常数零点不同；常数偏移为−288且与场无关，v2 review保留首轮记录，v3通过了拆分后的冻结判据。该结果不替代目标 production HMC 的力梯度检查。

- 每 trajectory 保存完整 $\Delta H$、接受/拒绝、plaquette/topological 或既定热化观测量、trajectory ID 和输入/代码 hash。
- 预声明热化切除、分块长度与 $\tau_{int}$ 估计规则；接受率/平均 $\Delta H$ 给有限样本区间，并保留拒绝与异常 trajectory。
- 生产 receipt 必须由实际命令、运行环境、依赖和原始 trajectory 数据生成；缺项标 `NOT_RUN`，不得仅修改 `RunState`。
- 输出独立目录 `results/wilson_loop/hmc_production_<id>/`，至少包括原始 JSON、参数/receipt、失败行和可复查图：
  $\Delta H$ histogram、接受率随 trajectory 的滑动曲线、热化观测量与 plateau/window 诊断；另附带区间的文字表。
- 通过阈值需在采样前声明；如果数据不足或自相关过长，结果标 `INCONCLUSIVE`，不发 physical score。

## 4. 可选 P4：一次只扩一条物理路线

候选路线：stout / improved loop、multilevel、GEVP excited-state control、多个体积或新的 momentum sector。
不要一次堆叠多个变化。先选一个明确假设，匹配硬件、精度、统计预算和总成本，再跑成对对照。

首轮 stout 路线的 [synthetic null / two-state controls](../../results/wilson_loop/audit_20261119_p4_controls/README.md)每类 40 datasets：旧 spread gate 在两态 common bias 下 80/80 PASS；已知真值 $E_0$ oracle diagnostic gate 80/80 abstain。80 个 gate decisions 在同一数据集内相关，不能当作 80 个独立样本，该轮仅是小样本 toy 诊断。

随后预注册的[每类 402 datasets 扩样](../../results/wilson_loop/audit_20261119_p4_controls_n402/README.md)以 dataset 为统计单位，保留两个 estimator 的 joint outcome。Null 下 false-improvement 为 3/402（CP95 0.154%–2.165%），oracle 任一 abstain 为 4/402（0.272%–2.528%）；common-bias 下 legacy 两者通过 402/402（99.087%–100%），oracle 两者 abstain 402/402（99.087%–100%），未形成改善声明。common-bias 下虽有 28/402 risk-ratio intervals 排除 1，oracle gate 均弃权。CP95 只描述所定义 synthetic event rate，不能推出真实 gate 或物理显著性。

纯空间 stout 的 CPU small-gauge 算符切片已通过：[独立实现与残差表](../../results/wilson_loop/audit_20261119_stout_cpu/README.md)在非立方 SU(3) 小场验证 gauge covariance、unitarity、determinant、时间局域、输入不变和 Wilson-loop gauge invariance，最大残差 $4.45\times10^{-15}$；rho→0 极限与坏输入拒绝也有测试。随后已接入[显式非默认 kernel/contract 路径](../../results/wilson_loop/audit_20261119_stout_interface/README.md)，默认 APE 输出和 score identity 未变。小场响应表用同一 synthetic field 对比 identity / APE / stout，但只有一个确定性场，没有 ensemble SE/CI、匹配 smear radius 或 matched cost，故不作物理排序。生产测量与 stout/APE 物理对照仍未执行。

### 已完成：known-improvement gate control（CPU 合成）

[冻结方案、逐 dataset 结果、CP95 与图](../../results/wilson_loop/audit_20261119_p4_known_improvement_v2/README.md)：402 个独立配对数据集，真实合成信号均为 $E_0=0.5$，candidate 噪声振幅为 baseline 的一半（输入噪声方差比精确为 4；风险比只在小噪声下近似为 4）。397/402 数据集两条 gate 均通过；最终改善判据检出 324/402，80.6%，CP95 [76.4%,84.3%]。78 个未检出中，5 个在 estimator gate 弃权，73 个两条 gate 通过但 ratio CI 下界仍不超过 1；一个代表性例的 point ratio=5.31，而 CI=[0.946,10.46]。这显示当前 16-block / 100-outer 配置对该强合成效应的检出率有限，不能据此声称生产功效。

同一批 raw blocks 的 [100 vs 1000 outer-draw 敏感性](../../results/wilson_loop/audit_20261119_p4_known_improvement_sensitivity_v1/README.md)给出 323/402 检出，CP95 [76.1%,84.1%]；16 例变为检出、17 例反向变化。故个别界限会移动，但总体约 80% 检出率不是由 100 次 outer quantile 抽样主导；这不是新独立样本，不能与主结果合并。

### 已完成：配置预算与正向效应强度扫描

[runner `p4_power_cost.py`](p4_power_cost.py) 的预注册 9-cell CPU 扫描在每 cell 使用 402 个独立 paired datasets、固定 block length=5，扫描 16/32/64 blocks（80/160/320 个配置）和 candidate 噪声幅度比例 0.75/0.50/0.35。逐数据集诊断与趋势解释见 [方案与汇总](../../results/wilson_loop/audit_20261119_p4_power_cost_v1/README.md)、[ANALYSIS](../../results/wilson_loop/audit_20261119_p4_power_cost_v1/ANALYSIS.md) 和[功效图](../../results/wilson_loop/audit_20261119_p4_power_cost_v1/power_vs_configurations.png)。

四倍输入噪声方差改善的检出数随预算为 324/402、350/402、369/402；320 configurations/dataset 首次通过预声明的点检出率≥0.90 且 pointwise CP95 下界≥0.85 规则。弱 1.78× 改善检出为 68/402、55/402、46/402，CP95 区间重叠；两条 estimator gates 通过数反而为 386/402、396/402、400/402，故低检出来自 ratio lower-bound 不过 1，而不是 gate 大量弃权。各预算用独立 dataset seeds，非单调点率不能解释为增样本降低功效；该预算比较现已另由 nested-prefix 配对设计复核，结果见下节。各 cell 0 failure；所有区间仅为逐 cell synthetic event-rate 区间，无 family-wise 或物理结论。

第一次实现因读取不存在的 `reference_nominal_window` 使 402 行全部失败，保留在 [v1 RUN_REVIEW](../../results/wilson_loop/audit_20261119_p4_known_improvement_v1/RUN_REVIEW.md)，状态已改为 `FAILED_PROTOCOL_FIELD`；未与 v2 数据混用。

### 已完成：nested-prefix 配对预算敏感性

[预注册结果、逐数据集记录与图](../../results/wilson_loop/audit_20261119_p4_nested_prefix_v2/README.md)使用每种效应 402 个独立 synthetic datasets；每份数据先生成 320 个配对配置，80/160/320 三档是同一数据的前缀。主关注弱效应（候选噪声振幅比 0.75、输入方差改善 1.78×）：检出数分别 53/402、51/402、55/402；配对差 160−80 为 −0.50 pp（bootstrap CI95 [−4.23,+3.23] pp），320−160 为 +1.00 pp [−2.74,+4.73] pp，320−80 为 +0.50 pp [−3.73,+4.73] pp。区间均跨零，现有模拟不能分辨弱效应的预算差异。图左侧给逐预算 CP95，右侧给同 dataset 的配对差区间。

4× 输入方差改善在 80/160/320 配置下检出 336/402、360/402、364/402；160−80 配对差 +5.97 pp [2.24,9.95] pp，而 320−160 为 +1.00 pp [−2.49,+4.48] pp。按预注册的点检出率≥0.90 且 CP95 下界≥0.85 规则，320 是本次测试中首个达标预算；这不表示 160→320 的边际增益已分辨。8.16× 效应接近检出率上限，预算差区间跨零。全 1206 行无执行失败。结果只测 oracle-anchor 单态 synthetic gate，不含真实 gauge 场、物理自相关、stout/APE 或 GPU 成本；`physical_status=NOT_RUN`。

交付内容：冻结 protocol 和盲测划分；观测量原始表；未收敛/失败样本；窗口与 block-length 敏感性；至少一张对照图
（误差/MC 区间、失败样本可见）或带完整误差口径的数值表。新 estimator 的 gate 必须先用两态污染反例和 null/improvement
模拟验证；不得靠把 `window_paired_z` 加进 score 就声称消除了系统偏差。

## 5. LatticeArena 可扩展部分

- 新观测量或算法接 `OperatorContract` / `MeasurementBundle`，显式声明 gauge covariance、Hermiticity、几何和能力。
- 新测量接 `RunSpec` / measurement plan 与 preflight；GPU 初始化前检查 source、边界、预算、identity 和 stop rule。
- 新评分方法接冻结 `score_spec`、paired comparator 和 `RunState`；物理分数需 execution receipt，诊断分另列。
- 新搜索策略接 `SearchAdapter`，由外部控制总预算和拒绝规则，保存 proposal/失败 trace。
- 新物理任务需要自己的强基线、null/known-signal calibration、blind split 与图表；共享框架不会自动带来统计认证。

## 6. 下一位 agent 的开工顺序

1. **CPU power-vs-cost 与 nested-prefix 配对预算诊断均已完成**：弱 1.78× 效应的 80/160/320 配对预算差区间均跨零；4× 改善在 320 配置达预注册检出率目标，但 160→320 的边际配对差仍跨零。不要再以现有 generator 追加同类数据或调 gate threshold。若后续需要缩小预算差异不确定度，应先说明它会改变哪项预算决策，再预注册更高精度目标和新的独立 seed 范围；同时扫描 block length 与物理自相关结构，并提供 paired-difference 图、逐配置误差区间及失败/弃权说明。
2. **HMC receipt 与 quality diagnosis 已完成，不再等待旧完整日志**：D/E 链 receipt、逐 trajectory ΔH/accept、manifest/raw-file hashes、thermalization trace、自相关和 block-length sensitivity 均有图文；跨链对照也已生成。旧 S16T16B/C 稀疏日志仍不能追溯为逐轨迹receipt，`protocol_v4` 指向旧 B 的历史身份不变。D 链的新版测量 RunSpec 已冻结为 [protocol_d_20261120.json](protocol_d_20261120.json)，并绑定输入 manifest 与相关源码 hashes；不要把新 D/E 报告伪装成 B 的 receipt，也不要把预检规格称为测量 receipt。
3. **D0–99 development GPU作业与双 lane 方案审阅均已完成，不重交、不覆盖**：job 128540026 `COMPLETED 0:0`，终态三件套、100/100逐行loops identity和manifest gauge hash/trajectory join均通过。本地副本、A/B/C图文与reference runner报告均已生成（详见文首）。A/B提案按未冻结统计量显示diagnostic pass，C centered/uncentered joint-max均拒绝；这些不一致的开发诊断不能挑选生产门。有限-T Creutz与基态离散静态力两条 lane 的合同见[当前决策记录§0](estimand_decision_review.md#0-当前选择两条-estimand-lane-分开交付)；下一位 agent 不重写合同、不追加 family-wise 模拟、不重复 force/power-cost 诊断，也不修改生产 gate。只有研究者审阅确认性参数和污染界并另行授权后，才计划新的测量或验证。
4. **APE/stout development配对风险—成本诊断已完成**：D0–99、20个length-5 blocks、500×500 paired bootstrap的分析和原始draw文件见[报告](../../results/wilson_loop/development_paired_diagnostic_20261121/PAIRED_REPORT.md)、[风险—成本图](../../results/wilson_loop/development_paired_diagnostic_20261121/paired_risk_vs_cost.png)及CSV。risk(identity)/risk(candidate)点值约4.84–12.11，但reference自身尚未认证，且这些development IDs已被观察；不能据此称物理改善。Stout候选每配置 `kernel+loop` 均值约87–175s，APE约0.75–1.27s，顺序单GPU运行不构成matched-walltime比较。旧指令“先闭合reference规则后测D120–139”已被双 lane 决策和当前封存边界取代；这些点值仍只是development诊断。20个配置不足时报告`INCONCLUSIVE`，不得读取D100–119 gap或D140–199 shared holdout。
5. 汇总 gate 时并列解释 §2 两态共同偏差、N=402 null/common-bias、known-improvement、独立 cell 的功效—成本扫描、nested-prefix 配对预算结果及 bootstrap-resolution 敏感性；不得合并相互独立的主实验数据。给出独立 dataset 数、通过/拒绝/失败/弃权计数、区间和适用边界。nested-prefix 结果只允许推断当前 synthetic generator 下的预算差异；若用于后续预算选择，需按“点检出率≥0.90 且 pointwise CP95 下界≥0.85”的原规则明确所达档位，不能用它弥补 gate 的共同偏差盲点。生产证据齐全前保持 `physical_score=None` / `NOT_RUN`；数据不足或自相关过长则标 `INCONCLUSIVE`。
6. 本地 toy force finite-difference 检查只认证 toy action；D/E HMC receipts也不认证 Wilson-loop estimator。若后续需要 production-force gradient check，绑定被测 action 源码，在同一左切向约定下提供逐 link/generator 残差热图、步长扫描、最大/中位误差及 Euclidean 边界约定说明。不要重复 toy v3，也不要把新链误称为 protocol_v4 旧 B 结果。

硬件范围说明：新 D/E 链的 production $\Delta H$/接受率和质量图文已经由 Kunshan 完成，不属于当前待办；旧 B `protocol_v4` 的历史 receipt 若要复核，先查原归档，不能用新链补写。D 链 GPU 测量、development 配对诊断、双 lane 理论/统计合同和有限-$N_t$ 热污染审阅均已完成。当前未闭合项是研究者审阅 lane-specific 的确认性 kernel/R/T、精度/多重性与谱/热污染容差，并在另行授权后取得必要的独立测量证据；外部绝对势锚不再是所选两条 lane 的默认前置项。共同偏移的不可识别性仍限制绝对势类声明，family-wise 校准只控制窗口比较族内错误率。P4 CPU synthetic controls已完成；不要重复固定 generator，也不要把合成结果升级为物理验证。

### D-development gate 可执行性检查：`NOT_READY`（2026-11-20 06:31:58 UTC）

**最近一次成功轮询（2026-11-20 08:12:10 UTC）**：job128540026当时为`RUNNING`，`sacct` elapsed=`03:19:37`、End=`Unknown`；stdout已写到cfg26。远端用Python读取provenance确认records为27行，IDs严格连续0–26；`development.commit.json` 的 generation 仍是`dd38c39f21982307c5abc2d5093b93c2aa12ef8848d6f9136519b1f8054b619e`，NPZ/provenance SHA与marker逐字节复核相符，分别为`b9956e9ad303a69068b6d7b15559611c58a7487d92c8a4155c96188f20775f6d`和`7bd9d5cc84acf4f40657b28e443edda991c8d99690de9c9adff1f8020bb5ba45`。stdout末尾cfg26耗时439.91 s。仍缺D27–99共73配置及最终终态收据；A/B/C对照仍`NOT_RUN_INCOMPLETE_DEVELOPMENT`。本轮只读取状态、日志末尾和提交三件套，没有复制或分析不完整前缀，也未访问其他split；**样本不完整，故不产出生产诊断图或score**。以下表保留06:31:58 UTC的详细检查快照。

**轮询边界（2026-11-20 08:34:16 UTC）**：本机没有`squeue`，经当前 `sshmini` 连接的远端也返回`command not found: squeue`；因此没有获得新 job state / elapsed / stdout 进度。08:12:10 UTC 的快照是最后一次已验证状态，不应视作当前状态。本轮未提交、重启作业、复制文件或读取不完整测量前缀；下次应在可用的 Kunshan Slurm 环境只读刷新该既有 job。

**历史稳定快照（2026-11-20 09:54 UTC）**：经 `ssh kunshan` 只读刷新，job 128540026 为 `RUNNING`，elapsed 05:01:50、End=`Unknown`；提交 generation=`dd38c39f21982307c5abc2d5093b93c2aa12ef8848d6f9136519b1f8054b619e`，稳定前缀40个配置 IDs 0–39。NPZ SHA=`ffd873c83740bdb9877a60ff32e90a79cc01e537fa9c41c587a4bfb1e53a9070`，provenance SHA=`23717dae299a580b157acf3d41b38aadd2c21f09903c52aa3afbe83fdbe1e44d`，loops SHA=`db03a21a41b016845ca8d38b1c21e5b185b27992a77004f2e2711bf2cecb2568`；三者匹配该时点 marker。此历史前缀不再用于当前进度或分析。

**历史稳定快照（2026-11-20 10:17:57 UTC）**：经 `ssh kunshan` 只读刷新，job 128540026 仍为 `RUNNING`，`sacct` elapsed 05:25:36、End=`Unknown`。远端提交 generation=`dd38c39f21982307c5abc2d5093b93c2aa12ef8848d6f9136519b1f8054b619e`、split=`development`；marker 读取前后未变，NPZ shape=`(44,7,4,5)`、IDs及provenance records严格连续0–43、loops全有限；44条逐行 loops hash 均匹配数组对应行。NPZ SHA=`3036feeb8f79cefbdeeb12c9f4c4e20c980c893eeee9fe60451c91c258288809`，provenance SHA=`12af4e470d4425e936183375bb1ab4d087bb24d522eb40b31ba8dc35de36c9b7`，loops array SHA=`ce3abb1cc265d6365c372448a024785b9dca079022f02cf97d6df7b80870e3d5`均匹配 marker。只核验该稳定提交，不分析增长中的非提交前缀；仍有56个配置未提交，故不做 gate、score 或统计结论；未重启/提交作业，未读 raw gauge 或其他 split。

**历史稳定快照（2026-11-20 10:28:46 UTC）**：job 128540026 仍为 `RUNNING`，`sacct` elapsed 05:36:19、End=`Unknown`。同一 generation 的稳定提交为 IDs 0–44 共45行，shape=`(45,7,4,5)`；逐行 identity/loops hash、marker 前后稳定性和有限性检查全部通过。NPZ SHA=`ae3e0d9e1e40c587224abc6d9c4c3223d345e37f84346d85e1bcd95f97ad9e5e`，provenance SHA=`816ee2355a78d6cc83a0b7ff14280613c9aa6a2a891bd4d8c0e21c96e832c674`，loops array SHA=`9b4a26cb9ce9d40f1197d9cd6cdb2d06ef9df6f8f6613e73591e012ffd5a6c84`均匹配 marker。只读验证没有分析未提交前缀；剩余55个配置，故不计算 gate/score或统计结论，也未读 raw gauge 或其他 split。

**历史稳定快照（2026-11-20 10:37:14 UTC）**：job 128540026 仍为 `RUNNING`，`sacct` elapsed 05:44:50、End=`Unknown`。同一 generation 的稳定提交为 IDs 0–45 共46行，shape=`(46,7,4,5)`；逐行 identity/loops hash、marker 前后稳定性和有限性检查全部通过。NPZ SHA=`a9d8ec9b8c8b71bbb428a2743c4cc434cf4458448a81fefbad6eb864b97689aa`，provenance SHA=`4de2a831899fd28eb7bc0e818d4f14039856af816a1120ca06b8df011863d490`，loops array SHA=`53ae16975e065fa0f946c4de8814b61274ddf447f52330fe8303399b28da457e`均匹配 marker。只读验证没有分析未提交前缀；剩余54个配置，故不计算 gate/score或统计结论，也未读 raw gauge 或其他 split。

**历史状态表（2026-11-20 10:51:53 UTC）**：该次只读获取既有 job 状态及 D-development 三件套；未读 raw gauge、gap/embargo、validation 或 shared holdout，没有重跑 GPU，也没有分析不完整前缀。

**历史状态表（约 2026-11-20 11:21 UTC）**：job 128540026 仍为 `RUNNING`，elapsed `06:28:47`、52个配置已提交。该次只读获取既有 job 状态及 D-development 三件套；未读 raw gauge、gap/embargo、validation 或 shared holdout，没有重跑 GPU，也没有分析不完整前缀。

**历史状态表（约 2026-11-20 11:44 UTC）**：job 128540026 仍为 `RUNNING`，elapsed `06:51:32`、55个配置已提交。该次只读获取既有 job 状态及 D-development 三件套；未读 raw gauge、gap/embargo、validation 或 shared holdout，没有重跑 GPU，也没有分析不完整前缀。

**历史状态表（约 2026-11-20 11:49 UTC）**：job 128540026 当时为 `RUNNING`，elapsed `06:56:38`、End=`Unknown`。该次只读获取既有 job 状态及 D-development 三件套；未读 raw gauge、gap/embargo、validation 或 shared holdout，没有重跑 GPU，也没有分析不完整前缀。

**历史状态截面（约 2026-11-20 12:22 UTC，已被文首更新取代）**：`sacct` 显示 job 128540026 仍为 `RUNNING`，elapsed `07:30:03`、End=`Unknown`。随后约 12:23 UTC 完成了最新三件套与逐行 identity 核验，稳定前缀为61/100；没有读取 raw gauge 或其他 split。

纯计算函数[reference_gate_diagnostic.py](reference_gate_diagnostic.py)本身仍只接收内存数组，不负责身份或 split 检查。新增[reference_gate_runner.py](reference_gate_runner.py)为文件级 fail-closed 前端：只接受完整 D-development 0–99 三件套，核验 frozen protocol / 源码 hash、generation、commit marker、NPZ/provenance bytes、ID顺序、逐行 loops hash、shape/finite、identity kernel、manifest hash 声明，以及每行唯一 trajectory ID 和 gauge SHA-256 字段；调用check_resume(..., verify_gauge=False)，不重新读取 manifest 或 raw gauge。不完整前缀会在创建输出目录前拒绝。真实D0–99的A/B/C development参考诊断已运行，结果见文首；该输出仍是proposal-only，不能作为生产门或physical score。

完整事务通过后，runner已在新目录生成 receipt、bootstrap index原始矩阵/hash、逐对比CSV、失败/弃权CSV、A/B/C决策表、参考势/配对差图、z热图、joint-max图及REFERENCE_REPORT.md。真实D0–99输出均标development_diagnostic_only / PROPOSAL_NOT_FROZEN，production_score=null；runner报告说明共同偏差盲点、未做family-wise calibration、未重读raw gauge。synthetic fixture定向测试仍为26 passed，只验证runner拒绝/产出边界；真实D结果另见文首报告。

### 16:22 UTC执行前缺项表（历史快照；后续均已在文首说明中完成）
| 必需项 | 历史观测（16:22 UTC稳定bundle；已由文首终态更新） | 当时缺项/条件 |
| --- | --- | --- |
| job 128540026 终态 | 16:23 UTC仍RUNNING，elapsed 11:31:08；93/100已提交，stdout到cfg92 | 等待既有job终态并记录最终State/ExitCode/End/full walltime与完整日志；不得重复提交 |
| development.npz | 16:22 UTC snapshot shape (93,7,4,5)、IDs 0–92连续、loops全有限；SHA=5bb5dbb0d3c96da98b8dfeb3f5c6e29f1b55d03d568017c796668209bc44d012 | 需完整shape (100,7,4,5)、IDs严格0–99；尚有7项 |
| development_provenance.json | 93条记录与NPZ IDs对齐，逐行loops hash通过、manifest raw SHA / hmc_trajectory 93/93匹配且唯一；SHA=8685438057d322f9f61758854109ce07112c1fa6379fd202cd51f90b56721261 | 终态复核剩余7条与raw SHA / trajectory字段；本轮没有重读raw gauge |
| development.commit.json | generation=dd38c39f21982307c5abc2d5093b93c2aa12ef8848d6f9136519b1f8054b619e；NPZ/provenance/loops hashes均匹配，marker SHA=a046d77f8eaef995d832e85edb14c0e5e9e921761af89b19075c8cf01752abe6，loops SHA=edf360c0dde75b63b436ec686591a8126f8c194ebd16124d7c76bc3d0879e2ce | 终态再次校验同一generation、marker、逐行hash与冻结身份；早期61行快照差异仍待解释 |
| 冻结身份 | check_resume(..., verify_gauge=False)返回93；generation、5项测量依赖、manifest identity、IDs/records/逐行loops hashes通过；93条trajectory IDs唯一 | 终态仍需运行同一只读检查并将receipt与完成输出绑定；不重读raw gauge |
| 本地公开 dev 副本 | results/wilson_loop/s16t16d_development_20261120/ 不存在 | 只在远端终态且三件套核验通过后复制development三件套与job日志；不复制raw gauge或其他split |
| A/B/C development数据诊断 | 均为NOT_RUN_INCOMPLETE_DEVELOPMENT；该16:22 UTC历史表截面为93/100 | 完整100行及终态审核通过后，生成development-only诊断图表；不改变生产门、不报physical score |

远端既有输出目录：`runs/wilson_production_d_20261120/results/wilson_loop/s16t16d_development_20261120/`；既有日志：`runs/wilson_production_d_20261120/logs/wilson_d_development_128540026.{out,err}`（均相对远端LatticeArena根目录）。

下一位可执行的前置条件清单：


1. **已完成**：既有job 128540026终态、100/100三件套、逐行loops identity、manifest join与轨迹唯一性已核验；开发事务副本和日志已归档。较早61行aggregate hash差异保留为未解释历史异常。
2. **已完成**：本地三件套校验通过100行/7核/4R/5T、ID顺序、generation、marker、source identity与逐行hash；没有重读raw gauge。
3. **已完成**：reference_gate_runner在真实development数据上生成A/B/C诊断表、失败表、bootstrap索引与三张图；proposal未冻结，生产score为null。
4. **已完成**：APE/stout配对风险/成本CSV、500×500原始draw和风险—成本图文已生成；效应边界和2个无效outer draw均已说明。
5. **CPU 方法学已有新进展，生产数据仍锁定。** §9共同偏移不可识别性、§10代数负控，以及[D0–99 force数据探索](../../results/wilson_loop/development_force_diagnostic_20261121_v1/README.md)均已完成；不要重复固定toy或同一D0–99 force图。用户已选有限-T Creutz和基态静态力；下一步分别冻结有限-Tχ统计比较，以及f₀的有限-T/离散化污染控制、比较族、多重性和失败/弃权状态。若有一项新合成DGP校准会改变未来协议选择，先写预注册方案和图文覆盖/功效目标；不要重复已完成的固定generator。绝对势外锚仅作历史参考，不再是当前lane的前置项。未经protocol审阅和授权，不读D120–139、gap或shared holdout，也不提交新GPU job。

### 2026-11-21 补充：基态静态力的谱污染敏感度界（解析，未拟合）

[推导、适用条件与敏感度图](../../results/wilson_loop/ground_state_bound_20261121_v1/README.md)从正谱展开得到 `g_R(T)=log[(1+rho_R(T))/(1+rho_R(T+1))]`，以及有限-T Creutz 相对基态离散静态力的界 `|chi-f0| <= log(1+Q exp(-DeltaE_min T))`。图扫描的 Q 与能隙仅是示意输入，不是从 D 数据拟合或推断；脚本不重读 D0–99，更未访问 D100–199。4个时间切片共14,884个确定性格点；本轮跨任务 focused tests 26 passed（其中 Wilson 界模块7 passed），图和 artifact hashes 已核验。

这项解析界推进的是识别与方案设计，不认证当前基态力：它要求正的前向谱及可辩护的 overlap 总界/能隙下界；`Nt=16` 的热绕行贡献另需模型或上界。原先“下一位 agent 冻结 R/T/比较族”的建议已由用户要求保持未冻结所取代；有限 `N_t` 迹表示、误差分解和停止规则现已完成，见[专门报告](../../results/wilson_loop/finite_nt_thermal_bound_review_20261122/README.md)。若热绕行界不可识别，标 `GROUND_STATE_FORCE_UNCERTIFIED`，不得把有限-T结果重命名为基态结果，也不打开验证/holdout。两条 lane 的样本相关性需在后续联合报告中保留。
### 本轮补充：snapshot 来源在仓库内不可追溯

`results/wilson_loop/hmc_quality_v1/manifest_snapshot.json` 命中 `.gitignore` 的 `results/` 规则、未被 Git 跟踪，生成脚本无法从仓库追溯；但 raw-byte identity 已由 live audit 独立闭合：snapshot 的 200 个 hash 与远端 S16T16C raw-file SHA 200/200 相同，首 100 个虽与主 manifest 的完整文件 SHA 不同，但 header 后 payload 100/100 相同。该旧 snapshot 的生成命令/receipt 仍不可追溯；这不影响新 D/E 链已有的独立 receipt、逐轨迹数据和输入 manifest，也不阻塞 D 链 Wilson 测量。除非研究问题要求复现旧 `hmc_quality_v1` snapshot，否则不要重复追索 gauge bytes 或猜 hash convention。

**原始字节复核与状态记录（2026-11-20）**：远端只读 live audit 已证实 snapshot 的200项 hash 与 S16T16C 实际 raw files 逐项对应；主100项 manifest 与 snapshot 的前100项 hash虽0/100相同，但两边各自都与实际 raw file匹配，且header后payload 100/100一致。GEVP200测量 provenance 另有180/180条raw SHA匹配 S16T16C；Pion旧pilot有90/90条raw SHA匹配 S16T16。见 [live archive audit](../../results/kunshan_logs/live_archive_audit_v1/README.md)。原 RunSpec 中的 GPU smoke 与 IDs 0–99 development 测量已启动；smoke已通过。job **128540026** 在06:31:58 UTC的进度（cfg0–12，共13/100）为历史截面，最新状态见上方轮询段。完整收据到位后只做development的A/B/C gate提案可执行性对照与APE/stout诊断，不选择或冻结生产门。当前授权不包括D IDs 120–139 validation；提案诊断不授权打开该split。交付逐配置能量/风险与 block-bootstrap 区间、reference/window 图、失败/弃权表、风险—walltime 图和解释文字。D IDs 100–119保持 gap，D IDs 140–199继续封存。D/E HMC逐轨迹 receipt 与质量图文已完成，不再把它们列为待办；physical score仍为`NOT_RUN`。
