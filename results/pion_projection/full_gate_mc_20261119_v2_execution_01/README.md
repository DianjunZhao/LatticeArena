# v2执行前检查：NOT_RUN，0/2814 worlds

原v1、v2计划、adapter parity目录未覆盖。本目录仅记录执行前阻塞，不是Monte Carlo结果；没有candidate-rate图或虚构CP区间。

## 明确的实现冲突

1. 冻结计划定义basis channel1作baseline、channel2作null/improved候选。通过parity的adapter实际调用production develop，它输出local(channel0)、tuned、SLSQP。直接执行会测量不同estimand，null下SLSQP搜索收益不能冒充channel1/channel2假认证率。
2. adapter只有null生成器路径，没有七场景接口或独立冻结的candidate noise/overlap生成规则；wrong-state需要不同候选污染，不能复用相同数组ratio=1的退化实验。
3. adapter预算reference32/outer4/inner8是程序parity smoke；冻结计划要求128/200/64，且现有execute接口不接受这些预算。主MC不能以smoke预算执行后仍标计划一致。

各计划源码的hash核查、当前adapter hash、计划hash及每cell零执行计数详见dataset_results.json；若存在源码漂移也列为独立阻塞。

## 最小下一步

实现显式SyntheticRunSpec：候选basis定义、七场景生成参数、120/60配置、shared noise结构、128/200/64预算与固定seed，先做一个完整预算的合法文件入口parity。production develop目前没有该固定basis1-vs-basis2提交接口；应由同一开发冻结逻辑支持显式候选集，并补固定候选/优化候选名称与预算的身份绑定，不能落盘后手工改submission伪装原冻结。

这需要受控扩展adapter/开发接口，而不是扩大MC样本；变更任何冻结源码前，应形成v2计划amendment及新hash并明确保留原计划。合法路径与七场景parity完成后再在新execution目录运行，不向本目录或旧计划追加观测。reference接受率、candidate power、wrong-state structural pass、false certification、abstain和failure届时分别统计。

当前NOT_RUN而非已运行结果INCONCLUSIVE；真实anchor/GPU仍NOT_RUN，physical_score=null。
