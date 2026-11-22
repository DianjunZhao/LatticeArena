# Wilson P4 known-improvement positive control

Run status: **COMPLETED**. Failed datasets remain in the planned denominator and in `raw.json`.

This is a new CPU-only synthetic control, separate from the frozen null/common-bias runs. The protocol was written before any dataset was generated; seed `2026111904`, 402 independent paired datasets, 80 configurations and 16 blocks per dataset. Both labels share the same ground-state signal $W(T)=e^{-E_0T}$ with $E_0=0.5$ and 80% common noise, while the candidate's multiplicative-noise amplitude is half the baseline's. Thus the input noise variance ratio is exactly four; because the reported risk contains log-potential and window-spread terms, its expected risk ratio is only approximately four in the small-noise limit.

The primary success event is frozen in `protocol.json`: both labels pass the legacy spread and exact synthetic-anchor diagnostic, and the paired outer-bootstrap 95% lower bound of risk(baseline)/risk(candidate) is greater than one. One independent dataset, not its bootstrap draws, is the statistical unit. Event intervals are pointwise exact Clopper-Pearson 95% intervals; no family-wise statement is made. Failures remain in the denominator.

| Event | Count | Rate | CP95 |
|---|---:|---:|---:|
| baseline pass | 398/402 | 0.9900 | [0.9747, 0.9973] |
| candidate pass | 401/402 | 0.9975 | [0.9862, 0.9999] |
| both pass | 397/402 | 0.9876 | [0.9712, 0.9959] |
| improvement detected | 324/402 | 0.8060 | [0.7639, 0.8435] |
| missed improvement | 78/402 | 0.1940 | [0.1565, 0.2361] |
| failure | 0/402 | 0.0000 | [0.0000, 0.0091] |

Descriptive median point risk ratio across successful datasets: 3.847 (dataset-bootstrap 95% interval [3.675, 4.096]); this is secondary to the detection-rate endpoint.

Of the 78 missed detections, 5 datasets abstained at a per-estimator gate (4 baseline and 1 candidate), while 73 passed both gates but had a ratio interval whose lower bound did not exceed one. For example, dataset 5 had point ratio 5.31 but interval [0.946, 10.46]; dataset 0 was detected with point ratio 6.96 and interval [1.37, 19.08]. The exact first-occurrence rows are in [`examples.json`](examples.json). Thus a fourfold input-noise variance reduction was detected in 80.6% of these synthetic datasets, not nearly all of them; this is a finite-control power result, not evidence about physical stout/APE.

The post-hoc [100-versus-1000 outer-draw resolution check](../audit_20261119_p4_known_improvement_sensitivity_v1/README.md) reuses the same 402 datasets. It found 323/402 detections at 1000 draws (CP95 [0.761, 0.841]), versus 324/402 at 100 draws; 16 cases changed to detected and 17 changed the other way. The detection rate was therefore not driven mainly by quantile Monte Carlo resolution, though individual dataset bounds moved. This sensitivity run is not an additional sample.

![Known-improvement control diagnostic](known_improvement.png)

This tests whether the current synthetic gate can detect a clear variance reduction when its exact anchor is available. It does not establish calibration for a noisy or estimated production anchor, does not cover common model bias, and does not measure stout/APE or physical Wilson loops. `physical_status` remains `NOT_RUN`.
