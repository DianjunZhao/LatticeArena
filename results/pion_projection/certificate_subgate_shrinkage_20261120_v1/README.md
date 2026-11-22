# Paired covariance-shrinkage sensitivity of the pion χ² subgate

This pre-registered follow-up uses 1000 independent ground-state-null datasets at each block count. Every dataset is fit under all three covariance shrinkage values, so the shrinkage comparison is paired. It isolates the subgate; it is not a full certificate or physical validation.

## Marginal rejection rates

| Blocks | Shrinkage | Reject | Invalid | Rejection rate (CP95) |
| ---: | ---: | ---: | ---: | --- |
| 6 | 0.0 | 1000/1000 | 0 | 1.000 [0.996, 1.000] |
| 6 | 0.25 | 160/1000 | 0 | 0.160 [0.138, 0.184] |
| 6 | 0.5 | 26/1000 | 0 | 0.026 [0.017, 0.038] |
| 12 | 0.0 | 701/1000 | 0 | 0.701 [0.672, 0.729] |
| 12 | 0.25 | 54/1000 | 0 | 0.054 [0.041, 0.070] |
| 12 | 0.5 | 8/1000 | 0 | 0.008 [0.003, 0.016] |
| 24 | 0.0 | 281/1000 | 0 | 0.281 [0.253, 0.310] |
| 24 | 0.25 | 25/1000 | 0 | 0.025 [0.016, 0.037] |
| 24 | 0.5 | 5/1000 | 0 | 0.005 [0.002, 0.012] |

## Paired shrinkage contrasts

Positive means the alternative shrinkage rejects more null datasets than production shrinkage 0.25. The six intervals have 95% family coverage by the predeclared Bonferroni adjustment.

| Blocks | Alternative | Difference | Familywise bootstrap CI95 | Alt-only / production-only rejects |
| ---: | ---: | ---: | --- | ---: |
| 6 | 0.0 | 0.840 | [0.809, 0.870] | 840 / 0 |
| 6 | 0.5 | -0.134 | [-0.164, -0.106] | 0 / 134 |
| 12 | 0.0 | 0.647 | [0.607, 0.687] | 647 / 0 |
| 12 | 0.5 | -0.046 | [-0.064, -0.029] | 0 / 46 |
| 24 | 0.0 | 0.256 | [0.221, 0.293] | 256 / 0 |
| 24 | 0.5 | -0.020 | [-0.033, -0.009] | 0 / 20 |

![Covariance-shrinkage sensitivity](shrinkage_sensitivity.png)

## Interpretation

Read the paired contrasts together with invalid counts and marginal intervals. This study asks whether the fixed covariance shrinkage setting explains the block-count size distortion observed in certificate_subgate_mc_20261120_v1. It does not select a replacement shrinkage or imply chi-square calibration outside this generator.

The per-dataset p-values, fitted masses, costs, statuses, seeds, frozen protocol, and hashes are stored beside this report. Reproduce with `python -B -m tasks.pion_projection.certificate_subgate_shrinkage --run`; verify with `python -B -m tasks.pion_projection.certificate_subgate_shrinkage --verify`.
