# 三个工作包的 todo 覆盖与下一步

当前覆盖状态（2026-11-22 Asia/Shanghai）：三个 task 的核心目标均未完成，故保留三份 TODO。报告继续区分 synthetic、development、production 与 blind 证据。Optimize 的 schema v2 worker、hard-timeout、显式 protocol child recheck、RunSpec builder CPU preflight，以及 `solver_contract` 到 `train.optimize` /显式协议入口的 CPU 接线已完成；4个定向测试模块 **87 passed**，带文本调用流程和拒绝场景的报告见[solver接线诊断](../results/optimize_gaussian/solver_contract_train_integration_cpu_v1/README.md)，builder/worker原报告见 [RunSpec 报告](../results/optimize_gaussian/task_runspec_preflight_cpu_v1/README.md)。真实 production RunSpec、研究者冻结的阈值/统计决策、训练和 GPU 执行仍未完成。Pion D0–99 single-cosh reference gate 仍 FAIL，M2 确认方案为 `ABSTAIN/NOT_READY`，E anchor、D validation 与 shared holdout均未解锁；旧 S16T16 source–sink 矩阵 5% Hermiticity 门的失败已补[逐时曲线、元素热图和文字报告](../results/pion_projection/source_sink_hermiticity_diagnostic_20261121_v1/README.md)。matched-smearing contract 已落到 source 实际调用路径：12个source propagator列直接使用sink相同的低层 Wuppertal callable/alpha；专用 multisource 默认协议、`--protocol` 与无 GPU 导入的 `--preflight-only` 已通过 CPU 检查；focused smearing suite **19 passed**，两个 Hermiticity 模块合计 **14 passed**，combined **33 passed**。完整代码 hash、候选协议和边界见[matched-smearing preflight](../results/pion_projection/matched_smearing_contract_cpu_v1/README.md)。这没有测试 QUDA 数值，也未修旧数组或证明历史远端根因。C2/C3 小样本提醒仅适用于原始网格；对应若干 selected cells 已有扩样和MC区间，仍未覆盖完整网格/拟议 M2 确认流程，不能视作发表级物理校准。Wilson D/E 链的 F4 逐轨迹 ΔH/接受率质量诊断已完成；旧 `protocol_v4` B 链的历史 receipt 缺失，但不能用新链补写，也不阻塞当前 D 结果。Wilson D0–99 job 128540026 已 COMPLETED 0:0、elapsed 12:15:58，100/100 identity/provenance/manifest join通过；A/B/C reference、APE/stout paired risk-cost 和 D0–99 T-window/Creutz force development-only 图文均已输出。20 个 length-5 blocks、5000/5000共同 bootstrap draw有效；identity force 在大 $R$ 仍随 $T$ 窗口明显变化，不能认证有限-$T$ 稳定性或物理 force。用户现已选有限-$T$ Creutz 与基态离散静态力两条独立 estimand lanes；确认性 R/T、primary/secondary、多重性和基态污染控制仍未冻结，physical_score=null；生产 APE/stout 独立比较仍未运行。D100–119仍为gap、D120–139未解锁、D140–199封存。

**2026-11-22 封存状态下的续审增量：**Pion 的[独立块/anchor receipt 审计](../results/pion_projection/independent_block_anchor_receipt_audit_20261122/README.md)确认 D0–99 的固定 trajectory 间距与 length-5 bootstrap 不能证明块独立，E anchor 尚无可用 correlator receipt，当前无独立 `A/B_A` 界；Wilson 的[有限 `N_t=16` 热迹污染审阅](../results/wilson_loop/finite_nt_thermal_bound_review_20261122/README.md)推导了 `Q/gap`、热迹与混合项的不同指数，复核了零温单点界的适用条件，并给出有限 extent 下 force-level 四角和的保守界。Optimize 的 D11/C1-C2 CPU审阅已完成，现有输入下没有新增 CPU 工作能改变结论。三项仍按用户答复保持 `NOT_READY/UNCERTIFIED`、数据封存、`physical_score=null`；没有新测量、MC或GPU执行。

**2026-11-22 最新用户确认：**三项工作均继续保持 `NOT_READY/UNCERTIFIED`，所有封存/未授权 split 维持关闭。Optimize 的 F=2 对照与 Wilson 的双 estimand 选择仍有效；Pion 的 bounded block-MSE 仍是条件性新 estimand。D04 reference、D06 `r_star`、物理质量范围/clipping、R/T/kernel、多重性、谱间隙/overlap与热污染容差均未冻结。后续只做不会读取受限数据、不会触发生产/GPU测量的可审阅CPU/理论工作；TODO记录了已完成的诊断和仅待决策/授权的后续步骤。没有新的物理/生产执行授权。

本轮 Optimize 又完成了[隔离 trainable-W CPU 参数化原型](../tasks/optimize_gaussian/trainable_w_cpu_prototype_20261121/README.md)：解析梯度、实际W更新、同模型族 synthetic coefficient fit、gauge/Hermiticity与48个立方/反演 signed permutations均有代码和图文诊断；focused tests 为9 passed，邻近 feature/kernel 为7 passed。它没有接入生产 `train.main`，不评估 gauge-ensemble physics risk、不比较 SLSQP，也不证明 positivity/物理优势。下一实现门是研究者先冻结主张/reference/最小效应，再把原型接入真实测量与 RunSpec；生产训练和blind对照仍为 `NOT_RUN`。Optimize决策材料见[19项生产前决策单](../tasks/optimize_gaussian/protocol_decision_review_20261121.md)。

Pion 的 M2 停机判断仍为 `ABSTAIN/NOT_READY`：拟议 N=60/12-block M2 流程没有通过 D 可行性筛查，不能靠新增同流程校准消除既有可辨识性/边界否决；用户另已接受 bounded block-MSE 作为不同 estimand，其独立条件性 CPU 校准现已完成，报告与逐行复核写在 Pion TODO，仍不构成物理 score。Wilson 的目标选择已由用户完成：有限-$T$ Creutz 与基态离散静态力分别作为两条 lane；[estimand 决策记录](../tasks/wilson_loop/estimand_decision_review.md)现在规定分开冻结统计与污染控制 contract，不能再把“选择目标”列为待办。Optimize 的确认性族也已由用户确定为 trainable-W 对同预算 SLSQP、以及 trainable-W 对固定强谱基（建议 degree-4 Chebyshev）；它们是两项独立对照。三份 TODO 均仍有物理或研究者决策门槛，继续保留。

本轮 Pion 旧 source–sink arrays 的逐配置和块不确定度复核已完成，报告含逐配置散点、block-length 1/2/5/10敏感性图、原始CSV和输入/source hashes：[报告与图](../results/pion_projection/source_sink_hermiticity_per_config_20261121_v1/README.md)。Development 60配置、已观察 validation 30配置的逐配置比值均约0.3；8个length-5 block-bootstrap 95%区间全部远高于0.05。该结果说明旧 ensemble-mean失败不是少数离群配置造成，但不确定历史根因；saved-configuration块也未与HMC trajectory spacing绑定。两个定向Hermiticity模块 **14 passed**，未访问新split/GPU。

Pion 路径边界已补入 TODO 与[独立 reference 确认草案](../tasks/pion_projection/reference_confirmation_plan_draft.md)：M2/P1–P2 使用 point-source correlator protocol；matched-smearing v2 是另一条 point/H4/H16 source–sink cross-matrix protocol，split、generation 和输入不同。两种结果不可互证或混池；matched-v2 CPU preflight 不代表 M2 point-source/E anchor 已测或通过。

本轮 Optimize 补充核查：solver rejection receipt 现作为 RunSpec 的 optional diagnostic output；父级只在 child process group 稳定后记录其 hash，并且不将它计为成功 artifacts。四个 solver/train 模块为 87 passed，加入 hard-timeout / worker / builder 后六模块 **113 passed**；详细文字轨迹和复现命令见[接线报告](../results/optimize_gaussian/solver_contract_train_integration_cpu_v1/README.md)。另完成[真实 `train.main` worker synthetic CPU integration](../results/optimize_gaussian/cpu_train_main_supervisor_v2/README.md)：Powell+solver contract 在 worker 子进程中完成，worker=`completed`、4/4 artifacts hash verified、3/3 synthetic identities verified、32 calls、KKT residual `2.86e-19`；图显示 calls/time best-so-far。该 smoke 只替换了合成 collect/risk/coefficient map，无 GPU/QUDA、生产数据或物理分数，也不是新增 pytest 通过数。软件接线报告给出控制流程、输入/产物身份和相关trace；只有真实方法比较才要求paired-risk区间及逐臂成本图，避免给没有对照的 smoke 虚构比较结果。Optimize-specific frozen-protocol 决策字段与分类型 graph/report 交付要求另汇总在 [protocol freeze draft](../tasks/optimize_gaussian/protocol_freeze_draft.md)；阈值/物理 reference/预算和 blind 解封仍待决，不得由 CPU toy 代填。

### 2026-11-21 后续CPU增量与当前下一门

- **Optimize**：[trainable-W 算符目标桥接](../tasks/optimize_gaussian/trainable_w_operator_cpu_20261121_final/README.md)用独立定义的 gauge-covariant heat kernel 目标、完整矩阵/Frobenius loss 和 Chebyshev 强谱基，补上了系数标签拟合不能回答的一个 implementation gap。36/36 optimizer runs 返回，4个预算截断/solver non-success保留；梯度FD误差最大 `1.23e-11`、压缩目标与直接算符损失最大差 `1.67e-16`。3个小panel没有稳定 trainable-W 优势，degree-4谱基在该谱目标上明显更低；这是目标条件下的结构性负诊断，不是物理排名。相同 heat-kernel 和 coefficient-label fixtures 不再扩样。下一步仍须先冻结物理目标、reference、归一化/正定约定、容量及总成本口径，再决定是否接生产训练。
- **Pion**：[有界 block-risk 设计稿](../tasks/pion_projection/bounded_score_design_review_20261121.md)推导了有界平方损失、真正独立块和独立 anchor 区间条件下的 family-wise Hoeffding 下界；12块、单比较、精确 anchor 时统计扣减为 `0.7066 R²`。用户已接受 bounded block-MSE 作为不同于 ensemble-risk 的 estimand；168×3000 synthetic 校准与失败块 worst-case/abstention 图文均已完成，但没有物理范围、独立evaluation blocks或anchor共偏差证据。下一步不再问 estimand 是否接受、不重扩同一MC；在封存下交物理范围/clipping、失败块、独立块、anchor和两测量流gate的候选方案与数据流图，不生成production score。
- **Wilson**：[paired force window contrast](../tasks/wilson_loop/force_window_contrast_20261121_v1/README.md)在核对冻结transaction、原protocol、全部window rows和5000×20 resampling indices逐项一致后，计算63项窗口漂移和54项 candidate-minus-identity drift contrasts。identity 的 `Rmid=2.5` late−early 为 `-0.02842`，点态95%区间 `[-0.05185,-0.00172]`；117项均未经多重性校准，且无法探测各窗共有的R依赖偏差。用户已选有限-$T$ Creutz 与基态离散静态力两条 lane；图仅提供 development 窗口敏感性描述。下一步分别提出不依赖解盲数据的候选统计/污染协议，不再问目标二选一，也不从已观察 D0–99 挑确认性 R/T。

这三项增量均已各自并入 task TODO，且都有对应图或完整文字诊断。三份 TODO **继续保留**：缺失条件分别涉及生产物理目标/真实GPU与独立盲测、reference/anchor可辨识性、Wilson估计目标及共同偏差控制。不得将这些CPU结果升级成物理score或盲测结论。

## 对先前“完成状态”描述的复核

- **Optimize 包 B 覆盖事故：基本属实，但范围限于当前仓库。** [`cpu_next_package_b/README.md`](../results/optimize_gaussian/cpu_next_package_b/README.md)记载 `unified_v1/` 曾被同名输出覆盖，旧 fold 未入 Git、当前 checkout 内不可恢复；外部备份并未排除。旧比值1.719/2.014/0.810仍作为三折描述值保留在任务README与package B报告，reference gate三折均失败、也不是独立误差估计；Optimize TODO现已明确记录该历史边界，不能把它们当作当前可复现证据。新输出目录保留 no-clobber 规则。
- **“所有未做项都只差 GPU/授权”：不准确。** Wilson 新 D/E 链的逐轨迹 ΔH/接受率及质量诊断已完成，P4 CPU synthetic gate / power-cost / nested-prefix 诊断也已完成；旧 `protocol_v4` B 的历史 receipt 缺失，但不能由新链替代且不阻塞当前 D 诊断。D0–99 Wilson-loop A/B/C、APE/stout配对和 force探索图文均已生成；当前缺的是可识别共同势偏移或已冻结静态力 estimand 的 reference 方案，以及独立 D120–139 验证/真实物理比较。Pion 新测量的确受 GPU 与 split 授权约束，但现有失败 gate 与 `ABSTAIN/NOT_READY` M2 方案意味着首先要解决方案审阅与可辨识性，不能直接开跑。Optimize 的 CPU solver gate 与 optional failure-diagnostic hash 接线现已完成；待做的研究者阈值、paired estimand 与生产 RunSpec 先于 GPU 工作，真实 trainable-$W$、production 2×2、metadata 重采和 blind comparison 才需要生产输入、GPU 及相应 split 授权。
- **C2/C3 小样本提醒：方向正确，不能混合不同模拟设计。** 原始 C2 很多 cell 只有6–8个 dataset（少数端到端变体8–15），原始 C3 多因素网格约30/cell；之后只对预选场景做了N=400/cell等扩样，且C2 χ²子门、J=2/K=2 family、C3 null/improvement、full-gate与family-wise试验的DGP、分母和estimand各不相同。扩样只收窄对应 synthetic Monte Carlo error，不补共同偏差、物理误差或未扩的完整网格；具体区间、失败/弃权分母见[Pion TODO](../tasks/pion_projection/todo.md)。

原 provenance-field 交叉核查：此前只比较本地 provenance hash 字段。新的 [Kunshan live archive audit](../results/kunshan_logs/live_archive_audit_v1/README.md) 已对500个远端 raw files 做真实字节核验：S16T16/B/C 各自 manifest 全部匹配，跨 campaign 重叠 ID 的完整文件 SHA 为0匹配、header 后 payload 为100/100、100/100、200/200匹配。主 manifest 与 snapshot 的 hash 差异因此来自 NERSC header，不代表 gauge payload 不同。旧身份矩阵仍能说明数字 ID 是 run-local 标签；不能据此把重复 payload 计作独立配置。

审计时间：2026-11-20基线，2026-11-21追加 Pion matched-smearing CLI preflight 与逐配置/block-bootstrap不确定度诊断；Wilson P4 nested-prefix、Pion amendment03同种子来源对齐重放、family-wise v1–v3、χ² subgate扩样/协方差因子化/conditional bootstrap、C2 family N=400、C3 anchor-bias-only/common-block/lower-bound、studentized paired-block sign-flip均有图文结果。**早先快照记录的全套 CPU/GPU-free suite 为374 passed, 1 skipped, 1 warning**；唯一 skip 是缺少 CuPy 的 stout parity test，warning 是 Wilson singular-domain rejection 的 `RuntimeWarning`。该快照未重跑 matched-smearing 专项；既有收据为 **19 passed**，两个 Hermiticity 模块 **14 passed**、合并 **33 passed**。另用候选 multisource v2 协议对 development IDs 0–1 做 `--preflight-only`，状态 `cpu_preflight_ready_not_authorized`，且未创建测量目录；该项不是授权或 GPU 测量。§8记载的385通过是2026-11-21快照；当前复跑见§12。

## 状态口径

- **完成**只表示已声明范围内有实现和可复查证据；不扩展成物理认证。
- **INCONCLUSIVE / 负结果**表示代码和诊断成立，但样本量、gate 盲点或构造性结果不支持强结论。
- **NOT_RUN**表示本工作区没有可复查执行证据，不等同失败。
- 三份 task `todo.md` 均保留：Pion reference gate失败且后续split封存；Wilson development测量及配对诊断已完成但reference proposal不一致、物理分数为空；Optimize训练/生产2×2/learned-$W$ blind comparison未完成。三项均有独立图文/文本状态报告；任何未完成的GPU/cluster工作需授权，但CPU协议/评分/校准设计仍可继续。140–199由Pion/Optimize/Wilson共同持有，须先联合冻结protocol/candidates/score/source再一次解盲。

## 0. 必须保持的三个负结论

1. **Wilson 两态污染：gate 盲点。** `spectral_physical_v1/` 中 spread/$V$ 仍小于 0.006、gate 仍通过，
   但 $c_1=0.5$ 时短窗 bias/SE 为 32.5。`window_paired_z` 更敏感但仍未进 gate。见
   [图与数据](../results/wilson_loop/spectral_physical_v1/README.md)及[有限 $N_t$ 口径](finite_nt_scope.md)。
2. **Pion 原 C2 0/8：INCONCLUSIVE。** 原 χ² subgate smoke 仅 8 个 dataset/cell，0/8 的双侧 95% CP 区间 [0,0.36942]、
   单侧上界 0.31234；这不能声称族错误率受控。独立 1000/cell 子门扩样随后发现，在 6/12/24 blocks 下正确 null 的拒绝率为 15.1%/5.4%/1.8%，说明固定 synthetic generator 下仍有明显 block-count 敏感性。原 smoke 与新 MC 是两个独立 run；C2 J=2/K=2 family 现有一项独立 400-dataset 扩样，183 valid、217 abstain、null cert 1/183、better power 20/183，twostate boundary 210/400。它是原 synthetic χ²-family subgate 的扩样，不是正式 full gate 或物理认证。Nnull=50 的最小可取 p 为 1/51，也不能检验 1% 门槛。
   配对协方差敏感性进一步在同 1000 个 ground-state-null datasets 上比较 λ=0/0.25/0.5：6 blocks 拒绝率为100.0%/16.0%/2.6%，12 blocks为70.1%/5.4%/0.8%，24 blocks为28.1%/2.5%/0.5%。这是协方差设置对 synthetic 子门 size 的强敏感性，不能据此挑选 shrinkage 参数作生产校准；配对差 familywise CI、p-value 分布和图见 [shrinkage 报告](../results/pion_projection/certificate_subgate_shrinkage_20261120_v1/README.md)。
   另一项 controlled Gaussian p=12/q=4 null simulation 将已知 covariance 与样本估计 covariance 分开：已知 covariance nominal size 为4.8–4.9%；λ=0 的样本 covariance size 在 B=6/12/24 为100%/69.3%/29.1%，B=6经验 q95 达 nominal χ² cutoff 的4.01e8倍，且 median rank=5/12；同DGP Monte Carlo rank calibration 的 held-out size 为4.4–6.0%。这定位出小 B 秩亏/eigen floor 的重要作用，但模型是固定线性高斯，并未验证生产非线性 mass fit。见[分因素报告与图](../results/pion_projection/certificate_subgate_factorized_20261120_v1/README.md)。
   production `fit_reference_gate` 的 plug-in Gaussian parametric bootstrap 随后在 Euclidean-time AR ρ=.5/.8、B=6/12/24、每 cell 250 outer × 399 bootstrap draws 中执行，598500次 bootstrap fit 全部有效。ρ=.5 下 χ² / bootstrap size 为16.4%/1.2%、6.0%/3.2%、2.4%/1.6%；ρ=.8 shifted generator 下两种方法都为0–0.4%。paired CI 显示 B=6/12 baseline 中 bootstrap 拒绝明显少于 χ²，但 bootstrap 自身未普遍达到5%，且 rho=.8 极保守；外层 N=250，不能据此选替代门。见[bootstrap报告与补充图](../results/pion_projection/certificate_subgate_bootstrap_20261120_v1/README.md) / [可读图复核](../results/pion_projection/certificate_subgate_bootstrap_20261120_v1/PLOT_REVIEW.md)。
3. **Optimize 类 B oracle 零误差：构造性。** 最新公平实验的目标显式含 $BHB$，类 B 又显式包含该 feature；
   oracle 为零是可表示性结果，不是 learned smear 学到了 $Q[U]$，也不证明 B 在真实物理数据上更优。

## 1. `pion_projection`

### CPU 已完成

| 工作 | 结果 / 边界 |
| --- | --- |
| A1–A5 身份与冻结 spec | submission/report/dev/val、实际 kernel/reference hash、IDs、候选、late metric 和 gate artifact；candidate 在 GPU runtime import 前验证身份。历史缺 artifact/spec 的 run 只 abstain。 |
| B GEVP rank / cutoff | rank=0、rank越界和负metric不再导致非法开方；原20/cell网格后已有独立16-cell × 400 datasets扩样、每 dataset 200 draws：coverage为0–4.0%，CP95上界最大约6.4%，mean bias 0.012–0.036，within-dataset bootstrap SE 0.00063–0.00321，所有外层/谱失败计数为0。typed failure区分 non-positive / unresolved metric；仍只证明该synthetic两态网格的区间严重欠覆盖。 |
| C gate / certificate / anchor | 正式流程和 χ² subgate 明确分开；wrong-state guard 8/8 标出。C2 J=2/K=2 family 独立扩样400计划 / 183 valid、217 abstain、null cert 1/183、better power 20/183、twostate boundary 210/400，只校准旧 synthetic χ²-family subgate。原 C3 anchor grid 仍 N=30；预选场景、bias-only null、common-block/lower-bound 与 sign-flip extension 均为各自独立 N=400/cell 图文。common-block lower bounds 的 null 假认证率为16.3–19.3%；independent-arm indices 在ρ=.9时只有0.5–1.0%，但 known-improvement power也仅4.5–5.0%。随后 studentized paired-block sign-flip 在明确 sharp exchangeable null 下的 rate 为2.8–6.0%，但 familywise CP95 较宽、power仅10.0%/21.0%，与 paired-t 没有清楚差别；bootstrap 功效较高但 null 认证也更高。所有结果只适用于各自声明的 synthetic generator，未测真实anchor，也未扩完整 C3 grid；不得称为物理错误率。 |
| 完整 reference-gate 首轮 MC | 7 个场景 × 100 个独立 dataset；按生产 `develop` gate 做 χ²、窗口漂移、相对误差、边界、反射检查。纯 E1 wrong-state 仍有 80/100 gate pass；relative-error 接受率 CI 半宽 0.1015 超出预注册 0.10 目标，标 `INCONCLUSIVE`，不含 candidate power。 |
| candidate full-certificate adapter parity | 真实文件入口 `develop→evaluate→joint→improvement_certificate` 与直接 helper 逐 draw parity：12 项差为 0，gate parity 通过；5 类身份篡改拒绝。adapter smoke 只验证程序路径，物理分数仍为 null；原 v2 主计划因 estimand / scenario / budget mismatch 未执行，不能与 amendment02 混为一轮。 |
| amendment01 / amendment02 主流程 | 原 v2 执行前审计为0/2814。amendment01误把smear `alpha=0.2` 当统计score alpha，故在595/2814停止；null cell 92/402 certificates、CP95 [0.189, 0.273] 仅作误配诊断。参数拆分后，amendment02 dry-run 核验五个合法链 `score_spec.alpha=metric level=0.05`、两类预期拒绝保留 seed/raw input/reason。修正版402/cell MC 已完成 2814/2814；null certification 28/402（CP95 [0.0468,0.0991]），wrong-state（ground overlap=0）仍有343/402认证，relative-error valid-only acceptance 25/60 为 `INCONCLUSIVE`。结果见 [ANALYSIS](../results/pion_projection/full_gate_amendment02_execution_01/ANALYSIS.md)、[RUN_REVIEW](../results/pion_projection/full_gate_amendment02_execution_01/RUN_REVIEW.md) 与[清晰 CP95 图](../results/pion_projection/full_gate_amendment02_execution_01/candidate_rates_diagnostic.png)。高层 prereg adapter hash 与执行 spec / receipts hash 不一致，故执行完成但严格 source provenance 为 `PARTIAL`；不得事后补样或合并其他 run。 |
| amendment03 source-aligned replay | 已完成 7×402=2814；13-file manifest/prereg/executor/current source hashes 闭合，2814/2814 receipt 与核心代码 hash 匹配，development/validation 原始数组与 amendment02 逐一相同，主结果及其他确定性字段 0/2814 不一致。2070 `PASS` + 744 `EXPECTED_REJECTION`，意外执行失败为 0。它是同 seed provenance/reproducibility audit，不是独立 MC；不合并、不缩窄区间，amendment02 仍是 `PARTIAL`。图文见 [ANALYSIS](../results/pion_projection/full_gate_amendment03_execution_01/ANALYSIS.md)、[RUN_REVIEW](../results/pion_projection/full_gate_amendment03_execution_01/RUN_REVIEW.md) 和[同 seed 对照图](../results/pion_projection/full_gate_amendment03_execution_01/candidate_rates_diagnostic.png)。 |
| robust-score family-wise CPU boundary scan | v1 的 0/2500 是零改善 far-null；v2/v3 才测试 log(1.05) 边界。v3 对 ρ=0.05/0.35/0.65、4 candidates×4 branches、2500 outer trials/cell 比较 candidate-level IUT + Holm/Bonferroni、branch Bonferroni-16、max-t-16、20% trimmed 与 Huber。Gaussian-boundary pointwise FWER 为 3/2500、39/2500、130/2500（0.12%/1.56%/5.20%）；在 ρ=.65 时 IUT Bonferroni、branch Bonferroni、max-t、trimmed、Huber 分别 21/2500、4/2500、23/2500、18/2500、25/2500。10% effect、ρ=.35 时检出率分别为 pointwise 69.0%、IUT Holm 41.4%、branch Bonferroni 19.2%、max-t 35.7%、trimmed 28.2%、Huber 39.2%。稳健估计量没有一致优于 mean；wrong-state 与 common-bias 结构负控中七种方法均 2500/2500 错误认证。见 [v3 图文报告](../results/pion_projection/familywise_score_cpu_20261120_v3/README.md)、[FWER 相关性图](../results/pion_projection/familywise_score_cpu_20261120_v3/correlation_fwer_diagnostics.png)、[功效图](../results/pion_projection/familywise_score_cpu_20261120_v3/robust_estimator_power.png) 和[结构负控图](../results/pion_projection/familywise_score_cpu_20261120_v3/structural_negative_controls.png)。该组 CPU 方法诊断的第一轮已完成；不可外推为物理 calibration，真实 independent anchor 仍 `NOT_RUN`。
| 新测量计划 | `NOT_RUN`/`READY`生命周期、generation绑定、manifest对照、checkpoint续跑与validation submission preflight已修复；4项focused tests passed。随后Pion D0–99真实测量已完成且identity/residual通过，但frozen reference gate FAIL；E anchor、D validation与共享holdout均未开启。

诊断文件：

- [Kunshan GPU pilot 90配置 provenance crosswalk、残差/耗时图](../results/kunshan_logs/archive_audit_v1/README.md)：pipe logs 与 pion provenance 90/90逐字段相同；v9复用了同一validation IDs 70–99。实际raw gauge身份与header后payload重复情况见[全量live byte audit](../results/kunshan_logs/live_archive_audit_v1/README.md)。
- [身份矩阵](../results/pion_projection/audit_20261119_identity/README.md)
- [GEVP ground-mode 网格](../results/pion_projection/gevp_ground_failure_grid_v1/README.md)
- [GEVP ground-mode 独立扩样 N=400/cell](../results/pion_projection/gevp_ground_failure_expanded_20261120_v1/README.md)与[coverage/bias 热图审查](../results/pion_projection/gevp_ground_failure_expanded_20261120_v1/PLOT_REVIEW.md)：CP95 coverage、dataset-bootstrap bias CI、失败与hash均逐项记录。
- [subgate calibration](../results/pion_projection/certificate_calibration_v1/README.md)
- [subgate 1000/cell 扩样](../results/pion_projection/certificate_subgate_mc_20261120_v1/README.md)与[补充可读图](../results/pion_projection/certificate_subgate_mc_20261120_v1/PLOT_REVIEW.md)：完整保存9个 cell 的逐例 p-value、失败、CP95 区间和 seed/hash；只验证 synthetic χ² 子门。
- [subgate 协方差 shrinkage 配对敏感性](../results/pion_projection/certificate_subgate_shrinkage_20261120_v1/README.md)：同一1000 datasets/blocks 配对比较 λ=0/0.25/0.5，含 marginal CP95、六项 familywise paired CI、p-value 分布图和 hashes；不支持 production λ 选择。
- [subgate known/estimated covariance 分因素校准](../results/pion_projection/certificate_subgate_factorized_20261120_v1/README.md)：12 cells、每 cell 5000 calibration + 5000 evaluation datasets，含 χ² size、经验临界值、rank-calibrated p-values、秩/eigen-floor诊断图及 source/protocol/output hashes；仅适用于声明的Gaussian线性null。
- [subgate production-fit conditional bootstrap](../results/pion_projection/certificate_subgate_bootstrap_20261120_v1/README.md)及[补充图审查](../results/pion_projection/certificate_subgate_bootstrap_20261120_v1/PLOT_REVIEW.md)：6 cells、每 cell 250 outer × 399 bootstrap fit，保存 nominal/conditional p-values、paired familywise intervals、invalid accounting 与 generator shift 图文；plugin bootstrap未普遍恢复5% size。
- [anchor paired intervals](../results/pion_projection/anchor_calibration_v1/README.md)
- [paired robust-score synthetic diagnostics](../results/pion_projection/robust_score_cpu_20261119_v1/README.md)
- [完整 reference-gate CPU MC](../results/pion_projection/full_gate_mc_20261119_v1/README.md)
- [candidate full-certificate adapter parity](../results/pion_projection/adapter_parity_20261119_v1/README.md)
- [candidate full-certificate MC v2 预注册计划（主 MC NOT_RUN）](../results/pion_projection/full_gate_mc_20261119_v2/README.md)
- [v2 原计划执行前阻塞（0/2814）](../results/pion_projection/full_gate_mc_20261119_v2_execution_01/README.md)
- [amendment01 完整预算 dry-run](../results/pion_projection/full_gate_mc_20261119_v2_amendment_01/README.md)
- [amendment01 停止原因与错误参数诊断](../results/pion_projection/full_gate_amendment01_execution_02/RUN_REVIEW.md)
- [amendment02 完整预算 dry-run 与图文状态](../results/pion_projection/full_gate_amendment02_full_dry_01/README.md)
- [amendment02 修正版预注册与执行计划](../results/pion_projection/full_gate_mc_20261119_v2_amendment_02/README.md)
- [amendment02 402/cell 执行汇总与逐例 receipts](../results/pion_projection/full_gate_amendment02_execution_01/README.md)
- [amendment02 结果解释](../results/pion_projection/full_gate_amendment02_execution_01/ANALYSIS.md)
- [amendment02 source-hash 复核](../results/pion_projection/full_gate_amendment02_execution_01/RUN_REVIEW.md)
- [amendment02 清晰 CP95 rate 图](../results/pion_projection/full_gate_amendment02_execution_01/candidate_rates_diagnostic.png)
- [amendment03 source-aligned replay 来源/逐 receipt/raw-array 审计](../results/pion_projection/full_gate_amendment03_execution_01/ANALYSIS.md)；完整 source/hash run review 在 [`RUN_REVIEW.md`](../results/pion_projection/full_gate_amendment03_execution_01/RUN_REVIEW.md)，CP95 + same-seed concordance 图在 [`candidate_rates_diagnostic.png`](../results/pion_projection/full_gate_amendment03_execution_01/candidate_rates_diagnostic.png)，结果文件 hash 在 [`analysis_provenance.json`](../results/pion_projection/full_gate_amendment03_execution_01/analysis_provenance.json)。并发从6调至10的执行 amendment 与原 spec 均有存档。
- [amendment01 402/cell 执行目录](../results/pion_projection/full_gate_amendment01_execution_02/)
- [robust-score family-wise v1 far-null与v2边界校准](../results/pion_projection/familywise_score_cpu_20261120_v2/README.md)，包含 preregistered protocol、独立dataset raw arrays、逐trial outcomes、source/output hashes、边界误认证放大图和弃权/common-bias图。v1 不得被解释为边界误认证率控制证据。
- [robust-score family-wise v3 相关性 / 多重性 / 抗离群诊断](../results/pion_projection/familywise_score_cpu_20261120_v3/README.md)，含 source/protocol/output hash 验证、独立 trial outcomes、逐场景 CP95 表，以及 FWER、power、结构负控三张图。candidate correlation 只扫声明的 equicorrelation；不能代表真实 correlator covariance。
- [测量计划 preflight](../results/pion_projection/measurement_plan_audit_v1/README.md)

### 仍需推进

- CPU 已完成第一轮方法诊断：paired log lower order statistic、median-only 排名诊断与 reference/window worst-case
  sensitivity 已对齐 draw IDs；400 个 synthetic datasets/cell 覆盖 null、known improvement、heavy tail、单个极端 draw、
  near-zero baseline、参考冲突和窗口排名翻转，输出 false-pass / abstain 的 Clopper–Pearson 区间及两张图。
  见 [稳健分数 README](../results/pion_projection/robust_score_cpu_20261119_v1/README.md)。这不是物理 calibration；若要报告
  首轮完整 gate 结果见 [README](../results/pion_projection/full_gate_mc_20261119_v1/README.md)，N=100 且 relative-error 场景精度未达标。原v2执行前审计发现候选/场景/预算不匹配，0/2814；amendment01因smear/statistical alpha混用停止，92/402 null certificates仅属于错误level=0.2诊断。代码现分开smear alpha与score alpha；amendment02 full-budget dry-run确认五个合法路径实际level=0.05、两类拒绝规范保存。修正版402/cell MC已完成；null 28/402的CP95包含5%但上界约9.9%，wrong-state仍343/402认证，relative-error valid-only接受率25/60为`INCONCLUSIVE`。高层 prereg 与执行 adapter hash 冲突，结果只作 synthetic diagnostic、严格来源链为`PARTIAL`；细节见 [ANALYSIS](../results/pion_projection/full_gate_amendment02_execution_01/ANALYSIS.md) 与 [RUN_REVIEW](../results/pion_projection/full_gate_amendment02_execution_01/RUN_REVIEW.md)。真实anchor仍 `NOT_RUN`。
- GEVP zero / near-zero / negative metric 已有 typed failure reason 与非法开方回归测试；旧 ground-mode 数据无需重跑。
- C2 J=2/K=2 synthetic family 已做独立 400 dataset 扩样：[原始结果、familywise CP95 和图](../results/pion_projection/certificate_family_expanded_20261120_v1/README.md)；该路径仍是 χ²-family subgate，two-state mass-boundary 导致主要弃权，不等同正式 full gate。
- C3 anchor 的三个预选 synthetic scenarios 已另做独立 400/cell 扩样（两臂 bootstrap indices 独立，旧称“paired”不表示共用配置块）：[数值表和图](../results/pion_projection/anchor_calibration_expanded_20261120_v1/README.md)、[绘图兼容性复核](../results/pion_projection/anchor_calibration_expanded_20261120_v1/PLOT_REVIEW.md)。原始 C3 多因素网格仍 30/cell；该扩样不替代真实 anchor。
- C3 等噪声 anchor-bias-only null 已独立运行 400 个 dataset IDs：[协议、逐例结果、偏差对照与图](../results/pion_projection/anchor_bias_null_20261120_v1/README.md)。即使 anchor 无偏，两臂独立 bootstrap 的 5th-percentile lower bound 仍有45/400假认证；固定±0.02偏移下为45/400与62/400。原文中的“paired”不代表共用配置块indices。naive 认证率为44.0–46.5%；anchor-offset 差的 familywise CI 跨零，不能声称偏移效应已分辨。新 [common-block 诊断](../results/pion_projection/paired_block_anchor_score_20261120_v1/README.md) 和 [三种 lower-bound 对照](../results/pion_projection/centered_anchor_score_20261120_v1/README.md)均为400 IDs/cell，均显示 common-block 下 null size 约16–19%，常见下界修正没有普遍修复；所有结果仅反映固定 synthetic DGP。
- 新增 **studentized paired-block sign-flip randomization**：[冻结 MC 结果](../results/pion_projection/block_randomization_score_20261120_v1/README.md)和[可读 null/anchor/power 与 paired-difference 图](../results/pion_projection/block_randomization_score_20261120_v1/plot_review/PLOT_REVIEW.md)。5 worlds × 2 correlation cells × 400 outer datasets；4000 dataset/correlation cases、7200条含 anchor offsets 的行全部有效。sharp exchangeable null 下 rate 2.8–6.0%，lower-noise power 10.0%/21.0%；配对 t 接近 sign-flip，bootstrap 功效更高但 null 认证也更多。结论是这条理论路线可在其明确 exchangeability 前提下作为方法候选，不是 weak-null 通用证书、物理 coverage 或共同模型偏差防护；下一步仍是物理 anchor。该结果完成原计划 CPU randomization 支线，勿重跑相同 DGP。
- robust-score family-wise v1–v3 的首轮 CPU 相关性、candidate-level Holm/Bonferroni、max-t、Huber/trimmed 比较已完成，不要重跑。v3 未覆盖实际 correlator covariance 与 near-zero abstention；如要继续 CPU 方法学，只能先声明能改变的具体决策，再冻结新协方差/样本量方案并报告 CP95 FWER、power、abstention、逐候选影响和失败文字。真实 anchor / 新 GPU 测量是当前主要未完成项。
- amendment03 的同 seed 重放证明当前 frozen manifest 下数组与 deterministic outputs 可复现，但不能增加 MC 精度或改变 amendment02 的 `PARTIAL` 标签。C2 原 J=2/K=2 family valid N=6 后已有独立400-dataset扩样：183 valid、217 abstain，null cert 1/183、better power 20/183，twostate boundary 210/400；它只扩展 synthetic χ²-family subgate，不是 full official gate。C3 原 anchor grid仍30/cell；C3另有三个预选场景的独立400/cell扩样，naive pseudo-replication频繁认证，paired在旧anchor-bias场景仍有18.2%认证，但该场景并非null，independent-repeat CI均跨零；新等噪声bias-only null中paired认证率为11.3–15.5%，零偏移下也高于5%，但±0.02的配对变化CI跨零。这没有扩完整C3 grid，也不构成物理anchor证据。GEVP已独立扩至400/cell并确认本synthetic两态网格覆盖率严重不足。新增 C2 子门及协方差/conditional-bootstrap校准只诊断子门行为，都不能校准 full certificate。它们也不同于 402/cell full-gate 和 2500-trial family-wise MC。production-fit bootstrap 首轮已完成但不普遍达到名义size；同一 generator 不再扩样。若扩其他小样本项，先计算并预注册目标 CP 区间精度，使用新独立 seeds，给逐场景区间图、失败/弃权计数与解释，不与旧 run 混池。
- 真实测量：历史pion pilot的90条配置可从Kunshan logs与provenance复核，但reference gate失败且不是独立anchor。新独立HMC链D(job128526595)与anchor链E(job128528670)已完成：receipt、逐trajectory ΔH/accept、manifest及raw payload hashes 200/200、100/100均核验，图文分别见[D诊断](../results/wilson_loop/hmc_production_20261120/diagnostic/README.md)、[E诊断](../results/wilson_loop/hmc_anchor_20261121/diagnostic/README.md)和[跨链比较](../results/wilson_loop/hmc_chain_comparison_20261120/README.md)。随后D IDs 0–99 Pion correlator measurement已完成，reference gate FAIL；两态与有效质量诊断见[Pion closure报告](../results/pion_projection/s16t16d_closure_20261120/README.md)。按stop rule不测E0–59 anchor、不测D validation、不打开D140–199。共享holdout仍须三方预注册并冻结后一次性解盲。
- 扩大 gate Monte Carlo 与多态 GEVP / mode tracking 属后续研究；先预声明精度和预算。

开工文档：[pion todo](../tasks/pion_projection/todo.md)。

## 2. `wilson_loop`

### CPU 已完成

P0 pending resume、P0b 投影支持域、P1a 事务故障矩阵、P1b NERSC header checksum、P2 invalid evaluate、P2b 统计口径、
P3 有限 $N_t$/paired-window 文档、F0–F3 receipts/search/state integration，以及 F4 receipt/schema synthetic preflight 均有代码/测试/文字诊断。新 P0b 受控相位
网格为 126 格；支持域 63/63 通过，域外 63/63 按策略拒绝；切口外协变残差最大 $9.9\times10^{-11}$。精确切口端点
有 7 个中心分支敏感的协变 outlier，已在图文报告中单列。参见
[受控相位图文诊断](../results/wilson_loop/audit_20261119_projection_domain_v2/README.md)。

关键证据：

- [resume](../results/wilson_loop/audit_20261119_resume/README.md)：同 spec 2/3→3，和 clean array/行摘要一致；
- [transaction](../results/wilson_loop/audit_20261119_transaction/README.md)：10 种混拼故障拒绝；
- [NERSC checksum](../results/wilson_loop/audit_20261119_nersc/README.md)：错误头拒绝，私有 MD5 不覆盖标准 checksum；
- [两态反例图](../results/wilson_loop/spectral_physical_v1/spectral_physical.png)：spread gate 通过但值系统偏离；
- [F4 preflight 故障矩阵](../results/wilson_loop/audit_20261119_f4_preflight/README.md)：1 个 synthetic schema control 只到 `schema_ready`，15 类坏输入拒绝，未生成 production receipt；
- [P4 null / two-state synthetic controls](../results/wilson_loop/audit_20261119_p4_controls/README.md)：旧 spread gate 在两态共偏差下仍 80/80 PASS；使用已知合成 $E_0$ oracle anchor 后 80/80 abstain，不能迁移成生产认证。
- [纯空间 stout CPU small-gauge 检查](../results/wilson_loop/audit_20261119_stout_cpu/README.md)：协变性、unitarity、determinant、时间局域和 loop gauge invariance 最大残差 $4.45\times10^{-15}$；目前只是 standalone NumPy kernel，未接生产 `build_kernel` / HMC。
- [stout opt-in interface 与单小场响应表](../results/wilson_loop/audit_20261119_stout_interface/README.md)：`kind=stout` 显式进入 kernel/contract，默认 APE 逐值不变；identity/APE/stout 只在一个 deterministic field 比响应，无 ensemble uncertainty 或物理排序。
- [P4 null/common-bias 402 datasets/cell 扩样](../results/wilson_loop/audit_20261119_p4_controls_n402/README.md)：dataset-level joint outcomes 与 CP95 分面图；common-bias 下 legacy 两者 402/402 通过，oracle 两者 402/402 弃权，结果不外推到真实 gate。
- [P4 known-improvement positive control](../results/wilson_loop/audit_20261119_p4_known_improvement_v2/README.md)：402 paired datasets；两 gate 同时通过397/402，改善检出324/402（CP95 0.764–0.843）；78次未检出中5次gate弃权、73次ratio区间跨1。
- [P4 outer-bootstrap resolution sensitivity](../results/wilson_loop/audit_20261119_p4_known_improvement_sensitivity_v1/README.md)：同一402 datasets将outer draws从100增至1000，检出323/402；不能当成额外独立样本。
- [P4 power-vs-cost scan](../results/wilson_loop/audit_20261119_p4_power_cost_v1/README.md)：独立预注册 9 cells × 402 datasets，固定 block length=5，扫描80/160/320个配对配置和1.78×/4×/8.16×输入方差改善。四倍改善检出324/402、350/402、369/402；320配置达到预声明90%检出目标（CP95 [0.887,0.943]）。弱效应各cell区间重叠且点率非单调，解释见[独立分析](../results/wilson_loop/audit_20261119_p4_power_cost_v1/ANALYSIS.md)。
- [P4 nested-prefix 配对预算诊断](../results/wilson_loop/audit_20261119_p4_nested_prefix_v2/README.md)：每种效应402个独立 synthetic datasets，80/160/320是同一数据的嵌套前缀；弱1.78×效应的三组配对预算差区间均跨零。4×效应从80到160有可分辨增加（+5.97 pp，paired bootstrap CI95 [2.24,9.95]），160到320未分辨（+1.00 pp [−2.49,4.48]）；320达到预注册检出率目标。图同时给 marginal CP95 和 paired contrast 区间；不是物理功效结论。
- RunState 当前 conditional-only；APE 263/233/222 是诊断，不是 physical score。

### 仍需推进

- F4 有部分 production log evidence，见[旧 HMC log 诊断](../results/wilson_loop/hmc_log_archive_diagnostic_v1/README.md)和[新 live byte audit](../results/kunshan_logs/live_archive_audit_v1/README.md)：旧 S16T16 DONE=900 planned、rounded acceptance=0.972、45个稀疏ΔH点；B/C两个200-config campaign各有70个checkpoint，日志物理字段70/70相同。B DONE=0.977按planned 1400对应1368次accept；在相同源码/批处理与max-save解释下，停止于traj1396，source-assisted实际率1368/1396=97.994%，但未记录每条轨迹的决定。500/500 raw-file SHA均匹配各自manifest，S16T16/B、S16T16/C、B/C的header后payload相同率分别100/100、100/100、200/200；旧跨manifest hash差异由NERSC header解释。raw-byte identity已闭合，但完整F4仍缺逐轨迹ΔH/accept-reject、热化与可靠自相关规则；见[身份图](../results/kunshan_logs/live_archive_audit_v1/identity_and_duplicate_payloads.png)和[HMC图](../results/kunshan_logs/live_archive_audit_v1/hmc_b_sparse_diagnostics.png)。
- P4 初始每类40已扩至每类402个独立datasets，null/common-bias与known-improvement控制均有图文；100/1000 outer-draw sensitivity不是新增样本。新 power-cost scan 显示四倍输入方差改善在80/160/320配置下分别324/402、350/402、369/402，320配置达到预注册90%检出目标；1.78倍改善仅46–68/402且区间重叠，不能把独立cell的非单调点率解释为功效随配置下降。上述全是oracle-anchor synthetic方法诊断，不是物理gate认证。stout已接显式`kind=stout` kernel/contract；本轮使其沿 NumPy/CuPy backend 运算，APE默认分支不变；单小场response无ensemble SE/CI。旧protocol_v4/B完整F4 receipt仍不可追溯，但新的D/E链HMC receipt已完成；真实Wilson-loop与stout/APE物理配对仍`NOT_RUN`。
- P4 选择一个 matched-budget 扩展（stout/improved loop、multilevel、GEVP、多体积或 momentum），不混合多项变化。
- nested-prefix 配对诊断已完成，弱1.78×预算差仍未分辨。新的 CPU 扩展只有在明确会改变预算或 gate 决策时再立项，需预注册精度、独立 seed 范围及 block-length/物理自相关扫描，并交 paired-difference 图和失败/弃权解释；不要重复同一 generator 的无目标扩样，也不要通过调低 gate 阈值追求通过。

开工文档：[Wilson todo](../tasks/wilson_loop/todo.md)。

## 3. `optimize_gaussian`

### CPU 已完成

| 包 | 结果 / 边界 |
| --- | --- |
| A trusted input | 内容摘要、metadata、residual 与实际 reference/bootstrap 文件身份；缺项降级/拒绝。 |
| B fit-state | point/replica 同估计量；60×200 独立 synthetic regression 与图；training-frozen 区间不传播 train amplitude uncertainty。另有 200 datasets/cell 的相关噪声、错误 reference、block length 和幅度传播 stress，以及三个质量 × 两个 reference-offset、400 datasets/cell 的配对扫描；均明确 q-profile coverage 与 q=1 reference-shape 检查不是同一问题。 |
| C fair operator-class / optimizer convergence | 全空间协变 Laplacian、clover $B$、matched point/color probes、同一实系数域；3-seed 初始诊断、N=20扩展和新的N=100独立 follow-up均有图文。N=100的最坏Bernoulli MCSE目标0.05，不是95%区间半宽保证；B oracle零误差仍是构造性，且该类实验不证明learned smear优势。 |
| D real BCB pipeline | BCB response 实际接入 Bundle/SearchAdapter；search 与 exact 一致是同一评价器的构造结果，不是 surrogate 误差验证。 |

诊断文件：

- [60×200 fit-state regression 与图](../results/optimize_gaussian/cpu_close_20261119_B_regression_fitted/README.md)
- [B 相关噪声 / block / 错误 reference stress 图与逐 dataset 区间](../results/optimize_gaussian/cpu_close_20261119_B_stress_v2/README.md)
- [B 多质量 reference-shape 图与逐 dataset 区间](../results/optimize_gaussian/cpu_close_20261119_B_multimass_v1/README.md)
- [B time-AR 400 datasets/cell 图与区间](../results/optimize_gaussian/cpu_close_20261119_B_timear_v1/README.md)
- [learned initializer 有限预算 toy 图文结果](../results/optimize_gaussian/cpu_initializer_toy_v1/README.md)
- [项目 H/B cross-link initializer 图文结果](../results/optimize_gaussian/cpu_operator_initializer_v1/README.md)
- [matched cross-link 结果与图](../results/optimize_gaussian/cpu_close_20261119_C_matched/README.md)
- [C optimizer convergence 图与逐 seed 结果](../results/optimize_gaussian/cpu_close_20261119_C_convergence/README.md)
- [C independent links/probes 20-dataset 扩展与 paired intervals](../results/optimize_gaussian/cpu_close_20261119_C_expanded_v1/README.md)
- [C independent links/probes N=100 follow-up 图文结果](../results/optimize_gaussian/cpu_close_20261119_C_followup_n100_v2/README.md)
- [实际 BCB—search 管线](../results/optimize_gaussian/cpu_close_20261119_D/README.md)
- 历史 `unified_v1/` 覆盖事故记录在 [package B README](../results/optimize_gaussian/cpu_next_package_b/README.md)；旧 fold 内容在仓库 git 中无法恢复，不能把旧点值冒充新 artifact。

### 仍需推进

- v9 已有修正特征的 GPU 系数重训与 held-out test IDs 70–99；其中 $W$ 是固定随机特征基而非训练参数，且 test 已经公开、不可重用。[v9 provenance audit](../results/optimize_gaussian/v9_provenance_audit_v1/README.md)进一步确认 manifest 的4/4源码依赖及 statistics hash 均可在当前树或 Git 历史精确找回；但训练环境/设备/命令 receipt、原始 propagator bytes 与原始输出 hashes 缺失；90个 gauge inputs 已与远端 raw files 90/90匹配。下一步是补齐剩余运行/propagator provenance，或明示不可恢复；之后仍需 trainable-$W$ 或 initializer、生产 P3 2×2，以及新 IDs 上对 SLSQP/强谱基的全新 blind comparison。
- 通用SPD和项目H/B cross-link learned-initializer toy均已完成：低预算下可优于部分zero/random SLSQP，但H/B IID strong spectral略优，shift下learned优势有限，高预算SLSQP更低；没有显示稳定超过强基线。C另有N=100 independent follow-up，在六个epsilon=0.1 class×budget条件中Powell−SLSQP test error均为正且dataset bootstrap CI95不跨零；它仍只是合成optimizer诊断，不是learned smear或物理数据证据。边界见[通用 toy](../results/optimize_gaussian/cpu_initializer_toy_v1/README.md)、[H/B cross-link结果](../results/optimize_gaussian/cpu_operator_initializer_v1/README.md)和[C N=100 follow-up](../results/optimize_gaussian/cpu_close_20261119_C_followup_n100_v2/README.md)。C N=100最坏Bernoulli MCSE目标为0.05但不是CI半宽保证；B time-AR正确reference下all-window coverage仅0.6125–0.655且未实现gate。
- B stress 固定一种相对噪声结构，进一步扩展应先定义效应与MC目标；C N=100 follow-up已完成一个独立CPU replication，若再扩样或扩噪声仍需新预注册和区间图，可在CPU开展但不能替代真实$W$盲测。

开工文档：[optimize todo](../tasks/optimize_gaussian/todo.md)。

## 4. 复核用户转述的其他 agent 结论

1. `unified_v1/` 被同名输出覆盖：package B README 已如实保留。当前 git 没有旧目录的已跟踪版本，因此“仓库内不可恢复”正确；这不能推出所有外部备份都不存在。
2. Pion的D0–99 correlator measurement已完成但reference gate FAIL；两态和effective-mass图文是同一development样本上的诊断，当前不启动E0–59 anchor、D validation或shared holdout。Wilson D0–99 development与真实reference/APE-stout开发配对诊断均已完成；A/B candidate pass、C joint-max reject，说明未冻结的reference候选仍不一致，不能认证物理分数。D链100/100身份通过但较早61行aggregate hash差异未解释。Optimize训练/P3 2×2/blind test仍未完成；generic worker和训练protocol hash接口已有CPU进展。D140–199须三任务共同冻结后才开放；跨任务重用不增加独立样本数。历史日志/source查证、RunSpec/solver/preflight和reference校准设计仍有CPU可推进项，因此“所有未做事项都需GPU/授权”过宽。
3. 小样本提醒正确但需区分：Pion C2其它子门仍有6–8 datasets/cell（部分端到端变体8–15），但 J=2/K=2 family 已另扩到400个计划数据集、183 valid；C3原始anchor grid仍30/cell，另有预选场景、等噪声bias-only、common-block / lower-bound 与 sign-flip 方法学诊断等独立400/cell结果；GEVP原grid为20/cell并已另扩至400/cell。Optimize C早期20-dataset扩展的最坏Bernoulli MC SE约0.112，另有独立N=100 follow-up。Pion amendment02虽完成402/cell，但 null 区间上界约9.9%，relative-error有效分母仅60且为`INCONCLUSIVE`，wrong-state结构假通过率高；同时高层 prereg / 执行 adapter hash 冲突，严格来源链`PARTIAL`。Optimize B stress为200/cell、多质量与time-AR扫描为400/cell；Wilson P4 power-cost为402/cell。样本数只约束各自声明的synthetic estimand，不消除物理系统误差，也不自动构成发表级精度。
4. 子 agent 提出的 pion rank/敏感性网格缺口由 `_eigvals` 修正与 `gevp_ground_failure_grid_v1` 覆盖；失败原因分类和零/近零 metric fixture 也已补齐。Wilson 投影遗漏由 `audit_20261119_projection_domain_v2/` 补上：控制实际 `arg det(M)` 并扫描切口两侧；精确端点的中心分支跳变有单独图文诊断。

## 5. LatticeArena 的可扩展部分

- **新物理任务**：新增 task module + frozen protocol / RunSpec，明示格点、边界、source/sink、momentum、单位和输入身份。
- **新算法 / kernel**：使用 `OperatorContract` 检查 linearity、Hermiticity、gauge covariance、symmetry 与资源能力；由
  `MeasurementBundle` 暴露统一数据。
- **可微算子**：将局部核梯度合同与ensemble-risk梯度分层；针对空间中心化、伴随边/方向映射等链式项做逐参数多步长差分图，配套有限输入/几何检查。算子级正确性可先在CPU证明，不能替代风险估计梯度或GPU数值验证。
- **新采集**：measurement plan、GPU 前 preflight、真实 provenance / code-input receipts、可续跑的事务存储。
- **算符参数一致性**：source/sink wrapper 参数可以在低层 kernel 层统一检查（例如 $\rho,n$ 到 Wuppertal $\alpha$），在 GPU 初始化前拒绝不匹配计划，并把核对表写入 receipt。
- **新分数 / reference**：冻结 `score_spec`、draw identity、reference gate、paired comparator 和 multiplicity；conditional score 与 physical score 分开。
- **新优化器 / agent**：经 `SearchAdapter` 走外部预算、candidate validation、失败记录和搜索 trace，不让 agent 自报增加预算。
- **新诊断**：统一保存 seed、数据集粒度、MC 误差、失败样本和图；新 benchmark 需 null 与 known-signal controls。
- **解析界与实验规划**：将定理假设、量纲参数和阈值显式化，先生成无量纲样本量/系统误差敏感度图，再由物理负责人填入有依据的范围；解析图与 synthetic calibration、真实测量用不同证据标签，边界单元和单调性由CPU tests检查。
- **多 estimand lanes**：同一底层测量可导出有限-T观测量与基态外推两个独立lane，共享逐样本身份但各自冻结统计估计、热/谱/离散化误差和弃权门；联合结果保留跨lane相关性，不把一个lane的通过移作另一个lane认证。
- **归档身份层**：同时存储完整文件 hash、NERSC header 后 payload hash、header 元数据与 run-local configuration ID，并显式标出跨目录重复 payload；本轮发现 raw-file SHA 不同仍可能是同一 gauge field，单一文件 hash不足以比较物理独立性。

## 6. 开工顺序

1. Pion amendment02修正版402/cell主MC严格source chain仍为`PARTIAL`；amendment03同seed audit2814/2814一致但不是新增样本。Family-wise v1–v3、common-block/lower-bound、sign-flip、rare-tail weak-null N=3000/cell方法对照已完成，不重复固定DGP。C2多数原始cell只有约6–8 datasets，C3原网格约30/cell；预选N=400/cell扩样只改善对应synthetic MC精度，不能合并402/cell full-gate或2500-trial family-wise分母。D0–99 development已测但single-cosh gate FAIL；两态、有效质量与reference-window图文已在Pion closure目录。下一步先冻结新的独立reference确认方案和stop rule；在方案定稿前不开E anchor、D validation或D140–199。该段385 passed是2026-11-21历史快照；当前全套 CPU/GPU-free suite见§12。
2. Wilson P4 controls、HMC D/E诊断、单配置GPU smoke、D0–99 full development、development-only reference/APE-stout分析及 offset-insensitive force 的真实数据探索诊断均已完成；100/100 identity与manifest join通过，job128540026 COMPLETED 0:0 / 12:15:58。A/B point-max candidate为2.0965 pass，C centered/uncentered joint max为2.741/4.084 reject，reference提案未冻结；paired candidate risk ratios为4.84–12.11，仍只是未认证reference上的development诊断。新 force 分析表明大 R 的 T-window/Creutz 变化仍显著且区间变宽，适合作为方法选择材料，不提供基态/物理认证。Stout明显比APE慢且非matched-cost。D120–139需在estimand、有限-T控制和family-wise规则冻结并授权后再考虑；D140–199继续封存，physical_score=null。图、报告和执行方向见[Wilson TODO](../tasks/wilson_loop/todo.md)及[force诊断报告](../results/wilson_loop/development_force_diagnostic_20261121_v1/README.md)。
3. Optimize已有CPU initializer与SLSQP/Powell比较，但不回答learned-smear优劣。v9 fixed-random-W GPU重训和 IDs70–99 test已公开；源码hash已恢复，但原始propagator bytes与运行/设备receipt仍缺。新D0–99 Pion propagator缓存和 receipt adapter 已对真实缓存100/100验证；无需重做这些point inversion。Optimize-specific RunSpec builder、假worker端到端 preflight、显式 solver-contract 到 `train.optimize` 的CPU接线均已完成，后者4模块87 passed并带文本诊断；尚未生成基于 reviewed protocol/真实文件的 production RunSpec，生产阈值也未冻结。Pion reference gate失败，因此所有基于它的风险分只能标`diagnostic_only`。trainable-W对Gaussian、同预算SLSQP与强谱基的blind comparison等三方共同冻结后才可能解盲D140–199；交paired-risk CI、KKT/residual、收敛/成本图、失败/弃权表和解释，不能把跨任务复用计为独立验证。
## 7. 2026-11-21 本次复核与用户决定

- **Optimize**：确认性 family 固定为 F=2：trainable-W 对同预算 SLSQP、trainable-W 对一个固定强谱基；[degree-4 Chebyshev contract/响应图](../results/optimize_gaussian/degree4_chebyshev_contract_20261122_v4/README.md)包含实际周期 kernel 的 matrix-free filter 与未归一化 Gaussian sandwich CPU 候选，仍是待审基线而非已证明最强或已批准方案。D11代数/CPU审阅和两份协议文档的共享objective/IDs/失败分母/双预算一致性核对均已完成，未发现冲突；D04/D06数值仍按用户要求不冻结。
- **Pion**：用户接受 bounded block-MSE 作为不同于原 ensemble-risk 的 estimand。独立读取 168-cell × 3000 raw datasets 后，504000 行下界、事件、认证和逐格分母与 summary 全部相符，最大逐行公式差为0；protocol source hashes与所有artifact hashes通过，图文已视检。此条件性 synthetic calibration 的 `physical_score` 仍为 null；下一步交物理范围/clipping、失败块、独立块来源、anchor共同偏差覆盖和两条测量流 identity/reference 的图或文字决策流程，不扩同一 Monte Carlo 网格。
- **Wilson**：用户选择有限-$T$ Creutz 与基态离散静态力两个分开的 estimand lanes。用户要求暂时保持 `NOT_READY/UNCERTIFIED` 与封存，因此下一位 agent 只整理lane-specific候选协议、误差/污染敏感度和图文分母流程，不要求现在冻结R/T/kernel、阈值或格距/体积误差预算，也不再要求二选一。
- **对先前 agent 汇报的核实**：`unified_v1/` 覆盖事故与 package B 报告一致，旧 fold 在当前 Git 中不可恢复；结论不涉及仓库外备份。把所有剩余项概括为“都需 GPU/授权”过宽，三个任务仍有 CPU/文档层的决策和协议工作。C2/C3 原小网格确有约6–30 datasets/cell的低分母，但已扩样的 N=400/402、N=1000/2500 结果属于不同的预选 DGP/estimand；如需更窄 Monte Carlo 误差，须先给出精度目标并逐格报告，不能合并，也不补物理系统误差。
- **上一轮测试快照（后由§8更新）**：bounded-score focused tests **12 passed**；当时全 CPU/GPU-free suite **374 passed, 1 skipped, 1 warning**。三份 task todo 均保留，因为 Pion reference/M2 gate、Optimize 真实方法对照、Wilson 两lane物理识别/确认协议尚未通过。

## 8. 2026-11-21 追加：CPU 分析推进与 handoff

- **Pion bounded block-MSE**：新增无量纲规划敏感度图与文字推导，扫描 `n=12/24/100/400`、`F=1/2/4` 和两种anchor误差分配。图说明统计误差随块数降低、anchor系统误差形成固定底限；示例 `B/R=0.05` 非物理估计。24个解析情景，没有新增MC/测量。相关测试合计 **26 passed**；后续需先冻结物理质量范围/单位、clipping与失败块规则、独立block来源和anchor common-bias上界。[报告](../results/pion_projection/bounded_score_planning_20261121_v1/README.md)
- **Optimize**：核对并链接现有[生产前研究决策单](../tasks/optimize_gaussian/protocol_decision_review_20261121.md)：F=2 已固定为 trainable-W vs 同预算 SLSQP、trainable-W vs 固定强谱基；degree-4 Chebyshev仅是待审候选。Pion reference未通过时风险只能 `diagnostic_only`；下一步由研究者审阅 D04/D06 和 D11 contract，再生成真实 hash-bound RunSpec、完成 trainable-W CPU接线图文。此步骤仍不访问盲测或启动GPU。
- **Optimize trainable-W算子梯度**：新CPU诊断使用实际 link-centred features 与Hermitian hopping kernel，在H=2合成fixture中对 `Re<psi|K(W,v,c)|psi>` 的7个参数做9级中心差分，共63/63个有限检查；固定步长最大绝对误差约`3.52e-8`，扫描最佳`3.24e-9`，图文与原始CSV见[报告](../results/optimize_gaussian/trainable_w_operator_gradient_20261121_v1/README.md)。这是实现级导数证据，不是ensemble-risk梯度、训练结果或物理比较；`train.main`/RunSpec的真实trainable-W目标仍未接通。
- **Optimize gradient regression**：新增完整实际算子相关函数的有限差分与非法输入用例，`tests/test_optimize_trainable_w.py` 当前 **13 passed**。它检查方向中心化的伴随项、双向 hopping、W/v/c 参数偏导和拒绝路径；不代表 GPU/CuPy或 ensemble-risk 目标验证。
- **Wilson**：新增正谱假设下有限-T Creutz 到基态离散力的解析污染界及 Q-gap 敏感度图；14,884个格点均为公式计算，不是拟合输入。focused 新旧相关测试合计 **26 passed**。下一步分别冻结有限-T Creutz 的 R/T/kernel 与统计规则，以及基态力的 Q/gap或多-T识别、Nt=16热污染和格距/体积误差界；无这些证据时维持 `GROUND_STATE_FORCE_UNCERTIFIED`。[报告](../results/wilson_loop/ground_state_bound_20261121_v1/README.md)
- **此轮复核和 suite**：跨任务 focused tests **26 passed**（Pion planning 7、bounded-score 12、Wilson ground-state bound 7）；Optimize trainable-W focused suite **13 passed**。全套 CPU/GPU-free pytest **385 passed, 1 skipped, 1 warning**。唯一 skip 为环境缺少 CuPy 的 stout parity；warning 是 Wilson projection rejection fixture 的既有 RuntimeWarning。三张新图已视觉检查，列出的 artifact 与源码 hash 已复算一致，新增 TODO/报告路径均存在。三份 TODO 均未完成，故保留；不得把新敏感度图升级为物理 coverage 或 production score。

## 9. 当前完成审计与最小下一步

| Task | 当前证据已闭合 | 核心未通过项 | 能改变状态的最小下一交付 | 责任/边界 |
| --- | --- | --- | --- | --- |
| `pion_projection` | D0–99 development 身份与诊断；bounded block-MSE 条件 synthetic calibration；两类 source/sink 流的 CPU contract/旧数据诊断；维度化 anchor/block 敏感度图；失败块硬弃权与最坏界计分的解析对照及单元测试 | single-cosh reference gate 为 FAIL；M2 为 `ABSTAIN/NOT_READY`；旧 source–sink 5% identity 门失败；物理范围、独立块、anchor 共偏差界及失败策略选择未定 | 研究者审阅目标质量/单位、range 或 clipping、独立 evaluation block 来源、anchor common-bias 界，并选择失败块硬弃权或failure-augmented estimand；point-source M2 与 matched source–sink 两流分别给出 reference/identity/stop contract。若该方案仍不能改变“不进入 E”的判断，则停止新 calibration | 方案/物理解释由研究者审阅；E、新 validation 与 shared holdout 仍需单独授权。不得以更宽松门槛翻转已观察 D 的 FAIL |
| `optimize_gaussian` | worker/RunSpec/solver CPU 接线；trainable-W 参数化和实际 hopping-correlator 局部梯度差分检查；用户已固定 F=2 与 SLSQP/强谱两项比较 | reference 未通过；`r_star`/D06、D11 baseline contract 未冻结；trainable-W 尚未进入生产 `train.main` risk objective；真实 F=2 与 P3 生产比较均未运行 | 研究者先决定 D04 reference、D06 最小效应；审阅 D11 degree-4 Chebyshev 算符与同一 objective/双预算。批准后，按新协议接 parameterized evaluator、RunSpec hashes、failure receipts 和 CPU risk fixture；生产比较另需 GPU、输入和 split 授权 | 实现者不代填 reference、阈值、solver/cost 与物理约束；63项局部梯度点不是训练样本或风险比较 |
| `wilson_loop` | D0–99 100/100 identity 与 development 分析；有限-T Creutz 和基态离散静态力已选为分开的 estimand；现有 force/window/paired 风险成本诊断及正谱 Q-gap 解析敏感度 | 两 lane 的 primary R/T、kernel、统计 family/多重性、容差与失败规则未冻结；F lane 的真实 Q/gap/热绕行及格距/体积系统误差未受控 | 研究者分别审阅 C lane 的有限-T observable contract 与 F lane 的谱/多-T截断或 Q-gap + thermal/systematic budget；若不可识别，F 保持 `GROUND_STATE_FORCE_UNCERTIFIED` | D0–99 已观察，只能支持 development 诊断；D100–119 gap、D120–139 validation、D140–199 holdout不因协议草案而开放 |
| 三任务共同 holdout | shared split 身份和跨任务复用约束已记录 | 三方 candidate、endpoint、exclusion、分析/source hashes 未共同冻结；一次性解盲未获授权 | 三方先冻结完整协议、代码和访问计划，记录独立/相关证据计数及 authorization，再按一次性流程访问；任一 reference gate 未通过则 preflight 必须拒绝访问 | 不把同一批配置计成多个独立验证；所有 planned failures/abstentions 留在分母 |

**审计结论（2026-11-21工作树）**：没有一份 task TODO 已达到可删除条件。CPU/文档可独立推进项已补入各自 TODO；剩余状态变化分别依赖研究者的科学决策，或真实输入/GPU/数据授权。该历史 suite 385 passed 仅支持软件/CPU fixture 范围，不能替代以上任一物理或生产门。

## 10. 2026-11-22 Pion 失败块处理敏感度

为推进已接受的 bounded block-MSE estimand、但不代填物理失败政策，本轮新增 `tasks/pion_projection/failure_aware_bounded_score.py` 与解析图文报告 [`bounded_score_failure_policy_20261122_v2`](../results/pion_projection/bounded_score_failure_policy_20261122_v2/README.md)。技术选择对照为：任何块缺失则整项 `ABSTAIN`；或者把失败块按`−R²`编码且使用planned块数作分母。后者的下界是`L/R²=(1−φ) μ_valid−φ−sqrt(2 log(F/α_s)/N)−2B/R`，认证条件还需大于`δ*/R²`。示例`F=2, α_s=0.05, B/R=δ*/R²=0`仅说明量纲与代数代价，不是生产参数；N=12、失败比例20%时，即使成功块改善达到最大值仍不可认证。14项纯CPU边界/单调性用例通过；未读测量或受限split，无MC/GPU/QUDA，物理分数保持null。若失败方法没有有界反事实输出，最坏编码定义的是新 operational estimand，不能包装成原始物理质量MSE。故该交付减少了失败处理方案的技术不确定性，但仍由研究者选择目标范围、block单位、anchor与失败策略；Pion TODO继续保留。

## 11. 2026-11-22 Optimize degree-4 谱基候选

为落实用户选定的第二个确认性对照（trainable-W vs 固定强谱基，同时保留 trainable-W vs 同预算 SLSQP，`F=2`），新增[受约束 Chebyshev 谱响应 contract 与图](../results/optimize_gaussian/degree4_chebyshev_contract_20261122_v4/README.md)。它基于现有周期三维协变 hopping `H`，规定 `spec(H)⊂[-12,0]`、`y=I+H/12∈[0,1]`，以单调 Bernstein controls `0≤b0≤b1≤b2≤b3≤b4=1` 定义 degree-at-most-4 多项式，再转换到 Chebyshev 计算基；候选响应因此在假设谱域内落在 `[0,1]`，低动量归一化为1并随 `−H` 不增。新增 matrix-free CPU `P4(H)` 与未归一化 `G^mP4(H)G^m` 候选；图中曲线只是可行系数示例，不是训练结果。

隔离纯 CPU 实现 `tests/test_optimize_chebyshev_baseline.py` **19 passed**，覆盖 dense/matrix-free kernel 一致、Gaussian仿射关系、Hermiticity、sandwich正定性与非法链接拒绝；Pion失败块 helper 定向测试为 **14 passed**。contract/响应图报告含新源码 hash。此证据只覆盖声明的周期/幺正算符与小型 CPU fixture，不代表物理最强基线、生产 objective、GPU或blind comparison。用户要求维持 `NOT_READY/UNCERTIFIED` 与封存；D11数学/接口审阅及 C1/C2 shared objective/IDs/双预算/失败分母的跨文档一致性检查已完成，未发现冲突；没有可以替代 D04/D06 研究决定或独立物理reference的其他 CPU 测试。三份 task TODO 均继续保留。

## 12. 2026-11-22 当前全仓 CPU/GPU-free 回归

在当前工作树（含 Optimize matrix-free Gaussian-sandwich增量）重新运行：`PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest -q -p no:cacheprovider -rs`，结果 **418 passed, 1 skipped, 1 warning in 28.81s**。唯一 skip 为 `tests/test_wilson_stout.py::test_stout_parity` 无法导入 CuPy；唯一 warning 是 `tests/test_wilson_loop.py::test_projection_domain_support_and_rejection` 中 rejection fixture 的 `RuntimeWarning: invalid value encountered in multiply`。命令退出码为0。该 suite 提供当前源码的 CPU regression evidence；不覆盖 GPU/QUDA、生产 physics、reference validity 或封存 split。三项工作仍分别有未通过的物理/统计门，所以本次测试不改变 `NOT_READY/UNCERTIFIED`、`physical_score=null` 或保留全部 TODO 的决定。

## 13. 2026-11-22 三项候选协议交接

- **Optimize**：`protocol_decision_review_20261121.md` 记录 D04/D06 和 D01–D19 的选项；`protocol_freeze_draft.md` §7 增加用户指定 F=2 下三臂共同目标/IDs/双预算文字流程与受约束 degree-4 Chebyshev候选，并将 C1 默认解释为同一 W/v/c 函数族下的 learned optimizer vs SLSQP，避免把模型变化误归因于求解器。该候选的14项 focused tests通过，不意味着函数族获批或物理比较完成。
- **Pion**：`bounded_score_design_review_20261121.md` 更正为“bounded block-MSE已接受作探索estimand”，并补物理单位/范围、clipping、独立evaluation-block、anchor common-bias、失败与两条测量流 identity gate 的候选矩阵和文字数据流。没有补物理值、未做新MC；当前D reference/M2状态和score不变。
- **Wilson**：`estimand_decision_review.md` §9 为 finite-$T$ Creutz 与 ground-state force 分别列比较对象、重采样、正值失败、多重性、谱/热污染路径和停止状态；继续共享draw的协方差描述，不把两个lane算作独立验证。

这三份候选包均为方案审阅材料，未生成 production protocol、访问受限 split 或触发测量。下一步只在保留数据封存的前提下继续数学/接口审阅和选项影响分析；任何物理阈值、reference、范围、block/anchor偏差、统计family或系统误差预算仍由研究者在适当阶段决定。三份 task TODO 均未达到删除条件。
