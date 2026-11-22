# P3 第一步：谱类 vs 非对易类的跨样本 teacher 实验

生成：`python -m tasks.optimize_gaussian.p3_teacher`；数值：`p3_teacher.json`。
小格点 `(3,3,3)`（81 维 site-colour 空间）、真实 diffusion kernel 的 $H$、$Q=(VH+HV)/2$。

teacher：$T=I+0.3H^2+0.1H^4+\epsilon Q$（$\epsilon=0$ 时完全在七幂基的谱类内）。
拟合：全局系数 $c_k$（谱类）或 $c_k,c_Q$（增广类），在 48 个训练 probe 上最小二乘，
在 48 个**独立 test probe** 上评估相对误差。

| $\epsilon$ | 谱类 test 误差 | 增广类 test 误差 | 有效秩 |
| ---: | ---: | ---: | ---: |
| 0 | $8.5\times10^{-16}$ | $6.3\times10^{-16}$ | 7 |
| 0.02 | $2.62\times10^{-3}$ | $9.1\times10^{-16}$ | 7 |
| 0.05 | $6.48\times10^{-3}$ | $7.8\times10^{-16}$ | 7 |
| 0.1 | $1.27\times10^{-2}$ | $6.7\times10^{-16}$ | 7 |

其他检查：$H$/$Q$ Hermitian 残差 0，$[H,Q]$ 范数 0.399。

读数：

- $\epsilon=0$ 谱类精确恢复（$<10^{-15}$）；
- $\epsilon>0$ 时谱类误差随 $\epsilon$ 增长，增广类保持机器精度——**新类在独立 probe 上确实降低了误差**；
- 有效秩仍是 7：新类没有“凭空增加有效秩”，它提供的是**不同方向**。

状态：**PASS**（$\epsilon=0$ 恢复、$\epsilon=0.1$ 谱类误差 $>10^{-3}$、增广类 $<10^{-15}$）。
范围：CPU teacher 实验；P3 第二步的 GPU class×optimizer 实验 **NOT_RUN**。
