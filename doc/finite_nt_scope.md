# 有限 Nt 的静态源谱与 window_z 口径

## 1. 一般静态源 sector

固定空间位置的静态源、零动量、周期时间、费米子时间反周期时，Wilson 圈（或静态源关联）在
有限 Nt 的谱表示为

$$
W(R,T)=\sum_n c_n(R)\left(e^{-E_n(R)T}+e^{-E_n(R)(N_t-T)}\right),
$$

其中 $E_n(R)$ 是静态源–反源 sector 的能级，$c_n$ 是重叠系数（可正可负）。
正反两项的系数**相同**是时间反演/周期性的结果；但“等幅”并不意味着两项在数值上总是同量级：

- 当 $T\ll N_t/2$ 时，$e^{-E_n(N_t-T)}\ll e^{-E_nT}$，零温（只保留正向项）近似成立；
- 当 $T\approx N_t/2$ 时，两项同量级，零温近似**不成立**；
- 等幅正反指数 $\cosh(E(N_t/2-T))$ 只是 $c_n$ 相等、且只保留一个能级时的**特例**；
  不能把它当作一般 Wilson 圈的有限 Nt 谱，也不能反过来断言一般 Wilson 圈必含等幅回绕项。

本仓库的 `spectral_physical.py` 反例使用**零温形式** $W=c_0e^{-E_0T}+c_1e^{-E_1T}$；
它证明的是“短窗口共同偏差可以骗过 spread gate”，不是有限 Nt 谱的完整实现。

## 2. window_z 的口径

旧写法把两个窗口的 SE 平方和开方当作分母（$ \sqrt{se_i^2+se_1^2}$）。同一组 bootstrap
draws 下两个窗口的 V 是**配对**的，正确口径是差值的 SE：

$$
z_i=\frac{V_i-V_{\rm nom}}{\operatorname{std}_b\left(V_i^{(b)}-V_{\rm nom}^{(b)}\right)}.
$$

`spectral_physical.py` 现在同时输出：

- `window_paired_z`：配对差 SE（正确口径）；
- `window_naive_z`：旧的独立 SE 合成（仅作对照）。

两者都不进入 gate：`window_z` 仍是**诊断量**，不是已认证的物理质量。当前 gate 只用
spread/V 与 reference 拟合，因此“gate PASS”不能升级为 E0 准确度（见
[`doc/wilson_spectral_quality.md`](wilson_spectral_quality.md)）。

## 3. 现行结果（`spectral_physical_v1/`）

| $c_1$ | bias/SE | spread/V | max\|paired z\| | max\|naive z\| |
| ---: | ---: | ---: | ---: | ---: |
| 0.05 | 3.1 | 0.0004 | 1.02 | 1.12 |
| 0.1 | 5.6 | 0.0014 | 3.01 | 2.49 |
| 0.2 | 13.1 | 0.0019 | 5.43 | 5.49 |
| 0.5 | 32.5 | 0.0058 | 16.65 | 14.94 |

配对口径在 $c_1=0.1$ 时刚好越过 3（诊断线），而 spread gate 全部通过——结论不变：
**spread gate 对共同偏差盲，window_z 只是更敏感的诊断，不是认证。**
