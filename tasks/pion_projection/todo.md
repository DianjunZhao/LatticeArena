# pion_projection：第三轮验收后的有限剩余工作

审计日期2026-11-19；实现基线 `b3f03a7`。**PARTIAL_NOT_FINAL：保留本文件。**
主agent本轮运行104项CPU测试，全部通过（23.36s）；另有本文两个无落盘mock反例。
本轮审计未重新执行GPU、MPI、远程测量或模型API；GPU结果属于归档证据。
本轮只修改三份task todo，源码、历史结果与其他文档不变。公共接口由[Wilson框架负责人](../wilson_loop/todo.md)维护；学习核fold内重训归[Gaussian任务](../optimize_gaussian/todo.md)。

## 1. 已关闭的具体切片与物理边界

任务固定point source，设计零动量pseudoscalar空间sink。Wilson κ=0.14；空间周期、费米子时间反周期；meson周期cosh；质量为am。
几何 `[x,y,z,t]`，links `(3,z,y,x,3,3)`，方向x/y/z；field `(z,y,x,color,nrhs)`。
`K=Σu_n H^n/A_n`是实际bilinear核，不是把同一组合再次施加两腿；signed overlap可为负。

| 已完成切片 | 证据与关闭范围 |
| --- | --- |
| 参考factory/冻结kind、动态反射 | `reference.py`、`experiment.py`及回归；T32旧274.269是假索引警报，修正2.398，不再重修 |
| Gram对象推导 | [算符说明](../../doc/gram_operator_identity.md)、Gram identity数值；明确sink Gram不等于标准source–sink变分矩阵，不作为独立anchor |
| GEVP估计顺序与失败语义 | `gevp_stats.py`：replica均值矩阵后解、去重、forward/cosh、固定平台整replica策略、local/whole失败计数；关闭这些切片，rank合法性与有限网格见B |
| GEVP窄合成benchmark | 已有100独立dataset coverage0.95；只支持声明生成族与模式，不认证真实基态 |
| score数组契约 | `scoring.py`的名称/shape/draws/原始正值/invalid检查，以及公共check_draws的一维约束已修；公共ratio其他边界仍见Wilson F1 |
| joint抽样与存储 | `joint.py`已保存共同dev/val内外索引、draw IDs、manifest、bootstrap mean与point值；剩余身份和最终状态见A |
| 200配置诊断 | [score_diagnostics_v3](../../results/pion_projection/score_diagnostics_v3/README.md)：120dev、60val、24开发blocks，cov已满秩 |
| outer cross-fit训练 | `nested_cv.py`已折内重拟合reference/尺度、选幂次、SLSQP、冻结训练metric；固定策略outer cross-fit切片关闭，不要求补无必要的inner选择 |
| C1自由度和null模拟 | `reference_gate.py`已dof=dim−nchannels−1，区分渐近p与dataset内null模拟；剩余正式路径一致性见C |
| 能量估计benchmark | `energy_experiment.py`已correlator→fit→bias/variance/MSE/coverage；单态失配、弱基态反例保留，非真实anchor认证 |

GEVP适用边界：当前按本征值排序、未做跨replica激发态mode tracking；已有固定ground-mode benchmark不扩大成全谱认证。多态tracking可延期，但原待办的rank检查与有限ground-mode敏感性网格不能默默删除。

当前真实归档仍未认证参考：`s16t16_gevp200/validation_results.json` 名义 `am=1.077112714±0.003357843`，χ²=90.641168/8，窗口漂移27.92σ/12.61σ。
4–8/5–8/6–8 covariance rank15/12/9；raw condition约3.55e8/5.54e7/8.41e6。满秩解除旧12blocks代数限制，不证明模型可信。

![固定参考质量的条件敏感性](../../results/pion_projection/score_diagnostics_v2/m0_scan.png)

该图只扫描假定m0下的risk/比分，显示排名可交换；绿色旧Gram范围不是独立anchor误差带。
log或有界变换不能修复reference依赖。没有可信基态参考时，输出abstain/diagnostic_only是合格负结果。

## 2. 有限CPU包A：同kind身份与最终状态一致性

本轮两个不落盘反例（未改归档）：

1. 用twostate档案，mock identity为合法并mock conditional certificate为`certified=True`，实际运行joint控制流 `outer=1,inner=2`。
结果顶层 `status=abstain, failure_reasons=[gate_artifact_missing]`，但内部candidate仍 `certified=True`。
**这是控制流反例，不是1个draw产生真实统计认证。**
2. 内存把同kind validation report的`submission_sha256`、`validation_sha256`改为`WRONG`，只mock文件文本，实际`verify_run_identity`返回 `('twostate', [])`。
证明当前检查没有绑定这两项；旧跨kind问题已修，不重复要求。

- [ ] A1：`identity.py`在读取/重采样前核对submission/report/dev/val完整身份：实际内容SHA、完整protocol、IDs/行数、reference实现、候选和late metric。
- [ ] A2：gate artifact绑定同一冻结reference/window/数据/分析，拒绝同kind旧报告或变化metric；joint调用可信load_data/reference验证路径。
- [ ] A3：统一最终abstain处理，任何理由都清除全部candidate.certified；缺artifact/旧legacy可明确diagnostic_only，不伪造新认证。
- [ ] A4：joint读取开发冻结score spec或明确标注临时单reference条件诊断；α、比较族、risk floor、baseline分辨阈值不能在验证后任意变更。
- [ ] A5：manifest绑定submission、gate、spec和实现依赖；同seed复现；不以事后记录新hash代替事前一致性拒绝。

输入：当前归档的只读副本/合成tmp fixtures。输出新目录 `results/pion_projection/audit_<id>/`，存在即拒绝覆盖。
交付：`joint_identity_audit.json`及数值文字表，列合法重放和同kind旧report、val重排/改行、metric/源码变化、缺artifact五类负例。
验收：合法路径可运行，变化路径fail closed；顶层与内部状态一致。停止：若legacy身份不足，只关闭为不可认证档案诊断，不硬补字段冒充原冻结。

## 3. 有限CPU包B：rank合法性与ground-mode敏感性

`_eigvals`显式rank会覆盖正值阈值mask；本轮无盘调用
`_eigvals(I,diag(-1,1),rank=2)`返回`[NaN,NaN]`并触发sqrt warning，`rank=0`反而选中全部两态。
上层能计NaN失败，不等于已验证rank。当前结果是固定rank/t0诊断，未见原计划的有限敏感性网格。

- [ ] 检查rank整数/范围/所选metric本征值正性及分辨阈值；非法输入返回明确原因，不先做非法开方。
- [ ] 贯通cutoff参数，选择development固定子空间或声明每replica自适应的ground-mode估计器。
- [ ] 预声明小网格，例如noise={.01,.05}、gap={.1,.5}、t0={1,2}、rank=2、cutoff={1e−8,1e−5}；固定模拟预算，保留失败。

交付：`gevp_ground_failure_grid.json`及失败率/偏差/coverage数值表或热图，写明MC区间。
验收：负/零/近零metric及rank=0反例处理正确；参数扫描实际作用到估计器。
停止：该有限网格有明确支持/失败边界即可；小样本可INCONCLUSIVE，多态tracking另行延期。

## 4. 有限CPU包C：先统一估计器，再解释有限MC结果

### C1/C2：正式预处理、gate与冻结metric必须同一路径

当前`reference_gate.fit_gate/null_pvalue`对完整T数据直接blocks，未走正式fold；`certificate_calibration`也直接blocks。
`certificate_calibration.run_simulation/run_family`调用risk不传development冻结late_inverse，metric由validation replica重估。
此外模拟gate仅nominal单态χ² p≥.05，与正式窗口/相对误差/反射等门控不同；K=2时twostate直接加入集合，没有对应接受记录。
这些是**估计器与认证定义差异**，增大dataset数不能修复。

![现有参考子门模拟](../../results/pion_projection/reference_gate_calibration_v1/reference_gate_calibration.png)

图中正确单态模型拒绝率为.02/.03，失配两态模型为.66/.59；分别对应渐近p/null模拟p。
这支持当前未fold的χ²子门诊断，不能当正式完整gate或候选证书的校准结果。

- [ ] C1：抽取共享raw→fold→blocks和reference gate函数；生产/evaluate与合成benchmark使用同一明确spec。
- [ ] C2：若只研究χ²子门，名称明确叫subgate benchmark；若称端到端，则包含实际所有声明门控、模型接受与身份步骤。
- [ ] C3：每模拟dataset在development计算候选late_metric并冻结，所有outer/inner验证risk使用它；与joint相同输入可逐项对照。
- [ ] C4：模型集合、窗口、prior/搜索、比较族在训练阶段确定；K2各模型有各自gate或明示未认证条件分析。
- [ ] C5：wrong-state例子当前baseline/candidate使用同一draw数组，log比恒0，所以0/7不是有效错误态候选认证测试；改为真实risk不同的候选，并明确无anchor时条件诊断或拒绝的策略。
- [ ] C6：删除/使用未生效的`contam_candidate`参数；用通道污染定义准确解释场景，避免声称生成了未生成的candidate世界。

MC边界：C2每cell **8个dataset**、C3每cell **30个dataset**是真实数量，现有文档已提MC误差；问题不仅是发表精度。
C2的3/8=.375是无条件认证率，3/6=.5才是gate通过条件下的率，不能混写。
0/8的双侧95% Clopper–Pearson区间为[0,.36942]，单侧95%上界.31234；不能由0/7或0/8声称族错误率已受控。
先声明MC验收目标/容忍范围，再选N；允许小规模smoke以INCONCLUSIVE或明确失败范围结项，**不要求本轮达到发表规模**。
N_null=50时最小校准p=1/51，不能检验正式1%阈值；选适合目标阈值的最小预算或明确只验证5%子门。

输入：冻结小网格、共享生成seed、6/12/24blocks与no-improvement/improvement/misspecification/wrong-state。
交付：`estimator_parity.json`、`certificate_calibration.json`、假认证/abstain/power带MC区间图或数值表；每cell记录dataset/null/bootstrap数、失败数、集合与metric身份。
验收：正式与模拟的预处理/gate/risk逐项一致；无条件/条件率分开；实际错误态策略可执行；结果不足则明确INCONCLUSIVE。
停止：不以候选收益为条件，不通过扩大N掩盖算法不一致，不靠所有情况abstain刷测试。

### C3：有效paired单ensemble区间与naive反例分开

`anchor_calibration.py`已删除np.full伪重复并产生真实mass bootstrap，关闭该旧bug。
但现有每dataset `lower_bound(delta)`仍把bootstrap draw当独立样本；脚本将它标naive，是有价值的负例。
`dataset_mean/dataset_se`估计多次独立实验的期望风险差，与一次ensemble的抽样区间是**不同estimand**。
README“正确物理推断必须用独立dataset均值”过强：单ensemble合法paired block bootstrap区间完全可以成立，不要求物理上重复30个世界。

- [ ] C7：同一物理dataset生成baseline/candidate估计，使用共同block索引；独立anchor使用共同anchor draw比较候选，物理区间不除sqrt(Nboot)。
- [ ] C8：实现一个明确的单ensemble paired区间，与naive错误区间和跨dataset期望风险均值分三列报告；outer datasets仅用于校准该区间。
- [ ] C9：anchor sigma/bias及一个明确共享配置相关性cell；记录anchor观测中心与内层抽样hierarchy，不把oracle真值中心等同实际anchor。
- [ ] C10：Nboot=50/200/800扫描固定同一raw data和anchor输入，采用配对随机数；当前源码每次生成newraw，不能称已验证固定物理数据。

交付：`anchor_calibration.json`、naive/paired/independent-repeat估计量语义表、固定数据Nboot区间宽度图、null和弱/零ground overlap数值表。
验收：同data增加Nboot只收敛MC近似，不任意缩小物理区间；独立外层null评估有MC区间；anchor偏差与相关性明确。
停止：小样本导致INCONCLUSIVE可结项，但未实现paired估计器不能归为仅剩GPU。

## 5. 测量计划：CPU验证仍属本轮，生产另移交

`measurement_plan.py`目前主要字段存在性检查，实际`measure.py`尚未强制读取计划；这不是GPU阻塞。

- [ ] 验证dev/val/anchor IDs唯一与隔离、geometry/source范围、真实hash与草案占位状态、freeze记录和质量/停止规则。
- [ ] 测量入口在任何GPU初始化前加载/核对计划；单元测试用mock证明非法输入未触发GPU初始化。
- [ ] NOT_RUN草案可保留占位但不得转RUNNING；生产需完整identity。新run目录存在即拒绝覆盖，partial resume需按同一身份。

交付：`measurement_plan_audit.json`或文字表：重叠IDs、占位hash、缺anchor来源、越界source、缺停止规则均拒绝；合法计划走到mock测量边界。
验收：CPU负例通过即可关闭计划验证；真实GPU新生产独立标NOT_RUN，不假装已执行。

## 6. 更稳健评分与真正新测量：可选独立移交

推荐物理路线仍是认证参考集合上的配对log改善：
`D_cm=log(R_bm+δ²)−log(R_cm+δ²)`；预声明同时单侧下界，再取模型间最小值。
它仅证明已冻结可接受模型集合中的条件改善；Bonferroni、模型平均或max/min本身不能修复模型错误/区间失准。
δ、baseline可分辨规则、实际收益阈值和集合须开发冻结；近零风险、集合为空或anchor冲突时abstain。

| 可选方向 | 最小独立交付与限制 |
| --- | --- |
| 独立基态anchor | 标准source–sink矩阵或长时高统计谱、识别/窗口图、隔离身份；Gram估计不自动等价 |
| 共同目标shape预测 | 固定共同target和训练metric、proper平方/log score、缩幅/方差膨胀反例；不认证ground state |
| 质量约束成本 | 先bias/coverage/SE质量门，再比较总成本/增量sink成本；未达质量则unresolved |
| 新GPU测量 | 12RHS残差、真实QUDA/设备/精度、gauge/prop/source摘要、HMC/相关性、小体积fast/generic对照；多source先配置内聚合 |

## 7. 本轮有限结项规则

顺序：A身份/状态 → B rank/有限网格 → C估计器一致性 → C3 paired区间 → 计划CPU验证。所有写入仅新输出目录，旧结果只读；不要求正收益。
每包记录输入/代码/spec hash、命令/seed、样本单位、阈值、失败数、拒覆盖规则，并给图或带数值文字表及观察/支持/限制。
同步修正覆盖报告/STATUS/总报告/相关README：不把0/7叫错误率控制，不混条件/无条件率，不把不同estimand叫同一物理推断。
A/B/C/计划验证有代码、负例、有限诊断及准确状态即可关闭本轮；MC不足可INCONCLUSIVE。真实anchor/新GPU、激发态tracking和可选研究独立移交，不用无限研究清单阻碍结项。
