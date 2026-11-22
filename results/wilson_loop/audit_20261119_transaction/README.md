# P1a：事务故障注入矩阵

生成：`python -m tasks.wilson_loop.transaction_audit`；数值：`transaction_matrix.json`。

## 修复

- `write_marker` 改为 tmp + `os.replace` 原子保存；
- `check_resume` 现在**要求** provenance 的 `dependencies` 含全部 5 个依赖 hash 且与当前文件一致；
  缺字段不再静默通过；
- `trust_status` 对缺失依赖 hash 记 reason（不因非 None 而通过）。

## 故障注入（10 类）

| 注入 | 期望 | 结果 |
| --- | --- | --- |
| 合法事务 | resume 3 行 | ok |
| 缺 npz / provenance / marker | partial transaction | 拒绝 |
| marker generation 改 | generation 不符 | 拒绝 |
| npz 内容改 | 文件 hash 不符 | 拒绝 |
| provenance 记录乱序（并重写 marker） | record ids 不符 | 拒绝 |
| gauge 文件删除（并重写 marker） | gauge 文件/hash 不符 | 拒绝 |
| 依赖 hash 改（并重写 marker） | dependency changed | 拒绝 |
| marker loops hash 改 | loops content 不符 | 拒绝 |

全部 `status=PASS`（`all_status_pass=true`）。

## 语义

- 任何“混拼”状态都被拒绝，不做自动修复；
- 损坏的 marker 只能拒绝或新 run（原子写避免半文件）；
- 身份相符 ≠ physical 认证：`trust_status` 仍返回 archived/diagnostic 与分项 states。

## 测试

`test_transaction_rejects_mixed_files`：合法前缀可 resume；缺文件/篡改 npz/改依赖均拒绝。
