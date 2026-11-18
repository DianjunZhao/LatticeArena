# 项目状态（2026-11-18）

三个任务的最终状态。细节见 [`doc/final_report.md`](doc/final_report.md)、
[`doc/todo_coverage.md`](doc/todo_coverage.md) 和各自的 task README。

## 一句话

| task | 状态 | 关键数字 |
| --- | --- | --- |
| `wilson_loop` | **修复后显著改善** | v3（80 留出组态）：APE score 263/233/222，配对区间不含 1；v4（+$R=4$）：663–808，区间不含 1 |
| `optimize_gaussian` | **与强基线未检出差异** | v9（link 中心 A1+ 特征）：测试 2.12×；候选 risk 0.007721 vs SLSQP 0.007703，配对 0.998 [0.78,1.18] |
| `pion_projection` | **无可信分数** | 参考质量 $m_0$ 在 1.02–1.09 间不确定；GEVP 偏向两态 1.057，单 cosh 1.086 给出相反的候选排序 |

## 各任务要点

### wilson_loop

- 修好了核的规范协变（双边极分解）与 staple 归一化（$\alpha/4$）；
- v2（60/30）点估计 3× 但区间跨 1；v3（200 组态系综、80 留出、16 blocks）**区间不含 1**；
- v4 加入 $R=4$：$V(4)$ 的 SE 从 0.0233 降到 0.005–0.007，分数 663–808（$R$ 集合不同，尺度不可比）。

### optimize_gaussian

- 修好了 plaquette 闭合与 A1+（link 中心特征，24 旋转 + parity 全过）；
- v9 GPU 重训：测试 2.12×（v7 为 1.52×），候选与 SLSQP 未检出差异；
- 历史 v1–v8 用旧特征，只能作为流程/负结果记录。

### pion_projection

- 参考模型的诊断链：模型失配 → 15 维/12 blocks 秩亏 → 校准 p 值/加长 T/两态/模型平均都无效；
- $m_0$ 扫描：分数变化约 7 倍，排序在 1.06 翻转；
- GEVP（两族/三族 Gram）给出 $m_0\approx1.02$–$1.05$，偏向两态参考；
- C2 完整算符集与 C3 独立 anchor 仍 NOT_RUN（需要新测量）。

## 剩余（都需要新资源）

- pion：更多 $t\ge6$ 统计量 / 完整 GEVP 算符集 / 独立 anchor；
- wilson：更大 $R$、更多体积/$\beta$；
- optimize：更强的函数类（群展开/多层）或更多数据。

## 健康检查

- 50 个 CPU 测试通过；
- 所有非公式链接有效；
- README / 总报告 / 结果 JSON 的数字一致。
