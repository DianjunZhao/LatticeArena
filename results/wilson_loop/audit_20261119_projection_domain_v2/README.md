# P0b determinant-phase controlled projection scan

生成：`python -m tasks.wilson_loop.projection_domain`；数值在 `projection_domain.json`，图在 `fig_projection_phase_branch.png`。这是 CPU 有限网格证据。

## 输入与范围

- 126 cells：6 个奇异值谱 × 3 个尺度（0.001, 1, 1000）× 7 个受控 determinant phases。
- 奇异值谱含单位矩阵、条件数 100/1,000/10,000/100,000 和奇异矩阵；支持策略为正奇异值且条件数 ≤ 1000。
- 左右奇异向量均规范为 SU(3)，所以实际 `arg det(M)` 与请求相位一致；扫描 `±π` 和两侧 `±(π−ε)`，`ε=1e-06`。
- 测试尺度仅覆盖所列三点；不能外推到任意浮点动态范围。

## 结果

| 诊断 | 结果 |
| --- | ---: |
| 支持域 cell 通过 | 63/63 |
| 域外策略拒绝 | 63/63 |
| 最大输入相位控制误差 | 8.201e-12 |
| 最大 unitary 残差（支持域） | 9.250e-11 |
| 最大 $|\det P(M)-1|$（支持域） | 9.612e-11 |
| 切口外最大双侧 SU(3) 协变残差 | 9.867e-11 |
| 精确切口端点协变超容差格数 | 7 |

![受控 determinant phase 的 SU(3) 中心分支](fig_projection_phase_branch.png)

## 正确解释

极分解的 unitary factor 保留 `arg det(M)`；最终 SU(3) 投影乘以 `exp(-i arg det(Q)/3)`，把 determinant 调到 1。因此
修正前后 determinant phase 的差是预期变换，不是误差。principal cube root 在 `±π` 两侧会发生中心相位跳变；本图显示该
有限边界行为，不声称切口处连续。精确端点的协变 outlier 单独报告；它们不能与切口外的协变通过混为一谈。域外有些
矩阵数值上仍可能可投影，但按预声明条件数策略拒绝。
