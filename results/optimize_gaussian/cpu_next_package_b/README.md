# 统一估计量（optimize 包 B）

生成：`python -m tasks.optimize_gaussian.unified`；数值：`unified.json`。
当前 fold 诊断图：`fig_folds_frozen.png` 与 `fig_folds_reselected.png`。

## 结果

三折 outer-training 内重新选择 power 后，三折都选 $H^{32}$。tuned/SLSQP 比值为
1.719、2.014、0.810；这是三折的描述性结果，不是独立样本标准误。reference gate 三折均失败，
因此只能作为条件诊断，也没有 inner CV，不能称为 nested CV。

每折保存 train/test block IDs、weights 与 masses hash、scale、search 预算、nfev、可行性、
reference 来源与失败状态。冻结历史权重图和 fold 内重选图分开保存，禁止混为一个估计量。

## 固定幅度回归

- `regression/` 是 **5 dataset × 20 draws 的 smoke**，不能沿用旧 README 中 60×200 的数字。
- 独立的 60×200 拟合幅度回归现存于
  [`cpu_close_20261119_B_regression_fitted`](../cpu_close_20261119_B_regression_fitted/README.md)，
  包含图、原始 JSON、训练幅度冻结与验证幅度重估两种估计量。

## 覆盖事故

包 B 开发期间同名输出曾覆盖 `unified_v1/`。旧 fold 文件没有纳入 git，当前仓库无法恢复原文件；
旧点值只保留作历史说明，不能再赋予新身份。后续生成使用独立目录，存在结果时拒绝覆盖。
