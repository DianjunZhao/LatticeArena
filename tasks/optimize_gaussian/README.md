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
\phi_h(x)=\tanh\!\left(W_h\cdot f(x)\right),\qquad
f_i(x)=1-\tfrac13\,\mathrm{ReTr}\,P_i(x)\ \ge 0
$$

其中 $P_i$ 是三个空间平面的 plaquette；$W$ 固定随机，$v$ 训练。

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

## v4（当前版本）：带符号 + 有界 + 更大的 dev-val

- 参数：$v_{\mu h}\in[-3,3]$（**带符号**），L2 系数 $\lambda_2\in\{0,10^{-3},10^{-2},10^{-1}\}$；
- 基座：$G^{32}$（v3 里胜出的基座）；
- 选择集：dev-val 扩到 **30 组态（20–49）**；测试集 30 组态（70–99）只看一次。

| $\lambda_2$ | 0 | $10^{-3}$ | $10^{-2}$ | $10^{-1}$ |
| --- | ---: | ---: | ---: | ---: |
| dev-val risk | 0.011906 | 0.010256 | **0.004991** | 0.013380 |
| $\max\|v\|$ | 3.00 | 2.95 | 1.48 | 0.87 |

选中 $\lambda_2=10^{-2}$。测试集：

$$
\mathrm{risk}_{\text{base}}=0.029732,\qquad
\mathrm{risk}_{\text{learned}}=0.022552,\qquad
\frac{\mathrm{risk}_{\text{base}}}{\mathrm{risk}_{\text{learned}}}=1.318 .
$$

![risk](../../results/optimize_gaussian/v4/fig_risk.png)

![shape](../../results/optimize_gaussian/v4/fig_q.png)

![coeff](../../results/optimize_gaussian/v4/fig_coeff.png)

## 怎么读这个 1.32×

**数字上是真的**：30 个留出组态、dev-val 与测试同向，learned 比 $G^{32}$ 基座好 1.32 倍；
$\lambda_2=10^{-2}$ 把 $\max|v|$ 压到 1.48，不再撞边界。

**但系数图要诚实解读**：$a_x(x,y=8,z)$ 几乎是一块**均匀的负值**（$-1.5$ 到 $-1.05$，起伏只有 $\pm0.2$），
即模型主要学到的是一次**整体的负 hop**

$$
a_\mu(x)\ \approx\ -1.3 ,
$$

它相当于在 $G^{32}$ 之后做一步“反涂抹”（sharpening）。这解释了增益的来源——$G^{32}$ 对这个
$m_0$ 和这套统计量来说**过涂抹**了，最划算的修正就是把涂抹拉回来一点；逐点自适应只占很小一部分。

换句话说：**1.32× 是“学到该少涂抹一点”，而不是“学到了一个丰富的空间结构”。** 这是有价值的
物理信息（基座选择错了），但不是“learned kernel 比多项式更强”的证据。

## 版本对比

| 版本 | 参数 | 基座 | 约束 | 测试集 | 结果 |
| --- | --- | --- | --- | --- | --- |
| v1 | 24 | 单步 | 无 | 10 组态 | 训练到 $10^{-24}$，留出 0.05/0.34/0.65，退化 |
| v2 | 24 | $G^8$ | $v\ge0$ | 10 组态 | 0.0195 vs 0.0384（1.97×，但测试集小） |
| v3 | 24 | $G^8/G^{32}$ | $v\ge0$（ReLU） | 30 组态 | 0.0311 vs 0.0297（**0.956×**） |
| v3′ | 24 | $G^{32}$ | 带符号（tanh） | 10 组态 | 0.0271 vs 0.0297（1.10×） |
| **v4** | 24 | $G^{32}$ | **带符号 + 有界** | 30 组态 | **0.02255 vs 0.02973（1.32×）** |

v3 与 v4 的对比说明：**非负约束是错的**，带符号才能拿到增益；但 v4 的系数图又说明，
增益主要来自“整体负 hop”，不是空间自适应。

## 限制与下一步

- 测试 block=2，忽略自相关；绝对 risk 不能和 pion run（60/30、block=5）直接比。
- 随机特征层固定、只训读出；不是完整反传。
- **均匀模式占主导**：下一步应把 $a$ 的均值扣掉（或对均值加惩罚），强制学习真正的空间起伏，
  再看增益是否还在——这直接检验“site-adaptive”是否有价值。
- 基座应换回 $G^8$ 或更小的涂抹，让修正不必承担“反涂抹”的角色。

## 运行

```bash
# kunshan DCU 节点（需要 PyQUDA + cupy + pion 传播子缓存）
sbatch pilot/optgauss.sbatch                                   # 协议里的 output 目录
python -m tasks.optimize_gaussian.plots results/optimize_gaussian/v4
```

单次 v4 约 20 分钟：30 个训练 + 30 个 dev-val 组态 × 16 时间片 × (32 步基座 + 28 个基响应)。
