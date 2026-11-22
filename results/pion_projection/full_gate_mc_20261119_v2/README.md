# Full-gate candidate MC v2：NOT_RUN预注册计划

本目录是独立v2计划；没有向v1追加任何样本，没有生成MC结果或虚构图。

CP95半宽目标≤0.05；对N=1..402、每个k=0..N逐项计算exact Clopper–Pearson，最小N=402，最坏k=201，半宽0.0499650438，区间[0.4500349562,0.5499650438]。每cell需402个独立dev/val世界；7cell总计2814。此目标是逐率marginal精度，不是跨cell同时置信或5%错误率认证。条件认证率按gate通过的实际分母计算，可能仍INCONCLUSIVE，不观察结果后追加。

## 尚未执行的具体原因

生产joint目前要求磁盘run的submission/reference/gate/report完整身份往返。尚无通过parity验收的synthetic run adapter；直接复制一个MC循环会重新引入fold、gate或late_metric不一致。因本轮未可靠完成该adapter，本次明确NOT_RUN，候选功效、假认证、弃权和wrong-state结果均没有观测值。dataset_results.json为空且标n_executed=0。

## 有限实施顺序

1. 建synthetic MeasurementBundle adapter，使用同一数据集内baseline/candidate和共同configuration/block噪声；null两独立通道相同分布，不能复制同一个risk数组。改善场景只降低excited overlap，保留ground和噪声可比条件。
2. 临时新run执行真实develop/evaluate/joint，记录protocol、reference、候选、late_metric、gate artifact、report及源码SHA。用相同索引核对直接纯函数与磁盘入口一致，交adapter_parity.json；mock或重新抄gate不能当该parity证据。
3. 保留full_gate_mc_v1 exact生产gate源码hash；若实现变动必须先更新冻结计划版本，不静默改变v2。先完成一个合法run及错误hash/错metric负例，才运行2814dataset。
4. 每dataset保存scenario/seed、gate各拒绝原因、失败、accepted models、certified条件状态、draw identities、真实谱与候选点值。物理score保持null，wrong-state结构false-pass与条件风险改善分开。
5. 汇总无条件false-certification/power/abstain/failure及有条件认证率，每项k/n和CP95；画带区间candidate_rates.png，给每场景失败/弃权样本文字。任一率未达精度标INCONCLUSIVE，不用reference通过率充当candidate power。

真实anchor/new GPU仍NOT_RUN；本计划不升级任何production physical_score。代码身份和固定seed、场景、样本数见preregistration.json。输出目录拒覆盖；实际执行应另建v2_execution目录并引用本计划hash。
