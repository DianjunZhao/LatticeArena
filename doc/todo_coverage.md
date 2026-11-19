# todo 覆盖报告（2026-11-19，按用户指出的“负结果”复核后）

状态图例（**不要把负结果读成认证**）：

- ✅ 完成：代码 + 证据，结论可以正面陈述，但只在声明的有限范围内；
- ⚠️ **负结果/INCONCLUSIVE**：代码与证据成立，但结论是“gate 有盲点 / 样本不足 / 构造性”等；
  **不是**“已认证”“已控制”“优于基线”；
- 🟡 部分；⛔ NOT_RUN。基线：最新提交；CPU 测试 **117 项通过**。

## 0. 三处最容易被误读的“负结果”（用户指定复核）

1. **wilson 两态反例 = gate 盲点，不是 E0 认证**
   `spectral_physical_v1/`：spread/V ≤ 0.006 的 gate 在 $c_1$ 到 0.5 时仍然通过，
   而短窗 bias/SE 达到 32.5。这说明**当前 spread gate 看不见共同偏差**；`window_paired_z`
   （1.02/3.01/5.43/16.65）只是更敏感的诊断，**没有进入 gate**。因此：
   - ❌ 不能写“两态反例已认证 gate”；
   - ✅ 只能写“已知反例下 gate 通过但值偏离 E0，说明 gate 不足”。
2. **pion 0/8 = smoke/INCONCLUSIVE，不是族错误率受控**
   χ² subgate benchmark 的每 cell 只有 8 个 dataset。0/8 的双侧 95% Clopper–Pearson
   区间是 **[0, 0.36942]**，单侧 95% 上界 **0.31234**——**不能**由 0/8 声称错误率受控。
   该 benchmark 只覆盖 5% 的 χ² 子门（$N_{\rm null}=50$ 时最小 p=1/51，不能检验 1%）。
3. **optimize 类 B 的 ε>0 零误差 = 构造性，不是学习/泛化优势**
   目标 $Q=H^2+\epsilon BHB$ 显式含 $G_0=BHB$，而类 B 的特征里就有 $G_0,G_0H,HG_0$；
   ε>0 时 B 的误差为 0 是**可表示性**的构造结果。类 A 的非零误差同样由目标在 A 的特征空间外
   所致。两者都不是“B 比 A 更好”的实证，也不是从数据学到 Q 映射。

## 1. pion_projection

| 包/条目 | 状态 | 证据与限制 |
| --- | --- | --- |
| A1 完整身份 | ✅ | submission/report/dev/val 内容 SHA、完整 protocol、IDs、reference 实现、候选、late metric；矩阵 `audit_20261119_identity/`；注意历史 run 无 artifact/spec，只能 abstain |
| A2 gate artifact | ✅ | 绑定 reference spec 哈希、窗口、dev hash、metric；joint 走 `load_data` 可信路径 |
| A3 统一 abstain | ✅ | 任一理由清除全部 `candidate.certified` |
| A4 冻结 score spec | ✅ | 缺 spec 的历史 run → `score_spec_missing` abstain |
| A5 manifest/复现 | ✅ | submission/gate/spec/deps 绑定；同 seed 两次 run 数组逐位相同 |
| B rank/网格 | ⚠️ 负结果 | rank/正性反例与 cutoff 已修；网格 20 dataset/cell 的 coverage=0（bootstrap 不含系统偏差），bias 0.02–0.04；**不能认证基态** |
| C1/C2 共享路径 | ✅（仅 subgate） | 模拟先 fold、同一 ReferenceFit；名称是 **χ² subgate**，不是完整正式 gate |
| C3 冻结 late metric | ✅ | 每 outer draw 用 dev 训练块 late_metric |
| C4 模型集合 | ✅（已补） | `run_family` 对 single/twostate **各自**做 gate（twostate 还检查 `at_boundary`）；本数据 2/8 abstain（twostate mass2 顶到上界）、valid 6，null 0/6、better 0/6 → INCONCLUSIVE |
| C5 wrong-state | ⚠️ 负结果 | 8/8 gate 以质量 1.50 通过、候选 ratio 0.49–1.68；独立质量 guard 8/8 标出；**gate 本身无法区分 E1/E0** |
| C6 参数清理 | ✅ | `contam_candidate` 删除 |
| C2 MC 语义 | ⚠️ INCONCLUSIVE | 0/8 的 CP 区间 [0,0.369]、单侧 0.312；只验证 5% 子门；见 §0.2 |
| C3 paired 区间 | ✅ | naive 1.49 / paired 20.64 / independent 0.14±0.49；固定数据 Nboot 50→800：naive 1.24→0.35、paired 7.2→9.96；paired 是单 ensemble 合法区间，不除 √B |
| §5 测量计划 | ✅ | 校验 + preflight（GPU 前）；draft/越界/占位/缺 stop rule 拒绝；`measurement_plan_audit_v1/` |

## 2. wilson_loop

| 包/条目 | 状态 | 证据与限制 |
| --- | --- | --- |
| P0 真实 pending 恢复 | ✅ | 同 spec 中断 2/3→3，数组/IDs/逐行 sha 与干净 run 相同；ledger incremental；`audit_20261119_resume/` |
| P0b 投影支持域 | ✅（含说明） | cond≤1e3 在 1e−9 内通过；域外**策略**拒绝；3 个域外 cell 数值残差仍小但按边界拒绝；SU(3) 协变 1.4e−10 |
| P1a 事务矩阵 | ✅ | 10 类故障注入全 PASS；原子 marker；必需依赖 hash |
| P1b 标准 checksum | ✅ | 32-bit word 和；冷场 ff400000；错误头（即使 MD5 正确）拒绝 |
| P2a invalid evaluate | ✅ | 坏候选 null+reason；坏 identity 拒绝；Vref 检查；paired nominal |
| P2b 统计口径 | ⚠️ 限定 | coverage=0.983 是**近似目标覆盖**（truth=4 为噪声比近似），不是“证明保守”；block/τint 与多重比较延期 |
| P3 有限 Nt/window_z | ⚠️ 负结果 | `finite_nt_scope.md`；两态反例是 gate 盲点，见 §0.1；window_paired_z 仅诊断，未入 gate |
| F0 receipt | ✅ | 证据 receipt（code/inputs/run sha）；空/篡改 PASS 拒绝；`scripts/verify_evidence.py` 对归档文件重算并验证（改数据/改 evidence 均失败） |
| F1 comparator | ✅ | 零/负分母、空 draw 拒绝；接入 paired 比值路径；pion 证书仍用 floor 处理零风险 |
| F2 预算/畸形 | ✅ | 每轮 + 全局上限；畸形提案记录拒绝不中止 |
| F3 receipts/状态 | ✅（conditional-only） | physical 需 execution receipts；develop 造 4 个、evaluate 验证并携带；comparison 保持 draft，**不发 physical 分数** |
| F4/P4 | ⛔ | 生产 ΔH/接受率/热化、stout/GEVP/multilevel/新盲测延期 |

## 3. optimize_gaussian

| 包/条目 | 状态 | 证据与限制 |
| --- | --- | --- |
| 包A 可信输入 | ✅ | 缺字段→archived；超残差 trusted 拒绝；reference 绑定实际 bootstrap |
| 包B fit-state | ✅ | weights/scales/blocks/reference 来源；回归 60×200；5×20 仅 smoke |
| 包C 公平 2×2 | ⚠️ 构造性诊断 | ε=0 A 精确；ε>0 A 0.0076/0.038/0.079、B=0；**B=0 是特征包含 G0 的构造结果**，不能读作学习/泛化优势；优化器≈oracle |
| 包D 实际闭环 | ⚠️ 管线演示 | 实际 BCB response 作 search 评价器；算子残差 ~1e−16；搜索/精确差 0 是**同一评价器**的构造结果，不是 surrogate 精度验证 |

## 4. 总结

- CPU 必做项均有代码、负例/诊断与有限结论；但 3 处负结果（§0）只能按“gate 盲点/INCONCLUSIVE/构造性”
  陈述，不能升级为“认证”“受控”“更优”。
- 未跑项（pion §6/新测量、wilson F4/P4、optimize GPU 2×2/真实 W）逐项 NOT_RUN/延期；
- 117 个 CPU 测试通过；所有非公式链接有效。
