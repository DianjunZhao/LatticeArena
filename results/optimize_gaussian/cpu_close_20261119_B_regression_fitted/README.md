# Fit-state synthetic regression（包 B）

生成：`python -m tasks.optimize_gaussian.estimator_regression`；原始数据：`regression.json`；
诊断图：`regression.png`。

## 设计

60 个独立 synthetic datasets，每个有 80 configurations、block length 5、16 blocks；随机分为
8 个训练块与 8 个验证块。每个数据集使用 200 个 bootstrap draws。训练分支从训练块拟合幅度并冻结，
验证分支在验证块上按同一公式重估幅度；两者的 point 与 replica 都使用对应的同一规则。

| 幅度规则 | point − replica 均值 | 平均逐时间覆盖率 | 四个时间点全覆盖的数据集数 |
| --- | ---: | ---: | ---: |
| training-frozen | $4.06\times10^{-6}\pm6.87\times10^{-5}$ | 1.000 | 60/60，CP 95% 区间 [0.940, 1.000] |
| validation-refit | $-1.99\times10^{-5}\pm2.22\times10^{-5}$ | 0.971 | 53/60，CP 95% 区间 [0.774, 0.952] |

覆盖率不确定度以 **dataset** 为独立单位；四个时间点在一个 dataset 内相关，CP 区间的二项事件定义为
“四个 score-window 时间点全部覆盖”。training-frozen 的验证区间以训练幅度为条件，**不传播训练幅度本身的
抽样不确定度**。因此结果只支持 point/replica 实现一致性与该 toy 条件下的覆盖诊断，不证明真实参考模型
正确或无条件 coverage。

![训练幅度冻结与验证幅度重估的回归诊断](regression.png)

## 复现与限制

- seed：`20261123`；输出目录已存在时程序拒绝覆盖。
- 单一质量、幅度和 1% 独立噪声；尚未覆盖时间相关噪声、参考失配和 block-length 敏感性。
- GPU 上真实 W 训练与新盲测仍未运行。
