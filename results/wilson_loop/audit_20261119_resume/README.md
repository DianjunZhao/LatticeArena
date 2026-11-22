# P0：真实 pending 恢复入口

## 问题（用户给出）

`measure.py` 里 `rows` 预载 `completed` 条、再 append 新行，但保存时用
`saved = completed + len(rows)` 双计旧前缀。mock 复现：

```text
resuming development from row 2/3
RuntimeError: row accounting mismatch: saved=5 len(rows)=3 len(records)=3
save_called: False
```

## 修复

- `saved = len(rows)`（rows 是**全部前缀**，不是新增行）；
- 断言改为 `saved == len(records)` 且 `[r['id'] for r in records] == spec['ids'][:saved]`；
- `measure(..., stop_after=N)` 只作为测试/中断钩子，不进入 spec/generation：
  在第 N 条**已完整保存**事务后抛 `KeyboardInterrupt`；
- ledger 不再覆盖历史：provenance 记录
  `ledger = {'incremental': bool(completed), 'current': ..., 'previous': ...}`。

## 验证（`tests/test_wilson_loop.py::test_measure_real_pending_resume_same_spec`）

1. 同一完整 spec 运行，`stop_after=2` 中断：npz 保存 2 行、records IDs `[0,1]`；
2. 再次调用同一 spec（不改 limit、不改 generation）：从第 2 行续到 3 行，
   records IDs `[0,1,2]`；
3. 与干净全量 run 对比：`loops` 数组逐元素相等、每行 `loops_sha256` 相等；
4. resume 的 provenance `ledger.incremental=True` 且 `previous` 非空。

## 语义

- 计时/时间戳不同，但物理数组、IDs、逐行摘要一致；
- 不中断与中断续测的 npz 内容（除压缩元数据）一致；
- 保存确实发生（中断前已落盘 2 行）。
