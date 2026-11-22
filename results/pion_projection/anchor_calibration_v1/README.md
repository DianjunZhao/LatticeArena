# Anchor 校准与三种区间语义（C3 修正版）

生成：`python -m tasks.pion_projection.anchor_calibration`；数值：`anchor_calibration.json`。

## 三种估计量（不再混淆）

| 估计量 | 含义 | 宽度（n=200） |
| --- | --- | ---: |
| naive | 把 bootstrap draws 当独立样本，`2·1.96·sd/√B` | 1.49 |
| **paired（单 ensemble）** | 同一 dataset 的配对 block 索引 + 共同 anchor draw；差值分位区间 | **20.64** |
| independent-repeat | 30 个独立 dataset 的 Δ 均值 ± 1.96·SE | 0.14 ± 0.49 |

- naive 宽度随 B 缩小，是**反保守**的负例；
- paired 是**单 ensemble 的合法区间**，不除以 √B；
- independent-repeat 估计的是“多次独立实验的期望风险差”，与单 ensemble 抽样区间是**不同 estimand**。

## 固定数据 Nboot 扫描（C10）

同一 raw data、同一 anchor 输入，只改 bootstrap 预算：

| B | naive 宽度 | paired 宽度 |
| ---: | ---: | ---: |
| 50 | 1.240 | 7.210 |
| 200 | 0.741 | 9.845 |
| 800 | 0.347 | **9.960** |

naive 持续缩小；paired 收敛到约 9.96——**增加 Nboot 只收敛 MC 近似，不把物理区间任意缩小**。

## 共享配置相关（C9）

`cfg_shared=0.5` 的 cell：naive 1.48、paired 20.59、independent 0.074±0.49。
共同配置偏移在配对差中抵消，但单 ensemble 区间仍由块间变化主导。

## 旧 cell 结果

- improvement：anchor σ=0 时 naive 0.567、dataset 认证 True；σ=0.005/0.01/0.02 时 naive 0.43/0.40/0.33、dataset False；
- null：naive 0.27–0.50（反保守），dataset 列以 5% 水平控制；
- bias 0.01/0.02/0.05 的 naive 0.23/0.40/0.63。

## 语义与限制

- 单 ensemble paired 区间已实现；外层 datasets 只用于校准该区间；
- anchor 中心用 oracle 真值 `e0=0.80` + 噪声，不是实际 anchor 观测；内层抽样 hierarchy 已记录；
- 小样本（30 dataset）导致 independent 列 INCONCLUSIVE 可接受。
