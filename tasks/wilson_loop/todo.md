# wilson_loop: finite-T Creutz 与基态离散静态力 handoff

## 用户已选择的两个独立 estimand

1. **C lane：有限时间 Creutz observable** `chi_k(R,T)`。在 protocol 冻结后，它可作为有限 `T` 的直接观测量报告；不能自动改名为基态精度或改善。
2. **F lane：基态离散静态力** `f0(R+1/2)=U0(R+1)-U0(R)`。只有激发态、有限 `N_t` 热/绕回和混合项的总系统误差有独立可审阅上界时才可认证。

目前仍为 `NOT_READY/UNCERTIFIED`、`GROUND_STATE_FORCE_UNCERTIFIED` 和 `physical_score=null`。不读取 gap、validation、shared holdout；不启动 GPU/QUDA。

## 已完成的解析与源核对

- [零温正谱敏感度报告](../../results/wilson_loop/ground_state_bound_sensitivity_20261123_v1/README.md)：实现 `|chi-f0| <= log(1+Q exp(-Delta_min*T))` 的条件界，并在 `Q=1e-3…1e2`、`Delta_min=0.01…1.0` 格点单位、`T=4…7` 上生成 14,884 行解析网格和四面板图。`Q` 和能隙全是插图输入，不是估计值；这个公式不包含有限 `N_t` 热迹。
- [有限 `N_t` 热/绕回理论审阅](../../results/wilson_loop/finite_nt_thermal_bound_review_20261122/README.md)：从 trace 展开静态对与无源两套 Hilbert sector，保留 pair excited `q`、thermal `h` 和 mixed `x`。如果各项有独立非负 envelope，则先构成 `B_k(R,t)=log(1+q_bound+h_bound+x_bound)`，再把四个 loop 点的 `B` 传播进 `Delta_R Delta_t` 的力/Creutz 系统界。当前没有任何物理 `Q,H,X,Delta` 输入，推导不等于认证。
- 原文编号已复核：有限温热迹和谱分解在 Bala et al. Appendix A 的 Eq. (35)–(36)；零温 Wilson-loop 正谱展开在 Brambilla et al. Eq. (3)。更复杂空间路径/链接 smear 会改谱权重，不改固定 action 下能级位置这一点来自有限温论文对静态介子算符的讨论。来源与适用边界见上述报告文末链接。
- [框架扩展点地图](../../doc/framework_extensibility.md)建议将 C/F 写成两个 versioned estimand contract：共享 loop/block IDs 和 paired draws，但分别设数值门和系统误差门。

![有限T Creutz与基态力的零温激发态敏感度](../../results/wilson_loop/ground_state_bound_sensitivity_20261123_v1/contamination_sensitivity.png)

文字流程图：`W_k(R,t;N_t)` → `q: pair excitations ~ Q exp(-Delta_Q t)` + `h: no-pair thermal ~ H exp(-Delta_0(N_t-t))` + `x: mixed sector` → `C lane 保留有限t的chi`；`F lane 经 log 后做 Delta_R Delta_t` → 加总统计、激发态、热/绕回、混合、finite-a/volume 误差 → 与事前容差比较 → 缺任一独立 bound 时保持 `GROUND_STATE_FORCE_UNCERTIFIED`。

## 解析公式与注意事项

零温正谱下写

```text
W_k(R,T)=A0_k(R) exp[-E0(R)T] [1+rho_k(R,T)]
rho_k(R,T) <= Q_k(R) exp[-Delta_min(R) T]
g_k(R,T)=log[(1+rho_k(R,T))/(1+rho_k(R,T+1))]
chi_k(R,T)=f0(R+1/2)+g_k(R+1,T)-g_k(R,T)
```

当 overlap 系数非负且能隙为正，`0<=g<=log(1+rho)`，可得单 kernel 的条件界。candidate-minus-identity 需要两侧污染界并相加。该界条件是正向、零温的谱和；有限时间窗拟合稳定或 bootstrap 区间很窄都不证明此条件。

有限 `N_t` 下，热迹可写成相对 ground-ground 项的

```text
W ~ exp[-V0(R)t] * [1 + q(R,t) + h(R,N_t-t) + x(R,t,N_t-t)]
```

增大 `t` 会压低 `q`，但缩短 `N_t-t`，可能放大 `h`。若每个污染项有可证的 envelope，定义其和的 log 上界 `B_k(R,t)`；保守的单 kernel 力/Creutz bias 界为参与的四个 `B` 之和。只有 `Q/gap` 的数值不能覆盖热迹和 mixed term，partition function 在差分中约去也不会抹掉 numerator 热项。

## 下一位 agent 的工作顺序

1. **C lane contract：**冻结 primary `R/T/kernel`、有限 `N_t`/边界与空间单位、loop mean 的正值/log 规则、坏点处理、候选族、多重性、配对 block 方案与精度目标。它的结论名称必须保留“finite-T Creutz”。开发数据不得反复用于选择确认点。
2. **F lane contract：**明确 `U0`、`f0` 的 lattice/physical units 和静态源约定；冻结 force finite-difference stencil、目标 `R`/`T`、谱模型/截断、置信度和总系统预算。给 `Q_k(R), Delta_Q(R), H_k(R), Delta_0, X_k(R)` 的独立来源，或提交有完整失败诊断的多态/变分谱方案。
3. 先用解析 toy 参数验证 `q/h/x -> log W -> Delta_R Delta_t` 的符号、R/T 四点索引、界的单位和误差传播；输出公式单元测试、污染面板图及逐项误差表。toy 范围必须标示 illustrative，不能称测得值。
4. 比较可审阅的证据路线：独立 static-source operator basis 的谱/overlap 稳定性；或 matched `N_t`（相同 action、`a_t`、空间体积、`R`、kernel）的热污染差异。任一路径均须冻结 rank/截断、重采样和失败/abstain 规则；短单 `N_t` 数据不可识别每个 sector 的上界。
5. 只有方案通过审阅并获数据/GPU 授权后才测量。报告 C/F 两条 lane 各自的 planned/valid/failed/abstained、paired intervals、统计误差、激发态界、热界、mixed 界、格距/体积误差及其图示。禁止把 C lane 数值重命名为 F lane。

## 停止规则

若 `R/T/kernel`、单位、失败和多重性规则未冻结，不做确认性比较；若 F lane 的任一独立谱/热/混合界无法以事前容差认证，则保留 `GROUND_STATE_FORCE_UNCERTIFIED`。有限-T 精度、窗口稳定、单一能隙假设或 narrow bootstrap 都不能代替缺失系统界。
