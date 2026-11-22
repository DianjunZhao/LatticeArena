# C 包条件数、KKT 与多起点预算诊断

生成方式：`python -m tasks.optimize_gaussian.cpu_convergence_diagnostic`。原始逐 seed、逐起点、逐预算结果在
`convergence_diagnostic.json`；代码摘要写在 JSON 中。本报告复用 `p3_crosslink_fair` 的三组 seed、独立 train/test
links、匹配 probes、$H^0,\ldots,H^7$ 与增广 $BHB,\{BHB,H\}/2$ 特征、实系数 $[-5,5]$ 和相同 oracle。

## 结果

实数化 design 在三个 seeds 中均满列秩：A 类 8/8，B 类 10/10。列 RMS 缩放后 condition number 为
$5.52\times10^5$ 至 $6.45\times10^5$；rank 满秩不代表问题数值良态，特征方向仍强相关。条件数不随 $\epsilon$
变化，因为输入特征矩阵不变，只有目标 $Q$ 改变。

最大预算是每个 start 400 次目标调用、5 个共同起点，因此总上限 2000 次。$\epsilon=0.1$、三个 seed 的均值：

| 类别 / 求解器 | train relative objective | projected-gradient KKT norm | 独立 link test error | 实际目标调用均值 |
| --- | ---: | ---: | ---: | ---: |
| A spectral / SLSQP | $1.47\times10^{-7}$ | $1.77\times10^{-9}$ | $3.83\times10^{-4}$ | 382 |
| A spectral / Powell | $6.73\times10^{-3}$ | $8.93\times10^{-3}$ | $8.17\times10^{-2}$ | 2000 |
| B nested / SLSQP | $1.27\times10^{-10}$ | $2.84\times10^{-9}$ | $6.72\times10^{-6}$ | 506 |
| B nested / Powell | $1.19\times10^{-2}$ | $1.68\times10^{-2}$ | $1.09\times10^{-1}$ | 2000 |

在最大预算的 24 个 seed × class × epsilon 条件中，SLSQP 的全部 5 个起点均在预算耗尽前返回成功；Powell 的
120/120 个起点都用完预算，且没有预算前失败。预算中止是未收敛记录，不能误报为 SciPy 的算法失败。图中曲线按
三个 seed 取均值并画标准误；error/test 反映此合成有限 probe 设计，不是物理预测。

![列缩放条件数和实化 design rank](fig_condition_number_rank.png)

![固定目标评估预算下的 train objective、KKT 残差与独立 test error](fig_budget_convergence.png)

## 结论边界与下一步

- 该构造性二次问题的 bounded least-squares oracle 是相同有限 design 上的凸优化参考；SLSQP 多起点在此问题上比
  Powell 更有效。该结论不等于所有初值、求解器或物理 smearing 问题上 SLSQP 都更好。
- 三 seeds 只用于发现尺度/收敛问题，不能形成发表级误差或跨 ensemble 泛化结论。
- 此结果不测试 learned smear 是否优于 SLSQP。真实学习可能通过初始化、有限预算搜索策略、跨 gauge ensemble 的参数迁移或
  总 walltime 获益；必须与同预算多起点 SLSQP、Gaussian base、强 spectral/Chebyshev 基线做 held-out 配对比较。
- 若 learned 参数只充当初值，应计入训练/setup 成本并在固定 objective-call 与 walltime 预算下比较；若同一凸二次目标已有
  全局 oracle，则不应把学习声称成更低的全局最优值。
- 真实 gauge $W$ 训练、GPU receipts、blind test 和额外 independent links 均未运行，仍为 `NOT_RUN`。
