# pion_projection：GEVP 与能量目标的设计（预注册草案，未执行）

本文是 `tasks/pion_projection/todo.md` 里 C2（GEVP）和 C3（能量目标）的设计稿。
**没有运行任何 GPU 任务**；所有数字都来自已有的诊断（`results/pion_projection/score_diagnostics_v2/`）。

## 1. 为什么现在的参考救不了

- 单 cosh + 共质量的参考在名义窗口 $[5,6,7,8]$ 上 $\chi^2=52/\mathrm{dof}=8$，窗口偏移 21.6σ/7.8σ；
- 名义窗口是 3 通道 × 5 时间 = 15 维，而只有 12 个 block：样本协方差秩 $\le11$，
  4 个零特征值，靠 25% 收缩 + floor 才可逆；
- 两态参考能过 gate，但 8 参数对 12–15 个点、$\chi^2=0.06$，是过拟合；
  profile 给出 $m_0\in[1.025,1.065]$，宽度约 0.04，是 bootstrap SE 的 4 倍（sloppy 方向）；
- 模型平均的 AIC/BIC 权重退化为两态（$\approx1$），候选排序随参考翻转。

结论：**参考不是“统计量不够”，而是模型/可识别性问题**。C2/C3 都是换问题，而不是继续调阈值。

## 2. C2：GEVP 参考

### 2.1 需要什么

GEVP 要的是**算符矩阵**，不是一条关联函数向量：

$$
C_{ij}(t)=\langle O_i(t)\,O_j^\dagger(0)\rangle,\qquad i,j=1\dots N,
$$

然后解广义本征问题

$$
C(t)\,v_n(t,t_0)=\lambda_n(t,t_0)\,C(t_0)\,v_n(t,t_0),
\qquad
E_n^{\rm eff}(t)=\log\frac{\lambda_n(t,t_0)}{\lambda_n(t+1,t_0)} .
$$

- 现在的 7 个通道（$H^0,\dots,H^{64}$）共享**同一个点源**，只有 sink 不同；
  它们给出的是 $C_{ij}$ 的一行/一列，不是完整矩阵；
- 要补全矩阵，需要**多个 source 涂抹**：对每个 source 核做一次传播子反演（或使用
  低秩/蒸馏方法近似）；
- 成本：现在每配置 1 次反演（12 RHS）；$N$ 个 source 约为 $N$ 倍，$N=4$ 时 4 倍。

### 2.2 预注册项

- 算符集合 $\{O_i\}$：source 与 sink 的 $H^n$ 列表（例如 $n\in\{0,4,16,64\}$，$N=4$）；
- $t_0$：固定为 2 或 3，并报告 $t_0$ 敏感性；
- 窗口：$t=3\dots8$，$E_0$ 的平台取最后三个点；
- bootstrap：按 configuration block 重采样，GEVP 在每个 draw 内重新求解，并检查 mode 交换；
- 失败判据：$C(t_0)$ 非正定/近奇异、本征值排序在 draw 间交换、$t_0$ 改变使 $E_0$ 移动超过
  预注册阈值、矩阵非 Hermitian 超误差。

### 2.3 验收

- 在合成数据（已知 $E_0,E_1$ 和 overlap）上，$E_0$ 的偏差 < 0.5%，coverage 在 MC 误差内；
- 在真实数据上，若 GEVP 的 $E_0$ 与单 cosh/两态一致且在误差内，则说明参考问题缓解；
  若不一致，输出“参考不可识别”，不强行给分。

### 2.4 合成数据验证（CPU，已完成）

`tasks/pion_projection/gevp.py` 实现了 GEVP 求解，并在已知两态谱的合成矩阵上验证：

- $N=3$ 个算符、$m_0=0.8$、$m_1=1.4$、200 个 block、1% 乘性噪声、$t_0=2$；
- 基态 $E_0=0.800\pm0.002$（真值 0.8），激发态 $E_1=1.40\pm0.02$（真值 1.4）；
- 奇异 $C(t_0)$ 与非 Hermitian 矩阵会明确拒绝。

![gevp synthetic](../results/pion_projection/score_diagnostics_v2/gevp_synthetic.png)

### 2.5 现有数据的 2×2 Hankel GEVP（CPU，已做）

对 sink 核 $K_i=H^{n_i}$，交叉关联满足

$$
C_{ij}(t)=\langle K_iS,K_jS\rangle=\langle S,H^{n_i+n_j}S\rangle=C_{0,n_i+n_j}(t).
$$

在已测的 7 个幂次 $\{0,2,4,8,16,32,64\}$ 里，只有 $\{0,8\}$ 的所有和（$0,8,16$）都在集合内，
所以能做的是一个 **2×2** Hankel GEVP（`tasks/pion_projection/hankel_gevp.py`，$t_0=2$）：

| 量 | 结果 |
| --- | ---: |
| $E_0$ | $1.067\pm0.010$ |
| $E_1$ | $1.276\pm0.009$ |
| $E_0(t=3,4,5,6)$ | 1.139 / 1.108 / 1.060 / 0.964 |

**没有平台**：$E_0$ 随 $t$ 单调下滑，$E_1$ 从 1.54 掉到 1.04（向 $E_0$ 靠拢）。说明 2×2 矩阵
不足以分离激发态，现有数据无法裁决“单 cosh 1.086 vs 两态 1.057”的分歧。

### 2.6 补测 $H^{24}$ 后的 3×3 Hankel GEVP（CPU，已做）

为了把 $\{0,8,16\}$ 的矩阵补全（$8+16=24$），在 `protocol_gevp.json` 里把幂次扩成
$\{0,2,4,8,16,24,32,64\}$，重测了同一批 60/30 组态（GPU，约 20 分钟）。3×3 GEVP（$t_0=2$）：

| 数据 | $E_0$ | 每时间点 $E_0(t=3,4,5,6)$ |
| --- | ---: | --- |
| development | $1.026\pm0.017$ | 1.068 / 1.061 / 1.025 / 0.950 |
| validation | $0.997\pm0.018$ | 1.060 / 1.005 / 1.035 / 0.890 |

**仍然没有平台**：$E_0$ 随 $t$ 下滑，dev 与 val 也相差 0.03。原因是 Hankel 矩阵的高阶通道
（$H^{32}$、$H^{24}$）在 $t\ge5$ 时已被噪声主导，而 powers-of-$H$ 家族彼此高度相关，
增加一个幂次不足以提供独立的算符方向。

### 2.7 现状

**合成验证已完成；真实数据的 2×2 与 3×3 尝试都无平台**。结论：仅靠 powers-of-$H$ 不够，
真正的 C2 需要**不同的 source 涂抹/算符结构**。多 source 的测量已跑通（90 组态、约 4 分钟），且 source/sink 矩阵是合法的 GEVP 矩阵；
但 $H^0/H^4/H^{16}$ 的 3×3 矩阵条件数太差，$E_0$ 强烈依赖 $C(t_0)$ 的本征值 floor
（$10^{-8}$ 时约 0.9、$10^{-2}$ 时约 1.0），没有与正则化无关的平台。详见
[`doc/pion_multisource_plan.md`](pion_multisource_plan.md) §6；要突破需要真正独立的算符
（不同 $\gamma$、wall、另一套 smearing），不是 powers-of-$H$ 的重新组合。

## 3. C3：直接面向能量误差的目标

如果目标改成“在给定成本下更准确地提取 $E_0$”，主指标应换成配对能量误差，而不是
“归一化曲线离 1 多近”。

### 3.1 定义

设 anchor 给出 $E_*$（独立、高统计、误差已知），候选 $c$ 的能量估计为 $\hat E_c$：

$$
\Delta_c=\frac{(\hat E_b-E_*)^2-(\hat E_c-E_*)^2}{\tau_E^2},
$$

- $b$ 是基线（identity / tuned Gaussian）；
- $\tau_E>0$ 是预注册的“有实际意义的能量精度”，例如 $0.01$（格点单位）；
- 采用**损失差**而不是风险比，避免分母接近零；
- 同一 anchor draw 供所有候选使用；若 anchor 与验证集共享组态，必须纳入 cross-covariance，
  不能宣称“anchor 方差自动抵消”。

### 3.2 认证条件

1. anchor 独立于候选训练和参考选择（不同组态或独立分析）；
2. 在已知谱的模拟上校准 $\Delta$ 的分布，报告 coverage 与假改善率；
3. 用相同 block 的配对 bootstrap，报告 $\Delta$ 的单侧下界；
4. 若 anchor 有模型偏差，报告多 anchor 模型下的同时下界，冲突则 abstain。

### 3.3 合成数据验证（CPU，已完成）

`tasks/pion_projection/energy_target.py` 实现了配对能量差和一个单侧下界
（均值 $-\,z_{1-\alpha}\,\mathrm{SE}$），并在已知 $E_0$、独立 anchor 的合成数据上验证：

| 场景 | $\sigma_b,\sigma_c$ | bias | $\Delta$ 中位数 | 认证比例 |
| --- | --- | --- | ---: | ---: |
| 候选更好 | 0.02, 0.005 | (0, 0) | $\approx+3.5$ | >0.9 |
| 噪声相同 | 0.01, 0.01 | (0, 0) | $\approx0$ | <0.15 |
| 候选有偏 | 0.01, 0.005 | (0, 0.02) | 负 | <0.1 |

![energy target](../results/pion_projection/score_diagnostics_v2/energy_target_synthetic.png)

**注意**：这里用“均值的单侧正态下界”，不是单次 draw 的分位数——后者对平方误差差
（重尾）会给出永远为负的下界。

### 3.4 现状

**合成验证已完成；真实数据 NOT_RUN**：需要独立 anchor 和新留出数据；当前 60/30 组态不足以支撑。

## 4. 与当前评分的关系

- 现有的 `scoring.py`（S1 证书）已经实现了“配对 log 改善 + Bonferroni 同时下界”的框架，
  C3 可以直接复用它，只要把 risk draws 换成能量误差 draws；
- 在 anchor 与 GEVP 参考就位之前，pion 的正式 `score` 应保持 `null`，只发布诊断。

## 5. 建议的执行顺序

1. 先做 C2 的合成数据验证（CPU，1 天量级）；
2. 再决定是否投入 4× 反演预算做多 source 测量；
3. C3 需要独立 anchor，建议与 C2 同批测量（同一批组态、不同分析）。
