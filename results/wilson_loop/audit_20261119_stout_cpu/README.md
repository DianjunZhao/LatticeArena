# 纯空间 stout：CPU small-gauge 契约

冻结定义：每条空间link四个同时间片staples，Cμ=ρΣstaples（不除4）；Ωμ=CμUμ†，Qμ=(Ωμ−Ωμ†)/(2i)−I Tr[(Ωμ−Ωμ†)/(2i)]/3，U′μ=exp(iQμ)Uμ。所有方向同步更新，ρ是每staple权重，不能等同APE α。矩阵指数用Hermitian eigh，未做额外SU3投影。来源方法为Morningstar–Peardon stout；本实现只支持NumPy complex128 CPU。

输入shape=(3,t,z,y,x,3,3)，d=0,1,2对应x,y,z（axis=3−d），周期空间边界。Uμ(x)→G(x)Uμ(x)G†(x+μ)，因此C同端点变换、Ω/Q在x处共轭、输出保持相同link变换律。无时间方向staple或时间轴shift；接口不接收temporal links。调用者保持temporal数组原样。本轮没有接入现有build_kernel或生产协议，不改变APE测量身份。

冻结测试seed=20261119，非立方(t,z,y,x)=(3,2,3,4)随机QR生成SU3，ρ/步数为0/3、.05/1、.1/3、.2/2，最大元素容差1e-11。改变t=1空间links，检查t=0,2完全不变；同时检查输入不被修改及最终圈规范不变。temporal_mutation只表明本调用未改该数组，不冒充新的temporal更新算法测试。

| rho | steps | covariance | unitarity | det−1 | time locality | input mutation | temporal mutation | loop gauge |
|---|---|---|---|---|---|---|---|---|
| 0.0 | 3 | 0.000e+00 | 8.882e-16 | 9.600e-16 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 3.296e-17 |
| 0.05 | 1 | 1.570e-15 | 2.442e-15 | 2.675e-15 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 3.469e-17 |
| 0.1 | 3 | 3.085e-15 | 3.775e-15 | 3.806e-15 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 8.327e-17 |
| 0.2 | 2 | 2.441e-15 | 3.553e-15 | 4.447e-15 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 7.980e-17 |

详细原始数值、源码hash与ε→0结果见[residuals.json](residuals.json)。另以seed7检查ρ=1e-3/1e-4/1e-5的最大变化近线性缩小，ρ=0、steps=0精确返回副本，冷场保持identity；非法shape/负ρ/负steps拒绝。6个回归测试通过（0.08s）。复现：`PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -q -p no:cacheprovider tests/test_wilson_stout.py`。

本结果只认证声明小场范围的算符性质，不是gauge/HMC生产样本，不说明stout与APE的risk、overlap、物理优劣或GPU成本。F4生产receipts、CuPy/GPU与MPI均NOT_RUN。进入下一物理阶段前须独立冻结候选/预算/统计与未见validation，保留共同偏差门控的conditional-only边界。
