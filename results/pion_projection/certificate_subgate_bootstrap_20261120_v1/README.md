# Conditional parametric bootstrap of the pion chi-square subgate

This preregistered CPU diagnostic reruns the actual single-state reference fit and chi-square gate. It compares nominal chi-square p-values to a plug-in Gaussian parametric bootstrap in the normalized selected reference-vector space. It is not physical validation or a full-certificate test.

The two synthetic null generators use time AR rho=0.5 (baseline) and rho=0.8 (shift), 250 independent outer datasets per block-count cell, and 399 bootstrap draws per outer dataset. The bootstrap uses the fitted mass/amplitudes, empirical block covariance, production shrinkage 0.25, and the production relative eigen floor 1e-10; every bootstrap sample is refit through `fit_reference_gate`.

Bootstrap p-values count invalid bootstrap draws conservatively in the upper tail. Invalid original fits are retained and reported separately. Confidence intervals are marginal CP95 among valid observed fits; paired differences use a six-cell familywise bootstrap interval.

| time AR rho | Blocks | Valid / planned | chi-square rejects | Bootstrap rejects | Paired bootstrap−chi2 rate difference (familywise CI95) | Invalid bootstrap draws / planned |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.5 | 6 | 250/250 | 41/250 (0.164, CP95 [0.120, 0.216]) | 3/250 (0.012, CP95 [0.002, 0.035]) | -0.152 [-0.216, -0.095] | 0/99750 |
| 0.5 | 12 | 250/250 | 15/250 (0.060, CP95 [0.034, 0.097]) | 8/250 (0.032, CP95 [0.014, 0.062]) | -0.028 [-0.060, -0.004] | 0/99750 |
| 0.5 | 24 | 250/250 | 6/250 (0.024, CP95 [0.009, 0.052]) | 4/250 (0.016, CP95 [0.004, 0.040]) | -0.008 [-0.024, +0.000] | 0/99750 |
| 0.8 | 6 | 250/250 | 1/250 (0.004, CP95 [0.000, 0.022]) | 0/250 (0.000, CP95 [0.000, 0.015]) | -0.004 [-0.016, +0.000] | 0/99750 |
| 0.8 | 12 | 250/250 | 0/250 (0.000, CP95 [0.000, 0.015]) | 0/250 (0.000, CP95 [0.000, 0.015]) | +0.000 [+0.000, +0.000] | 0/99750 |
| 0.8 | 24 | 250/250 | 0/250 (0.000, CP95 [0.000, 0.015]) | 1/250 (0.004, CP95 [0.000, 0.022]) | +0.004 [+0.000, +0.016] | 0/99750 |

![Conditional bootstrap calibration](bootstrap_calibration.png)

## Interpretation and limits

The bootstrap conditions on a fitted Gaussian mean and regularized covariance estimated from each observed dataset, then re-estimates covariance and refits the nonlinear mass for every resample. It is therefore sensitive to model misspecification and small-sample covariance estimation. The rho=0.8 generator is a limited time-correlation shift; it does not reproduce arbitrary lattice autocorrelation or physical correlator covariance.

Do not use this comparison to select shrinkage or claim universal p-value calibration. A difference from chi-square supports further model-specific calibration only if it changes the gate decision; otherwise prioritize the independent physical anchor. Raw outer outcomes, bootstrap exceedance counts, failures, seeds, frozen source/protocol hashes, and artifact hashes are retained beside this report.

Verify with `python -B -m tasks.pion_projection.certificate_subgate_bootstrap --verify`.
