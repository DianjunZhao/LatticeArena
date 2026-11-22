# 候选证书的 **χ² subgate** benchmark（C2 修正版）

生成：`python -m tasks.pion_projection.certificate_calibration`；数值：`certificate_calibration.json`。

**负结果/INCONCLUSIVE（不是族错误率受控）**：0/8 的双侧 95% CP 区间是 [0, 0.36942]，
单侧上界 0.31234；每 cell 仅 8 个 dataset，本 benchmark 只验证 5% 的 χ² 子门。
J=2/K=2 的 null 0/6、better 0/6 同样不能证明“族错误率已控制”。

## 名称与范围（重要）

本 benchmark 的 gate **只是正式 gate 的 χ² 子门**：development 上单 cosh 拟合的
$p=\chi^2_{\rm sf}(\text{cost},8)\ge0.05$。正式 gate 还包含窗口配对漂移、反射、相对误差等；
本文件**不**声称是完整端到端 gate 校准。证书链本身（joint draws → certificate）是真实的。

## 修正（相对上一版）

- 生成数据先 `fold`（时间折叠），与生产/evaluate 的预处理一致（C1）；
- 每个 outer draw 在 **development 训练块**上计算候选 `late_metric` 并冻结，
  validation risk 使用该 `late_inverse`（C3，不再由 validation replica 重估 metric）；
- 删除未使用的 `contam_candidate` 参数；场景用通道污染数组定义（C6）；
- wrong-state 的 baseline/candidate 使用**不同权重通道**（真实 risk 差，point ratio 0.49–1.68），
  不再是同一数组（C5）；
- 记录无条件与条件比率分开，并给出 MC 区间（下）。

## 结果（每 cell 8 个独立 dataset；60 outer / 24 inner draws）

| 场景 | blocks | abstain | valid | certified | 无条件率 | 条件率 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| no_improvement | 6 | 0 | 8 | 1 | 0.125 | 0.125 |
| no_improvement | 12 | 0 | 8 | 0 | 0.0 | 0.0 |
| no_improvement | 24 | 0 | 8 | 1 | 0.125 | 0.125 |
| known_improvement | 6/12/24 | 1 | 7 | 7 | 0.875 | 1.0 |
| misspecified_reference | 6 | 6 | 2 | 0 | 0.0 | 0.0 |
| misspecified_reference | 12/24 | 8 / 8 | 0 / 0 | 0 | 0.0 | — |
| J=2,K=2 family | 24 | 2 | 6 | null 0、better 0 | 0.0 / 0.0 | — |
| wrong excited state | 24 | 0 | 8 gate 通过 | 0 | — | — |

**MC 说明**：

- 8 个 dataset 的 0/8 不能当作“错误率受控”：双侧 95% Clopper–Pearson 区间为
  **[0, 0.36942]**，单侧 95% 上界 **0.31234**；1/8 的区间约 [0.003, 0.65]。
- wrong-state 的 8/8 gate 通过、拟合质量 1.50，独立质量 guard 8/8 标出；
  候选 point ratio 0.49–1.68，说明候选确实不同，但 0 个被认证——**gate 本身无法区分 E1/E0**，
  正确行为是拒绝（guard）而不是依赖证书。
- J=2/K=2：两个模型各自过 gate（single p≈0.14、twostate p≈0.067 但 mass2 顶到上界 3.0，
  `at_boundary=True` → 该 dataset 判 **不接受 twostate**），2/8 abstain、valid 6；
  null 0/6、better 0/6。功效为 0 是小样本 + K=2 + boundary 拒绝的结果，**INCONCLUSIVE**，
  不能读作“族错误率已受控”或“证书无效”。

## 验收状态

- 预处理/gate/risk 路径与生产**逐项一致**的范围：fold→blocks、ReferenceFit 窗口、冻结 late_metric、
  draw 身份与证书 spec；剩余差异是 gate 只含 χ² 子门，已在标题与上表标明；
- 条件/无条件率分列；MC 目标：8–20 dataset smoke，允许 INCONCLUSIVE；
- N_null=50 时最小 p=1/51，不能检验 1% 阈值——本文件只验证 5% 子门，未声称 1%。

## 未做

- 完整正式 gate（窗口漂移/反射/相对误差）纳入同一 benchmark；
- 大规模 MC（>100 dataset/cell）；
- J/K 更大族与真实数据。
