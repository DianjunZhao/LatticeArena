# Wilson loop 与公共框架：下一轮开工单

核查基线：`dfa63fe`；2026-11-18。**保留本文件：部分完成，仍有具体 CPU 工作。**
本轮仅重新组织计划，不修改实现或历史数据，不启动 GPU/MPI/远程/模型 API。
默认所有新结果写新 run；下文新增输出路径均为**拟议**，不得覆盖旧 results。
研究负结果、受控拒绝及有证据的停止均可验收，不要求无限扩展直到成功。

## 1. 已完成证据与当前结论

| 类别 | 当前证据 | 结论及边界 |
|---|---|---|
| SU3 / APE | `kernels.project` 改 polar+det phase；四空间 staples 改 α/4；新增双侧协变、多参数测试 | 旧 Gram–Schmidt bug 已修；不能再列作未修问题；病态/分支仍见 P0 |
| 数组与读取 | `common.load_data` 验完整shape/ID/hash/finite；NERSC验支持格式与payload长度 | 完整通用NERSC、checksum与geometry一致性仍未完成 |
| 冻结 | `experiment.evaluate` 检查开发数据SHA、kernel SHA、参数；测量记录gauge hash/git/时间 | 依赖闭包与测量身份绑定仍不完整 |
| 保存 | NPZ、JSON各自临时文件替换 | 单文件原子保存已做；跨文件一致恢复未做 |
| 重测 | v2/v3/v4档案存在；v3留出80组态/16块 | 属归档实测证据，本轮未复跑GPU |
| 配对 | `paired.py` 同块同索引nested bootstrap | 区间已实现；覆盖率、功效、自相关与多比较尚未校准 |
| 回归 | 主agent复跑51 tests全过 | Python3.13.12 / NumPy2.5.1 / SciPy1.18.0 / pytest9.1.1；不等于物理问题全部解决 |
| 环境 | 本地无GPU/MPI相关库 | GPU/MPI/backend一致性为NOT_RUN，CPU任务照常推进 |
| 公共层 | `core/io.py`、`core/stats.py`；LLM prompt已按协议动态生成 | 五类公共接口与统一证据流程尚未实现 |

当前几何为16⁴、纯规范β=6.0；link轴 `(mu,t,z,y,x,3,3)`。
空间d对应数组axis=3-d，时间axis=0；temporal links不smear。
圈orientation为 `K(x)P(x+R)K†(x+T)P†(x)`，平均ReTr/(9×四维体积)。
冷场、非对易暴力圈、原始gauge与新增APE协变测试覆盖主要约定。
势仍是log(mean W)对T的无权线性回归，名义窗口仍写作windows[1]。
risk仍为 `mean_R[(SEboot/Vref)^2+(std_windows(V)/Vref)^2]`；Vref是开发identity的尺度。
该目标衡量固定窗口精度/稳定性，**不是已证明的基态总误差**。

### 归档数字：严禁混用点估计和bootstrap中位数

| 版本 | 原样本score | 配对bootstrap结论 |
|---|---|---|
| v2 | 96.669 / 103.253 / 105.535 | 中位数3.013 / 3.425 / 3.410；与点比值严重偏移，待诊断 |
| v3 | 263.3 / 232.8 / 221.9 | 比值95%区间[1.315887,5.932374] / [1.248364,5.819607] / [1.171982,6.336328] |
| v4 | 663.3 / 745.8 / 808.0 | 同系综扩R=4的诊断，不能当独立复现或与v3同刻度比较 |

v2已用当前代码只读复算，与归档一致；约3倍是bootstrap中位数，绝非其点改善。
v3区间支持当前重采样假设下的固定risk降低，不直接证明ground-state accuracy。
[已有v3图](../../results/wilson_loop/paired_s16t16_v3/score_paired.png) 的柱高是100×bootstrap中位数，
不是原样本263/233/222；报告/图例须明确二者。
同一天/同机器不决定盲性；应核查冻结、信息访问和split记录。
找不到validation打开前的plan身份，就不能补称历史预注册。
数值来源：[v3 原样本结果](../../results/wilson_loop/s16t16_v3/validation_results.json)、
[v3 配对结果](../../results/wilson_loop/paired_s16t16_v3/paired.json)、
[v4 原样本结果](../../results/wilson_loop/s16t16_v4/validation_results.json)。

## 2. P0：投影数值边界（第一优先，CPU）

文件：`kernels.py`、`tests/test_wilson_loop.py`。
已知反例：`project(I)`残差0，`project(1e4 I)`残差约1.11e-16；
合批 `stack[I,1e4 I]` 却拒绝（unitarity defect约0.3998），1e6混批约0.9999。
原因线索：inverse-square-root用全batch同一scale与固定24次Newton–Schulz。
这是batch尺度敏感实证，**不说明v3所有测量失败**。

只读复现（从仓库根目录；当前合批项会受控拒绝）：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B - <<'PY'
import numpy as np
from tasks.wilson_loop.kernels import project
eye = np.eye(3, dtype=complex)
for name, matrix in [('I', eye), ('1e4 I', 1e4*eye),
                     ('mixed', np.stack([eye, 1e4*eye]))]:
    try:
        print(name, np.max(np.abs(project(matrix)-eye)))
    except ValueError as error:
        print(name, str(error))
PY
```

- [ ] 增加单矩阵/同质batch/混尺度batch的等价性回归，范围与精度显式声明。
- [ ] 生成已知奇异值谱，覆盖非零rank缺失、近奇异、极端scale、Inf/NaN。
- [ ] 检查det相位靠近±π及独立左右SU3变换；声明分支切口和容差。
- [ ] 比较逐矩阵规范不变scale、收敛准则或稳定fallback，给成本与拒绝策略。
- [ ] 不静默clip失败矩阵；错误定位到batch索引，测量层再附cfg/方向。
- [ ] 将原有冷场、α=0、steps=0、暴力圈、unitarity/det/APE协变继续作为回归。

拟议产物：`results/wilson_loop/audit_<new-id>/projection.json`及条件数×scale热图/文字表。
验收：支持域内批次拆分不改变结果至预设容差，域外受控拒绝；det与unitarity均合格。
依赖：无新数据。停止：无法定义稳定支持域时先报告边界，不启动重测。
GPU数值/性能对照另列NOT_RUN；CPU通过不冒充CuPy通过。

## 3. P1：可信加载、冻结与原子恢复（CPU）

文件：`common.py`、`measure.py`、`experiment.py`、`paired.py`、`core/io.py`。

- [ ] `paired.main`复用完整加载/冻结校验，禁止直接np.load绕过身份验证。
- [ ] 去掉“协议名非v1即physical”的自动认证；从独立算符/参考/统计/输入状态导出报告。
- [ ] 冻结measure/statistics/helper依赖闭包，绑定测量provenance、kernel、数据与split身份。
- [ ] 检查gauge header geometry与RunSpec、payload hash/checksum支持范围；legacy明确只读身份。
- [ ] 设计新run拒绝覆盖、可验证完整前缀resume；NPZ/provenance用共同generation身份。
- [ ] 故障注入各替换步骤，确保恢复至同一可信generation或拒绝，不拼接不同前缀。
- [ ] 记录设备/库/精度、加载/平滑/收缩/写盘时间；不能把旧时序当新硬件承诺。
- [ ] 用篡改测试覆盖数据、kernel/helper/statistics、protocol、ID重复/重排、缺provenance。

拟议产物：同audit目录 `identity_audit.json`、恢复状态机文字与故障注入表。
验收：每种不一致均fail-closed；两次恢复输出与不中断参考一致；旧档案不补造来源。
依赖P0仅在需要新测量时；缓存身份审计现在即可做。

## 4. P2：配对统计诊断与校准（CPU缓存+合成）

文件：`paired.py`、`statistics.py`、测试；先冻结诊断spec再跑。

- [ ] 逐个复算v2/v3/v4原样本risk，分解每R的SE项和window项。
- [ ] 专门解释v2原点比值约1而nested中位数约3：记录外层重复块、有效独立块数、
  分子/分母分布及相关性，比较leave-one-block-out；未解释前禁止只报中位数。
- [ ] 保留整块(kernel,R,T)配对，明确outer数据不确定性与inner Monte Carlo误差。
- [ ] 非正mean W、非正bootstrap W、NaN、零分母逐项计数并声明拒绝规则。
- [ ] 合成同效/已知增益/共同相关噪声下检验coverage与假阳性；不能只测同核比值等于1。
- [ ] 扫预声明block length与seed/抽样次数，报告区间稳定性；根据保存间隔与τint选block。
- [ ] 明确检验族、冻结候选与多比较、最小有用增益、统计功效设计；不虚构所需组态数。
- [ ] `probability_better`改明确称bootstrap exceedance fraction，不当posterior或校准p值。
- [ ] 查原始plan commit/hash/数据访问时间；缺证据改称历史诊断，不补造预注册。

拟议产物：`paired_audit.json`；点值与bootstrap中位数并列图、比值分布、block敏感性图。
验收：点值精确重放，校准范围与失败率公开；区间跨1可验收为INCONCLUSIVE。
依赖：P1可信入口；无新GPU。停止：coverage/自相关无法支持正式解释则只报诊断。

## 5. P3：物理质量门控与共同错误平台（先CPU）

- [ ] 将reference gate的含义与配置名同步：目前仅正势及spread/V≤5%；window_z未用。
- [ ] 把nominal索引从硬编码windows[1]变成经验证的spec。
- [ ] 构造相邻窗口全部稳定但共同偏离E0的两态/多态反例，展示现risk的盲点。
- [ ] 比较log bias、T相关协方差及条件数；相关拟合/shrinkage须开发冻结与合成校准。
- [ ] 从有限时间静态源transfer matrix定义允许谱；不能直接套pion cosh。
- [ ] 文档删除普遍“回绕1e-4–1e-6”的断言；若假设等幅反向指数，
  相对项exp[-V(16-2T)]在T=8为1，但这也不能反过来证明Wilson圈必有该cosh。
- [ ] 对v3/v4画各R有效势、各核窗口势及风险贡献，明确共同错误平台仍未排除。
- [ ] 区分降低当前risk、降低SE、改善overlap、提高E0准确度四类主张。

拟议产物：`spectral_quality.json`、共同错误平台合成图和有限T推导文字。
验收：新门控能明确哪些反例可排除/不可排除；不把gate PASS升级为真实E0证明。
依赖：无新测量即可完成反例；更晚T/独立anchor验证再列新数据需求。
停止：不可识别时保留诊断目标与abstain，不反复换参考直到给分。

## 6. P4：有条件的研究扩展（先设计，后判别实验）

优先只选一个扩展轴，不同时换系综、算符、参考与估计器。

| 路线 | 下一步与依赖 | 图/文字验收与停止 |
|---|---|---|
| 纯空间stout | 定义无迹Hermitian Q与exp(iQ)U；相同协变/时间局域测试，开发冻结成本/半径 | APE对照cost-risk图；无收益可停止 |
| 小basis GEVP | 设计底线i/顶线j完整cross loops；现有Wii不能拼Cij；冻结T0/截断/条件数 | 合成谱与矩阵质量报告；真实数据需新cross测量，无平台可验收负结果 |
| multilevel | 先读局域纯规范条件平均算法；定义固定边界子更新与无偏性 | 独立估计器赛道的cost-error图；不能算kernel-only胜利 |
| 新盲测 | 候选、门控、统计计划冻结后用未见样本；按τint/功效设计N | 完整manifest、成本及配对区间；跨1或质量失败保留负结果 |

原始依据：[Morningstar–Peardon stout](https://arxiv.org/abs/hep-lat/0311018)、
[Blossier et al. GEVP](https://arxiv.org/abs/0902.1265)、
[Lüscher–Weisz multilevel](https://arxiv.org/abs/hep-lat/0108014)。
这些论文支持方法与条件，不保证本R/T和预算下收益。
旧已观察validation及同系综v4扩展不能重新命名为新盲测。

## 7. 公共框架 F0–F5：仍需实施，先两任务复用

公共层当前只有io/stats；不得把以下拟议接口写成已经存在。
由单一集成负责人修改core/agents，各task负责人提供适配器与物理反例。

### F0：统一证据与测试契约（CPU第一切片）

- [ ] 公共证据schema记录test_id/task/claim/command/seed/geometry/dtype/code与input hashes、
  observed/threshold/status/scope；scope分synthetic_CPU/archived_data/live_GPU。
- [ ] 各自保存gauge、Hermitian、O_h、平移、时间局域等证据，不强迫全部task同一约束。
- [ ] 将可复用残差计算抽入拟议 `core/operator_checks.py`；已知坏闭环、旧GS右协变、错反射索引作为反例fixture，与合法核同时验证，不修改生产核来重现旧bug。
- [ ] 建立拟议 `scripts/audit_run.py`、`scripts/summarize_evidence.py`，输出真实存在的证据引用。

验收/产物：Wilson与pion同schema的一份JSON和文字矩阵；反例、拒绝、NOT_RUN均可表达。
停止：不自动把研究假设标完成；测试总数不能替代逐项验收。

### F1：五类接口与不可变运行身份（CPU第二切片）

按顺序小步抽取现有实现，两个任务实际使用后再扩大：

1. TaskSpec/RunSpec：物理定义、geometry/BC/source/split/reference/metric/budget及依赖闭包。
2. OperatorContract/CandidateSpec：axes/dtype/变换律/支撑/参数/依赖与适用约束。
3. MeasurementProvider/Bundle：数组与manifest，声明linear_response/cross_matrix/new_source能力。
4. ReferenceProvider/Metric/Comparator：分离参考、目标与比较族，共享draw IDs与baseline身份。
5. SearchAdapter：optimizer与LLM统一候选、校验、预算与Evaluator。

验收/产物：数据流文字图、两task adapter、同spec统计一致与缓存失效反例。
不能从单源/对角缓存推测缺失响应；不首先重建泛化注册表。

### F2：LLM与搜索入口的真实隔离（CPU mock，不调用API）

动态prompt已完成；但loop当前只查维数/非零，risk查finite，不强制sum(u)=1与L1≤8。

- [ ] 统一候选校验sum约束、L1、维数、finite与合法类型；optimizer/LLM同路径。
- [ ] 评估入口复用全部manifest/frozen身份检查，移除直接np.load validation绕行。
- [ ] mock LLM提交NaN、越界、错误维数、零和、合法候选，记录拒绝原因与预算。
- [ ] development搜索期间禁止读取validation；用拦截文件访问测试证明。

验收/产物：mock轨迹JSON及非法候选/无validation访问文字报告。
可信Python插件不等于不可信提交的安全隔离；hash也不构成访问控制。

### F3：状态、fold-local统计与成本账本（CPU）

- [ ] run_state与operator/reference/numerical/statistical/comparison状态分离；score可null。
- [ ] manifest绑定split、draw IDs、baseline/score spec、reference draws和搜索预算。
- [ ] 每outer fold重建reference、normalization、covariance、feature正交化和内部超参。
- [ ] seed选择、早停、窗口/模型选择都算搜索；观察过validation永久记录已观察。
- [ ] 统一成本账本，区分setup、solve、残差复核、kernel apply、IO、analysis与total；记录冷/热缓存、精度、设备和并行度，不混合比较。

验收/产物：状态转换表、泄漏反例和同draw跨入口一致性报告。
INCONCLUSIVE不等于无效，evaluated不等于物理有效；不同100分不直接合榜。

### F4：数据生产质量与扩展边界

HMC生成器已入库，但force/reversibility/ΔH/autocorr生产质量缺少新增核验证据。

- [ ] CPU小场先做force有限差分、可逆性/积分误差阶、ΔH与接受率诊断设计。
- [ ] 归档生成链热化、保存间隔、seed及自相关证据缺失处明确NOT_RUN。
- [ ] 多体积/多动量/多rank按geometry、相位/复共轭、little group、halo与归约分别验收。
- [ ] GEVP/训练网络必须声明新source/cross响应与函数类；估计器与kernel赛道分开。

验收/产物：HMC质量文字/图表与扩展能力表；无生产证据不能仅凭高接受率认证系综。
新GPU生产与多rank执行另行规划，不妨碍先完成CPU测试和设计。

可扩展部分要随诊断更新到公共能力表，而不是只罗列新task名字：

| 扩展轴 | 可复用部分 | 新增物理验收 |
| --- | --- | --- |
| 多T/非立方体积/质量 | RunSpec、轴/边界、输入和fold计划 | source-origin、有限T/体积、质量/尺度与参考适用性 |
| 跨系综迁移 | 模型制品、训练预算、ensemble-level split | 整系综留出、物理smear半径标定、domain shift |
| 非零动量 | operator/measurement/search接口 | 相位、复共轭、±p、little group与source/sink约定 |
| baryon/三点函数 | provenance、冻结、配对和成本 | Wick/自旋投影、source-sink间隔、激发态结构；重定义目标 |
| 真实相关矩阵/可训练核 | capability声明与数据缓存 | 实测cross/source数据、精确可复用参数范围及梯度检查 |
| CPU/CUDA/ROCm/MPI | 后端适配与证据schema | 相同输入/残差/精度的跨后端、halo与归约对照 |
| 多source/multilevel | 测量接口、质量门控与成本 | 无偏性、自相关、配置内聚合；与kernel-only赛道区分 |

### F5：集成与关闭条件

1. 先交P0数值边界、P1可信入口与F0证据schema，保留失败前后记录。
2. 再交P2/P3诊断与F1/F2两task复用、mock搜索回归。
3. 再交F3/F4明确范围的fold-local与生产质量证据；只选一个P4判别实验。
4. 逐项更新coverage与报告，过时bug移至已完成，未做项保留NOT_RUN，不靠删条目宣告完成。

每轮必须交图或可审计文字报告，并标明实际产物路径、命令、输入/代码身份与未跑范围。
本次51项测试的复核命令为 `PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest -q -p no:cacheprovider --basetemp=.audit-todo-pytest-20261118`；该临时目录已在核查后清理。后续使用新的任务内临时路径，并仅清理本轮产生的文件。
本文件只在所有必需条目有验收证据，或研究路线有明确负结果/停止决定且范围被接受后才可关闭。
尚有CPU缺口时不得写“剩余只能新GPU”；未实施的低优先级研究扩展可明确延期，不能假装完成。
