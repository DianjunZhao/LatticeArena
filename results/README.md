# results/

这些是**真实跑出来的**结果文件，默认被 `.gitignore` 忽略，这里只强制加入小体积的、可离线复算的产物。

## `pion_projection/s16t16_v1/`

- **数据来源**：2026-11-13 在 kunshan DCU 上，用本仓库代码 + PyQUDA HMC 现产的 100 个 `16^4`、β=6.0 纯规范组态；开发 0–59、gap 60–69、留出 70–99。
- **协议**：本次运行用的是 60/10/30 的协议，和仓库里 `tasks/pion_projection/protocol.json`（30/5/15、jinchen 路径）**不同**。该运行的协议快照存在本目录的 `protocol.json`，哈希为 `d03b1e6f…`；`development.npz` / `validation.npz` 里也带着同一个哈希。
- **结论**：参考态没过 gate（名义窗口 p=1.7e-8，窗口漂移 21.6σ / 7.8σ），所以 `score_status = unscored_reference_failed`，所有 `score` 为 `null`。这是设计行为，不是 bug。
- **前三名（诊断口径）**：`agent_signed_mixture` 0.00770（相对 local 40.6）、`tuned_gaussian` 0.01256（24.9）、`local` 0.31267（1.0）。区间与解读见 `REPORT.md`。

### 文件

| 文件 | 内容 |
| --- | --- |
| `development.npz` / `validation.npz` | `(60,7,16)` / `(30,7,16)` 的关联函数 + ids + protocol_hash |
| `development_results.json` | 7 个基线的开发集 risk，以及 SLSQP 混合的结果 |
| `submission.json` | 冻结提交：权重、哈希、参考诊断 |
| `validation_results.json` | 留出结果（score 全 null）+ 嵌套区间 |
| `REPORT.md` | 代码生成的前三名表格 + LLM 解读 + LLM 作答（post-hoc） |
| `pilot_results.png` | 4 面板诊断图 |
| `protocol.json` | 本次运行实际使用的协议（60/10/30） |
| `agent/` | LLM 每轮提案（`round{r}_{i}.json`）、最佳（`best.json`）、交卷定义（`llm_candidate.json`） |
| `candidates/*/development_verification.json` | 用 `candidate --verify-only` 在 1 个组态上核对通用算子与基矢组合一致（最大相对差 1.9e-15） |

### 离线复算

有 npz 就能跑分析，不需要 GPU：

```bash
python -m tasks.pion_projection --output results/pion_projection/s16t16_v1 report   # 需要 API key
python -m tasks.pion_projection --output results/pion_projection/s16t16_v1 agent --rounds 1
```

注意：`develop` / `evaluate` 用的是 `tasks/pion_projection/protocol.json`，和本目录的 60/10/30 协议不一致时会直接报错——这是冻结机制在起作用，不是文件损坏。
