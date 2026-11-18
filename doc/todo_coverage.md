# todo 覆盖报告（2026-11-18，按新开工单）

对应三份更新后的 `tasks/*/todo.md`。状态：✅ 完成（代码+证据）、🟡 部分（有设计/合成证据，
真实数据或完整验收未做）、⛔ NOT_RUN。基线：`ded77ae`。

## 1. pion_projection

| 条目 | 状态 | 证据 |
| --- | --- | --- |
| §1 A：reference 身份/工厂、反射动态化 | ✅ | `reference.py`、`experiment.py`、T32 反射 274.27→2.40 |
| §1 B：归档/参考/窗口/两态诊断 | ✅ | `score_diagnostics_v2/`（旧 60 dev）；P1.3 扩展到 120 dev |
| §1 S1：保守评分 | ✅ | `scoring.py` + `score_contract.md`（P0.4/P0.5 强制边界） |
| §1 C2：矩阵探索 | ✅ | `gram_operator_identity.md`：M≠标准 C（差 30%，C 自身 anti-Hermitian 30%） |
| §1 C3：能量目标 | 🟡 | `energy_experiment.py`：单 cosh 覆盖率 0、两态 0.99；真实 anchor ⛔ |
| §1 D：新 campaign | ✅ | S16T16C 200 组态；参考仍失败（χ²=90.6/8，m0=1.0771） |
| P0.1 测量对象推导 | ✅ | `doc/gram_operator_identity.md` + `gram_identity_check.json` |
| P0.2 估计顺序 | ✅ | `gevp_stats.py`：去重→block bootstrap→replica 平均→秩截断→平台 |
| P0.3 已知谱验收 | ✅ | 100 个独立数据集覆盖率 **0.95**、偏差 2e-4 |
| P0.4 estimand | ✅ | `doc/score_contract.md` |
| P0.5 schema/身份强制 | ✅ | `scoring.py`：模型/候选集合、一维等长、原始正值、invalid 比例、近零 baseline、门槛 |
| P0.6 联合 resampling | ✅ | `joint.py` + `results/pion_projection/joint_20261118/`（200×64，gate 失败→abstain） |
| P1.1 双层校准 | ✅ | `calibration_full.py`：full 0.025、fixed 0.095、两态拒绝率 0.53 |
| P1.2 校准分辨率 | ✅ | $(k+1)/(N+1)$，400 次模拟；6/12/24 blocks 扫描 |
| P1.3 120-dev 诊断 | ✅ | `score_diagnostics_v3/`：秩满但条件数 $10^6$–$10^8$；$m_0$ 从 1.44 掉到 1.08；两态 profile 半宽/SE=2.7 |
| P1.4 全链 nested CV | ✅ | `nested_cv_v1/`：5 折，local/SLSQP 209–750（平均 427±89）；学习核重训 ⛔ |
| §6.1 能量估计实验 | ✅ | `energy_target_v1/`：bias/variance/MSE/coverage、$N_{\rm boot}$ 语义、anchor 敏感性 |
| §6.2 共同目标预测 | ⛔ | 未做 |
| §7 新测量先决条件 | ⛔ | 未做（需要新 GPU 生产/访问记录） |

结论：P0/P1/§6.1 已全部落地；真实 anchor、共同目标预测、新测量先决条件仍 NOT_RUN。

## 2. wilson_loop

| 条目 | 状态 | 证据 |
| --- | --- | --- |
| P0 投影数值边界 | ✅ | 逐矩阵 Newton–Schulz + 收敛检查；混尺度 batch 1e-16；rank-2 拒绝；`audit_20261118_projection/` |
| P1 可信加载/冻结 | ✅ | `identity.py`：generation、resume、gauge 几何、trust_status；v3 归档判 archived_diagnostic |
| P2 配对统计审计 | ✅ | `paired_audit_v1/`：v2 点值 1.07–1.18 vs 中位数 3.0–3.4；唯一 block 分布、jackknife 0.49–4.53 |
| P3 物理质量门控 | ✅ | `spectral_quality_v1/`：平但错反例（偏差 170σ、risk 2.7e-7、gate 通过）；`doc/wilson_spectral_quality.md` |
| P4 研究扩展（设计） | ⛔ | 只有 todo 中的设计表 |
| F0 证据 schema | ✅ | `core/evidence.py`、`operator_checks.py`、`scripts/audit_run.py`、`summarize_evidence.py` |
| F1 五类接口 | ✅ | `core/specs/measurement/comparator/search/reference_provider`；一致性 + 缓存失效反例 PASS |
| F2 LLM/搜索隔离 | ✅ | `core/candidates.validate_weights`、mock 轨迹、`--no-validation` 拦截测试 |
| F3 状态/账本 | 🟡 | wilson develop/evaluate 已持久化 run_state、measure 带 ledger；pion nested_cv bindings；pion evaluate 与 GPU 账本仍未接 |
| F4 HMC 质量 | 🟡 | manifest 审计（seed/间隔/τ_int=0.512；ΔH/接受率缺失）；toy 可逆性 $10^{-10}$、$\Delta H$ 二阶；生产 ΔH/接受率/多 rank ⛔ |

结论：P0–P3 与 F0–F2 完成；F3 部分；F4 的 toy 通过、生产证据缺失；P4 仅设计。

## 3. optimize_gaussian

| 条目 | 状态 | 证据 |
| --- | --- | --- |
| P0.1 完整 BCB 验证 | ✅ | `tests/test_optimize_gaussian.py`；`audit_20261118_bcb/`（<1e-10） |
| P0.2 basis/输入身份闭包 | ✅ | basis_key 含依赖 hash + gauge/propagator 内容摘要；mutation 测试覆盖依赖/输入/ID 变更 |
| P0.3 audit 与措辞修正 | ✅ | audit.py 按 manifest 分类（v9 = current_operator_diagnostic）；显式 --out 拒绝覆盖；dev_val 不回退；措辞已改“未检出差异” |
| P1 统一统计/fold-local | 🟡 | `unified.py`：同一入口复算 local/SLSQP 逐位一致；3 折 fold-local 比率 185/75/389（平均 216±92，训练折幅度）；学习核重算与整链 nested CV 仍 ⛔ |
| §P2 函数类实验 | 🟡 | `teacher_check.py`：七幂误差 0.01268 > 谱外 0.01239，增广基 1.8e-16；GPU class×optimizer ⛔ |
| §P2 函数类实验 | 🟡 | `teacher_check.py`：七幂基对非对易 teacher 的误差 0.01268 > 谱外 0.01239，增广基 1.8e-16；训练的 class×optimizer 实验 ⛔（GPU） |
| §P3 最小判别实验 | 🟡 | CPU 跨样本 teacher PASS（ε=0 恢复、ε=0.1 谱类 0.0127 vs 增广 6.7e-16）；GPU class×optimizer/消融 ⛔（[`doc/optimize_p3_design.md`](optimize_p3_design.md)） |

结论：P0.1–P0.3 完成；P1 为部分（统一入口一致、fold-local 比率方差大）；P2/P3 只有 CPU 切片与设计；GPU 实验全部 ⛔。

## 4. 总结

- pion：P0/P1/§6.1 全部完成；⛔ = anchor/预测/新测量先决条件；
- wilson：P0–P3 与 F0–F2 完成；🟡 = F3/F4；⛔ = P4；
- optimize：P0 完成；P1/P2/P3 为 CPU 部分/设计；GPU 2×2、消融、新盲测 ⛔；
- 73 个 CPU 测试通过；所有非公式链接有效；旧“CPU 已全部完成”的说法已作废。
