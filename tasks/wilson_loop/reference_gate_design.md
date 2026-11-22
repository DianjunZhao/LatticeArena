# D-chain reference/window gate：定义缺口与可复现提案

**状态：`PROPOSAL_NOT_FROZEN`；`production_execution=NOT_RUN`；`physical_score=null`。**

本文件只定义待冻结的分析方法及 synthetic 测试，不读取生产数据，不改变现有协议、测量源码或运行中的作业。`reference_max_window_z=2.5` 是给定阈值；不得沿用旧 toy 图的 3.0。完整 production gate 的语义尚不能从现有冻结文件唯一恢复，因此本提案不能授权 validation、生产 score 或 shared-holdout 解封。

## 1. 原始文件已经确定什么

- `protocol_d_20261120.json:21–31,47–52`：development D0–99，block length 5，5000 bootstrap draws，seed 2026112021，R=1,2,3,4，T=4,…,8；窗口 `[4,5,6]`、`[4,5,6,7]`、`[5,6,7,8]`，nominal index=1；window-z 阈值2.5。
- `experiment.py:48–55`：现有 gate 仅检查 nominal 势正值及 `spread/V <= 0.05`；没有使用 window-z。
- `doc/finite_nt_scope.md:25–39`、`spectral_physical.py:38–49`：历史诊断以相同 bootstrap draws 上的窗口差标准差作为分母；对 nominal 比较。旧独立-SE合成不能替代该相关分母。
- `spectral_physical.py:30–43,60,72`：历史实现只有一个R、500 draws/seed11、零分母变NaN，再用 `nanmax` 画图，诊断线3.0。它没有定义D的全R生产门。
- `core/stats.py:5–12`：连续完整blocks、至少3块、禁止丢余数；`default_rng(seed).integers` 生成有放回等长bootstrap索引。
- `statistics.py:6–11,14–37`：先对Wilson loops取ensemble/block-bootstrap均值，再取log做无权线性斜率；不是先对每配置势取均值。

上述资料支持逐窗口配对SE公式，**没有唯一确定**对全R/窗口的联合聚合、零/近零分母、无效draw策略、等号边界、是否用max统计量的bootstrap分位数。将这些补入生产gate是新的分析定义，必须有独立冻结及hash，不可回填原RunSpec。

## 2. 共同的数据流与公式

以下是候选A/B/C共同的可复现约定提案；在采纳前仍属于本提案。只对完整授权development的identity核计算reference gate。候选核可同图作诊断，不得从候选中挑一个替代identity reference。

输入 `W[c,r,t]` 为identity实Wilson-loop估计，格点单位、轴序`(configuration,R,T)`。100个配置按递增保存序号分为20个连续长度5的block，记block均值为 `X[j,r,t]`。保留并核对原始ID/trajectory顺序，不能按plaquette重排。复数、缺行、额外ID、非有限值或轴标签不匹配须先拒绝；不能静默丢虚部或丢配置。这里不要求每个配置W为正，但用于log的点均值及每个bootstrap均值必须严格为正。

取唯一索引矩阵 `I[b,j]`，shape `(5000,20)`，由 `bootstrap_indices(20,5000,2026112021)` 生成，保存整数矩阵及其hash。每个draw的同一行索引同时作用于**所有R、T和窗口**：

\[
\bar W_{rt}=\frac1{20}\sum_jX_{jrt},\qquad
\bar W^{(b)}_{rt}=\frac1{20}\sum_jX_{I_{bj},rt}.
\]

对窗口`w`，令 `x_t=t-mean(w)`，按当前`potential`计算

\[
\hat V_{rw}=-\frac{\sum_{t\in w}x_t\log\bar W_{rt}}{\sum_{t\in w}x_t^2},\quad
V^{(b)}_{rw}=-\frac{\sum_{t\in w}x_t\log\bar W^{(b)}_{rt}}{\sum_{t\in w}x_t^2}.
\]

名义窗口`n=1`。定义 `d[r,w]=Vhat[r,w]-Vhat[r,n]`、`D[b,r,w]=Vboot[b,r,w]-Vboot[b,r,n]`。

\[
s_{rw}=\operatorname{std}_{b}(D_{brw};\mathrm{ddof}=1),\quad
z_{rw}=d_{rw}/s_{rw}.
\]

分子使用原始样本均值的势差；不能静默换成bootstrap势差均值。分母是bootstrap估计分布的SD，**不再除以`\sqrt{5000}`**。不要用 `sqrt(SE_w^2+SE_n^2)`，因为 `s²=SE_w²+SE_n²-2Cov(V_w,V_n)`。nominal与自身的对比是结构性0/0，必须从对比集合排除，另记为`structural_nominal`。

## 3. 尚须选择的候选定义及影响

| 候选 | 统计量与给定2.5的比较 | 影响/尚缺定义 |
|---|---|---|
| A：对nominal的point-max | `M=max_{R,w!=n} abs(z[r,w])`；`M<=2.5`才通过 | 与历史逐窗口公式最接近；4R×2窗口共8个相关对比。阈值2.5的联合误拒率没有由此校准，不能声称5% family-wise控制。 |
| B：所有窗口对的point-max | 每个`w<v`用同draw差的SD标准化，再对4R×3对取max；与2.5比较 | 加入两个非nominal窗口之间的比较；这对的差可能大于nominal两侧差，但协方差可让标准误也改变，因此不能简单由A推出B；可能改变门结论。 |
| C：bootstrap-max分位数 | 沿用A的对比，构造每draw `M_b=max abs(D[b,r,w]/s[r,w])`；例如比较`q0.95(M_b)<=2.5` | 要求整个估计分布高分位也处于阈值内，通常比point-max严格；0.95、quantile方法及是否居中均未在RunSpec冻结。不能将该例当成已有含义。 |

不能把候选A称为“原生产gate”。本文件的CPU测试仅验证A的数学及错误处理，未选择生产解释。

如果计算bootstrap-max，必须**先对每个draw的完整R/窗口向量取max，再统计这些max的分布**；不能对各单项分位数取max，也不能为每个窗口/R另抽索引。无中心版本的 `M_b` 衡量不确定性加观测漂移；居中版本

\[
M_b^{0}=\max_{r,w\ne n}\left|\frac{D_{brw}-\overline D_{rw}}{s_{rw}}\right|
\]

用于模拟零漂移噪声的联合结构，与无中心版本不同。`q0.95(M_b^0)`和 `mean(M_b^0>=M)`可以报告为未经coverage校准的diagnostic；不能当作预冻结p值。另对每draw估计自身SE是studentized/nested bootstrap新方法，需要新的inner draws/budget，不能冒充上式。

## 4. 失败、边界与状态（提案）

1. `FAIL_INPUT_INTEGRITY`：ID/source/hash/shape/axis/commit不符；不计算gate。完整100配置未到为`NOT_READY`，不能用前缀补足抽样。
2. `INVALID_ESTIMATOR`：任一必需点均值或任何draw的均值非有限/非正、势差非有限。记录完整失败mask和计数，**不丢失败draw后在不同R上凑不同样本**。当前提案采用任何失败draw即弃权；不能擅自引入5%豁免。
3. `ABSTAIN_DEGENERATE_SE`：除结构性nominal外，任何所需`s`为0/非有限。即使观测差同时为0，也不强行置`z=0`获得PASS。可将无噪声解析等窗另设deterministic规则，但须另行冻结。
4. 近零分母提案：对每个对比令 `S=max(1,max(abs(Vboot_w)),max(abs(Vboot_n)),abs(Vhat_w),abs(Vhat_n))`，`s_floor=64*eps_float64*S`；`s<=s_floor`弃权，保留`s`、floor及ratio。该数值floor **不是RunSpec既有参数**，64及尺度都须冻结；不允许clip分母到floor后继续给PASS。格点单位是此绝对floor中1的必要条件。
5. 有效统计量若`M>2.5`，记`REJECT_WINDOW_INSTABILITY`；`M<=2.5`记`PROPOSAL_DIAGNOSTIC_PASS`。等号通过仅是当前测试约定，必须在采纳时冻结；报告阈值margin及float64原始值，不用四舍五入后的2.50裁决。
6. point-max通过还要满足既有正势/spread门及所有identity/numerical/statistical证据；**不产生生产PASS/score**。共同窗口偏差仍可使所有窗口同时错而彼此一致；window-z不是基态无偏性或equilibrium证明。

## 5. 冻结、receipt与hash

任何未来生产执行先写独立analysis plan，状态为`FROZEN_ANALYSIS_AMENDMENT`，关联原RunSpec文件hash，不覆盖其内容；明确A/B/C、比较集合、最大值顺序、分子、`ddof`、center、quantile方法、denominator floor、无效draw/等号政策和阈值2.5。若仍无法唯一确认原意，保持`PROPOSAL_NOT_FROZEN`并停止validation升级。

新receipt至少包含：

- `schema/version/status/created_utc`；`analysis_plan_sha256`、本设计文档及focused tests的bytes hash；`original_runspec_sha256`及原RunSpec source-hash map。
- 输入development NPZ、provenance、commit marker的bytes hash及generation；identity kernel名称、明确split与完整ID/trajectory列表、manifest bytes hash。禁止把仅存在路径当作身份。
- 实际使用的analysis实现、`statistics.py`、`core/stats.py`、`common.py`、`identity.py`及测试文件bytes hash；源码是否等于原RunSpec绑定值；Git commit/dirty仅补充，不能替代bytes hash。
- Python/NumPy版本、dtype、平台；索引生成器/seed/shape、原始索引文件及hash；输入axis/window/R/T顺序；block定义及数量、无丢行声明。
- 每个对比的point势/差、bootstrap均值差、SE/covariance、分母floor、signed/absolute z、有效/失败draw计数、失败mask/原因；`M/argmax/ties`、2.5及margin、居中/无中心max分布的独立标签。
- 既有gate各项结果与新proposal gate分开；`production_score=null`、`validation_accessed=false`、`holdout_accessed=false`；不能把文档/测试hash当作production execution证据。

运行中的原测量receipt保持原样，新receipt通过hash引用它。20个validation配置的信息量限制不会因新增gate而消失。

## 6. 参考窗口图与文字报告字段

未来仅在完整授权development到位后输出：

1. `reference_windows.png`：四R面板，三个窗口的point势、各自bootstrap SD、标明nominal；副面板显示**配对差SD**误差条，不能用两个独立SE拼接。
2. `reference_window_z.png`：R×非nominal窗口的signed-z热图、±2.5标识、max及argmax；退化/失败格用显式mask，不用`nanmax`悄悄忽略。
3. `reference_joint_max.png`：仅在plan冻结后展示相同draw下的joint-max分布；居中/无中心区分，point-max、2.5和分位数分别标注；图注明“未经family-wise calibration”。
4. `reference_window_rows.csv`、`reference_failures.csv`、receipt JSON及`REFERENCE_REPORT.md`：输入/代码hash、方法版本、独立block数/有效draw数、每对比数值、门边界、失败/弃权、既有门与proposal门差异、共同偏差反例限制和下一步条件。没有生产输入时只给模板，不生成假生产图。

## 7. 本次CPU验证及适用边界

`tests/test_wilson_reference_gate_design.py` 是测试内局部实现，**不导入生产测量，不连接gate**。覆盖候选A通过/拒绝、跨R最坏项、exact2.5边界、同draw配对协方差、draw内joint-max、零/近零分母、NaN和nominal结构项；另外从synthetic block loops计算真实窗口势再进入该代数。测试成功只证明提案公式实现自洽，不证明阈值有统计coverage、没有共同偏差或生产gate已启用。

复跑：`PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest -q -p no:cacheprovider tests/test_wilson_reference_gate_design.py`。

本次实际执行该命令：**9 passed in 0.07s**。没有生产输入、生产gate执行、GPU或validation测试；没有生成生产参考图。通过与拒绝示例仅为synthetic单指数扰动/确定性曲率及显式bootstrap势数组。

## 8. 现有独立CPU计算模块（仍未冻结）

`reference_gate_diagnostic.window_gate_proposals(identity_loops, windows=..., t_values=..., nominal=1, block_length=5, bootstrap_samples=5000, seed=2026112021)`仅接收内存中实identity loops `(nconfig,nR,nT)`，没有文件、GPU、split、生产gate或RunSpec操作。调用者必须事先确认完整授权development身份；纯计算函数不能证明输入属于哪个split，也不自动认证100配置的生产完整性。它复用`statistics.potential`与`core.stats`，返回可JSON序列化的字典：

- `status=PROPOSAL_NOT_FROZEN`、`scope=development_diagnostic_only`、`production_score=null`，给定阈值2.5仅作候选展示。
- `A/B.contrasts`逐R/窗口对记录point差、paired SD、64eps分母floor、signed z、有效/失败draw数与失败draw索引。`window_mean_diagnostics`进一步区分非有限均值和非正均值。任一必需失败draw/分母使整组比较`ABSTAIN`，不会删除draw估计条件SD。
- A的nominal contrasts、B的all-pair contrasts，及C在A contrasts上先逐draw取联合max的`centered/uncentered.q95`和各自候选结论；C固定报告0.95/linear仅是本提案敏感性。C居中使用bootstrap差均值；SD使用ddof=1，不增加inner bootstrap。
- 实际block/bootstrap参数、原始索引矩阵与其canonical little-endian int64 bytes SHA；`point_potentials`、`comparison_status`。上层可据此生成CSV/图，但函数本身不写产物。

该模块实现完整A/B/C对照的CPU数学，不实现或选择生产门。新receipt仍须由未来独立runner绑定模块、依赖、analysis plan及完整输入三件套的bytes hashes，并保存索引矩阵；本函数返回值不能替代这些收据。形状、标签、参数错误抛`ValueError`；数值未定义返回弃权原因。相同窗口无噪声也会因退化SE弃权，不自动获得PASS。

`tests/test_wilson_reference_gate_diagnostic.py`仅使用synthetic loops/势数组，检验A/B以及A/C可能给出不同候选结论、同draw相关分母、全R联合max、精确2.5边界、失败与退化、索引复现及严格JSON输出。连同原设计tests，实际CPU复跑为**22 passed**。不读取真实split、不生成生产分数。复跑命令：`PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest -q -p no:cacheprovider tests/test_wilson_reference_gate_diagnostic.py tests/test_wilson_reference_gate_design.py`。

## 9. 共同偏移的不可识别性（解析诊断；不是生产结论）

窗口一致性只能检验窗口之间的相对漂移，不能排除所有窗口共有的势偏移。设原始逐配置 Wilson loop 为 `W_c(R,T)>0`，构造共同乘法偏差

\[
W'_c(R,T)=e^{-\delta T}W_c(R,T),
\]

其中同一个常数 `\delta` 作用于所有配置、R 和 T。对任一 T 窗口，ensemble mean 及每一个共用 bootstrap draw 都乘上同一个 `e^{-\delta T}`。因此 log-linear slope 满足

\[
V'_w(R)=V_w(R)+\delta,\qquad
V'_w(R)-V'_v(R)=V_w(R)-V_v(R).
\]

bootstrap 配对差、其标准差与 `z` 也完全不变。故候选 A、B、C 的窗口统计量及其任何 family-wise 校准都不能检出这个共同模式：它们可对所有窗口漂移给出相同的 PASS，而逐窗口势实际整体移动了 `\delta`。这是一种解析上的观测等价，不是 bootstrap 次数少或阈值选择不佳；单纯增加同一统计量的 draws、调整 2.5 或改用 max-t 不能解决。

**图文诊断**：把窗口势写成三条曲线 `V_w(R)`，共同偏差后每条曲线整体竖直平移 `\delta`；任意两条曲线间的垂直差、误差条和 z 值保持原样。`reference_windows.png` 的绝对势面板会显示共同平移，但其窗口差/稳定性内容不变；`reference_window_z.png` 与 `reference_joint_max.png` 对该变换完全不变。若没有独立物理锚点，图上能看到整体位移，却不能判定原曲线或平移后的曲线哪一条更接近真值。这段等式本身是可复核的文本诊断；没有生成合成或生产数值图，也没有声称已经实施代码测试。

**对后续方案的约束**：把“从同一组 T 窗口识别共同偏差”从内部统计量的目标中移除。A/B/C 至多成为经校准的内部稳定性诊断，不足以产生物理 reference PASS 或 `physical_score`。若要恢复物理解释，需先明确一个不由同一组窗口定义、且有独立偏差论证的锚定量/方法，并说明共享配置相关性与共同失效模式；若研究问题只依赖势差或静态力等对加性常数不敏感的量，则应改写 estimand 并重新冻结对应 score。第二个算符、APE/stout 核、同一数据上的额外拟合或独立 bootstrap 本身都不自动构成无偏真值。找不到可辩护外锚时，状态应维持 `REFERENCE_UNIDENTIFIABLE` / `physical_score=null`。

## 10. 候选替代 estimand：离散静态力（待研究者选择）

若科学目标允许放弃绝对势，可考虑改报 lattice-unit 离散力

\[
F_{R+1/2}^{(w)}=V_w(R+1)-V_w(R),
\]

其中两个势必须来自同一 T 窗口、同一 bootstrap draw 和同一配置块。对上节的共同偏移 `V'_w(R)=V_w(R)+\delta`，有 `F'_{R+1/2}=F_{R+1/2}`；这正好消掉所有 R 相同的加性常数。等价的单指数极限量是 Creutz ratio

\[
\chi(R,T)=-\log\frac{W(R+1,T+1)W(R,T)}{W(R+1,T)W(R,T+1)}
\longrightarrow V(R+1)-V(R),
\]

但有限 T 的激发态、有限格距效应及相邻 Wilson loop 的相关性仍需处理。这个定义只能给出格点单位的离散力；物理单位和连续极限还需格距标定及多格距控制。

它提供的是一个**改写后的目标量**，不自动建立真值：随 R 变化的共同偏差、窗口曲率、有限 T 污染、action/体积效应都可能留下；candidate 与 identity 仍共享同一 gauge ensemble。若采用该目标，最低限度 CPU 方法诊断应使用相同 block/bootstrap 索引，构造已知 `R`-独立 `\delta`（应严格不改变力）与已知 `R`-依赖偏差（应被显式检出）两类负控；逐 R 配对画出 force shift、SE、候选间差和失败/弃权率，并对所有 `(R,T-window,kernel)` 比较族校准。仅有第一个负控通过时，可称“对共同加性偏移不变”，不能称“识别了绝对势”或“认证了 ground state”。

当前 production protocol 固定以 `V(R)` 为目标，故本节不是对既有 protocol 的修改，也不是评分授权。若必须保留绝对势，需选择外部锚和可审计偏差界；若研究者接受离散力 estimand，须冻结新 protocol、拟合/Creutz estimator、block策略、比较族、门槛与单位报告，再考虑新的测量或 validation。
