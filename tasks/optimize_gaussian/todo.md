# optimize_gaussian 后续研究与开工清单

本文件是研究规划，不是新实验报告。依据当前源码、JSON 数值及 NPZ 结构审阅；未运行 GPU、MPI、远端或模型 API。
核对日期2026-11-18，Git基线`40a7c9d`；本轮CPU反例不等于修复已经实现。
核心约束：先证明执行核、训练响应、对称性和评测目标一致，再讨论学习空间是否值得扩大。
已有 validation 在多个版本中被反复观察，后续只能称历史诊断集。
后续研究重点见§12及末尾的谱类表达能力反例；[框架扩展总纲](../wilson_loop/todo.md)规定共享算符认证、MeasurementBundle、搜索预算和证据回写，[pion评分重设计](../pion_projection/todo.md)规定统一科学目标。学习task负责新函数类与训练器，不能单独换一个有利loss作为胜出证据。

## 1. 职责与交接边界

本任务负责规范协变、时间局域的学习型 sink kernel。
上游 pion_projection 负责传播子、参考态、risk 和正式冻结评测。
不要在本任务私自修参考态，或把 require_valid=False 的诊断包装成正式分数。
本阶段允许做 CPU 算子审计、离线重分析和新实验设计。
新增 GPU 样本需要独立计划、资源预算与执行授权。
不得覆盖 results 中历史文件；每次运行使用独立目录。
不要直接执行 README 的 sbatch 或 compare 命令：前者提交集群任务，后者会写旧候选目录。

## 2. 代码与数据地图

- `features.py`：周期 shift、dagger、三个空间 plaquette 实迹、方向输入。
- `kernels.py`：实系数最近邻核与二次型 correlator。
- `submission.py`：供 pion candidate 调用的精确三明治核。
- `train.py`：响应收集、Powell、正则选择、测试和绘图用 q。
- `protocol.json`：当前 v7 参数；不是 v1–v6 的历史配置快照。
- `compare.py`：历史 v8 配对诊断；输出位置硬编码。
- `plots.py`、`compare_plot.py`：展示产物，不能替代风险计算。
- `tasks/pion_projection/statistics.py`：blocks、bootstrap、risk、ReferenceFit。
- `tasks/pion_projection/candidate.py`：精确测量、冻结及数据身份检查。
- `tests/test_pion_projection.py`：已有通用统计、参考和基本核测试。
- 目前 tests 只有 pion_projection/wilson_loop 两文件，没有学习特征专属测试文件。
- `results/optimize_gaussian/smoke{,20,_h2}`：最初形状拟合档案。
- `results/optimize_gaussian/v2`–`v7`：响应、模型、风险和图。
- 没有独立 v1/v8 目录：v1 对应 smoke 系列，v8 在下述候选目录。
- `results/pion_projection/s16t16_v1/candidates/f686a72d9c868716/compare.json`：配对风险。
- 同目录 development/validation NPZ、frozen.json、paired_draws.npz：正式接口的历史诊断。

## 3. 原始产物支持什么

下表数值直接取相应 JSON，不把 README 当测量证据。

| 档案 | 直接支持的事实 | 限制 |
| --- | --- | --- |
| smoke | loss 0.255992 → 6.216e-24；历史验证 loss 0.052628 vs base 0.362622 | 形状目标不是完整风险 |
| smoke_h2 | final loss 5.297e-23；验证 0.339356 | 几乎拟合完不等于泛化 |
| smoke20 | final loss 1.078e-24；验证 0.645719 | 比 base 更差，反驳训练 loss 即成功 |
| v2 | test risk 0.0195236 vs 0.0384388 | 仅 10 个历史测试组态 |
| v3 | 0.0310939 vs 0.0297323，base/learned=0.956211 | 非负版本没有增益 |
| v4 | 0.0225522 vs 0.0297323，比值 1.318376 | 早期结构与当前不同 |
| v5 | uniform 0.0161648、spatial 0.0174601、full 0.0144570、base 0.0196002 | 单次划分消融 |
| v6 | learned 0.0130868，base 0.0196002，比值 1.497699 | A1+ 名称仍需检验 |
| v7 | learned 0.0128696，base 0.0196002，比值 1.522977 | 同一历史测试样本 |
| v8 | SLSQP 0.007702708、learned 0.009596964、local 0.312670255 | 参考 gate 失败下的诊断 |

v8 字段 `ratio_a1p_over_slsqp` 实际计算 R_slsqp/R_a1p。
其点值 0.802619244，95% 区间 [0.635534515,0.944254941]。
它是 inverse-risk 改善比，不能按字段名字理解为 R_a1p/R_slsqp。
当前冻结度量下 SLSQP 更好；不能推广成学习方法普遍无效。

NPZ 结构已只读检查：

- smoke C=(10,28,16)，smoke20=(20,28,16)，smoke_h2=(10,10,16)。
- v2 C_fit=(20,28,16)，C_dev=(10,28,16)。
- v3 两个基座的 C_fit=(20,28,16)，C_dev=(10,28,16)。
- v4/v5 C_fit=(20,28,16)，C_dev=(30,28,16)。
- v6 C_fit=(20,10,16)，C_dev=(30,10,16)。
- v7 三份 seed 响应各 C_fit=(20,10,16)，C_dev=(40,10,16)。
- v3–v7 精确测试 C_test/C_base=(30,16)。
- 这些结构检查不等于独立重算所有历史风险。

v7 fit IDs=0–19，dev_val=20–59，test=70–99。
三个 seed 是 W 的随机特征 seed，不是三个系综或三个数据划分。
λ=0.01 的 dev risk 分别 0.003972706、0.003953458、0.003906464。
λ=0 时分别 0.068726392、0.028619632、0.022048875。
因此只能说该划分下正则后对三份 W 不敏感。
不能由此推出训练 W 无用，也不能说已证实跨数据种子稳定。

## 4. 必须先澄清的公式和约定

空间轴是 (z,y,x)，direction d=0,1,2 对应 x,y,z。
场维度是 (z,y,x,color,n)，n 汇总其余传播子指标。
shift(a,k,d)=a(x+k μ_d)，实现 roll(-k,axis=2-d)。
规范变换应满足 U'_μ(x)=g(x)U_μ(x)g†(x+μ)。
场变换为 f'(x)=g(x)f(x)。

实系数核：

\[
C(a)=I+\sum_\mu[a_\mu(x)T_\mu+a_\mu(x-\mu)T_\mu^\dagger].
\]

后向系数错一格会破坏 Hermitian；不要仅测试输出实部。
submission 实际是 K=B C(a) B，B=(I+α hop)^m。
train.collect 使用 <B S,C(a) B S>，由 B†=B 可与精确核一致。
train/submission docstring 写单侧核，不能作为执行定义。
训练 base C0=<BS,BS> 对应 B²，不是 B。

当前 α=0.09090909、m=8。
它不等于 pion H=(I+0.2 hop)/2.2 的一步形式。
即使整体尺度可被幅度拟合消除，hop 与 identity 比例仍会改变频谱。
比较 Gaussian 基座前必须明确两者半径和归一化，不要混用 H^8 与 B²。

features.py 返回 ReTr(P)/3，README 写 1-ReTr(P)/3。
两者经 tanh 和去均值后通常不能用整体符号简单替代。
特征在每个方向、每个时间片对空间去均值；不等于逐点旋转投影。
当前 W 的两个输入权重不相等，交换两个横向平面一般改变 tanh。
正向原点 plaquette 在反射下还会改变锚点。
因此“共享 W”不足以证明 O_h/A1+；主 agent 的轴交换反例已显示当前执行核不满足该约束。
更根本地，当前 plaquette 路径未闭合，独立 CPU 复核已证实规范不变性失败，见末节。

训练 risk_of 未调用 fold，block_length=2。
正式 candidate/compare 调用 fold，使用 pion 快照的 block_length=5。
两者风险不可直接按数值相等验收；v7 与 v8 差异也不能全部归因于模型。
训练固定 m0，但 bootstrap masses 来自上游参考；需要记录质量样本和索引配对。
q_curve 使用未折叠均值和普通最小二乘幅度，仅供图示。
不能用图示 q 代替正式协方差加权 q。
optimize 返回名为 risk 的 fit.fun 包含正则项，应拆成 raw_risk/penalty/objective。
正则实际为 λ mean(v²)，不是 README 的 λ sum(v²)。

## 5. P0：CPU 正确性与身份审计

### 5.1 算子测试

建议新增 `tests/test_optimize_gaussian.py`，先只用 NumPy 小格点。
输入：随机复场、QR 生成 SU(3) links、固定 seed、双精度。
使用非立方小格点检出轴交换，立方格点做群测试。
输出：相对残差、seed、geometry、dtype 和失败样本。

- 测 shift 的周期边界和正负方向。
- 测 <f,Cg>=<Cf,g>，相对残差目标 <1e-11。
- 测 K 的 Hermitian，使用 f≠g，不能只看 <f,Kf> 实部。
- 测 `K[U'](gf)=gK[U]f`，随机局域 g。
- 测训练线性响应与 submission 精确 <S,KS> 一致。
- 包括零 theta、仅 c、仅一个 v、混合 theta、m=0/1/8。
- 改变每一分量并测有限差分响应，确认没有遗漏交叉项。
- NaN、complex coefficients、W/theta 维度不符应明确拒绝。
- Hermitian 不蕴含正定；signed kernel 不应误标为正 smearing。

### 5.2 O_h 测试

实现 24 个 proper rotations 和 parity 的 links/field 精确变换。
反向 link 必须 dagger 并平移锚点。
测试 `K[R U](R f)=R K[U]f`，而非仅测 correlator 平均接近。
对任意 SU(3) links 验证；identity links 太特殊会掩盖错误。
若失败，将历史核标记为“未经 A1+ 认证”；保留原档案。
修复候选：在无向边中心构造 reflection-even loop 特征，再群平均。
也可用轨道上对称多项式；仅排序两个输入还不足以解决锚点问题。
验收：全群相对残差 <1e-10；不通过不得训练更大网络。

### 5.3 缓存与冻结

train.main 仅检查 basis_sSEED.npz 是否存在。
其中没有 IDs、W、完整 protocol、links/propagator 指纹。
改动 steps、alpha、hidden 或数据仍可能命中旧缓存。
collect 直接按 cache_key 读传播子，不复用 candidate 的完整校验。
候选 identity 只 hash builder 所在 submission.py。
其依赖 features.py、kernels.py 改动不自动改变此 builder hash。
这属于身份覆盖漏洞，不能据此指控历史文件已被篡改。

新 schema 必须记录：

- schema version、完整配置与规范化 JSON hash。
- IDs 的顺序、split 与全部原始输入摘要。
- W 数值、seed、代码依赖闭包 hash。
- α、m、geometry、轴约定、dtype、boundary condition。
- QUDA/PyQUDA 版本与反演残差、传播子内容摘要。
- scoring/reference/bootstrap 文件与各自 hash。

验收：只改任一物理参数、ID 顺序或依赖文件即拒绝缓存。
允许新增目录重算，不允许静默覆盖已冻结记录。

## 6. P1：统一离线评测与公平对照

先建独立 CPU audit 入口，输入旧 NPZ/快照，输出新目录 JSON。
不要直接运行会覆盖 compare.json 的旧脚本。
所有候选用同一 fold、block、参考质量 draws、late inverse 策略与 bootstrap 索引。
记录原值、统一口径值和原因，不能只保留改善后的值。
同时输出 variance、departure_squared、amplitude Z、SNR、q 和失败比例。
reference gate 失败时输出 diagnostic_only，正式 score=null。
嵌套 bootstrap 需记录退化 draw，不能选择性丢弃失败样本。

SLSQP 与学习核的公平性分两层：

1. 同样候选数据上的冻结风险比较：已有 v8 回答了这一层。
2. 同样训练信息/调参预算/物理约束下的方法比较：当前尚未完成。

第二层统一 fit/dev 样本及 L1/谱范数或输出幅度约束。
同时比较 uniform、固定 W spatial、full、七通道混合。
SLSQP/Powell 都报告起点数、函数调用数、收敛状态、边界饱和。
不要只给学习模型增加搜索预算；也不要用参数个数相近代替函数类可比。
以同一训练流程进行连续块外层交叉验证，内部选 λ/seed。
历史 70–99 可用于探索性重分析，不再作为独立确认集。
新盲测必须新数据或预先封存且从未读过的来源。

参考模型是本任务共同瓶颈。
使用上游已冻结的单态/两态或预注册模型平均方案做敏感性分析。
权重只能由开发数据决定，不能按哪个参考让学习核胜出来选择。
参考更换后重新传播质量、幅度和协方差不确定性。
若候选排序随合理参考翻转，结论为参考依赖，不宣称物理改进。

## 7. P2：学习空间为何以及如何改变

现有核只有一次 a 插入，所以响应关于 theta 严格线性。
把多层非线性网络直接堆在 field 上会改变接口线性性，原则上不接受。
允许对 gauge-only 特征用非线性网络，再线性作用于 quark field。
最小扩大不是默认加大 hidden，而是让学习类包含强基线：

\[
K=\sum_n u_n H^n/A_n+\sum_j\theta_j B_j Q_j[U] B_j.
\]

要求 Q_j Hermitian、协变、时间局域并经 O_h 投影。
u 与 theta 同时训练，theta=0 恢复七通道基线。
此嵌套设计可直接问“空间项是否提供基线之外的信息”。
先测响应矩阵白化后的奇异值与条件数。
若空间响应已近线性落在多项式响应张成空间内，加网络没有判别力。
可把空间响应对多项式响应正交化，但变换只从训练集估计。
不要在全数据上白化后声称外层独立。

另一条路线是协变 Laplacian 的谱滤波或低秩 distillation。
它提供更明确的空间分辨率与带宽控制，但成本、体积标度不同。
它不是当前一步核上的免费性能结论。
GEVP 需要完整 source/sink 矩阵和正定度量；当前单点源响应不能直接替代。
若转向变分优化，先列出新增反演与交叉收缩需求。

## 8. 推荐的最小有判别力实验

问题：在包含 SLSQP 的函数类里，真实空间调制是否有独立收益？

第一阶段完全 CPU：

- 完成 P0，尤其 O_h 与训练/精确核一致性。
- 复算同口径 historical diagnostics。
- 在现有 dev 上做三折连续块外层交叉验证。
- 四臂：七通道、七通道+uniform、七通道+spatial、七通道+full。
- λ 仅在内部选择，所有臂共享数据、参考和随机 draws。
- 现有响应不能直接跨不同 α/m 当作同一基座，缺失处标 NOT_RUN。

第二阶段需 GPU，但只测一个修复后的小空间模型：

- 封存架构、全部超参数、参考和样本数规则。
- 同一批新传播子同时测四臂所需响应，做严格配对。
- 样本数由历史块效应量/方差做 power simulation 决定。
- 不能把预设 30 或 60 个组态称必然足够。
- 报告 setup、kernel apply、measurement、total time，保留精度与残差。

成功条件：new-data R_baseline/R_spatial 的预注册 95% 区间下界 >1。
且收益超过预注册的实际意义阈值，对参考选择和块长稳定。
若区间跨 1：证据不足；若上界 <1：该候选负结果。
若对称性失败、缓存不匹配、参考失效：实验无效或诊断性，不能算方法输赢。
若主要收益来自 uniform，停止扩空间网络，保留负消融。

## 9. 文献入口与支持范围

本轮读取以下原始论文摘要页，未声称精读全文或复现其数值：

- [Peardon et al., 0905.2160](https://arxiv.org/abs/0905.2160)：低秩平滑场和 distillation 的方法依据；不能证明当前 pilot 会改善。
- [Favoni et al., 2012.12901](https://arxiv.org/abs/2012.12901)：保持局域 gauge equivariance 的网络层和 Wilson loop 构造；不替代 O_h/Hermitian 检验。

本文三明治 Hermitian、线性响应和对称性疑点来自源码代数分析。
它们与上述论文的实测性能没有直接等同关系。

## 10. 给下一位 agent 的交付清单

- 先报告当前 HEAD、dirty 状态和实际文件是否存在。
- 以 P0 测试和身份 manifest 为第一批小改动。
- 新增独立 audit 目录，保留历史 JSON/NPZ 原样。
- 写清 observed/inferred/NOT_RUN，不将规划写成完成。
- 交付统一风险表、对称性残差表和缓存失效测试。
- 参考未稳时只报告条件诊断，不输出正式 leaderboard 成绩。
- 最后才决定是否启动新 GPU 数据；不要先扩大模型再寻找可赢的 loss。

### 本轮共享验证补充

主 agent 已运行现有 14 项 CPU tests 通过；当前没有 optimize_gaussian 专属 pytest。
因此该通过不能证明学习核的 O_h、Hermitian 或训练/执行一致性。
当前环境缺 cupy、mpi4py、pyquda，GPU/MPI 验证为 NOT_RUN。
上游 two-state 环境切换的模型 identity/hash 覆盖也需纳入 P0 冻结审计。
不能从 STATUS 继承其它任务“最可信”等结论；各任务仍需独立算子测试。

## 11. P0 阻断项：当前 plaquette 路径确定性错误

`features.py:plaquettes` 的第二段错误地沿 nu shift，第三段错误地沿 mu shift。
闭合路径必须是 U_mu(x) U_nu(x+mu) U_mu†(x+nu) U_nu†(x)。
当前实现不闭合，因而 trace 并非 gauge invariant。
下面反例由本任务独立 CPU 执行，未修改源码：

```bash
python -B - <<'PY'
import numpy as np
from tasks.optimize_gaussian.features import plaquettes, shift, dagger
from tasks.optimize_gaussian.submission import build_kernel
r = np.random.default_rng(20261118)
def su(shape):
    a = r.normal(size=shape+(3,3))+1j*r.normal(size=shape+(3,3))
    q, _ = np.linalg.qr(a)
    q[..., :, 0] /= np.linalg.det(q)[..., None]
    return q
u = su((3,3,3,3))
g = su((3,3,3))
v = np.stack([g@u[d]@dagger(shift(g,1,d)) for d in range(3)])
def closed(u):
    return np.stack([
        np.trace(u[m]@shift(u[n],1,m)@dagger(shift(u[m],1,n))
                 @dagger(u[n]), axis1=-2, axis2=-1).real/3
        for m,n in ((0,1),(0,2),(1,2))], -1)
f = r.normal(size=(3,3,3,3,2))+1j*r.normal(size=(3,3,3,3,2))
p = dict(W=[[.3,-.7],[1.1,.4]], theta=[.1,.3,-.2],
         steps=1, alpha=.09090909)
a = build_kernel(v,p).apply(g@f)
b = g@build_kernel(u,p).apply(f)
print('current plaquette:', np.max(abs(plaquettes(u)-plaquettes(v))))
print('closed control:', np.max(abs(closed(u)-closed(v))))
print('kernel max:', np.max(abs(a-b)))
print('kernel relative:', np.linalg.norm(a-b)/np.linalg.norm(b))
PY
```

本轮输出：current plaquette=0.8418143497696925，closed control=4.996003610813204e-16，
kernel max=0.8924467514886081，kernel relative=0.17420918499030777。
主 agent 使用另一 SU(3) QR/determinant 实现也得到 O(1) plaquette 误差及 0.193904 kernel 相对误差。
主 agent 另测 x-z 交换 kernel 相对误差 0.102821，A1+ 执行要求同样失败。
两份随机场生成实现不同，故不要求数值逐位相同；均远离双精度舍入误差。

因此当前源码的 gauge invariance 和 A1+ 应标为 **FAILED**，不是“尚未证明”。
历史版源码与依赖身份未完整保存，不能断言全部 v1–v8 都有同一错误。
历史 risk 表仍是档案中的条件数值，但其物理算符解释必须核对对应代码身份。
先修闭环路径并通过局域 gauge 测试，再单独修横向输入排列和反射锚点。
修 plaquette 不自动证明 A1+；通过群测试前不得恢复此物理标签。
修复后使用新 identity、新缓存、新冻结和新测量；不能沿用旧响应声称修复后性能。

### 隔离确认：闭环修复仍不足以恢复 A1+

在上面反例的同一 Python 进程末尾追加以下代码（只替换内存引用，不写源码）：

```python
import tasks.optimize_gaussian.submission as sm

def directional_closed(u):
    q = closed(u)
    return np.stack([q[..., [0,1]], q[..., [0,2]], q[..., [1,2]]])
sm.directional_features = directional_closed
k = lambda u,f: sm.build_kernel(u,p).apply(f)
a, b = k(v,g@f), g@k(u,f)
ur, fr = u[[2,1,0]].swapaxes(1,3), f.swapaxes(0,2)
c, d = k(ur,fr), k(u,f).swapaxes(0,2)
print('fixed gauge max:', np.max(abs(a-b)))
print('fixed x-z max/relative:', np.max(abs(c-d)),
      np.linalg.norm(c-d)/np.linalg.norm(d))
```

本任务独立输出 gauge max=1.831026719408895e-15，而 x-z max=0.5833717067658163、relative=0.10361915449683853。
闭环后 gauge 恢复而轴交换仍失败，因此 A1+ 是独立问题，不能只归咎路径错误。
可靠 CPU oracle：令 K_A1[U]=(1/48) Σ_R R⁻¹ K[R U] R，R 遍历 O_h。
正确实现 links 的方向、负向 dagger 和锚点后，该群平均保留 field 线性、Hermitian 与 gauge 等变，并给出 A1+ 投影。
先以此验证便宜的无向边中心特征实现；仅排序两个输入仍不能修复反射锚点。

## 12. 继续研究：学习型 smear 能否超过强多项式基线

值得认真检验，现有结果没有回答其上限。
SLSQP 是优化算法，不是核函数类。
已有赢家是“七通道扩散多项式类 + SLSQP + 当前数据/参考/约束”的组合。
固定随机 W 加 Powell 没有测试可训练 W 网络的上限。
修复 P0 是新比较可信的前提，不应被解释为停止研究学习核。
以下路线按信息增益/成本排序。

### 12.1 哪些算子自由度可能真正有用

对固定时间片的 Hermitian H，写 H=V diag(h_i)V†。
任意多项式 p(H)=V diag(p(h_i))V† 共享同一本征向量。
增大多项式次数或训练谱响应，可以改善频率权重，但不能改变该本征基。
因此先排除七个稀疏幂次覆盖不足，避免把更宽谱滤波误称空间学习收益。
若目标算子的最佳低噪声方向和 H 的本征方向不一致，非对易修正可能有用。
例如 gauge-conditioned a_mu(x) 的 C(a) 一般与 H 不对易。
它可以混合 H 本征模，也可能仅引入样本噪声。
这个“可能”需要跨样本配对数据支持。

改变函数类有望有益的条件：

- 强多项式类的近似误差大于统计与参考不确定性。
- 局域 gauge 特征含有对低能 overlap 或噪声可迁移的信息。
- 参数有效维数与独立块数匹配，正则具有可解释的约束。
- 优化器能稳定找到改进，而非只在一个起点偶然胜出。
- 新增测量与 apply 成本没有抵消统计效率收益。

更大 hidden 不自动满足这些条件。
若误差由参考偏差或小样本主导，扩大类可能使历史 loss 更低而新数据更差。

### 12.2 结构 A：嵌套强基线的非对易修正（首选）

定义 P_u(H) 包含现有七通道及 identity。
定义 Q_j[U] 为群投影后的实系数边输运或闭合路径修正。
使用 K=P_u(H)+Σ_j theta_j B_j Q_j[U] B_j。
各 B_j 是固定 Hermitian 多项式，Q_j 是 gauge-covariant Hermitian。
逐项 O_h 投影保证零动量目标量子数。
有限 j 下对 u/theta 仍是线性响应模型，最容易审计。
以 theta=0 严格恢复强基线，使用同一归一化与可行约束。
固定 gauge 特征时可预收集全部响应，之后 CPU 优化。

需要避免“嵌套但约束不嵌套”：

- 全类预算不能让 theta=0 时原 u 被更严格约束排除。
- 正则应在 theta=0 恢复基线原目标。
- 原幅度归一化和后续 fold 内拟合需要一致。

类的包含关系只保证同一训练目标的全局 infimum 不更差。
它不保证有限预算优化结果、泛化风险或计算效率更好。
建议先用 1–3 个预定义 orbit 特征，测残差响应秩后再增维。

### 12.3 结构 B：可训练谱滤波与独立路径基

第一层强对照：稀疏幂次改为稳定 Chebyshev 基 T_k(H_tilde)。
H_tilde 的谱映射区间由理论界或训练数据界确定并封存。
不要在测试数据上选谱区间、阶数或滤波 cutoff。
用 K=Σ_k c_k T_k(H_tilde)，通过系数约束控制谱放大。
identity 是 k=0 项；实系数保证 Hermitian。
这个类仍共享 H 本征向量，是强谱滤波基线，不是空间自适应证据。
对目标样本同时检查极端本征值、算子范数和负谱权重。

第二层增加独立路径 orbit：

- 直线路径、折线路径、带闭环装饰的输运路径。
- 路径端点输运矩阵按 gauge transformation 变换。
- 每条路径与逆路径配对，确保 Hermitian。
- 对完整 O_h 轨道求和，确保所需表示。
- 对训练集响应作 QR/SVD 去除与多项式响应近共线部分。

路径响应的正交化度量和截断阈值必须 fold 内估计。
不能把相关函数响应正交称为全算子空间正交。
若路径只重现 hop 的幂展开，没有新有效秩，则停止增加这类路径。

### 12.4 结构 C：真正可训练的 gauge-only 系数网络

构造 `a_mu[U](x;W)`，输入只含修复且对称处理的 gauge 特征。
网络可以非线性依赖 U，但不得非线性依赖传播子 f。
K[U]f 对 quark field 必须保持严格线性。
实边系数、逆边配对、三明治和群投影分别保证 Hermitian 与对称性。
以 residual 输出缩放 epsilon 初始化为零，使初始点恢复基线。
训练 W 与输出层，分别记录优化失败与函数类失败。

现有 C_fit 仅缓存固定 W 对应的压缩响应。
改变 W 会改变 tanh 特征，不能从这份 C_fit 学任意 W。
可选实现路线：

1. 每次 W 更新重新 collect：最简单但 GPU 数据访问昂贵。
2. 缓存 raw gauge features 与局域传播子双线性响应密度，再动态收缩。
3. 保留 gauge/propagator，使用可微框架实现算子及梯度。

第 2 路线需先推导 C(a) 的局域边密度，包含逆边配对和空间去均值。
若 B_j 固定，可缓存 B_j S 的相关双线性量；B_j 也训练则需更丰富缓存。
记录缓存体积、精度、I/O 和隐私/路径身份；不要默认可装入单卡。
第 3 路线需要有限差分检查 W 梯度，不需对 Dirac inversion 反传。
传播子可作为冻结输入，前提是优化范围仅 sink。
先训练小网络，例如一隐藏层 2–8 单元，再按学习曲线决定扩展。

### 12.5 必须做的 class × optimizer 对照

最低 2×2 设计如下，统一目标与约束：

| 函数类 | SLSQP/约束梯度优化 | Powell/无梯度优化 |
| --- | --- | --- |
| 七通道/较宽谱滤波 | 强基准 | 排除算法选择效应 |
| 固定特征嵌套修正 | 检验类收益 | 与既有流程接轨 |

可训练 W 另加带梯度小网络实验，不强行把高维网络交给 Powell。
若只有更换优化器带来收益，结论是优化收益而非空间信息收益。
若扩大谱基已消除差距，不能声称局域 gauge 学习不可替代。

并行报告两种公平口径：

- parameter matched：相近可训练维数/有效秩，保留类差异说明。
- budget matched：相同函数调用、起点和 wall-time 预算，分别报告。

所有方法使用同一可预测信息、样本、内部 split 与 seed 列表。
不得让网络额外读取未来时间片或测试组态统计。
训练 seeds、W seeds、bootstrap seeds 与系综生成 seeds 分开记录。
最佳 seed 的挑选属于调参，必须内部完成，不能报最优测试 seed。

### 12.6 真空间信息与 shuffled 对照

至少比较真实空间特征、uniform、空间项关闭和 shuffled 特征。
shuffled 不能随意打乱 links 或颜色矩阵，那会破坏 gauge covariance。
一种可行零假设：将 gauge-invariant 无向边特征整体做周期平移。
取多个预注册平移并对 O_h 轨道平均，保持方向变换规则。
平移的 feature 场与原 links/传播子局部相关性被削弱，但仍可构造协变核。
不直接把另一组态的固定scalar map贴到当前links上：它会引入外部数据依赖和固定空间锚点，O_h投影也不自动恢复平移协变。这类对照只有另行满足完整数据/平移契约才可接入，首轮使用同组态平移轨道对照即可。
不要把固定 permutation 当作自动对称；需实测全群算子关系。
对照 seed 只在开发阶段规定，真实/假特征用相同网络及训练预算。
若 shuffled 与真实一样好，证据偏向额外滤波自由度或正则，而非局域 gauge 信息。

### 12.7 CPU 最小 synthetic/operator 实验

目标是先证明新类能够表达基线缺失的方向，避免用小系综承担算子调试。
输入：小立方格点 random SU(3)、固定传播子型复场、独立 gauge transforms。
构造两个已知 teacher：p(H) 和 p(H)+epsilon BQ[U]B。
Q 使用经认证的非对易无向边修正，epsilon 在预注册网格变化。
监督目标可取 teacher.apply(f) 或多随机 probe 的二次型。
这不是物理 pion 数据，不应产生物理性能结论。

输出与验收：

- 当 epsilon=0，谱类应在表达/优化容差内恢复 teacher。
- 当 epsilon>0，新增空间类应在新 links/probes 上降低 teacher 误差。
- 同时测 [H,Q] 的范数、响应有效秩和 O_h/gauge/Hermitian 残差。
- shuffled Q 不应系统重现真实 teacher 局域关联。
- 运行 2×2 优化对照，区分局部极值与表达能力。
- 若 teacher 都无法恢复，先调试表达/优化，不上新物理样本。

### 12.8 nested CV 中容易遗漏的上游泄漏

不只 theta/λ 要 fold 内训练。
上游 reference、channel normalization A_n、base amplitudes、late inverse covariance
如果来自全 development 60 个组态，也会把外层验证信息带入目标。
重新构造每个 outer fold 的完整训练状态，包括 reference fit 和 bootstrap masses。
通道归一化、谱范围、正交化、幅度/噪声约束也只由该 fold 训练部分确定。
若无法从现有文件恢复这些训练输入，则该 CV 标为 conditional/transductive diagnosis。
不能用“权重没看验证集”声称整个比较无泄漏。
固定物理常数和人工预设窗口可共享；数据拟合量必须区分来源。
参考不稳的 fold 不能按赢家选择性删除，记录门控失败和失败比例。

### 12.9 新 GPU 实验与优先顺序

优先级 1：P0 + CPU teacher + 完整 fold-local 离线评测。
资源：CPU、现有 NPZ；不需要新 inversion。
优先级 2：结构 A 与较宽 Chebyshev 基线，共享一次新 gauge/propagator 测量。
资源：GPU apply、响应缓存；若已有可信新传播子可免新增 inversion。
优先级 3：结构 C 小网络，先评估 raw density 缓存再决定可微后端。
资源：GPU 特征收缩、梯度与 I/O profiling，不默认需要大模型。

预注册一个主终点：新独立块上风险比或上游稳健物理指标的配对改善。
同时报告单位总计算成本的信息收益；反演、setup、apply、训练分开计时。
成功必须在强多项式基线、参考敏感性和随机 seeds 下保持。
反证：真实空间与 shuffled 无差别，或更宽谱基已获得相同收益。
停止条件：连续预定轮次无新数据收益、成本显著恶化、有效秩不增加。
“不显著”只限制当前效应量与样本范围，不等于证明所有学习 smear 无效。

多动量与 momentum-smearing 是可延伸方向，但应建立新协议。
非零动量 little group 与零动量 O_h/A1+ 不同，不能沿用本任务标签。
动量相位、复系数 Hermitian 条件及 ±p 关系必须重新推导。
应先证明零动量改进机制，再以独立预算考察多动量泛化。

### 12.10 本轮已执行的表达能力检查：存在任何谱滤波都缺失的方向

在3³随机SU(3)场上，取同一Hermitian扩散矩阵H；用闭合plaquette的四角平均、三个空间平面平均构造实标量s(x)，去均值并归一化。
定义V为颜色单位矩阵乘s(x)，`Q=(VH+HV)/2`。s的clover与空间平均构造用于保持gauge与立方变换规则；后续实现仍需完整属性测试。
Q为Hermitian，且通常`[H,Q]≠0`，属于空间非均匀修正。
取人为teacher `K*=I+0.2H+0.1Q`。在H本征基中，任意`f(H)`均为对角矩阵，所以

\[
\min_f\|K_*-f(H)\|_F
\geq 0.1\|\operatorname{offdiag}(V_H^\dagger QV_H)\|_F.
\]

这里`V_H`是H的本征向量矩阵，与前面的对角算符V不同；退化本征值情形该式仍是下界，不必声称可达。
本轮NumPy、complex128、seed321实际得到：

| 检查 | 结果 |
| --- | ---: |
| H、Q的最大Hermitian残差 | 均0（当前浮点构造） |
| `||[H,Q]||_F` | 1.09810309 |
| 任意谱滤波相对Frobenius误差下界 | 0.04421517 |
| 七个偶次幂无约束最小二乘误差 | 0.04463029 |
| 加入H与Q后的线性类误差 | 4.63e-16 |

这是刻意包含非对易项的teacher，证明的是**存在可表达性优势**，不是学到真实QCD最优核或新数据泛化优势。
七幂比较还放宽了实际SLSQP的L1/幅度约束，因而不能把表中数值直接当实际训练收益。
它排除了“任意空间学习都等价于把H多项式加宽”的一般断言；是否需要这些方向，仍由§12.7–12.9的新links/probes与物理配对实验回答。

复现命令（只读，无GPU；正确plaquette在本进程显式构造，未修源码）：

```sh
python -B - <<'PY'
import numpy as np
from tasks.pion_projection.kernels import build_kernel
from tasks.optimize_gaussian.features import shift, dagger
rng=np.random.default_rng(321)
shape=(3,3,3)
a=rng.normal(size=(3,*shape,3,3))+1j*rng.normal(size=(3,*shape,3,3))
u,_=np.linalg.qr(a)
u=u/np.linalg.det(u)[...,None,None]**(1/3)
s=np.zeros(shape)
for mu,nu in ((0,1),(0,2),(1,2)):
    p=np.trace(u[mu]@shift(u[nu],1,mu)@dagger(shift(u[mu],1,nu))@dagger(u[nu]),axis1=-2,axis2=-1).real/3
    s+=p+shift(p,-1,mu)+shift(p,-1,nu)+shift(shift(p,-1,mu),-1,nu)
s=s/12
s-=s.mean()
s/=np.sqrt(np.mean(s*s))
n=3*np.prod(shape)
probe=np.eye(n,dtype=complex).reshape(*shape,3,n)
H=build_kernel(u,dict(powers=[1],weights=[1.],alpha=.2)).apply(probe).reshape(n,n)
V=np.diag(np.repeat(s.ravel(),3))
Q=(V@H+H@V)/2
teacher=np.eye(n)+.2*H+.1*Q
_,VH=np.linalg.eigh(H)
qt=VH.conj().T@Q@VH
floor=.1*np.linalg.norm(qt-np.diag(np.diag(qt)))/np.linalg.norm(teacher)
A=np.stack([np.linalg.matrix_power(H,k).ravel() for k in [0,2,4,8,16,32,64]],axis=1)
def error(A):
    c=np.linalg.lstsq(A,teacher.ravel(),rcond=None)[0]
    return np.linalg.norm(A@c-teacher.ravel())/np.linalg.norm(teacher)
print('Hermitian',np.max(abs(H-H.conj().T)),np.max(abs(Q-Q.conj().T)))
print('commutator',np.linalg.norm(H@Q-Q@H))
print('spectral floor / seven powers / augmented',floor,error(A),error(np.column_stack([A,H.ravel(),Q.ravel()])))
PY
```

与实际统计效率有关的原始入口：[Detmold–Endres, 1404.6816](https://arxiv.org/abs/1404.6816)。本轮读取摘要，支持source/sink优化可能改进信噪比且收益依赖体系及算符基；它未证明本任务的空间网络一定胜过强多项式基线。
