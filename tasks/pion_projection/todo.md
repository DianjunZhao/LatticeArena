# pion_projection：CPU 验收结论与下一阶段

### 2026-11-22 完整性复核：保留 TODO

**最新边界确认（2026-11-22）：**用户明确要求维持 `NOT_READY/UNCERTIFIED` 与数据封存状态；此前已接受 bounded block-MSE 作为不同于 ensemble-risk 的 estimand。不要再询问是否接受该 estimand，也不解封 E anchor、D validation/gap 或 shared holdout，不启动 GPU/QUDA，不把条件性 synthetic 校准升级为物理 score。下一位 agent 只推进可在封存下完成的 CPU/文档工作；不能据示例代填 m*、单位/范围、clipping、anchor 共偏差界或生产失败策略。交付须有图或可复查的文字流程、明确假设、planned/valid/failed/abstained 分母和停止规则。single-cosh `FAIL`、M2 `ABSTAIN/NOT_READY` 与 `physical_score=null` 保持不变。

封存下的候选合同矩阵、失败块两种estimand处理、条件性校准和文字决策流已补到[bounded-score 设计稿](bounded_score_design_review_20261121.md)；该稿明确质量单位/范围/clipping、block来源、anchor共同偏差、失败分母和停止条件的候选项，不代填物理值。本TODO继续负责物理数据/身份 gate 与停止条件。

**2026-11-22 receipt/trajectory/source 身份审计已完成：**见[独立块与 anchor 证据表及文字数据流](../../results/pion_projection/independent_block_anchor_receipt_audit_20261122/README.md)。D0–99 有100条配置记录，trajectory ID从401到896、间距严格为5；每5条配置组成一个可复现的block，共20块，但当前证据没有 score-specific autocorrelation bound，故不证明块独立。12个spin-color RHS属于同一配置观测；1000次bootstrap只是重采样20块。E0–59仅是计划中的独立anchor，当前审计没有可用的E correlator receipt，`A/B_A`仍未知。旧 `s16t16_ms` 是不同的v1 source–sink身份且无trajectory/generation/protocol receipt字段；其 observed matrix anti-Hermitian gate失败。提议的matched-v2只有候选protocol fingerprint `f3150c45…`，无绑定测量generation。审计没有找到能改变 `ABSTAIN/NOT_READY` 的现成CPU证据。不要重跑 bounded-score Monte Carlo 或重写§9矩阵；继续保持数据封存、`physical_score=null` 与本 TODO。

### 2026-11-22 失败评价块的保守处理（解析 CPU，不是物理校准）

新[图文诊断与逐项输出](../../results/pion_projection/bounded_score_failure_policy_20261122_v2/README.md)把此前未定义的失败块口径分成两条：**任一planned block失败就整项ABSTAIN**；或将失败块的paired improvement按最坏有界值`−R²`编码并保留planned分母。第二条对“失败块上仍存在有界反事实估计”的目标给出保守下界；若优化器不收敛意味着估计量本身不存在，它改为failure-augmented operational estimand，不能称原始物理质量MSE。输入身份、协议/运行级故障始终整项ABSTAIN，禁止逐块imputation。

最坏编码下`L/R²=(1−φ) μ_valid−φ−sqrt(2 log(F/α_s)/N)−2B/R`，其中`φ=f/N`。图中仅作代数示例`F=2, α_s=0.05, B/R=0, δ*/R²=0`：N=12时要求成功块均值分别为φ=0/0.05/0.10/0.20下的`0.784/0.878/0.982/1.230`倍R²；最后一项超过最大可能`R²`，即使成功块达到上界也不能得到正下界。连续φ轴是敏感度示意，小N的可实现比例只能取`f/N`。这些数不是物理效应阈值或生产规则。

独立纯函数、输入拒绝与单调性用例 `tests/test_pion_failure_aware_bounded_score.py` **14 passed**；只运行解析 helper 和画图脚本，不读correlator、不做Monte Carlo/GPU/QUDA，也不改reference、E、validation或holdout。该分析补齐“失败块怎么处理”的技术选项，但选择生产政策仍需研究者审阅目标估计量、物理范围和block身份。因此维持 `NOT_READY/UNCERTIFIED`、`physical_score=null` 与数据封存，本 TODO 保留。

D0–99 correlator 的 identity/residual 与 development-only 诊断已有证据，但冻结的 single-cosh reference gate **FAIL**，拟议 M2 方案仍为 `ABSTAIN/NOT_READY`；E anchor、D validation、shared holdout和`physical_score`均未开启。因此整项研究没有完成，不能删除本文件。停止原因目前首先是 reference/model identifiability 与确认方案未通过审阅，不只是缺 GPU；后续真实测量还需要冻结一个物理上可辩护的新方案、source/input identity、stop rule和用户授权。不要以调阈值让D通过，也不要先启动新GPU测量。

C2/C3 小样本警示对原始网格成立，但应按每个模拟的estimand、DGP和有效/弃权分母分别报告：后续已扩大的若干预选 cell 不代表完整网格或拟议 N=60/12-block M2确认流程已校准。已有稳健分数比较显示 size/power/abstention 的取舍，且 wrong-state/common-bias 下的方法仍可共同误认证；不得把synthetic robust-score当成reference gate替代品。具体MC区间和后续唯一可推进的方案审阅步骤见§4及§6。

**bounded block-MSE 的新 estimand 已由用户接受，候选校准方案现已整理**，见[图文结果](../../results/pion_projection/bounded_score_calibration_20261121_v1/README.md)、[失败块敏感度](../../results/pion_projection/bounded_score_failure_policy_20261122_v2/README.md)与[候选合同矩阵](bounded_score_design_review_20261121.md#2026-11-22-封存状态下的候选合同矩阵不冻结)。168 cells × 3000 outer datasets 的条件校准为504000/504000 valid、0 failed；它只覆盖声明假设下的有限组合成DGP，不证明物理范围、块独立或anchor覆盖。不要重写矩阵或扩同一MC。receipt/trajectory/source身份审计已完成；其结论是当前没有能改变`ABSTAIN/NOT_READY`的独立块界或anchor bias证据。m*、单位和物理范围/clipping均保持未冻结，不读受限split，不启动GPU。

当前完整 CPU/GPU-free suite（2026-11-22，含 Optimize matrix-free Gaussian-sandwich增量）在现有工作树为 **418 passed, 1 skipped, 1 warning**；唯一 skip 是缺少 CuPy 的 stout parity test，warning 是 Wilson projection rejection 的既有 `RuntimeWarning`。这只是软件与 CPU fixture 的回归证据，不改变 Pion reference FAIL、M2 `ABSTAIN/NOT_READY` 或 `physical_score=null`。2026-11-21 的385 passed与较早的413/415/417均为历史快照。

**本次裁决与下一工作边界：**新 E anchor、D validation 和 shared-holdout 测量确实未运行；但“所有未做项都只差 GPU/授权”不准确。现有 D0–99 correlator 已测且 reference gate 失败，不能重跑来争取通过；M2 可辨识性、独立块身份、anchor共同偏差和source–sink协议仍是方案审查问题。C2/C3原始小网格与后来各预选N=400/402扩展不得混池。候选决策流、校准矩阵和receipt/trajectory/source身份审计均已有文字图表。当前没有能改变`ABSTAIN/NOT_READY`的现成证据；后续需要研究者给出并审阅物理量定义、块自相关规则和anchor共同偏差控制，之后才可冻结确认性方案。任何新测量仍须遵循冻结的planned/valid/failed/abstained分母、身份图和物理边界。

**已完成的方法分支：source–sink GEVP 矩阵约定审计（不要重跑旧矩阵）。** 一手方法论文指出，在含 $N$ 个插值算符的相关矩阵 GEVP 中，适当的大时间极限下激发态修正按能隙指数衰减；增加独立算符数可改变相关能隙，但这不保证有限样本、病态矩阵或错误矩阵身份下自动得到可靠基态（[Blossier et al., arXiv:0902.1265](https://arxiv.org/abs/0902.1265)）。只读核验显示源–汇数组已经存在：`s16t16_ms/development.npz` 为 IDs 0–59、shape `(60,3,8,16)`，`s16t16_ms/validation.npz` 为 IDs 70–99、shape `(30,3,8,16)`；source labels 是 point/H4/H16，protocol hash 与 provenance 相符。按 H0/H4/H16 取同名 source/sink 子矩阵，原 ensemble-mean anti-Hermitian max-norm 相对差在 development 的 $t=3,4,5,6$ 分别为 **0.294、0.301、0.303、0.304**，validation 分别为 **0.299、0.309、0.316、0.316**；5% 身份门失败。原有[ensemble-mean 图文诊断](../../results/pion_projection/source_sink_hermiticity_diagnostic_20261121_v1/README.md)已由新的[逐配置与 block-bootstrap 诊断](../../results/pion_projection/source_sink_hermiticity_per_config_20261121_v1/README.md)补充：development IDs 0–59 与已观察 validation IDs 70–99 的单配置比值均集中在约0.3，所有8个长度5 block-bootstrap的95%区间下限均高于0.287；对长度1/2/5/10的敏感性图也已提供。逐配置比值只是描述量，5%门仍按 ensemble-mean matrix 判定；validation不是blind，长度10的validation仅有3块，相关区间低分辨率。sink–sink Gram 与 source–sink 矩阵差约30%，2×2 / 3×3 Gram GEVP没有时间平台；旧 GEVP 仍只可作探索性诊断。当前 Pion `MeasurementBundle` 也声明 `cross_matrix=false`，不会自动认证这些外部归档矩阵。矩阵 identity 的公式、原始值与图文入口见 [`gram_operator_identity.md`](../../doc/gram_operator_identity.md) 和 [`gram_identity_check.json`](../../results/pion_projection/gram_identity_check.json)。

**旧 source–sink arrays 的不确定度诊断已完成（仅已有 observed IDs）**：新报告保存逐配置CSV，并对 ensemble-mean 矩阵指标使用 saved-configuration 顺序下的非重叠 block bootstrap，length=1/2/5/10、每格5000 draws。8个 length=5 的95%区间下限为0.2879–0.2972，均远高于0.05；逐配置比值范围在development为0.2277–0.3720、observed validation为0.2396–0.4119。图文说明该误差敏感性描述不是物理覆盖校准，且block未绑定HMC轨迹间距。`tests/test_pion_source_sink_hermiticity_diagnostic.py` 与新增 uncertainty tests 合计 **14 passed**。不要重复旧数组统计；新 generation 的块级图仍须待获授权 GPU preflight 后生成。

当前 API 核对已发现具体参数不一致。接手者不应重新跑旧 GEVP。旧 provenance 没有远端 PyQUDA 版本和源码 hash；只做一次有界的外部 receipt/log 查找，若不可恢复，就把历史根因保留为“强候选、未证实唯一归因”，不重复本地 Git 搜索。新的 CPU 路径已实现：source propagator 的12个 spin/color 分量逐一通过与 sink 相同的低层 `wuppertalSmear` callable，使用同一个 `protocol.alpha`；rho→alpha 只用于 preflight 参数一致性检查。16 项 focused test 以 fake callable 验证参数流，尚未验证 QUDA 数值。旧数据的逐配置与块不确定度已补，不要重复该诊断。下一步先冻结版本化 protocol/generation/source/software hashes，并提交 alpha/steps/rho 参数表及数据流文字说明供研究者审阅；获授权后才做小规模 GPU preflight，检查新 generation 原始 $C_{ij}(t)$ 的5%身份门，再考虑完整新 development 测量。不得把旧 `s16t16_ms` 数组用 `(C+C†)/2`、对角缩放或重新标记为 PASS。若新矩阵通过身份门，才进行按 rank/算符子集分面的有效能量—时间图、广义特征值/奇异值与条件数图、mode-tracking/边界/失败计数，并附 block 重采样和有限时间可辨识性的文字解释；此前不得读取 E anchor、D validation 新数据或 shared holdout。**新 generation 仍缺的图文证据**是逐配置/连续块间 anti-Hermitian 分布与区间、source-alpha 对照表、5%门失败/通过数；这些图表和失败/弃权解释必须随获授权的小规模 preflight 一并交付。

**2026-11-21 source-smearing 参数只读审计（CPU，解释为候选原因而非已证实历史归因）：** 当前本地 [PyQUDA source.py](/Users/zhaodianjun/PyQUDA/pyquda_utils/source.py:402) 的 `source.gaussian12` 先按 `alpha=1/(4*n_steps/rho**2-6)` 计算参数，再把该值直接传给 `dirac.wuppertalSmear`；[底层 wrapper](/Users/zhaodianjun/PyQUDA/pyquda_core/pyquda/dirac/gauge.py:139) 原样传入 `performWuppertalnStep`。旧 protocol 的 H4/H16 `rho` 对应 source alpha 都是 **0.5454545455**，不是 sink 的 **0.2**。rho 在当前公式下改为约 **1.206045/2.412091** 可匹配 alpha=0.2。新代码现对 source 的12列直接调用与 sink 相同的低层 `wuppertalSmear(..., protocol.alpha)`；fake-callable 测试只验证传参，不证明 GPU/QUDA 数值。参数不一致是现存 Hermiticity 失败的可检验候选原因，但旧 receipt 没有 PyQUDA/source.py hash，不能断言是历史远端唯一原因。旧 correlator 必须原样保留。版本化候选 [`protocol_multisource_matched_v2.json`](protocol_multisource_matched_v2.json)、source/sink alpha 表和数据流已在 CPU 报告中列出；接手者先审阅其 ID、hash、stop rule 与 no-clobber 输出路径，再决定是否提交授权 GPU preflight。获授权后交 anti-Hermitian 随时间图、逐配置/连续块区间图、source-alpha 对照表、5% 门通过/失败/弃权计数和解释文字。不得把静态/fake-callable 验证说成测量修复，也不得把 GPU preflight 当作 reference gate 通过。

**2026-11-21 matched-smearing CPU contract、source identity 与 no-clobber preflight 已加入（无测量）：** [`smearing_contract.py`](smearing_contract.py) 复现本地 `gaussian12` 的 rho→alpha 映射；[`measure_multisource.py`](measure_multisource.py) 现在默认读取专用 `protocol_multisource.json`（修复原先继承单源 `protocol.json` 的入口错误），支持 `--protocol PATH` 指定候选协议，并在 CuPy/MPI/PyQUDA imports、输出目录创建及 `core.init` 前检查 source/sink alpha；`--preflight-only` 可输出 split、IDs、hash、generation 和 alpha 表后退出，不导入 GPU 栈或创建输出。匹配后，source propagator 的12个spin/color分量直接调用与sink相同的 `wuppertalSmear` callable 和 `p['alpha']`。measurement generation 绑定原始 protocol bytes SHA、canonical protocol hash、split、配置 ID 顺序及 measurement/contract 源码 hashes，NPZ 与 provenance 均保存 generation；provenance 另记 alpha 对照表。旧 `protocol_multisource.json` 的 H4/H16 均被拒绝；新版本化候选 `protocol_multisource_matched_v2.json` 的代数匹配参数通过 CPU preflight，development IDs 0–1 的 CLI 状态为 `cpu_preflight_ready_not_authorized`，指定输出目录未创建。focused smearing tests **19 passed**，两个 Hermiticity 模块 **14 passed**，combined **33 passed**；包括12列匹配参数的fake-callable检查。图文、代码 hash 和执行流程见[CPU 报告](../../results/pion_projection/matched_smearing_contract_cpu_v1/README.md)。这关闭的是未来启动前阻止错配和目录覆盖的接口缺口，不修改旧 protocol/arrays，也不证明历史远端版本、QUDA kernel 数值、反Hermitian门通过或唯一物理归因。接手者先审阅候选协议的 ID/hash、alpha/steps/rho 表、stop rule 和新输出路径；只有方案审阅及 GPU 授权通过后，才运行 development matched-kernel preflight，并提交逐配置/连续块区间图、anti-Hermitian 随时间图、5%门通过/失败/弃权数和解释文字。即使identity gate通过，reference gate仍须独立通过；E anchor、new D validation、shared holdout和physical score继续关闭。

### 2026-11-21 稳健分数在 reference 失败时 fail closed（CPU复核）

当前代码已将“reference 先通过、分数才有资格被解释”落实为失败闭锁：[`joint.py`](joint.py) 在 `reference_passed=false` 时把 certificate 置为 `abstain`、记录 `reference_gate_failed` 并将所有候选 `certified=false`；稳健分支仍明确 `status=diagnostic_only`、`physical_score=null`。[`experiment.py`](experiment.py) 将失败参考写为 `unscored_reference_failed`，[`candidate.py`](candidate.py) 的 candidate score 在该条件下为 `null`。本轮针对 robust pairing、失败 gate abstain、失败 anchor score null 的三项用例 **3 passed**；随后连同 Optimize 两个执行器测试文件重跑，`tests/test_pion_projection.py` 全文件及 Optimize 两文件共 **70 passed**。整文件命令为 `PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest -q -p no:cacheprovider tests/test_optimize_hard_timeout.py tests/test_optimize_worker_runspec.py tests/test_pion_projection.py`。

这验证的是软件状态传播，不是 reference 物理有效性。更换 paired lower bound、studentized test、max-t 或抗离群估计量，都不能从同一错误参考中恢复基态真值；已完成的 synthetic size/power 实验也指出 wrong-state/common-bias 可共同误认证。故当前建议仍是：robust score 作为有效 reference 条件下的候选比较器，并在 reference 未通过时弃权；任何 physical score 仍需一个预先冻结、独立可辩护的 reference/anchor。不要重跑已有 score grid 来寻求 D 通过。

### 2026-11-20 可恢复的 multi-start bootstrap journal 已完成

新增 [`bootstrap_checkpoint.py`](bootstrap_checkpoint.py) 将 `iter_bootstrap_multistart` 接入可恢复 JSONL journal：manifest 绑定拟合 block 数据 hash/shape、通道归一化 scales、重采样矩阵、块内 configuration IDs、起点、固定 precision、拟合配置、优化器控制、执行器源码和 Python/NumPy/SciPy/platform；每个 draw 的完整 multi-start 结果经哈希链逐行落盘并 `fsync`。显式 `resume=True` 时先取得单写锁、比对 manifest、验证每行 ID 和哈希；只丢弃未换行的尾部半行，完整行损坏或身份不符即停止。完成全部计划 draw 后原子发布 `status.json`，新目录默认 no-clobber。流程图和边界见[CPU 实现报告](bootstrap_checkpoint_report.md)。

`tests/test_pion_bootstrap_checkpoint.py` 覆盖单样本提交后模拟 solver 中断、保留已提交行并从下一 draw 恢复、残缺末行修复、manifest 错配、完整行损坏、乱序 draw 拒绝及 strict-JSON 行为（5 个 checkpoint 用例）；与稳定两态执行器测试合计 **16 passed**。这只是 CPU 落盘/恢复验证，不是 M2 calibration、physics gate 或全局最优证明；中断中的当前 draw 会从冻结起点重跑。

### 2026-11-20 D 链首轮物理开发测量：reference gate 失败，保留 TODO

Kunshan job **128538946** 已完成 S16T16D development IDs 0–99 的 GPU correlator 测量，100/100 trajectory join 与 raw gauge SHA 匹配；最大 12-RHS inversion residual 为 `9.99751e-11`，测量数组 SHA-256 为 `8a78947c…a7fe3`。原测量源码与 frozen generation 保持不变。冻结分析曾因 N=100 不可被 block length 3 整除而中断；独立的 [`experiment_analysis_amendment_20261120.py`](experiment_analysis_amendment_20261120.py) 明确略过该不可整除长度，使用完整分割的 1/2/4/5/10/20/25 配置块，并记录测量、计划、源码和输出 hashes。分析图文见[开发报告](../../results/pion_projection/s16t16d_closure_20261120/README.md)与[reference-window / block-length 图](../../results/pion_projection/s16t16d_closure_20261120/development_diagnostics.png)。

**Reference gate 明确 FAIL**：nominal single-cosh mass `1.096183`，bootstrap SE `0.003046`，近似拟合优度 `p=1.081e-15`；拟合窗口 `[4,5,6,7,8]` 和 `[6,7,8]` 相对 nominal 的 paired shifts 分别为 20.41σ 与 15.78σ。reflection-odd 最大 z=1.024（阈值4），但不能抵消参考模型失配。按冻结 stop rule，不测独立 E IDs 0–59，不测 D validation，也不打开 shared holdout；`physical_score=null`。注意旧写法 `1.0961829(30)` 会把误差读成约 `3e-6`，与实际 SE 相差约千倍，故本文件统一列出中心值和 SE。

随后只在同一 D development 样本上做了明确标作 exploratory 的两态模型诊断：[报告](../../results/pion_projection/s16t16d_closure_20261120/two_state_diagnostic.md)与[单态/两态窗口图](../../results/pion_projection/s16t16d_closure_20261120/two_state_diagnostic.png)。两态近似 p 值为 0.90–0.997，ground-state mass 跨窗口约 1.040–1.063，配对漂移 0.86σ/1.92σ；但 `[6,7,8]` 的 excited-state bootstrap 碰到 mass 上界，条件数约 `3e5`。因此它提示单态可能遗漏时间曲率，却没有稳定识别第二态；原冻结 gate 仍 FAIL，不能据此测 E 或赋予 physical score。

新增的 [D-only gap profile 图文](../../results/pion_projection/two_state_gap_profile_d_20261120_v1/README.md)进一步发现：旧两态坐标搜索的每个窗口点都不是本次加密profile找到的最低目标点；目标降低0.0750/0.0821/0.0150，晚窗profile点条件数达 `1.46e6`。稳定复算旧点与旧cost仅有舍入差，说明差别来自搜索路径/盆地，而非cost公式漂移。profile扫描并不保证全局最小，目标差没有校准为显著性。旧bootstrap质量gap被 `m0<m1` 参数化约束为正，不能用其正百分位宣称第二态已分辨。详见[固定hash只读profile报告](../../results/pion_projection/two_state_gap_profile_d_20261120_v1/README.md)和脚本[`two_state_gap_profile.py`](two_state_gap_profile.py)；六项合成数值单测通过。该诊断强化“现方案 NOT_READY”，不改变single-cosh FAIL，也不打开E。

后续指定的确定性 multi-start 搜索也已完成，见[图文报告和逐起点记录](../../results/pion_projection/two_state_multistart_d_20261120_v1/README.md)。每个窗口29个起点，SLSQP正常终止24/29、有限终点29/29；每窗另有5个状态4（`Inequality constraints incompatible`），均保留为非成功而非改记通过。近似端点簇数为6/7/8，`gap=0`端点为5/6/6；最低目标相对旧坐标搜索分别改善0.07495/0.08212/0.01505，与profile找到的点一致。目标较低不证明全局收敛或两态物理可辨识，状态4结果仍要保留在planned-start分母。新的[多起点脚本](two_state_multistart_diagnostic.py)绑定与前述相同的D0–99固定来源hash；单/双态、零gap退化、上下质量边界与输入拒绝的synthetic test加上gap-profile测试共 **15 passed**。不得重跑同一D样本或把本诊断升格为reference gate。

development-only 的有效质量扫描现已补齐：[图文报告](../../results/pion_projection/s16t16d_closure_20261120/effective_mass_diagnostic.md)、[全时间图](../../results/pion_projection/s16t16d_closure_20261120/effective_mass_diagnostic.png)和[晚时间放大图](../../results/pion_projection/s16t16d_closure_20261120/effective_mass_late_time.png)由同一批100个 D 配置、20个长度5块和1000个 bootstrap draws 得到。可见质量从早时间向晚时间下降，且晚时间仍随 sink power 变化；这是 unresolved spectral curvature 的诊断线索，不是独立 plateau 验证，也不能推翻 frozen single-cosh gate。不要重复同一数据、同一判据的有效质量图。若继续诊断，须先指出新的结果会改变哪项决策，保留边界命中/失败数，并限定为 `diagnostic_only`。要恢复 anchor 流程，必须另建冻结的新方案、说明如何避免模型选择偏差并在测 E 前绑定源码和门槛；不得事后调阈值。IDs 140–199 仍由 Pion / Optimize / Wilson 共同封存。

新的[独立 reference 确认方案草案](reference_confirmation_plan_draft.md)保持 `DRAFT / NOT_APPROVED / NOT_FROZEN / NOT_RUN`，没有测量授权。草案拟将 M2 设为唯一确认模型、M1 仅作诊断，并列出完整样本/失败分母、协方差秩、来源 hash、停机与图文交付；但现有 D 两态晚窗条件数为 `299317`，草案明确**尚不具备 READY 资格**。公开 D0–99 的[既有两态数值可行性表](reference_confirmation_plan_draft.md#d-development-feasibility)已补齐：晚窗 full-sample boundary=false；固定hash链的只读审计脚本[`two_state_bound_count_audit.py`](two_state_bound_count_audit.py)复核有 **2/1000** 个既有 bootstrap resample 的激发态质量触及上界；focused test为 **10 passed**。拟议条件数上限为 `1e5`，因此 M2 全窗口门在现有 D 上为 **ABSTAIN**。`2/1000`是固定 D 样本的 resample 计数，不是物理事件率或 coverage；1000/1000 valid 与未校准的高 `p_approx` 也不能抵消边界和病态性。方案可行性审查已完成，裁决和后续CPU工作见[独立备忘录](../../results/pion_projection/reference_confirmation_plan_review_20261120_v1/README.md)：维持 ABSTAIN/NOT_READY；若需改模型/阈值，须说明物理依据、重新校准并送审，不得为了获得通过而调到 D 成功。不得据此测 E、D validation 或 shared holdout。

小样本提醒**部分正确，必须按模拟与 estimand 限定**：原始 C2 单元多为 6–8（部分端到端变体 8–15），原始 C3 多因素网格为 30 datasets/cell；但不是所有现有模拟都只有 8–30。已有 C2 χ² 子门 N=1000/cell、C2 `J=2/K=2` family N=400（183 valid、217 abstain、210/400 two-state boundary）、C3 多个预选场景 N=400/cell、full-gate 402/cell 与 family-wise 2500-trial 扩展。C2 N=400 是相关的 M2 family-subgate 证据，但不是拟议 E 确认方案的精确 N=60 / 12-block pipeline 校准；C3 扩展也未扩完整原始网格。各项图、CP/Monte Carlo 区间、失败/弃权分母见 §4 与对应报告。不得混池不同 DGP、分母或估计对象；是否再扩样只由预注册精度目标和决策需要决定，模拟精度不等于物理校准。

### 2026-11-20 测量前的本地续查：旧来源无法从当前 Git 恢复（状态见文首更新）

对 amendment02 preregistration 声明的 synthetic_adapter.py SHA-256（206cce77df19375fe79a02bc796806d572775c0f6a0e8df18b0b7ff0a9aa9f7d）扫描了当前 Git object database 全部 1,077 个 blob 内容，未发现匹配字节。当前仓库内没有可恢复的旧 adapter；这不排除外部备份或原运行者留档。下一个 agent 不必重复遍历本地 Git；只有原运行者提供对应旧源码与当次完整 run receipt 才能闭合 amendment02。若拿不到，继续标为 PARTIAL；amendment03 同 seed replay 或未来按新协议重采都属于独立证据，不会修复旧 run 的来源缺口。该次检查时桌面无 GPU/MPI 栈和本地 raw gauge 副本，Pion correlator 当时尚未运行；后续 D0–99 实测与当前 reference gate 见文首，E anchor 与 validation 仍未打开。旧 pilot 与 GEVP200 的重叠 payload 实际相同，因此旧数据不是独立 gauge chain；新 D/E HMC 链已可用，不需再申请一条新的 HMC chain。

审计基线：先前全套 CPU / GPU-free 测试为170 passed, 1 skipped, 1 warning；新增 Optimize 异常收据、Pion bound-count 和 Wilson gate diagnostic 后的历史快照为 **222 passed, 1 skipped, 1 warning**。再加入 D-only gap-profile 及 multi-start 后为 **243 passed, 1 skipped, 1 warning**；新增 Optimize solver-contract cases 后为 **254 passed, 1 skipped, 1 warning**；加入稳定两态振幅解、多起点回放和重采样收据后曾为 **265 passed, 1 skipped, 1 warning**；加入 Wilson 文件级 gate runner 后，最新全仓 suite 为 **274 passed, 1 skipped, 1 warning**（2026-11-20，`PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest -q -p no:cacheprovider -rs`）。Pion 测试文件合计 **96 passed**；稳定两态执行器回归 **11 passed**，checkpoint focused **5 passed**，两者合并 **16 passed**。唯一跳过项是本机缺少 CuPy 的 stout parity test；warning 是已知 Wilson projection rejection `RuntimeWarning`。身份、测量计划、GEVP 网格、robust-score、amendment02 402/cell full-gate、family-wise v1–v3、χ² subgate 1000/cell 扩样、paired shrinkage、factorized calibration、conditional bootstrap、C2 family N=400、C3 anchor-bias-only null N=400、common-block/lower-bound 对照及 studentized block-randomization extension 均有图文结果。
本文件继续保留：amendment02 严格 source provenance 仍为 `PARTIAL`，amendment03 是同 seed 重放；真实独立 E-chain anchor correlator 仍未测，D0–99 development 的 reference gate 已失败（见文首），不得重测或打开 validation；HMC 独立链本身不是 Pion correlator。v3只验证声明的synthetic covariance/score组合，不能替代物理anchor。

### 2026-11-20 新测量闭环修复与独立链状态

此前的 `measurement_plan.py` 没有 `READY` 状态，导致合法冻结计划也无法开跑；验证 split 的 preflight 把已有开发输出误判为冲突；`measure.py` 检查点没有写入 generation，且不能从前缀续跑。上述问题已修复：generation 绑定 frozen plan、协议、split、measure 与 kernel 源码；preflight 校验 trajectory manifest、split 前缀、correlator shape/finite/positive 条件、已完成配置的 gauge/propagator SHA 与 12-RHS residual，再在导入 CuPy/MPI/PyQUDA 前验证 submission；其他 split 的输出文件允许共存。独立 anchor report 还必须绑定 anchor/development/submission/plan/protocol/generation 全部 hash；anchor reference 拟合失败时也生成 `physical_score=null` 的失败图文并阻断 validation。相关针对性测试通过；本轮全套 CPU 测试为 **161 passed**。图文审计见[measurement-plan audit](../../results/pion_projection/measurement_plan_audit_v1/README.md)。

#### Measurement-plan audit 汇总字段修复（CPU）

复核发现 v1 的 [`measurement_plan_audit.json`](../../results/pion_projection/measurement_plan_audit_v1/measurement_plan_audit.json) 写出 `all_expected=false`：用例字段 `ok` 对 schema 测试表示“validator 是否接受”，却对 draft preflight 表示“预期拒绝是否发生”，聚合时把两种语义混在一起。保留 v1 原件，新增 [v2 图文矩阵](../../results/pion_projection/measurement_plan_audit_v2/README.md)，分列 `accepted`、`expected_acceptance` 与 `passed`；该次 D/E split fixture 的 6/6 个预期结果一致，新增回归为 **2 passed**。该审计只验证合成身份下的计划控制流；没有测量远端 manifest、propagator 或 GPU。之后的真实 D0–99 测量与失败门槛见文首，不能把 v2 CPU audit 说成该次测量的验证。

本轮冻结计划 amendment 见 [`protocol_fresh_20261120.json`](protocol_fresh_20261120.json) 与 [`measurement_plan_fresh_20261120.json`](measurement_plan_fresh_20261120.json)：development 为 `S16T16D` IDs 0–99，独立 anchor 为 `S16T16E` IDs 0–59，gap 为 D IDs 100–139，validation 为 D IDs 140–199。旧 HMC receipt 中曾提议 D IDs 100–119 作 anchor；该字段保留为历史，现由独立 E 链替代，不得改写旧 receipt。主链 job 128526595 已完成 1396 条轨迹、400 热化、996 生产、200 个保存配置；独立 anchor 链 job 128528670 已完成 896 条轨迹、400 热化、496 生产、100 个保存配置。两链的逐轨迹和 200/200、100/100 raw payload hashes 均已核验，诊断图文见[主链报告](../../results/wilson_loop/hmc_production_20261120/diagnostic/README.md)、[独立链报告](../../results/wilson_loop/hmc_anchor_20261121/diagnostic/README.md)及[跨链比较图文](../../results/wilson_loop/hmc_chain_comparison_20261120/README.md)。该次计划审计时 D development/anchor/validation 均 `NOT_RUN`；随后 D0–99 已测但 reference gate FAIL，E anchor 与 validation 仍 `NOT_RUN`，physical score 仍为 null，见文首。

D IDs 140–199 是 Pion validation、Optimize blind test 与 Wilson 配对可能共用的 60 个配置。Wilson 已冻结 [D 链 RunSpec](../wilson_loop/protocol_d_20261120.json)，其中明确保留这段 shared holdout、只预定 D0–99 development 与 D120–139 internal validation；这并未授权读取 holdout。三个任务的 protocol、candidate、score/endpoint、源码 hash 和分析方法仍必须在任何一个任务首次读这些 ID 前一起冻结；任务间重用是相关证据，不能计作多份独立验证。Pion validation 仍未打开。

**历史 GPU 试跑的边界**：本地有 2026-11-13 的 `s16t16-pilot-v1` 真实测量归档：开发 ID 0–59、未使用 gap 60–69、验证 ID 70–99。跨文件 audit 的90条测量记录与主 Kunshan manifest 字段90/90一致，最大残差为 $9.9924\times10^{-11}$。新 [live byte audit](../../results/kunshan_logs/live_archive_audit_v1/README.md)进一步将90/90 `gauge_sha256` 与远端 S16T16 raw-file bytes 对上；该 pilot 与 B/C campaign 对应 ID 的 header 后 payload 也逐字节相同。旧 reference 拟合仍失败（质量 1.08617，SE 0.00307，$\chi^2/\mathrm{dof}=52.00/8$、近似 $p=1.68\times10^{-8}$，窗口配对漂移21.6σ与7.8σ），`score_status=unscored_reference_failed`；它不是独立物理 anchor，也不校准 robust score。optimize-gaussian v9 又复用了 IDs 70–99，不能算新的 blind validation。之前的跨 manifest SHA 冲突已由完整 raw-file 与 payload 哈希核验解释为不同 NERSC header；并非不同 gauge-link fields。见[逐 ID 身份矩阵](../../results/kunshan_logs/live_archive_audit_v1/identity_and_duplicate_payloads.png)。

**GEVP200 与 HMC snapshot 的 byte-level 身份结论（2026-11-20 更新）**：旧 [provenance-field crosswalk](../../results/kunshan_logs/pion_gevp200_snapshot_crosswalk_v1/README.md) 显示 GEVP200 的180条已测记录与snapshot字段相符、与主manifest的同ID字段不同。新的[live audit](../../results/kunshan_logs/live_archive_audit_v1/README.md)读取远端原始NERSC文件后确认：GEVP200 180/180 hash匹配S16T16C raw files，旧pilot 90/90匹配S16T16 raw files；三目录每个重叠ID的header后payload字节全部相同。raw SHA不同是header字节变化，不是gauge-link fields不同。GEVP200的ID 0–99与旧pilot/S16T16同ID payload相同；ID100–199是同seed链上较晚保存的配置，不构成独立链。GEVP200自身reference gate失败、`score_status=unscored_reference_failed`，已分析validation不能作为新的blind physical anchor。旧`measure.py`源码仍可在Git历史恢复；其余provenance边界见图文audit。后续无需再索取旧gauge bytes或重复ID/hash crosswalk；独立D/E HMC链已齐备；D0–99 correlators已测且reference gate FAIL。按§6先冻结独立reference确认方案与stop rule；在此之前不测E anchor或validation、不打开共享holdout。

## 1. 当前可陈述的结论

- 原始归档 `s16t16_gevp200` 的参考拟合仍不通过：名义质量 $am=1.0771$，$\chi^2=90.6/8$；不可将其
  risk 比值解释为基态物理优劣，可信物理分数保持 `null` / `abstain`。
- A1–A5 身份链、GEVP rank/cutoff 主验收、χ² 子门校准、paired anchor 区间和新测量计划 CPU preflight 均已有代码、测试
  与诊断。身份验证现在要求真实 kernel/reference implementation hash；验证路径要求 report/spec 完整一致；
  candidate 在加载 CuPy / PyQUDA 前拒绝身份不一致。
- 原 GEVP ground-mode 网格每 cell 20 datasets、60 draws 曾显示 coverage=0；现有独立 N=400/cell 扩样见下方链接：
  新 16-cell 扫描中 coverage 为0–4.0%（4/16 cells非零，CP95上界最大约6.4%），bias约0.012–0.036，而within-dataset
  bootstrap SE约0.00063–0.00321；仍是声明的synthetic两态网格，不构成物理基态认证。
- 原 C2 χ² 子门 / J=2,K=2 smoke 每 cell 只有 8 datasets（family valid N=6）；0/8 的双侧 95% Clopper–Pearson 区间为
  [0, 0.36942]，单侧上界 0.31234。新增独立子门扩样见 §4：它将单一 χ² gate 的 synthetic size 估到 1000/cell，
  但没有扩候选 family。随后 J=2/K=2 family 在独立 400-dataset run 中有效 183、abstain 217、invalid 0；null 认证1/183，
  known-better 检出20/183。它扩展的是原 synthetic χ²-family subgate benchmark，不是正式全 gate / 物理认证。
- C2/C3 模拟规模仍须按实验拆开：C2 多数 gate / family 场景每 cell 约 6–8 个独立 dataset（端到端变体有 8–15），C2
  J=2/K=2 family 现有独立 N=400 预选 synthetic extension；原 C3
  anchor sensitivity grid 为 30 个 dataset/cell。另有一项独立 C3 扩样只覆盖 improvement/null/anchor-bias 三个预选场景，每场景
  400 个 dataset；结果见 §4。它提高了这些 synthetic 场景的 MC 精度，但没有扩完整 C3 网格，也没有测真实 anchor。
  小样本诊断足以暴露反保守区间、激发态混淆和弃权行为，但不能给发表级 false-certification / power 精度；这些实验与
  full-gate 402/cell 和 family-wise 每 cell 2500 outer trials、每 trial 30 datasets 不同，不能混作同一分母。
  若这些小样本率会影响下一步决策，再按目标 MC 区间半宽预注册独立扩样；必须交逐场景区间图、失败与 abstain 计数。
- C2 单态 χ² subgate 的独立 null MC 为 1000 datasets/cell，但结果显示 size 随 block 数变化：6/12/24 blocks 下拒绝率
  15.1%/5.4%/1.8%。在同 1000 个 paired null datasets 上，shrinkage λ=0 / 0.25 / 0.5 的拒绝率分别为
  100.0%/16.0%/2.6%、70.1%/5.4%/0.8%、28.1%/2.5%（对应 6/12/24 blocks）。这说明协方差处理强烈影响子门，
  但只适用于当前 synthetic generator；不可用它调 λ 直到得到 5%，也不能称作 full-certificate 或物理校准。
- 新增的 controlled Gaussian linear-null 校准将 p=12、q=4、nominal df=8 下的已知 covariance 与估计 covariance 分开。
  已知 covariance 的 χ² 拒绝率为 4.8–4.9%（每 cell 独立评估 N=5000）；估计 covariance 的 λ=0 在 B=6/12/24
  为100.0%/69.3%/29.1%，λ=0.25 为20.9%/7.5%/3.2%，λ=0.5 为5.9%/2.0%/0.8%。B=6、λ=0 的经验 q95
  达 nominal χ² q95 的 $4.01\times10^8$，median covariance rank=5/12、平均有58.3%特征值触及 floor；这是秩亏和
  `1e-10` eigen floor 的数值放大，不宜只笼统归因于 shrinkage。独立 Monte Carlo rank 校准在声明的同一 DGP 下回到
  4.4–6.0% 范围，但这是分布校准的预期性质，不证明可迁移到真实 correlator 或非线性 production fit。
- production `fit_reference_gate` conditional Gaussian parametric bootstrap 已按 baseline Euclidean-time AR $\rho=0.5$ 与 shifted
  $\rho=0.8$ 执行，每 cell 250 outer datasets × 399 bootstrap draws，无 observed/boot invalid。baseline $\rho=0.5$ 下，
  nominal-$\chi^2$ / bootstrap rejection 在 B=6 为16.4%/1.2%，B=12 为6.0%/3.2%，B=24 为2.4%/1.6%；B=6 与 B=12
  的 paired 差 bootstrap−$\chi^2$ familywise CI 分别为[-21.6,-9.5] pp 与[-6.0,-0.4] pp。$\rho=0.8$ shifted 世界中两种方法
  均很保守（0–0.4%）；N=250 的 CP95 较宽。这个 plug-in bootstrap 没有在所有 cell 恢复 5% size，不得称为已校准替代门。
- wrong excited state 的单态 gate 8/8 通过，而独立质量 guard 8/8 标出；说明 gate 本身无法区分 $E_1/E_0$。
- anchor 诊断中 naive 区间宽度随 $N_{boot}$ 增大而缩小，paired 单 ensemble 区间趋于稳定；naive 27–50% 的
  认证率不能解释为物理置信度。
- GEVP 的负/零/未分辨 metric 现在不会触发非法开方，rank=0/越界也有测试；`_eigvals_with_reason` 将
  `metric_rank_contains_nonpositive_eigenvalue` 与 `metric_rank_unresolved_by_cutoff` 分开，`bootstrap_gevp` 透传失败原因。
  测试覆盖负、零、near-zero metric；2×2 网格不需重跑。

可复查的数值/文字诊断：

- [Kunshan GPU pilot 归档 crosswalk、90 配置残差/耗时图](../../results/kunshan_logs/archive_audit_v1/README.md)
- [身份审计矩阵](../../results/pion_projection/audit_20261119_identity/README.md)
- [GEVP ground-mode 网格](../../results/pion_projection/gevp_ground_failure_grid_v1/README.md)
- [GEVP ground-mode 独立扩样 N=400/cell](../../results/pion_projection/gevp_ground_failure_expanded_20261120_v1/README.md)与[coverage/bias 补充热图](../../results/pion_projection/gevp_ground_failure_expanded_20261120_v1/PLOT_REVIEW.md)：独立 seeds、每 dataset 200 bootstrap draws、CP95 coverage 和 dataset-bootstrap bias CI；只强化该 synthetic grid 的 MC 精度。
- [χ² 子门校准与小样本限制](../../results/pion_projection/certificate_calibration_v1/README.md)
- [paired / naive / independent anchor 区间](../../results/pion_projection/anchor_calibration_v1/README.md)
- [测量计划 preflight](../../results/pion_projection/measurement_plan_audit_v1/README.md)
- [robust-score 合成对照与两张图](../../results/pion_projection/robust_score_cpu_20261119_v1/README.md)
- [χ² subgate 1000/cell 扩样及补充可读图](../../results/pion_projection/certificate_subgate_mc_20261120_v1/README.md) / [补充图复核](../../results/pion_projection/certificate_subgate_mc_20261120_v1/PLOT_REVIEW.md)
- [χ² subgate 协方差 shrinkage 配对敏感性](../../results/pion_projection/certificate_subgate_shrinkage_20261120_v1/README.md)
- [known/estimated covariance 分因素校准](../../results/pion_projection/certificate_subgate_factorized_20261120_v1/README.md)：12 cells × 5000 calibration + 5000 evaluation datasets，含名义χ² size、经验q95、Monte Carlo p-value、协方差秩 / eigen-floor 图与hash核验。
- [production `fit_reference_gate` 条件自举](../../results/pion_projection/certificate_subgate_bootstrap_20261120_v1/README.md)与[补充可读图](../../results/pion_projection/certificate_subgate_bootstrap_20261120_v1/PLOT_REVIEW.md)：6 cells × 250 outer × 399 bootstrap fits，比较 nominal χ² 与 conditional Gaussian p-value、paired familywise CI、rho shift、失败与 invalid 计数。
- [factorized run 的时间字段说明](../../results/pion_projection/certificate_subgate_factorized_20261120_v1/PROVENANCE_NOTE.md)：`prepared_utc` 是固定日期占位值，不是运行时间；不影响 seed 或结果，但不能作为实际时间引用。

## 2. 已完成：paired robust-score CPU 合成诊断

`robust_score_diagnostic.py` 对同一 paired draw ID 比较 median-only 描述分、paired log lower order statistic 和冻结
reference/window 分支的 worst-case 下界；生产 `joint` 复用同一风险 draws 与 score spec 写入 `robust_score_diagnostic`，
`evaluate` 透传该字段。它保持 `status=diagnostic_only`，`physical_score=None`，不改变现有 certificate，也不把本机归档
失效的 reference 升级为可信物理分数。

[合成校准结果、逐场景 MC 区间与两张图](../../results/pion_projection/robust_score_cpu_20261119_v1/README.md)：400 个独立
合成 dataset/cell、每个 64 paired draws。null、heavy-tail null 和 single-extreme-draw null 的阈值通过均为 0/400
（95% CP 上界约 0.009）；已知 30% 改善为 400/400，95% CP 下界约 0.991；near-zero baseline 400/400 abstain。
单态/两态 reference conflict 与 window conflict 均没有 robust lower-bound 通过；两种窗口的 candidate winner 反转。
共同乘法尺度变化下 paired log lower bound 最大变化 $1.3\times10^{-15}$。正风险下用 inverted-CDF order statistic 时，
raw risk-ratio lower bound 与 log lower bound 是单调变换的同一排序统计量，不能当作两种独立证据；median-only 只作排名诊断。

该实验仍是 synthetic method check，MC 区间只描述模拟重复，不是物理覆盖率保证。它没有覆盖真实相关 correlator、完整
reference gate 的大样本 family-wise 校准或共同模型偏差；多模型/窗口集合也只在 synthetic 分支中测试。真实 anchor 仍为
`NOT_RUN`。

### 已完成第一轮：完整 reference-gate CPU MC（强校准结论仍未完成）

[完整 gate MC 图、逐例说明与原始结果](../../results/pion_projection/full_gate_mc_20261119_v1/README.md)：7 个场景、每 cell 100 个独立 dataset、128 paired bootstrap draws；执行 `experiment.develop` 中的完整 reference gate 判据（χ²、paired 窗口漂移、相对误差、质量边界、反射），并绑定源码 hash。null 的参考接受率 87/100，CP95 [0.788, 0.929]；纯 E1 wrong-state 的参考接受率 80/100，说明这些统计门无法证明拟合态就是基态；relative-error 场景 47/100 通过，CP95 [0.369, 0.572]，半宽 0.1015 超过预声明 0.10，标 `INCONCLUSIVE`。

这只是完整 gate 的首轮 CPU 方法诊断，不含候选评分，也不是 family-wise certificate 物理校准。`known_improvement` 只复用 null reference 测接受率，不代表 candidate power。源码段提取避免 gate 判据复制漂移，但后续结构重构仍可改为共享纯函数。真实 anchor / GPU 测量仍 `NOT_RUN`。

### candidate full-certificate MC：原 v2 与 amendment 01 的负诊断；amendment 02 执行完成（有来源 hash reconciliation 限制）

[v2 原始计划](../../results/pion_projection/full_gate_mc_20261119_v2/README.md)冻结 CP95 marginal half-width ≤0.05；逐项穷举二项分布后最坏情形最小为 402 独立 dataset/cell，7 个场景共 2814 个 dev/val worlds。adapter 已在真实 `develop → evaluate → joint → improvement_certificate` 文件入口完成 smoke parity 与 5 类身份篡改拒绝，见[adapter parity 诊断](../../results/pion_projection/adapter_parity_20261119_v1/README.md)：12 项逐 draw 差为 0，gate parity 通过；但只测 4 outer × 8 inner 和一个 null 生成器。这只能证明该 smoke 路径程序一致。

后续[执行前诊断](../../results/pion_projection/full_gate_mc_20261119_v2_execution_01/README.md)确认原计划因 estimand / scenario / budget mismatch 未执行，原 v2 为 **0/2814**。amendment 01 的七场景 dry-run 与主 MC 记录在[初版计划](../../results/pion_projection/full_gate_mc_20261119_v2_amendment_01/README.md)、[dry-run](../../results/pion_projection/full_gate_amendment01_full_dry_02/README.md)和[执行目录](../../results/pion_projection/full_gate_amendment01_execution_02/)；但源码复核发现 `protocol.alpha=0.2` 是 Gaussian smear 系数，却被误写入统计 `score_spec.alpha`，receipt 实际使用 quantile `level=0.2`。

因此 amendment01 主 MC 在 595/2814 时停止并保留为误配诊断：null cell 402/402 中 92 个 candidate certificates（22.9%，CP95 [18.9%,27.3%]），known-lower-excited-overlap 193/402；其余五个 cell 未开始。详见 [RUN_REVIEW](../../results/pion_projection/full_gate_amendment01_execution_02/RUN_REVIEW.md)。这些数不是目标 score alpha=0.05 下的校准结果，旧 checkpoint 的 `RUNNING` 是最后原子写入状态，不表示仍有 executor。

已修复 [`experiment.py`](experiment.py)：核系数单列为 `smear_alpha`，证书统计门读取分离的 `score_alpha`（默认 0.05；当前主测量 protocol 无单独覆盖）。Pion 定向回归为 **51 passed**；新 [amendment02 full-budget dry-run](../../results/pion_projection/full_gate_amendment02_full_dry_01/README.md) 对 7 个场景各跑 1 个 world，五个合法路径的 `score_spec.alpha` 与 certificate `level` 均为 0.05，两类预期拒绝留有 raw inputs / seed / stage / reason。该 dry-run 只验路径与配置，不估计误认证率。

修正版 402/cell 计划在 [amendment02 preregistration](../../results/pion_projection/full_gate_mc_20261119_v2_amendment_02/README.md)。CPU 主 MC 已在独立目录完整执行：[汇总、逐例结果、原始 receipts](../../results/pion_projection/full_gate_amendment02_execution_01/README.md)、[清晰 CP95 图](../../results/pion_projection/full_gate_amendment02_execution_01/candidate_rates_diagnostic.png)、[结果解释](../../results/pion_projection/full_gate_amendment02_execution_01/ANALYSIS.md)。7×402 共 2814/2814，driver `COMPLETE`，2070 个 full-path `PASS` receipts 全部 score level=0.05、draw parity=0；744 个预期输入拒绝是 relative-error 342 个和 nonfinite 402 个，没有 `BLOCKED` 或意外计算失败。

Null 假认证 28/402=6.97%，CP95 [0.0468, 0.0991]，包含名义5%但上界约9.9%，不能证明 false-certification ≤5%。known-lower-excited-overlap 候选证书 335/402=83.3%（CP95 [0.793,0.868]）；window mismatch 与 reflection 均0/402认证、402/402弃权；wrong-state 在 ground overlap=0 时仍343/402=85.3%认证（CP95 [0.815,0.886]），这是结构假通过，说明 paired robust score 不能验证参考态就是基态。relative-error 有效样本仅60；valid-only reference acceptance 25/60 的 CP95 半宽0.1302，按预注册规则 `INCONCLUSIVE`；不得事后加样本。nonfinite 有效分母0，其 conditional rate 不定义。

**来源限制**：[RUN_REVIEW](../../results/pion_projection/full_gate_amendment02_execution_01/RUN_REVIEW.md)发现 amendment02 高层 `preregistration.json` 的 `synthetic_adapter.py` hash=`206cce…`，而 `executor_spec.json`、当前源码及全部2814 receipts为`26e76…`。执行器启动时核验的 executor spec 与 receipts 一致，其他重叠 hashes 一致；但旧源码字节不可得，无法判定该差异是否仅为元数据或涉及行为。因此保留完整数据作 synthetic diagnostic，严格 preregistration 源码链标为 `PARTIAL`；不要改写冻结计划、补跑后混池或称作完全无来源缺口的预注册结果。真实物理分数仍为 null。

**amendment03 source-aligned replay 已完成**：新计划 [`v2_amendment_03`](../../results/pion_projection/full_gate_mc_20261119_v2_amendment_03/README.md) 将同一 7 场景、402/cell、seed 和当前 13 文件 hash manifest 同时冻结到 preregistration / executor / manifest；执行目录 [`full_gate_amendment03_execution_01`](../../results/pion_projection/full_gate_amendment03_execution_01/) 保留 launch hash validation、2814 个逐例 receipts、checkpoint 与 worker resume provenance。13/13 源文件 hash 一致；2814/2814 receipts、development/validation 原始数组、seed 和确定性结果字段均与 amendment02 相同；2070 个 `PASS`、744 个 `EXPECTED_REJECTION`，0 个意外执行失败。完整图文见 [`ANALYSIS.md`](../../results/pion_projection/full_gate_amendment03_execution_01/ANALYSIS.md)、[`RUN_REVIEW.md`](../../results/pion_projection/full_gate_amendment03_execution_01/RUN_REVIEW.md)、[同种子对照图](../../results/pion_projection/full_gate_amendment03_execution_01/candidate_rates_diagnostic.png) 和[分析产物 hash](../../results/pion_projection/full_gate_amendment03_execution_01/analysis_provenance.json)；6→10 workers 的断点调整见 [`execution_amendment_01.json`](../../results/pion_projection/full_gate_amendment03_execution_01/execution_amendment_01.json)。它只检查来源对齐和同种子可复现性，不是独立 MC；不得与 amendment02 合并或扩大分母。旧 amendment02 仍保留 `PARTIAL`，不得回写为 source-complete。
事后复核命令：`python -B -m tasks.pion_projection.source_aligned_replay_summary`（对2814个 receipts 与原始数组逐项校验，并重建分析表和图；不会重新运行 MC）。

## 3. 下一步 B：当前生产停机状态与新的 reference 确认

旧版本节曾要求“按冻结计划直接采集 anchor”；该指令已被 D0–99 真实开发结果和 §6 更新取代，**不得照旧启动 E**。D development 已完成测量但 reference gate 失败，故 E anchor correlator、D validation 和 shared holdout 仍为 `NOT_RUN`。HMC 生成 E 链不等于测得 Pion anchor correlator。

指定的预E CPU搜索稳定性工作已由固定hash的gap-profile和multi-start诊断、合成单/双态及退化/边界测试完成（详见文首与§6）。独立方案审查已完成，见[审查备忘录](../../results/pion_projection/reference_confirmation_plan_review_20261120_v1/README.md)：结论维持 `ABSTAIN / NOT_READY`。关键原因是拟议 M2 在公开 D 上违反 condition / bootstrap-bound 筛查，且 SLSQP 有 gap=0 退化失败；12 个主 block 对 15 维协方差及 M2 `p_approx` 的确认校准也未完成。已有 C2 N=400 family 不是零证据，不能再笼统称“缺 M2 合成模拟”；它没有覆盖本方案确切的 N=60 / 12-block、多窗口、固定 covariance、2000 draw 与全失败/边界弃权规则。C2 χ²子门、C2 family、full-gate、C3 selected / common-block 与拟议 M2 的覆盖矩阵已完成，见[覆盖审计表和图文边界](../../results/pion_projection/m2_calibration_coverage_audit_20261120_v1/README.md)；不要重复制作矩阵或把不同 estimand 合并。下一位 agent 只有在物理上可辩护、经研究者审阅的 M2 改案可能改变 `ABSTAIN / NOT_READY` 决策时，才冻结 M2 角色、start 家族、协方差/重采样、错误接受与功效目标及全 planned 失败/弃权分母，再做最小执行 smoke；精确 N=60 / 12-block 校准也仅在其结果能改变是否进入 E 的决策时运行，并报告 MC 区间、失败/弃权表及图文。不得为让 D 通过而调门。用户审阅新方案和 hashes 冻结之前，不测 E IDs 0–59、不测 D validation、不打开 shared holdout。

## 4. 可延期的物理 / 数值扩展

- **amendment02 CPU 校准执行已完成**，图、数值表、拒绝阶段与 provenance 限制见上述 `ANALYSIS.md` / `RUN_REVIEW.md`。主要未决问题不再是 Monte Carlo 没跑完，而是结构 wrong-state 假认证与物理 anchor 缺失；只在新实验有清晰问题时另开目录，禁止事后 top-up。
- **C2 χ² reference subgate 的独立扩样已完成，完整 family 校准仍未完成**。[预注册方案、逐 dataset p-value / 状态、CP95 区间及诊断图](../../results/pion_projection/certificate_subgate_mc_20261120_v1/README.md)在 ground-state null、single-cosh misspecification、pure-E1 wrong-state 三个 synthetic worlds 下，扫描 6/12/24 个独立 blocks，每 cell 1000 datasets。正确 null 的 gate rejection 分别为 151/1000（15.1%，CP95 [12.9%,17.5%]）、54/1000（5.4%，[4.1%,7.0%]）、18/1000（1.8%，[1.1%,2.8%]）；标称 5% 只落在 12-block 区间内，block-count 改变时子门明显失准。失配参考的拒绝率为 76.9%/92.1%/99.8%。纯 E1 world 在 24 blocks 下仍 967/1000（96.7%，CP95 [95.4%,97.7%]）通过单态拟合门，说明拟合优度不确认基态。9/9 cells 无无效拟合。
  这是 C2 的子门方法学 MC，沿用同一 synthetic generator 和 production `fit_reference_gate`；它没有重跑 full develop→certificate，也没有扩 J=2,K=2 候选 family（原 valid N=6、null 0/6、better 0/6）。因此既不替代完整 certificate / family-wise 校准，也不改变 physical score `null`。原 8-dataset smoke 保留为历史有限诊断；新独立 run 使用单独目录和 seed，禁止混池。文字与可读图见 [PLOT_REVIEW](../../results/pion_projection/certificate_subgate_mc_20261120_v1/PLOT_REVIEW.md)，冻结统计、原图及 hash 见该目录 `README.md` / `execution_provenance.json`。
- **C2 J=2/K=2 synthetic family 的独立 N=400 扩样已完成，正式全 gate 与物理验证仍未完成**。[协议、逐 dataset 记录、CP95 和图](../../results/pion_projection/certificate_family_expanded_20261120_v1/README.md)使用新 seeds，重复两候选（null/better）× 两模型（single/twostate）的 χ²-family gate、40 outer risk draws 与16 inner mass draws。400 个计划中 183 valid、217 abstain、0 invalid；two-state mass-boundary 210/400。null family certification 为 1/183 valid（0.55%，全计划口径1/400=0.25%；marginal CP95 [0.01%,3.01%]）；better power 为20/183 valid（10.9%，全计划口径20/400=5.0%；marginal [6.8%,16.4%]；familywise [5.9%,18.0%]）；非可评估比例为217/400（54.25%，familywise CP95 [47.9%,60.5%]）。报告的 conditional rates 必须与 217/400 abstention 并读。主结果反映该 synthetic benchmark 中较高的 twostate boundary abstention 和较低的 conditional power；不能外推到真实 candidate 或基态识别，也不能与 amendment02/03 full-gate 402/cell 混池。旧 N=6 为历史 smoke；本扩样来源 hash / seed 与原 run 独立，parity smoke 对旧函数通过。
- **χ² subgate 的协方差 shrinkage 影响已用同数据配对隔离**。[冻结设计、逐例结果、familywise paired CI 与图](../../results/pion_projection/certificate_subgate_shrinkage_20261120_v1/README.md)在 ground-state null 下对同一 1000 个 dataset/blocks 配置比较 shrinkage λ=0、生产 λ=0.25、λ=0.5。拒绝率（λ=0 / 0.25 / 0.5）在 B=6 为 100.0% / 16.0% / 2.6%，B=12 为70.1% /5.4% /0.8%，B=24 为28.1% /2.5% /0.5%。相对生产 λ=0.25，零 shrinkage 的配对拒绝差为 +84.0 pp [+80.9,+87.0]、+64.7 pp [+60.7,+68.7]、+25.6 pp [+22.1,+29.3]；λ=0.5 的差为 −13.4 pp [−16.4,−10.6]、−4.6 pp [−6.4,−2.9]、−2.0 pp [−3.3,−0.9]，均为预注册六重 Bonferroni family 95% bootstrap intervals。零 shrinkage 在 B≤12 时 sample covariance 秩亏，并依赖 eigenvalue floor；本试验没有分解该 floor 与自由度估计的各自贡献。
  结果说明固定 shrinkage 选择能大幅改变子门 size；controlled Gaussian linear-null 诊断进一步显示 B=6、λ=0 的极端反保守主要伴随 rank=5/12 与 eigen-floor 主导的 q95 放大。其后 production `fit_reference_gate` plug-in Gaussian bootstrap 已完成 baseline/shifted ρ 对照：baseline B=6 χ²拒绝16.4%、bootstrap拒绝1.2%，B=12为6.0%/3.2%，B=24为2.4%/1.6%；shifted ρ=.8 下两者均0–0.4%。bootstrap 的 size 并未在各 cell 覆盖名义5%，不能把它升级为替代 production gate。外层仅250 datasets/cell，继续 CPU 工作只有在能改变 gate 决策时才值得增加；若继续，须针对条件bootstrap的 plug-in covariance bias 做预注册诊断、提高外层精度，并保留独立验证 generator。不能据此选取“最佳” λ 或套用于真实 ensemble；物理 anchor 仍优先。
- **C3 anchor interval 的独立扩样已完成三个预选场景，完整物理 anchor 仍未完成**。[冻结方案、逐 dataset 结果、familywise 区间及图](../../results/pion_projection/anchor_calibration_expanded_20261120_v1/README.md)使用独立 seeds，每场景 400 个 dataset、每 dataset 两臂各 200 个 mass-bootstrap draws；[绘图兼容性复核](../../results/pion_projection/anchor_calibration_expanded_20261120_v1/PLOT_REVIEW.md)记录原分析完成后 Matplotlib `labels=` 接口不兼容，补图只读 raw/summary，没有改动数据。`improvement` / `null` / `anchor_bias` 的 naive pseudo-replication 认证率分别为 45.3% / 36.5% / 49.7%；单 dataset bootstrap delta 的 5th-percentile 认证率为 0% / 0% / 18.2%，六重 familywise CP95 区间分别为 [0,1.4%]、[0,1.4%]、[13.5%,23.9%]。这里旧文中的“paired”只表示对两臂 bootstrap 风险差取 lower quantile；两臂使用独立 correlator 样本和独立 bootstrap indices，并非共用配置块 indices。三种 independent-repeat mean delta 的 familywise dataset-bootstrap CI 均跨 0。原 `anchor_bias` 场景 candidate noise=.01、baseline noise=.02，含真实 noise 改善，不是 bias-only null；其18.2%认证率不能称为假认证率。原 C3 多因素网格仍为 30 datasets/cell。旧 [anchor_calibration_v1 报告](../../results/pion_projection/anchor_calibration_v1/README.md)的“同一配对 block 索引”“合法区间”“5% 控制”表述已被源码与后续负结果推翻：`anchor_calibration.py` 两臂分别生成 bootstrap indices；该旧报告只作历史记录，不应用作 paired interval 或 size 控制证据。后续 N=400 common-block 与 anchor-bias-only 结果见下两条。
- **C3 anchor-bias-only null 已完成独立 N=400 CPU 诊断**。[协议、逐 dataset 结果、CP95 和图](../../results/pion_projection/anchor_bias_null_20261120_v1/README.md)对每个独立 dataset 只拟合一次两臂（两臂真值与 noise=.02 相同），然后复用同一组质量抽样，将 anchor 分别置于真值偏移 −.02、0、+.02；三臂共用 400 个 dataset IDs，每臂200个 mass-bootstrap draws。naive `sd/√Nboot` 的假认证率为44.5%/44.0%/46.5%，两臂独立重采样的 5th-percentile 规则为11.3%/11.3%/15.5%；旧文所称“paired”不代表相同配置块 indices。该规则的六重 familywise CP95 在零偏移下为[7.5%,16.0%]，高于名义5%。anchor 偏移相对零偏移的配对 dataset-bootstrap CI 均跨0，故暂不能说 ±.02 本身显著改变认证率；但即使 anchor 无偏，当前单 ensemble lower-quantile 规则在此 null 下也未达到5% size。独立重复的平均 delta CI 均跨0。结果否定“普通 bootstrap lower quantile 已足够稳健”的强说法；只适用于声明的 synthetic generator，不是物理假认证率或校准保证。
- **显式共用 configuration IDs 的 synthetic common-block bootstrap 与两种常见 lower-bound 修正已完成独立 N=400/cell CPU 对照，未找到可用的 production score**。[冻结方案、逐 dataset outcomes、familywise CP95 和图](../../results/pion_projection/paired_block_anchor_score_20261120_v1/README.md)用相同配置 ID、配置 AR(1) ρ=0.5、匹配两臂噪声相关 ρ=0.5/0.9、120 configs / block length 5，对照 common block indices 与 independent-arm indices；新 seed 的[follow-up](../../results/pion_projection/centered_anchor_score_20261120_v1/README.md)另比较 percentile、basic/reflected、bootstrap-normal 三种正向 lower bound。zero-anchor equal-noise null 下 common-block 假认证率分别为：ρ=.5 时 18.0% / 19.3% / 18.0%，ρ=.9 时 18.0% / 16.3% / 16.8%（方法顺序 percentile/basic/bootstrap-normal；各自 familywise CP95 见图文）。独立两臂 indices 在 ρ=.9 下仅 0.5–1.0%，但 known-improvement power 也只有 4.5–5.0%；不能把它解释为校准成功。common-block 下三种规则的 known-improvement power 约 14.0–18.2%，仍与明显过高的 null size 并存；basic/reflected 与 bootstrap-normal 没有一致改善 null size 和 power 的折衷。两轮均为固定 anchor、特定 Gaussian/AR(1) synthetic DGP，非真实相关函数、非物理 coverage，也不能证明 block length 5 适用于 gauge ensemble。早期“paired”结果只在 outer dataset-level 对照上配对，不是两臂共用 block resampling。不要再重复该 DGP 或只靠替换 lower-bound 公式挑规则。
- **studentized paired-block sign-flip randomization 已完成一次预注册 CPU 方法对照；不能据此选择 production score**。[冻结协议、逐例结果、familywise CP95 和原始图](../../results/pion_projection/block_randomization_score_20261120_v1/README.md)覆盖5个 synthetic worlds × 两种 matched-arm noise correlation，每 cell 400 个独立 outer datasets；24 个独立 paired blocks/dataset、每块5配置，999 次 sign-flip 与 bootstrap draws。固定 equal-arm、common-truth-shift、Student-t5、uncertain-anchor null 和 lower-noise alternative；共4000个 dataset/correlation cases、7200个含 anchor-offset 逐例行，全部 valid。零偏移 null 下 sign-flip rate 为2.8–6.0%，familywise CP95较宽；known-lower-noise power为10.0%/21.0%（ρ=.5/.9）。paired t 与 sign-flip 的配对认证率差很小；block bootstrap power 高约6.0/5.75 pp，但 Gaussian null 下认证也多约1.5/3.0 pp，方向是多认证而非证明更好。所有数值只适用于本次 DGP。可读的[重排版 null/anchor/power 图、paired difference 图及限制说明](../../results/pion_projection/block_randomization_score_20261120_v1/plot_review/PLOT_REVIEW.md)只读取冻结 summary/raw；原结果 hashes 未改。
  sign-flip 的理论尺寸控制依赖独立 paired blocks、每块臂标签在 sharp no-arm-effect null 下可交换，且共同 pooled reference 对块内标签交换保持不变；它不保证所有 equal-mean weak null，也不能识别共同模型/态偏差。block-level risk estimand 不等于完整 ensemble 的 `improvement_certificate`。本次测试未建立物理 coverage，亦未以校准数据调阈值。
- **robust-score family-wise 第一轮已完成，但仍不能选 production score**。旧 [familywise_score_cpu_20261120_v1](../../results/pion_projection/familywise_score_cpu_20261120_v1/README.md) 的零效应远离 5% 最低改善门槛；其 0/2500 只能作为 far-null 负控制，不能证明阈值边界上的 family-wise error 已受控。修正后的 [v2 protocol 与结果](../../results/pion_projection/familywise_score_cpu_20261120_v2/README.md) 在每个 trial 用 30 个独立 synthetic datasets、4 candidates × 4 reference/window branches、2500 outer trials；先冻结 near-zero abstain，再比较 absolute paired risk difference / relative log-risk、pointwise t、Bonferroni 与 dataset-level max-t。
  在 log-improvement 恰为 log(1.05) 的 Gaussian boundary null 上，pointwise 的 family-wise 假认证为 absolute 9/2500（CP95 [0.0016,0.0068]）、relative 11/2500（[0.0022,0.0079]）；branch-wise Bonferroni 为 0/2500（上界 0.0015），max-t 各 1/2500（上界 0.0022）。重尾 null 下 pointwise 为 8/2500、15/2500，单数据集极端值下为 7/2500、10/2500；Bonferroni 均 0/2500，max-t 为 0–2/2500。10% 真改善的 candidate A 检出率：pointwise 30.5% / 37.7%，Bonferroni 2.0% / 3.2%，max-t 5.9% / 8.8%（absolute / relative）。低基线下 relative 三种规则按冻结 floor 2500/2500 弃权；common-bias 下六种方法均 2500/2500 错误认证，说明统计多重性校正不能识别共同模型偏差。逐方法 CP95、候选计数和图见 [README](../../results/pion_projection/familywise_score_cpu_20261120_v2/README.md)、[边界误认证放大图](../../results/pion_projection/familywise_score_cpu_20261120_v2/familywise_calibration_zoom.png) 和 [弃权 / bias 图](../../results/pion_projection/familywise_score_cpu_20261120_v2/abstention_bias_diagnostics.png)。
  该轮仅对声明的高相关 synthetic family 有效；pointwise 率低于名义 5% 不证明低相关候选选择也受控。Absolute margin = 0.05 × baseline scale，较 relative ratio=1.05 略严格，二者应分开解读。只有独立 physical anchor 盲测后才考虑升级 production score；在此之前 physical_score 仍为 null。
- **family-wise v3 已完成第一轮相关性与稳健估计量扩展，仍不能选择 production score**。[预注册方案、逐场景 CP95 表、原始 trial outcomes 和三张图](../../results/pion_projection/familywise_score_cpu_20261120_v3/README.md)覆盖 ρ=0.05/0.35/0.65，每 cell 2500 outer trials、每 trial 30 个独立 dataset；candidate-level IUT（四 branch p-value 取最大）再做 Holm/Bonferroni，与 branch-wise Bonferroni-16、max-t-16、20% trimmed 和 Huber IUT 比较。
  Gaussian `log(1.05)` 边界 null 下，pointwise FWER 随候选相关性从 3/2500（0.12%）升至 39/2500（1.56%）和 130/2500（5.20%；CP95 [4.4%,6.1%]）。ρ=0.65 时 Bonferroni-4 为 21/2500（0.84%）、branch Bonferroni-16 为 4/2500（0.16%）、max-t 为 23/2500（0.92%）、trimmed 为 18/2500（0.72%）、Huber 为 25/2500（1.00%）。边界重尾及单 dataset outlier 下，Huber/trimmed 没有一致优于 mean；ρ=0.65 的 outlier 场景 false-certification 分别为 47/2500、32/2500，而 mean IUT Bonferroni-4 为 28/2500。10% 真改善、ρ=0.35 时检出率从 pointwise 的 69.0% 降至 candidate Holm 的 41.4%、branch Bonferroni-16 的 19.2%、max-t 的 35.7%、trimmed 的 28.2%、Huber 的 39.2%；6% 弱改善时所有校正规则功效仍低。
  wrong-state proxy improvement 与 common-bias 两类结构反例中，七种方法均 2500/2500 错误认证；多重性修正或抗离群估计量不能校正状态错认或共同模型偏差。v3 没覆盖 near-zero abstention（v2 已显示冻结 floor 下 relative score 2500/2500 abstain），也未验证真实 correlator 的协方差结构。图分别展示相关性下边界误认证、真效应功效及结构负控；所有 CP95 仅为 synthetic Monte Carlo 区间，不是物理 coverage。
- GEVP 跨 replica mode tracking、rank>2 和更长时间平台；需独立 ensembles 与 systematics 项，不能靠 bootstrap spread
  代替激发态污染误差。
- 多体积 / 多动量、不同 sink family 或独立 anchor；每次只扩一个维度并使用独立 test set。真实 anchor / 新测量需要 GPU / 集群；CPU full-gate MC 不依赖该硬件。

硬件依赖仅适用于真实 anchor / 新测量；amendment02 的 402/cell 合成校准完成但高层 preregistration 与执行 source hash 不一致，严格来源链仍为 `PARTIAL`。amendment03 已完成 source-aligned 同 seed 重放，2814/2814 原始数组和确定性结果一致；它没有增加独立样本，也不修复旧 run 的来源缺口。不要对 amendment02 事后补样或与 amendment03 混池。C2/C3 与 GEVP 小样本结论仍须按 §1 标为有限诊断；任何后续扩样都应先预注册精度，交逐场景区间图、失败/弃权计数和解释文字。

每个扩展都交图或带误差/失败样本的表，不以“所有候选都 abstain”刷过关，也不把分数稳定误读成物理准确。

### 已完成：weak-null 非交换性与有限方差 robust bound（CPU）

[冻结方案、18,000 个独立外层数据集、逐例 block difference、CP95 和图文诊断](../../results/pion_projection/weak_null_nonexchangeable_20261120_v1/README.md)新增比较 paired t、raw studentized sign-flip、centered wild sign-flip t、block-bootstrap percentile，以及需要外部已知方差上界的 median-of-means (MoM) 单侧界。每 cell 使用 3000 datasets，24/48 independent blocks；positive-control 是同一 rare-tail DGP 加 $+1.5\sigma$。在 Gaussian sharp-null 下 t / raw sign-flip / centered wild 的认证率为 5.5–5.9%，点态 CP95 覆盖名义 5%；percentile bootstrap 为 6.2–7.0%。在声明的均值为零、方差为1、10%稀有负贡献的左偏 weak-null 下，24 blocks 的 paired t / sign-flip / centered wild / percentile-bootstrap false-certification 为 10.6% / 12.4% / 16.6% / 9.4%；48 blocks 下仍为 9.4–10.6%，各自点态 CP95 均在 5% 之上。MoM 已知方差上界为1时两种 null 都是0/3000认证；对 $+1.5\sigma$ 强改善的 power 为 94.8% / 99.9%（24/48 blocks）。这是 iid independent-block synthetic result：MoM 的保证依赖可由外部证据支持的方差上界；当前物理数据没有该上界，且块间依赖会破坏此保证。不得据此选择 production score，也不要重复同一 rare-tail generator；若后续测试别的 weak-null/covariance structure，必须先证明它会改变 decision，并报告 size/power/abstention 的 paired 区间、失败数与图文。版式复核图见 [PLOT_REVIEW](../../results/pion_projection/weak_null_nonexchangeable_20261120_v1/PLOT_REVIEW.md)，该复核只重绘冻结 summary，没有重跑或修改模拟数据。

### 2026-11-21 bounded block-MSE：用户接受新estimand，条件合成校准已完成

用户已接受 bounded block-MSE 是不同于原ensemble-risk的estimand，并要求继续校准。[理论设计稿](bounded_score_design_review_20261121.md)的原始`THEORY/DESIGN_ONLY`状态是校准前快照；其范围、独立性、anchor物理条件仍有效，当前实现与结果见[新实验完整报告](../../results/pion_projection/bounded_score_calibration_20261121_v1/README.md)及[可读图复核](../../results/pion_projection/bounded_score_calibration_20261121_v1/plot_review/README.md)。这项新estimand校准是下方历史“停止重复旧grid”规则的明确增量，不是重跑既有rare-tail direct-delta实验。

新增[`bounded_score_calibration.py`](bounded_score_calibration.py)逐式复核 `d=(b−A)²−(c−A)²∈[−R²,R²]`、anchor扣减`2B_A R`与F重Bonferroni的Hoeffding下界；12项解析边界/输入拒绝/单位缩放/seed/no-clobber测试通过。冻结实验为质量域[0,1]、m*=0、δ*=0.1；n=12/24/100/400、F=1/2/4；exact与99%覆盖的independent uncertain anchor；另含anchor undercoverage和完全跨块依赖stress。DGP从有界b/c质量构造真实平方损失差，包括最大可能方差的反相关endpoint null、shared-baseline family null、Δ=δ*边界null、Δ=.2/.4改善与anchor-sensitive equal-MSE null。protocol在生成前写入并绑定源码/理论稿hash；无测量数据参与。

**完整分母：168 cells×3000=504000 planned，504000 valid、0 failed；其中24个assumption-violation stress cells共72000个数值有效但推断ineligible的dataset全部abstain。** stress中的数值crossing只作假设失效负对照，不是发出的证书。每cell的joint coverage、false-family crossing、power均附marginal与全表Bonferroni binomial MC区间；[raw CSV.gz](../../results/pion_projection/bounded_score_calibration_20261121_v1/raw_datasets.csv.gz)保留每个dataset的充分统计、anchor、各candidate下界、true delta、failure/eligibility和证书状态。对全部504000行已独立复算公式及计数、核对协议source和artifact hashes，均一致。

**诊断结果体现保守性和假设代价：**eligible cells最大观测joint noncoverage为37/3000=1.233%（uncertain-anchor sensitive null，n100/F2；coverage CP95 [0.9830,0.9913]），不能据此声称所有DGP均已校准。在n400/F1时，Δ=.2改善的power在exact anchor为794/3000=26.47%（CP95 [24.89%,28.08%]），uncertain anchor为0/3000（上界0.123%）；Δ=.4则为3000/3000与2951/3000。故小size不是单独成功指标。n400的anchor-undercoverage stress数值假认证crossing为3000/3000；完全相关block stress约49–50%，尽管两类全都按ineligible弃权。这明确说明有界化不能替代anchor系统误差控制或真实独立块。

**下一物理缺口：**新estimand的条件合成实现已经成立，但现有Pion仍缺可辩护质量/损失范围与clipping/失败政策、真正独立评价块的来源、独立anchor及含共同偏差的有效误差区间。不能把D bootstrap draws当独立块；不能将代码质量域当真值物理界。先分别审阅point-source M2与matched source–sink generation的protocol/hash，保持两条测量流身份分开。当前reference FAIL、M2 NOT_READY、E/new validation/shared-holdout关闭和`physical_score=null`保持有效。本轮未运行GPU/QUDA或读取受限split。未来只有新物理contract可能改变NOT_READY且获授权时，才做最小GPU identity preflight，并交anti-Hermitian时间/逐块区间图、source-alpha表、planned/valid/failed/abstained计数和文字物理边界。不要继续无目的扩大本MC网格。

## 5. LatticeArena 可复用扩展点

- `measurement_plan` / `RunSpec`：加入新的 ensemble、source/sink、RHS、边界条件和预算，并在 GPU 初始化前拒绝非法计划。
- `smearing_contract`：把高层 source 参数（如 $(\rho,n)$）映射到实际低层 kernel 参数，与 sink kernel 做 GPU 前等同性检查，并把映射表写入 provenance；扩展到不同 smeared operator family 时可复用此边界。
- `OperatorContract` / `MeasurementBundle`：为新候选核或观测量声明输入几何、能力、Hermitian / covariance 约定。
- `evidence receipts` / `RunState`：把测量、代码、输入与状态机绑定，使“conditional diagnostic”和“physical score”分开；可复用 hash-chained JSONL checkpoint 记录长 bootstrap 的逐 draw 进度并安全续跑。
- `score_spec` / comparator：可以换 robust score 或多模型 sensitivity，但冻结 alpha、风险下限、比较族和 draw 身份。
- `SearchAdapter` / proposals：复用外部预算与候选校验；搜索轨迹和拒绝原因写入可审计结果。

## 6. 下一个 agent 开工顺序

**测量流隔离提醒：** 独立 reference 草案的 M2/P1–P2 是 `protocol_fresh_20261120.json` point-source correlator 流（sink powers 0,2,4,8,16,32,64；D development 0–99；E anchor correlator 尚未测量）；`protocol_multisource_matched_v2.json` 则是另一个 source–sink cross-matrix 流（point/H4/H16 sources；development 0–59、gap 60–69、validation 70–99）。matched-v2 CPU preflight 不代表 point-source M2 correlator 或 E anchor 已测/已修复/已通过，M2 点源结果也不认证 cross-matrix 的 Hermiticity。两流不得混用 correlators、splits、generation 或 hashes；各自须冻结独立 measurement contract 和输入清单。详见[reference confirmation 草案](reference_confirmation_plan_draft.md)。

### 2026-11-21 CPU 增量工作的停止判定（先于下方开工清单）

**当前判定：在现有输入、模型与草案门槛保持不变的范围内，没有一个新增 CPU 校准的结果能把 `ABSTAIN / NOT_READY` 改成可进入 E 的状态；本轮不提议或执行新模拟、拟合或测试。** 这不是声称任何未来 CPU 工作都无用，而是当前没有经研究者审阅、增加独立物理信息的新 reference/measurement contract 可供校准。先停止执行性 CPU 校准，仅保留方案审阅工作。

停止理由是联合门中的已知否决项，不能由另一个统计门的通过抵消：公开 D 的 single-cosh gate 已 FAIL；拟议 M2 的晚窗条件数与既有 bootstrap mass-bound 已违反自己的筛查，gap=0 处还有退化与非成功终点。SVD、multi-start 和可恢复 journal 的实现/回放已完成，它们减少数值执行风险，但不增加谱信息，也没有把新多起点 bootstrap 接入已冻结的确认门。[执行器回放](../../results/pion_projection/two_state_executor_replay_20261120_v1/README.md)的87个同输入端点质量/目标值逐字一致，不能视为87次独立确认。[既有覆盖矩阵](../../results/pion_projection/m2_calibration_coverage_audit_20261120_v1/README.md)已经说明精确 N=60/12-block M2 流程尚未校准；**即使新增校准给出理想 size/power，当前 D 可辨识性否决和未获审阅的新物理信息仍然存在，所以本轮不运行它。** 更换 lower bound、加 bootstrap draws、追加同 DGP seeds 或放宽 condition/boundary 门均不能补上该信息。

新 source–sink generation 是潜在的物理改案，不是现有 M2 数据的数值补丁。matched-alpha CPU contract 只支持预期参数流；新 generation 尚无原始矩阵身份门的测量证据。不能以对旧矩阵对称化、重标度、重复 fake-callable/synthetic grid 来证明新矩阵 Hermiticity，也不能用矩阵身份通过替代基态识别。相关既有[development/observed-array 诊断报告](../../results/pion_projection/source_sink_hermiticity_per_config_20261121_v1/README.md)仅作为历史公开报告来源；本轮没有重新读取其 correlator 或任何 validation 数组。

```text
固定当前输入/模型/门槛
  → D 的物理/可辨识性否决仍成立？是
  → 即使候选 CPU 校准结果最佳，是否仍必须 ABSTAIN？是
  → 停止新增 CPU 校准；保留 TODO、physical_score=null、NOT_READY

只有出现增加独立信息且物理上可辩护的新方案
  → 研究者先审阅：确认命题、source/sink contract、模型职责、独立验证 estimand
  → 若仍不能改变已有否决：停止，不开模拟/拟合/测试或 GPU
  → 若有可能改变：先写唯一关键缺口及两种结果分别改变什么决定
  → 再冻结执行器/起点、协方差/重采样、size/power目标与全 planned 分母
  → 另获相应执行授权后，才评估一次最小必要 smoke/CPU 校准
  → CPU结果仍只回答该DGP的统计/执行问题；测量与盲测另行授权
```

**历史分母与本轮零执行记录（来源是既有报告，不是本轮复跑）：**

| 证据/单位 | planned | valid / 正常执行 | failed / 输入拒绝 | abstained 与边界（不能混作失败） | 解释边界 |
|---|---:|---|---|---|---|
| point-source D development 配置 | 100 | 100/100 identity/residual 通过 | 配置身份/残差失败0/100 | 配置级 abstain 未定义；该批 reference 分析 FAIL，不是100次独立 gate | 一条已看过开发链；原 gate 不被 M2 事后覆写 |
| 旧 M2 bootstrap，各窗口分别计 | 每窗1000 draws | 每窗1000 finite-valid | 每窗invalid=0 | m1上界命中0/1000、0/1000、2/1000；按草案全窗口口径整体 ABSTAIN | 固定D的重采样，不是3000个独立ensemble；见[只读审计表](reference_confirmation_plan_draft.md#d-development-feasibility) |
| D multi-start/同输入 executor replay | 每窗29起点，共87端点 | 每窗29/29有限端点；24/29 SLSQP正常终止 | 每窗5/29非成功；合计15/87，不从分母删除 | gap=0端点5/6/6（按原multi-start描述）；起点级 score abstain未定义 | 起点相关；solver success不等于reference通过，回放不新增样本 |
| C2 χ² subgate | 9 cells，各1000独立datasets | 各cell 1000 valid | invalid=0 | 只是PASS/REJECT子门，没有完整certificate弃权；null三cell拒绝151/54/18 | 单态子门DGP，不校准完整M2；[报告](../../results/pion_projection/certificate_subgate_mc_20261120_v1/README.md) |
| C2 J=2/K=2 family | 400独立datasets | 183 gate-valid | invalid=0 | 217 abstain；210/400 two-state boundary，与abstain重叠不可相加 | null1/183与1/400、better20/183与20/400须并报；[报告](../../results/pion_projection/certificate_family_expanded_20261120_v1/README.md) |
| full-gate amendment03 replay | 7×402=2814 worlds | 2070 full-path PASS receipts | 744预期输入拒绝；意外执行失败0 | certificate弃权须逐场景读，不能从receipt PASS推成物理通过或总弃权数 | 与amendment02同seed，不双计分母；[分析](../../results/pion_projection/full_gate_amendment03_execution_01/ANALYSIS.md) |
| C3三个预选场景扩样 | 每场景400 datasets | 每场景400 valid | invalid=0 | 认证否与abstain不是同义；该实验未定义完整M2弃权门 | 原30/cell网格未被全扩；oracle anchor与两臂抽样语义见[报告](../../results/pion_projection/anchor_calibration_expanded_20261120_v1/README.md) |
| 本轮新增 CPU 校准/拟合/测试 | **0** | **0** | **0** | **0次执行；状态 NOT_RUN，不能写成0/N错误率或“全弃权通过”** | 本轮只审阅报告并编辑本TODO |
| 拟议 point-source E 确认 | 草案60配置→12个length5块/15维；拟议2000 draws，均未审批冻结 | 本轮配置/draw执行均0 | 未运行，无实测失败率 | valid/failed/abstained率未定义，不能以0/60写成功率 | 12块的协方差秩至多11；HMC E链不等于E correlator |
| 新 matched source–sink generation | 样本数/访问清单须独立审阅冻结 | 本轮执行0 | 无新失败率可估 | 未运行，不推算valid、失败或弃权概率 | 新矩阵流与point-source E流的ID、hash及估计对象不得混用 |

上述分母逐实验保留；原C2 6–8（部分端到端8–15）、原C3 30/cell、各N=400扩展、full-gate402/cell和family-wise2500-trial均不能混池。MC区间只描述各自声明的synthetic重复，不证明物理coverage或共同reference偏差已消除。现有数值/边界警示可以支持“当前信息/方案不足”的决策，不能证明所有两态模型在物理上错误，也不证明增加算符或换source/sink必然成功。

**历史停止判定（2026-11-21）：**当时结论是在现有输入/门槛下不新增 M2 校准；该结论仍有效。当前不是再交方案审阅文本，而是按文首核对已有 receipt/trajectory/source-sink 记录是否能支持独立块与 anchor 覆盖。若不能增加可识别的独立信息，继续停在 `ABSTAIN/NOT_READY`；新 generation 的 anti-Hermitian 时间图、质量/条件数、mode tracking 和全 planned 失败/弃权表只能在未来获授权测量后产生。本轮不读 E、gap、validation 或 shared holdout，不启动preflight/GPU。

1. **不要重跑已完成的 synthetic grid。** amendment02 source chain 保持 `PARTIAL`；amendment03 是同 seed replay，不增加独立样本。Family-wise v1–v3、randomization、common-block 与固定 C2/C3 子门 DGP 已有图文结果，不要只换同一 DGP 的 seed 或阈值后把它算作新证据。
2. **检查小样本警示时保留各自分母。** C2 多数 gate/family 单元仍只有约6–8个 dataset（部分端到端变体8–15）；J=2/K=2 子门的独立 N=400 中183 valid、217 abstain；C3 原全网格约30/cell，但预选 bias/null/improvement 等场景已有独立 N=400/cell；完整 full-gate 402/cell 与 family-wise 2500 outer trials 又是不同设计。N=400扩样只改善声明的 synthetic estimand 的 MC 精度，不修复模型共同偏差、物理系统误差或外推性。若发表决策确实依赖更窄 MC 区间，先预声明目标半宽/功效与独立 seeds，再交逐场景 CP 区间图、失败/弃权数和限制说明；不能合并分母。
3. **覆盖审查与稳定 M2 数值诊断已完成；不要重复现有校准。** [`m2_calibration_coverage_audit_20261120_v1/README.md`](../../results/pion_projection/m2_calibration_coverage_audit_20261120_v1/README.md)按 estimand、分母和生成器并列 C2 χ² N=1000/cell、C2 J=2/K=2 N=400、amendment03 同 seed replay、C3 selected N=400 与 common-block N=400；它们不能合并，也不能当成 N=60/12-block M2 确认流程校准。`TwoStateFit` 现以 Cholesky-whitened SVD 解线性振幅，并新增保留每一起点 optimizer 结果/异常/边界/秩的 `fit_full_multistart`、逐 planned draw 输出完整行/索引/hash 的 `iter_bootstrap_multistart`，以及带 manifest/source/environment、fit-data/channel-scale 与 block-ID 身份、fsync、hash chain、损坏拒绝和显式续跑的 [`run_checkpointed_bootstrap`](bootstrap_checkpoint.py)。稳定拟合 focused **11 passed**，checkpoint focused **5 passed**，两者合计 **16 passed**；全 Pion 测试 **96 passed**。使用同一 hash-audited D0–99 数据和既有29个起点/窗口的[执行器回放](../../results/pion_projection/two_state_executor_replay_20261120_v1/README.md)显示87个端点的 mass 与 cost 全部逐字相同、每窗24/29 SLSQP success。这是同输入实现一致性，不是独立样本或全局最小值证明。旧 `fit_full()` / `bootstrap()` 仍使用排除gap=0的坐标搜索；新多起点/重采样路径还未接入冻结的确认bootstrap或production gate。

   当前独立方案审查[`reference_confirmation_plan_review_20261120_v1/README.md`](../../results/pion_projection/reference_confirmation_plan_review_20261120_v1/README.md)维持 `ABSTAIN/NOT_READY`，D 上晚窗条件数/触界与搜索路径不稳定仍违反草案拟议筛查。**本轮不跑 N=60 合成校准**：在 D 已触发停止条件时，更多 synthetic rate 不会改变“不进入 E”的决策。若之后出现物理上可辩护且经研究者审阅的新 M2 方案，下一位 agent 应先冻结显式 start 家族、M1/M2职责、协方差/重采样、错误接受/功效目标与全 planned 分母；再用 [`run_checkpointed_bootstrap`](bootstrap_checkpoint.py) 做小规模执行 smoke 和配置/恢复审计。只有计划通过审阅且模拟结果会改变是否进入 E 的决策时，才以 N=60/12 blocks 评估 null、wrong-state、known-improvement、common-bias 下的错误接受率/功效和 MC 区间，并交校准图或表。不得为让 D 通过而调阈值，也不得打开 E、validation 或 holdout。
4. **生产继续停机。** 不测 E IDs 0–59，不测 D validation，不打开共享 blind IDs140–199；用户批准并且新方案、执行器、source/input hashes 冻结前，不启动新 GPU/QUDA测量。reference门即使未来通过也只支持声明范围的独立复现，不自动支持基态或候选score。
5. **锁定共享 blind holdout 后才打开。** `S16T16D` IDs 140–199 同时预留给 Pion validation、Optimize blind test 和可能的 Wilson stout/APE comparison。Wilson 的 D-chain protocol 已冻结且没有授权这60个ID；Optimize 的真实 trainable-$W$/P3 candidates、score 与源码版本仍要在开放前冻结。三方须共同记录访问方案，只允许一次解盲，不得在任何一方查看结果后改另一方候选或口径。跨任务复用要明确标为相关证据，不得声称独立重复。Anchor reference gate 未通过时，validation preflight 必须拒绝读取；任何失败/弃权仍保留在预注册分母。
6. **物理结论边界与交付。** 所有生产结果继续报告每配置 provenance/residual、reference mass/window残差图、anchor/reference一致性图、paired risk及区间、失败/弃权表和解释文字。只要 reference、anchor 或共同偏差控制不通过，`physical_score=null`；robust synthetic-score 不能覆盖错误 reference。上述生产门槛未闭合前保留本 TODO，不删除。

### 2026-11-21 补充：bounded block-MSE 无量纲规划图（CPU，解析敏感度）

[报告与图](../../results/pion_projection/bounded_score_planning_20261121_v1/README.md)将已接受的 bounded block-MSE 下界写成无量纲条件 `g > sqrt(2 log(F/alpha_s)/n) + 2B/R`，扫描 `n=12/24/100/400`、`F=1/2/4` 和 exact/uncertain anchor allocation。图的横向变化显示增加独立块只压低统计误差项；纵向 anchor 偏差项形成不能靠扩样消除的下限。24个公式情景是确定性计算，`B/R=0.05` 只作代数示例，未声称是物理可行值；本次没有新增 Monte Carlo、fit 或测量。

本轮跨 Pion/Wilson focused tests 共 **26 passed**：planning 7、bounded-score regression 12、ground-state bound 7；图已视检，summary/source/artifact hashes已写入结果目录。下一位 agent 不扩同一模拟网格。先由研究者审阅目标质量与单位、物理范围或事前 clipping、失败块政策、独立 block 来源及 anchor common-bias 上界；随后按该合同重算可行 n/精度。没有这些输入时继续 `ABSTAIN/NOT_READY`，不把维度化图或条件 synthetic calibration 叫作物理校准，`physical_score=null`。
