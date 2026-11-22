# P1b：标准 NERSC CHECKSUM 与私有 MD5

生成：`python -m tasks.wilson_loop.nersc_checksum_audit`；数值：`nersc_checksum.json`。
原始实现依据：Grid `NerscIO.h`（读取 header `CHECKSUM`）与 `BinaryIO.h`（32-bit word 加和）。

## 算法

- 标准 `CHECKSUM` = payload 的 **32-bit word 和（mod 2³²）**，在 host-order 值上计算：
  - `IEEE64LITTLE`：直接对文件小端字求和；
  - `IEEE64BIG`：先按大端读 double、转 host 端序，再对字求和；
- 私有 16-byte MD5 尾单独验证，**不能覆盖标准头失败**。

## 矩阵（BytesIO/冷场 1⁴）

| 用例 | 标准头 | MD5 | 结果 |
| --- | --- | --- | --- |
| cold_standard_ok | `ff400000` 正确 | — | verified=True |
| cold_standard_wrong | `ff400001` 错 | — | 拒绝 |
| cold_standard_wrong_md5_ok | 错 | 正确 | **拒绝**（标准头优先） |
| cold_standard_ok_md5_ok | 正确 | 正确 | 两者 verified |
| cold_md5_only | 缺 | 正确 | standard=absent，verified=False |
| cold_absent | 缺 | 缺 | 双 absent，verified=False |
| cold_payload_altered | 头未改、payload 改 | — | 拒绝（computed ff480000） |
| big_standard_ok | 大端正确 | — | verified=True |

冷场 1⁴ 的 32-bit word 和 = **ff400000**，与用户给出的反例一致；错误头 `ff400001` 被拒绝。

## 语义

- `checksum_status` 现在是 `{'standard': ..., 'md5': ..., 'verified': bool}`，measure 逐条记录；
- `verified` 只表示标准头通过；私有 MD5 通过不把 `verified` 置真；
- 格式不支持（如 IEEE32LITTLE）明确拒绝。

## 测试

`test_nersc_standard_header_checksum`：正确/错误头、错误头+正确 MD5、大端、payload 改变。
