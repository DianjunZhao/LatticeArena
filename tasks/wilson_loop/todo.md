# wilson_loop：有限-T Creutz 与基态静态力

## 用户已确定

并行保留两种 estimand：

- 有限温度 Creutz observable `chi_k(R,T)`；
- 基态离散静态力 `f0(R+1/2)=U0(R+1)-U0(R)`。

当前维持 `NOT_READY/UNCERTIFIED`、`GROUND_STATE_FORCE_UNCERTIFIED` 与 `physical_score=null`。不得访问 gap、validation 或 shared holdout，不启动 GPU/QUDA。

## 尚未闭合的研究边界

1. **有限-T lane：**冻结 primary kernel、`R/T` 网格、正值/log 失败处理、比较族、多重性与可接受精度。有限-T 的候选差值应按有限-T observable 解释，不自动升级为基态改善。
2. **基态力 lane：**给出可审计的激发态 overlap/能隙界，以及有限 `N_t` 热迹和混合项界；把污染界传播到离散 `Delta_R Delta_T` 静态力，并与事前系统误差预算比较。
3. **离散化与有限体积：**冻结格距、体积和静态源约定；说明哪些误差由当前 estimand 保留，哪些需要后续外推。
4. **新证据：**只有在方案经审阅并另行授权后，才设计独立谱或 matched-`N_t` 测量；开发数据不得再用于选择确认性 `R/T/kernel`。
5. **报告：**两条 lane 分开列 paired 区间、planned/valid/failed/abstained 分母、失败原因、图或可复查文字及各自的适用范围。

有限温度拟合精度或窗口稳定性本身不能认证基态力。若污染界不可识别，继续报告 `GROUND_STATE_FORCE_UNCERTIFIED`，不把有限-T结果重命名为基态结果。
