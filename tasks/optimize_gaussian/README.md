# optimize_gaussian: learned gauge-invariant smear

$p=0$ pion sink：把候选从固定的 $H^n$ 多项式换成**学出来的**逐点 hopping 系数。

## 模型

在时间片内定义一步协变跳跃的修正算子，叠在一个多步高斯基座上：

$$
K = C_{\mathrm{hop}}(a)\,G^{m},\qquad G = I + a_0\,\mathrm{hop},\qquad a_0=\frac{\alpha}{1+6\alpha}
$$

$$
C_{\mathrm{hop}}(a) = I + \sum_{\mu}\Big[\,a_\mu(x)\,T_\mu + b_\mu(x)\,T_\mu^{\dagger}\,\Big],
\qquad (T_\mu q)(x)=U_\mu(x)\,q(x+\mu)
$$

厄米条件（没有它关联函数会出现虚部，v1 的 `candidate` 会直接拒绝）：

$$
b_\mu(x) = a_\mu(x-\mu)
$$

逐点系数由一个随机特征层给出：

$$
a_\mu(x)=\sum_{h} v_{\mu h}\,\phi_h(x),\qquad
\phi_h(x)=\mathrm{ReLU}\!\left(W_h\cdot f(x)\right),\qquad
f_i(x)=1-\tfrac13\,\mathrm{ReTr}\,P_i(x)\ \ge 0
$$

其中 $P_i$ 是三个空间平面的 plaquette。$f\ge 0$、$\phi\ge 0$、$v_{\mu h}\in[0,v_{\max}]$，于是

$$
a_\mu(x)\ \ge\ 0 .
$$

## 训练目标

用 pion 的完整 risk（bootstrap 方差项 + 偏离项），而不是只拟合形状：

$$
\mathrm{risk}(\theta)=\frac{1}{|W|}\sum_{t\in W}
\Big[\mathrm{Var}_{\mathrm{boot}}\big(q_\theta(t)\big)+\big(q_\theta(t)-1\big)^2\Big],
\qquad
q_\theta(t)=\frac{\bar C_\theta(t)}{A_\theta f_0(t)},
$$

$$
f_0(t)=e^{-m_0 t}+e^{-m_0(16-t)},\qquad m_0=1.0861669 .
$$

**为什么能高效训练**：$C_\theta(t)$ 对 $a$ 是线性的，因此对 $v$ 也是线性的。对每个基函数
（identity、3 个常数方向项、$3H$ 个特征项）各做一次 hop，得到响应 $D_p(t)$，任意 $v$ 的
关联函数就是

$$
C_\theta(t)=C_0(t)+\sum_p v_p D_p(t).
$$

训练因此退化为预计算基上的 Powell 搜索，不需要反传。

## v3：两个基座 + 非负约束 + 完整 risk

超参数只在 **dev-val（20–29）** 上选，测试集（70–99，30 组态）只看一次。

| 基座 | $\lambda_2=0$ | $10^{-3}$ | $10^{-2}$ |
| --- | ---: | ---: | ---: |
| $G^8$ | 0.01629 | 0.01640 | 0.01731 |
| $G^{32}$ | **0.01525** | 0.01550 | 0.01554 |

选中 $G^{32}$、$\lambda_2=0$。测试集：

$$
\mathrm{risk}_{\text{base}}=0.02973,\qquad
\mathrm{risk}_{\text{learned}}=0.03109,\qquad
\frac{\mathrm{risk}_{\text{base}}}{\mathrm{risk}_{\text{learned}}}=0.956 .
$$

**结论：在严格非负约束下，学到的修正没有改善留出集（0.956×，反而略差）。**

![risk](../../results/optimize_gaussian/v3/fig_risk.png)

![shape](../../results/optimize_gaussian/v3/fig_q.png)

![coeff](../../results/optimize_gaussian/v3/fig_coeff.png)

第三张图是学到的 $a_x(x,y=8,z)$ 在 $t=0$、组态 70 上的分布：系数非负（$4.5\times10^{-5}$ 到 1.47），
但只在一部分格点上激活——修正表现为稀疏的局域跳跃，而不是均匀的额外平滑。

## 关键发现：真正有用的是**带符号**的修正

同一套流程在去掉非负约束（$\phi=\tanh(W f)$、$v$ 可负）时，测试集从 0.02973 降到 0.02707，
即 **1.10×** 的改善；但那时 $a$ 会低到 $-1.5$，违反非负约束（图里直接能看到）。

这与第一个任务完全一致：pion 的最优核是带符号的多项式，

$$
u=[-0.431,\,0.068,\,0.274,\,0.424,\,0.437,\,0.278,\,-0.049],
$$

负的局域项负责抵消短距离贡献。**非负约束把这个自由度拿掉了，增益也就没了。**

## 历史（v1 / v2）

- **v1**（只拟合形状，10 组态）：训练损失到 $10^{-24}$，但留出损失在 0.05 / 0.34 / 0.65 之间乱跳——
  线性基可以把 $C(t)$ 精确拼成参考的 $\cosh$ 形状，目标本身可被 game。
- **v2**（完整 risk + 单步基座 + 非负）：dev-val 0.0089，测试 0.0195 vs 基座 0.0384（**1.97×**），
  但那只用 10 个测试组态、block=2，和 v3 不可直接比。

## 限制与下一步

- dev-val 只有 10 个组态（5 个 block），选出来的超参数不稳定（dev-val 0.0152 与测试 0.0311 差 2 倍）；
- 测试用 block=2 忽略了自相关；绝对 risk 不能和 pion run（60/30、block=5）直接比；
- 隐藏层 $W$ 固定、只训读出（随机特征），不是完整反传；
- 修正只有一步，基座 $G^{32}$ 承担半径。

**v4 计划**：带符号但有界的参数化（$|a|\le a_{\max}$ 加正则，而不是硬性 $a\ge0$）；dev-val 扩到 30 组态；
基座换 $H^{32}$ 或 SLSQP 混合核；最后接 `candidate` 冻结流程。

## 运行

```bash
# kunshan DCU 节点（需要 PyQUDA + cupy + pion 传播子缓存）
sbatch pilot/optgauss.sbatch                      # 默认 → results/optimize_gaussian/v3
python -m tasks.optimize_gaussian.plots <out_dir> # 出三张图
```

单次 v3 约 20 分钟：2 个基座 × 30 个组态 × 16 时间片 × (m 步基座 + 28 个基响应)。
