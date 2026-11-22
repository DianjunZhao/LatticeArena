# LatticeArena 阶段性总结（2026-11-18）

三个任务在 2026-11-18 做了算子修复、契约冻结和 GPU 重测。这一页是索引和结论；
细节都在各自的 task README 与 `results/` 里。

## 0. 一句话

- **`wilson_loop`**：修复核的协变性、扩大系综后，协变 APE **显著优于 identity**（留出分数 263/233/222，
  三个配对区间都不含 1）；
- **`optimize_gaussian`**：修复特征后学习核比高斯基座好 **2.12 倍**，候选 risk 与 7 参数 SLSQP **未检出差异**
  （0.998 [0.78,1.18]）；
- **`pion_projection`**：参考模型仍不可识别，正式 `score` 保持 `null`；GEVP（C2）与能量目标（C3）
  的合成验证已完成，真实数据需要新测量。

## 1. 结果总表

| task | 修复前 | 修复后 | 统计结论 |
| --- | --- | --- | --- |
| wilson_loop | 旧 APE 核不协变，结果作废 | v3：identity 100、APE(0.4,5) **263.3**、APE(0.4,10) 232.8、APE(0.6087,10) 221.9；v4（+$R=4$）663–808（尺度不同） | 配对中位数 2.8–3.1（v3）/ 6.6–9.5（v4），区间均不含 1 |
| optimize_gaussian | v7：1.52×，候选 0.009597，输给 SLSQP（0.803 [0.636,0.944]） | v9：**2.12×**，候选 **0.007721** vs SLSQP 0.007703 | 配对 **0.998 [0.78,1.18]**，未检出差异 |
| pion_projection | 参考 gate 未过（χ²=52/8，窗口偏移 21.6σ/7.8σ） | 诊断更完整，参考仍不可识别；C2/C3 合成验证通过 | 无正式分数（设计如此） |

## 2. wilson_loop：静态势

### 修了什么

- 逐列 Gram–Schmidt 只保左酉 → 换成**双边极分解** $Q=M(M^\dagger M)^{-1/2}$，det→1；
  满足 $P(gMh)=gP(M)h$；
- 3 个空间方向只有 4 个 staple → 归一化改为 $\alpha/4$；新旧 $\alpha$ 关系 $2\alpha/(3-\alpha)$；
- NERSC 读取校验 `DATATYPE`/`FLOATING_POINT`（真实值是 `IEEE64LITTLE`）/payload 长度；
- 原子保存、每配置 gauge sha256、kernel/git hash、evaluate 校验 development SHA 与 kernel 参数。

### 三个阶段

| 版本 | 留出 | 结论 |
| --- | --- | --- |
| v1 | 30 / 6 blocks | 核不协变，作废 |
| v2 | 30 / 6 blocks | 点估计 3×，区间跨 1 → 未证明 |
| **v3** | **80 / 16 blocks**（200 组态系综） | **区间不含 1 → 显著** |

### 物理读数

$V(1)$ 几乎不变，$V(3)$ 的误差减半（0.0073 → 0.0034），中心值 0.715 → 0.706。涂抹改善的是
大 $R$ 的信噪比。

详见 [`doc/wilson_loop_v3.md`](wilson_loop_v3.md)。

## 3. optimize_gaussian：学习型 smear

### 修了什么

- `plaquette` 路径闭合（原先第二/三段沿错方向平移，不是规范不变的）；
- 特征改为 **link 中心**平均（每条 link 两侧两个 plaquette）再做对称组合；
- 24 个 proper rotation + parity 的协变测试**全部通过**（A1+ 认证）；
- 训练缓存 identity、run manifest（protocol/W/θ/IDs/缓存 key/依赖 hash）。

### 结果

| 版本 | 特征 | 测试 risk | 相对 $G^8$ | 候选 risk |
| --- | --- | ---: | ---: | ---: |
| v7 | 旧的前向锚点 | 0.012870 | 1.52× | 0.009597 |
| **v9** | **link 中心 A1+** | **0.009236** | **2.12×** | **0.007721** |

与 SLSQP 的配对比值 $0.998\ [0.78,1.18]$，统计上未检出差异（区间跨 1，不是等效性证明）。学到的系数从“几乎纯均匀”变成有实质
空间调制（$|v_h|\approx0.13$）。

详见 [`tasks/optimize_gaussian/README.md`](../tasks/optimize_gaussian/README.md)。

## 4. pion_projection：为什么没有可信分数

按诊断链顺序，每一步都排除了一个“本来可以救它”的可能。

### 4.1 参考模型本身失配

单 cosh + 共质量在名义窗口 $[5,6,7,8]$ 上 $\chi^2=52/\mathrm{dof}=8$，窗口偏移 21.6σ/7.8σ；
T=32 上仍失败（$\chi^2=120/11$，偏移 20.3σ/16.3σ）。T=32 归档里的反射 z=274.27 是硬编码
T=16 索引造成的假警报，按真实 $C(t)-C(T-t)$ 应为 2.40——但 χ² 和窗口偏移仍然失败。

### 4.2 统计量不足以识别它

名义窗口是 3 通道 × 5 时间 = 15 维，而只有 12 个 block：样本协方差秩 $\le11$，4 个零特征值。
预声明的 block/shrinkage 扫描（$\{2,3,4,5,6\}\times\{0,0.1,0.25,0.5\}$）里没有任何组合能让
名义参考通过（最大 p=0.0072）。

### 4.3 校准 p 值、加长 T、两态、模型平均都不能救

- 模拟校准 p 值：校准本身正确（合成误判率 0%），但名义参考校准后 p≈0 → 模型偏差；
- 两态：gate 通过，但 8 参数对 12 个点、$\chi^2=0.06$，是过拟合；profile 1σ 宽度 0.04 ≈ 4×
  bootstrap SE（sloppy 方向）；
- 模型平均：AIC/BIC 权重退化为两态（$\approx1$），候选排序随参考翻转。

### 4.4 参考质量的直接影响

固定候选权重、扫描 $m_0\in[1.00,1.10]$：分数在 $m_0\approx1.06$–$1.07$ 处峰值约 25,000，
两端掉到 1,000–5,000（约 7 倍）；tuned/SLSQP 的排序在 $m_0\approx1.06$ 翻转。

固定 $m_0$ 的端到端配对评分（200×128）：

| 参考 | $m_0$ | tuned score | SLSQP score | SLSQP/tuned | 结论 |
| --- | ---: | ---: | ---: | ---: | --- |
| 单 cosh | 1.0862 | 2504 | 4098 | 1.629 [1.398, 2.192] | SLSQP 更好 |
| 两态 | 1.0570 | 18214 | 18119 | 1.089 [0.659, 2.288] | 未检出差异 |
| GEVP | 1.0350 | 6305 | 4425 | 0.701 [0.679, 0.731] | tuned 更好 |

**“谁更好”本身依赖参考质量**：单 cosh 是唯一给出 SLSQP 更好的选择。

> 200 组态 campaign（120 dev / 60 val）后参考**仍然失败**：$m_0=1.0771\pm0.0034$、$\chi^2=90.6/8$；
> 而且 $m_0$ 随统计量漂移（12 blocks 时 1.0862，24 blocks 时 1.0771）。GEVP 平台仍只到 $t=5$。

### 4.5 GEVP 给出的独立证据

- 2×2/3×3 Hankel（powers-of-$H$）没有平台；
- 两族/三族 Gram GEVP（$H^n$、APE-$H^n$、$\alpha=0.4$ 的 $H^n$）在 $t=3$–$5$ 给出
  $m_0\approx1.02$–$1.05$（两族 $1.050\pm0.014$ / $1.036\pm0.017$；三族 $1.035\pm0.010$ /
  $1.023\pm0.024$）；$t=6$ 仍被噪声主导；
- 这些值与两态参考 1.057 在约 $1\sigma$ 内一致，比单 cosh 1.086 低约 2–3σ：**GEVP 证据偏向两态**。

### 4.6 结论

pion 没有可信分数，不是因为“统计量差一点点”，而是因为**参考质量本身在 1.02–1.09 之间不确定，
而分数和排序对它的依赖大于候选之间的差异**。要修，只有三条路：

1. 把 $m_0$ 认证到 $\le1\%$（更多 $t\ge6$ 的统计量，或更好的算符基）；
2. 把 $m_0$ 的系统误差传播进分数（`scoring.py` 的证书框架，对模型集合取同时下界）；
3. 换一个参考更稳的可观测量（能量误差目标，C3 的设计已就绪）。

已建立的工具：`reference.py`（参考 spec 冻结）、`scoring.py`（S1 证书）、`gevp.py` + `gram_gevp.py`
（C2）、`energy_target.py`（C3 合成验证）、`m0_scan.py` / `evaluate_fixed_m0.py`（参考敏感性）。

## 5. 负结果清单

| 尝试 | 结果 |
| --- | --- |
| 只拟合形状（pion/学习核） | 目标可被 game，训练损失到 $10^{-24}$，留出不泛化 |
| 严格非负约束（学习核） | 增益被抹掉（0.956×） |
| 逐方向独立系数 | 破坏立方对称，是过拟合 |
| 加长 $T$ 到 32（pion） | 参考仍失败；反射失败是假警报 |
| 模型平均（pion） | 权重退化，不能救参考 |
| 学习核超过 SLSQP | v9 只做到未检出差异，没有超越 |

## 6. 仍然 NOT_RUN

- pion：真实数据的 C2 多 source 测量（约 4× 反演）、C3 独立 anchor、新盲测；
- wilson：更大 $R$、更多体积/$\beta$、与动力学 QCD 的连接；
- optimize_gaussian：更强的函数类（群平均、多层）或更多数据以图超越 SLSQP。

## 7. 文档与复现索引

| 内容 | 位置 |
| --- | --- |
| 跨任务审计 | [`doc/audit_2026-11-18.md`](audit_2026-11-18.md) |
| wilson v3 结果 | [`doc/wilson_loop_v3.md`](wilson_loop_v3.md) |
| pion GEVP/能量目标设计 | [`doc/pion_gevp_design.md`](pion_gevp_design.md) |
| pion 评分诊断 | [`results/pion_projection/score_diagnostics_v2/`](../results/pion_projection/score_diagnostics_v2/) |
| 学习核记录 | [`tasks/optimize_gaussian/README.md`](../tasks/optimize_gaussian/README.md) |
| todo 覆盖报告 | [`doc/todo_coverage.md`](todo_coverage.md) |
| 测试 | `PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -q -p no:cacheprovider tests/`（104 项） |

## 10. 2026-11-18 晚：按新开工单的审计与实现

这一轮按更新后的三份 `tasks/*/todo.md` 重做，新增结果如下（证据路径都在括号里）。

### pion_projection

- **GEVP 矩阵身份**：sink–sink Gram 与标准 source–sink 矩阵差约 30%，且后者本身有 30% 的
  anti-Hermitian 部分；旧 Gram GEVP 降级为探索性（`doc/gram_operator_identity.md`）。
- **GEVP 统计**：去重 → block bootstrap → replica 平均矩阵 → 秩截断 → 平台；已知谱 100 个独立
  数据集的 95% 覆盖率为 0.95（`gevp_stats.py`、`doc/gevp_stats.md`）。
- **评分契约**：`score_contract.md` + `scoring.py` 强制模型/候选集合、等长 draw、原始正值、
  invalid 比例、近零 baseline、improvement 门槛；反例（未批准模型、广播、负 risk）全部拒绝。
- **联合 resampling**：`joint.py` 在同一 draw 内重拟合参考并评估所有模型/候选；参考 gate 失败 →
  强制 abstain（`results/pion_projection/joint_20261118/`）。
- **双层校准**：完整估计器 24 blocks 假阳性 0.025，fixed-metric 0.095（反保守），6/12 blocks 时
  0.235/0.085；两态真值拒绝率约 0.53（`score_calibration_v1/`）。
- **120-dev 诊断**：秩满但条件数 $10^6$–$10^8$；$m_0$ 随窗口从 1.44 掉到 1.08；两态 profile
  半宽/SE=2.7（`score_diagnostics_v3/`）。
- **nested CV**：5 折、每折重拟合参考/标度/协方差/SLSQP；local/SLSQP 209–750（平均 427±89）
  （`nested_cv_v1/`）。
- **能量估计实验**：单 cosh 偏差 0.0065、覆盖率 0；两态无偏但 SE 0.039；基态消失偏差 0.33、
  覆盖率 0；$N_{\rm boot}$ 增加只缩小 naive SE（`energy_target_v1/`）。

### wilson_loop

- **投影数值边界**：逐矩阵 Newton–Schulz 尺度 + 收敛检查；混尺度 batch 与单矩阵一致（1e-16），
  rank-2 受控拒绝（`audit_20261118_projection/`）。
- **可信加载**：generation、resume 前缀、gauge 头部几何、`trust_status`；v3 归档判
  archived_diagnostic（`audit_20261118_identity/`）。
- **配对审计**：v2 点值 1.07–1.18 vs 嵌套中位数 3.0–3.4；6 blocks 的唯一 block 分布、jackknife
  0.49–4.53、相关性 0.14–0.30 解释了差异（`paired_audit_v1/`）。
- **谱质量**：合成“平但错”反例偏差 170σ、risk $2.7\times10^{-7}$、gate 通过；v3/v4 窗口
  $V$ 图（`spectral_quality_v1/`、`doc/wilson_spectral_quality.md`）。
- **HMC**：manifest 审计（seed 20261109、τ_int=0.512），但 ΔH/接受率/热化声明缺失；toy SU(3)
  积分器可逆性 $10^{-10}$、$\Delta H$ 二阶（`hmc_quality_v1/`）。

### 公共框架

- F0 证据 schema、F1 五类接口与跨入口一致性（4 个下界差值 0；改数据/改协议均 fail-closed）、
  F2 候选校验与搜索/validation 隔离、F3 状态机与成本账本、F4 审计（`doc/interfaces.md`、
  `doc/agent_isolation.md`、`doc/run_state.md`、`doc/evidence_framework.md`）。

### optimize_gaussian

- 完整 BCB 闭环验证通过（非立方格点、多 theta、$f\ne g$，残差 <1e-10；
  `audit_20261118_bcb/`）。
- P0.2（basis/输入身份闭包）与 P0.3（audit 分类/措辞）已做；README 的“打平/追平”已改为
  “未检出差异”。
- 包 A 切片：`train.validate_inputs`（gauge/propagator 摘要、residual、metadata 不符即拒绝）；
  manifest 记录 inputs/environment/reference 状态。
- 包 B 切片：point/replica 同幅度算法；synthetic regression 偏差 −1.9e-6/−1.0e-5、
  q=1 覆盖 1.000/0.983。
- 包 C：独立 train/test links、同一 $Q[U]$ 规则；oracle 显示嵌套类跨 links 误差 0、
  谱类 0.06→0.5；SLSQP/Powell 不收敛（nfev 1.3e4–9.4e4）。
- 包 D：OperatorContract/MeasurementBundle/SearchAdapter 的 CPU 端到端适配；能力拒绝抛错。

### 仍未做（NOT_RUN）

pion 的 §6.2/§7 执行（真实 anchor、共同目标预测、新测量先决条件）；wilson 的 P4 研究扩展、
生产 HMC ΔH/接受率、多 rank；optimize 的 GPU class×optimizer 2×2、消融、新盲测、真实 W 训练。

## 11. 2026-11-19：第三轮工单验收

- pion：完整身份绑定（submission/report/dev/val 内容 SHA、IDs、reference 实现、候选、late metric）、
  gate artifact/score spec 冻结、统一 abstain、rank 合法性网格、χ² subgate 端到端 benchmark、
  三种区间语义与固定数据 Nboot 扫描、测量计划 preflight；
- wilson：真实 pending 恢复、投影支持域、事务故障矩阵、标准 NERSC CHECKSUM、invalid evaluate、
  receipt 证据、comparator 正值契约、外部预算、RunState execution receipts、有限 Nt 文档；
- optimize：可信输入分流、fit-state 保存、公平 2×2（ε=0 精确、ε>0 嵌套类迁移）、
  实际 BCB—response—core search 闭环。

**负结果必须按负结果读**：wilson 两态反例是 gate 盲点（spread gate 通过而 bias/SE 32.5），
pion 0/8 的 CP 区间 [0, 0.369] 不足以声称族错误率受控，optimize 类 B 的 ε>0 零误差是
目标含 $G_0$ 的构造性可表示性结果。未跑项仍为 GPU/新测量/真实 W 训练，逐项标 NOT_RUN。

## 12. 2026-11-18 深夜：新工单的 CPU 闭环

- pion：`reference_gate_calibration_v1/`（dof=8，假拒绝 0.02/0.03、失配功效 0.66/0.59）、
  `certificate_calibration_v1/`（假认证 3/8 @6 blocks、0/7、0/8；J=2/K=2 族 null 0/7）、
  `anchor_calibration_v1/`（naïve null 27–50%，独立 dataset 控制）、`joint_identity_v2/v3/`、
  `certification_v1/`、`nested_cv_v2/`、`gram_stats_v2/`；
- wilson：measure 入口 bug 修复（`test_measure_entry_end_to_end`）、三文件恢复事务、
  投影失败 batch 索引、NERSC checksum trailer、`paired_audit_v2/`（点值重放、leave-one-block-out、
  非退化 coverage 0.983）、`spectral_physical_v1/`（两态反例 bias/SE 32.5）；
- optimize：包 A/B/C/D（`cpu_next_package_b/`、`cpu_next_p3_crosslink/`、`cpu_next_package_d/`）。

三份 todo 的逐项状态见 [`doc/todo_coverage.md`](todo_coverage.md)；当前 104 个 CPU 测试通过。

## 13. 2026-11-19：后续复核与 todo 重整

本节覆盖前文的旧状态与旧测试数；截至 2026-11-19 最后复核，全套 **158 个 CPU / GPU-free 测试通过**（singular-domain 拒绝路径有 1 条 RuntimeWarning）。此前 `104` / `117` / `123` / `125` / `126` / `143` / `150` / `157` 项是
历史轮次快照，不是当前测试结果。

- pion：A1 身份检查加严，验证路径要求完整 report/spec；candidate 在加载 CuPy / PyQUDA 前拒绝身份不匹配。
  paired robust-score CPU 方法诊断、首轮完整 reference-gate 7 场景 × 100 dataset MC 和 GEVP typed failure 已完成；relative-error 场景仍 `INCONCLUSIVE`，纯 E1 有 80/100 通过统计 gate。真实 anchor、新测量与更窄 MC 区间仍开放。
- wilson：P0b determinant-phase 受控切口检查现有 126 格 CPU 结果；F4 receipt/schema preflight 有 1 个合成合法控制和 15 个拒绝负例，但生产 $\Delta H$/接受率仍 `NOT_RUN`。P0/P1/P2/P3、F0–F3 与两态 spread gate 盲点已有代码、测试和诊断；P4 stout 物理比较未执行。
- optimize：修正跨 links 实验为全空间协变 Laplacian、clover $B$、匹配点源/color probes、实系数与相同有界域；
  新结果见 `cpu_close_20261119_C_matched/`。目标含 $BHB$，B oracle 为零是构造性，不是学习收益。
- optimize 包 B：在新目录重跑 60 dataset × 200 draws 的 train-frozen / validation-refit synthetic regression，
  生成 point/replica 偏差与 dataset-level coverage 图。原 `cpu_next_package_b/regression/` 明确降格为 5×20 smoke；
  其测试写入路径已改成临时目录，避免覆盖归档输出。
- optimize v9 learned/SLSQP 比值 0.998 [0.78,1.18] 仍是“未检出差异”；真实 GPU $W$ 训练与盲测尚未运行。
  C 包收敛诊断另显示实化 design 满列秩但列缩放条件数为 $5.52\times10^5$–$6.45\times10^5$；最大固定预算下
  SLSQP 的 KKT 残差约 $10^{-9}$，Powell 起点都耗尽预算。图文见 `cpu_close_20261119_C_convergence/`；这是合成优化器对照，
  不证明学习型物理 smear 的优劣。
- optimize 包 B 新增 200 datasets/cell 的 AR(1) configuration/time noise、block length、错误 reference 与训练幅度传播诊断；
  图和逐 dataset 区间在 `cpu_close_20261119_B_stress_v2/`。正确 reference 下 block length 增大时区间 coverage 下降；错误
  reference 下 true $q$ profile coverage 仍可高而 $q=1$ reference-shape 检查全窗 0/200。它仍是单通道单质量 toy。
- optimize 包 B 的 follow-up 扩展三个质量，每 cell 400 独立 datasets、400 bootstrap draws；正确 reference 的 all-four-time $q=1$
  覆盖为 0.730–0.770，错误 reference 为 0/400（CP95 上界 0.00918），正确 reference 的 pointwise 覆盖仅 0.8975–0.9275。
  [报告和图](../results/optimize_gaussian/cpu_close_20261119_B_multimass_v1/README.md)显示当前 percentile intervals 自身欠覆盖，
  不能把 reference-shape 灵敏度误称为区间校准或 learned 优势。

LatticeArena 可扩展点、各项证据边界和后续 agent 开工方案统一见 [todo 覆盖总表](todo_coverage.md)。

## 14. 本轮完整性复核

- 三份 task todo 均保留：pion amendment02 synthetic full-gate MC 已完成，但严格 source provenance 为 `PARTIAL` 且物理 anchor 未做；Wilson 生产 HMC/P4、optimize GPU 学习对照与扩展 MC 仍有未完成工作。
- Pion 的 `_eigvals` rank/cutoff 修正、负/零/near-zero typed failure 与 2×2 ground-mode 网格均已完成并有测试；无需重跑旧数据网格。
- Wilson 原 90 格投影域扫描的 `phase` 字段没有直接控制实际 $\arg\det M$（随机 U(3) QR 因子带入自身 determinant phase）；已新增 determinant 受控 126 格扫描，切口外协变残差最大 $9.9\times10^{-11}$，精确端点中心分支 outlier 为 7 格，均有图文记录。
- `unified_v1/` 覆盖事故、GPU 未运行状态与小样本 MC 限制已在工单记录；覆盖事故的“无法恢复”仅指仓库 git 证据，未声称排除了外部备份。
- C2 certificate-calibration cell 多为 6–8 个独立 dataset，C3 anchor simulation 为 30 个；Optimize C 已在三 seed 诊断外新增20个独立 links/probes datasets，但 N=20 仍是有限扩展。旧样本量只支持 smoke / 方法诊断，发表级错误率和功效仍需预注册扩样。

## 15. 2026-11-19：task TODO 完整性复核

- 三份 `tasks/*/todo.md` 都保留：各自仍有未完成研究，不能因为本轮 CPU 切片有结果就整份删除。Pion 的 rank / cutoff 负谱语义和有限 ground-mode 网格、Wilson 的受控 determinant-phase 126 格扫描、Optimize B/C 的 stress 与收敛诊断均有相应实现、测试或图文结果。
- 后续 CPU 切片已分别补入工单：Pion 完整 gate 首轮 MC（7×100）、真实文件入口 adapter parity、v2 estimand mismatch 的0/2814前置诊断、amendment01 alpha混用负诊断、score/smear alpha分离和amendment02七场景full-budget dry-run及402/cell主MC；Wilson F4 schema preflight、P4 402/cell controls、stout opt-in kernel/contract；Optimize B 三质量/time-AR stress、C links/probes 扩展和通用及 H/B cross-link learned-initializer toys。synthetic / oracle 与物理证据区分；最新全套测试为158 passed。
- 用户转述的 `unified_v1/` 覆盖事故、旧点值留档和仓库 git 内无法恢复旧 fold 内容，与 package B README 一致；该结论只限定仓库证据，不排除外部备份。
- “未做项都需要 GPU / 授权”不准确：Pion amendment MC、Wilson CPU controls、Optimize operator initializer 可在 CPU 做；真实 pion anchor、Wilson HMC/物理配对及 Optimize W 训练/盲测仍依赖生产 GPU 数据。
- Pion adapter smoke parity 不能支持原 v2 402/cell MC：固定候选 estimand、scenario和预算不匹配，原计划0/2814。amendment01虽完成七场景dry-run，但代码把`protocol.alpha=0.2`的smear系数传给统计score alpha；该主MC在595/2814停止，null候选认证92/402、CP95 [0.189,0.273]仅为错误level=0.2诊断。参数拆分后，amendment02 full-budget dry-run核对五条完整路径的score alpha/level均为0.05；修正版402/cell MC已完成2814/2814。null certification 28/402（CP95 [0.0468,0.0991]）包含5%但不能证明假认证率≤5%；wrong-state在ground overlap=0时仍343/402认证，relative-error valid-only acceptance 25/60为`INCONCLUSIVE`。高层 preregistration 的 adapter hash 与执行 spec / 2814 receipts 不一致，无法判断是元数据还是行为差异，因此结果仅作synthetic diagnostic、严格来源链为`PARTIAL`；图文与复核见 `results/pion_projection/full_gate_amendment02_execution_01/ANALYSIS.md` 和 `RUN_REVIEW.md`。真实anchor仍未运行。
- Wilson P4 扩为每类402个独立数据集后，common-bias synthetic control 中 legacy gate 402/402通过、oracle gate 402/402弃权；这展示当前 spread gate 的 toy 盲点，不证明 oracle gate 能迁移到生产。stout 作为显式非默认 kernel 接入，默认 APE 未变。
- Optimize learned-initializer CPU tests 显示低预算下可优于部分 zero/random SLSQP 起点，但项目 H/B IID strong spectral 略优，且高预算 SLSQP 更低；不支持稳定超越强基线，更不构成 learned smear 物理优势。
- 后续要求统一为图或文字诊断：按场景给出原始数据集数、错误/弃权/失败计数、MC 区间、图表和边界说明。任务级下一步以 [`doc/todo_coverage.md`](todo_coverage.md) 和三份 task todo 为准。

## 16. 2026-11-19：Wilson paired-budget 与 Pion source-aligned replay 收口

- **Wilson P4 nested-prefix 配对预算**：每个效应 402 个独立 synthetic datasets，80/160/320 为同一 dataset 的嵌套前缀。弱 1.78×输入方差改善的三组配对率差区间均跨零；4×改善的 80→160 为 +5.97 pp（paired bootstrap CI95 [2.24,9.95]），160→320 为 +1.00 pp [−2.49,4.48]。320 配置 364/402，CP95 [0.873,0.932]，满足预注册检出率≥0.90及下界≥0.85目标，但不说明 160→320 边际增益已分辨。见 [结果与图](../results/wilson_loop/audit_20261119_p4_nested_prefix_v2/README.md) / [图像](../results/wilson_loop/audit_20261119_p4_nested_prefix_v2/nested_prefix_diagnostics.png)。仍是 oracle-anchor synthetic test。
- **Pion amendment03**：7×402=2814 同 seed source-aligned replay 完成。13-file frozen manifest、plan/prereg/executor、current sources、2814 receipts 与核心代码 hashes 一致；development/validation 原始 arrays 2814/2814 完全相同；status、reference acceptance、candidate certification、其他确定性字段均 0/2814 不一致。2070 `PASS`、744 `EXPECTED_REJECTION`、0 意外执行失败。它证明在新 frozen manifest 下同一 synthetic 路径可重现，不是独立 MC，也不修复 amendment02 旧 preregistration hash 冲突；后者继续标 `PARTIAL`，`physical_score=null`。并发从6调至10以缩短执行时间，旧 spec 和执行 amendment 均已归档。
- 初步重述的三项 agent 结论：`unified_v1/` 覆盖事故在仓库范围内记录正确，但不能推断外部备份不存在；指出的真实 GPU / 生产数据工作未运行是正确的，但“所有未做工作都需 GPU”太宽，family-wise robust-score CPU 校准及某些明确预注册的合成敏感性仍能用 CPU 做；C2/C3 的 6–30 datasets/cell 小样本提醒成立，同时需要与 Pion 402/cell 的后续 MC、Optimize C N=100、Wilson 402/cell 分开说明，样本数不会消除结构偏差或物理系统误差。
- **三个 TODO 均保留**：Pion 下一项是 family-wise robust-score 的多候选/多窗口校准（交 false-certification/power/abstention 图）及独立物理 anchor；Wilson 是生产 HMC ΔH/接受率诊断与独立 gauge IDs 上的 matched stout/APE 图文；Optimize 是真实 learned $W$ 对同预算 SLSQP 与强谱基的 GPU blind-test，提交 paired-risk、收敛/成本、失败图表。此轮未重跑全套测试；上次记录为158项通过，本轮对新增后处理脚本做语法解析并对修改过的 Markdown / TODO 做 `git diff --check`。

## 17. 2026-11-20：Pion family-wise robust-score 首轮校准

- **实验设计**：另建 family-wise v1/v2 目录；v1 的零效应离 5% 最低改善门槛较远，结果 0/2500 只作 far-null negative control。v2 在每个 trial 使用 30 个独立 synthetic datasets、4 candidates × 4 frozen reference/window branches、2500 outer trials；以 log-improvement = log(1.05) 作为最不利 null 边界，比较 absolute paired risk difference、relative log-risk、pointwise t、branch-wise Bonferroni 与 dataset-level max-t。
- **边界结果**：Gaussian boundary 下 pointwise FWER 为 absolute 9/2500（CP95 [0.0016,0.0068]）、relative 11/2500（[0.0022,0.0079]）；Bonferroni 两者均 0/2500（CP 上界 0.0015），max-t 各 1/2500（上界 0.0022）。heavy-tail / 单数据集 outlier stress 下 pointwise 为 8–15/2500，Bonferroni 为 0/2500，max-t 为 0–2/2500。
- **功效与弃权**：10% 真改善时 candidate A power 为 pointwise 30.5% / 37.7%、Bonferroni 2.0% / 3.2%、max-t 5.9% / 8.8%（absolute / relative）。near-zero baseline 下 relative 方法均按冻结 floor 弃权 2500/2500；common-bias 下六种方法均 2500/2500 错误认证，显示统计方法不能替代独立物理 anchor。
- **解释限制**：当前 DGP 令候选之间相关较高，pointwise family error 低于名义 5% 不能外推至低相关候选家族；Bonferroni/max-t 的假认证少但功效也低。Absolute margin 取 baseline scale 的 5%，相对门槛为 ratio 1.05，两者略有差异，分开解释。所有区间是 synthetic outer-trial event-rate 的 CP 区间，不是物理 coverage。
- **图文和复核**：见 [v2 README](../results/pion_projection/familywise_score_cpu_20261120_v2/README.md)、[边界误认证放大图](../results/pion_projection/familywise_score_cpu_20261120_v2/familywise_calibration_zoom.png)、[弃权与共偏差图](../results/pion_projection/familywise_score_cpu_20261120_v2/abstention_bias_diagnostics.png) 和 [hash receipt](../results/pion_projection/familywise_score_cpu_20261120_v2/execution_provenance.json)。模拟器 verify 核验通过；全套测试本轮未运行。
- **对其他 agent 复核意见**：unified_v1 覆盖与仓库内旧 fold 不可恢复的说明正确，不能推断外部备份不存在；真实 anchor、Wilson HMC/物理配对和 learned W 盲测确实未运行且依赖生产输入/GPU，但“所有未完成项都需要 GPU”不成立，family-wise 与若干稳健估计量比较仍可 CPU 推进；C2/C3 的 6–30 独立 dataset/cell 小样本限制成立，不能把它与 402/cell full-gate MC 混为一谈。
- **当时的 TODO 结论（由 §18 更新）**：三个文件均应保留。写入此段时 Pion 的候选相关性扫描和 robust estimator 比较仍开放；这些 CPU 项现已由 v3 完成，当前未完成项改为独立物理 anchor / 新测量。Wilson 仍尚需生产 HMC 和 matched stout/APE 物理比较；Optimize 仍尚需真实 W、metadata、同预算强基线及盲测。

## 18. 2026-11-20：Pion family-wise score v3 与三个 TODO 复核

- **v3 已补完此前 TODO 列出的 CPU 方法学首轮**：在 ρ=0.05/0.35/0.65、每 cell 2500 outer trials、每 trial 30 independent datasets、4 candidates × 4 reference/window branches 上比较 candidate-level IUT + Holm/Bonferroni、branch Bonferroni-16、max-t-16、20% trimmed 和 Huber。协议和 source/output hash 的 `--verify` 检查通过；逐例 synthetic 结果保存在 [v3 报告](../results/pion_projection/familywise_score_cpu_20261120_v3/README.md)。
- **主要诊断**：Gaussian `log(1.05)` 边界下 pointwise FWER 为 3/2500、39/2500、130/2500（0.12%、1.56%、5.20%），随候选相关性上升；ρ=.65 时 IUT Bonferroni、branch Bonferroni、max-t、trimmed、Huber 分别为 21、4、23、18、25 / 2500。10% 真改善、ρ=.35 时检出率为 pointwise 69.0%、IUT Holm 41.4%、branch Bonferroni 19.2%、max-t 35.7%、trimmed 28.2%、Huber 39.2%。三张图分别显示相关性与边界 FWER、10%/6% 功效、reference/window conflict 与 wrong-state/common-bias 结构负控。
- **不能下的结论**：Huber/trimmed 没有在所有相关结构/离群设定下稳定优于 mean；wrong-state proxy 与 common bias 下所有七种规则均 2500/2500 错误认证。v3 没包含 near-zero baseline abstention（该项见 v2），equicorrelation 也不能代替真实 correlator covariance；所有结果是 synthetic method calibration，不能认证 physical score。
- **TODO 审计决定**：三个 `tasks/*/todo.md` 均保留，因为尚有未完成的核心证据门槛。Pion family-wise v1–v3 第一轮 CPU 对照已完成，下一 agent 不应重做；主要下一步是独立 physical anchor / 新测量、完整 provenance 和窗口/残差/anchor-bias 图。C2/C3 的 6–30 datasets/cell 仍是小样本；若其扩样会改变决策，须先预注册 MC 精度并用独立 seeds，单独报告 CP 区间、失败/弃权与图文，不能和 402/cell 或 2500-trial 结果合并。Wilson 保留真实生产 HMC 与 matched stout/APE 物理配对；Optimize 保留真实 learned W、metadata、强基线与一次性盲测。
- **核验范围**：重新核验 v3 `--verify` 成功；没有重跑 158 项全套 CPU tests，也未运行 GPU/HMC/anchor 生产任务。三个 TODO 和覆盖总表已据此更新。

## 19. 2026-11-20：Pion χ² subgate 1000/cell CPU 扩样

- **问题与方案**：原 C2 子门 smoke 的 0/8 双侧 CP95 区间为 [0,0.36942]，无法判断 5% χ² gate 是否校准。为检验该子门在明确 synthetic DGP 下是否随统计量变化，预注册三个世界（正确 ground-state null、single-cosh reference misspecification、纯 E1 wrong-state），每个 6/12/24-block cell 使用 1000 个独立 development datasets；输入、fit/gate 路径、seed、排除规则和 N=1000 下预期 null CP95 半宽 0.0141 均在主模拟前冻结。
- **结果**：正确 null 的拒绝率在 6/12/24 blocks 下为 151/1000=15.1%（CP95 [12.9%,17.5%]）、54/1000=5.4%（[4.1%,7.0%]）、18/1000=1.8%（[1.1%,2.8%]）；前后两档均不包含名义 5%，显示这一 χ² subgate 在该 generator/covariance setting 下有明显 block-count 敏感性。misspecified-reference 拒绝率分别为76.9%、92.1%、99.8%。纯 E1 world 的 gate pass 为 751/1000、912/1000、967/1000，最高统计量仍有 96.7% 接受单态拟合，拟合优度不能认证态身份。全 9000 个数据集拟合有效，无 `INVALID`。
- **图与来源**：冻结报告和逐例结果见 [README](../results/pion_projection/certificate_subgate_mc_20261120_v1/README.md)；原始冻结图保留，补充可读图和出图来源见 [PLOT_REVIEW](../results/pion_projection/certificate_subgate_mc_20261120_v1/PLOT_REVIEW.md) / [plot review provenance](../results/pion_projection/certificate_subgate_mc_20261120_v1/plot_review_provenance.json)。主执行器 `--verify` 核验 9 cells × 1000 rows 及 source/protocol/output hashes 成功。
- **解释边界与下一步**：该 run 只估计 production `fit_reference_gate` 的 χ² 子门，不跑 full certificate 或 J=2/K=2 family；旧 family 仍 valid N=6。C3 anchor (N=30) 和 GEVP grid (N=20/cell) 仍是有限模拟。它们只有在能改变决策时才应另行预注册扩样。Pion 首要未完成证据仍是独立物理 anchor / 新 GPU 测量；全套 CPU tests 本轮未重跑。

## 20. 2026-11-20：Pion χ² subgate 协方差 shrinkage 配对敏感性与 TODO 复核

- **冻结设计**：对每个 6/12/24-block ground-state-null 配置生成1000个独立 datasets；同一 dataset 依次通过生产 gate 的协方差 shrinkage λ=0、0.25、0.5，避免把生成差异混入 shrinkage 比较。预注册 source/protocol/output hashes、逐例状态、invalid 计数、CP95 marginal intervals、六个 paired contrast 的 95% familywise bootstrap intervals 与诊断图均保存在[结果目录](../results/pion_projection/certificate_subgate_shrinkage_20261120_v1/README.md)，`--verify` 已成功。
- **结果**：λ=0/0.25/0.5 的 null rejection rate 在 B=6 为100.0%/16.0%/2.6%，B=12为70.1%/5.4%/0.8%，B=24为28.1%/2.5%/0.5%。相对生产 λ=0.25，λ=0 的 paired 差为+84.0、+64.7、+25.6个百分点，六项 familywise CI 均不跨零；λ=0.5 差为−13.4、−4.6、−2.0个百分点，区间也均不跨零。图表显示当前 synthetic 子门对 block 数与 covariance shrinkage 都敏感；λ=0 在 B≤12 时样本 covariance 秩亏并受 eigen floor 影响，λ=0.5 在此 generator 下偏保守。
- **边界与建议**：不能用这些点值挑 λ 来“调到”名义 5%，也不能外推到真实 ensemble 或 full certificate。若继续 CPU 方法学，需先做分因素 preregistration：已知 covariance 的 nominal χ² 基线、估计 covariance 下 rank/shrinkage/eigen-floor 分离、以及 production p-value 与参数/块自举 reference 的预设对照；报告逐 cell p-value calibration、size CP95、rank/condition 图、INVALID/失败计数和解释。若不能改变 production gate 决策，应停止合成微调，优先独立物理 anchor。
- **其他 agent 提交的三项说明复核**：①`cpu_next_package_b/README.md`及当前仓库状态支持“包B开发时同名输出覆盖`unified_v1/`、旧 fold 未入 git、旧文件无法从当前仓库恢复”；这只证明仓库内不可恢复，不能推断外部备份。②他们列出的 Pion 新测量、Wilson F4 生产 ΔH/接受率与 P4 物理配对、Optimize 真实 W/metadata/盲测确实需要真实生产输入与对应 GPU/集群；但“所有未完成工作都需 GPU”不成立，Pion C2 family/C3/GEVP若能影响决策仍有 CPU 方法学空间。③C2/C3 小样本提醒成立：C2 完整 J=2/K=2 family valid N=6，C3 anchor N=30，GEVP 为20 datasets/cell；应和C2单态χ² 1000/cell、full-gate 402/cell、family-wise 2500 outer trials分开，不互相借用样本量或MC精度。
- **TODO 决定与下一步**：三个 `tasks/*/todo.md` 均保留。Pion 优先是独立 anchor、新 GPU 测量、provenance/12-RHS 残差及窗口/质量残差和 anchor-bias 图；若另做 CPU calibration，按 TODO 中的因素分离方案输出 size/p-value、CP95、rank/condition 图和失败文字。Wilson 下一项是冻结参数下的 F4 生产 HMC ΔH/接受率与热化/autocorrelation 诊断，再做独立 gauge IDs 的 matched stout/APE paired comparison。Optimize 下一项是完成 P3 生产数据 2×2 与metadata复采，然后真实 learned W 对 Gaussian、同预算 SLSQP、强谱基线的一次性 blind test，交 paired-risk、收敛/残差、walltime/training 成本与失败图文。每项未完成任务必须保留 NOT_RUN/INCONCLUSIVE 边界。
- **本轮核验范围**：核对了三个 TODO、覆盖表、status、相关结果目录和仓库跟踪状态；没有重跑全套测试。缩减 covariance shrinkage 结果的主执行器与 provenance 校验已核实，源于独立 synthetic MC 而非物理数据。

## 21. 2026-11-20：Pion known-covariance 与 estimated-covariance 分因素校准

- **冻结方案**：用 Gaussian linear null $p=12,q=4,\nu=8$，AR(1)-like covariance $\rho=0.6$，扫描 $B=6,12,24$ independent blocks。每个 B/method 使用5000个独立 calibration datasets 和另一组5000个 evaluation datasets；方法包括 exact known covariance control、以及从 B 个样本估计 covariance 后采用 shrinkage $\lambda=0,0.25,0.5$。方案在运行前冻结；12个 cells 均有 raw quadratic forms、rank、eigen-floor fraction、condition number、校准 p-values 和 hash provenance，`--verify` 通过。报告和图见[结果目录](../results/pion_projection/certificate_subgate_factorized_20261120_v1/README.md)。
- **结果**：exact covariance control 下 nominal $\chi^2_8$ size 为4.8–4.9%。估计 covariance 的 nominal size，按 $B=6/12/24$ 排列：$\lambda=0$ 为100.0%/69.3%/29.1%，$\lambda=0.25$ 为20.9%/7.5%/3.2%，$\lambda=0.5$ 为5.9%/2.0%/0.8%。$B=6,\lambda=0$ 的经验95%临界值是 nominal $\chi^2_8$ 临界值的$4.01\times10^8$倍，median raw covariance rank为5/12且median eigen-floor fraction为58.3%；$B=12$ 的median rank为11/12。独立 calibration sample 排名得到的 held-out Monte Carlo p-value size 为4.4–6.0%。
- **解释边界**：控制协方差结果验证名义 reference 在固定线性高斯设定下表现正常；样本协方差结果表明小 B 秩亏、eigen floor 与 shrinkage 会联合作用。独立 rank calibration在同一DGP下回到约5%是预期内部校准，不证明对真实相关函数或 production nonlinear mass fit 的迁移。下一项若仍有 CPU 决策价值，应预注册实际 `fit_reference_gate` 的 conditional parametric/block bootstrap 与 generator-shift comparison；否则优先等待独立物理 anchor，不通过选择 λ 追逐名义 size。

## 22. 2026-11-20：Pion production-fit 条件参数自举与生成器偏移

- **冻结设计**：在 ground-state-null `certificate_calibration.world` 上，按 Euclidean-time AR $\rho=0.5$ baseline 与 $\rho=0.8$ shifted generator、$B=6,12,24$ blocks，每 cell 250 independent outer datasets；每个数据集做399个 plug-in Gaussian bootstrap draws。自举先从生产 `fit_reference_gate` 取得拟合 mass/amplitudes 与归一化参考向量协方差，使用 production shrinkage $0.25$ 和 eigen floor $10^{-10}$ 生成伪 block vectors，再逐次重估协方差并重跑实际 gate/nonlinear mass fit。invalid bootstrap draw 按保守上尾计，不删除；计划共598500个bootstrap拟合，全部有效。冻结协议/source/output hashes及逐例数据在[报告目录](../results/pion_projection/certificate_subgate_bootstrap_20261120_v1/README.md)，另有[可读图审查](../results/pion_projection/certificate_subgate_bootstrap_20261120_v1/PLOT_REVIEW.md)。
- **结果**：baseline $\rho=0.5$ 下 nominal-$\chi^2$ / bootstrap rejection 在B=6为41/250=16.4% / 3/250=1.2%（paired差−15.2 pp，familywise CI95 [−21.6,−9.5] pp）；B=12为15/250=6.0% / 8/250=3.2%（差−2.8 pp [−6.0,−0.4]）；B=24为6/250=2.4% / 4/250=1.6%（差−0.8 pp [−2.4,+0.0]）。shifted $\rho=0.8$ 下两规则均非常保守，6/12/24 blocks 拒绝率为0–0.4%，N=250的CP区间上界约1.5–2.2%。
- **解释与限制**：plug-in conditional bootstrap 显著降低 baseline 小 B 的拒绝率，却在多数cell低于5%；它不能作为已校准替代门。rho=.8 是 Euclidean-time noise correlation shift，不是 gauge-trajectory autocorrelation。外层N=250导致区间较宽；bootstrap生成还以拟合 Gaussian mean / regularized covariance 为条件，无法解决 generator misspecification或physical anchor缺失。只有结果可能改变production gate决策时，才值得继续扩大外层MC或比较其他bootstrap机制；不应通过选shrinkage调到目标size。

## 23. 2026-11-20：Pion GEVP ground-mode N=400/cell 独立扩样

- **冻结方案**：对原 GEVP ground-mode 2×2/rank=2 网格使用独立数据 seeds 扩至 16 cells × 400 datasets；每 dataset 200 bootstrap draws，bootstrap index seeds也按 dataset 独立。保持 noise={0.01,0.05}、gap={0.1,0.5}、$t_0={1,2}$、cutoff={1e-8,1e-5}、120 configurations/block length=5及固定 plateau定义不变。N=400对应二项覆盖率最坏情形 CP95半宽约0.05；没有事后补样。source/protocol/output hashes、逐数据集结果、failure reasons 与`--verify`成功记录见[报告](../results/pion_projection/gevp_ground_failure_expanded_20261120_v1/README.md)和[补充热图](../results/pion_projection/gevp_ground_failure_expanded_20261120_v1/PLOT_REVIEW.md)。
- **结果**：6400/6400 datasets 有效，外层失败和 recorded GEVP failure events 均为0。16 cells 覆盖率为0–4.0%，只有4 cells非零，CP95上界最高约6.4%；mean bias为0.0124–0.0360，dataset-bootstrap CI95约窄至$10^{-4}$量级；within-dataset bootstrap SE仅0.00063–0.00321。原N=20/cell的低覆盖现象由独立扩样确认，cutoff差异很小。
- **解释边界**：该扩样只说明固定 synthetic 两态世界中，此Gevp估计量的bootstrap normal interval严重欠覆盖，系统偏差高于区间所见的随机误差；不能外推为真实 pion correlator 的错误率，也没有把系统偏差纳入物理误差预算。C3 anchor仍N=30，C2完整J=2/K=2 family仍valid N=6；它们若扩样，需另行预注册、说明对决策的影响并提供独立seed与图文诊断。

## 24. 2026-11-20：C3 anchor 三场景独立扩样与 TODO 再审

- **扩样范围**：原 C3 anchor grid 每 cell 30 datasets。另按独立方案对 improvement、null、anchor-bias 三个选定场景各生成400个datasets，每个dataset的 baseline/candidate mass 各有200个bootstrap draws；raw outcomes、协议/source hash、汇总、图和 `--verify` 均在[结果目录](../results/pion_projection/anchor_calibration_expanded_20261120_v1/README.md)。
- **统计诊断**：naive `sd/sqrt(Nboot)` 的认证率为181/400、146/400、199/400（45.3%、36.5%、49.7%）；单dataset paired 5th-percentile rule 为0/400、0/400、73/400（0%、0%、18.2%），六重 familywise CP95 已列于 README。三种 independent-repeat mean delta 的 familywise dataset-bootstrap CI 都跨0。结果加强了 pseudo-replication 会让 bootstrap draw-level interval 过度认证的证据。anchor-bias cell 的 candidate noise=.01而baseline noise=.02，包含真实的两臂噪声差，不是 bias-only null；18.2%不能叫假认证率。要估计纯 anchor 偏移下的 false-certification，仍需另一个两臂同噪声的 null。
- **图表处理记录**：主计算全部完成后，当前 Matplotlib 版本因 `Axes.boxplot(labels=...)` 参数不兼容而在写图阶段退出。补绘脚本只读取既有 raw/summary、改用 `tick_labels=` 并生成图、README 与 provenance，没有重算或更改样本；执行器 `--verify` 随后通过。[PLOT_REVIEW](../results/pion_projection/anchor_calibration_expanded_20261120_v1/PLOT_REVIEW.md)记录该修复边界。
- **复核三项 agent 说明**：包 B 同名输出覆盖、旧 fold 未入 git且当前仓库不可恢复的说明与本地证据相符，但不能推断外部备份不存在。真实 Pion anchor、新测量、Wilson HMC/生产 ΔH 与物理 stout/APE、Optimize 真实 W/metadata/盲测确实需要生产输入与相应 GPU/集群；“所有未完成工作都需 GPU”仍然过宽，Pion C2 full-family synthetic校准和有明确决策目的的 bias-only null仍可在CPU执行。C2 full J=2/K=2 family仍valid N=6；C3原始网格仍30/cell，但选定的三种场景已有400/cell；不能与full-gate 402/cell、family-wise outer trials或GEVP 400/cell混并。
- **TODO 决定与下一步**：三个 task 的核心目标都未完成，因此三个 `tasks/*/todo.md` 均保留。Pion 优先执行真实独立 anchor / 新测量；若 CPU 结果确会改变 gate，再单独预注册 C2 full family 或两臂同噪声的 anchor-bias null，提供事件率 CP95、逐例拒绝/弃权/失败和图文。Wilson 下一步为有授权后完成 F4 生产 ΔH/接受率和独立 gauge IDs 上的 matched stout/APE；Optimize 下一步为真实 metadata 复采、P3 2×2 与一次性 learned-W blind test，对照 SLSQP 和强谱基，并交 paired-risk、成本/残差与失败图文。
- **验证边界**：本轮核验了 C3 frozen hashes、1200条记录（3×400）及最终图文；未重跑全套158项CPU测试，也未执行GPU/HMC或真实物理测量。

## 25. 2026-11-20：C3 anchor-bias-only null 与三个 TODO 最终复核

- **新增 CPU 诊断**：第24节 C3 `anchor_bias` 场景的 candidate noise=.01、baseline noise=.02，不是 null。为直接检验 anchor 偏差本身，另冻结等噪声 null：两臂都使用 noise=.02、相同真谱；每个独立 dataset 生成/拟合两臂一次，随后在相同质量抽样上评估 anchor offsets −.02、0、+.02。共400个独立 dataset IDs，每臂200个 bootstrap draws；±.02 取自先前冻结敏感性，不按新结果挑阈值。方案、逐例结果、hash 与图见[结果目录](../results/pion_projection/anchor_bias_null_20261120_v1/README.md)。
- **结果**：naive `sd/sqrt(Nboot)` 假认证分别178/400、176/400、186/400（44.5%、44.0%、46.5%）；当前 single-ensemble paired 5th-percentile 为45/400、45/400、62/400（11.3%、11.3%、15.5%）。在无 anchor offset 时 paired 认证的六率 familywise CP95 为[7.5%,16.0%]，高于名义5%。因此 paired 规则在该固定 generator 下比 naive 低，但仍不具名义 size。各 bias 下独立重复 mean-delta familywise CI 都跨0；anchor offset 相对零偏移的配对认证率差 CI也跨0，不能断言±.02本身显著改变错误率。400样本的区间仍只约束这个 synthetic estimand。
- **图与复现**：Figure 同时显示 false-certification 率与 familywise CP95、dataset-level paired-delta 分布；脚本为 [`anchor_bias_only_null.py`](../tasks/pion_projection/anchor_bias_only_null.py)。新 run `--verify`、C2 family N=400 `--verify`、C3 三场景 N=400 `--verify` 均通过。没有重跑全套测试（上次记录158 passed），也没有执行GPU/HMC或真实 anchor 测量。
- **对其他 agent 三项说法的复核**：`unified_v1/` 同名覆盖及旧 fold 未入 git的说法与 package B README / 当前 tracked 状态一致；只能说当前仓库内不能恢复，不能推断外部备份不存在。Pion真实 anchor、新测量，Wilson F4生产ΔH/接受率与matched stout/APE，Optimize真实W/metadata/P3盲测仍需GPU或生产输入；但“所有未做工作都要GPU”不成立，已有与本轮完成的CPU校准即为例子。小样本提醒正确但需分开分母：C2 J=2/K=2 family从valid N=6扩到400计划/183有效；C3三个预选场景和bias-only null各400，原完整C3 grid仍30/cell；C2其他子门仍有6–8/cell。不能与Pion 402/cell full-gate或2500-trial family-wise实验互借精度。
- **TODO 决定**：三个 `tasks/*/todo.md` 都保留，因为核心物理证据未闭环。Pion 下一步为独立 physical anchor / 新测量，并以独立配置或块层级 uncertainty 设计能通过 null 与 known-improvement 的评分；不要重复同一 synthetic generator。Wilson 下一步为有GPU和输入后执行F4真实trajectory质量诊断，再做独立 gauge IDs matched stout/APE；Optimize 下一步为production metadata复采与P3 2×2，然后真实 learned W 对 Gaussian、同预算 SLSQP 和强谱基盲测。所有交付都需按各 TODO 给图、置信区间/成本与失败样本文字。完成前不得删除任一 TODO，也不把 synthetic结果标为 physical score。

## 26. 2026-11-20：C3 matched-ID common-block 重采样与下界规则复核

- **术语修正**：早先 C3 anchor expansion / bias-only 报告中的 “paired 5th-percentile” 指对两臂风险差抽样后取 lower quantile；两臂使用独立样本和独立 bootstrap indices，并不等于在同一组 configuration IDs 上共用 block-index matrix。anchor-offset 的 dataset-level 对照使用同一 outer dataset 的多种偏移结果，因此也不能据此称两臂重采样已配对。历史数值不变，但解释边界应按其实际索引方式理解。
- **common-block 方法对照（合成数据）**：新增[common-block报告](../results/pion_projection/paired_block_anchor_score_20261120_v1/README.md)与[lower-bound follow-up](../results/pion_projection/centered_anchor_score_20261120_v1/README.md)。每个 quality × matched-arm noise-correlation 条件有400个独立 IDs；每个 dataset 120个配置、configuration AR(1) ρ=.5、block length 5、200 bootstrap draws。对照相同 configuration IDs 下的 common block indices 与独立两臂 indices，并在新独立 seeds 上比较 percentile、basic/reflected、bootstrap-normal 三个冻结下界。报告各有逐例数据、协议/source/output hashes、familywise区间和图。
- **结果**：equal-noise、anchor无偏 null 下，common-block 三个下界在 matched-arm ρ=.5 的假认证率依次为18.0%、19.3%、18.0%；ρ=.9时为18.0%、16.3%、16.8%，均明显高于5%。对应 common-block known-improvement power 约14.0–18.2%；basic/reflected 与 bootstrap-normal 没有一致修复 null size / power 的权衡。独立两臂indices在ρ=.9时假认证为0.5–1.0%，但已知改善 power也仅4.5–5.0%。因此共同配置配对是保留相关结构的必要方案，但未经校准的 lower-quantile 仍不稳健；独立indices的低错误率也不能单独作为合格分数证据。
- **解释边界与后续**：这是固定 anchor、特定 Gaussian/AR(1) synthetic generator 的 estimator comparison，不是物理 false-certification、真实 correlator coverage 或 gauge autocorrelation 诊断。停止在该 DGP 上继续换公式。后续优先获取真实独立 anchor / 新测量；若 CPU 方法研究能改变明确决策，先注册 null-imposed/studentized cluster inference 或带明确可交换假设的 block-level randomization，并用新 covariance / tail / anchor-uncertainty generator 做 blind evaluation，提交 size、known-improvement power、abstention/failure、familywise CP95、paired-difference 与 anchor-sensitivity 图及文字限制。
- **复核其他 agent 的三项说明**：package B README 与当前 git tracked 状态支持“旧 `unified_v1/` fold 当前仓库不可恢复”，但不能推断外部备份不存在。GPU 相关的真实 Pion anchor、新测量、Wilson HMC ΔH/接受率与物理 stout/APE、Optimize 真实 W/生产 metadata/blind test仍未完成；“所有未做项都需要 GPU”不成立，CPU 方法支线仍可在明确目标下做。小样本提醒方向正确，但要分开分母：C2 J=2/K=2 family已有400计划、183 valid；C3预选场景和多项 null/score 对照均400/cell，原全网格仍30/cell；其他C2子门仍有6–8/cell，full-gate 402/cell、2500 outer-trial 和不同模块的样本不可互借。
- **TODO 决定**：三个 `tasks/*/todo.md` 都保留。Pion 下一步优先独立物理 anchor / 新测量；若转 CPU 方法比较，仅按任务 TODO 中的独立生成器、预注册、校准与图文条件推进。Wilson 继续等待 F4 生产 ΔH/接受率和 matched stout/APE gauge inputs；Optimize 继续等待真实 metadata / $W$、P3 2×2 与 blind IDs，再按同预算比较 learned smear、SLSQP、强谱基。三项交付均需图或可读表格、失败/弃权计数和解释边界。
- **本轮验证**：`paired_block_anchor_score --verify` 与 `centered_anchor_score --verify` 均通过；后者校验了19,200条记录与冻结 hashes。肉眼检查了新生成的 null-size / power / anchor-sensitivity 图；未运行全套测试，也未执行真实 GPU/HMC 测量。

## 27. 2026-11-20：Pion studentized paired-block randomization 与三项 TODO 状态

- **决定与约束**：前一轮 common-block bootstrap 与 percentile/basic/bootstrap-normal 都在固定 Gaussian/AR(1) equal-noise null 下出现约16–19%假认证；只有一个明确理论条件下的方法才值得继续CPU诊断。这里预注册的条件是独立 paired configuration blocks，并且在 sharp no-arm-effect null 下每个块内两臂标签可交换； pooled reference 对这些交换保持不变。
- **冻结与执行**：新脚本 [`block_randomization_score.py`](../tasks/pion_projection/block_randomization_score.py) 在执行前冻结 protocol、六个源文件哈希与 seed。其后执行5种世界（Gaussian equal-arm、common truth shift、Student-t5 equal-arm、uncertain anchor、known lower noise）× 两种 matched-arm noise correlation，400 outer datasets/cell；每个 dataset 24 个 paired blocks × 5 configurations，999 次 sign-flip 与 bootstrap draws。共4000 dataset/correlation cases，因 Gaussian/Student-t5 null 各有三种anchor offset，写出7200条逐场景行；7200/7200 均 valid。`python -B -m tasks.pion_projection.block_randomization_score --verify` 核对5×2×400结构以及 protocol/source/output hashes 通过。原始数据、数值表和冻结结果图见[主 README](../results/pion_projection/block_randomization_score_20261120_v1/README.md)。
- **结果**：zero-offset 等效应世界的 sign-flip certification rates 在2.8–6.0%之间，所有报告的 familywise CP95 仍较宽，故只称与名义5%相容，不称已校准。known-lower-noise alternative 的检出率为ρ=.5时40/400=10.0%，ρ=.9时84/400=21.0%。paired t 与 sign-flip 配对差在两种功效 cell 分别为−0.25 pp（familywise dataset-bootstrap CI95 [−2.50,+1.75]）和+0.25 pp（[−1.50,+2.00]），没有分辨出方法差。paired-block bootstrap 功效高+6.00 pp和+5.75 pp，但零效应 Gaussian cell 的认证也多+1.50/+3.00 pp；较高 certification 不等于校准更好。anchor offset 与各 null size 的区间图及 paired method contrasts、解释和结果 hash 见[可读图文复核](../results/pion_projection/block_randomization_score_20261120_v1/plot_review/PLOT_REVIEW.md)。该复核只重排 frozen raw/summary，不改任何统计结果；图已肉眼检查。
- **适用边界**：sign-flip 的理论有限样本保证只针对明确的 sharp exchangeable null 与独立块；不覆盖所有“平均 risk 相同”的 weak null，不对 gauge-trajectory 自相关做验证，不能发现两臂共同的错误模型/态，也不等同于 full-ensemble `improvement_certificate`。这些结果全是 synthetic CPU method diagnostics，不是物理 coverage 或可直接投入生产的分数；没有使用同一校准集调阈值。
- **三个 TODO 审核**：pion 的真实独立 anchor / 新测量，optimize 的真实 metadata、生产 P3 2×2 与真实 learned-$W$ blind test，以及 Wilson 的生产 F4 $Delta H$/acceptance 与 matched stout/APE 物理对照仍未完成。故三个 `tasks/*/todo.md` 都保留。接手者应优先完成各自 TODO 中的生产输入与盲测；pion 不再重复本轮或 common-block 固定 generator，只有新 weak-null / covariance 问题确会改变决策时才另开预注册实验。
- **验证边界**：本轮执行 synthetic block-randomization 与只读补图；没有重跑全套 CPU 测试（最近记录为158 passed），没有 GPU/MPI/HMC/真实物理测量。

## 28. 2026-11-20：生产归档复核与三份 TODO 状态更正

- **Wilson HMC 归档复核**：在 `results/kunshan_logs/hmc_production.log` 中发现一段真实 Kunshan/HIP 运行记录，日志报告 $16^4$、$\beta=6.0$、120 steps、seed 20261109、$\tau=0.5$、900 trajectories、100个保存配置、rounded aggregate acceptance=0.972、401.5秒；每20条轨迹打印一次记录，共45个稀疏 $\Delta H$ checkpoints。对照 `hmc_quality_v1/manifest_snapshot.json`，日志的100个 saved rows 全部匹配manifest的前100/200项（ID、trajectory、plaquette）；manifest余下100项在trajectory 901–1396，日志没有覆盖。首个save在401只能作为观测到的输出边界，不是热化 cut 声明。45个后段checkpoint的 $\Delta H$ 均值/样本SD为−0.00959/0.06695，只是稀疏描述量，不是逐trajectory分布或自相关校正估计。
- **身份限制**：日志写到 `data/S16T16`，snapshot `ensemble` 字段为 `LatticeArena-pilot`，旧 HMC quality README 曾称 `S16T16C`，而 `protocol_v4.json` 指向 `S16T16B`。本地没有 gauge files；manifest hashes 无法与实际 bytes 核验。故先前“整个工作区没有生产 $\Delta H$/acceptance 证据”应修正为“存在部分归档证据”；protocol_v4 的生产 receipt / `physical_status` 仍 `NOT_RUN`，stout/APE物理配对也未做。抽取脚本、逐点CSV、统计JSON、散点诊断图和边界说明见[报告](../results/wilson_loop/hmc_log_archive_diagnostic_v1/README.md)。
- **Optimize v9 口径复核**：v9 已有 link-centred feature 修复后的 GPU 系数重训和 test IDs 70–99 held-out evaluation；$R_{SLSQP}/R_{learned}=0.998$、95% CI [0.78,1.18]，reference gate仍失败、official score为null。README §8 明确 $W$ 是固定随机特征基、没有训练，拟合的是系数；因此“trainable $W$ 尚未训练”正确，但“没有 GPU 训练或 test split”不正确。v9 test 已报告，不能再称未观察的 blind set。当前 TODO 改为补齐 v9 完整运行/设备 provenance，并在生产 P3 2×2 后，使用新 gauge IDs 评估 trainable-$W$ 或 learned initializer 对 SLSQP 与强谱基。
- **其他 Agent 说明的判定**：同名覆盖事故由 package B README 与 git 当前状态支持“仓库内旧 fold 不可恢复”，外部备份未检查；“所有未做项都需 GPU/授权”不成立，GPU 主要阻塞新的物理测量，其他方法探索需按是否改变决策决定；小样本提醒只对部分子问题仍成立，不能把不同分母混为一谈：Pion C2 J=2/K=2 为400计划、183 valid，χ²子门有1000/cell；C3原完整网格仍30/cell，但预选 anchor / bias-only / common-block / sign-flip等已有独立400/cell结果。每个结果只支持自己对应的 generator。
- **TODO 决定与下一位 Agent 的工作**：pion、optimize_gaussian、wilson_loop 三份 TODO 均仍有未完成生产门槛，全部保留。下一位 Agent 按各自 TODO 首先恢复/核对真实输入与身份；Pion取得独立 anchor / 新测量，Optimize补齐 trainable-$W$ 计划、P3 2×2和新 blind test，Wilson解决HMC manifest/log/ensemble身份并补完整F4或说明无法恢复、随后做独立stout/APE配对。所有新诊断均需配图或可读数值表、失败/弃权说明和适用边界；现有synthetic generator不得仅为增加N而重跑。
- **本轮验证**：`python3 -B -m tasks.wilson_loop.hmc_log_diagnostic` 生成归档诊断；`python3 -B -m tasks.wilson_loop.hmc_log_diagnostic --verify` 的输入/输出哈希校验通过；`git diff --check` 通过。未重跑全套测试、未连接GPU/集群、未核验远端备份或实际gauge文件。

## 29. 2026-11-20：Kunshan pipeline provenance 交叉审计

- **Pion GPU 归档**：[跨文件 audit](../results/kunshan_logs/archive_audit_v1/README.md)解析到60条开发和30条验证测量。90/90 `gauge_sha256` 与 Kunshan 100配置 manifest 同ID一致，且90/90条目的残差、cache key、耗时、plaquette、memory 字段与仓库 `s16t16_v1` development/validation provenance 逐项相同。最大记录残差为 $9.9924\times10^{-11}$，无行超过目标 $10^{-10}$；总耗时中位数2.717秒/配置。图展示了按ID的残差与耗时，灰区为预留 IDs 60–69。
- **分数与复用关系**：历史 `s16t16-pilot-v1` 参考质量仍失败：$m=1.08617$、SE=0.00307、$\chi^2/\mathrm{dof}=52.00/8$、近似 $p=1.68\times10^{-8}$，另外两个参考窗相对名义窗漂移21.62σ与7.82σ，故 `score_status=unscored_reference_failed`。`optimize_gaussian/v9/manifest.json` 引用同一 `validation_provenance.json`，test IDs 70–99 完全重合；它们已被观察，不能当作新 blind test。该记录是旧 signed-mixture pilot，不证明 v9 的 $W$ 被训练或其 training 环境已完整复现。
- **Wilson 身份冲突**：`hmc_production.log` 的100个 SAVED rows 与 Kunshan 100项 manifest、HMC quality 200项 snapshot 前缀在 ID/trajectory/plaquette 上匹配；但SAVED行没有 hash。Kunshan manifest 与 snapshot 的首100项 hash 为0/100一致，而90条 pipeline hashes 与 Kunshan manifest 一致。由于 gauge bytes 不在本地，不能判定是哪套 hash 与 HMC 输出字节相符；也不能把这段记录归为 protocol_v4 `S16T16B` 完整receipt。
- **后续开工顺序**：三份 TODO 都保留。Wilson 先向归档提供者核实 hash 输入与格式并恢复 trajectory>900 的日志和 gauge bytes；拿不到时重跑冻结 F4 并记录逐轨迹 $\Delta H$/接受状态、thermalization 与 $\tau_{int}$。Pion 使用新的独立 gauge IDs 获取 anchor / validation，先过参考与残差诊断再计算 physical score。Optimize 完成 trainable-$W$ 或学习初始化的定义与生产 P3 2×2，在未观察的新 IDs 上和 Gaussian、同预算 SLSQP、强谱基配对比较。所有诊断继续给图或清楚数值表、失败/弃权和边界。
- **本轮执行**：`python3 -B -m tasks.kunshan_archive_audit` 生成逐配置 crosswalk、summary、图和 provenance；`python3 -B -m tasks.kunshan_archive_audit --verify` 校验输入与输出 hashes；只读检查原始归档，未运行 GPU/HMC 或全套测试。

## 30. 2026-11-20：Pion weak-null 与 Wilson toy-force CPU 补充

- **Pion 分数稳健性**：[预注册 weak-null 诊断](../results/pion_projection/weak_null_nonexchangeable_20261120_v1/README.md)每 cell 3000 个独立 synthetic datasets，比较 paired t、raw sign-flip、centered wild sign-flip、block-bootstrap percentile 与带已知方差上界的 MoM bound。rare-tail equal-mean null 下常见 plug-in/resampling 方法在24 blocks的假认证为9.4%–16.6%，48 blocks仍为9.4%–10.6%；MoM为0/3000，但依赖物理数据目前没有的有效方差上界，且强+1.5σ场景power为94.8%/99.9%。这是对特定 synthetic DGP 的方法反例，不是 production score选择或物理校准。经版式复核的[图和复核记录](../results/pion_projection/weak_null_nonexchangeable_20261120_v1/PLOT_REVIEW.md)读取冻结 summary，没有改动模拟数据；TODO因此不再重复同一rare-tail generator，下一步仍优先拿独立物理anchor。
- **Wilson toy analytic force**：[CPU审计](../results/wilson_loop/audit_20261120_hmc_force_fd_v3/README.md)对两个周期$2^4$ SU(3) link fields的512个link-generator分量扫五个中心差分步长，共5120个对照；归一化误差在$10^{-4}$处最大$2.49\times10^{-9}$，action场依赖显式循环残差$2.56\times10^{-13}$。解析力 leapfrog步长减半时$|\Delta H|$约缩至四分之一，正反向可逆性约$10^{-15}$。首轮误把action零点差异判作绝对action不一致，v2保留失败过程，v3显式处理加法常数−288后通过。该结果关闭toy CPU有限差分项，不能外推到production HMC；F4仍需权威gauge身份、完整逐轨迹数据或新GPU receipt。
- **TODO 状态**：三份 task TODO 继续保留。Pion与Wilson新增结果均提供图、逐例数据及文字限制；Optimize的CPU initializer toy 已完成，但learned-$W$ 对SLSQP/强谱基的真实blind比较仍待新生产数据。
- **本轮验证**：Pion weak-null主结果、plot-review与Wilson toy-force v3 的数据/哈希验证通过；未运行全套测试，也未连接GPU/MPI。

## 31. 2026-11-20：Wilson HMC 接受率重建与分母敏感性

- **来源与推导**：归档 log 的 DONE 行写 `trajectories=900 accept_rate=0.972`，但这900是计划轨迹数。运行说明记录 `max_save=100`、每5条保存一次，最后一条保存轨迹为896；当前生成器在第100个保存后退出，并用 `accepted / args.trajectories` 计算 DONE 值。45个稀疏累计率在该格式规则下唯一反推出轨迹881时已接受860次。若历史脚本与当前源码一致，DONE 的0.972唯一对应875次接受，因此实际运行率为875/896=97.656%（21次拒绝），打印值875/900=97.222%低0.434个百分点。
- **分母敏感性**：该运行没有 run-specific source hash。若历史程序改为用实际停止轨迹896作为 DONE 分母，0.972也唯一对应871/896=97.210%（25次拒绝）；此时末段轨迹882–896为11/15次接受，而当前源码解释给出15/15。当前仓库的生成器与运行说明支持 planned-denominator 情形，但不能证明它就是当次执行文件。v2因此同时报告两种解释，不恢复未记录的拒绝位置，也不计算假设独立的二项区间。
- **诊断输出**：[v2图文报告](../results/wilson_loop/hmc_acceptance_reconstruction_v2/README.md)含累计接受率和分窗接受数图、45个 checkpoint 的整数计数、46个不重叠窗口表、JSON汇总、输入/代码/输出哈希及复核命令。旧 [v1 结果](../results/wilson_loop/hmc_acceptance_reconstruction_v1/README.md)保留原样，并用 `RUN_REVIEW.md` 说明其单一分母解释已由v2补充。
- **边界与后续**：这比“接受数完全不可恢复”更强，但仍只是 source-assisted 部分归档证据，不是生产 receipt。F4 仍缺权威 gauge-byte / source identity、逐轨迹 $\Delta H$ 与接受决定、预声明热化 cut、$\tau_{int}$ 规则和 `S16T16B` 身份；因此 Wilson TODO 保留。下一位接手者优先核实实际运行脚本哈希及 gauge hash 输入约定、恢复轨迹896之后的数据；无法恢复时按冻结协议重新采集完整 receipt，并提供 $\Delta H$ / 接受率随轨迹图和热化、自相关文字诊断。
- **本轮验证**：`python3 -B -m tasks.wilson_loop.hmc_acceptance_reconstruction verify` 通过，核对45个 checkpoint、46个窗口及冻结输入/输出哈希；此前 Pion weak-null、其 plot review 和 Wilson toy-force v3 的验证均已通过。本轮未重跑全套测试或连接 GPU/MPI。

## 32. 2026-11-20：optimize_gaussian v9 源码 provenance 恢复

- **源码 hash 复核**：[v9 provenance audit](../results/optimize_gaussian/v9_provenance_audit_v1/README.md)逐项核对 manifest 的四个训练依赖。features.py、kernels.py、submission.py 与当前源码 hash 一致；当前 train.py hash 不同，但 manifest 所需的旧字节在本地 Git commit ea83f9ed0934 中精确找回。manifest 记录的 pion statistics.py hash 也与当前文件一致。因此 v9 的声明源码依赖已 4/4 恢复，统计依赖已恢复；后续不必再重复搜索这些源码版本。
- **身份与输入边界**：20/40/30 的 fit/dev-val/test IDs 两两不交，90个 cache key 与这些 ID 的并集一致；但 test IDs 70–99 与历史 pion validation 的 30 个 IDs 完全相同，不能作为 fresh blind test。v9 manifest 没有训练环境、GPU/driver、依赖锁定或运行命令 receipt，也没有为十个归档输出绑定 hashes；本地无顶层 data/ 目录，原始 gauge/propagator bytes 未恢复。历史训练源码显示随机固定 W、优化的是系数，因此不能称作 trainable-W 训练。完整逐项表和当前 artifact hashes 见 audit README / CSV。
- **下一步与 TODO 状态**：这只关闭源码字节可恢复性，不关闭 v9 的设备/运行/输入 provenance，也不改变真实 learned-W 盲测未完成的结论。已在 [optimize TODO](../tasks/optimize_gaussian/todo.md) 和 [覆盖表](todo_coverage.md) 中改为优先找回运行 receipt 与原始输入；找不到时明确列缺项，然后完成生产 P3 2×2 与 fresh gauge IDs 上的 learned-W/initializer 对照 SLSQP 和强谱基，交付配对风险、收敛、成本、失败图文。
- **本轮验证**：`python3 -B -m tasks.optimize_gaussian.v9_provenance_audit verify` 通过：4/4 manifest 源码 hash 可恢复、30/30 test IDs 与已用 validation 重合，五个冻结审计产物的 hashes 匹配。未重跑 GPU、训练或全套测试。

## 33. 2026-11-20：Optimize initializer 训练成本摊销

- **计算**：[成本摊销图文](../results/optimize_gaussian/cpu_initializer_amortization_v1/README.md)从冻结的 H/B operator-initializer raw 记录中读取每 cell 40条已观察 test-link wall times 与一次训练/选择耗时1.339 CPU秒，按 $T_{\rm learned}(N)=T_{\rm train}+N\bar t_{\rm learned}$ 计算部署总成本；没有重跑 generator、修改原始结果或估计 timing CI。
- **结果**：相对 zero/random SLSQP，按平均 CPU时间摊平训练成本需 IID 预算25/100/400下2,906/364/192次部署，epsilon-shift下5,203/416/216次。相对当前 fixed spectral baseline，六个 cell 的 spectral 平均单例时间都低于 learned initializer，因此本实现下没有 CPU 时间交叉。配对风险的方向并不一致：IID 的 spectral baseline 略优于 learned，epsilon-shift 中 learned 风险较低；高预算下 SLSQP held-out risk 更低。
- **边界**：这是同一合成 operator toy 的事后成本分析，epsilon-shift 只改变 $\epsilon$，每 cell 仅40个已观察测试链接；单机 CPU 时间不能预测 GPU，也不代表 trainable-W、learned smear 或物理泛化。TODO据此保留“有限预算 warm-start 有条件可行”的假设，但不重复同一 benchmark；真实比较仍需 fresh gauge IDs 和匹配 objective-call / walltime 的 SLSQP、Gaussian 与强 Chebyshev/spectral arm。
- **本轮验证**：`python3 -B -m tasks.optimize_gaussian.initializer_amortization verify` 通过，重算6个 population×budget cells、240条 source timing rows，并核对5个审计产物 hashes；成本图已检查。本轮未运行全套 tests 或 GPU。


## 34. 2026-11-20：三份 TODO 的续查与本地可执行边界

- **Pion 来源审计**：amendment02 高层 preregistration 声明的旧 synthetic_adapter.py SHA-256 为 `206cce77df19375fe79a02bc796806d572775c0f6a0e8df18b0b7ff0a9aa9f7d`。本轮读取当前 Git object database 全部 1,077 个 blob 并逐个计算内容 SHA-256，没有命中。结论只限当前仓库对象库；不排除外部备份。amendment02 继续标 `PARTIAL`，只有原运行者提供旧源文件及当次 receipt 才能闭合旧 run；若无法恢复，amendment02 继续标为 PARTIAL。按新协议重采是独立新证据，amendment03 同 seed replay 也不修复旧来源缺口。
- **本机执行能力盘点**：Python 可导入 NumPy、SciPy、Matplotlib、h5py；CuPy、torch、mpi4py、PyQUDA/pyquda_utils 不可导入，`nvidia-smi`、`nvcc`、`mpiexec`、`mpirun` 未找到。仓库常见 gauge-data 后缀 `.h5/.hdf5/.lime/.ildg/.scidac` 没有原始输入；存在的 `.npz` 是分析/模型产物，不能当作 gauge-byte provenance。故本轮没有执行或伪造 Pion anchor、新 gauge measurement、Optimize P3 GPU 2×2/新 blind test、Wilson protocol_v4 HMC 或 stout/APE 物理配对。
- **TODO 完整性核查**：逐项解析三份 TODO 的本地 Markdown 链接，Pion 66、Optimize 20、Wilson 30 个目标全部存在；三份文档中引用的 7 个静态图文件均存在。结合各任务现有 raw outcomes、图文报告和仍未闭合的生产门槛，三份 TODO 都应保留。各自开工条件与验收图表已写在 [Pion TODO](../tasks/pion_projection/todo.md)、[Optimize TODO](../tasks/optimize_gaussian/todo.md) 和 [Wilson TODO](../tasks/wilson_loop/todo.md)。
- **验证边界**：本轮做了本地 Git 内容 hash、输入文件后缀、运行依赖和 TODO 引用完整性盘点；没有重跑全套 158 项 CPU tests，也没有运行 GPU/MPI/HMC。所有新结论均为本地文件/环境盘点，不是新的物理结果。

## 35. 2026-11-20：GEVP200 与 Wilson snapshot 身份交叉核查

- **直接观察**：[逐 ID crosswalk、CSV 和身份矩阵图](../results/kunshan_logs/pion_gevp200_snapshot_crosswalk_v1/README.md)比较已有 provenance 字段，不读取 gauge bytes。Pion `s16t16_gevp200` 的 120 个 development IDs (0–119) 与 60 个 validation IDs (140–199) 对 Wilson 200 项 HMC snapshot 的 hash 字段和 plaquette 均为 180/180 匹配，最大 residual 为 $9.9964\times10^{-11}$。在 ID 0–99，GEVP200 对主 Kunshan manifest 为0/100 hash字段匹配、plaquette 100/100匹配；历史 `s16t16_v1` pilot 对主manifest为90/90 hash字段匹配。GEVP200与旧pilot重叠的90个数字ID，其hash字段0/90匹配。数字ID因此只能当作run-local标签。
- **来源证据边界**：GEVP200 provenance 记录的旧 `measure.py` SHA-256 字节可在当前 Git 历史中恢复；其记录的 kernel hash 与当前源码相符。它佐证了测量程序身份字段，但没有独立重算 raw gauge bytes、证明 HMC `SAVED` 行的实际文件字节，或解释主 manifest 与 snapshot 的 hash 差异。GEVP200 validation 的 reference gate 失败、`score_status=unscored_reference_failed`；它不是可接受的物理 anchor，也不能作为尚未观察的 blind validation。
- **对用户转述的其他 agent 结论复核**：`unified_v1/` 覆盖事件在仓库范围内记录成立，但不排除外部备份；specific physical tasks（Pion新anchor、Wilson完整F4/真实stout-APE、Optimize trainable-$W$/new blind test）确实缺少生产GPU/独立输入，但“所有剩余工作都需要GPU/授权”过宽，CPU方法学诊断仍可开展，现有若干CPU项已完成；C2/C3小样本警示正确，但需与之后各自预选场景的独立N=400扩样、Pion full-gate 402/cell、family-wise 2500 outer trials区分，扩大N只改善对应synthetic estimand的MC精度，不消除结构偏差或物理系统误差。
- **TODO 决定与下步**：Pion、Optimize、Wilson 三份 TODO 均保留，因为各自的物理/生产闭环仍未完成。已把 crosswalk 图文及身份边界写入三份 TODO、覆盖表、Kunshan 报告和 `STATUS.md`。之后不重复本地 ID/hash 字段比对；先向原生产者索取 raw gauge bytes、snapshot 生成脚本/receipt 与 hash 输入和序列化规则，补充 HMC `SAVED` 与轨迹>900 数据。若无法取得，在 Wilson TODO 依冻结 protocol_v4 完整重采；Pion和Optimize则使用独立新 gauge IDs 完成其生产 anchor / P3 2×2 / trainable-$W$盲测，均交付配对差图、残差/收敛/成本图、失败样本表和解释文字。
- **验证**：`python3 -B -m tasks.kunshan_gevp200_crosswalk verify` 通过：snapshot/GEVP200 hash字段180/180相符、主manifest 0/100相符、逐ID输出200行且冻结产物哈希匹配。未运行全套tests、GPU/MPI/HMC或新物理测量。

## 36. 2026-11-20：Kunshan 原始 gauge bytes 全量复核与 TODO 决定

- **直接观察**：用只读 `kunshan` SSH alias 运行 `python3 -B -m tasks.kunshan_live_archive_audit build`，完整扫描远端 `S16T16`（100 files）、`S16T16B`（200）和 `S16T16C`（200），总计约18 GB。各自 raw-file SHA 与远端 manifest 均500/500匹配；两个本地 manifest/snapshot 副本也与远端 JSON逐字节一致。跨目录 full-file SHA均0匹配，但 `END_HEADER` 后 payload 相同率分别100/100、100/100、200/200。故主 manifest 与 snapshot 的旧 SHA-256冲突是 NERSC header 字节差异，header后的 gauge payload 实际相同。Pion pilot 90/90 provenance hashes匹配S16T16 raw files；GEVP200 180/180匹配S16T16C raw files。身份矩阵、逐ID CSV、HMC图和解释见[live audit report](../results/kunshan_logs/live_archive_audit_v1/README.md)。
- **HMC 证据与限制**：S16T16B/C两份batch scripts与当前归档源码逐字节一致；manifest均记seed 20261109。两份日志70个共享 checkpoint 的 accept flag、plaquette、ΔH和累计接受率70/70一致，200个 overlap gauge payload 也200/200相同；这强烈支持同seed重复链，不把两目录当作独立样本。B日志 `DONE=0.977`、planned=1400 对应1368 accepted；依据当前匹配源码和 `max_save=200` 规则，source-assisted停止为trajectory 1396，实际aggregate rate 97.994%。因为日志不逐轨迹记录决定、且无run-specific source hash，不能将重建称为完整F4 receipt。探索性plaquette tau敏感性也不能替代预声明 thermalization/autocorrelation 规则。
- **对其他 agent 结论的复核**：`unified_v1/` 被覆盖的记录在当前仓库范围成立，但不证明外部备份不存在。物理生产任务确实还需要 GPU 与独立输入；不过“所有未做项都必须 GPU/授权”过宽，本次大规模只读hash审计无需GPU job，若干 synthetic CPU方法学项目也已完成。C2/C3小样本担忧正确，但应区分原始 N=6–30/cell cells 与后续独立 N=400/cell扩样、Pion full-gate N=402/cell等；这些扩样只提高各自 synthetic estimand 的MC精度，不提供物理系统误差保障。相关数字与图文要求已写入三份 TODO。
- **TODO 决定**：Pion、Optimize、Wilson 三份 TODO 均保留。Pion仍需新独立 HMC chain / anchor sample、通过 reference residual 和 wrong-state/null/abstention 检查后才报告 robust physical score；Optimize仍需补 v9 propagator与运行 receipt，完成 trainable-$W$或 initializer 对 SLSQP、Gaussian、强谱基的生产配对与 fresh blind test；Wilson的 raw gauge identity 已解决，但仍需完整逐轨迹HMC receipt或冻结协议下的重采，并完成真实stout/APE配对。每项下一步都需逐例表和可读图或文字诊断、区间、失败/弃权样本和适用范围。`todo.md` 只有在这些目标闭合后才删除。
- **本轮运行验证**：live audit `build` 成功；`python3 -B -m tasks.kunshan_live_archive_audit verify` 通过，检查了冻结报告、CSV、图和 payload identity counts。图已打开检查。没有运行全套测试、GPU/MPI/HMC或新测量；远端只读访问总读取量约18 GB，没有下载原始 gauge 文件或提交作业。

## 37. 2026-11-20：三项 TODO 复核、HMC 生产诊断与下一步分割

- **完成性判断**：Pion、Optimize、Wilson 三份 `tasks/*/todo.md` 均保留。Pion 的新 correlator measurement/independent anchor 尚未运行；Optimize 的新 propagator、生产 P3 2×2、trainable-$W$ 与 blind comparison 未运行；Wilson-loop production measurement 及 matched-cost stout/APE 配对未运行。各 TODO 已按本轮实际证据更新，并明确需要交付的图、逐配置表、失败/弃权计数和边界文字。
- **HMC直接证据**：Kunshan DCU job 128526595 (D) 完成1396条轨迹，400热化、996生产，保存200个配置；job 128528670 (E) 完成896条轨迹，400热化、496生产，保存100个配置。D/E各自逐轨迹日志、receipt、manifest、运行代码/launcher hash闭合；200/200与100/100 raw payload hashes核验通过。只把摘要、manifest、日志与图文复制回工作区，未复制原始gauge文件。
- **质量诊断边界**：D生产接受率982/996=0.98594（exact CP95 [0.9765,0.9923]）、ΔH均值0.00117、plaquette τint约3.76；E为483/496=0.97379（CP95 [0.9556,0.9860]）、ΔH均值0.00320、τint约4.03。跨链plaquette均值差9.68×10⁻⁵；按trajectory block length 1/2/5/10/20/50，其相对combined block SE为3.29/2.59/1.97/1.60/1.30/1.01，显示差异对自相关处理敏感。诊断不证明equilibrium、topological tunneling或物理score；`physical_status=NOT_RUN`。图文见[主链](../results/wilson_loop/hmc_production_20261120/diagnostic/README.md)、[独立链](../results/wilson_loop/hmc_anchor_20261121/diagnostic/README.md)和[跨链比较](../results/wilson_loop/hmc_chain_comparison_20261120/README.md)。
- **Pion plan amendment**：当前使用D0–99 development、E0–59 independent anchor、D100–139 gap、D140–199 holdout。HMC receipt里原提议D100–119作为anchor的字段保留作历史，不能改写；新Pion测量plan使用E链替代。D140–199为Pion validation、Optimize blind test及可能Wilson对照共用；三方需在首次读取前共同冻结protocol、candidate/score、源码和分析hash，解盲后跨任务结果只能算相关证据。
- **软件验证**：修复Pion READY/resume计划闭环与anchor报告全hash绑定，并让reference-fit失败也生成score-null图文报告、阻断blind validation；新增失败路径测试后全套CPU测试为 **161 passed**，1条已知Wilson projection rejection RuntimeWarning仍在。未运行Pion/Wilson/Optimize物理测量。
