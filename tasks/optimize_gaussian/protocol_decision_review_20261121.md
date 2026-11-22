# Optimize 生产前研究决策单（2026-11-21）

**状态：`REVIEW_DRAFT_NOT_FROZEN`；本文件是方案审阅，不是 production RunSpec、执行授权或新的实验结果。**
当前 reference 未通过时，相关风险只能标 `diagnostic_only`，`physical_score=null`。
本轮只读当前任务说明与接口、编写文本；未运行测试、训练、GPU/QUDA、生产任务、synthetic 扩样或 sealed 数据读取。

决策依据为 [当前 TODO](todo.md) 第5节和 [protocol freeze draft](protocol_freeze_draft.md)。
D01 的两个确认性比较由用户要求确定；下面其余“建议”仍是待审选项，未把研究者尚未给定的数值填为已冻结。科学阈值不能从旧 pilot、toy residual、已有 test 效果或示例1.2反推。

## 1. 先决定什么：一页文本流程

```text
现有证据：v9固定随机W；输入adapter可复用；reference未通过；CPU软件闭环已有诊断
    │
    ├─ 可直接确定的约束：保留TODO、不重复inversion、不重用旧test、不解封、不称toy物理优势
    │
    ▼
用户已确定 D01：trainable-W vs 同预算 SLSQP；trainable-W vs 固定强谱基（F=2）
研究者决策 A：reference / estimand / r_star；实现者提出固定强谱基的精确 contract
    ├─ reference未认证 → 仅开发诊断；不产生physical score
    ├─ 参数未选择 → 继续文本与接口准备；不生成“已冻结生产协议”
    ▼
研究者决策 B：estimator / 配对及block / CI与multiplicity / 精度或功效 / 样本数
    ├─ 现有60个封存配置不足目标精度 → 保留封存，先决定新增独立数据或降低主张
    ▼
研究者决策 C：模型/基线 / solver residual / 双预算 / failure与abstain / stop
    ▼
实现者按批准值落实：显式protocol → 真实输入/源码/环境hash → task RunSpec preflight
    ├─ drift / overlap / missing receipt / 输出冲突 → 拒绝；保留诊断，不启动GPU
    ▼
另行授权后：设备启动/中断/回收smoke → fit/dev开发与锁定候选
    ▼
Pion/Optimize/Wilson共同冻结候选、endpoint、exclusion与分析hash
    ▼
按一次性解盲计划开展真实比较，保留失败/弃权分母、图与负结果
```

CPU preflight 通过只证明指定的软件约束，没有研究者选择权或生产授权。P3 class×optimizer 2×2与 trainable-W
比较是两个实验，不能通过完成前者关闭后者。

## 2. 可以由现有证据决定的项目

这些是当前证据支持的限制，不是新的数值冻结。

| 项 | 已有证据/状态 | 可决定的行动 | 不能据此决定的值 |
| --- | --- | --- | --- |
| 真正训练W | draft §1.1描述现有 `model_space` 随机生成W、优化theta；v9 test已观察 | 主候选必须实际更新W；fixed-W作机制对照；旧test不作fresh blind | hidden width、W域、正则、训练器、训练轮数 |
| 真实优势 | CPU initializer只显示低预算条件性收益；IID谱基/高预算SLSQP存在反例 | 保留Gaussian、强SLSQP、强谱基；不重复相同labels扩样 | 物理改善量、GPU成本、真实泛化优势 |
| 输入复用 | TODO记录D0–99 adapter 100/100输入身份/residual核验 | 在新协议兼容时复用point propagator，不重复核验或inversion | 模型metadata已复采、learned训练已完成、reference已认证 |
| reference | freeze draft记录D reference FAIL、M2仍ABSTAIN/NOT_READY | 沿用该reference时只能diagnostic_only，physical_score=null | 新reference形式、窗、物理真值或阈值 |
| split | 既有计划D0–59 fit、60–99 dev、100–139 gap、140–199 sealed | 保持封存，不按任务重复算作独立验证；E不自动成为Optimize训练集 | 60个holdout能否满足功效、有效独立block数 |
| solver/worker | 当前接口要求显式solver policy、hash-bound protocol和isolated child environment；已有CPU报告 | 不隐式继承parent环境；拒绝缺策略、hash漂移、ID重叠和旧输出 | 生产KKT容差、hard cap、设备回收安全和physics PASS |
| 历史产物 | 旧fold恢复边界、v9receipt缺项已经记录 | 保留缺项，不重做同仓库恢复搜索，不回填历史身份 | 外部备份不存在、完整重现已证明 |

本轮没有重复adapter、历史suite或归档byte audit；表中实验状态来自上述任务文档，不是本轮重新测得。

## 3. 必须由研究者选择的TBD：建议、备选与影响

**D01 确认性比较族已由用户要求确定为两个预先固定的 contrast（F=2）：C1=trainable-W vs same-budget SLSQP；C2=trainable-W vs 一个固定的强谱基线。** Gaussian 与 fixed-W 为 secondary / mechanism controls，不进入这两个确认性 contrast；若要对它们另作确认性优越主张，须在解盲前显式扩大 family 并修改多重性控制。D04 reference、D06 最小效应、α、样本量等仍为 `TBD_RESEARCHER_DECISION`；不再询问是否纳入强基准。

为避免 C1 同时改变模型和 solver，当前最小审阅解释是：SLSQP臂与 trainable-W 臂使用同一 W/v/c 函数族、同一约束/正则和同一拟合目标/fit IDs；唯一预先声明的算法差异是参数搜索器、起点/restart方案及其总预算。若后续“learned”实现改为 gauge→kernel 网络或更宽参数化，则 C1 已是模型+solver复合对照，须按新方法写清并增加 mechanism/control contrast；不得继续把它简称“solver superiority”。该解释是公平比较的设计约束，不替研究者冻结函数域、目标或预算。

建议将强谱基具体化为 **degree-4 Chebyshev**，依据为[现有 operator-level 合成诊断](trainable_w_operator_cpu_20261121_final/README.md)。该诊断的 heat-kernel 目标本来属于谱函数族，不能证明 degree4 对物理目标最强；此处是待审的固定 baseline contract 建议。最终在读取 blind 数据前写死 degree=4、谱尺度/算符定义、系数域、正则/归一化与训练规则，不能看盲测后升降阶；如果物理约束要求改阶，须在任何盲测前修订协议并保留理由。

| 决策ID / 项 | 建议方案（未冻结） | 备选与科学/计算影响 | 批准前必须明确的参数/材料 |
| --- | --- | --- | --- |
| D01 主张与比较族（用户已确定 F=2） | C1=trainable-W vs same-budget SLSQP；C2=trainable-W vs一个固定强谱基；建议degree4 Chebyshev，精确算符contract按D11审阅 | Gaussian/fixed-W仅secondary/mechanism；initializer/restart不是trainable-W替身。若扩大确认性主张，先扩大family并重做D09/D10 | 不再选择是否纳入强谱基；仍须冻结C1的SLSQP参数化/起点与C2的degree4谱定义、归一化、系数域、同一objective及双预算；D04/D06等不代填 |
| D02 可训练参数化 | 以draft §1.1共享方向的real W/v/c与两侧Gaussian sandwich作为最小实现候选 | 交替profile与joint训练+polish是不同算法；正定性、归一化和额外算符方向会改变可行函数类 | H、m、alpha、W/v/c域、kernel normalization、是否要求positivity、feature scaling、regularization；均不从v9自动继承 |
| D03 训练/选择 | fit训练，dev只做预先列出的超参/seed选择；所有臂同一选择规则；test只评一次 | 预先冻结多个seed后取均值与dev选单seed是不同方法；训练ensemble平均目标与每配置initializer目标也不是同一个估计量 | 网格、seed数与列表、选优/平手规则、early stop、polish、是否输出一个全局kernel或每配置参数 |
| D04 reference路径 | 先通过独立reference审查，再谈物理risk优越；当前failed reference仅开发诊断 | 两态、variational/GEVP或独立anchor都可审阅，但不能由拟合成功自动认证基态；anchor可降低复用偏差但引入额外测量成本 | 模型、数据来源/允许IDs、窗、激发态与边界约定、gate、reference不确定度传播；review owner与通过证据 |
| D05 objective/estimator | 每臂使用同一冻结physics target和完整估计流程；搜索loss含正则时与报告的physics risk分列 | training-frozen amplitude与validation-refit是不同estimands；unweighted与covariance fit改变目标；不能按臂挑最有利定义 | amplitude/refit规则、t窗、covariance/shrinkage、质量bootstrap配对、正则、单位/归一化、score定义 |
| D06 最小物理效应 | 以R=R_baseline/R_candidate，审阅规则为同时下界超过r_star>1；**不建议一个未经物理判断的r_star数值** | 用Delta=R_baseline-R_candidate适合近零分母，但效应阈值有量纲且需重新定；“CI跨1”不是等效证据 | r_star或Delta_star、方向、是否有成本/失败率联合要求、科学上值得部署的改善量；旧1.2不是批准值 |
| D07 配对与缺配对 | 同配置/source/probe/target/precision，逐臂有序ID与hash完全绑定；不静默求交集 | 预注册的共同完整对分析可作secondary，但可能因算法失败导致选择偏差；需另报全部planned分母 | per-arm IDs/order、source/sink/边界、missing-pair和failure规则；不能用重复optimizer draws增加gauge样本数 |
| D08 block与CI | 建议报告95%描述性paired CI；同一block重采样索引作用于全部臂及reference不确定度，重算完整estimator | block bootstrap、stationary bootstrap或更保守独立batch设计各有假设；相关链的短block可能欠覆盖，样本小无法靠增加bootstrap draws补救 | 独立单位、block长度/敏感性网格、置信水平、区间构造、reference同/异数据源的重采样层级 |
| D09 multiplicity（F=2已定，α待定） | 建议Bonferroni：两项各用one-sided (1−α/2) 下置信界，生成family-wise至少(1−α)的同时界；分别检验冻结的r_star或Delta_star | Holm可用于两项有效p值的逐步拒绝；与置信界同报时须用一致反演。联合block-bootstrap max-stat界可利用配对相关，但需独立校准；不假设两contrast独立 | α仍TBD；冻结区间/检验构造、两项主张如何映射PASS/INCONCLUSIVE；增加Gaussian/消融/多W主张须扩大F。未经校正的描述性CI不能作同时确认性证据 |
| D10 样本/功效 | 在批准effect、block模型和failure estimand后，建议以90%功效规划，80%作成本敏感性；或直接批准CI精度目标 | 以估计精度为主可避免虚构effect；当前60 sealed配置只是上限，不等于60独立样本。若不足，先定新链/新增数据方案，不先解盲 | 目标power或CI半宽、效应/方差来源、MC精度、sim seed、样本数/失败膨胀规则；本轮不运行功效模拟 |
| D11 SLSQP与固定强谱基 | C1：SLSQP与trainable-W须采用同一W/v/c函数族、objective、fit IDs、约束/正则和起点/restart规则；C2 的 degree-4 候选见[CPU contract与响应图](../../results/optimize_gaussian/degree4_chebyshev_contract_20261122_v4/README.md)：周期三维协变 hopping `H∈[-12,0]`，`y=I+H/12∈[0,1]`，以 `0≤b0≤b1≤b2≤b3≤b4=1` 定义单调 Bernstein polynomial，再转为同一 degree-4 Chebyshev polynomial；dense 与实际周期 kernel 的 matrix-free `P4(H)` / 未归一化 `G^mP4(H)G^m` 已在 CPU 交叉验证 | 这是算符与数值约束候选，不是物理最强证据或批准的固定基；谱基和learned的自由参数、作用范围、gradient/直接解成本不同；闭式解不能硬算一个等价黑箱call；Gaussian零模归一化和共同objective仍未定 | 不从blind调阶/选基线；D11代数/CPU接口审阅已完成，不重复；下一步审核C1/C2共同目标、IDs、失败分母与双预算字段的一致性。方案批准后固定每臂objective-call/walltime caps、调参成本和基构造/特征/训练/inference/solve账本。若C1采用不同参数化，明确标为复合方法对照；生产若要求约束则实现约束优化，不能clip-LS后称最优 |
| D12 残差与solver gate | 先明确可微性/盒约束后选择优化残差；初始审阅倾向require_solver_success=true且残差合格，两者均非单独证明 | success=false但独立残差合格是否可接纳需单列批准；预算耗尽不能因best-so-far较低自动算成功；非光滑loss可能需别的stationarity判据 | residual_field与定义、缩放/单位、有限差分步长/探针、residual_tolerance、require_solver_success；**无推荐数值容差** |
| D13 两种residual | 分开QUDA inversion residual和优化stationarity/KKT | 满足反演残差不保证优化收敛；KKT小不认证物理reference或全局最优 | 反演定义/precision/metadata兼容、优化残差定义；D0–99既有tol记录不能替代新policy审阅 |
| D14 objective-call预算 | 按当前接线计所有objective、最终点重算和KKT probes；记录phase，KKT探针不更新optimizer best-so-far | gradient/Jacobian/feature构建若大量复用，单一call数不能表示同成本；另报底层work与walltime，不能让解析梯度免费解释为算力公平 | per-arm cap、每restart预算、训练/调参总次数、probe accounting；**无推荐cap数值** |
| D15 walltime与可中断范围 | 正式总成本比较建议独立worker hard deadline，明确包含setup/train/inference/solve/IO/teardown；soft guard另标overshoot | cooperative cap只在call边界拒绝；parent可杀CPU进程不证明GPU/QUDA context及时释放。可按完整arm或固定batch监督，统计单位也随之改变 | hard/soft选择、outer timeout、TERM grace、timing边界、冷/热cache、checkpoint粒度；设备smoke另行授权；**无推荐秒数** |
| D16 成本/摊销 | 主表同时列未摊销总成本和按预定部署次数N的摊销；GPU同步与memory有明确边界 | 只报inference可隐藏训练/选择成本；按事后有利N算break-even会改变部署结论；CPU toy时钟不能预测GPU | N、hardware/precision/并行度、训练复用范围、失败成本、经济或科学cost ceiling |
| D17 失败/弃权/停止 | 保留全部计划臂、训练runs/starts、配置/blocks的各自分母；reference失败→物理ABSTAIN；软件失败不返回partial fit | 失败率门槛、失败候选是否进入效用endpoint需批准；不可事后赋无限risk或剔除失败以改善均值 | input mismatch/NaN/solver reject/timeout/cleanup failure/missing pair映射、允许失败率、run-level stop、重试次数与重试是否耗预算 |
| D18 多次查看/停止 | 先冻结总样本/总预算与一次主检验；负/不确定结果也归档 | sequential designs需预先处理多次查看；不能不断加seed、换loss或看holdout后补样追显著 | max runs、预定开发轮次、无效/不可辨识停止、是否允许sequential方案及其错误控制 |
| D19 RunSpec/环境/输出 | 从批准protocol生成task-specific spec，绑定真实cache/provenance/源码、显式child environment与no-clobber输出；parent回链产物hash | CPU fixture仅验证控制流；设备与库版本、driver/runtime和source hash更新都需新receipt，不回填旧v9 | `outputs.artifacts`/`outputs.diagnostics`完整清单、环境可见变量、设备ID/库版本与权限、run/review/授权记录 |

D01 两项比较清单已确定。D11 的 degree-4 contract 已有可审阅 CPU 候选，但未获批准。D04/D06 与其他 TBD 的备选表、识别条件、成本和流程已在本决策单与 protocol freeze draft 中列出；2026-11-22 的交叉核对确认 C1/C2 共用目标、ID/source/probe/precision、失败分母框架与双预算记账没有文档冲突。精确 endpoint/reference/失败处理/预算值仍缺研究者选择，故当前不补数、不将建议写入 production protocol；CPU 文档审阅到此停在明确门槛，真实训练与 comparison 等研究方案、身份和授权通过后再做。
“实现者可以确定”仅指按已批准方案编码和绑定身份，不能替研究者选择效应、精度或资源代价。

## 4. 当前字段接口与研究决策的接点

这是一份静态接口映射，不是可执行protocol，也不含可误当生产值的占位数字。

| 接口 | 已有字段/行为 | 待决策如何落地 |
| --- | --- | --- |
| `SolverPolicy` | `objective_call_cap`, `walltime_cap_seconds`, `residual_field`, `residual_tolerance`, `require_solver_success`；policy不接受缺字段/未知字段 | D12–D15批准后填入显式`solver_contract`；盒KKT有限差分与QUDA residual不得混名 |
| task builder | `protocol_path`, `output_directory`, `receipt_directory`, `run_id`, `timeout_seconds`, `terminate_grace_seconds`, `environment` | D19执行前冻结路径/文件清单，D15选择outer scope；不得现在调用builder去读取sealed输入 |
| builder当前split | 从protocol的fit/dev_val/test闭区间推导互斥IDs，并为实际文件绑定hash | 生产spec包含sealed test时必须受首次读取规则约束；文本列ID不等于授权hash/读取test bytes。fit/dev-only开发与最终blind spec的表示/执行阶段仍需明确，不能用dummy test冒充blind |
| worker schema v2 | 绑定文件/hash、explicit child environment、no-clobber outputs；成功后核验artifacts，失败diagnostics分开 | 如实列results/manifest/data/basis与rejection receipts；成功hash不是模型正确或物理通过的证据 |
| `train.main` | 显式protocol path与raw-byte SHA child recheck；当前训练主入口仍是fixed-W路径。隔离的`trainable_w.py`已完成synthetic coefficient-fit CPU原型，但未接入`train.main`或真实测量 | 仍须在生产入口真正实现并验证W更新、真实objective/receipt与失败路径；builder不能把现有入口或CPU原型自动变成production trainable-W训练器 |

单独的hard-timeout监督器与nested solver walltime不是同一层预算。KKT probes消耗剩余预算，若不足应按冻结策略拒绝，
不能临时放宽阈值或让probe点“改善”optimizer best-so-far。

## 5. 输入、分母、失败状态与建议图表

本决策单的输入是当前TODO、freeze draft及上述源码接口；**没有新增数值实验，故本轮实验分母=0，没有估计新成功率/coverage/power。**
TODO所列CPU场景数和通过数是历史软件覆盖记录，不是gauge分母或生产失败率。

| 后续报告项 | 输入与分母必须写清 | 建议图/文本及失败处理 |
| --- | --- | --- |
| 配对physics risk | 计划配置数、实际共同可用配置数、独立blocks、各臂缺件；同一reference/amp/covariance估计流程 | 两主contrast及interval图。risk若为ensemble-level非线性量，应在共同block bootstrap中重算完整risk；不能平均“每配置risk比”冒充该estimand |
| 配置/块影响 | 仅在所选estimand有定义时给逐配置差；否则用delete-block/jackknife influence并注明 | 标出失败/高影响blocks；不是把相关配置当独立重复测量 |
| 收敛 | 每臂run/seed/start数、完成/进入calls、最终点/probe phases；每个预算点可用run数 | best-so-far对calls与elapsed双图；截断保留停止点，不能外推补曲线；KKT probes另标不更新best |
| residual | optimizer attempts与gauge inversion两套分母；非finite、无法求导、probe耗尽、solver flag分别列数 | KKT/physical residual两图或两表；所用定义、单位、阈值与失败状态清楚写出 |
| 成本/部署 | 相同设备/precision/执行边界；全计划runs包含失败时间；N与warm/cold cache固定 | setup/train/inference/solve/IO/teardown堆叠及摊销曲线；未采设备数据时不造GPU成本图 |
| failure/abstain | planned arms、planned fits/starts、planned gauge IDs与completed pairs分别作分母 | 状态流/逐例CSV或文字表，区分NOT_RUN、软件FAIL、reference ABSTAIN、INCONCLUSIVE、预算截断、cleanup failure |
| 实现预检 | 实际尝试的固定软件场景，逐例输入/预期拒绝/实际状态，不混入physics样本 | drift/overlap/output-conflict的控制流表；无paired methods时不虚构paired-risk图 |

建议预先采用以下状态语义作为审阅起点：未执行=NOT_RUN；未通过身份/数值/进程清理=相应软件失败；reference不认证=物理ABSTAIN；
满足执行/认证条件但区间未过冻结门槛=INCONCLUSIVE或无实用改善，具体区分由D17/D18批准。
只有冻结的效应/统计/数值/reference规则全部满足，才讨论目标主张的PASS；不能以测试绿灯、success flag或文件hash替代。

## 6. 审阅回填与下一步（本轮不执行）

每个D编号按下面格式记录，避免口头批准与RunSpec脱节：

```text
Decision ID: Dxx
Owner / reviewer / date: TBD
Selected option / explicit value / units: TBD
Rejected alternatives and reason: TBD
Effect on estimator / family / cost / failure denominator: TBD
Evidence needed before launch: TBD
Protocol field and analysis/source hash: TBD
Status: TBD_RESEARCHER_DECISION → APPROVED_FOR_FREEZE → HASH_BOUND
Execution/data/GPU authorization: separate record, never inferred from approval
```

下一步保持 **D01（C1/C2，F=2）不变**；degree-4 Chebyshev 的周期谱界、Bernstein/Chebyshev换基、实际 kernel 的 matrix-free递推和未归一化Gaussian sandwich已有[CPU候选、响应图与报告](../../results/optimize_gaussian/degree4_chebyshev_contract_20261122_v4/README.md)及19项聚焦测试。D11代数/CPU审阅和两份 protocol 的 C1/C2共同objective、IDs、失败分母框架、双预算一致性检查已完成；未发现文档冲突。D04 reference、D06 `r_star`、精确score endpoint、失败映射与数值预算继续 TBD，依用户要求不冻结、不重复起草；后续应等待研究者审阅并在授权后实施。强基线已纳入确认性族，不再重复询问。
未来获批准并真实比较时，每项实际对照须交paired CI、calls/time best-so-far和成本图、planned/valid/failure/abstain分母及文字边界；当前 CPU 方案审阅仅交算符响应图、共享目标/预算的数据流与明确适用范围，不启动训练/生产RunSpec，不访问 sealed IDs。全部19项协议只有获研究审阅后才可转为 `APPROVED_FOR_FREEZE`。
trainable-W的隔离CPU解析梯度、真实feature/kernel调用、48个signed-permutation测试与synthetic coefficient-fit已完成，见[图文原型报告](trainable_w_cpu_prototype_20261121/README.md)；它不含物理risk或SLSQP比较。批准研究决策后，下一项实现工作应是将其接入真实`collect/evaluate/train.main`及身份/RunSpec路径，再做CPU接口/梯度回归；另行授权后才做设备smoke与真实方法比较。
不再做相同synthetic标签扩样、重复adapter核验或旧fold恢复搜索；没有冻结/授权之前不启动训练、生产2×2或shared holdout读取。

### 2026-11-21 CPU addendum：实际 hopping correlator 梯度核验

在初稿之后增加了[actual-kernel gradient finite-difference report](../../results/optimize_gaussian/trainable_w_operator_gradient_20261121_v1/README.md)。解析 `W/v/c` 梯度现在对实际 link-centred feature 和 paired hopping kernel 的 `Re<psi|K|psi>` 做了H=2 fixture的9个差分步长×7个参数、共63项确定性检查，固定步长误差约`3.52e-8`，扫描最小约`3.24e-9`；`tests/test_optimize_trainable_w.py` 为13 passed。该结果关闭的是局部算子链式导数的CPU实现检查；不代表ensemble risk/refit梯度、生产`train.main`已接入、GPU正确或训练比较。D04/D06仍须研究者在适当阶段审阅；D11已有候选但未冻结，详见2026-11-22 contract 报告。
