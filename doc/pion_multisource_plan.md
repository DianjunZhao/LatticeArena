# pion_projection：多 source GEVP 的预注册方案（未执行）

C2 的 2×2 和 3×3 Hankel GEVP 都失败了（`doc/pion_gevp_design.md` §2.5–2.6）：powers-of-$H$
家族彼此高度相关，补一个 $H^{24}$ 也换不来独立的算符方向。本文把“多 source 测量”写成
可执行的预注册方案，**尚未提交任何 GPU 任务**。

## 1. 为什么需要多 source

Hankel 构造依赖

$$
C_{ij}(t)=\langle K_iS,K_jS\rangle=\langle S,H^{n_i+n_j}S\rangle,
$$

所有通道都来自**同一个点源**，只是 sink 不同；矩阵的秩由 $S$ 的谱决定，而不是由独立的算符
方向决定。要得到真正的 GEVP 矩阵，source 侧也必须是不同的算符：

$$
C_{ij}(t)=\langle O_i(t)\,O_j^\dagger(0)\rangle,
\qquad O_i=\bar q\,\Gamma K_i q .
$$

## 2. 测量方案

### 2.1 source 集合

| 编号 | source | PyQUDA 入口（待核对签名） |
| --- | --- | --- |
| 0 | point | `source.source(latt, 'point', ...)`（现有） |
| 1 | Gaussian, $H^4$ 等效 | `source.gaussian12` / `source.gaussianSmear` |
| 2 | Gaussian, $H^{16}$ 等效 | 同上，steps 更大 |
| 3（可选） | wall | `source.wall` |

建议先做 $N_s=2$（point + Gaussian）验证可行性，再扩到 $N_s=3$。

### 2.2 每个配置的流程

1. 对每个 source $j$：构造源场 $\rho_j$（保存其空间剖面），做一次反演得到 $S_j$；
2. 对每个 sink $i$：把 $K_i$ 作用到 $S_j$ 上，与 $\rho_j$ 收缩，得到 $C_{ij}(t)$；
3. 存成新的数组 `correlators_ij.npz`，shape `(nsrc, nsink, T)`，**不改动现有 NPZ**；
4. 记录每个 source 的 hash、反演残差、耗时。

### 2.3 成本

- 反演：$N_s$ 次/配置（现在是 1 次）→ $N_s=2$ 约 2×，$N_s=3$ 约 3×；
- 收缩：$N_s\times N_k$ 次 kernel 应用（现在 $N_k$ 次）；
- 60 开发 + 30 留出、$N_k=7$、$N_s=3$：约 **50–70 分钟** GPU（现有单 source 约 20 分钟）。

## 3. 预注册项

- source 集合与 $N_s$、sink 集合与 $N_k$；
- $t_0$（建议 2 或 3）与 $E_0$ 平台窗口（建议 $t=4\dots8$，取最后三点）；
- bootstrap：按 configuration block（长度 5）重采样，GEVP 在每个 draw 内重解；
- 失败判据：
  - $C(t_0)$ 非正定或条件数 > $10^{10}$；
  - 本征值在 draw 间排序交换超过 5%；
  - $t_0$ 从 2 改到 3 使 $E_0$ 移动 > 2σ；
  - $E_0(t)$ 在平台窗口内漂移 > 2σ。
- 若失败：输出“GEVP 不可识别”，不发布能量。

## 4. 与现有评分的关系

- 这个测量只增加通道，不改变 $\kappa$、几何、splits 或统计；
- 新的 GEVP 参考若通过预注册的门，可以替换 `reference.py` 里的单 cosh/两态，成为
  `references` 集合的第三个模型；
- 在它通过之前，pion 的正式 score 保持 `null`。

## 5. 状态

**NOT_RUN**：需要新的 GPU 测量与 `measure.py` 的 source 扩展。本文只固定方案与判据，
不包含执行结果。
