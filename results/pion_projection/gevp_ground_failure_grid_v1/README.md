# GEVP ground-mode 有限网格（B）

生成：`python -m tasks.pion_projection.gevp_grid`；数值：`gevp_ground_failure_grid.json`。

## 修正

- `_eigvals` 的 `rank` 现在必须是整数且 0 ≤ rank ≤ dim；rank=0 返回空谱；
  非正/未分辨的 metric 本征值不会被开方（返回空谱，由上层计 failure）；
- `cutoff` 参数贯通到 `bootstrap_gevp`（`rtol`）；
- rank 选择只在**已分辨**的本征值中进行，数量不足时返回空谱。

## 反例

- `_eigvals(I, diag(-1,1), rank=2)` → `[]`（旧实现返回 `[NaN, NaN]` 并触发 sqrt warning）；
- `rank=0` → `[]`（旧实现反而选中全部）；
- `rank=3` / `rank=-1` → 明确 `ValueError`。

## 网格（2×2 矩阵、rank=2）

noise={0.01,0.05} × gap={0.1,0.5} × t0={1,2} × cutoff={1e-8,1e-5}；每 cell 20 dataset、
60 bootstrap draws；平台时间 t0+1..t0+3。

| 指标 | 观察 |
| --- | --- |
| 失败数 | 全部 cell 为 0/20（网格内没有不可识别 cell） |
| bias | 0.02–0.04（随 gap 增大；短平台与激发态污染） |
| coverage | **0.0**（bootstrap 区间只反映 replica 散布，漏掉系统 bias） |

读数：该网格给出的是**偏差 vs 区间**的负结果——bootstrap SE 不能覆盖激发态污染导致的
系统偏差；这不是“GEVP 已认证”，而是“区间需要系统误差项”。20 dataset 的 MC 误差约 ±0.05。

## 语义

- 所有 cell 的 `failures=0` 只说明“没有缺失/非法谱”，不是物理基态认证；
- cutoff 1e-8/1e-5 在本网格内不改变失败计数；
- 多态 tracking、rank>2、更大统计量延期。
