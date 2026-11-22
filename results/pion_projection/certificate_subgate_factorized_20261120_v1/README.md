# Factorized calibration of the pion chi-square subgate

This preregistered controlled Gaussian linear-model study separates nominal chi-square behavior with known covariance from finite-sample effects caused by estimating covariance, shrinkage, rank deficiency, and the eigenvalue floor. It is not an end-to-end `fit_reference_gate` test, a physical validation, or a replacement production gate.

## Design and method

The model has p=12 data components, q=4 fitted linear parameters, and nominal df=8. The covariance is AR(1)-like with rho=0.6; 6, 12, and 24 independent blocks are used. Each B/method cell has 5000 independent calibration datasets and a separate 5000-dataset evaluation sample. Four methods are compared on paired raw datasets: known covariance, and estimated covariance with shrinkage 0, 0.25, and 0.5. The production relative eigen floor is 1e-10.

The nominal rule uses the chi-square(df=8) 95% critical value. The second rule ranks each held-out statistic against the independent calibration sample for the same declared B/method/DGP; it is an unconditional Monte Carlo rank calibration under a known synthetic null, not a conditional parametric bootstrap from observed correlators.

## Held-out results

Rates include exact marginal CP95 intervals. The empirical q95 is estimated from the independent calibration sample; no uncertainty interval is attached to that critical-value estimate.

| Blocks | Method | Nominal chi-square rejects | Rank-calibrated rejects | Calibration q95 / nominal q95 | Median raw covariance rank | Median eigen-floor fraction |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 6 | known_covariance | 238/5000 (0.048, [0.042, 0.054]) | 239/5000 (0.048, [0.042, 0.054]) | 0.999 | — | — |
| 6 | shrink_0.0 | 5000/5000 (1.000, [0.999, 1.000]) | 248/5000 (0.050, [0.044, 0.056]) | 4.01e+08 | 5.0 | 0.583 |
| 6 | shrink_0.25 | 1043/5000 (0.209, [0.197, 0.220]) | 231/5000 (0.046, [0.041, 0.052]) | 1.76 | 5.0 | 0.000 |
| 6 | shrink_0.5 | 295/5000 (0.059, [0.053, 0.066]) | 220/5000 (0.044, [0.038, 0.050]) | 1.09 | 5.0 | 0.000 |
| 12 | known_covariance | 247/5000 (0.049, [0.044, 0.056]) | 242/5000 (0.048, [0.043, 0.055]) | 1.01 | — | — |
| 12 | shrink_0.0 | 3465/5000 (0.693, [0.680, 0.706]) | 299/5000 (0.060, [0.053, 0.067]) | 8.1 | 11.0 | 0.083 |
| 12 | shrink_0.25 | 375/5000 (0.075, [0.068, 0.083]) | 268/5000 (0.054, [0.048, 0.060]) | 1.09 | 11.0 | 0.000 |
| 12 | shrink_0.5 | 102/5000 (0.020, [0.017, 0.025]) | 247/5000 (0.049, [0.044, 0.056]) | 0.786 | 11.0 | 0.000 |
| 24 | known_covariance | 239/5000 (0.048, [0.042, 0.054]) | 253/5000 (0.051, [0.045, 0.057]) | 0.989 | — | — |
| 24 | shrink_0.0 | 1453/5000 (0.291, [0.278, 0.303]) | 246/5000 (0.049, [0.043, 0.056]) | 1.9 | 12.0 | 0.000 |
| 24 | shrink_0.25 | 158/5000 (0.032, [0.027, 0.037]) | 275/5000 (0.055, [0.049, 0.062]) | 0.887 | 12.0 | 0.000 |
| 24 | shrink_0.5 | 38/5000 (0.008, [0.005, 0.010]) | 277/5000 (0.055, [0.049, 0.062]) | 0.677 | 12.0 | 0.000 |

![Factorized finite-sample calibration diagnostic](factorized_calibration.png)

## Interpretation boundary

Known covariance is a control for the nominal chi-square reference in this fixed linear-Gaussian model. Estimated-covariance results expose finite-B behavior in a controlled p=12, q=4 setting. Independent rank calibration should be near 5% under the same generator by construction; it does not establish transfer to time-correlated lattice correlators, nonlinear mass fits, the production certificate, or physical ensembles.

The next method step, only if it could change the production gate decision, is to compare this controlled result against the real reference-fit model using a separately preregistered conditional parametric/block bootstrap and generator-shift controls. Keep failures, ill-conditioned cases, rank, and abstentions visible. Never tune shrinkage on this synthetic null to force nominal size.

Raw calibration/evaluation statistics, Monte Carlo p-values, ranks, floor fractions, conditions, frozen protocol, and hashes are stored alongside this report. Verify with `python -B -m tasks.pion_projection.certificate_subgate_factorized --verify`.
