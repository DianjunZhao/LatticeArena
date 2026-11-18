# LatticeArena 阶段性总结（2026-11-18）

三个任务在 2026-11-18 做了算子修复、契约冻结和 GPU 重测。这一页是索引和结论；
细节都在各自的 task README 与 `results/` 里。

## 0. 一句话

- **`wilson_loop`**：修复核的协变性、扩大系综后，协变 APE **显著优于 identity**（留出分数 263/233/222，
  三个配对区间都不含 1）；
- **`optimize_gaussian`**：修复特征后学习核比高斯基座好 **2.12 倍**，候选 risk 与 7 参数 SLSQP **打平**
  （0.998 [0.78,1.18]）；
- **`pion_projection`**：参考模型仍不可识别，正式 `score` 保持 `null`；GEVP（C2）与能量目标（C3）
  的合成验证已完成，真实数据需要新测量。

## 1. 结果总表

| task | 修复前 | 修复后 | 统计结论 |
| --- | --- | --- | --- |
| wilson_loop | 旧 APE 核不协变，结果作废 | v3：identity 100、APE(0.4,5) **263.3**、APE(0.4,10) 232.8、APE(0.6087,10) 221.9 | 配对中位数 2.8–3.1，95% 区间 [1.17, 6.34] 等，**均不含 1** |
| optimize_gaussian | v7：1.52×，候选 0.009597，输给 SLSQP（0.803 [0.636,0.944]） | v9：**2.12×**，候选 **0.007721** vs SLSQP 0.007703 | 配对 **0.998 [0.78,1.18]**，打平 |
| pion_projection | 参考 gate 未过（χ²=52/8，窗口偏移 21.6σ/7.8σ） | 诊断更完整，参考仍不可识别；C2/C3 合成验证通过 | 无正式分数（设计如此） |

## 2. wilson_loop：静态势

### 修了什么

- 逐列 Gram–Schmidt 只保左酉 → 换成**双边极分解** $Q=M(M^\dagger M)^{-1/2}$，det→1；
  满足 $P(gMh)=gP(M)h$；
- 3 个空间方向只有 4 个 staple → 归一化改为 $\alpha/4$；新旧 $\alpha$ 关系 $2\alpha/(3-\alpha)$；
- NERSC 读取校验 `DATATYPE`/`FLOATING_POINT`（真实值是 `IEEE64LITTLE`）/payload 长度；
- 原子保存、每配置 gauge sha256、kernel/git hash、evaluate 校验 development SHA 与 kernel 参数。

### 三个阶段

| 版本 | 留出 | 结论 |
| --- | --- | --- |
| v1 | 30 / 6 blocks | 核不协变，作废 |
| v2 | 30 / 6 blocks | 点估计 3×，区间跨 1 → 未证明 |
| **v3** | **80 / 16 blocks**（200 组态系综） | **区间不含 1 → 显著** |

### 物理读数

$V(1)$ 几乎不变，$V(3)$ 的误差减半（0.0073 → 0.0034），中心值 0.715 → 0.706。涂抹改善的是
大 $R$ 的信噪比。

详见 [`doc/wilson_loop_v3.md`](wilson_loop_v3.md)。

## 3. optimize_gaussian：学习型 smear

### 修了什么

- `plaquette` 路径闭合（原先第二/三段沿错方向平移，不是规范不变的）；
- 特征改为 **link 中心**平均（每条 link 两侧两个 plaquette）再做对称组合；
- 24 个 proper rotation + parity 的协变测试**全部通过**（A1+ 认证）；
- 训练缓存 identity、run manifest（protocol/W/θ/IDs/缓存 key/依赖 hash）。

### 结果

| 版本 | 特征 | 测试 risk | 相对 $G^8$ | 候选 risk |
| --- | --- | ---: | ---: | ---: |
| v7 | 旧的前向锚点 | 0.012870 | 1.52× | 0.009597 |
| **v9** | **link 中心 A1+** | **0.009236** | **2.12×** | **0.007721** |

与 SLSQP 的配对比值 $0.998\ [0.78,1.18]$，统计上打平。学到的系数从“几乎纯均匀”变成有实质
空间调制（$|v_h|\approx0.13$）。

详见 [`tasks/optimize_gaussian/README.md`](../tasks/optimize_gaussian/README.md)。

## 4. pion_projection：参考的问题

### 证据

| 诊断 | 结果 |
| --- | --- |
| 单 cosh 名义窗口 | $\chi^2=52/\mathrm{dof}=8$，窗口偏移 21.6σ/7.8σ |
| 协方差 | 15 维 vs 12 blocks，秩 ≤ 11，4 个零特征值 |
| 模拟校准 p 值 | 校准本身正确（合成误判率 0%），但名义参考校准后 p≈0 → 模型偏差 |
| T=32 | 参考仍失败；归档反射 z=274.27 是硬编码 T 的假警报（修正后 2.40） |
| 两态 | gate 通过但过拟合（8 参数/12 点，$\chi^2=0.06$）；profile 1σ 宽度 0.04 ≈ 4× bootstrap SE |
| 模型平均 | AIC/BIC 权重退化为两态；候选排序随参考翻转 |

### 已建立的工具

- `reference.py`：参考 spec 冻结（kind + 源码 hash），evaluate/candidate 强制校验；
- `scoring.py`：S1 保守改善证书（Bonferroni + min-over-models）；
- `gevp.py`：C2 GEVP，合成两态恢复 $E_0=0.800\pm0.002$；现有数据的 2×2 Hankel 尝试（$E_0=1.067\pm0.010$）**无平台**，说明 2×2 不足以裁决参考分歧；
- `energy_target.py`：C3 能量误差目标，合成场景下认证/拒绝/无差别行为符合预期。

详见 [`tasks/pion_projection/README.md`](../tasks/pion_projection/README.md) 与
[`doc/pion_gevp_design.md`](pion_gevp_design.md)。

## 5. 负结果清单

| 尝试 | 结果 |
| --- | --- |
| 只拟合形状（pion/学习核） | 目标可被 game，训练损失到 $10^{-24}$，留出不泛化 |
| 严格非负约束（学习核） | 增益被抹掉（0.956×） |
| 逐方向独立系数 | 破坏立方对称，是过拟合 |
| 加长 $T$ 到 32（pion） | 参考仍失败；反射失败是假警报 |
| 模型平均（pion） | 权重退化，不能救参考 |
| 学习核超过 SLSQP | v9 只打平，没有超越 |

## 6. 仍然 NOT_RUN

- pion：真实数据的 C2 多 source 测量（约 4× 反演）、C3 独立 anchor、新盲测；
- wilson：更大 $R$、更多体积/$\beta$、与动力学 QCD 的连接；
- optimize_gaussian：更强的函数类（群平均、多层）或更多数据以图超越 SLSQP。

## 7. 文档与复现索引

| 内容 | 位置 |
| --- | --- |
| 跨任务审计 | [`doc/audit_2026-11-18.md`](audit_2026-11-18.md) |
| wilson v3 结果 | [`doc/wilson_loop_v3.md`](wilson_loop_v3.md) |
| pion GEVP/能量目标设计 | [`doc/pion_gevp_design.md`](pion_gevp_design.md) |
| pion 评分诊断 | [`results/pion_projection/score_diagnostics_v2/`](../results/pion_projection/score_diagnostics_v2/) |
| 学习核记录 | [`tasks/optimize_gaussian/README.md`](../tasks/optimize_gaussian/README.md) |
| 测试 | `PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -q -p no:cacheprovider tests/`（47 项） |
