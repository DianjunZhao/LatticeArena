# Learned initializer finite-budget toy

Not learned smear, not physical evidence. Spec saved before training. Analytic target labels make this a favorable algorithmic possibility test. Chebyshev is a realizable scheduled spectral iteration baseline with certified bounds, not a physical smearing kernel.

Training seconds: 0.002909790724515915; raw rows include inference/solver seconds, calls, residuals, traces and truncations. Training amortization is training_seconds / deployment_count; figure uses 100, not an assumed universal break-even.

|population|budget|comparator minus learned risk|CI95|
|---|---|---|---|
|iid|8 zero_random_SLSQP|0.7625711327403303|[0.634350401281568, 0.9025710941617024]|
|iid|8 Powell|4.341458294759183|[4.093500852947531, 4.624119645172958]|
|iid|8 Chebyshev|0.11307388668364186|[0.07720990517750284, 0.15360457025709195]|
|iid|24 zero_random_SLSQP|2.5339620650795716e-10|[1.618770371171292e-10, 3.689964513873433e-10]|
|iid|24 Powell|2.9376315031323186|[2.7744445931778063, 3.0962863177960087]|
|iid|24 Chebyshev|0.0017711363864480864|[0.0009910971661816867, 0.0027028017597525177]|
|iid|64 zero_random_SLSQP|-1.0568564402488463e-11|[-1.4476531064411085e-11, -7.220699530981009e-12]|
|iid|64 Powell|0.21445022163612307|[0.16490558279525286, 0.27176380653141713]|
|iid|64 Chebyshev|4.986048780855282e-07|[1.509524417571371e-07, 9.987530925179454e-07]|
|shift|8 zero_random_SLSQP|1.8481139972620753|[1.6499685968870033, 2.0478984406745604]|
|shift|8 Powell|6.53043959718406|[5.790689165651931, 7.328179896753781]|
|shift|8 Chebyshev|1.1388960719577423|[0.9893744989883139, 1.2988921834922915]|
|shift|24 zero_random_SLSQP|5.928471400008586e-10|[3.634386837659831e-10, 8.644596390568469e-10]|
|shift|24 Powell|4.12568161495747|[3.827174466614578, 4.481756315746064]|
|shift|24 Chebyshev|0.15741081516807046|[0.12762377238677858, 0.18953045072111216]|
|shift|64 zero_random_SLSQP|-7.345806617505987e-12|[-9.939801361995995e-12, -4.646552291702369e-12]|
|shift|64 Powell|1.1331704614187392|[0.9799156775873019, 1.2814884478779953]|
|shift|64 Chebyshev|0.002858709269819483|[0.0020358167987946916, 0.0038084518274355533]|

## Failure diagnostics

|population/method (budget64)|truncated/100|residual >1e-5|mean calls|
|---|---|---|---|
|iid/learned_SLSQP|0|9|12.07|
|iid/zero_random_SLSQP|0|0|25.28|
|iid/Powell|100|100|64.0|
|iid/Chebyshev|0|48|64.0|
|shift/learned_SLSQP|0|10|12.46|
|shift/zero_random_SLSQP|0|2|25.87|
|shift/Powell|100|100|64.0|
|shift/Chebyshev|0|100|64.0|

![Budget curves](budget_risk.png)

![Trajectory and cost](trajectory_cost.png)

Every residual-large case is retained by instance ID in raw.json. Success is a solver flag, not convergence proof. Analytic SLSQP gradients are not charged as objective calls, and walltime is separately recorded. No GPU or independent physical blind test is substituted.

## Explicit worst residual cases

- learned_SLSQP: population=iid, instance=88, risk=1.09953e-10, PG=1.967e-05, calls=12, success=True, truncated=False.
- zero_random_SLSQP: population=shift, instance=43, risk=4.19682e-11, PG=1.11795e-05, calls=24, success=True, truncated=False.
- Powell: population=shift, instance=48, risk=4.46886, PG=5.91489, calls=64, success=False, truncated=True.
- Chebyshev: population=shift, instance=83, risk=0.0227214, PG=0.223088, calls=64, success=True, truncated=False.

Chebyshev uses a fixed scheduled root order with box clipping and best evaluated iterate; this is not an optimal stable Chebyshev implementation. Its weakness cannot establish superiority over all spectral solvers. IID and shifted confidence intervals cover independent-instance mean paired differences only; multiple comparisons are descriptive and unadjusted.
