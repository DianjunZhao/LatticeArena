# wilson_loop：CPU 验收结论与下一阶段

### 2026-11-26 本 checkout 回归核验

新增 raw-matrix snapshot projection reader 后，当前 PR #6 worktree 的完整 Wilson 测试文件集 `tests/test_wilson*.py` 为 **109 passed**，完整 repository CPU suite 为 **336 passed**（2026-11-26）。Wilson 测试覆盖 lane contract、force-budget propagation、Markov 支持界、finite-`N_t` 代数、toy/randomized fixtures、C/F task adapter 的默认 source-byte fail-closed 行为，以及 GEVP 截断、overlap 对象和 raw-matrix snapshot 投影诊断；只确认软件和指定 toy 公式，不提供 C/F measurement、独立 q/h/x/GEVP/thermal receipt 或 coverage/calibration 证据。新 reader 使用同一 immutable `SourceByteSnapshot`，并在 `numpy.load` 前做 NPZ 资源预检；它只从 synthetic cross-correlator 生成投影 correlator，不做谱拟合、不产出 q 区间，也未接入物理 gate。Wilson adapter 默认要求 source root 与显式路径 map，source bytes 匹配后最多将 gate 推进到 draft；它仍未接入实际生产 RunSpec/source reader。PR #5 的共享 [`core/evidence.py` metadata contract](https://github.com/Greyyy-HJC/LatticeArena/blob/c7a4c9b2c8858d1fdf3499966a2223c45427bbc6/core/evidence.py)包含单 envelope 和 multi-envelope bundle gate；PR #5 的 Pion adapter/诊断另行保留。字节一致不认证真实来源、reviewer 独立性或物理内容。2026-11-26 查询 GitHub 时 PR #6 为 OPEN、`MERGEABLE/CLEAN`，未报告 checks；这只是当时状态。现有图文分析和 lane-specific 未决项如下文，仍保持 `NOT_READY/UNCERTIFIED`、F=`GROUND_STATE_FORCE_UNCERTIFIED`、`physical_score=null`。

### 2026-11-26 F-lane raw cross-correlator snapshot → GEVP 投影诊断

新增 [`f_lane_raw_matrix_snapshot_diagnostic.py`](f_lane_raw_matrix_snapshot_diagnostic.py) 与[图文报告](f_lane_raw_matrix_snapshot_diagnostic_20261126_v1/README.md)。reader 要求同一 `SourceByteSnapshot` 中严格绑定 manifest 与 NPZ；检查 captured-byte digest、校准 split、manifest/NPZ hash、精确的 operator/R/time 顺序、矩阵 shape/dtype/有限性/Hermiticity，并在 `numpy.load` 前通过 `core.npz_safety.validate_npz_payload`。每个 operator/R cell 用 ensemble mean 的 `C(t0=1), C(td=2)` 解一次 principal GEVP，以 `v†C(t0)v=1` 归一化，再用同一固定向量投影每个 block 的 `C_ij(R,t)`，返回投影 correlator 和条件数。流程为：`captured manifest+NPZ -> schema/hash/split/axis/资源检查 -> mean C(t0),C(td) -> fixed GEVP -> block projection -> CSV/图`。

图中 24 个四态 forward-spectrum synthetic blocks 的 6 个 operator×R cell 均生成 `t=1..7` 投影曲线；阴影是确定性 toy 的 10–90% block spread，只作描述，**不是置信区间或独立性证据**。分母 planned/valid/failed/abstained：source files `2/2/0/0`；operator×R 投影 `6/6/0/0`；operator×R×time 值 `42/42/0/0`；物理 q/interval/certification `1/0/0/1`。报告同时记录 `physical_score=null`、`GROUND_STATE_FORCE_UNCERTIFIED`。

重要缺口被此接线具体化：当前 repo 没有 raw cross-correlator exporter，现存不同 kernel 的对角 Wilson-loop 序列不能推回缺失的非对角 `C_ij`。manifest 规定生产 exporter 必须实际测量并固定 sink/source 指标及 smearing basis；不能把对角元素复制成矩阵。新 reader 也不拟合 state overlaps/gaps，不传播 paired interval，不处理有限-`N_t` backward/thermal `h`、mixed `x`、谱模型误差或 force/reference uncertainty。定向用例 **8 passed**，Wilson 全集 **108 passed**，全仓 CPU suite **335 passed**。合成输入与图只验证 schema、hash/split fail-closed 和线性代数；不可用于估计生产污染或接入 gate。

**接续次序：**先由独立 reviewer 审 `C_ij` 定义、cross-term 生产测量与 `td` 候选，再开发有统计协方差的 GEVP/state-overlap fit 和成对 interval reducer；coverage 至少覆盖 exact three-state recovery、omitted-state bias、近简并/近奇异矩阵、finite-`N_t` 双向谱、small `Z_0(v)`、bootstrap 与覆盖率。随后才把真实同 snapshot raw matrix/fit receipts 接入 q-bound reader；仍须另有 matched-`N_t=32` thermal、mixed-sector、spectral truncation、reference-force 下界、独立 coverage/review 与数据授权。完成这些以前维持 `NOT_READY/UNCERTIFIED`、`GROUND_STATE_FORCE_UNCERTIFIED`、`physical_score=null`，不读封存 split、不启动 GPU/QUDA。

### 2026-11-25 当前接手：C/F 方法默认已提出，独立证据和认证门仍未完成

用户已选择保留两个不同 estimand：有限-$T$ Creutz 和基态离散静态力；随后要求执行者自行提出剩余规则。建议默认值已登记在 [`lane_contract_v2.json`](lane_contract_v2.json) 的 `selected_protocol` 与 `common` / `lanes` 草案映射中，状态仍为 `DRAFT_NOT_READY` / `METHOD_DEFAULTS_SELECTED_EVIDENCE_NOT_READY`。本次完成数据-free 映射，并在[结构检查器 v9](../../results/wilson_loop/lane_contract_diagnostic_20261125_v9/README.md)列出当前剩余字段；这不等于独立审阅、生产数据授权或物理认证。下方早期“等待选择 R/T/kernel/阈值”的说法由本节替代。

### 2026-11-25 F-lane q/h/x 到力级误差预算的传播已补齐（纯代数）

此前合同把 `q/h/x` 的 `1.5%/1.5%/1.0%` 与力级系统误差预算写在相邻字段，但没有明确这些百分数是逐 loop corner 上限，还是完成 stencil 传播后的力级上限。这个区别会改变结论。新 helper [`force_budget.py`](force_budget.py) 对两种 kernel、`R=2,3`、`t,t+1` 的 8 个带符号 loop corner 使用

```text
delta_k(R,t) = log(1 + q_k + h_k + x_k)
|Delta_R Delta_t delta_candidate - Delta_R Delta_t delta_reference|
  <= sum_over_8_corners delta_corner
  <= sum_corner log(1+q) + sum_corner log(1+h) + sum_corner log(1+x).
```

因此将 `1.5%/1.5%/1.0%` 明确解释为**相对正 reference-force 同时下界的、传播后的 q/h/x 力级预算**。若某个分量在 8 个 corner 都用同一 raw bound `c`，要满足分量预算 `epsilon`，输入必须满足 `c <= expm1(epsilon*f_L/8)`，其中 `f_L` 是独立统计下界；不得把力级百分数直接填成每个 loop 的 q/h/x raw bound。

[图文诊断](../../results/wilson_loop/force_budget_propagation_cpu_20261125_v1/README.md)扫描 50 个纯公式 `f_L` 情景，分母 `50/50/0/0`。在仅用于演示的 `f_L=1` 下，若误把每个 corner 的 raw bound 设为 `q=h=0.015`、`x=0.01`，传播后分量力界分别为 `0.1191`、`0.1191`、`0.0796` 倍 `f_L`，不是目标 `0.015/0.015/0.01`；加上 `1%` 模型截断和 `5%` 统计半宽后，保守总上界为 `0.3778 f_L`，高于 `10%` 门。按力级预算反解时，`f_L=1` 对应 raw corner 上限为 `q=h=0.00187676`、`x=0.00125078`。这些是假设算术，不是 Wilson 输入。合同与 `empty_contract()` 已同步写明 8-corner 布局和反解公式；专测 `29 passed`。

该检查不补出 `q/h/x`、正 reference-force 下界、谱模型截断或统计覆盖收据；物理证据分母仍为 `1/0/0/1`，Lane F 仍 `GROUND_STATE_FORCE_UNCERTIFIED`、`physical_score=null`。新模块及合同定向测试为 **29 passed**，当前 `tests/test_wilson*.py` 全集 **62 passed**。下一步只能用独立 receipts 填入逐 kernel/R/time 的 raw envelopes，经该传播器生成 force-unit bounds，再由 reviewer 核查谱假设与数据来源。

### 2026-11-25 C-lane 条件 Markov 支持界：替代方案已量化，仍不足以认证

[图文敏感度报告](../../results/wilson_loop/c_lane_markov_support_bound_20261125_v3/README.md)给有限-$T$ Creutz 提出一个与 block bootstrap 不同的条件路线：若每个 saved configuration 的 observable 确为 `ReTr(U_loop)/3∈[-1/3,1]`，先把四个 loop means 分别映射到 `[-1,1]`，用 Paulin corrected arXiv v5 Theorem 3.11 / Eq. (3.25) 做四个双侧 simultaneous marginal intervals（`F=4, alpha_C=0.025`），再将正值置信盒通过四项对数的单调性传播为 Creutz 区间。任一 loop-mean 下界不正或 half-width 超过 `0.02` 即 `ABSTAIN`。此处矩形联合区间忽略跨 loop 协方差，优点是覆盖论证明确，代价是很保守。

界限依赖 saved-configuration Markov chain 的齐次性、唯一平稳分布、伪谱隙正下界和测量支持域；HMC trajectory 间隔、经验自相关时间与 bootstrap draw 数都不能代替这些收据。当前 schema 没有生产 normalization、该 saved chain 的 `gamma_ps`、stationarity/burn-in TV 或独立 review receipt。本报告没有读取 loops 或其他 split，96 个纯公式 scenario 的分母为 planned/valid/failed/abstained=`96/7/0/89`；valid 仅表示假设下数学区间达到精度，并非数据结果。即便取最有利 `gamma_ps=1` 且四个样本均值 floor 达到 support 上界 1，半宽 `0.02` 仍需 222,616 个配置；若 floor 为 0.5 则需 3,343,119 个。对 `gamma_ps=0.1`，相应样本数为 2,226,156 与 33,431,187。故此路线不能支持当前小样本精度，也不替换提议的主 bootstrap 方案；它提供的是严格的条件备选和停止规则。若后续收到独立可审阅的 gap receipt，才值得评估更紧的真方差上界或 nonstationary-TV 版本；不能用当前 AR(1)/finite-dependence toy 推出 gap。

文字流程：`normalized bounded loop traces + saved-chain gamma_ps receipt -> four simultaneous mean boxes -> positivity check -> monotone Creutz interval -> 0.02 precision gate or ABSTAIN`。来源：[Paulin corrected arXiv v5](https://arxiv.org/html/1212.2015v5)。

实现回归：[Markov support-bound 单元测试](../../tests/test_wilson_c_lane_markov_bound.py)加当前 lane-contract 测试共 **26 passed**；图文报告的 hash 清单 **6/6 匹配**。这些检查覆盖公式、支撑域映射、对数传播、非正下界弃权和 no-data 报告身份，不检验实际链的 gap 或区间覆盖。

### 2026-11-25：C/F canonical mapping 与误差合同审计

`empty_contract()` 现在把已选的 C/F primary、显式四角 stencil、alpha allocation、精度目标或相对精度提案和谱计划映入 canonical `common` / `lanes`。proposal action/source descriptors 以 `_proposed` 标识；split、paired-block、独立 review、q/h/x、传播后的力误差和实际数据 receipt 仍为 null。检查器结果是 C lane `planned/valid/failed/abstained=1/0/1/0`、F lane `1/0/1/0`；C 留 3 个结构缺项，F 留 26 个，精确原因见 v9 JSON/README。另有 5 个物理运行阶段均 abstain (`5/0/0/5`)。完整的 8-fixture 结构表与分母为 `16/7/9/0`；没有新增 Wilson measurement。

审计发现并修正一个合同缺口：旧 F validator 要求 `finite_a` / `finite_volume` bounds，却漏掉用户选定的 `spectral_model_truncation` force-level bound。当前 primary 是固定格距、固定体积下的无量纲 lattice force `a_s a_t F`，连续极限和无限体积极限不属于它的 estimand；因此 schema 不应把这两种外推误差强制塞进当前预算。validator 现要求四个与选定 `5%` systematic budget 一致的 force-unit 项：excited-state、finite-$T$ thermal、mixed-sector、spectral-model truncation；24 个 q/h/x 输入 cell 和 4 个 model cell 仍按总计 28 个校准单元做 family-wise 分配。只有以后声明 continuum 或 thermodynamic estimand 时才另加相应外推界。因 primary 输出保持格点无量纲，合同明确允许不提供物理 $a_s,a_t$ 转换；若以后改为物理单位输出，则必须重新要求 spacing 及单位收据。

这轮只核对了合同/检查器结构，不是独立 reviewer 的物理签署。v9 中 synthetic C+F fixture 可达 `CONTRACT_COMPLETE_REQUIRES_HUMAN_REVIEW`，但真实 C/F lane 仍是 `NOT_READY`，`physical_score=null`，F 仍 `GROUND_STATE_FORCE_UNCERTIFIED`。图文报告区分 proposed caps 与 measured force bounds，不把 1.5%/1%/5%/10% 设计门伪装成数据。

- **共同设计：**16⁴、Wilson β=6、周期边界、`N_t=16`；提议 stout `rho=0.10,n=5` 为候选核，APE `alpha=0.4,n=5` 仅作弱场匹配描述对照，不声称非微扰 smear radius 等价。两个 co-primary lanes 在总 family-wise error probability `alpha=0.05` 下各分配 `0.025`；C lane 用双侧区间，F lane 再把统计 `0.0125` 分给双侧力差区间与单侧正 reference-force 下界、另 `0.0125` 给 systematics family。10,000 circular block-bootstrap draws，主 block length 5、敏感度 2/10，区间取 block-length hull。若任一必需 loop mean 无效则该 draw 无效；无效比例 `>1%` 或精度不达标即 abstain。
- **Lane C：**primary 提案为绝对有限时 `chi_stout(R=2,T=5)`，公式 `-[log Wbar(3,6)+log Wbar(2,5)-log Wbar(3,5)-log Wbar(2,6)]`；先对同一 paired configurations 求四个 loop means，再对正均值取 log；无量纲 half-width 目标 `0.02`。[`C-lane development preflight`](c_lane_open_development_diagnostic_20261125_v1/README.md)只重算已打开的 D0–99：点值 `0.10443172`，30,000/30,000 bootstrap draws 有效，L=2/5/10 区间 hull `[0.09531340,0.11350806]`、half-width `0.00909733`，通过数值 precision/invalid-draw preflight。报告附区间图、输入身份与文字数据流；同一 D0–99 已用于开发，故这不是独立 coverage calibration、confirmation、plateau 或 ground-state 证据，bootstrap 覆盖率也未建立。
- **Lane F：**primary 提案为 `R_mid=2.5` 的 stout-minus-identity ground-state force，`[U0_stout(3)-U0_stout(2)]-[U0_identity(3)-U0_identity(2)]`，单位 `a_s a_t F`。谱方案为 3×3 GEVP（identity/APE/stout，`R=2,3`，`t0=1,td=2`，窗口 `[3,7]`、`tmin=3,4,5`、2/3-state checks）并要求 matched `N_t=32` 热污染证据。相对正 reference-force simultaneous lower bound，提出 `q≤1.5%`、热污染 `h≤1.5%`、混合 `x≤1%`、谱模型截断 `≤1%`，systematic sum `≤5%`，statistical half-width `≤5%`，linear total `≤10%`；24 个 q/h/x 与 4 个模型项共 28 个 family-wise cells。全部独立谱/污染 receipts、reference 下界、common action/source/split hashes 和 physics review 仍为 null，因此 `GROUND_STATE_FORCE_UNCERTIFIED`。

**kernel 身份交叉核验（开发包层面已闭合，生产门仍开）：**合同 canonical ID `spatial_stout_rho0.10_n5` 与 D0–99 preflight 的显示名 `stout_rho0.1_n5` 通过结构化描述交叉核验为同一开发算符：`kind=stout, rho=0.1, steps=5, spatial links`。开发 protocol 明确记录参数；其 pinned `stout.py` / `kernels.py` SHA-256 与 Git 中的源代码 blob 一致；实现把 `name` 仅作为允许的 metadata，不用于运算分派。逐项证据、源码空间约定与限制见[身份交叉核验](../../results/wilson_loop/kernel_identity_crosswalk_20261125_v1/README.md)。这只解除历史 D0–99 preflight 的命名歧义；缺少独立 production-link/source/action receipt、confirmation 数据与 physics review，所以合同 operator/comparison gate 仍 abstain，状态仍为 `DRAFT_NOT_READY`、`physical_score=null`。APE `alpha=0.4` 与 stout `rho=0.1` 仍只是弱场首阶配对，不代表非微扰 smear-radius 等价。

**已完成但只支持方法/接口的诊断：**[`lane_contract_diagnostic_20261125_v8`](../../results/wilson_loop/lane_contract_diagnostic_20261125_v8/README.md)把 16 个结构 fixture（planned/valid/failed/abstained `16/7/9/0`）与五个物理阶段 abstain（`5/0/0/5`）分开，图文说明哪些字段缺失；[`finite_nt_randomized_stress_20261123_v1`](../../results/wilson_loop/finite_nt_randomized_stress_20261123_v1/README.md)在 4,000 个合成正谱样本上核对有限-$N_t$ 四点恒等式/包络，最大代数残差 `3.20e-14`，不代表物理污染覆盖；[`reference_window_open_development_20261125_v1`](reference_window_open_development_20261125_v1/README.md)归档 D0–99 的 A/B point-max `2.0965` 与 C centered/uncentered joint-q95 `2.7408/4.0844` 对照候选阈值 2.5，但阈值未校准且原 runner 未归档，所以不能冻结 reference 规则。

**新增覆盖率压力诊断（2026-11-25；合成方法校准，不是物理证据）：**[`c_lane_block_bootstrap_coverage_stress_20261125_v3`](../../results/wilson_loop/c_lane_block_bootstrap_coverage_stress_20261125_v3/README.md)用已知真值的四变量 lognormal AR(1) loops，扫描 adjacent-configuration `rho=0,0.3,0.6,0.8,0.9` 和 log-loop SD `0.10/0.35`；每个 `(rho,SD)` cell 有 240 个独立数据集、每个 L 有 800 draws，共 2,400 datasets，图给出覆盖率 Wilson MC intervals 与 median half-width。现行 L=2/5/10 hull 在 `rho=0.8/0.9` 的经验覆盖率分别为 `0.863/0.779`（SD 0.10；95% MC intervals `[0.813,0.900]` / `[0.723,0.827]`）和 `0.879/0.762`（SD 0.35；`[0.832,0.915]` / `[0.705,0.812]`），远低于名义 97.5%；把敏感度扩到 L=20/30 后仅升到 `0.875/0.812` 与 `0.900/0.792`，95% MC intervals 仍未接近名义覆盖。低相关 cell 也出现轻微 undercoverage；在 SD 0.10 下 half-width≤0.02 仅 `rho=0` 的 34/240 和 `rho=0.3` 的 2/240 达到，其余 cell 为 0/240。所有 loop means 正且分母为 planned/valid/failed/abstained=`2400/2400/0/0`。结论仅限所声明模型：block-length hull 和增加 draw 数不能替代实际依赖界；延长 block 有有限改善但没有解决高相关失覆盖。因此不改 `lane_contract_v2.json` 中已提的主 L=2/5/10 规则，也不据此估计真实 HMC rho。

**替代区间方法对照（2026-11-25；同一合成样本种子）：**[`c_lane_interval_alternative_coverage_20261125_v1`](../../results/wilson_loop/c_lane_interval_alternative_coverage_20261125_v1/README.md)在 2,400 个同分布样本上比较已知-rho 协方差 delta benchmark、Newey–West HAC bandwidth 5/10/20/30 和 stationary bootstrap mean-block 5/10/20；图示 coverage Wilson MC intervals 与 half-width。高相关 `rho=0.8/0.9` 时，已知参数 benchmark 覆盖率约 `0.975–0.988`；但它知道真实 rho/log-scale 且对非线性 Creutz 只用 delta 近似，不能部署，且低噪声 iid cell 覆盖率 `0.954`（95% MC `[0.920,0.974]`）也低于 nominal。HAC 在 `rho=0.9` 的最佳 bandwidth 覆盖率仅 `0.812`（SD 0.10）/`0.796`（SD 0.35），stationary bootstrap 的最好结果分别 `0.767/0.767`，对应 MC 区间均远低于 0.975；各自区间虽然比 covariance benchmark 窄，却不能支撑 nominal coverage。每个 method 的 planned/valid/failed/abstained dataset 分母为 `2400/2400/0/0`。因此当前被测的非参数区间都未跨越长相关假设场景的 calibration gate；不挑最有利 bandwidth/block，也不更改 C lane confirmation protocol。

**下一步：**(0) **已完成（PR #6）**：Wilson C/F task adapter 将 C 的四 loop means / chain support / gap-TV metadata 与 F 的 propagated force-unit q/h/x/spectral/thermal envelopes 分开映射到 `core/evidence.py`；缺项进入 `RunState.abstained`，完整 metadata/denominators 最多到 `draft`，不同 chain ID 不被解释为独立。(1) canonical stout ID 的开发包映射与 `selected_protocol -> common/lanes` 结构映射已经完成；独立 reviewer 仍须检查 `chi` 符号、loop 索引、force stencil、单位、边界、action/static-source 与两 lane alpha 分配，并审阅 4 项 force-level systematic bound 的传播和是否遗漏/重复计数，不得将两个 estimand 合并。(2) 覆盖校准的 AR(1)、有限依赖、颜色类 empirical-Bernstein 与 Markov 支持界报告已完成：不能只增加 draws、调 bandwidth/block，或假设一个未收据化的 gap；在没有独立、可证明的生产依赖 envelope / saved-chain `gamma_ps` 下界和 loop 支持域时 C lane 继续 `ABSTAIN`。不要重跑已完成 synthetic DGP；只有新证据能改变 release 可行性时，才做不同的纯 CPU 方法诊断。(3) 对 C lane 取得独立、获授权 calibration package 后再估计 precision/coverage，随后才冻结 confirmation。(4) 对 F lane，补独立 3×3 谱/overlap 与 matched-`N_t=32` 输入，逐项形成 q/h/x 和 model-truncation 上界、转换到力单位并给 simultaneous intervals；没有正 reference-force 下界即 abstain。(5) 任何新数据/设备运行前都需相应 owner 授权；不访问 gap、validation、shared holdout、confirmation 或 GPU/QUDA。所有新增诊断须带图或可复查文字，列 planned/valid/failed/abstained 分母与失败原因。维持 `NOT_READY/UNCERTIFIED`、`GROUND_STATE_FORCE_UNCERTIFIED`、`physical_score=null`，本 TODO 保留。

### 2026-11-25 C-lane 颜色类 empirical-Bernstein 续查

[新诊断](../../results/wilson_loop/c_lane_colored_empirical_bernstein_20261125_v1/README.md)在已声明 Gaussian-copula Beta moving-sum 合成 DGP 上加入 Maurer–Pontil Theorem 11 颜色类 empirical-Bernstein，并扫描 `n={100,500,2000,5000}`、`m={0,5,10}`，每个参数 cell 250 个 paired-seed datasets。定理适用于相互独立但可不同分布的有界变量；本模拟中 `index mod (m+1)` 的每个 loop-coordinate 色类由不重叠创新构成独立样本。它仍条件依赖事前正确的色图与 support；真实 HMC 的 `m` 未知，不能把这个色图移植到生产。

每种方法 planned `12000` 个 dataset。颜色类 empirical-Bernstein 有 `1426` 个有限区间、`10574` 个触零无界区间；有限区间在该合成网格中 `1426/1426` 覆盖真值，逐 cell Wilson Monte Carlo 区间见 CSV（最小样本 cell 的区间很宽）。Graph-color Hoeffding 为 `0` 个有限、`12000` 个无界。**两者都没有 precision pass：valid/failed/abstained=`0/0/12000`，half-width `≤0.02` 通过数 `0/12000`。**有限的 empirical-Bernstein 区间只出现在 `m=0,n≥2000` 的 cell；其 cell median half-width 约 `1.025–5.144`，远高于 `0.02`。图显示有限区间覆盖、release fraction 和半宽随样本数变化。

结论：方差自适应能在这个合成 DGP 的部分弱依赖、大样本 cell 避免 Hoeffding 触零，但并未形成可用 C-lane 校准，也不改变主协议。下次不要仅扩充相同 DGP 的样本数；只有拿到独立审阅、事前可证明的生产依赖 envelope 和支持域后，才可评估这些 conditional bounds。无此输入时继续 `ABSTAIN`。理论依据：[Maurer & Pontil (2009), Theorem 11](https://arxiv.org/abs/0907.3740)。

### 2026-11-22 历史交接：两条 lane 已选，数值默认见上方 2026-11-25 提案

本段有限-$N_t$推导与候选物理界仍是有效理论背景；其中“暂不选 R/T/kernel”已由上方的 method-default proposal 更新。不得把 D0–99 development 诊断升级为确认性选择、基态认证或物理 score，也不得重跑已经归档的窗口 bootstrap、force 图、power-cost 或同一 toy。不得启动 GPU 或打开 D100–119、D120–139、D140–199；`GROUND_STATE_FORCE_UNCERTIFIED`、`physical_score=null` 和本 TODO 保留。

**2026-11-22 有限 `N_t=16` 理论审阅已完成：**见[谱分解、误差表与文字数据流](../../results/wilson_loop/finite_nt_thermal_bound_review_20261122/README.md)。transfer-matrix 展开将静态源激发项 `Q exp(−Δ_Q t)`、热迹无源激发项 `H exp(−Δ_0(N_t−t))` 和混合项分开；有限 `N_t` 下增大 `t` 会降低第一项的指数、同时缩短第二项的抑制区间。`N_t=16`、候选 `t=4…8` 的补时长是12…8，但缺少独立的谱间隙与 kernel-dependent overlaps，不能给出污染数值。Creutz lane可作为固定`k,R,t`的有限时观测量；ground-state force lane仍须将对数污染传播到`Δ_RΔ_t`层并满足事前误差预算。没有拟合、模拟或打开封存split。引用的有限温度迹表示与零温 Wilson-loop 谱表示分别来自原始论文[Appendix A](https://arxiv.org/abs/2110.11659)和[static-force spectral decomposition](https://doi.org/10.1103/PhysRevD.105.054514)。
**零温界的有限 `N_t` 接合审计也已完成：**已有 `|χ−f₀|≤log(1+Qe^{-Δt})` 仅在正的零温前向谱下成立；加入热迹与混合项后不能沿用单点 `Q/gap` bound。报告 §5 现在给出带独立 `Q/H/X/Δ` envelope 时的四角和 force-level 保守界。当前这些输入均未测得，所以它是未来认证合同，不构成当前 pass。

**当前可执行边界（由上方 2026-11-25 提案细化）：**不再从 D0–99 选择确认性 `R/T/kernel`，也不重跑现有 `Q/gap` toy/窗口 bootstrap。`R/T/kernel`、lane alpha、数值门和 F 的误差预算已有可审阅默认值；剩余缺口是独立 review、独立 calibration/confirmation receipts、谱与热污染界、common metadata 以及数据/设备授权。不得启动 GPU 或打开 D100–119、D120–139、D140–199。界限未闭合时继续 `NOT_READY/UNCERTIFIED`、`GROUND_STATE_FORCE_UNCERTIFIED`、`physical_score=null`。

### 当前用户决定：有限-T Creutz 与基态离散静态力同时保留为两个 estimand lane

**目标选择已完成；确认性物理输入与独立证据仍未冻结，TODO保留，`physical_score=null`。** 用户选择有限-T `χ_k(R,T)` 与 ground-state `f₀(R+1/2)=U₀(R+1)−U₀(R)`；2026-11-25 的默认 primary、kernel、精度/多重性和 F 污染预算见本文件开头与 [`lane_contract_v2.json`](lane_contract_v2.json)。[双 lane 定义、认证条件和文字数据流](estimand_decision_review.md#0-当前选择两条-estimand-lane-分开交付)仍保留为估计量背景；绝对势外锚不是当前 lane 的前置项。

**最新边界确认（2026-11-26）：**方法默认已提出，但不能把它写成物理认证或测量授权。C lane 的 D0–99 precision pass 仅为 retrospective numeric preflight；synthetic coverage 报告显示在长相关假设下已测的 block bootstrap、stationary bootstrap 与 HAC 均不能保证 nominal coverage，known-rho delta benchmark 又依赖生产不可得的真参数且有弱 undercoverage。**此前“kernel ID 映射和正式 `common/lanes` metadata 也未核实”已过时：**开发包 canonical kernel ID 与 preflight 名称的结构化身份 crosswalk、`selected_protocol -> common/lanes` 映射及 v9 检查报告均已完成；这不提供 production-link/source/action receipt、独立审阅或物理认证。F lane 的谱/热/mixed-sector receipts 仍全空。框架可复用方向见 [`framework_extensibility.md`](../../doc/framework_extensibility.md)：C lane 需绑定 loop support、归一化和共同 block-chain receipt，F lane 需绑定谱界并传播到 lattice-force 单位；建议的 shared typed evidence envelope 目前不是已实现 runtime。当前只在收到新、可审阅的数据-free方法问题时继续做依赖界/abstention 方法；生产 evidence 仍需独立 data receipt 与 owner authorization。不得启动 GPU，不打开 gap、validation 或 shared holdout。`GROUND_STATE_FORCE_UNCERTIFIED` 与 `physical_score=null` 保持，本 TODO 保留。

- **Lane C（有限-T Creutz）**：primary method default 为 stout kernel 下 `R=2,T=5` 的绝对 χ；window-slope force、T依赖及成本为 secondary 诊断。不同 smear 一般改变 overlap 与有限-T 值，故 paired `χ_k−χ_identity` 是观测量差，不能直接写成对共同真值的误差改善。数值 gate 即使通过，也须独立校准/确认后才可认证精度或预定义差值。
- **Lane F（基态离散静态力）**：primary method default 为固定格距/体积/静态源约定下 `R_mid=2.5` 的 `f₀` 差。窗口估计、χ长T趋势、同draw漂移只是 secondary 支持证据。目前 `GROUND_STATE_FORCE_UNCERTIFIED`。需要独立激发态/热污染界及谱/多-T证据；不能把 χ 的高精度、窗口漂移小或误差条窄当作基态认证。continuum/格距外推不在当前 primary estimand 内。

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

### 2026-11-26 共享 evidence schema v2 的 Wilson 接线要求

PR #5 的共享 gate 已使用 evidence-envelope v2。review 元数据要求 `reviewer_role_claim="independent"`、scope/receipt hash 与 `independence_claim_sha256`；这些字段只能索引审阅声明，不能认证 reviewer 身份、无利益冲突或真实独立性。为使 PR #6 可基于 `main` 单独检查，本 PR 携带 shared gate 的最小 runtime 和 schema tests，并由 Wilson-owned adapter 调用；Pion task adapter/诊断仍单独留在 PR #5。该时间点 task adapter 尚未接入逐字节门；2026-11-26 后续条目记录了 C/F 默认 byte-gate 接线，但真实 RunSpec/source reader 仍未连接。

- **C lane / finite-T Creutz：**单独绑定 stout `R=2,T=5` 主点、四个正 loop means、同一 saved-configuration chain 与归一化 map；要求对应 multiplicity、precision 和 inference receipt。现有 synthetic coverage 显示在长相关情景下常用 bootstrap/HAC 未保证名义覆盖；没有独立 gap/TV 或新覆盖校准时不得把旧 D0–99 bootstrap 升成 confirmation interval。
- **F lane / ground-state force：**单独绑定 `R_mid=2.5` 离散力 estimator、正 reference-force simultaneous lower bound、3×3 GEVP/operator provenance、matched `N_t=32` thermal evidence，以及 q/h/x + spectral-model error 经 8-corner stencil 后的 `a_s*a_t*F` 力级包络；统计、谱/热/mixed/model 项保持分立 receipts 与 family allocation。
- **负例与状态：**C/F chain、kernel、split、loop/force unit 或 source hash 串用；non-independent/self-review role；缺 independence-claim hash；任一 planned fit/window/corner 未运行；C loop positivity 或 F positive-reference lower bound 不成立；q/h/x 仅有单 loop 原始界而没有传播后的 force-unit 界。RunReceipt 逐项计 planned/valid/failed/abstained；完整元数据最多到 `draft`，缺证据则 `abstained`。

目前 C lane 独立覆盖/依赖收据与 F lane 独立谱、正 reference-force、`N_t=32` 热污染和 propagated-error receipts 都未提供。此接线说明不授权 GPU 或打开 gap、validation、shared holdout；维持 `NOT_READY/UNCERTIFIED`、`GROUND_STATE_FORCE_UNCERTIFIED` 与 `physical_score=null`。图文交付仍须给出 lane 分离的数据流、错误预算图或逐步骤文字及完整分母。

文字流程：`C: 同一配置上的四个正 loop means -> 有限-T Creutz 与预注册区间/精度门 -> 覆盖与依赖 receipt -> C lane 独立结论或 ABSTAIN`；`F: 3×3 GEVP + matched Nt=32 -> f0 正下界 -> q/h/x 与谱项通过 8-corner stencil 传播到 a_s*a_t*F -> 合计统计/系统误差门 -> F lane 独立结论或 GROUND_STATE_FORCE_UNCERTIFIED`。两条 lane 共享样本时保留相关性，但各自不能替另一条提供证书。

本轮与 Optimize 一起复跑 `tests/test_optimize*.py tests/test_wilson*.py`：**184 passed**。这是 CPU 软件/合同回归，不覆盖 C/F 生产测量、独立污染界、确认区间或 physical score。

PR #6 当前的 `apply_evidence_bundle_gate`：C lane 可将四个 loop/source/coverage receipts 组成一个原子 bundle；F lane 可将 GEVP、reference-force 与 q/h/x/thermal/spectral receipts 组成另一 bundle。C、F 是 co-primary estimands，adapter 维护 lane-specific RunState/denominators，不能让一条 lane 的 draft 代替另一条；链身份不同仍不构成独立性证明。

### 2026-11-26 Wilson C/F task adapter 接线与剩余边界

当前 PR #6 携带共享 evidence schema v2 的最小实现，并将 gate 接到 [`evidence_adapter.py`](evidence_adapter.py)；C 与 F 各自使用独立 envelope、receipt、统计预算和 RunState。Pion task-specific adapter/诊断仍单独留在 PR #5：

- `apply_wilson_creutz_gate` 固定 C 为有限温 `chi_stout(R=2,T=5)`。它绑定四个 paired loop means、`R/T/kernel/sign` map、coverage/dependence/authorization/review hashes；检验 3×10,000 = 30,000 个 length-2/5/10 bootstrap draws、invalid draw 比例 `<=1%` 及 dimensionless hull half-width `<=0.02`。数值 precision 通过仍只到 draft，不证明 coverage。
- `apply_wilson_force_gate` 固定 F 为 midpoint `R=2.5` 的 stout-minus-identity 基态力。它将 force interval 与正 reference-force 下界绑定在同一 paired chain；另外绑定 3×3 GEVP、excited `q`、matched `N_t=32` thermal `h`、mixed `x`、spectral-model truncation 与 8-corner propagation。分母要求 30,000 个 force interval draws、30,000 个 reference draws、36 个 GEVP fit variants、28 个 simultaneous systematic cells 和 1 个 matched-`N_t=32` receipt。四个 force-unit 系统项分别受 1.5%、1.5%、1.0%、1.0% 上限；系统合计 `<=5%`、统计 half-width `<=5%`、合计线性误差 `<=10%`，且 reference-force simultaneous lower bound 必须为正。

文字流程：`C calibration split -> 四个 loop means -> paired 30k bootstrap / L=2,5,10 hull -> 1% invalid + 0.02 precision 检查 -> C draft/abstain`；`F calibration inputs -> 3x3 GEVP + Nt32 thermal -> q/h/x/model 28 cells -> 每个角点传播到 a_s*a_t*F -> reference positivity + 5/5/10% budget -> F draft/abstain`。两个 lane 的 samples 可以相关，adapter 不从不同 chain ID 推断独立，也不让 C 的有限温 Creutz 结果替代基态力。

本轮 synthetic positive fixture 的可复查分母为：C `four_required_loop_means=4/4/0/0`、`paired_bootstrap_draws=30000/30000/0/0`；示例 hull `[0.09,0.11]`、half-width `0.01`、invalid `0`。F `force_interval_draws=30000/30000/0/0`、`positive_reference_draws=30000/30000/0/0`、`gevp_fit_variants=36/36/0/0`、`force_systematic_cells=28/28/0/0`、`matched_nt32_thermal_receipts=1/1/0/0`；示例正 reference lower bound `1.0`，四项 propagated force bounds 为 `.01/.01/.005/.005`，statistical half-width `.03`。这些全是 metadata/summary fixtures，非 Wilson measurement 或物理污染界。C/F adapter 专项 `5 passed`，与 Optimize adapter 合计 `10 passed`。

通用字节身份前置由 [`core/source_integrity.py`](../../core/source_integrity.py) 的 `verify_source_bytes` 提供；共享 `apply_evidence_gate_with_source_bytes` / bundle variant 会在 metadata gate 前核验调用方逐项映射的 root 内相对路径，完整报告每个 planned 文件的 valid/failed/abstained。临时文件专项 **6 passed**，shared gate 集成用例另计。当时 Wilson task adapter 尚未接入 source-byte wrapper；随后 2026-11-26 更新已将 wrapper 接入 C/F gate，但生产 RunSpec/reader 尚未提供真实 source path map。digest 只支持当前读到的字节匹配，不认证生产来源、授权、独立性或后续不可变性。即便 byte gate 完整也最多到 `draft`。

**继续工作：**独立 reviewer 仍须复核 C 依赖/coverage 方法、四 loop 符号与 paired inference，以及 F 的 `q/h/x` 物理定义、GEVP/热态适用条件、角点传播和系统项相关性/重复计数；软件侧需将 source-byte gate 接入实际 reader/RunSpec，并核对每个 lane 的期望 hash 与所读文件清单。实际 manifest、loop/GEVP/thermal 原始 bytes、独立 coverage 与 contamination receipts、授权收据尚未提供。故当前不重跑 Wilson 测量、不打开 gap/validation/holdout/confirmation、不做 GPU/QUDA，维持 `NOT_READY/UNCERTIFIED`、F=`GROUND_STATE_FORCE_UNCERTIFIED`、`physical_score=null`。真实诊断仍须附图或可复查文字，并按 lane 报告 planned/valid/failed/abstained 与失败原因。


### 2026-11-26 Wilson C/F task adapters 的 source-byte 默认门

本次把 shared source-byte wrappers 接入 C 与 F 两个 Wilson task gate。C 单 envelope 接受 `source_root + source_paths`；F 六路 bundle 接受同一 root 下按 route 区分的 `source_paths_by_envelope`。默认 `require_source_bytes=True`，缺 root 或 map 即使 metadata 摘要齐全也 abstain；只有 synthetic tests 显式传 `require_source_bytes=False` 且没有 source 参数时才使用 metadata-only 路径。给出部分路径时 wrapper 对 C 所有注册的 source-hash 项、F 所有 route 的注册 source-hash 项逐一计数；缺路径/文件是 abstained，hash mismatch/越界/read failure 是 failed，所有文件匹配才交给 shared metadata/receipt gate。完成仍只到 draft。

文字流程：`C 四 loop means + dependence/coverage/review/source hashes -> C map/precision gate -> root 下逐文件字节核验 -> C draft 或 abstained`；`F 六 route envelopes + force/GEVP/thermal/systematic receipts -> force-unit 与 28-cell 预算 gate -> 六 route 的 source hashes 展开成 planned 文件 denominator -> 原子字节核验 -> F draft 或 abstained`。逐 route 文件清单必须由真实调用者提供，adapter 不搜索 production tree，也不推断 chain 独立性。

新增 C 与 F 默认缺路径拒绝测试；缺路径时 source-file P/V/F/A 为 C `8/0/0/8`、F `53/0/0/53`。C 正向映射 8/8 文件有效，篡改 common receipt 后为 `8/1/7/0` 并 abstain；F 六路正向映射 53/53 文件有效，篡改 common receipt 后为 `53/6/47/0` 并原子 abstain。Wilson adapter suite 为 **9 passed**，Optimize/Wilson adapters 与 shared evidence/source-integrity tests 合计 **44 passed**；整个 checkout CPU suite **276 passed**，Optimize/Wilson test 文件组合 **202 passed**。目前没有真实 Wilson 路径映射，task adapter 的可用 C/F source 包仍未提交，因此这些 CPU fixtures 不是 production receipt。SHA-256 一致不认证 digest 来源、物理语义或审阅独立性，也不锁定读完后的文件。

下一步接线应让 C loop reader 与 F GEVP/thermal/force reader 在同一输入清单上产出其真正读取的路径和 hashes，再验证每个 receipt 文件与 reader 文件完全一致，保留 planned/valid/failed/abstained 和失败原因。独立 reviewer 仍需确认 C 依赖与 coverage、Creutz 符号/index、F 的谱/热污染定义和角点 force-unit 传播。没有获授权的真实 calibration files、独立 dependence/coverage receipts、matched-`N_t=32`/GEVP 污染界及 positive reference-force 时，不测 GPU/QUDA、不打开 sealed/confirmation 数据；状态仍为 `NOT_READY/UNCERTIFIED`、`GROUND_STATE_FORCE_UNCERTIFIED`、`physical_score=null`。


### 2026-11-26 Wilson 生产读入器目标盘点

只读检索当前 PR #6 checkout 后，没有找到 `tasks/wilson_loop/measure.py`、Wilson `protocol_d_*.json` 或 `measurement_input_manifest` 实现；当前 task-owned 实现是 lane contract、结构/诊断脚本和 C/F evidence adapter，没有接入所选 C/F measurement 的 live reader。历史 TODO/归档记录中的 reader、RunSpec 或远端任务不能据此视为当前 checkout 可调用的入口。故 source-byte API 目前只接受调用方显式给的路径，尚不能证明这些路径就是 C loop、F force、GEVP/thermal 计算真正读取的文件。

文字诊断：`当前 checkout: protocol/lane contract + archived diagnostics + adapter -> no selected-lane reader -> no production file map -> C/F remain abstained`。后续先补一个冻结、可审查的 C/F source reader/RunSpec：在读取前做 split、hash、geometry/action/kernel 和授权 preflight；同一 read transaction 产出所读文件清单、manifest/receipt hashes 与 source paths；随后才调用 task adapter，并以 CPU fixture 测试 reader/gate 清单一致、缺文件、篡改、split 拒绝和完整分母。当前代码盘点没有读取任何 gauge/loop/GEVP/thermal 数据，物理文件分母 `0/0/0/0`；没有启动 GPU/QUDA。该软件入口完成也不会补出独立 coverage、q/h/x bounds、正 reference-force 或 physics review，状态继续保持 `NOT_READY/UNCERTIFIED`、`GROUND_STATE_FORCE_UNCERTIFIED`、`physical_score=null`。

### 2026-11-26 C/F source snapshot 与 reader 分支核对

shared [`core/source_integrity.py`](../../core/source_integrity.py) 现提供有界 `capture_source_snapshot`，Wilson C 单 envelope 与 F 六路原子 bundle gate 可接收同一批 immutable snapshots。任务 reader 可先从 snapshot 的 `read_bytes(name)` 解析 loop/force/GEVP/thermal 数据，再将同一 snapshot 交给 gate；后者会重算保留字节的 SHA-256，并在结果写 `read_mode=immutable_snapshot`。默认捕获总量最多 64 MiB，超限文件不进入 snapshot，按 failed 处理；大 gauge field 仍需受审的流式 reader，不能提高上限来掩盖内存预算。

文字流程：`selected C/F source map -> read once into bounded snapshot -> C: parse four paired loops / F: parse force + GEVP + Nt32 receipts -> route-specific metadata/budget gate -> same snapshot byte gate -> lane draft or abstain`。合成负控在捕获后改写原路径，C 仍核验 `8/8`，F 六路仍原子核验 `53/53`；缺文件保持 planned，不能因其它 route 通过而部分 draft。PR #6 聚焦 shared/Optimize/Wilson adapter suite **52 passed**、完整 CPU suite **284 passed**；这些不是生产 gauge/loop/GEVP 输入。

此次 Git 核验还发现另一条本地历史分支 `fork/dianjun@54f0e97` 有 `tasks/wilson_loop/measure.py` 与 `protocol_d_20261120.json`；当前 PR #6 HEAD 不含它们，而且该分支携带大量与本 PR 无关的代码和结果差异。故“当前 checkout 没有 reader”仍准确，但不能写成“本地 Git 中从未存在 reader”；也不把整条分支或 D protocol 直接并入已选定的有限-$T$ Creutz / 基态力 lane，因为其中测量窗与方法未逐项对齐当前合同。

仍未完成的具体软件工作：审计是否能最小移植 `measure.py` 所依赖的 NERSC/identity/kernel 模块；不得绕开新 lane contract，且要把当前 C 的 `(R=2,T=5,stout)` 与 F 的 `R_mid=2.5` stencil 映射到同一 snapshot reader。加入 reader 实际解析对象与 receipt summary 的一致性测试、split/hash/action/kernel 拒绝、C/F planned denominator 和 route 原子失败图文，再由 reviewer 独立核验 Creutz 符号与 F 的谱/热污染定义。没有独立 coverage、matched-$N_t=32$、正 reference-force 与 q/h/x receipts 前不重测/不解封数据；保持 `NOT_READY/UNCERTIFIED`、`GROUND_STATE_FORCE_UNCERTIFIED`、`physical_score=null`。

### 2026-11-26 C-development 读入器接入 immutable snapshot

现有 [`c_lane_open_development_diagnostic.py`](c_lane_open_development_diagnostic.py) 的 pinned D-development 读入器现在将验证逻辑拆为“路径捕获 / snapshot 捕获 + 同一 bytes parser”两层。snapshot 模式只接受 `development.npz`、`development_provenance.json`、`development.commit.json` 三项显式命名输入；复核固定 D0–99 generation、NPZ/provenance/loop hashes、R/T 轴、周期边界、`stout_rho0.1_n5` 参数、依赖指纹、轨迹 ID 和数组有限性。`run(..., source_snapshot=...)` 可将这份 snapshot 直接交给原 diagnostic 与出图流程，且输出 protocol 记录 `read_mode=immutable_snapshot`，捕获后改写磁盘原文件不会改动分析输入。

文字流程：`三项已开放 D-development transaction bytes -> pinned hash/generation/split/kernel/action preflight -> 解析 loop[ID,kernel,R,T] -> 选 stout kernel -> 四 loop paired Creutz + block-length hull -> CSV/PNG/README，仍标记 RETROSPECTIVE_DEVELOPMENT_ONLY_NOT_CONFIRMATION`。新增 synthetic tests 覆盖完整解析、原路径覆写、额外 split 拒绝、交易项缺失、图文产物和 no-clobber；Wilson C/reader/lane 聚焦 suite **29 passed**。end-to-end fixture 的输入分母是 source-file `3/3/0/0` 与 synthetic configuration `100/100/0/0`；小型测试用 `24×3=72` 个 bootstrap draws，仅检查代码流和 artifact，不代表已校准的生产精度。当前真实物理输入读取分母仍为 `0/0/0/0`，没有运行这份历史 D0–99 data bundle，也没有 GPU/QUDA。

这关闭的是**开放 development diagnostic 的 same-bytes reader**，不是 C-lane calibration reader：pinned D0–99 是已观察的 retrospective development，不满足 calibration split 和独立 coverage 证据要求。此段记录时 F 还没有 snapshot reducer；后续已增加已拟合 GEVP support receipt 的 q reader 和 force-summary v2 reader，但仍没有 raw correlator/3×3 GEVP、thermal `h` 或 mixed-sector `x` reader，真实 F bounds 仍没有从物理 reader 派生。后续 C-calibration reader 已从同一 snapshot 重算并核对 interval summary，再将结果送入 C gate；仍待受审 production exporter/schema 的符合性、依赖/coverage receipts 和独立 reviewer。不得把 D0–99 diagnostic 升为 confirmation；继续保持 `NOT_READY/UNCERTIFIED`、F=`GROUND_STATE_FORCE_UNCERTIFIED`、`physical_score=null`，gap/validation/holdout/confirmation 数据封存。

本次在同一 bytes parser 中又补了两项 preflight：NPZ 内 `protocol_hash` 必须等于捕获 provenance protocol 的 canonical fingerprint，选取 C-lane loop 前要求整个 loop tensor 有限。此前只验证 transaction 中记录的 source hash 和 loop-array hash；现在再显式检查 provenance 与测量载荷的协议关联以及非有限值。对应 synthetic snapshot regression 已包含路径覆写、协议/transaction 拒绝、绘图产物和 no-clobber；它仍是 fixture，真实 D measurement 本轮未读取，生产 C/F adapter 仍不接收此 retrospective reader 输出。

随 PR #6 更新重跑的完整 CPU suite 当前为 **295 passed**；其中 Wilson source-snapshot reader regression 只使用测试构造的 bytes/合成 loop tensor，不读取归档的实际 D0–99 NPZ。此数是软件回归证据，不关闭 C coverage/calibration 或 F ground-state-force 证据门。


### 2026-11-26 F force summary 的 immutable-snapshot 代数读入器

新增 [`force_summary_reader.py`](force_summary_reader.py)，把旧 F gate 中“调用方提供 `force_summary` 数字、gate 另行查同名 SHA”的间接关系收紧为一条可复核数据流。初版只接受 `wilson-f-force-summary-input-v1`；该历史 schema 已被下文的 v2 顺序校验取代。reader 要求六个 F route 的 `SourceByteSnapshot` 都捕获同一份 summary bytes；解析时拒绝重复键、NaN/Inf、额外/缺失字段、错误单位、负值和错误 corner 形状。输入给出 `q/h/x` 各自 2 kernels × 4 corners 的非负 dimensionless bound，以及外部提供的正 reference-force 下界、statistical halfwidth、model-truncation bound 和无效 draw 计数。reader 用现有 [`force_budget.py`](force_budget.py) 重新计算 `Σ log(1+q)`, `Σ log(1+h)`, `Σ log(1+x)`、四项 systematic 总和与 statistical + systematic 总界，再把派生 summary 与同一 snapshots 交给 F evidence gate。

文字流程：`六路 immutable snapshots -> 6/6 同一 force-summary bytes -> strict schema/unit/shape check -> 2×4 q/h/x -> force-unit log1p propagation 重算 -> 对照现有 F gate thresholds/receipts/source hashes -> draft 或 abstain`。新增测试用合成 summary 确认 snapshot 捕获后磁盘文件被覆写仍使用原字节；source-file denominator=`53/53/0/0`，summary-route denominator=`6/6/0/0`，`physical_score=null`。q/h/x 单项、model、statistical 和总界都从 fixture 明确的输入重新计算；错配一个 route 的 summary hash会 `ABSTAIN`，错误 corner 维度也会 `ABSTAIN`。Wilson evidence adapter suite **11 passed**，PR #6 全仓 CPU suite **297 passed**。

此 reader 只校验确定性的角点到 force-unit 传播；并未从 raw Wilson loops 重建 force interval 或 positive reference，也未从 3×3 GEVP/overlap、matched-`N_t=32` 或 mixed-sector 数据推导 q/h/x。输入中的谱界、正 reference、statistical halfwidth 和 model truncation 仍是待独立来源支持的假设/摘要；成功最多到 `draft`，不认证摘要来源、reviewer 独立性或物理 bound。当前实际输入 planned/valid/failed/abstained=`0/0/0/0`，没有读 gauge/loop/GEVP/thermal bytes，没有 GPU/QUDA。

下一软件阶段应让 reviewed GEVP/thermal parsers从同一 snapshot 产出可追溯的谱、overlap、finite-`N_t` 和 mixed-sector quantities，再由明确的物理公式推导 q/h/x corners；对 force/reference bootstrap draws 也要从固定 `R=2,3`、`Rmid=2.5` stencil 同源重算 summary，而非接受调用方 summary 数字。需配 spectra/residual 与污染边界图或完整文字诊断，并逐项报告 planned/valid/failed/abstained。没有这些真实 calibration receipts、独立物理 review、positive reference-force 和数据授权前，继续保持 `NOT_READY/UNCERTIFIED`、`GROUND_STATE_FORCE_UNCERTIFIED` 与 `physical_score=null`；C finite-T Creutz lane仍独立。


### 2026-11-26 C-lane calibration 的同字节区间重算

新增 [`c_lane_snapshot_reader.py`](c_lane_snapshot_reader.py)，与既有锁定 D0–99 的 retrospective reader 分开：新入口只接受明确命名的 `C-calibration` snapshot，先核对 manifest、measurement NPZ、interval-summary 三种同源字节的 SHA-256，再校验 calibration split、16⁴ Wilson β=6、周期边界、R/T 轴、kernel 参数、manifest→NPZ 关联、递增 configuration IDs 与有限 loop tensor。它从 captured NPZ 选 `spatial_stout_rho0.10_n5`，按当前 C 合同的四个 loop means 与符号计算有限温 `χ(2,5)`，复用已有圆形 moving-block bootstrap，在 L=2/5/10 上用同一 draw indices 重算 97.5% 区间 hull、无效 draw 数和 halfwidth；之后逐项与 captured `interval_summary` 核对，再把派生 summary 和**同一 snapshot**传入 C gate。

文字流程：`C calibration manifest + loop matrix + interval summary -> hash/split/action/kernel/axis/ID preflight -> 四个 paired loop means -> L=2/5/10 bootstrap -> 30,000 draws 的 invalid denominator + percentile hull -> summary 数值与哈希一致才交 C gate -> draft/abstain`。合成端到端样例用 12 个常数 loop configuration，读入文件 `3/3/0/0`、配置 `12/12/0/0`、draw `30,000/30,000/0/0`，总 evidence source bytes `8/8/0/0`；捕获后覆写磁盘 NPZ 仍按快照通过，summary 值篡改和 validation/sealed split 均拒绝。Wilson evidence adapter suite **13 passed**，PR #6 全仓 CPU suite **299 passed**。这些常数 toy 只检查同字节传递、符号/轴和 denominator，不是覆盖率或物理数据证据；text-flow 包含 interval 与失败分母，因此本轮不伪造物理诊断图。

边界：reader 的 strict manifest/NPZ/summary schema 是本轮实现的数据接口约定，尚未从真实 measurement producer 的输出核准。确定 bootstrap seed 目前沿用既有 retrospective diagnostic 的 `20261125 + block_length`，当前 lane contract 冻结了 block lengths/draw count/alpha，却未单独冻结 seed；不得把此 seed 说成已审阅的研究决定。虽可重算 interval summary，bootstrap coverage calibration、依赖 gap/TV、输入 HMC provenance、review/authorization 内容仍由外部收据负责；示例的 `DRAFT_PENDING_TASK_VALIDATION` 也绝非统计或物理认证。实际 gauge/loop 输入读取仍为 `0/0/0/0`，未运行 GPU/QUDA。

后续软件工作：先让经审阅的 production measurement exporter 输出并冻结这些 manifest/NPZ schema、source hash 与 seed；另写测试覆盖 exporter↔reader agreement、所有 summary 字段/每个 block-length 的失败率、source map 缺项/错 hash、非有限或非正 ensemble means 和 byte-budget 超限。随后由独立 reviewer 审 C-lane block-bootstrap coverage 与 Creutz 公式；只有授权且独立的 calibration measurement/coverage receipts 到位后才能接入物理 lane。D0–99 retrospective 包永不因新 reader 改标为 calibration，validation/gap/shared holdout/confirmation 仍关闭。

### 2026-11-26 immutable NPZ 解压预算防护

C calibration loop reader、D0–99 retrospective snapshot parser 和 Optimize D06 q-matrix reader 现都在 `numpy.load` 前调用 [`core.npz_safety.validate_npz_payload`](../../core/npz_safety.py)。它验证 NPZ 成员为唯一、扁平的 `.npy` 项，读取受限 NPY header 检查 dtype/shape/声明长度，拒绝 object array，并将 ZIP 解压总量限制在 64 MiB。这个上限与 source snapshot 的压缩字节预算是两道不同检查；压缩小文件不能借高膨胀比迫使 NumPy 分配超预算数组。

文字流程：`captured compressed bytes -> ZIP/NPY 结构预检 -> 解压总量、成员计数与 array-header 长度通过 -> 原 task parser -> split/manifest/axis/inference checks`。shared preflight fixtures 覆盖正常压缩、膨胀拒绝、巨大 shape 欺骗、object dtype 和重复 member；连同 Optimize/C reader 回归定向 **33 passed**，PR #6 全仓 CPU suite **305 passed**。所有正向数据是合成 NPZ；C/F calibration 和实际 loop/spectrum source 分母仍为 `0/0/0/0`。

该防护只约束 NPZ snapshot parser 的预分配资源，不校验 ZIP CRC 之外的授权、data provenance、measurement producer 或物理语义；超过 64 MiB 解压预算的未来 GEVP/thermal 原始数据需设计流式读取并独立复核，不能为适配而取消预算。仍缺 C reader 与受审 production exporter/schema 的一致性、F 的原始 GEVP/thermal parser、coverage/contamination receipts 与研究审阅；`NOT_READY/UNCERTIFIED`、`GROUND_STATE_FORCE_UNCERTIFIED`、`physical_score=null` 不变。

### 2026-11-26 C lane bootstrap seed 与摘要 schema 冻结

当前 C reader 之前沿用 retrospective diagnostic 的 `SEED_BASE + block_length`，但 calibration 摘要没有声明 seed，故相同 JSON schema 可能代表不同随机数流。现将该计算默认提升到 `wilson-two-lane-selected-v2`：`bootstrap_seed_base=20261125`，每个 `L∈{2,5,10}` 的 NumPy `default_rng(seed_base+L)` 生成圆形 block indices；每个长度 10,000 draws，`alpha_lane=0.025`、central interval level 0.975、无效 draw 最大比例 0.01、halfwidth 目标 0.02。这个 seed 只是沿用已存在的 deterministic default 以固定复现路径，不是按观测结果挑 seed，也不解决 bootstrap coverage calibration。

`wilson-c-creutz-interval-summary-v2` 现要求 summary 同时声明方法、block lengths、draw 数、alpha、invalid-fraction cap、precision target、seed base/rule 和 interval level；reader 从选择合同取得 seed，以该值重算 interval，再与 snapshot 中声明的 resampling protocol 和区间/分母逐项比对。与合同不符的 seed 会在 interval 计算后被拒绝，不进入 C evidence gate。文字流程：`selected protocol v2 -> (L, draws, alpha, caps, seed rule) -> snapshot loop bytes -> deterministic paired bootstrap -> compare v2 summary + denominator -> gate or ABSTAIN`。

新增 synthetic 负控改变摘要 seed，验证其返回 `ABSTAIN_C_SUMMARY_RESAMPLING`；正控断言 reader 输出的 seed、block lengths 与选定合同一致。C lane + lane contract + C development reader 定向 suite **34 passed**；正向测量仍是 12 个常数 loop fixture，source/configuration/draw denominator 为 `3/3/0/0`、`12/12/0/0`、`30,000/30,000/0/0`，不验证 coverage 或有效样本数。实际 C calibration 文件分母仍 `0/0/0/0`，没有 GPU/QUDA、sealed split 或物理测量。

这关闭的是 seed 未声明导致的重现歧义；统计校准、独立 dependence/gap/TV receipt、真实 calibration exporter 对 v2 schema 的符合、独立 reviewer 与授权仍未完成。finite-`T` Creutz 和 ground-state force 仍是分开的 estimand；状态保持 `NOT_READY/UNCERTIFIED`、`GROUND_STATE_FORCE_UNCERTIFIED`、`physical_score=null`。

### 2026-11-26 C-development 报告绑定其 NPZ 预检源码

Retrospective C-development parser 现在在输出 `protocol.json` 和 `summary.json` 时记录诊断脚本与 `core/npz_safety.py` 两份 `analysis_source_sha256`，并将两份脚本副本放入新报告目录；`manifest.json` 以报告目录内相对路径覆盖每个文本、CSV、NPZ、PNG 和源码快照。这样即使输出写到项目目录之外，manifest 仍可自包含验证，不再依赖源文件恰好位于输出父目录。

图文数据流：`pinned D0–99 transaction snapshot -> NPZ preflight/parser -> paired Creutz + bootstrap -> README/CSV/PNG + parser source snapshots -> relative artifact manifest`。Wilson snapshot reader、lane-contract 和 source-integrity focused suite **33 passed**；测试按 manifest 验证每个产物哈希，并确认保存的 helper hash 等于 protocol 记录；PR #6 全仓 CPU suite **306 passed**。输入仍是 synthetic regression fixture，D0–99 物理数据并未重读；此改动不改变 retrospective-only 标记，也不建立 calibration coverage、F 谱污染界或生产 reader，lane physical status 仍 abstained/uncertified。

### 2026-11-26 F-lane 污染时间点与 GEVP overlap 上界 reducer

**补上的协议坐标：**旧 F 合同写了 3×3 GEVP 的 fit window `[3,7]`、`tmin={3,4,5}` 与 8 个 `q/h/x` loop corners（两个 kernel、`R=2,3`、`T,T+1`），却没有说明这 8 个角点使用哪个 `T`。这会让生产 parser 各自挑时间，导致边界数值不再对应同一 estimand。现提出 `T=5`、`T+1=6`：两点都在 `[3,7]` 内，也都落入全部三个 `[tmin,7]` 变体的实测窗口；这是协议方法默认值，仍待独立物理/统计 reviewer 审阅，未标成确认性物理输入。

新增 [`spectral_q_bound_reader.py`](spectral_q_bound_reader.py)，只接受 immutable snapshot 中严格格式的**已拟合 support receipt**，不接受路径 fallback。它要求 identity/APE/stout × `R=2,3` × `tmin=3,4,5` × 2/3-state 的 36 个 fit variants；对每个 kernel/R/T 计算正谱上界

```text
q_upper(T) = max_over_(tmin,state_count) sum_n ratio_upper[n] * exp(-gap_lower[n] * T),  T in {5,6}
```

选中的 identity 与 stout 产生 8 个可按力 stencil 顺序消费的 q cells，APE 另列 4 个描述性 basis cells。每个 q cell 的 alpha 按 systematics family `0.0125/28` 分配，再对 6 个 fit variants × 最多 2 个 excited states × ratio/gap 两侧端点预留 24 个 Bonferroni slots；二态模型未用的 slots 不重新分配。reader 检查 schema、units、split、source bytes/hash、variant completeness 和 alpha metadata，并返回最大值对应的 fit variant，**不验证**上游 marginal interval coverage 或正谱假设是否适用于真实 Wilson-loop correlator。

文字流程：`one captured fit-support receipt -> 36/36 GEVP fit variants + alpha/split/hash preflight -> 各 kernel/R/T=5,6 的 ratio_U exp(-gap_L*T) -> 六种时间窗/态数取最大 -> identity/stout 8 q cells + APE 4 descriptive cells -> 仅可送后续同源 force reducer，仍未认证`。合成正控 denominator 为 fit variants `36/36/0/0`、selected q cells `8/8/0/0`、APE cells `4/4/0/0`；缺 fit、重复 variant、状态数组错长、alpha 改写、错 hash 和 gap/validation/sealed split 都 fail closed。q-reader 初版定向 suite **26 passed**；当前 `tests/test_wilson*.py` 为 **89 passed**，PR #6 全仓 CPU suite 为 **316 passed**，`git diff --check` 通过。这些只验证 reducer 与草案结构，synthetic ratios/gaps 不是谱测量、覆盖率校准或污染证据；`physical_score=null`。

接线补充（2026-11-26）：F force-summary wrapper 现从 `q_excited` envelope 的 `gevp_receipt` hash 与同一 `SourceByteSnapshot` 调用 q reader，重算 36 个拟合支持 variants 与 8 个 q 上界；按 stout/identity 和 `(R,T)=(2,5),(2,6),(3,5),(3,6)` 的固定角点顺序，要求 force summary 提供的每个 q corner 不小于对应谱上界，之后才重算 q/h/x 的 force-unit budget 并将同一 snapshots 交给 F bundle gate。文字流程：`q_excited GEVP receipt bytes -> q_upper(T=5,6) -> compare all 8 q corners against force-summary JSON -> q/h/x force propagation -> same-byte F gate or ABSTAIN`。新增正控确认 fit variants `36/36/0/0`、selected q cells `8/8/0/0`、q force corners `8/8/0/0`；q 被低报的负控按 `8/0/8/0`（planned/valid/failed/abstained）逐角点失败并保持 `RunState.abstained`。Wilson evidence adapter + q-reader 定向套件 **23 passed**，完整 Wilson suite **89 passed**，PR #6 全仓 CPU suite **316 passed**。这些都是 synthetic fit-support / force-summary bytes，不给谱假设、上游区间 coverage、h/x 或 force 数据背书。仍未实现/验证：raw correlator-matrix reader、3×3 GEVP 与 overlap/gap interval producer、上游 simultaneous coverage、matched-`N_t=32` thermal `h`、mixed `x`、模型截断四格、force/reference bootstrap 从原始 paired loops 同源重算，以及独立 reviewer/owner authorization。q reader 的输入仍是已经拟合的 support summary；正谱假设和 confidence bounds 不由它验证。F gate 当前能核对 q 不低报并传播调用方提供的 h/x、reference-force 和 model/statistical summaries，但后几项仍需同源 reader/独立 receipts。不得用合成接口打开封存数据或启动 GPU/QUDA；F 继续 `GROUND_STATE_FORCE_UNCERTIFIED`，C finite-`T` Creutz 仍为不同 estimand，双 lane `NOT_READY/UNCERTIFIED`。

### 2026-11-26 F force-summary corner 顺序显式化

复核 q→force 接线时发现 schema v1 只要求 `q/h/x` 是 `2×4` 矩阵，没有在原始 summary 中声明两行对应哪个 kernel、四列对应哪个 `(R,T)`。reader 自身的 q 顺序是 `spatial_stout_rho0.10_n5, identity`，角点为 `R2_T5, R2_T6, R3_T5, R3_T6`；若生产 exporter 交换顺序，数值仍能通过 shape 与预算检查，却可能把 q 上界比较到错误角点。现将 strict input schema 升至 v2，强制携带并逐项比较 `force_kernel_order` 与 `force_corner_order`，仅接受上述两种 canonical order，缺项、反序或其他映射均 fail closed。

文字流程：`same six route snapshots -> strict v2 JSON -> assert kernel rows [stout, identity] and columns [R2_T5, R2_T6, R3_T5, R3_T6] -> compare eight q cells with same-snapshot spectral bounds -> propagate q/h/x -> same-snapshot F gate or ABSTAIN`。positive synthetic fixture 的 summary route denominator 为 `6/6/0/0`、bundle 为 `1/1/0/0`、q force corners 为 `8/8/0/0`；kernel-row 反序和 corner-column 反序两种负控各自得到 summary bundle `1/0/1/0`、八个后续 q corners abstained，RunState 进入 abstained。完整 `tests/test_wilson*.py` **90 passed**；PR #6 全仓 CPU suite **317 passed**。生产输入分母仍 `0/0/0/0`；v2 只固定数组语义，不证明原始 GEVP、thermal `h`、mixed `x`、force/reference bootstrap、coverage、authority 或 reviewer 独立性。schema 迁移仅适用于未来受审 exporter；不得改读封存数据，F 仍 `GROUND_STATE_FORCE_UNCERTIFIED`、双 lane `NOT_READY/UNCERTIFIED`、`physical_score=null`。

### 2026-11-26 F-lane moving-GEVP 截断敏感度诊断与 `td` 合同歧义

新增 [`gevp_t0_truncation_diagnostic.py`](gevp_t0_truncation_diagnostic.py) 和[图文报告](gevp_t0_truncation_diagnostic_20261126_v1/README.md)。它以已知四态、三算符正向谱矩阵 `C_ij(t)=Σ_n Z_ni Z*_nj exp(-E_n t)`，按 moving GEVP `C(t)v=λ(t,t0)C(t0)v` 计算 `E_eff=log[λ0(t,t0)/λ0(t+1,t0)]`，比较选定 `t0=1`、固定 `t0=2,3` 和对有限差分两端均满足 `t0≥(t+1)/2` 的敏感度曲线。选定 fit window `t=3…7` 中最大绝对能量偏差分别为 `0.118567`（t0=1）、`0.101543`（t0=2）、`0.064864`（t0=3）、`0.101543`（逐点条件路线）；单位为 `a_t E`。三态恰满秩 fixture 恢复精确基态，加入第四态后的三算符截断产生非零偏差。GEVP 点分母=`19/19/0/0`，物理输入=`0/0/0/0`，认证门=`1/0/0/1`。新测试 **4 passed**；增补后 Wilson 全集 **94 passed**、PR #6 全仓 CPU suite **321 passed**。

这项结果是完全确定的正向、无限时间 extent、无噪声 toy；它不是拟合或覆盖率证据。Blossier 等原始 GEVP 分析给出 moving-GEVP 与 effective-energy 定义，并明确把有限时间 extent 项忽略在近似里，要求时间 extent 足够大；其 `t0≥t/2` 条件用于得到较快的渐近修正阶，并非有限 `N_t` 误差证书。[原文](https://arxiv.org/abs/0902.1265)。本项目 `N_t=16` 的 q 与 matched-`N_t=32` thermal `h` 不能由本 toy 合并推断。

复核当前 [`lane_contract_v2.json`](lane_contract_v2.json) 与 [`spectral_q_bound_reader.py`](spectral_q_bound_reader.py) 还发现：合同写了 `t0=1, td=2`，reader 只核对这两个整数，却没有定义 `td` 是固定 eigenvector diagonalization time、moving GEVP 的某个时间，还是 fit 参数；也未定义 `overlap_ratio_upper` 指原始 smear operator overlaps 还是 GEVP-projected operator overlaps。两者在一般截断谱中不能静默互换。后一节已给出候选固定向量/投影 overlap 定义和 raw-matrix snapshot projection reader；它们仍未写入 lane contract，也未接 q-bound reader。接 gate 前仍须独立审阅该对象定义，并实现上游 cross-correlator producer、状态重叠拟合和区间传播。

文字流程：`4-state exact forward spectrum -> 3x3 C(t) -> fixed-t0 GEVP -> t=3..7 effective-energy pairs -> t0/basis-truncation sensitivity -> identify overlap-object ambiguity -> candidate fixed-vector definition + raw snapshot projection -> keep F uncertified`。raw snapshot reader 的 synthetic schema/投影层现已完成；仍待 `td`/overlap 合同的独立审阅、真实 cross-correlator exporter、covariance-aware GEVP/overlap fit 和 paired interval producer。后续覆盖应含 exact three-state recovery、omitted-state bias、非正/近奇异矩阵、finite-`N_t`、small `Z_0`、bootstrap coverage 与 split/hash；没有经审阅的 producer/consumer 合同、覆盖率、热污染、mixed-sector、force/reference receipts 与授权前，不连接物理 gate，保持 `GROUND_STATE_FORCE_UNCERTIFIED`、`NOT_READY/UNCERTIFIED`、`physical_score=null`。

### 2026-11-26 F-lane `td` / overlap 对象提案及精确谱 toy

新增 [`gevp_overlap_object_diagnostic.py`](gevp_overlap_object_diagnostic.py)、5 个定向回归和[图文诊断包](gevp_overlap_object_diagnostic_20261126_v1/README.md)。为使后续 reader 有唯一可执行定义，先给出候选默认值：`t0=1` 是广义本征问题的 metric reference；`td=2` 是固定一次的 principal-vector 求解时间，解 `C(td)v0=λ0 C(t0)v0` 并取最大正本征值向量，以 `v0†C(t0)v0=1` 归一化。按本任务相关函数约定 `C_ij(t)=Σ_n Z_ni Z*_nj exp(-E_n t)`，将此向量定义出的固定投影算符 overlap 设为 `Z_n(v0)=Σ_i v0_i* Z_ni`，并计算

```text
q_v(T) = Σ_{n>0} |Z_n(v0)/Z_0(v0)|² exp[-(E_n-E_0)T],  T∈{5,6}.
```

这是一项**供独立审阅的合同提案**，尚未写入 `lane_contract_v2.json`，也未接入 q-bound reader 或物理 gate。有限四态、三算符、无限时间 extent、无噪声 toy 显示对象差异非常大：`td=2` 投影的 `q(5),q(6)=8.8819,7.7106`；三个原始算符中的最大值为 `0.9880,0.7742`，前者分别约为后者的 `8.99×,9.96×`。保持同一四态谱，只改固定投影时间 `td=3,4,5`，`q(5)` 变为 `4.2709,1.4458,0.4735`；与此同时 `cond[C(td)]` 从 `29.4` 增至 `45.9`。因此当前数据结构中的 `overlap_ratio_upper` 必须明确是某个固定 GEVP-projected operator 的逐态比值，不能接受未说明是原始 smear 基还是投影态的数组。toy 的 `q(T)` 只表示正向谱污染项，不等于有效能量偏差；结果不意味着真实投影必然更差，也不确定生产 `td`。

图文流程：`exact 4-state spectrum + 3 bare operators -> solve (td,t0) principal vector -> C(t0)-normalize and fix phase -> derive projected Z_n -> q(T=5,6) -> compare original-basis objects and td choices -> reviewer candidate only; F remains uncertified`。分母：原始算符×T 单元 `6/6/0/0`，GEVP `td×T` 单元 `16/16/0/0`，物理 correlator/spectrum 输入 `0/0/0/0`，认证门 `1/0/0/1`（planned/valid/failed/abstained）。新增测试验证三态恰满秩时 excited overlaps 消去、第四态截断时 q 对象/td 敏感、向量缩放/相位与可逆 operator-basis 变换不改 q，以及奇异 metric/零基态 overlap 拒绝；新增定向测试 **6 passed**，全复跑结果见本节最新验证快照。

下一步可由独立物理 reviewer 先审 `C_ij` 与投影 overlap 的共轭/指标约定、`td=2` 的物理适用性和 q-bound 上界含义；认可后再出 `lane_contract_v3` 并实现同一 `SourceByteSnapshot` 的 raw 3×3 matrix → covariance-aware GEVP/state-overlap fit → paired interval reader。覆盖应增加有噪声 bootstrap、有限-`N_t` 双向谱、近简并态、接近零的 `Z_0(v0)`、投影向量换相位/基变换和估计覆盖率诊断。没有这些受审合同、同字节 raw correlator、matched-`N_t=32` 热项、mixed `x`、force/reference intervals、独立 coverage/review 与授权之前，不能由 toy 数据填入 `q`，不能连接 F gate；继续 `GROUND_STATE_FORCE_UNCERTIFIED`、`NOT_READY/UNCERTIFIED`、`physical_score=null`。
