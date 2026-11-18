# 项目状态（2026-11-18，新开工单后）

三个任务的最终状态。细节见 [`doc/final_report.md`](doc/final_report.md)、
[`doc/todo_coverage.md`](doc/todo_coverage.md) 和各自的 task README。

## 一句话

| task | 状态 | 关键数字 |
| --- | --- | --- |
| `wilson_loop` | **修复后显著改善；P0–P3/F0–F2 完成** | v3 留出 263/233/222，配对区间不含 1；投影混尺度修复；v2 异常已解释（点值 1.07–1.18 vs 中位数 3.0–3.4）；F4 toy 通过、生产 ΔH ⛔ |
| `optimize_gaussian` | **与强基线未检出差异；P0 完成、P2/P3 CPU 完成** | v9 2.12×；候选 0.007721 vs SLSQP 0.007703（0.998 [0.78,1.18]）；BCB 闭环 <1e-10；七幂 teacher 盲区 0.0127；GPU 2×2 ⛔ |
| `pion_projection` | **无可信分数；P0/P1/§6.1 完成** | 参考仍失败（χ²=90.6/8，$m_0=1.0771$）；GEVP 已知谱覆盖率 0.95；校准 full 0.025 / fixed 0.095；nested CV 427±89；能量实验单 cosh 覆盖率 0 |

## 各任务要点

### wilson_loop

- 双边极分解 + $\alpha/4$：v3（200 组态、80 留出、16 blocks）配对区间不含 1；
- P0：逐矩阵 Newton–Schulz + 收敛检查（混尺度 batch 1e-16、rank-2 拒绝）；
- P1：generation、resume 前缀、gauge 几何、`trust_status`（v3 归档判 archived_diagnostic）；
- P2：v2 点值 1.07–1.18 vs 嵌套中位数 3.0–3.4；6 blocks 的唯一 block 分布、jackknife 0.49–4.53；
- P3：合成“平但错”反例（偏差 170σ、risk $2.7\times10^{-7}$、gate 通过）；
- F4：manifest 审计（seed 20261109、$\tau_{\rm int}=0.512$）；toy 可逆性 $10^{-10}$、$\Delta H$ 二阶；生产 ΔH/接受率 ⛔。

### optimize_gaussian

- P0.1：完整 BCB 闭环（非立方格点、多 theta、$f\ne g$，<1e-10）；
- P0.2：basis key 含依赖 hash + gauge/propagator 内容摘要；
- P0.3：audit 按 manifest 分类（v9 = current_operator_diagnostic）；
- P1：统一入口复算 local/SLSQP 与归档逐位一致；3 折 fold-local 比率 216±92；
- P2：七幂基对非对易 teacher 误差 0.01268 > 谱外 0.01239，增广基 $1.8\times10^{-16}$；
- P3 CPU：$\epsilon=0$ 谱类恢复（$8.5\times10^{-16}$），$\epsilon=0.1$ 谱类 0.0127 vs 增广 $6.7\times10^{-16}$；
- GPU 2×2/消融/新盲测：⛔（[`doc/optimize_p3_design.md`](doc/optimize_p3_design.md)）。

### pion_projection

- P0.1：Gram 与标准 source–sink 矩阵差约 30%，$C$ 自身 anti-Hermitian 30%；
- P0.2/P0.3：去重→block bootstrap→秩截断→平台；已知谱覆盖率 0.95；
- P0.4/P0.5：评分契约 + 强制 schema（未批准模型/广播/负 risk 均拒绝）；
- P0.6：joint draws（200×64），参考 gate 失败 → 强制 abstain；
- P1.1/P1.2：full 0.025、fixed 0.095、6/12 blocks 0.235/0.085；
- P1.3：120 dev 秩满但条件数 $10^6$–$10^8$，$m_0$ 随窗口 1.44→1.08；
- P1.4：5 折 nested CV，local/SLSQP 209–750；
- §6.1：单 cosh 覆盖率 0、两态 0.99、基态消失偏差 0.33；$N_{\rm boot}$ 不产生物理精度；
- 真实 anchor/§6.2/§7：⛔。

## 公共框架

- F0：统一证据 schema + 可复用检查 + 审计脚本；
- F1：五类接口（TaskSpec、OperatorContract、MeasurementBundle、ReferenceProvider、SearchAdapter）+ 跨入口一致性（4 个下界差 0）+ 缓存失效反例；
- F2：候选校验、mock 轨迹、搜索不读 validation；
- F3：RunState + Ledger + fold bindings（未接入 evaluate 持久化，🟡）；
- F4：见上（🟡）。

## 剩余（都需要新资源/授权）

- pion：真实 anchor、§6.2 共同目标预测、§7 新测量先决条件；
- wilson：P4 研究扩展（stout/GEVP/multilevel/新盲测）、生产 ΔH/接受率、多 rank；
- optimize：GPU class×optimizer 2×2、real/shuffled 消融、新盲测、power simulation。

## 健康检查

- 75 个 CPU 测试通过；
- 所有非公式链接有效；
- README / 总报告 / 结果 JSON 的数字一致。
