# todo 覆盖报告（2026-11-19，第三轮验收后）

对应三份更新后的 `tasks/*/todo.md`。状态：✅ 完成（代码+证据）、🟡 部分、⛔ NOT_RUN。
基线：最新提交；CPU 测试 **117 项通过**。

## 1. pion_projection

| 包/条目 | 状态 | 证据 |
| --- | --- | --- |
| A1 完整身份 | ✅ | `verify_run_identity` 绑定 submission/report/dev/val 内容 SHA、完整 protocol、IDs、reference 实现、候选集合、late metric；矩阵 `audit_20261119_identity/joint_identity_audit.json`（stale report/重排/换源均拒绝） |
| A2 gate artifact | ✅ | artifact 绑定 reference spec 哈希、窗口、dev hash、metric；joint 校验并在缺失时 abstain |
| A3 统一 abstain | ✅ | 任一理由（缺 artifact/spec、gate 失败）清除全部 `candidate.certified` |
| A4 冻结 score spec | ✅ | joint 读取 submission 的 `score_spec`；缺失（历史 run）→ `score_spec_missing` abstain；alpha/族/floor 不可事后改 |
| A5 manifest/复现 | ✅ | joint manifest 绑定 submission/gate/spec/deps；同 seed 两次 run 数组逐位相同 |
| B rank/网格 | ✅ | `_eigvals` 整数/范围/正性；rank=0、负本征值反例；cutoff 贯通；`gevp_ground_failure_grid_v1/`（20 dataset/cell，bias 0.02–0.04，coverage 0——bootstrap 不含系统偏差） |
| C1/C2 共享路径 | ✅ | 模拟先 `fold`、同一 ReferenceFit/gate；名称明确为 **χ² subgate** benchmark |
| C3 冻结 late metric | ✅ | 每 outer draw 在 development 训练块计算并传入 validation risk |
| C4 模型集合 | ✅ | K=2 时两模型各自 gate；缺认证则 abstain |
| C5 wrong-state | ✅ | baseline/candidate 用不同通道（point ratio 0.49–1.68），8/8 gate 通过、质量 1.50、独立 guard 8/8 标出 |
| C6 参数清理 | ✅ | 未使用的 `contam_candidate` 删除；场景由通道污染定义 |
| C2 MC 语义 | ✅ | 条件/无条件率分列；0/8 的 CP 区间 [0,0.369]、单侧上界 0.312；8–20 dataset smoke 允许 INCONCLUSIVE |
| C3 paired 区间 | ✅ | 三种估计量（naive 1.49 / paired 20.64 / independent 0.14±0.49）；固定数据 Nboot 50→800：naive 1.24→0.35，paired 7.2→9.96；共享配置 cell |
| §5 测量计划 | ✅ | 计划校验 + preflight（GPU 前）；draft/越界/占位 hash/缺 stop rule 拒绝；`measurement_plan_audit_v1/` |

## 2. wilson_loop

| 包/条目 | 状态 | 证据 |
| --- | --- | --- |
| P0 真实 pending 恢复 | ✅ | `saved=len(rows)`；同 spec 中断 2/3 后续到 3，数组/IDs/逐行 sha 与干净 run 相同；ledger incremental/previous；`audit_20261119_resume/` |
| P0b 投影支持域 | ✅ | 冻结奇异值×scale×相位网格；cond≤1e3 在 1e−9 内通过，域外策略拒绝；SU(3) 协变残差 1.4e−10；`audit_20261119_projection_domain/` |
| P1a 事务矩阵 | ✅ | 原子 marker、必需依赖 hash；10 类故障注入全 PASS（`audit_20261119_transaction/`） |
| P1b 标准 checksum | ✅ | header CHECKSUM=32-bit word sum；冷场 ff400000；错误头/错误头+正确 MD5 均拒绝；私有 MD5 单独状态（`audit_20261119_nersc/`） |
| P2a invalid evaluate | ✅ | 坏候选 risk/score/ratio=null+reason；坏 identity 受控拒绝；Vref 零/非有限拒绝；paired 传 nominal（`audit_20261119_invalid/`） |
| P2b 统计口径 | ✅ | `doc/statistics_scope.md`：点值/诊断/区间分列，0.983 为近似目标覆盖，block/τint 与多重比较延期 |
| P3 有限 Nt/window_z | ✅ | `doc/finite_nt_scope.md`；window_z 改为配对差 SE（`window_paired_z`），naive 列保留为诊断 |
| F0 receipt | ✅ | 证据带 receipt（code/inputs/run sha）；空/篡改 PASS 拒绝；`results/framework/audit_20261119_receipt/` |
| F1 comparator | ✅ | 零/负分母、空 draw 明确拒绝；接入 paired 比值路径 |
| F2 预算/畸形提案 | ✅ | 外部每轮 + 全局上限；malformed 转换记录拒绝不中止；mock 覆盖 |
| F3 receipts/状态 | ✅ | `RunState` physical 需 execution receipts；develop 造 4 个、evaluate 验证并携带；conditional-only 保持；`unverified-text` 不能 physical |
| F4/P4 | ⛔ | 生产 ΔH/接受率/热化、stout/GEVP/multilevel/新盲测明确延期 |

## 3. optimize_gaussian

| 包/条目 | 状态 | 证据 |
| --- | --- | --- |
| 包A 可信输入 | ✅ | 缺字段→archived_diagnostic；超残差 trusted 拒绝；reference identity 绑定实际 bootstrap 文件；mutation 测试 |
| 包B fit-state | ✅ | 每折 weights/scales/blocks/reference/gate 来源；回归 60×200 与 README 同步；5×20 仅 smoke |
| 包C 公平 2×2 | ✅ | `cpu_close_20261119_C/`：ε=0 A 精确、ε>0 B 迁移 0；优化器=oracle；维度/秩/nfev/梯度记录 |
| 包D 实际闭环 | ✅ | `cpu_close_20261119_D/`：实际 BCB response 作 search 评价器；算子残差 ~1e−16；bundle 能力拒绝 |

## 4. 总结

- 三份 todo 的 CPU 必做项均有代码、负例/诊断与有限结论；
- 未跑项（pion §6/新测量、wilson F4/P4、optimize GPU 2×2/真实 W）已逐项标 NOT_RUN/延期；
- 117 个 CPU 测试通过；所有非公式链接有效。
