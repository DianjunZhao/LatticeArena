# v2 amendment01：固定候选生产链与预算dry-run

旧v2、execution_01、原adapter parity不变；本目录为新版本。主MC NOT_RUN，0/2814。

生产develop新增仅在protocol显式synthetic且fixed spec准确为channel1/channel2时启用的冻结模式；不运行SLSQP、不事后改submission。冻结protocol包含候选定义，submission保存synthetic_fixed_candidates；evaluate支持固定候选名称集合。joint仍执行真实身份与certificate链。

生成器synthetic_worlds.py：通道共享噪声+独立噪声共同构造；null两个通道同分布，improvement降低channel2 excited overlap；wrong_state最低出现能级1.5而非物理E0=.8并保留不同污染。所有结果synthetic，physical_score=null。

## 七场景parity/拒绝表
|场景|预算|秒|结果|说明|
|---|---|---:|---|---|
|null_equal_candidate|128/200/64|11.3362|PASS|逐draw一致、gate一致、身份负例拒绝|
|known_lower_excited_overlap|32/4/8 smoke|0.1199|PASS|逐draw一致、gate一致、身份负例拒绝|
|window_mismatch|32/4/8 smoke|0.1212|PASS|逐draw一致、gate一致、身份负例拒绝|
|reflection|32/4/8 smoke|0.1159|PASS|逐draw一致、gate一致、身份负例拒绝|
|relative_error|32/4/8 smoke|0.0293|BLOCKED|ValueError: Amplitude not identified: z=2.778|
|wrong_state|32/4/8 smoke|0.1134|PASS|逐draw一致、gate一致、身份负例拒绝|
|nonfinite|32/4/8 smoke|0.0046|BLOCKED|ValueError: Nonfinite measurement|

完整null预算耗时11.3362s；按此单次粗略线性投影2814个world约8.86小时，包含evaluate与joint两条抽样流程及IO；不是实际总耗时或跨硬件性能保证。
null完整预算检查200×2=400个candidate/draw差异；其余成功smoke为4×2=8项。每个目录adapter_parity.json记录精确差异和submission/reference/gate/report/late-metric负例。
高噪声在真实develop的risk幅度门触发z=2.778，nonfinite在load_data拒绝；这不是伪造认证失败，也不能悄然丢dataset。当前adapter用BLOCKED捕获异常；下一执行器须将这两类预期拒绝规范化为failure/abstain并保存原始输入、seed、异常阶段。
## 仍需完成的有限前置
将expected rejection映射到dataset结果schema；其余六场景完成完整预算dry-run（不计入402cell）；再以同一冻结amendment启动可恢复执行器。保持每cell402固定，输出逐例记录、CP95和candidate-rate图。此目录未生成MC图，不能将参考接受率或smoke certificate称candidate power。
生产gate、joint、identity等新hash已写preregistration；它是amendment的新hash，绝不是旧402计划hash仍然有效。真实anchor/GPU仍NOT_RUN。
回归命令：PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -q -p no:cacheprovider tests/test_pion_synthetic_adapter.py tests/test_pion_full_gate_mc.py。

## 后续完整预算 dry-run

上表记录的是 amendment 刚建立时的 initial parity：只有 null 跑了 full budget，其余场景仍是 smoke 或 `BLOCKED`。这不是最新 dry-run 状态。随后在独立目录 [`full_gate_amendment01_full_dry_02/`](../full_gate_amendment01_full_dry_02/README.md) 对 7 个场景各执行 1 个 world，固定预算均为 128 / 200 / 64；5 个合法场景通过完整文件入口，relative-error 与 nonfinite 按 frozen schema 记录为 `EXPECTED_REJECTION`，并保留 seed / 原始输入 / 拒绝阶段 / 原因。该 follow-up 只验证执行路径与拒绝规范化，不产生可用的 MC rate（每 cell N=1）或物理结论。

amendment01 主 MC 在 595/2814 时因 score-alpha 与 smear-alpha 混用而停止；最后 checkpoint 与原因见 [`full_gate_amendment01_execution_02/RUN_REVIEW.md`](../full_gate_amendment01_execution_02/RUN_REVIEW.md)。该目录 checkpoint 保留为历史原子写入状态，不可恢复或并入修正版。修正版的计划、0.05 full-budget dry-run 与主 MC 分别见 [`amendment02 preregistration`](../full_gate_mc_20261119_v2_amendment_02/README.md)、[`amendment02 dry-run`](../full_gate_amendment02_full_dry_01/README.md) 和 [`amendment02 execution`](../full_gate_amendment02_execution_01/)；此目录的 initial status 仅记录早期版本。
