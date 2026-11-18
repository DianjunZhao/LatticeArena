# pion_projection 后续开工单

本文件是研究规划，不是新实验报告。2026-11-18 根据实际源码、忽略目录中的 NPZ/JSON 和论文摘要核对；本轮未运行 GPU、MPI、远程命令或模型 API。已有 validation 已公开且反复用于诊断，不能再称全新盲测。
核对基线为Git提交`40a7c9d`；本轮只新增三个任务的todo，不修改源码或历史输入。以下行号针对该版本，实施前重新确认。
后续补充已纳入本文“评分重设计”和“直接面向能量误差的后续主指标”；LatticeArena公共接口、测试证据回写和扩展顺序见[框架扩展总纲](../wilson_loop/todo.md)。本task负责ReferenceProvider/Metric/Comparator的科学定义，公共实现由一个集成负责人维护。

## 职责与当前判断

LatticeArena 固定测量和评估，允许候选只改空间 sink。此任务检验：固定 point source 时，空间核能否更早、更精确地提取 quenched pseudoscalar 基态。它不测物理点 pion，不直接证明动力学 QCD 的普适改善。

当前最重要的工作是修复评估契约和验证参考的可识别性，暂缓更复杂候选搜索。流水线已有真实档案，但绝对分数尚不可信。两态通过既有 gate 只说明没有触发那些规则，不证明模型正确。模型平均也不能把两个失配模型自动变可靠。

## 实际实现及物理约定

- 科学定义：`doc/pion_projection.md`；执行协议：`tasks/pion_projection/protocol.json`。
- Wilson valence，κ=0.14，裸质量 `1/(2κ)-4`；空间周期、费米子时间反周期；零动量、γ5、原点 source；规范场无需固定。
- 几何协议 `[x,y,z,t]`；kernel links `(3,z,y,x,3,3)` 的方向顺序 x/y/z，field `(z,y,x,3,nrhs)`。
- `candidate.py:20–37 apply_kernel` 从 propagator 重排到 48 RHS，用 `vdot(S,K S)` 收缩；实部之外若超过相对阈值就拒绝。
- γ5-hermiticity 下 pseudoscalar 收缩化为该形式的推导和 PyQUDA 自旋/颜色顺序，仍应建立显式小体积对照，不能仅靠 reshape 正常运行证明。
- `H=(I+0.2 spatial_hopping)/2.2`；幂次 `[0,2,4,8,16,32,64]`。
- `H^(2k)` 对应两腿各 H^k 的范数平方；线性组合对应实际 `K=Σu_n H^n/A_n`，不是将这个组合再作用到两腿。
- 实际支持 real Hermitian、spin scalar；signed kernel 可产生负 C，不能施加所有通道幅度非负的错误限制。
- 保留 A1+、平移与 gauge covariance；复杂非 Hermitian 扩展只在科学说明中，当前 executable 不支持。
- `statistics.py:11 fold` 逐组态折叠；meson 周期 cosh 不能把费米子 APBC 直接变成 meson 负号。
- 所有质量是 am，不能不经 a 标定换算 MeV。

## 已核对的实际证据

以下数值来自磁盘产物；只读 CPU 核对了数组形状并读取 JSON，没有重做远端反演，因此 GPU 正确性是档案证据。

| 产物 | 已核对内容 | 限制 |
| --- | --- | --- |
| `results/pion_projection/s16t16_v1/development.npz` | `(60,7,16)`，60 IDs | 与仓库默认30开发组态不同 |
| 同目录 `validation.npz` | `(30,7,16)`，30 IDs | 已公开，6个长度5的block |
| 同目录 `reference_bootstrap.npz` | masses `(1000,)`，indices `(1000,12)` | 开发12 blocks，非README所述6 |
| 同目录 `nested_bootstrap.npz` | risks `(200,3)` | 固定协方差条件下的嵌套区间 |
| `s16t16_twostate` 同名数组 | 同为60/30，7通道T16 | 同一批数据的模型探索 |
| `s16t16_t32/development.npz` | `(60,7,32)` | 无 validation NPZ，不能称完整留出实验 |

真实 T16 协议是 development IDs 0–59、gap 60–69、validation 70–99（60/10/30）；根默认协议30/5/15。使用每个 run 的 provenance/protocol 快照，不要直接默认重跑 develop/evaluate。

`results/pion_projection/s16t16_v1/validation_results.json`：

- 单 cosh `am=1.0861669411 ±0.0030744009`，χ²=52.0009629，dof=8，近似 p=1.68238e-8。
- 窗口偏移21.6224σ、7.81751σ；reflection max z=1.52935通过。
- local risk=0.312670255；tuned=0.0125563692；SLSQP=0.00770270804；均 `score:null`。
- tuned/SLSQP risk ratio=1.630124，配对95%区间[1.396310,2.190467]；这是失配参考下的诊断。
- local 的 departure²=0.3112793 远大于 variance=0.00139094，优化主要受参考偏差项支配。

`calibration.json`：名义窗口模拟校准 p=0，晚窗6–8 p=0.266667；合成 false-fail=0。这个零是有限模拟零 exceedance，不是严格概率零，更不是校准“完全正确”的证明。

`reference_systematics.json` 固定同一套权重、只换参考：

- 单态→两态 mass 1.086167→1.057000；两态 SE=0.00983683。
- 两态 χ²=0.0583192 /4，p≈0.999583；极低χ²提示可识别性/协方差/自由度问题，不能只凭它断言已证明过拟合。
- local risk 0.312670→0.559246；tuned 0.0125564→0.00469991；SLSQP 0.00770271→0.00484013。
- 排序翻转：两态下 tuned 优于原 SLSQP。这里的诊断比分11899/11554不是独立冻结实验分。

`results/pion_projection/s16t16_twostate/validation_results.json` 是重新优化的另一实验：

- gate=True，pilot_only；tuned score4050.4206，SLSQP6039.7294。
- tuned/SLSQP=1.49114，[0.865047,1.857764]，包含1。
- 不可与固定权重 systematics 混为同一结论。

T32 `submission.json`：χ²=120.2316/11，偏移20.252σ/16.263σ，reflection z=274.2693。主agent本轮CPU复算已定位为假警报：`experiment.py:56` 使用硬编码T16表达式 `raw[...,1:8]-raw[...,15:8:-1]`，在T32错误地比较两段前向数据，精确复现274.2692780312892。按真正T-t计算，t=1..15的max z=2.398144774908899，t=1..7为1.4445846358937766，均通过阈值4。正确reflection不能消除独立存在的χ²和窗口漂移失败，也不证明加T一般无效。`doc/pion_projection_results.md:171` 的因果结论仍过强。

## 最高优先级：冻结边界存在可复现缺口

证据位置：`experiment.py:13–18 make_reference`、`:102–113` 冻结、`:147–166 evaluate`；`common.py:10`。

- 参考类别来自环境变量 `LATTICEARENA_REFERENCE`，submission 未显式冻结 model identity。
- evaluate 校验 statistics.py、kernels.py，却没有绑定 experiment.py、reference_twostate.py 或 reference model选择。
- 同一 submission 可在环境变化后重新拟合另一模型，但沿用旧 `reference_passed`，形成语义不一致风险。
- `candidate.py:113` 以后直接实例化 `ReferenceFit`；不通过 make_reference，因此 twostate主流程与generic candidate可能使用不同参考。
- builder只哈希源文件，外部helper依赖变化不一定纳入身份。可信本地代码模式也不构成防数据访问沙箱。

这是静态代码确认的缺口；本轮没有执行写入结果的复现实验。后续在pytest tmp_path合成数据中复现，不改既有档案。

## 阶段 A：先做CPU契约修复（推荐第一项）

输入：上述源码和小型合成数组；输出：版本化 submission/reference schema、统一 factory、回归测试。

1. 在 `common.py`/`experiment.py` 统一 reference spec，显式保存 model kind、参数化、bounds、搜索策略、window、协方差规则、source hashes和schema版本。
2. `make_reference` 以显式 spec工作；CLI环境只在创建run时解析，evaluate必须使用已冻结spec或拒绝不匹配。
3. candidate/reference_systematics/nested_intervals均复用同一个factory；systematics明确建立独立 diagnostic身份，不能覆盖冻结结果。
4. 冻结评分依赖闭包或明确实现版本；确保候选helper与量测/收缩约定可审计。旧submission缺字段时走清晰legacy只读模式，不伪造哈希或迁移原件。
5. 测试单态冻后切twostate拒绝；修改参考代码拒绝；generic与主流程在合成同一C上得到同样reference/risk；协议不匹配、dev SHA变更、缺行、重复ID、partial checkpoint均拒绝。
6. 保留既有scale invariance、负权重、degenerate outer draw、fold、covariance/linearity/Hermiticity测试。

验收：在无GPU环境独立构造fixture并通过；同一冻结身份永远给同一reference语义；错误条件明确fail closed。停止条件：仍须依赖未冻结环境变量才可复现，不启动候选训练。

建议命令（后续实施时；本轮未执行）：

```sh
PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -q -p no:cacheprovider tests/test_pion_projection.py
```

## 阶段 B：CPU档案审计与参考可识别性

输入：既有NPZ/provenance/submission，不读凭据、不自动调用agent/report。
输出：新run诊断目录中的 inventory、参考扫描表、原始/折叠对照图和失败清单，不覆盖历史JSON。

1. 为所有split列出hash、IDs、完整性、finite、geometry、来源host、软件版本；区分源码当前版本与档案版本。
2. 修复 `experiment.py:56` 硬编码反射索引，按T动态生成t与T-t，并显式要求当前origin-source约定；新增T16/T32对称及注入反对称噪声fixture。保留归档错误z并标注来源，输出修正版诊断；不得因此删除χ²/窗口失败理由。
3. 源码对12个spin-color列逐列验残差，但保存的records只有`residual_max`，不能从档案恢复12列逐项值；核对保存的最大值、cache-hit和时间，缺少的诊断明确记录。本轮只读核对：T16开发/验证最大残差分别9.99238e-11/9.97657e-11，60/30条gauge hash均与`results/kunshan_logs/manifest.json`对应；这是档案内部一致性，不是重新求解或独立残差验证。
4. 12个dev blocks对12维名义参考均值，原始样本协方差rank至多11；25% shrinkage使逆可算不等于信息充分。
5. 输出协方差谱、condition number、eigen floor触发数；在预声明网格下比较shrinkage和block长度，不按validation挑最好值。
6. 两态改为返回并存储m0、m1、gap、各通道幅度、normal matrix condition、边界命中、多起点结果；当前fit只返回m0/cost，信息不足。
7. 搜索网格粗0.02、细0.01/0.003：检查bootstrap误差是否受格点化影响；用独立bounded optimizer对照、profile likelihood/gap扫描和奇异情况处理。
8. 模拟已知单态/双态/三态、signed overlap、近简并gap和相关噪声；报告mass bias、coverage、错误接受率/拒绝率、失败replica数，不丢不收敛样本。
9. `calibration.py:15–24` 是从逆固定metric构造Gaussian均值模拟；它没有重估样本协方差和autocorrelation，不能覆盖完整数据生成链。
10. 增加block级生成、重新估计metric的校准与fixed-metric条件校准对照；使用 `(1+k)/(Nsim+1)` 并给MC误差/置信界，报告Nsim。

验收：已知真值的覆盖率在MC误差内符合预定水平，近简并/失配场景能触发“不确定/无分数”；参考质量和候选排序对合理预声明分析范围稳健。失败则保留pilot诊断，停止绝对排名。

## 阶段 C：理论路线及失败判据

### C1 多态参考与受控系统误差（CPU先做）

谱表示 `C_k(t)=Σ_j a_kj [exp(-E_j t)+exp(-E_j(T-t))]`；共能级、通道依赖overlap符合固定源不同sink的结构，但有限T还需确认热贡献适用性。

- 比较受约束gap、多窗口多态、可辨识的共同质量；对signed cross correlator不强制所有overlap非负。
- prior必须在development模拟中选定，报告prior敏感性；不能借窄prior制造小误差。
- 模型平均仅纳入通过预测/覆盖检查的候选模型，报告within/between-model不确定性和排序稳定性。
- 使用同一配对resample传播reference、幅度及risk相关性，避免把质量系统误差独立叠加造成错计。
- 失败判据：m0由prior/边界/窗口决定，gap不识别，合理模型之间排名翻转；输出“不可排名”。

### C2 GEVP/变分参考（通常需新source测量）

原始论文：Blossier et al., [arXiv:0902.1265](https://arxiv.org/abs/0902.1265)。本轮阅读其原始摘要：支持相关矩阵GEVP及在适用条件下随能隙控制的渐近污染抑制；不保证本pilot短时间窗自动有效。

- 构造 `C_ij(t)=<O_i(t)O_j†(0)>`，求 `C(t)v=λ C(t0)v`；记录t0选择、metric谱和本征向量稳定性。
- 现有7条point-source/sink通道不是7×7相关矩阵，不能对7向量直接宣称完成GEVP。
- polynomial H组合或已有prop上的交叉收缩仍保持同一点源，不自动补齐不同source插入。
- 新source smearing/多次反演预算先做小矩阵与local对照，再扩维。
- 失败判据：矩阵非Hermitian超误差、负/近零metric modes、bootstrap mode交换、t0强敏感；缩小basis或判不可识别，不裁掉失败样本刷区间。

### C3 改用预测/信息目标（CPU设计，需新留出验证）

- 用完全development内部cross-fitting预测未拟合时间窗；或以固定模型下能量估计MSE/区间宽度并有coverage gate作为目标。
- 给出人工注入excited-state情况下的目标响应，避免kernel把晚窗幅度压近零或利用reference偏差。
- 不把有效质量平台“看起来平”当无偏证明；报告bias-variance及时间相关性。
- 失败判据：合成失配样本得到高分、缩小幅度或过强取消能game目标；暂停目标发布。

## 阶段 D：新GPU数据与可移植性

仅在A/B可验收、分析方案冻结后推进；需明确新的未观察validation IDs和数据授权。T16原validation只供历史回归。

1. 核实生成轨迹间隔、热化、HMC参数与独立性；block长度由autocorrelation证据定，不把5视普遍常数。新数据量通过CPU功效模拟确定，不空喊更多组态。本地只有生成日志/manifest，没有`data/`规范场、传播子缓存或文档引用的`pilot/hmc_generate.py`；完整重生产须先补齐对应版本的生成器和输入身份。验收包括力的有限差分、可逆性、步长与ΔH标度、独立起链和平衡检查；高接受率或plaquette单个lag不能替代这些验证。`Note.md`/旧运行报告的“冷启动必死”只可保留为某次配置/实现下的失败记录，不能作为HMC的一般理论结论。
2. 多source降噪必须先源内平均、再按configuration/block bootstrap；source数不能冒充独立配置数。
3. 先一配置12 RHS显式残差、identity及H^(2k) fast/generic对照；再小样本完整缓存、冻结、evaluate。
4. 新候选先测gauge covariance、线性、Hermiticity、全部立方旋转/反演和平移；generic实数输出检查不能证明全部物理条件。
5. 当前 `measure.py:41` 只寻找 `QUDA_PATH/lib/libquda.so`，找不到标unavailable；须实际解析加载库并记录hash，不能把unknown当充分provenance。
6. CuPy包名/平台兼容与QUDA实际后端分开检查；单rank限制明确保留，不能从kunshan档案推断本地CUDA或多rank可跑。
7. 记录gauge/source hashes、PyQUDA/QUDA/驱动/设备、精度、solver参数；setup、solve、residual-check、smear、IO、total分别计时。cache-hit时间不可与冷反演作性能比较。
8. 300s是完成后的合作式检查，10GiB仅CuPy pool，不是QUDA整体硬上限；若作为预算比赛需另做进程级资源控制。
9. 同步两条GPU路径在每个split至少一个配置，记录最大绝对/相对误差；现有verify-only只取首配置，不能声称全split验证。
10. 冻结reference、候选、统计spec和依赖后一次性打开新validation。失败照实输出null，不重新调窗口后叫盲测。

验收：输入可追溯、残差全通过、operator独立对照通过、reference预测/覆盖门控通过、配对区间可区分目标效应且系统误差不翻转结论。任何项失败保留负结果；不启动更复杂学习核来掩盖评估问题。

## 交接边界

本任务与 `optimize_gaussian` 共享propagator/评分链；先解决这里的reference身份和模型识别，再考虑学习核。与 `wilson_loop` 的共性是冻结、blocked bootstrap和留出设计，但其势平台不能直接用作pion能谱证据。

首个可交付PR应仅完成阶段A及CPU回归，保持所有原始results、submission、协议快照不变；随后单独交付阶段B诊断。直到获得新的受控数据与稳定reference，本任务最准确的结论仍是“流程和诊断已建立，改善物理信息提取的可信排名未建立”。

补充跨任务核对（主agent本轮执行）：14项CPU测试全通过；环境Python3.13.12、NumPy2.5.1、SciPy1.18.0、pytest9.1.1；CuPy/MPI/PyQUDA不可用，因此此结果不覆盖GPU测量。`agents/loop.py` 的prompt硬编码T16，直接ReferenceFit绕过两态选择；候选u需显式验证finite、sum=1、L1上限，validation身份/hash/IDs需要与主流程相同的完整性检查。阶段A应把此入口也纳入统一契约，并用越界/NaN/错误协议fixture拒绝。`Note.md`关于没有LLM的旧描述需要随后同步，但本规划不调用模型API。

### T32反射假警报的只读CPU复算

在仓库根目录运行；只读归档、不落盘，不依赖GPU：

```sh
PYTHONDONTWRITEBYTECODE=1 python -B - <<'PY'
import numpy as np
raw = np.load('results/pion_projection/s16t16_t32/development.npz', allow_pickle=False)['correlators']
assert raw.shape == (60, 7, 32)
def maximum_z(odd):
    b = odd.reshape(12, 5, *odd.shape[1:]).mean(axis=1)
    se = b.std(axis=0, ddof=1) / np.sqrt(12)
    return np.max(np.abs(b.mean(axis=0) / se))
print('legacy wrong:', maximum_z(raw[..., 1:8] - raw[..., 15:8:-1]))
T = raw.shape[-1]
for stop in (8, T // 2):
    t = np.arange(1, stop)
    print('correct t range:', t[0], t[-1], maximum_z(raw[..., t] - raw[..., T-t]))
PY
```

预期依次为274.2692780312892、1.4445846358937766、2.398144774908899。此修复与reference身份冻结同属第一批CPU修复；修复后T32参考仍因χ²与窗口漂移而不可评分。

## 评分重设计：先定义要估计的量，再决定能否给分

当前风险的目标可以定义为“指定样本量下，归一化相关函数估计器相对给定基态曲线的MSE”。
若 `qhat` 无偏估计真实 `q*`，则

\[
\mathbb E[(\hat q-1)^2]=\mathrm{Var}(\hat q)+(q_*-1)^2.
\]

因此当前 `Var_boot(q)+(qhat-1)^2` 在上述频率学MSE目标下，期望可能含两份估计噪声。
这不是所有解释下必然错误：若目标是条件于观测中心的bootstrap扰动风险，它是另一个合理但不同的量。
必须在schema写出estimand，不能继续把两者都叫“真实基态偏差”。
幅度拟合和reference不确定使简单无偏修正也不再自动成立；直接减variance可能负值且增加噪声。
建议以已知谱模拟比较当前plug-in目标、cross-fitted平方误差和有限样本修正，不先钳零宣布解决。

### 推荐路线：有认证门控的多参考保守改善证书

推荐优先保留物理目标，但把“绝对100分制”改为相对固定local或Gaussian的保守改善证书。
核心要求：独立开发数据能够支持至少一个可接受的基态参考；若没有，输出abstain。
当前T16/T32不具备这一新认证，不能立即重新包装出可信分数。
多个参考的包络仅表征所列集合敏感性，不覆盖集合外未知系统误差。

定义候选 `c`、冻结基线 `b`、开发时冻结的可接受reference集合 `M`。
每个reference有联合latent参数 `η_m=(E0, gaps, overlaps, covariance hyperparameters)`。
给定一个共同外层bootstrap重复 `r`，同时抽开发block与验证block。
从该重复的开发数据重拟合/抽样 `η_m^(r)`，用于同一重复内所有候选。
同一验证resample估计 `R_cm^(r)` 和 `R_bm^(r)`，保留其相关性。
不可为每候选独立抽reference mass，也不可把质量误差当独立对角噪声相加。

\[
D_{cm}^{(r)}=\log R_{bm}^{(r)}-\log R_{cm}^{(r)},\qquad
D_c=\min_{m\in M}D_{cm}.
\]

最差模型改善为正，才表示在这个预声明集合内一致改善；它不是基态正确性的证明。
不要直接对原始带噪risk比值取平均：分母接近零时极不稳定，且平均比值不等于比值的平均。
log改善便于成对分析，但本身不能消除零风险或模型错误。

最低可实施CI算法：

1. 每个模型用同一paired block draws得到 `D_cm` 分布；所有模型/候选共享draw索引。
2. 固定待比较候选数量J、模型数K；对每个候选每个模型给单侧 `α/(JK)` 下界。
3. 候选证书 `L_c=min_m L_cm`；union bound给有限比较族的保守同时覆盖目标。
4. 具体percentile/bootstrap方法仍是有限样本近似；用合成数据验证实际覆盖率，不声称union bound能修复bootstrap失效。
5. 若开发已经只冻结一个候选，J=1；若验证后从J个挑最大，必须计入这一步多重比较。
6. 不能把bootstrap中的 `min` 分位数未经非光滑选择校准直接叫严格置信下界。
7. 最终可显示 `improvement_lower_bound=exp(L_c)`；`L_c<=0` 报“未证实改善”。
8. 不推荐截为总是≥100的得分，因为它掩盖劣化；同时报告点估计、各模型结果和下界。
9. 若需要产品分数，采用有符号 `100*L_c` 并显示reference gate；它是证书刻度，不沿用旧分数可比性。

零/近零risk策略必须预注册：

- 非finite/非正估计风险不参与log计算，输出明确invalid或abstain，不丢重复。
- 若某模型baseline低于预定可分辨风险尺度，输出 `baseline_unresolved`，不报巨大改善。
- 可改估计有实际测量分辨率意义的正目标 `R+δ²`，但δ必须来自开发功效/anchor精度并固定到共同无量纲尺度。
- 不允许每候选不同δ，也不能把任意1e-12当物理正则化；改变δ时必须报告敏感性。
- 重复中出现风险无效的比例必须报告；超过开发预注册容忍值即abstain，不能条件于成功draw给窄CI。

reference集合与权重：

- `M`仅由development中预测检查、已知谱coverage、identifiability和物理适用性确定。
- 必须冻结模型列表、窗口、prior、协方差处理、接受准则和模型源码身份。
- validation不能删除“不利模型”，也不能加入一个有利模型改变主分数。
- 若有模型平均作为次级分析，权重只能development确定并冻结，说明是posterior概率、预测权重还是人为权重。
- 未通过coverage/预测检查的模型不能因权重大而获认证；两个错误模型的平均仍可能错误。
- `M`为空、所有模型不能识别E0、或独立anchor冲突，主分数为null。
- 若模型集合过宽导致无改善，结论就是未证实；不在validation缩窄集合“救分”。

### 可行替代一：固定共同尺度的cross-fitted shape prediction

用途是比较“在未拟合时间点预测ensemble mean correlator”的能力，不认证ground-state isolation。
可以在现有数据做流程研究，但报告必须叫shape prediction。
为了比较不同kernel，不能把候选自己的任意尺度C直接当共同目标。
建议预测固定anchor通道集合或预声明的标准化响应，标准化常数仅由训练fold确定并冻结。
候选表示用于预测同一个目标向量 `y`，基线与候选均在相同held-out blocks上评分。
这与原sink质量任务不同：它衡量表示的信息和可预测性，不应混称更好pion sink。

\[
S_c=\frac1N\sum_i (y_i-\hat\mu_c)^\top W_{\rm train}(y_i-\hat\mu_c),
\]

其中W是共同正定metric，只由训练fold中的固定anchor估计；不能由候选给出方差。
平方损失对条件均值是proper，候选无法通过报告巨大预测方差降损失。
如果评分是individual-block预测，它含有不可约噪声；这对共同目标的配对比较可接受，但不等于mean估计MSE。
若目标是验证ensemble mean，用其已知抽样协方差定义清楚权重和样本量；不能随意混用两类目标。

若允许候选输出概率预测，可用Gaussian negative log score：

\[
S_c=\tfrac12[(y-\mu_c)^\top\Sigma_c^{-1}(y-\mu_c)+\log\det\Sigma_c+d\log(2\pi)].
\]

logdet防止无限放大方差无代价；仍需positive-definite与特征值范围，且评分目标必须固定。
Gaussian log score只在声明的预测分布族内有相应解释；不自动给出正确tails或基态概率。
固定anchor和共同target防缩小candidate幅度game；若按candidate各自的零均值target评分，零kernel可能轻易获胜。
检查train/held-out mean、误差相关、invariance与不平衡block，不把折叠后的时间点当独立样本。

内部nested CV必须重走上游：

- outer训练fold重新选reference集合/窗口、拟合mass、幅度尺度、metric、候选超参数。
- outer held-out fold不能影响上述任何量，inner CV仅在outer训练数据中进行。
- 已由完整60组态拟合的reference_bootstrap不能直接给outer folds共用；这会泄漏。
- 按configuration blocks拆分，source、time和basis维度不得随机切分充当独立验证。
- 现有已公开validation仍仅用于历史诊断；内部CV改善不恢复新盲测身份。

### 可行替代二：已知谱质量估计MSE与coverage

在可控制生成分布中，优化最终能量估计而非q接近1：

\[
R_c(N)=\mathbb E[(\hat E_{0,c}(N)-E_0)^2],\quad
\mathrm{Cov}_c=\Pr[E_0\in I_c].
\]

固定N、generator族、noise/cross-channel covariance、excited spectra和分析预算。
候选与基线使用相同模拟随机数和block，比较配对energy error²，附MC区间。
必须包含非Gaussian噪声、autocorrelation、signed overlaps、弱gap、有限T和模型失配反例。
coverage gate与区间宽度共同报告，不能只看窄CI；能量偏差明显则停止认证。
训练generator和测试generator分离；冻结测试seed集合并避免候选读取真值。
优点是直接知道真实基态，反作弊与bias-variance诊断明确；局限是只认证生成族，不能代替真实QCD数据。
真实anchor可来自独立高统计、多source、相关矩阵/长时稳定谱分析，仍需独立误差和系统误差审计。
anchor必须不被当前候选训练和reference选择使用；若共享配置，显式纳入联合相关而不是宣称独立。

### 可行替代三：质量约束后的成本效益

先通过E0 bias/coverage或独立anchor一致性门控，再衡量达到目标精度所需资源。
定义固定目标 `|bias|<=b_max`、coverage门限和 `SE(E0)<=s_target`。
通过多个预声明N拟合学习曲线，仅在覆盖数据范围内估算达到目标的 `N_c*`。

\[
G_c=\log\frac{C_b(N_b^*)}{C_c(N_c^*)},\quad
C_c(N)=C_{{\rm setup},c}+N C_{{\rm per-config},c}.
\]

计入propagator solve、额外sources、kernel application、IO与必要analysis；报告是否可摊销共同反演。
若固定point propagator是共享前提，可同时给“含反演总成本”和“增量sink成本”，不要挑有利口径。
设备、精度、residual、cache状态、并发策略固定；用重复计时给误差，不用一次walltime排名。
先设质量约束避免快速但有偏估计获胜；不建议直接用原risk×秒，因为量纲与统计目标混杂。
若目标精度在观测样本范围内未达到，报告unresolved，不外推任意巨大加速。
CPU阶段只验证学习曲线算法；GPU真实性能仍需同硬件新测量。

### 三阶段实施交付与验收

**阶段S1：评分定义和独立合成测试，CPU。**

- 新模块建议 `tasks/pion_projection/scoring.py`，纯函数接口 `evaluate_metric(blocks, frozen_spec, reference_draws)`。
- reference接口返回联合draws和model ID，不只masses；保留candidate共享的draw_id。
- `score_spec.json` schema建议字段：version、estimand、target、baseline_id、accepted_models、model_weights、train_ids_hash、anchor_id、metric_hash、risk_floor_policy、alpha、comparison_family、bootstrap_plan、cost_policy。
- 输出 `metric_results.json`：status、failure_reasons、per_model_risk、paired_log_improvement、simultaneous_lower_bound、invalid_draw_count、sample_information、source_hashes。
- 合成生成器建议独立 `tests/pion_spectra.py`，不把真实results改成fixtures。
- 单元/统计测试覆盖：缩放/负权重、零kernel、方差膨胀、近零baseline、共同reference相关、失配模型、重复block、CV上游重拟合、模型集合变化拒绝。
- 验收：已知谱覆盖和假改善率有MC置信区间且符合预注册容忍范围；未知reference时必abstain；不得仅因测试全绿宣布真实数据评分有效。

**阶段S2：历史数据诊断和功效设计，CPU。**

- 输出新目录 `results/pion_projection/score_diagnostics_v2/`，保留旧档案不变。
- 先输出 `inventory.json` 和 `fold_plan.json`，绑定IDs/hash与12/6 block信息；不得将1000 bootstrap draws称1000独立样本。
- 输出 `synthetic_calibration.json`、`historical_sensitivity.json`、`power_plan.json`；区分实测档案、CPU重算、合成结果。
- 真实数据仅比较旧目标的reference敏感性、score选择稳定性和shape预测流程，不标新认证通过。
- 利用功效模拟估算新开发/新validation与anchor的需求，报告假定effect size、相关时间和计算成本；不凭6个validation blocks断言精确覆盖。
- 停止条件：所有合理模型仍失配、CI无法校准或候选可game目标；停在diagnostic_only。

**阶段S3：独立anchor与新validation，GPU另立run。**

- 测量前冻结 `score_spec.json`、reference factory版本、候选、anchor隔离方案、比较族和新IDs。
- 输出完整 `run_manifest.json`、测量provenance、reference joint draws、paired draws、quality gates、成本记录和主/次指标。
- 主要终点只一个：推荐多参考保守改善证书；shape预测、模拟MSE、成本为清晰标注的次级终点。
- reference未认证则主终点null，允许仍发布shape预测结果但不得转换为ground-state结论。
- 验收：质量门控、独立anchor一致性、预注册同时CI、预算和数据完整性均通过；证书下界>1才称在冻结模型集合内有改善。
- 任一分母不可分辨、模型集合空、anchor冲突或coverage失败就abstain；负结果是合法交付。

统计背景：[Gneiting–Raftery原文作者存档](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf)。DOI入口一度403，随后已读取作者提供原文的§4（log score，式19；均值平方误差，式23）及§7的预测比较讨论。原文支持proper预测损失的构造；平方损失识别均值，不能严格识别整个预测分布。这不是本pilot已校准的证据，实际应用仍须按S1验证。

### 当前数据能立即完成的判别，及新指标的物理含义

本轮只读重算`reference_systematics.json`：固定权重时，tuned/SLSQP风险比在单态/两态下分别为1.630124/0.971029。
取log后为0.488656/-0.029399；映射为`200 R_baseline/(R_baseline+R_candidate)`后为123.958/98.530。
两种显示方法仍然翻转优劣；压缩数值幅度不等于改善评分稳健性。
上文`R_cm`必须绑定明确的estimand及其经过校准的估计方式。如果暂时沿用旧risk，证书只认证“冻结条件loss的改善”，不能命名为真实E0的MSE改善。
对新的物理主榜，更直接的目标是下节的能量误差，而不是仅让旧q-loss数值稳定。

本轮还执行了一个**合成评分反例**：给定E0=0.8和E1=1.1，分别构造纯基态与纯激发态cosh通道；给它们相同的小相对噪声。
当reference误认E1为基态时，纯激发态risk=4.69873e-6，而真正基态risk=0.458796，且两者幅度Z均远大于门槛。
改用正确reference E0后，基态risk=4.69873e-6，纯激发态risk=8.71858。
这个反例不声称真实候选已经做到了完全消去基态；它证明“高SNR、非零幅度、接近某条cosh”不足以识别那条cosh是不是基态。
后续所有新评分必须保留此反例：若没有区分真基态的信息，允许拒绝认证，不允许将错误态判为物理胜者。

以下只读命令可复现；不改源码、不需要GPU：

```sh
python -B - <<'PY'
import json, numpy as np
from pathlib import Path
from tasks.pion_projection.statistics import risk, shape, blocks, bootstrap_indices
p = json.loads(Path('tasks/pion_projection/protocol.json').read_text())
rng = np.random.default_rng(20261118)
t = np.arange(9)
noise = rng.normal(size=(60,9))
C = np.stack([shape(m,t,16)[None,:]*(1+.01*noise) for m in (.8,1.1)], axis=1)
data = blocks(C,5)
index = bootstrap_indices(12,1000,987)
for m in (1.1,.8):
    for name,w in [('ground',[1,0]),('excited_only',[0,1])]:
        result = risk(data,w,m,np.full(1000,m),index,p)
        print(m,name,result['risk'],result['amplitude_z'])
PY
```

### 直接面向能量误差的后续主指标：独立anchor与配对损失差

如果目标是“在给定成本下更准确地提取E0”，建议在有可靠anchor后，将**能量估计误差**作为下一版物理主终点。
这比永远以某个reference的归一化曲线距离为主指标更贴近任务目的；当前数据不足以立即执行该认证。
为每个冻结候选使用预声明的能量提取程序，得到`Ehat_c`；所有候选使用相同数据量/预算口径。
anchor `Ehat_*`由独立高统计谱分析给出，保留其统计、模型、窗口与有限T系统误差。
在独立、无偏anchor且相同目标E0的条件下，

\[
\mathbb E[(\widehat E_c-\widehat E_*)^2]
=\operatorname{MSE}(\widehat E_c)+\operatorname{Var}(\widehat E_*).
\]

因此可使用配对的误差改善量

\[
\Delta_c=
\frac{(\widehat E_b-\widehat E_*)^2-(\widehat E_c-\widehat E_*)^2}
{\tau_E^2},
\]

其中`τ_E>0`是预先规定的有实际意义的能量精度，单位与E一致；同一anchor方差在期望差中抵消。
这里采用损失**差**，避免接近零的基线风险作分母；不能在平方误差之外再无定义地重复加估计方差。
单个batch的Δ是噪声估计，不是已知MSE差：需在已知谱模拟/独立重复batch中校准推断，并在真实数据上对候选、基线和anchor联合传播不确定性。
配对bootstrap用相同validation blocks，anchor数据独立重采样；同一anchor draw供所有候选使用。
如果anchor来自同一批配置，上式的独立性条件不成立，必须纳入cross-covariance，不能直接宣称方差抵消后的无偏MSE差。
anchor若有偏差，其交叉项也不会自动抵消；需对可接受anchor模型给同时保守下界，发生冲突就abstain。
事后用全部validation选择能量窗口或模型会使这一指标同样失效；分析器选择必须在开发阶段冻结。
CI覆盖、错误态反例、ground overlap可识别性和预算门控通过后，Δ的校准单侧下界大于预定最小收益才认证改善。

时间顺序：**现在**用多参考敏感性与保守比较改进历史诊断；**取得可信独立anchor后**将能量误差改善设为唯一物理主终点，旧q-loss作为次指标，不并列挑选有利的主终点。
如果研究目标是算符平台形状而不是最终能量，也可以继续以q-loss为主，但必须显式更名和限定结论。
模型不确定性处理的原始方法入口：[Jay–Neil, 2008.01069](https://arxiv.org/abs/2008.01069)与[Neil–Sitison, PRD109 014510](https://journals.aps.org/prd/abstract/10.1103/PhysRevD.109.014510)。本轮读取其摘要，分别支持将模型/拟合范围不确定性纳入平均，以及研究不同信息准则权重；它们不证明上述新指标在本pilot已经校准。
