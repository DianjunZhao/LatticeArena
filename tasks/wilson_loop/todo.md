# Wilson loop 后续工作交接（2026-11-18）

核对基线：Git提交`40a7c9d`。下面区分当前源码的CPU反例、已有档案数值和未来实验；实施前先核对代码版本。

## 判定与首要行动

当前是 **测量/打分 pilot 已跑通；APE 的物理有效性未通过审查**。
最先做 `kernels.project` 的独立左右规范变换回归测试与协变投影修复，随后重新测量。
不能先扩组态、训练核或把旧 score 当作物理基线。
本文件仅规划；本轮未修改实现、数据或旧报告，未运行 GPU/MPI/远程任务。

## 已完成与证据

- 根 README、STATUS、task README、protocol、源码和七项测试已审阅。
- 实物目录为 `results/wilson_loop/s16t16_v1/`。
- 有 development/validation NPZ、两份 provenance、submission 和 validation_results JSON。
- 协议：16⁴、纯规范 β=6.0；development IDs 0–59，gap 60–69，validation 70–99。
- 每组态四核、R=1,2,3，T=4,5,6,7,8；block_length=5。
- 因而开发 12 块、留出 6 块；seed=20261116，bootstrap=1000。
- 规范数组 `(mu,t,z,y,x,color,color)`；空间方向 d=0,1,2 对应 axis=3-d。
- 时间方向链路未经 smearing。
- `measure.loops` 在全部空间点、时间原点及三个轴向平均。
- 归一化为 `ReTr/(3 color × 3 directions × volume)`。
- orientation 为 `K(x) P(x+R) K†(x+T) P†(x)`。
- 冷场、随机非对易场暴力 Wilson 圈、原始链路 gauge invariance 测试覆盖此 orientation。
- 它们没有覆盖 **先做 APE 后的规范不变性**。
- `statistics.potential` 是 log(mean W) 对 T 的无权线性回归，不是相关 χ² 拟合。
- 名义窗口固定为 windows[1]，不是动态读取 nominal 索引。
- risk 是 `mean_R[(SEboot/Vref)^2+(std_windows(V)/Vref)^2]`。
- 后一项只是窗口一致性代理，不是真实基态偏差的估计。
- Vref 为开发 identity：0.4102935140、0.5972295854、0.7033454544。
- 开发 identity spread：0.0003867054、0.0024845589、0.0058308088。
- 现行 gate 仅检查正势与 spread/V≤0.05；并没有验证谱模型正确。
- `reference_max_window_z=2.5` 未使用；`reference_max_relative_se` 实际用作 spread 门槛。
- 开发 identity risk=7.8203575253e-5；APE(0.5,5)=1.9476781811e-5。
- 开发最佳由冻结 submission 选择，不能根据留出最佳另选候选。
- 留出精确数值以下以 JSON 为准，README 有少量舍入/旧数值偏差。

| 核 | validation risk | score |
|---|---:|---:|
| identity | 5.5532964283e-5 | 100 |
| APE(0.5,5) | 5.8009775642e-5 | 95.73035529 |
| APE(0.5,10) | 5.4096534442e-5 | 102.65530838 |
| APE(0.7,10) | 5.4722119354e-5 | 101.48174984 |

## P0：协变性阻断项（CPU 即可）

`project` 逐列 Gram–Schmidt 只自然保持左酉作用，不保持一般右酉作用。
link 必须满足 `P(Gx M Gy†)=Gx P(M) Gy†`，独立左右 G 均需成立。
单纯 `U†U=I, det(U)=1` 并不蕴含该条件。
本轮直接在随机 SU(3) 2⁴ 场测了一步 APE，α=0.5：
使用 tests 的 QR SU3 生成器、default_rng(3)，先生成 links 再生成 g；
比较 `ape(g U g_next†)` 与 `g ape(U) g_next†`。
最大逐元素绝对差 **0.442292531289015**。
这是 CPU 实证，不是 GPU 数值舍入猜测。
因此 README 所称此 Gram–Schmidt 保持规范协变应修正。
旧 APE 输出保留作历史实现诊断，当前不能据它宣称合法空间算符优化。旧provenance未冻结核源码，须恢复对应实现身份才可判断哪些历史运行受同一缺陷影响；本轮反例直接证明的是当前源码。

下一 agent：

1. 在 `tests/test_wilson_loop.py` 加上述失败回归、独立左右投影测试。
2. 在 `kernels.project` 实现双边酉协变投影：非奇异M先取`Q=M(M†M)^(-1/2)`，再取`P=Q exp[-i Arg(det Q)/3]`以回到SU(3)。polar factor本身只保证U(3)，不能省掉det修正；这也不等同于未经证明的最优SU(3)距离投影。
3. 明确奇异值阈值、近奇异行为、有限性、复数精度与 det 相位分支。
4. 不能静默 clip 后输出不合格 SU3；失败要给出组态/方向/位置摘要。
5. 检查 determinant cube-root 在分支附近的连续性与左右变换稳定性。
6. 检查 NumPy/CuPy batched SVD/eigh 行为与成本。
7. APE 在三空间维仅有四个 staples，而代码除以 6。
8. 若用规范化 staple 平均应为 α/4；这是 v2 参数口径改变，不能原地重命名旧 α。
9. 四-staple 当前口径在正齐次投影下可映射有效权重`α_eff=2α/(3-α)`（对本pilot的0≤α<1成立），但不能假定旧 GS 等于正确 APE。
10. 修复完成后，全部 APE 数据需重测；identity 可在核/输入校验相同的条件下复核复用。

验收：随机独立端点变换、至少多 seed、多 α、多步均满足约定容差；
complex128 CPU 建议 atol 1e-10（待实现时按条件数设计），同时检验 det、unitarity、finite。
冷场、α=0、steps=0、非对易暴力圈须继续通过。
若协变性失败或近奇异未定义，停止生成新物理分数。

## P1：缓存与冻结可信边界（CPU 即可）

涉及 `common.read_nersc/load_data`、`measure.measure`、`experiment.develop/evaluate`。
现行 provenance 保存 protocol 和每组态秒数，但没有原始 gauge hash、代码 hash、环境/设备记录。
NERSC reader 固定 `<c16`，没有验证 DATATYPE、FLOATING_POINT、checksum、payload 长度。
必须先确认共享生成器写出的实际格式，不能把它当任意 NERSC reader。
共享来源还包括 `tasks/pion_projection/measure.py` 对相同 `wilson_b6.ID` 的读取。
应核对生成链、保存间隔、热化、随机种子、action 和读写轴序；本轮没有当地原始 gauge 数据。

- NPZ 强制验证完整 shape `(Ncfg,Nkernel,3,5)`、dtype、finite、ID 唯一有序。
- 验证 protocol 几何与实际 gauge header 一致。
- 加 payload hash、每个输入 gauge hash、kernel source hash、commit/dirty 状态。
- 保留硬件、库版本、精度、setup/measurement/write 分时。
- measure 目前循环覆盖同名 NPZ，无完整 resume 校验；改为新 run 目录与原子保存。
- develop 保存 development_sha256，但 evaluate 没有重新检查它。
- evaluate 只核对协议 hash，不能证明执行核与冻结核相同。
- submission 应冻结核实现、参数、投影版本、输入清单、统计版本及全部 hash。
- 任意 build_kernel candidate CLI 尚未实现；现行仅四核列表。
- 后续 candidate 先离线审查时间局域、协变、确定性、无 temporal links，再允许重测。
- 修改代码与协议后使用新 version、新目录；旧 submission 永不覆盖。

验收：修改一字节数据、换核源码、调换 ID、换协议、重复 ID 均明确拒绝。
缺少输入 gauge hash 的旧产物标为 legacy provenance，不能补造历史 hash。

## P2：配对区间与统计审查（缓存可做）

旧 JSON 只有每个核 risk 点估计，没有 risk 比值的区间。
同一 `bootstrap_indices` 保持了核间配对，但 vb 的 SE 不是 score 的置信区间。
因此“±3% 不显著”原报告没有附其所需的配对检验依据；也绝不等于等效。

本轮缓存探索：validation 按 5 组态成 6 块；外层1000次整块配对重采样，
seed=773；每个外层样本都对四核使用同一 inner indices，
inner=1000，seed=20261117，按原 risk 和固定开发 Vref 重算。
对 identity risk/candidate risk 的 percentile [2.5%,50%,97.5%]：

| 候选 | 2.5% | 50% | 97.5% |
|---|---:|---:|---:|
| APE(0.5,5) | 0.673643 | 2.434330 | 23.475481 |
| APE(0.5,10) | 0.702845 | 2.761984 | 21.019946 |
| APE(0.7,10) | 0.689504 | 2.738871 | 19.924634 |

这些仅是**探索性 nested bootstrap**，六块下有重复块退化与强偏斜，不能当校准过的正式 CI。
它们均跨 1，支持“目前未证明改善”，不支持“无效/等效”。
且 P0 已表明旧 APE 核无协变性，以上只能保留为统计流程诊断。

下一步输出独立 audit JSON（未来实现时新增，不在本轮创建）：

- 精确复算旧点值，记录 score epsilon、seed、完整窗口与 denominator 定义。
- 输出每 R 的 SE²/Vref² 与 spread²/Vref²，避免均值掩盖 R=3 主导。
- 配对外层重采样保持整个 `(kernel,R,T)` 向量，不独立重采样各核。
- 区分 outer 数据不确定性与 inner Monte Carlo SE，不混用两类 bootstrap。
- 不允许对单组态 W 先取 log；先 ensemble mean，再 log。
- 非正均值、bootstrap 非正 W、NaN 明确计数并失败，不能只丢失败样本。
- 小样本下比较 percentile、jackknife、合成校准；不机械推荐 BCa。
- 用构造的同效、已知增益、强相关、弱相关数据校准覆盖率/假阳性。
- 扫 block length、链段、leave-one-block-out，记录有效块数与结果敏感性。
- 根据原始 Markov 保存间隔与 τint 选择 block；当前“5 保守”没有验证。
- 禁止用本次留出重调 α、N、窗口、门槛后再称其为验证集。

正式成功标准须预注册：配对比值区间下界>1且超过预设最小有用增益；
最小增益、置信度、多候选校正和统计功效均待设计，不把60组态当保证。
失败条件：区间跨1、参考失败、质量失败；保留负结果。
等效结论需要预设等效界和相应检验，不能由未拒绝零假设代替。

## P3：谱/平台目标重审（先CPU，后新测量）

纯规范静态源的理想谱表达为 `W_ij(R,T)=Σn Z_i,n Z_j,n* exp(-E_n T)`。
空间 smear 改变 overlap，目标是更快隔离 E0，并不改变同一作用量下 E0。
多个相邻窗口一致不排除它们共同落在错误平台。
现行 risk 完全不罚相对真实 E0 的共同偏移，所以不是“总误差”的完整定义。
开发 Vref 只作尺度，并非真值；gate passed 仅代表代码定义的 gate 通过。

- 合成两态/多态、共同偏差、噪声相关、短平台与负均值测试。
- 检查拟合 log bias 与 T 相关协方差，报告条件数及 shrinkage 的选择依据。
- 预先固定更早/更晚 T 的诊断范围，不事后挑最好窗口。
- 有限时间 Wilson 圈不应未经推导直接套 pion cosh。
- README 的回绕项“1e-4–1e-6”没有统一支持：若仅按其模型，
  相对因子为 exp[-V(16-2T)]，T=8 时等于1，绝非普遍可忽略。
- 这不是断言 Wilson 圈必有等幅 cosh；需从有限时间静态源 transfer matrix 推导允许态。
- 用较长时间方向或有限温谱对照检验，明确有无 wrap-around 路径贡献。
- 若改 gate/拟合/risk，发布新版本；旧分数只作历史记录。

## P4：确实可能成立的理论路线

### 较小实现改动：纯空间 stout 对照

在投影修复与回归之后，可增加独立stout候选`U'_μ=exp(iQ_μ)U_μ`，其中Q由空间staples构造为无迹Hermitian矩阵，时间links保持原样。它避免额外的SU(3)投影，但仍需相同的协变、反射、精度与成本测试。
原始依据：[Morningstar–Peardon, hep-lat/0311018](https://arxiv.org/pdf/hep-lat/0311018)，本轮读到正文§II的定义、纯空间权重选择和规范变换证明；该文不保证本pilot的收益。固定半径/成本和开发调参预算，比较正确APE与stout；不把换算法等同于已有物理改进。

### 优先：小型 operator basis + GEVP（需新 cross loops）

原始依据：[Blossier et al., JHEP 0904:094](https://arxiv.org/abs/0902.1265)。
其分析支持合适时间区间与基底下抑制未包含态污染；本轮已阅读原文摘要。
完整实现前再读正文关于 t0、t 与矩阵非奇异条件，不能把渐近结论当短T保证。
对相同 R 用2–3个已验证协变、时间局域空间线构建完整 Cij。
现有四个核各自 W_ii 不能恢复 Cij，禁止从 NPZ 拼假 cross matrix。
扩 `measure.loops` 支持底线 i、顶线 j；固定 temporal transport 和 orientation。
解 `C(T)v=λ(T,T0)C(T0)v`，C(T0) 条件数与截断在开发集冻结。
采用时间片内不同 smear 半径/同端点对称路径；保持静态源量子数与空间对称性。
同一 frozen 向量/算法用于全新验证样本，报告 eigenvector 噪声与排序不稳定。
收益假设是减少激发态，尚无本仓库实证；计算预算需先用小样本 profiling。

### 次优先：multilevel（独立测量算法，不能算 kernel-only 胜利）

原始依据：[Lüscher–Weisz, JHEP 0109:010](https://arxiv.org/abs/hep-lat/0108014)。
原文摘要支持纯规范局域理论利用多层条件平均降低大圈误差，示例为 SU3 Polyakov 相关。
本项目纯规范条件相符，但需要固定边界子晶格更新；缓存 W 无法实施。
先验证 action/locality、子更新正确平衡、边界与空间 smear 支撑不跨错误分层。
在独立任务比较相同总 GPU/CPU 时间成本下误差，而非仅比较组态数。
R≤3 的小圈是否值得额外 setup 尚无证据；以先导 cost-error 曲线决定停止/继续。
不得把论文大面积极限提升倍数外推为本任务收益。

## 测试矩阵与执行顺序

| 阶段 | 输入 | 必做检查 | 输出与退出条件 |
|---|---|---|---|
| P0 CPU | 随机SU3/冷场 | 双边协变、APE后圈不变、unitarity、singular | 测试通过才可重测 |
| P1 CPU | 旧JSON/NPZ、合成header | hash、shape、ID、版本、拒绝篡改 | provenance audit |
| P2 CPU | 完整缓存 | 点值复算、配对区间、覆盖率、block敏感性 | 标探索/正式边界 |
| P3 CPU | 合成谱 | 共同偏差/两态/相关噪声/非正值 | gate与risk方案冻结 |
| 重测GPU | 同一旧gauge | CPU/GPU逐项对照、计时、修复核 | 新版development，不覆盖旧run |
| 新盲测 | 全新未见gauge | 输入隔离、核与统计冻结、配对评估 | PASS/INCONCLUSIVE/FAIL |
| GEVP | 新cross matrices | Hermitian、正性、条件数、谱校准 | 独立v3实验 |

旧0–99组态全部已被分析或相邻披露，均不能用作新盲验证。
扩留出必须使用未见过的样本、足够热化/间隔和 provenance；60+只是规模建议。
先估 τint 与最小有用增益，再做功效/资源设计；不虚构所需 N。
现有 provenance 记录首次开发组态15.76s，其余多约1.4–1.8s，
不能把此当新投影/新硬件下的计时承诺；setup/solve概念在此应分为加载/平滑/圈收缩/写盘。
先小规模 profiling，再向用户报告预计总量；本文件不授权启动远程生产。

## 后续 agent 第一轮交付

先只做 P0 回归与小范围修复，附失败前/通过后的 CPU 证据。
第二轮完成 P1/P2 可审计分析；再决定是否值得 GPU 重测。
修复协变性前停止所有“更好 smearing”的物理主张。
即使修复后仍无显著收益，也保留该负结果及成本，不无限搜索直到成功。

### P0 完整复现命令（仓库根目录，无GPU，无文件输出）

```bash
PYTHONDONTWRITEBYTECODE=1 python -B - <<'PY'
import numpy as np
from tests.test_wilson_loop import random_su3
from tasks.wilson_loop.kernels import ape, dagger
from tasks.wilson_loop.measure import loops
rng = np.random.default_rng(3)
u = random_su3(rng, (3, 2, 2, 2, 2))
g = random_su3(rng, (2, 2, 2, 2))
v = random_su3(rng, (2, 2, 2, 2))
def transform(a):
    return np.stack([g @ a[i] @ np.roll(dagger(g), -1, axis=3-i)
                     for i in range(3)])
vg = g @ v @ np.roll(dagger(g), -1, axis=0)
p = {'r_values': [1], 't_values': [1]}
a = ape(u, 0.5, 1)
ag = ape(transform(u), 0.5, 1)
print('link covariance:', np.max(abs(ag-transform(a))))
print('raw loop invariance:', np.max(abs(loops(transform(u), vg, p)-loops(u,v,p))))
print('APE loop invariance:', np.max(abs(loops(ag,vg,p)-loops(a,v,p))))
PY
```

本轮输出依次 0.442292531289015、2.2551405187698492e-17、0.008637815130061252。
raw loop 对照排除了本反例的坐标/端点变换错配；APE 后规范不变性明显失败。
根 agent 已运行14项现有CPU测试全通过，但该结果不覆盖此新增反例。
GPU、CuPy、mpi4py、PyQUDA 在本地不可用，未做对应验证。

## LatticeArena 框架扩展总纲：由测试反例驱动接口设计

本节是三个任务共享的架构开工方案，不把框架扩展限定为Wilson loop。
评分细节见[相邻pion开工单](../pion_projection/todo.md)，学习算符见[学习核开工单](../optimize_gaussian/todo.md)。
下面列出的模块/接口都是**拟议实现**；当前仓库只有已有的core/io.py、core/stats.py及任务内函数。
优先从现有函数抽出小接口，两个任务实际复用后再抽象，不以重建旧注册表作为第一项工作。

### F0 从已执行检查提炼可复用能力

| 本次测试/源码证据 | 暴露的框架缺口 | 应当形成的公共能力 | 最小验收 |
| --- | --- | --- | --- |
| 原14个CPU测试通过，APE后圈却不规范不变 | SU(3)成员资格被误当完整物理约束 | operator contract及属性测试工厂 | 同时测unitarity、双侧协变和最终observable不变 |
| 学习特征的错误闭环；修闭环后仍不满足轴交换 | 单个gauge测试覆盖不了完整表示 | 分离gauge、Hermitian、O_h、平移、时间局域各项证据 | 每项独立PASS/FAIL/NOT_RUN，不能合成一个含糊“通过” |
| T32反射检查仍按T16索引 | geometry/源位置只是配置字符串 | 带轴名的observable spec和geometry参数化测试 | T16/T32、非立方格点、非零source-origin的适用范围有明确定义 |
| reference由环境切换、依赖helper未被hash覆盖 | 冻结缺乏完整语义身份 | 版本化RunSpec与依赖闭包指纹 | 同一身份不允许改变reference、算符或统计目标 |
| 固定W响应无法支持任意W训练 | 缓存没有声明数学可重用范围 | 带basis身份和能力声明的MeasurementBundle | W/基底/收缩改变使旧响应拒绝复用 |
| 同一份数据更换reference可翻转排序 | scorer与物理目标、参考耦合 | 独立ReferenceProvider、Metric、Comparator | 每项结果携带estimand、reference、基线与比较族身份 |
| 学习核与pion的fold/block不同 | 各task复制统计流程且口径漂移 | 共享ResamplingPlan及fold-local流水线 | 同一输入和spec在两条入口得到相同统计量 |
| LLM入口与SLSQP入口校验不同 | 搜索器可以影响评测定义 | 统一SearchAdapter、Evaluator和预算账本 | optimizer/LLM都只能提交同一种CandidateSpec |

### F1 五个可扩展接口，先明确数据流

建议状态流：`RunSpec → 数据清单/划分 → 算符认证 → development搜索 → 冻结 → validation测量 → 配对比较 → 报告`。
已有数据离线重分析可从MeasurementBundle进入，但必须标为历史诊断，不能重新获得盲测身份。

1. **TaskSpec/RunSpec**：任务物理定义与一次运行分开。TaskSpec定义observable、量子数、允许算符、测量后端和科学目标；RunSpec冻结geometry、边界、source、split、协议版本、reference、metric、budget与代码身份。
2. **OperatorContract/CandidateSpec**：描述输入axes、dtype、变换律、field线性、Hermitian、时间支撑、空间表示，以及参数与依赖文件。不要求所有任务都Hermitian/正定，要求每个任务显式声明哪些条件必要。
3. **MeasurementProvider**：输出完整数组和manifest；支持CPU小场、已缓存响应、GPU量测。能力包含`linear_response`、`requires_new_sources`、`cross_matrix`，不能从已有单源数组猜出缺失测量。
4. **ReferenceProvider + Metric + Comparator**：reference输出同一draw_id下共享的联合参数；metric只计算定义好的统计目标；comparator负责配对效应、同时区间、质量门控和判定。搜索器没有权力改变这些对象。
5. **SearchAdapter**：SLSQP、Powell、随机搜索、可微学习、LLM共用`propose → evaluate_development → freeze`流程，记录真实调用预算和失败候选；可插拔搜索不意味着可插拔科学定义。

可先在`core/contracts.py`使用小型dataclass/JSON schema表达，保留现有CLI。
不要先写通用深继承框架；先让pion和Wilson各接通一次最小适配器，再决定是否需要registry。
`agents/loop.py`从RunSpec生成prompt，避免T、幂次和窗口硬编码；LLM仅收到允许的开发信息。
`agents/report.py`读取结构化结果，数值表由代码生成，模型解释仍标为叙述。

MeasurementBundle建议明确以下数组，不统一压成无语义二维表：

- pion basis：`C[configuration,basis,time]`；记录source及反射/折叠约定。
- 学习响应：`C[configuration,response,time]`；额外绑定固定W/路径基/基座，明确对哪些参数严格线性。
- Wilson：`W[configuration,kernel,R,T]`；记录空间/时间原点平均方式。
- GEVP扩展：`C[configuration,sink_operator,source_operator,time]`；交叉元素必须实际测量。
- 多source：保留source轴或可审计的源内聚合，独立样本单位仍为configuration/Markov block。

验收时用“同一新候选经过不同后端”而非仅JSON可解析验证接口。
CPU/GPU对照必须固定精度、几何和输入；已有档案不能伪装成当前后端执行证据。

### F2 将过程脚本变成可审计的测试与研究反馈

下一轮建议逐步新增以下入口；本轮只把接口与验收写入todo，未创建这些脚本：

| 拟议位置 | 输入 | 输出/职责 |
| --- | --- | --- |
| `core/operator_checks.py` | CandidateSpec、随机场/变换、seed、容差 | 每项物理约束的残差和反例；供pytest与独立audit共用 |
| `tests/test_operator_contracts.py` | 两个已知合法核及本轮已知坏核fixture | 能抓到错误闭环、GS右协变、轴交换与时间泄漏；合法核不误拒 |
| `core/resampling.py` | cfg IDs、chain/source映射、block/split计划 | 公共paired draw IDs及nested CV计划，不擅自估计reference |
| `core/run_manifest.py` | spec、依赖列表、输入与输出hash | 不可变运行身份、缓存适用性检查、legacy只读读取 |
| `scripts/audit_run.py` | 已有run目录、显式diagnostic spec、新输出目录 | 数据完整性、源码/档案身份差异、可复算指标和NOT_RUN清单 |
| `scripts/summarize_evidence.py` | 本轮机器可读证据记录 | 生成待合并的todo进展片段；不自动把研究假设勾选完成 |

每条证据最少记录`test_id, task_id, claim, code_hashes, input_hashes, command, seed, geometry, dtype, observed, threshold, status, evidence_scope`。
status区分`PASS/FAIL/NOT_RUN/INCONCLUSIVE`；evidence_scope区分`synthetic_CPU/archived_data/live_GPU`。
例如“APE协变失败”要保留坏核反例和修复后合法核结果，不能只保存最后绿色测试数。
例如“模型排序稳健”必须附模型集合、全部配对结果和选择程序，不能由单元测试PASS推导。

每轮工作固定做：

1. 读取todo当前假设、输入范围和首个未完成验收项，创建本轮运行身份。
2. 运行范围内测试/诊断，失败样本与未运行条件同样保存。
3. 将观察映射到具体假设：支持、反驳或信息不足；不要让摘要模型重写数值。
4. 更新对应task todo的“已执行证据/剩余假设/下一判别实验”，保留原结论及被修订原因。
5. 若发现跨task缺口，在此总纲增加对应接口/回归项，随后分别更新两个使用方。

一个doc条目可引用`artifact:...#test_id`，但目标文件必须真实存在；未实现入口始终写“拟议”。
不要把全部future checklist直接标为可执行脚本，也不要因源码修复把旧物理结果升级认证。

### F3 结果状态、统计口径与泄漏边界

运行阶段与科研结论分开保存。例如：

```json
{
  "run_state": "evaluated",
  "operator_status": "pass",
  "reference_status": "unidentified",
  "score_status": "diagnostic_only",
  "comparison_verdict": "inconclusive",
  "score": null,
  "evidence_scope": "archived_data"
}
```

此例是拟议schema示例，不是对本轮某个run新出具的认证。
`evaluated`不等于物理有效，`score=null`不等于程序崩溃，`inconclusive`不等于方法无效。
独立保留算符、reference、数值执行、数据完整性、统计功效各门控。
baseline_id与score_spec_id共同定义比较口径；不同task、不同reference的100分不能直接相加作统一榜单。

所有candidate共享configuration/block重采样索引和reference draws。
CV每个outer fold重新拟合reference、幅度归一化、covariance、特征正交化以及内部超参数。
不能仅把最后的优化器放进CV，而复用完整development拟合量。
候选选择、早停、最佳seed、模型/窗口选择都是搜索的一部分，必须写入预算与split依赖。
已打开的validation永久标记为已观察；改目录名或协议版本不恢复其独立性。
现有可信Python插件仅能做流程级隔离；若将来开放不可信提交，需另建真正的数据访问隔离，当前hash不是隔离机制。

### F4 在保持物理定义清楚的前提下扩大任务范围

| 扩展方向 | 可以复用的部分 | 必须新增的物理/数值证据 |
| --- | --- | --- |
| 多体积、多T、多质量 | RunSpec、数据清单、参数化kernel tests | 非立方轴序、有限体积/温度、reference适用性；不能只改geometry |
| 不同算符/完整相关矩阵 | MeasurementProvider、配对统计 | 新source反演、cross contraction、Hermitian和metric可识别性 |
| 非零动量、momentum smear | 搜索预算和缓存框架 | 相位/复共轭、little group、±p与边界，重新定义表示要求 |
| baryon/三点函数 | provenance、candidate冻结、成本比较 | Wick/自旋投影、source-sink及excited-state结构，不能沿用pion风险 |
| 可微gauge条件核 | OperatorContract、Evaluator | U非线性但quark field线性、梯度有限差分、可重用密度缓存 |
| 跨系综迁移 | 训练/测试数据角色和模型制品 | 以整系综留出检验domain shift；验证使用按a/体积标定的物理半径 |
| CPU/CUDA/ROCm、多rank | 后端接口和数据规范 | 单rank到多rankhalo/全局归约/残差对照；不继承旧单rank证据 |
| multilevel/多source等估计器 | 质量门控、成本账本 | 新测量算法的无偏性与自相关；与kernel-only任务分赛道 |

先选一个扩展轴做成端到端受控实验，不同时更换系综、reference、kernel和估计器后归因于一个因素。
跨任务汇总优先展示有效性、效应区间、成本和失败范围；若将来需要综合榜单，任务权重与缺失项规则必须预先固定。

### F5 实施依赖与最小可交付切片

1. **第一个切片：共用算符测试**。Wilson修投影，学习核修闭环/O_h，pion修T索引；各task所有者负责物理实现，框架只抽取确实复用的测试逻辑。交付失败前/修复后证据。
2. **第二个切片：RunSpec与回放**。pion负责reference factory，公共层负责hash/split/draw身份；Wilson和学习核各实现一个adapter。交付两task同spec统计一致与缓存失效反例。
3. **第三个切片：可插拔评分与搜索**。pion按相邻开工单校准Metric/Comparator，学习核做class×optimizer实验；LLM走同一候选校验与预算。交付全部CPU可复现的合成benchmark。
4. **第四个切片：一个真实新数据实验**。冻结候选和评分，确认算符/参考门控，测新validation与成本；再决定推进GEVP、多动量或跨系综。

不要让三个agent同时修改公共schema；指派一个集成负责人处理`core/`与`agents/`，task负责人实现适配器并提供反例。
主验收不是代码行数或任务数量，而是：加入第二种reference、第三种搜索器或新geometry时，不再复制另一套冻结/统计/证据逻辑。
