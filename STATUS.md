# 项目状态（2026-11-21 Asia/Shanghai；UTC 快照 2026-11-20，独立 HMC 诊断完成）

## 当前结论

| 工作包 | 当前证据 | 结论边界 |
| --- | --- | --- |
| `pion_projection` | amendment02/03 来源复核、family-wise v1–v3、χ² subgate、协方差 factorization、production-fit bootstrap、GEVP N=400/cell、C2/C3扩样及 robust-score 图文均已完成；measurement plan 的 READY/续跑及 anchor-report 身份闭环已修复 | HMC job 128526595 (D) 与独立 anchor job 128528670 (E) 均完成并通过 raw payload hash 核验。D IDs 0–99 correlator development 已完成且 identity/residual 通过，但 frozen single-cosh reference gate **FAIL**；两态与有效质量图文只作开发诊断。旧 S16T16 source–sink ensemble-mean 矩阵的 anti-Hermitian 差为 29–32%，超过预设5%门；development/已观察 validation 曲线与 t=5 元素热图已补，validation 不是 blind。E0–59 anchor、D validation和D140–199 holdout均未打开，physical score仍null。C2多数原始单元N约6–8、C3原网格约30/cell；选定场景N=400/cell只提高对应synthetic MC精度。 |
| `wilson_loop` | P0b、F4/P4、D/E HMC质量诊断、100/100 Wilson development测量及development-only A/B/C / APE-stout风险成本图文已完成 | job 128540026 `COMPLETED 0:0`，elapsed 12:15:58；终态输入/逐行identity和manifest join通过。参考提案仍不一致：A/B max-z=2.096通过候选阈值，C centered/uncentered joint q95=2.741/4.084拒绝；reference未冻结、无family-wise calibration，production_score=null。D0–99另完成 20 blocks / 5000 shared draws 的 T-window slope force 与 Creutz force 配对探索，5000/5000 draws有效；identity大R force 仍有明显T-window/T敏感性，不能认证finite-T或ground-state。APE/stout风险比约4.84–12.11仍只是同一开发样本条件诊断；Stout约慢两个数量级。较早61行aggregate hash异常仍未解。D100–119 gap、D120–139未解锁、D140–199 sealed；真实物理配对和physical_score尚未形成。 |
| `optimize_gaussian` | A–D CPU切片、B噪声/reference stress、C独立N=100 follow-up、learned-initializer toys已完成；v9 fixed-random-W系数重训与已观察 test IDs70–99有记录；worker RunSpec、Optimize-specific builder CPU preflight 和 solver-contract 到 `train.optimize` CPU 接线已完成 | Pion D0–99 point propagators 与 generation-bound receipt 已经由 Optimize adapter 在真实远端缓存上 **100/100验证**；schema v2 builder 绑定 protocol/source/input/split/environment/output artifacts 并通过 no-launch preflight。新增定向接线验证涵盖 explicit-policy preflight、final-point reevaluation、KKT预算计数及拒绝后停止 learned candidate dev-val/test评分，四模块 **87 passed**，文字诊断见[报告](results/optimize_gaussian/solver_contract_train_integration_cpu_v1/README.md)。仍未生成真实 production RunSpec、冻结生产阈值/统计策略或启动训练。训练/物理计分、生产P3 2×2或blind comparison仍未完成。D140–199与Pion/Wilson共用且保持封存，三方必须先冻结候选/score/source。v9原始propagator bytes/完整运行receipt仍缺；固定随机$W$不等于trainable-$W$。 |

## 最新增量（2026-11-21）

- Pion 新增[有界 block-risk 与独立 anchor 理论设计稿](tasks/pion_projection/bounded_score_design_review_20261121.md)：给出全族 Hoeffding 下界、anchor 系统误差扣减、样本量成本表和文字决策流。它是 `THEORY / DESIGN_ONLY`，改变原 ensemble-risk estimand；独立性、物理范围与可信 anchor 均未建立，不能据此生成分数或启动校准。
- Wilson 新增[同 draw 窗口漂移 contrast](tasks/wilson_loop/force_window_contrast_20261121_v1/README.md)及[图](tasks/wilson_loop/force_window_contrast_20261121_v1/late_minus_early.png)。复用的5000×20 bootstrap indices、原分析协议和window rows均逐项核对一致；pointwise窗口差仍不能识别窗口共同偏差，也不认证基态/物理分数。
- Optimize 新增[算符级 trainable-W CPU 对照](tasks/optimize_gaussian/trainable_w_operator_cpu_20261121_final/README.md)：heat-kernel目标上的36个受限优化器运行及degree-4 Chebyshev比较，验证目标/实现一致并给出条件性负诊断。目标有意属于谱函数，3个panel不足以作总体推断；它未接入生产训练，也不回答物理风险或生产SLSQP比较。

## 验证

- 最近已记录的全套 CPU / GPU-free 测试为 **274 passed, 1 skipped, 1 warning**；唯一跳过是缺少 CuPy 的 parity test，保留1条已知 Wilson projection rejection `RuntimeWarning`。这不是本轮重新运行的结果。
- 本轮只运行 Optimize solver-contract、RunSpec builder、training protocol 与训练接口四个定向模块：**87 passed**。调用流程、拒绝原因与范围边界见[solver接线 CPU 报告](results/optimize_gaussian/solver_contract_train_integration_cpu_v1/README.md)；未运行全仓测试，也未使用生产输入、GPU 或 QUDA。
- 新增 trainable-W 原型测试 **9 passed**，feature/kernel 聚焦测试 **7 passed, 48 deselected**；算符级诊断另在运行时对18个目标、独立 fit/heldout links 的解析梯度和压缩/直接矩阵 loss 进行断言。该36-run诊断不是pytest统计校准。Wilson force-window contrast 对应的原 force focused tests **4 passed**、脚本解析/输入自检 **5项通过**。这些更新均未重跑全仓 suite。
- 增加父级失败诊断哈希后，六个 Optimize solver/train/worker/hard-timeout 模块合并复跑 **113 passed**。`optimizer_contract_rejection.json` 通过 RunSpec optional diagnostic output 独立回链；nonzero child 仍是 `worker_failed`，其诊断 hash 不会被记为成功训练 artifact。没有在真实 `train.main` 子进程、GPU 或 QUDA 上执行此闭环。
- 本轮另运行 Optimize hard-timeout supervisor focused CPU suite：**9 passed**，文本诊断见 [v2 报告](results/optimize_gaussian/hard_timeout_cpu_v2/README.md)；这组不计入274项全仓 suite。它只覆盖合成进程控制，不涉及 train.optimize、GPU/MPI 或物理 score。
- 本轮新增 Optimize frozen worker RunSpec 与 hard-timeout focused CPU 验证：**17 passed**，图文见 [worker RunSpec v3 报告](results/optimize_gaussian/worker_runspec_cpu_v3/README.md)。这覆盖协议/源码/输入hash、split ID、启动前拒绝、child receipt和显式环境隔离；不证明真实训练入口或GPU/QUDA可安全中断，也未重跑全仓测试。
- 本轮 Wilson 定向回归验证 **55 passed, 1 skipped**；CuPy backend parity test 因本机无可用 CuPy/CUDA runtime 而跳过，保留1条已知 projection-domain rejection warning。没有重跑全套测试。
- 本地桌面仍无GPU/MPI栈，但 Kunshan DCU 已完成 jobs 128526595 (D) 与128528670 (E)。receipt、逐轨迹日志、manifest与图文摘要已复制到 `results/wilson_loop/hmc_{production_20261120,anchor_20261121}/`；未复制raw gauge files。新的HMC receipt不代表Pion测量、Wilson-loop physical result或trainable-$W$训练。
- 本轮只读续查扫描了当前 Git 的全部1,077个 blob，未找到 amendment02 旧 synthetic_adapter.py SHA；常见 raw gauge 后缀在工作区未发现。另通过只读 Kunshan alias 对远端18GB/500个 NERSC文件做完整哈希，结果均匹配各自manifest；本机仍无GPU/MPI栈，不能执行新物理测量。
- GEVP200 provenance-field crosswalk 与 [live byte audit](results/kunshan_logs/live_archive_audit_v1/README.md)均已验证；原500个文件的重复campaign payload边界仍适用。新增HMC D/E链另有独立receipt与raw-file hash核验，其HMC质量图文和跨链block sensitivity结果见各自结果目录；两条链都只作质量诊断，不认证平衡或物理分数。
- 任务级详细覆盖、每项图表/数值证据与下一步开工说明见 [todo 覆盖总表](doc/todo_coverage.md) 和三份 task todo。

## 重要负结果

- Wilson 两态例中 spread/$V$ gate 通过但 bias/SE 达 32.5：当前 gate 不能排除共同偏差。
- Pion 原 χ² subgate smoke 的 0/8 CP 区间 [0,0.36942] 过宽；新 1000/cell 子门 MC 在6/12/24 blocks下 null rejection 为15.1%/5.4%/1.8%，说明当前拟合子门对block配置敏感。它不是完整证书的校准；纯E1 world在24 blocks仍96.7%通过拟合门，状态识别仍需独立物理证据。
- Pion family-wise v1 的 0/2500 是 far-null 控制，不是边界校准；v2/v3 才测试 `log(1.05)` 边界。v3 显示候选相关性升高时 pointwise FWER 可达 130/2500=5.20%；Holm/Bonferroni、max-t、Huber/trimmed 首轮表现已比较，但校正有功效代价且 robust estimator 没有一致优势。wrong-state 与 common-bias 下所有方法都 2500/2500 误认证，独立物理 anchor 仍是关键缺口。
- Pion 新增的 studentized block sign-flip 在独立、臂标签可交换的 paired-block sharp null 下有理论依据；本次 synthetic size 2.8–6.0%，但 familywise CP95 较宽、已知改善功效 10.0%/21.0%，没有胜过 paired-t 的明确证据。common-truth-shift 与其它 null 结果只说明相对 arm-effect，不能检测共同状态/模型偏差。
- Optimize 类 B $\epsilon>0$ oracle 零误差：只证明该目标在包含 $BHB$ 的特征族里可表示，不证明学习优势。
- Optimize 包 B 开发期间曾覆盖 `unified_v1/`；仓库没有旧 fold 的 git 版本。事件与限制保留在 package B README，旧数值只作历史记录。

## 下一步

1. Pion：不要重复固定 generator 或通过调λ追求5% size。synthetic common-block bootstrap 下 percentile/basic/bootstrap-normal 在等噪声 null 均有16.3–19.3%假认证；independent-arm indices 的低认证率伴随低功效。新增的 paired-block sign-flip 在声明 sharp exchangeable null 下与名义5%相容，但区间宽、功效10.0%/21.0%，未显示相对 paired-t 的清楚优势，也不处理弱零假设或共同模型偏差。D0–99真实 correlator development已完成但single-cosh reference gate FAIL；两态和有效质量图文均为同一样本诊断。按stop rule不测E anchor、不测D validation、不打开shared holdout；若希望恢复anchor流程，先冻结一套独立reference确认方案与stop rule。C2 family 只有183/400通过候选模型 gates、better power 20/183，两态边界造成210/400弃权；全为 synthetic 子门结果。
2. Wilson：CPU synthetic controls、D/E HMC receipt与质量诊断、单配置GPU smoke、D0–99 full development job及reference/A-B-C和APE/stout配对风险—成本图文均已完成。job 128540026 `COMPLETED 0:0`、elapsed 12:15:58；三件套100/100、manifest identity/trajectory join通过，未重读raw gauge。A/B proposal pass与C joint-max reject不一致，说明候选reference门尚未冻结且不能认证；APE/stout ratios也只是开发风险结果，非物理优势。Stout每配置kernel+loop约87–175s，APE约0.75–1.27s。下一步先提出能识别共同偏差并校准family-wise误差的reference方案，附公式、模拟、阈值/弃权规则和图文；研究者冻结并明确授权前不读D120–139、gap或shared holdout。较早61行aggregate hash异常保留未解释；详见 [Wilson TODO](tasks/wilson_loop/todo.md)。
3. Optimize：C 的N=100 CPU follow-up已完成但仍是合成方法诊断；v9 的固定随机 $W$ GPU 系数重训与已观察 test 已有记录。D0–99的真实point propagator缓存和Pion receipt已通过Optimize validator集成100/100；无需重做这些inversion。solver-contract 已接入显式训练协议、`train.optimize` 和 RunSpec CPU preflight；87项定向测试通过并输出文本诊断。核心未决问题是研究者冻结生产 solver threshold/计时口径/统计决策、生成真实 Optimize-specific RunSpec与确认可用reference，再做trainable-$W$/learned initializer、生产P3 2×2以及与SLSQP/强谱基的配对比较。由于Pion reference gate失败，基于该reference的风险只能标为`diagnostic_only`；新blind IDs必须在三任务锁定protocol/candidates/source之后共同解盲，提交paired CI、成本/收敛/失败图文。
