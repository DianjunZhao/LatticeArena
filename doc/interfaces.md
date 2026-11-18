# 公共接口（F1，第 1–2 类切片）

已实现：`core/specs.py`（校验）+ 两个 task 的 spec adapter。**第 3–5 类接口（MeasurementProvider、
ReferenceProvider/Metric、SearchAdapter）仍未抽取**，任务仍直接调用现有实现。

## 1. TaskSpec / RunSpec

字段：`name / observable / geometry / boundary / source / splits / reference / metric / budget / dependencies`。

校验：

- geometry 必须是四个正整数；
- splits 必须声明 `development` 与 `validation`；
- dependencies 是 name→hash 映射。

`run_spec(task, protocol_hash, data)` 绑定一次运行的协议与数据 hash，不做注册表。

适配器：

- `tasks/pion_projection/spec.py`：`task_spec_for(protocol, reference_kind, protocol_path)`、
  `operator_contract_for()`；
- `tasks/wilson_loop/spec.py`：同样的两个函数。

两个 adapter 的 geometry、splits、kernels/statistics hash 都直接来自各自的协议与源码，测试保证与协议一致。

## 2. OperatorContract / CandidateSpec

字段：`name / axes / dtype / transformation / support / parameters / dependencies / constraints`。

允许的 axes（当前实现用到四种）：

- `(mu,t,z,y,x,3,3)`：wilson 的 link；
- `(3,z,y,x,3,3)`：pion 的空间 link；
- `(z,y,x,3,nrhs)`：pion 的费米子场；
- `(t,z,y,x,4,4,3,3)`：传播子（lexico）。

`transformation ∈ {gauge_covariant, gauge_invariant, spin_scalar}`，
`support ∈ {spacetime_local, time_slice, point}`。
`candidate_spec(builder, parameters, contract, dependencies)` 只接受已声明的 contract 名。

## 3. 两个 task 的 contract

| task | name | axes | transformation | support |
| --- | --- | --- | --- | --- |
| pion | `pion-kernel-v1` | `(z,y,x,3,nrhs)` | spin_scalar | time_slice |
| wilson | `wilson-kernel-v1` | `(mu,t,z,y,x,3,3)` | gauge_covariant | spacetime_local |

## 4. 未做（NOT_RUN）

- MeasurementProvider/Bundle（声明 linear_response / cross_matrix / new_source 能力）；
- ReferenceProvider/Metric/Comparator（共享 draw ID 与 baseline 身份）；
- SearchAdapter（optimizer 与 LLM 的统一候选、预算与 evaluator）；
- 跨 task 的缓存失效反例与统计一致性报告。

## 5. 测试

`tests/test_specs.py`：

- TaskSpec 缺字段/几何/splits 报错；
- OperatorContract 的 axes/transformation 白名单；
- CandidateSpec 的 builder 格式与 contract 名；
- 两个 adapter 与各自协议的 geometry/splits/hash 一致。
