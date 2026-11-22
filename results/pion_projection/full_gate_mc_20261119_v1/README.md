# 完整生产reference gate的CPU MC诊断

每cell 100独立dataset，128配对bootstrap；先写preregistration再执行。
生产develop的全部gate语句按原文提取执行，包含χ²、paired窗口漂移、相对SE、边界与反射；不是χ²子门。
单态模型/窗口固定；不含候选优化或真实anchor，因此没有physical score。known_improvement仅检查参考接受率，不是candidate检验功效。
wrong_state通过是结构假通过：可拟合的纯激发态无法由这些gate认证为基态。

|场景|pass|abstain|failure|pass CP95|精度|
|---|---:|---:|---:|---|---|
|null|87/100|13/100|0/100|[0.7879593229125502, 0.9289269538145705]|PASS|
|known_improvement|80/100|20/100|0/100|[0.7081573109113719, 0.8733444478980441]|PASS|
|window_mismatch|0/100|100/100|0/100|[0.0, 0.03621669264517641]|PASS|
|reflection|0/100|100/100|0/100|[0.0, 0.03621669264517641]|PASS|
|relative_error|47/100|53/100|0/100|[0.3694051641943945, 0.5724185151099548]|INCONCLUSIVE|
|wrong_state|80/100|20/100|0/100|[0.7081573109113719, 0.8733444478980441]|PASS|
|nonfinite|0/100|100/100|100/100|[0.0, 0.03621669264517641]|PASS|

![rates](full_gate_rates.png)

## 失败/弃权样本
- null: dataset=10 seed=20261129 ['Reference window [6, 7, 8] shifts by 2.86 paired standard errors']；dataset=22 seed=20261141 ['Nominal correlated reference fit fails the approximate goodness-of-fit gate']
- known_improvement: dataset=9 seed=20361128 ['Reference window [6, 7, 8] shifts by 2.80 paired standard errors']；dataset=11 seed=20361130 ['Forward/backward symmetry check exceeds the fixed z threshold']
- window_mismatch: dataset=0 seed=20461119 ['Nominal correlated reference fit fails the approximate goodness-of-fit gate', 'Reference window [4, 5, 6, 7, 8] shifts by 38.24 paired standard errors', 'Reference window [6, 7, 8] shifts by 22.29 paired standard errors']；dataset=1 seed=20461120 ['Nominal correlated reference fit fails the approximate goodness-of-fit gate', 'Reference window [4, 5, 6, 7, 8] shifts by 53.29 paired standard errors', 'Reference window [6, 7, 8] shifts by 20.39 paired standard errors']
- reflection: dataset=0 seed=20561119 ['Nominal correlated reference fit fails the approximate goodness-of-fit gate', 'Reference window [4, 5, 6, 7, 8] shifts by 13.32 paired standard errors', 'Reference window [6, 7, 8] shifts by 27.99 paired standard errors', 'Forward/backward symmetry check exceeds the fixed z threshold']；dataset=1 seed=20561120 ['Nominal correlated reference fit fails the approximate goodness-of-fit gate', 'Reference window [4, 5, 6, 7, 8] shifts by 20.88 paired standard errors', 'Reference window [6, 7, 8] shifts by 15.54 paired standard errors', 'Forward/backward symmetry check exceeds the fixed z threshold']
- relative_error: dataset=0 seed=20661119 ['Reference mass relative uncertainty exceeds 5%']；dataset=4 seed=20661123 ['Reference window [4, 5, 6, 7, 8] shifts by 4.89 paired standard errors']
- wrong_state: dataset=0 seed=20761119 ['Nominal correlated reference fit fails the approximate goodness-of-fit gate', 'Reference window [6, 7, 8] shifts by 3.73 paired standard errors']；dataset=5 seed=20761124 ['Reference window [6, 7, 8] shifts by 2.55 paired standard errors']
- nonfinite: dataset=0 seed=20861119 ['ValueError: nonfinite correlator']；dataset=1 seed=20861120 ['ValueError: nonfinite correlator']

## 解释与限制
null/known_improvement的pass是接受率；window/reflection/relative-error的abstain是检测功效；wrong-state的pass是结构false-pass。失败是abstain子集，不能相加。
相对误差场景可同时触发其他门，reason_counts给出各原因；不假装各场景只操纵一个统计量。
CP区间按独立dataset计，bootstrap次数不是独立样本量。任何半宽未达0.10的率为INCONCLUSIVE，不因观察结果追加样本。
生产软件路径复用通过源码段提取确保判据一致；源码hash绑定并在结构变化时失败。后续可独立重构为共享纯函数。
真实anchor、新GPU/集群测量仍NOT_RUN；此实验不升级production physical_score。

## 可复现命令与逐例诊断

```sh
PYTHONDONTWRITEBYTECODE=1 python -B -m tasks.pion_projection.full_gate_mc --dest results/pion_projection/full_gate_mc_<fresh_id> --datasets 100 --bootstrap 128
```

输出目录必须不存在；相同输入/seed/代码应重现全部dataset。输入是本模块冻结的合成生成器及protocol，不读取生产gauge/propagator。完整protocol、module与生产develop源码hash见preregistration.json。

- null拒绝13/100：晚窗漂移5次、早窗2次、χ²4次、反射5次；原因可重叠。这是完整多门组合拒绝率，不能简单拿单个1%χ²阈值当其名义总体水平。
- known_improvement与null的参考生成分布相同，仅独立seed；80/100不是“改善检出功效”，因为gate不读取候选。本实验拒绝借用候选改善名义认证reference。
- window_mismatch的100次拒绝均含χ²与两个窗口漂移；该污染被完整gate稳定发现，但不能外推所有gap/overlap。
- reflection的100次均触发反射门，同时污染折叠形状并触发其他门；这是联合故障情景，不声称单独识别因果。
- relative_error触发相对SE门38/100，任意门53/100；其pass CP95=[0.369405,0.572419]，半宽0.101507>0.10，INCONCLUSIVE。
- wrong_state为纯E1=1.5，80/100通过；证明统计拟合/稳定性门无法认证未耦合的E0=.8。必须依靠独立物理anchor或明确只作条件诊断。
- nonfinite全部输入拒绝；failure计数100也是abstain的子集，不能重复计算为200次失败。

新增针对实际生产反射判据和CP边界的CPU回归：`tests/test_pion_full_gate_mc.py`，1 passed（0.52s）。MC精度PASS仅指预注册区间宽度，不指物理模型正确或gate质量通过。
