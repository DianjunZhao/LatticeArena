# 静态夸克势：空间 Wilson 线核优化（pilot）

第二个任务。目标：在固定的纯规范系综上，设计一个**空间链路核**（对每个时间片的 3 个空间方向做平滑），用它构造空间 Wilson 线，改善静态夸克势 `V(R)` 的**精度**和**平台稳定性**。

## 固定 vs 可改

| 角色 | 内容 |
| --- | --- |
| 固定（出题人） | 组态与划分；时间方向 link 不参与优化；`R = 1,2,3`；`T = 4..8`；对全部空间点、3 个方向、16 个时间原点取平均；三个拟合窗口 `[4,5,6] / [4,5,6,7] / [5,6,7,8]`；bootstrap 与种子 |
| 可改（agent） | `build_kernel(spatial_links, parameters)`：输入 `(3, t, z, y, x, 3, 3)` 的空间 link，返回同形状的模糊化空间 link。必须规范协变、时间局域、同一规则用于所有时间片与组态、不使用时间方向 link |

参考实现是带投影的 APE 平滑：

$$
F = \mathrm{Proj}\big[(1-\alpha)U + \tfrac{\alpha}{4}\textstyle\sum_{\text{4 staples}}\big]
$$

`Proj` 是**双边极分解**投影：

$$
Q = M\,(M^\dagger M)^{-1/2},\qquad P = Q\,e^{-i\arg(\det Q)/3}
$$

它满足 $P(gMh)=gP(M)h$（独立的左右 $SU(3)$ 变换），这是 APE staple 需要的协变性。
三个空间方向每个 link 只有 4 个 staple，所以归一化是 $\alpha/4$（旧版误用 $\alpha/6$）。
旧版逐列 Gram–Schmidt 只保持左酉；2026-11-18 的 CPU 反例显示规范变换后最大元素差 0.44，已修复。

> **2026-11-18 修复说明**：旧 APE 核不满足规范协变，所有旧 APE 结果（`APE(0.5,5)` 等）
> 只能作为历史诊断；identity 不受影响。数值 $\alpha$ 的口径也变了，新旧关系为
> $\alpha_{\rm new}=2\alpha_{\text{old}}/(3-\alpha_{\text{old}})$（保持 staple 与 identity 的比例）。
> 修复后需要重新测量才能给出物理结论（本轮 GPU 重测未运行）。

## 打分

对每个 `R`：

```
V(R) = -d log W(R,T) / dT      （名义窗口 T = 4,5,6,7 上的线性拟合）
risk(R) = (SE_boot(V) / V_ref)² + (spread_windows(V) / V_ref)²
risk = mean_R risk(R)
score = 100 · (risk_identity + 1e-12) / (risk + 1e-12)
```

- `V_ref` 是**开发集 identity**（不平滑）的 `V(R)`，作为固定尺度；不随候选变化。
- 第一项奖励精度（bootstrap 误差小），第二项奖励平台稳定（三个窗口给出的 V 一致）。
- identity 恒等于 100 分。
- gate：identity 的 `V(R) > 0` 且相对平台散布 ≤ 5%；不过就不给分。

## 命令

```bash
# 需要 GPU（cupy）和组态；CPU 上只能跑测试
python -m tasks.wilson_loop --output results/wilson_loop/s16t16_v1 measure --split development
python -m tasks.wilson_loop --output results/wilson_loop/s16t16_v1 develop
python -m tasks.wilson_loop --output results/wilson_loop/s16t16_v1 measure --split validation
python -m tasks.wilson_loop --output results/wilson_loop/s16t16_v1 evaluate
python -m tasks.wilson_loop --output results/wilson_loop/s16t16_v1 plot
```

`measure` 在 GPU 上约 1.5 s/组态（60 组态约 1.5 分钟）；CPU 上会慢约 10 倍。7 个单元测试完全不需要 GPU：

```bash
python -m pytest -q tests/test_wilson_loop.py
```

## 这次 pilot 的结果（16⁴、β=6.0、100 组态，开发 0–59 / 留出 70–99）

参考通过（identity 的 V(1,2,3) = 0.410 / 0.597 / 0.703，平台散布 0.0004 / 0.0025 / 0.0058）。

| 核 | 开发 risk | 留出 risk | 留出 score |
| --- | ---: | ---: | ---: |
| identity | 7.82e-5 | 5.60e-5 | 100.0 |
| APE α=0.5, N=5 | 1.95e-5 | 5.81e-5 | 95.7 |
| APE α=0.5, N=10 | 1.74e-5 | 5.42e-5 | **102.7** |
| APE α=0.7, N=10 | 1.65e-5 | 5.51e-5 | 101.5 |

**诚实结论**：开发集上 APE 好 4.5 倍，但**没有转移到留出集**——留出集只有 6 个块，±3% 的差异不显著。这个 pilot 目前**没有**证明空间 smearing 能稳定改善静态势；它证明的是这条测量/打分链路能跑通并给出可比较的数字。

## 限制（v0）

- 只支持协议里列的 4 个核；任意 `build_kernel` 提交（`candidate` 子命令）还没实现——那需要重新测量，成本较高。
- `V(R)` 用 T=4..8 的单指数拟合，忽略周期回绕项 `exp(-V(16-T))`（在 1e-4–1e-6 量级）。
- 组态自相关没有测；5 组态一块是保守选择。
- 16⁴、淬火、β=6.0，`V(R)` 是格点单位下的裸势，不能直接和物理量比较。

## 文件

| 文件 | 作用 |
| --- | --- |
| `protocol.json` | 组态路径、划分、R/T、窗口、核列表、种子、阈值 |
| `common.py` | protocol、split 索引、NERSC 读取、npz 读取与校验 |
| `kernels.py` | `build_kernel`（APE + 重幺正化） |
| `measure.py` | Wilson 圈测量（支持 cupy 加速） |
| `statistics.py` | V(R) 拟合、bootstrap、risk |
| `experiment.py` | `develop` / `evaluate` |
| `plots.py` | `V(R)` 与 risk 图 |
| `__main__.py` | CLI |
