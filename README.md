# LatticeArena

LatticeArena 把格点规范理论里的研究问题，改造成**有固定测量流程、固定打分规则**的任务：AI（或人）只优化一个很窄的对象，其余全部由评测器控制。目标不是刷榜，而是看"能不能提出一个真正更好的方案"，并且诚实地报告"没做到"。

当前包含三个研究工作包：**`pion_projection`**（π 介子 sink 设计）、**`wilson_loop`**（静态势 Wilson 圈）和 **`optimize_gaussian`**（学习型 smear 与优化基线比较）。仓库包含相应的测量、参考拟合、优化、打分和诊断流程。

> `wilson_loop` 的 APE 分数 263/233/222 仍是条件诊断，未生成 physical score。Kunshan live archive audit 与D/E HMC链质量诊断图文已完成。D IDs 0–99 development job 128540026 已 `COMPLETED 0:0`，elapsed 12:15:58；终态100/100 loops/provenance与manifest gauge hash/trajectory join核验通过，未重读raw gauge。本地副本和development-only参考窗口诊断已保存：A/B point-max proposal显示2.0965通过未冻结阈值2.5，C joint-max centered/uncentered分别2.7408/4.0844而拒绝，故参考门尚未稳健；APE/stout配对risk比约4.84–12.11，但仅是未认证reference上的同样本开发诊断。新增的 D0–99 offset-insensitive force 分析见[图文报告](results/wilson_loop/development_force_diagnostic_20261121_v1/README.md)：20 blocks、5000/5000 shared draws有效，但identity force对T窗口在大R仍敏感，不认证finite-T或ground-state。Stout每配置kernel+loop约87–175s，APE约0.75–1.27s；不构成matched-walltime或物理改善证明。较早61行hash差异未解释；D100–119 gap、D120–139未授权validation、D140–199封存，physical_score仍为null。图文与后续方案见 [Wilson TODO](tasks/wilson_loop/todo.md)。
> `pion_projection` 的参考仍不可认证，物理分数为 `null`；amendment01 因 smear alpha 与统计 score alpha 混用在 595/2814 停止并保留为负诊断。修正版 amendment02 的 402/cell CPU MC 已完成（2814/2814）：null 28/402 的 CP95 上界约 9.9%，wrong-state 在 ground overlap=0 时仍有 343/402 认证。高层 prereg 与执行 adapter hash 不一致，严格 provenance 标记为 `PARTIAL`。D0–99 correlator development 已完成，但 frozen single-cosh reference gate **FAIL**；两态和有效质量只作同数据开发诊断，不能据此继续 E anchor 或打开 validation。当前计划为D0–99 development、E0–59 anchor、D100–139 gap、D140–199 shared holdout；Pion/Optimize/Wilson须共同冻结后才打开holdout。
> `optimize_gaussian` 的 v9 GPU 系数重训与 test IDs 70–99 held-out 评估已经存在，比值 0.998、95% 区间 [0.78, 1.18]，未检出相对 SLSQP 的差异；该 run 的 $W$ 是固定随机特征基而非训练参数，test 已公开，不是独立新 blind set。新增 CPU learned-initializer 诊断只显示有限预算条件性，不是 learned-smear 物理优势。D0–99 point propagator cache 的 Optimize adapter 身份/residual 集成已核验100/100；schema v2 Optimize RunSpec builder 的 no-launch preflight 和 supervisor 合成 fixture 已通过（builder 11 tests，builder+worker 26 tests）。此前也在合成 fixture 中跑通了 `train.main` 的 CPU worker integration；真实 production `train.main`、生产数据训练及 GPU/QUDA 执行均未运行。真实 production RunSpec、生产 solver policy 冻结、P3 生产2×2和trainable-$W$ 对 Gaussian、同预算 SLSQP与强谱基的 blind comparison仍未完成。
> 新增 CPU 研究诊断：Optimize 的完整算符热核目标比较没有显示稳定 trainable-W 优势，四阶 Chebyshev 在该谱目标上更低（[图文报告](tasks/optimize_gaussian/trainable_w_operator_cpu_20261121_final/README.md)）；Pion 补充了有界 block-risk + 独立 anchor 的条件性分数理论稿（[设计稿](tasks/pion_projection/bounded_score_design_review_20261121.md)）；Wilson 补充了逐draw配对窗口漂移 contrast（[报告与图](tasks/wilson_loop/force_window_contrast_20261121_v1/README.md)）。三项均是 CPU/理论诊断，没有改变物理分数、未测数据或未解封 shared holdout；三个 task TODO 仍保留。
> 总览见 [doc/final_report.md](doc/final_report.md)，todo 覆盖情况见 [doc/todo_coverage.md](doc/todo_coverage.md)。

---

## 快速开始（CPU 就能跑）

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest -q -p no:cacheprovider -rs  # 最近记录：274 passed, 1 skipped, 1 warning
python -m tasks.pion_projection --help    # measure / develop / evaluate / plot / candidate / agent / report
```

有 `development.npz` 但没有 GPU 时，分析和打分都能跑：

```bash
python -m tasks.pion_projection --output results/pion_projection/s16t16_v1 report
python -m tasks.pion_projection --output results/pion_projection/s16t16_v1 agent --rounds 3
python -m tasks.wilson_loop --help          # 第二个任务：静态势
```

`agent` / `report` 需要一个大模型 API key，默认读 `~/Desktop/api.key`（也可以用环境变量 `LLM_API_KEY`），默认走 `https://api.deepseek.com/v1` 的 `deepseek-flash`。

---

## 这个任务是什么

在淬火 Wilson 系综（`16^3 x 16`，β=6.0，κ=0.14）上，固定原点 point source，让 agent 设计 sink 的空间核 `K`：

```
K = Σ_n u_n H^n / A_n,    H = (I + 0.2 · spatial_hopping) / 2.2
```

- 只能改 `u`（7 个归一化系数，`Σu=1`、`Σ|u|≤8`，允许带符号）；
- `H^0 = I` 是局域 sink，也就是 100 分基线；
- 评测器负责反演、收缩、折叠、参考拟合、bootstrap 和打分。

分数：

```
q(t) = C(t) / (A · f0(t)),   f0(t) = exp(-m0 t) + exp(-m0 (16-t))
risk = mean_{t∈{2,3,4,5}} [ Var_boot(q(t)) + (q(t)-1)² ]
score = 100 · (risk_baseline + 1e-12) / (risk_candidate + 1e-12)
```

参考不稳（窗口漂移、拟合 p 值、反射对称等）时，`score` 一律为 `null`。

---

## 仓库结构

| 路径 | 作用 |
| --- | --- |
| `tasks/pion_projection/` | 任务一（π 介子 sink）：`measure.py`（可信测量）、`statistics.py`（参考/风险）、`experiment.py`（develop/evaluate）、`candidate.py`（交卷）、`kernels.py`（参考核）、`protocol.json`（唯一数值真源） |
| `tasks/wilson_loop/` | 任务二（静态势）：Wilson 圈测量、APE 核、平台稳定性打分 |
| `tasks/optimize_gaussian/` | 学习型 smear 的方法与执行框架：规范不变特征、Hermitian hopping kernel、SLSQP/Powell 和 trainable-W 原型；当前 CPU 合成诊断齐全，但 production physics comparison 尚未运行 |
| `core/io.py` | 通用哈希与 JSON 工具，供所有任务复用 |
| `agents/` | LLM 作答入口：`loop.py`（`agent` 子命令）、`report.py`（`report` 子命令）、`llm.py`（API 客户端） |
| `tests/` | 三项工作包与共享框架的 CPU / GPU-free 回归测试；最近完整记录为274 passed、1 skipped、1 warning（CuPy parity环境缺失，Wilson projection路径有已知warning） |
| `doc/` | 任务科学定义、环境搭建、第一次实验结果、kunshan DCU 试跑报告 |
| `results/` | 真实运行产物（默认被 git 忽略，只提交小件），见 [results/README.md](results/README.md) |
| `Note.md` | 一份很详细的中文使用说明：架构、每个文件、远端部署、LLM 接入 |

---

## 跑完整流程

```bash
python -m tasks.pion_projection --output run measure --split development   # 需要 GPU + QUDA
python -m tasks.pion_projection --output run develop
python -m tasks.pion_projection --output run measure --split validation
python -m tasks.pion_projection --output run evaluate
python -m tasks.pion_projection --output run plot
```

顺序不能反：`develop` 会冻结 `submission.json`，之后不许重开。

在 DCU 集群（Slurm）上的完整步骤、移植补丁和踩坑记录见 [doc/kunshan_dcu_run.md](doc/kunshan_dcu_run.md)。

---

## LLM 是怎么参与的

仓库里的 "agent" 有两层含义，别混淆：

1. **`agent` 子命令**：真的调用大模型。它把题目、7 个通道的幅度和风险、历史提案给模型，模型输出 3 个候选 `u`，脚本逐个打分、记录、迭代；最后在开发集上冻结的度量下算一次留出诊断。产物在 `<run>/agent/`，**不会**碰冻结的 `submission.json`。
2. **`agent_signed_mixture`**：这是 `develop` 里 SLSQP 优化器算出来的候选，不是大模型。

`report` 负责"前三名 + LLM 解读"：表格由代码从 `validation_results.json` 生成，大模型只写叙述，产物是 `<run>/REPORT.md`。

---

## 诚实的边界

- 这是 **pilot**：参考态没有通过门控，所有 `score` 为 `null`；`agent_signed_mixture` 相对 Gaussian 的 1.63 倍（区间 [1.40, 2.19]）只是冻结度量下的诊断，不是 SOTA。
- 16⁴、淬火、κ=0.14 的 π 是"重 π"，不能和物理质量比较。
- 提交的核是**受信任的本地代码**，不是沙箱；不要直接跑不可信来源的模块。
- 学习核（`optimize_gaussian`）修复特征后：比 Gaussian 基座好 2.12 倍，候选与 7 参数 SLSQP 打平（0.998 [0.78, 1.18]）；细节见 [tasks/optimize_gaussian/README.md](tasks/optimize_gaussian/README.md)。
- 第二个任务（`wilson_loop`）的 pilot 结论是负面的：开发集上 APE 比不平滑好 4.5 倍，但留出集只有 6 个块，差异消失（score 95.7–102.7）。见 [tasks/wilson_loop/README.md](tasks/wilson_loop/README.md)。
- 仓库里的 `tasks/pion_projection/protocol.json` 是 30/5/15 的原始协议；已提交的这次运行用的是 60/10/30（协议快照在 `results/pion_projection/s16t16_v1/protocol.json`），所以 `develop`/`evaluate` 不能直接在这份数据上重跑。

---

## 历史

旧的多任务实现（`core/task.py` 注册表、`wilson_loop`、`pion_2pt`、`gsfit_2pt`、CI、排行榜页面）保留在提交 `f62c613` 中；重置提交是 `5e0ceb9`，当前 pilot 从 `3a88b10` 开始。访问方式：

```bash
git show f62c613:core/task.py
```
