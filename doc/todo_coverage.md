# todo 覆盖报告（2026-11-18）

三个 `tasks/*/todo.md` 的条目按状态分类：

- ✅ **完成**：代码 + 测试/真实结果；
- 🟡 **部分**：设计/合成验证完成，真实数据或完整实验未跑；
- ⛔ **NOT_RUN**：需要新的 GPU 数据、新的算符/测量设计，或用户授权。

核对基线：`e87367d`。

## 1. pion_projection

| todo 条目 | 状态 | 证据 / 位置 |
| --- | --- | --- |
| 阶段 A：reference spec 冻结、统一 factory、反射泛化、legacy 模式 | ✅ | `reference.py`、`experiment.py`、legacy 重放精确复现归档数值 |
| 阶段 A：CPU 回归测试 | ✅ | `tests/test_pion_projection.py`（含冻结/篡改/反射） |
| 阶段 B：归档 inventory、参考扫描、协方差谱 | ✅ | `results/pion_projection/score_diagnostics_v2/` |
| 阶段 B：T=32 反射假警报 | ✅ | 274.27 → 2.40（`reflection_check.json`） |
| 阶段 B5：预声明 shrinkage/block 扫描 | ✅ | 网格内无组合通过（max p=0.0072） |
| 阶段 B6：两态返回 $m_1$/gap/幅度/条件数 | ✅ | `reference_twostate.py` + 测试 |
| 阶段 B9/B10：block 级 p 值校准 | 🟡 | 已实现（`calibration_blocks.py`），但 12 blocks/15 维导致循环零分布，结论不可用 |
| 评分重设计 S1：保守改善证书 | ✅ | `scoring.py` + 合成测试；真实数据 abstain |
| C1：多态/模型平均 | 🟡 | `model_average.py`：AIC/BIC 权重退化，排序随模型翻转 → 不能救参考 |
| C2：GEVP | 🟡 | 合成 ✅（`gevp.py`）；真实数据 2×2/3×3 无平台；两族/三族 Gram GEVP 给出 $m_0\approx1.02$–$1.05$；完整算符集 ⛔ |
| C3：能量误差目标 | 🟡 | `energy_target.py` 合成验证 ✅；独立 anchor ⛔ |
| 阶段 D：新 GPU 数据/可移植性 | 🟡 | 200 组态 S16T16C（120 dev / 60 val）已生成并测量；参考仍失败、GEVP 平台仍限 $t\le5$；生成器已入库 |
| T=32 新系综测量 | ✅ | `results/pion_projection/s16t16_gevp/` 与多 source 数据 |

**结论**：参考不可识别是结构性的（15 维/12 blocks、模型失配、$m_0$ 在 1.02–1.09 间不确定），
CPU 侧能做的诊断和工具链已经完成；真实数据的 C2（完整算符集）和 C3（独立 anchor）未执行。

## 2. wilson_loop

| todo 条目 | 状态 | 证据 / 位置 |
| --- | --- | --- |
| P0：双边极分解投影 | ✅ | `kernels.project`，左右协变测试 |
| P0：staple 归一化 $/4$ | ✅ | `protocol_v2.json`，$\alpha$ 口径说明 |
| P1：NPZ/NERSC 校验 | ✅ | `read_nersc`（DATATYPE/FLOATING_POINT/payload）、`load_data` |
| P1：provenance（gauge/kernel/git/计时） | ✅ | `measure.py`；硬件/QUDA 版本仍缺 |
| P1：evaluate 冻结校验 | ✅ | development SHA、kernel hash、参数一致性 |
| P2：预注册配对分析 | ✅ | `paired.py`；v3 区间不含 1 |
| 修复后 GPU 重测 | ✅ | `s16t16_v2`（60/30）与 `s16t16_v3`（200 系综，80 留出） |
| 更大 $R$ / 更多体积/$\beta$ | ⛔ | 需要新测量 |

**结论**：协变 APE 在 v3（80 留出组态、16 blocks）下**显著优于 identity**（263/233/222，
配对区间不含 1）；更远的外推未做。

## 3. optimize_gaussian

| todo 条目 | 状态 | 证据 / 位置 |
| --- | --- | --- |
| §5.1：shift/Hermitian/covariance/线性响应测试 | ✅ | `tests/test_optimize_gaussian.py` |
| §5.2：全 O_h 群（24 旋转 + parity） | ✅ | link 中心特征；全部通过 |
| §5.3：缓存 identity、run manifest | ✅ | `basis_key`、`manifest.json`（protocol/W/θ/IDs/依赖 hash） |
| §6：统一离线评测 | 🟡 | `audit.py` 出历史表；特征已变，无法统一重算旧响应 |
| §7：学习空间扩展（群平均/多层） | ⛔ | 未实现；v9 已追平 SLSQP，需要更强函数类才可能超越 |
| §8：最小有判别力实验 | 🟡 | v9 GPU 重训 + 与 SLSQP 配对（0.998 [0.78,1.18]）；新数据配对 ⛔ |
| §11：plaquette 路径闭合 | ✅ | 规范不变测试（1e-15） |
| 修复后 GPU 重训 | ✅ | `results/optimize_gaussian/v9/`（2.12×，与 SLSQP 打平） |

**结论**：算子正确性、A1+ 认证、身份闭包和一次 GPU 重训都已完成；要超越 SLSQP 需要新的
函数类或更多数据，这是研究性问题，不在“完成 todo”的范围内。

## 4. 总结

- ✅ 三个 task 的**算子修复、契约冻结、测试、诊断、文档**已经完成；
- ✅ 两次 GPU 重测（wilson v3、optimize v9）给出修复后的物理结果；
- 🟡 pion 的 C2/C3 只有合成验证和部分真实数据尝试，完整实验需要新算符/新 anchor；
- ⛔ 所有需要**新 GPU 生产**的条目都明确列出，未假装完成。

合计：50 个 CPU 测试通过，所有非公式链接有效，README/总报告/结果索引数字一致。
