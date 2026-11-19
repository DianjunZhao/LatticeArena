# optimize_gaussian：本轮四个有限 CPU 验收包

基线：`b3f03a7`，2026-11-19。**保留 todo：原验收仍有有限 CPU 缺口。**
主 agent 本轮运行104个CPU tests通过，23.36s；不是GPU复测证据。
只完成下述四包即可结束本轮CPU工作，负结果和明确的证据缺口均可结项。
真实W训练、新物理样本和多动量路线另列可选研究，不能因未获GPU而无限保留本轮。

## 1. 已关闭项与现有证据

| 已完成 | 证据 | 边界 |
| --- | --- | --- |
| plaquette/link-centred/A1+修复 | `features.py`、专属tests | 不再把旧算子bug列现行待办 |
| 完整BCB线性响应与Hermitian | `audit_20261118_bcb/operator.json`、专属tests | geometry=(3,4,5)，submission/direct最大2.274e-13，Hermitian最大5.684e-14 |
| stale-basis核心身份 | `train.basis_key`及mutation tests | 依赖及gauge/propagator内容摘要已接入；生产metadata可信分流另见包A |
| audit分类与独立输出接口 | `audit.py`、`audit_v2/` | 不是生产重测 |
| 统一point/replica幅度分支 | `unified.py:40–77` | train分支固定同一幅度；不等于全部fit-state可重放 |
| 两组分图与线性候选fold重选 | `cpu_next_package_b/` | 已区分frozen/reselected；reference未认证、无inner CV |
| 独立train/test links的toy产物 | `cpu_next_p3_crosslink/` | 已执行，不再称“只有新probes”；实验对象和公平性未满足原验收 |
| core接口管线演示 | `cpu_next_package_d/` | synthetic toy已接bundle/search，实际BCB闭环另见包D |

目录均相对仓库根，完整证据仍以源码和JSON为准，coverage文字不替代验收。

## 2. 已有物理诊断与覆盖事故

v9训练口径为raw/block2：learned risk=0.0092357620，Gaussian base=0.0196001510，
base/learned=2.122201826。这个2.12×不是相对SLSQP。
fit=0–19、dev_val=20–59、历史test=70–99；后者已反复观察，不再是新盲测。

正式接口folded/block5：SLSQP=0.0077027080，learned=0.0077207899。
R_SLSQP/R_learned=0.9976580312，95%CI=[0.7799244162,1.1756779868]。
只能说未检出差异，不能称等效或优于；reference gate失败仍是条件诊断。
两种统计口径必须分栏。

![v9开发风险](../../results/optimize_gaussian/v9/fig_risk.png)

图为同一数据划分的固定随机W×λ，不是多个数据种子，也未训练W。

覆盖事故：包B README明确记载`unified_v1/`曾被同名输出覆盖。
本仓库git没有可用于恢复该旧目录的已跟踪版本证据；本轮没有搜索外部备份。
因此不声称“全局不可恢复”，但现有旧fold内容不能继续当原始实证。
接受此历史证据缺口，保留事故说明即可，不无限追补。
旧文字数值仅作历史记录；本todo不再引用unified_v1图并赋予旧身份。

![当前冻结权重组](../../results/optimize_gaussian/cpu_next_package_b/fig_folds_frozen.png)

此图是冻结历史权重的诊断，不是fold内重新训练成绩。

![当前fold内重选组](../../results/optimize_gaussian/cpu_next_package_b/fig_folds_reselected.png)

此图对应outer-training内重选，三折H^32，tuned/SLSQP约1.719、2.014、0.810。
不是nested CV或学习核的CV；包B补齐身份后再作为可重放诊断归档。

## 3. 共用执行与停止规则

新输出目录均为**拟议**：`results/optimize_gaussian/cpu_close_<runid>/A|B|C|D/`。
入口必须显式接收新目录，目录存在即拒绝覆盖；不运行默认会写旧结果的脚本。
每包交输入/代码摘要、参数、原始JSON/表及文字解释；必要时交图。
小型identity/残差项可用充分数值文字表代替图。
不得修改旧结果来模拟修复后的结果；按改动范围运行测试，公共接口变化时补跨task集成回归。
尊重共享代码库已有改动，不回退其他agent文件。
资源均为CPU与已有小数据，不能标成GPU依赖。

## 4. 包A：可信输入分流与实际reference身份（P0）

当前：`train.validate_inputs:98–108`缺geometry/boundary等字段会设None，
但仍可能仅由residual/precision授予verified；超残差则降级而非拒绝可信入口。
`reference_identity:115–120`摘要默认reference.npz/nested_bootstrap.npz，
训练实际读取`p['reference_bootstrap']`，消费文件与身份文件可能不同。

动作：

1. 明确可信入口必需字段；缺字段保持archived_diagnostic/unknown，不能verified。
2. 超残差、协议不符等在可信入口拒绝；诊断入口显式接受降级且不出可信成绩。
3. 绑定实际消费的reference/bootstrap文件、模型和来源split，不猜默认邻接文件。
4. 保留旧GPU硬件/精度等unknown，不用当前机器信息补旧档案。

交付：字段/入口分流表、缺字段/超残差/错误bootstrap mutation结果和receipt文字。
验收：可信入口fail-closed；合法输入不误拒绝；实际文件变化使身份变化。
停止：测试闭环即完成，历史缺metadata记录缺失即可，不要求远程补采。

## 5. 包B：可重放CV状态与回归证据同步（P0）

当前分支已修幅度point/replica混用，不重复该修复。
剩余：weights只有hash、scales未存；reference passed来自全run submission，
不是fold级重新计算。可以保留上游gate但必须标真实来源。

回归证据冲突：`regression/regression.json`实际n_dataset=5、n_boot=20，
README却写60×200、coverage=.983。
实际train bias=0.000235942±0.000435224、coverage=1；
test bias=0.000050485±0.000232487、coverage=.95。
不能把相关时间点当独立dataset计算校准强度。

动作：

1. 保存每fold weights/scales、block IDs、mass/reference身份、search预算/失败。
2. gate若来自全run就标upstream gate；若声称fold gate则实际计算并保存。
3. 保持frozen与reselected图/数值分离；无inner选择不称nested CV。
4. README/coverage与实际JSON同步；可将5×20降格为smoke。
5. 以确定性/解析测试验证同算法分支；如另做更多模拟须预设样本数并存新目录。
6. 包B README过期“仍未做”列表同步，不把已交产物反复重做。

交付：fit-state JSON、重放数值表、两组当前图说明、回归设计/限制文字。
验收：保存状态可重放；train/test不混用；没有outer-held-out数据进入训练状态。
训练幅度条件冻结的含义明确；若不传播其不确定性，不宣称完整无条件coverage。
停止：一致性和状态闭环即可；5×20不能作高精度coverage证明，但可接受smoke结论。

## 6. 包C：纠正实验对象与公平CPU 2×2（P1）

现`p3_crosslink.py`确有独立links与2×2执行，但不是原operator class验收。
`63–67`展平矩阵元素，`84`用自由feature-to-output矩阵回归；
这不是共享实标量系数Σc_kH^k，通常不保持gauge covariance。
H是4维plaquette矩阵和，不是空间扩散H；固定平面B未做O_h投影。
oracle为无约束复least-squares，优化器为实参数box，不能以误差差距断言固有优化失败。
两类循环分别抽sites，maxiter相同不等于nfev/时间预算匹配。

现档案eps0/seed0：A SLSQP误差24.8778、Powell31.7211，oracle4.286e-14；
B分别39.4838、50.7639、2.497e-14。success=True不是有效收敛证据。
README nfev上限与JSON172235也有出入，应修正实际范围。

有限修正方案：

1. 用小格点空间扩散H与同一确定gauge-conditioned Hermitian/O_h Q规则。
2. 两类使用相同links/sites/probes；实共享scalar coefficients，新增类严格包含基线。
3. oracle、SLSQP、Powell使用同一实参数域/约束；oracle只作同域可达误差参考。
4. 预先固定少量seed/epsilon/起点和nfev预算；同时报告维数/有效秩与时间。
5. 保存coefficients、可行性、目标值/梯度或最优性残差、失败，不只success。
6. 若不修原复杂模型，则明确降格并拒收其operator-class结论；仍需交上述小CPU验收。

交付：epsilon–test-error图、2×2误差/成本表、属性残差表、原始数据与局限文字。
验收：epsilon=0基本恢复；epsilon>0收益/失败按新links误差如实报告。
给定Q特征只能证明系数迁移，不是学习gauge→Q网络；负结果允许结项。
停止：完成预设有限网格即结束，不因无正收益扩大模型或预算。

## 7. 包D：实际BCB—response—core search闭环（P1）

当前`adapt.py:29–33`为一维roll toy，search evaluate与该kernel不连通。
公共core接口演示可关闭，但尚未满足Gaussian自身端到端适配。

动作：用现有小格点submission和固定W响应，通过MeasurementBundle进入同一SearchAdapter。
评价合成响应与精确BCB结果，OperatorContract检查实际对象；保留NaN/预算/能力拒绝。
不要求真实GPU C_fit，不重造公共框架。
交付：输入/输出字段表、评价差异/残差数值表、预算及拒绝receipt。
验收：同一theta经response与精确kernel评价一致；搜索实际调用该评价。
停止：一个CPU端到端实例通过即关闭，不扩成生产框架重写。

## 8. 可选物理研究移交，不阻碍CPU结项

SLSQP是优化器，强基线是扩散多项式类及其训练流程。
三条可证伪路线保留：嵌套空间修正P_u(H)+Σtheta BQB；wider/Chebyshev/独立path基；
真正训练W的gauge-only系数网络。固定W的C_fit不能学习任意新W。
p(H)共享H本征向量，非对易Q可增加模式方向；是否有真实统计收益尚未证实。
类包含只保证同约束训练global infimum，不保证泛化或有限预算优化。

后续新GPU研究需先固定强谱基、real/uniform/off/shuffled、效应阈值/预算/样本量power。
真实特征优于对称性保持的shuffled才支持局部信息机制；更强谱基解释收益也是有效反证。
新独立物理数据配对CI须与reference/块长敏感性和总成本同时报告。
真实W训练、盲测与多动量little-group协议可延期，不以这些未做无限保留本轮。

四个CPU包逐项验收后，本轮可关闭；删除todo前仅核对原验收，不新增无限研究门槛。
