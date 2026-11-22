# F4 synthetic receipt/schema preflight

范围：synthetic_CPU；真实生产 HMC **NOT_RUN**。16项测试通过，1个合法合成控制仅schema_ready，15个故障明确拒绝。没有生成生产receipt，也没有运行HMC、GPU、远程或API。

已有 `core.receipts.verify` 检查内容签名和非空身份，但不校验外部预期hash或trajectory schema。新增Wilson专属 `f4_preflight.preflight` 复用它，补外部code/input绑定、trajectory字段/顺序/计数/内容hash与metadata检查；不修改共享状态框架。

## 故障矩阵

| case | result | reason |
|---|---|---|
| valid_synthetic | ACCEPT_SCHEMA_ONLY | identity/schema only; not a production-quality certificate |
| missing_trajectory_sha256 | REJECT | missing production schema fields |
| missing_n_trajectories | REJECT | missing production schema fields |
| missing_thermalization_cut | REJECT | missing production schema fields |
| missing_tau_int_rule | REJECT | missing production schema fields |
| missing_environment | REJECT | missing production schema fields |
| missing_parameters | REJECT | missing production schema fields |
| code_mismatch | REJECT | code hash mismatch |
| input_mismatch | REJECT | input hash mismatch |
| trajectory_missing | REJECT | trajectory data missing or too short |
| trajectory_count | REJECT | trajectory count mismatch |
| trajectory_hash | REJECT | trajectory content hash mismatch |
| missing_delta_h | REJECT | trajectory fields missing |
| duplicate_id | REJECT | trajectory IDs duplicate or unordered |
| nonfinite | REJECT | trajectory values nonfinite |
| invalid_acceptance | REJECT | trajectory id/acceptance type invalid |

完整机器记录见 [preflight.json](preflight.json)。合成控制仍返回physical_status=NOT_RUN，不触发RunState物理认证。当前矩阵没有声称覆盖任意损坏格式；receipt hash说明内容一致，不证明任务真实执行。调用方必须从可信运行上下文取得expected_code/expected_inputs，不能直接复制待验receipt自己的hash。生产生成器尚未接入本preflight，本轮交付为独立接口/合成拒绝测试。

## 复现与边界

从仓库根运行 `PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -q -p no:cacheprovider tests/test_wilson_f4_preflight.py`。JSON保存被测源码hash。schema通过不证明force正确、可逆性、接受率合格、热化完成或tau_int可识别；cut只检查范围，tau_int_rule只检查声明存在。生产阶段须保存原始trajectory、异常/拒绝、环境和执行命令receipt，另做统计质量门控与区间图。toy不能替代这些证据。

## P4 单路线冻结提案（尚未执行）

只选纯空间stout与当前合法APE比较，固定action/geometry/R/T/时间links与risk定义。开发集限定同等提案次数，先冻结stout参数网格、基线、所有kernel版本、统计draw计划、最小有用增益和独立validation IDs；预算数值在生产profiling后、打开新validation前写入protocol。比较同一组态配对risk及加载/平滑/收缩/总时间，至少交cost-risk图区间和失败表；不同时换GEVP或multilevel。先验收协变/时间局域和null/two-state controls，无法排除共同偏差则只报conditional diagnostic。

执行条件：可用GPU/CuPy与已验收F4生产trajectory receipts；同精度/硬件/收敛口径、未见独立样本、原始gauge hashes和足够自相关信息。当前这些条件未满足，物理测量NOT_RUN。没有区间收益或成本收益可作为负结果停止，不扩大搜索到成功。
