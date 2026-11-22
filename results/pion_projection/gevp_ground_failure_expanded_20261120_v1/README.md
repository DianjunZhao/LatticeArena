# Independent expansion of the pion GEVP ground-mode grid

This new independent-seed CPU replication expands the earlier 20-dataset/cell grid to 400 datasets/cell and uses independent bootstrap-index seeds per dataset. It estimates Monte Carlo uncertainty for the specified synthetic GEVP estimator; it is not physical ground-state certification.

The 2x2 matrix, rank=2, 120 configurations blocked by 5, plateau times t0+1..t0+3, noise/gap/t0/cutoff grid, and whole-replica validity rule are held fixed. Each dataset uses 200 bootstrap draws. At N=400, the worst-case binomial CP95 half-width is approximately 0.05; no top-up is allowed.

| Noise | Gap | t0 | Cutoff | Valid / planned | Coverage / CP95 | Mean bias / dataset-bootstrap CI95 | Mean within-dataset bootstrap SE | Failure reasons |
| ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | --- |
| 0.01 | 0.1 | 1 | 1e-08 | 400/400 | 0.000 [0.000, 0.009] | 0.01405 [0.01398, 0.01411] | 0.00064 | `{}` |
| 0.01 | 0.1 | 1 | 1e-05 | 400/400 | 0.000 [0.000, 0.009] | 0.01408 [0.01401, 0.01415] | 0.00064 | `{}` |
| 0.01 | 0.1 | 2 | 1e-08 | 400/400 | 0.000 [0.000, 0.009] | 0.01261 [0.01255, 0.01267] | 0.00063 | `{}` |
| 0.01 | 0.1 | 2 | 1e-05 | 400/400 | 0.000 [0.000, 0.009] | 0.01261 [0.01254, 0.01268] | 0.00064 | `{}` |
| 0.01 | 0.5 | 1 | 1e-08 | 400/400 | 0.000 [0.000, 0.009] | 0.03598 [0.03592, 0.03604] | 0.00064 | `{}` |
| 0.01 | 0.5 | 1 | 1e-05 | 400/400 | 0.000 [0.000, 0.009] | 0.03604 [0.03598, 0.03611] | 0.00064 | `{}` |
| 0.01 | 0.5 | 2 | 1e-08 | 400/400 | 0.000 [0.000, 0.009] | 0.02220 [0.02214, 0.02227] | 0.00064 | `{}` |
| 0.01 | 0.5 | 2 | 1e-05 | 400/400 | 0.000 [0.000, 0.009] | 0.02224 [0.02217, 0.02231] | 0.00064 | `{}` |
| 0.05 | 0.1 | 1 | 1e-08 | 400/400 | 0.007 [0.002, 0.022] | 0.01404 [0.01373, 0.01436] | 0.00316 | `{}` |
| 0.05 | 0.1 | 1 | 1e-05 | 400/400 | 0.022 [0.010, 0.042] | 0.01389 [0.01357, 0.01423] | 0.00317 | `{}` |
| 0.05 | 0.1 | 2 | 1e-08 | 400/400 | 0.035 [0.019, 0.058] | 0.01242 [0.01211, 0.01273] | 0.00316 | `{}` |
| 0.05 | 0.1 | 2 | 1e-05 | 400/400 | 0.040 [0.023, 0.064] | 0.01254 [0.01221, 0.01288] | 0.00318 | `{}` |
| 0.05 | 0.5 | 1 | 1e-08 | 400/400 | 0.000 [0.000, 0.009] | 0.03595 [0.03564, 0.03627] | 0.00318 | `{}` |
| 0.05 | 0.5 | 1 | 1e-05 | 400/400 | 0.000 [0.000, 0.009] | 0.03591 [0.03556, 0.03625] | 0.00319 | `{}` |
| 0.05 | 0.5 | 2 | 1e-08 | 400/400 | 0.000 [0.000, 0.009] | 0.02237 [0.02205, 0.02271] | 0.00316 | `{}` |
| 0.05 | 0.5 | 2 | 1e-05 | 400/400 | 0.000 [0.000, 0.009] | 0.02213 [0.02181, 0.02245] | 0.00321 | `{}` |

![Expanded GEVP coverage and bias](gevp_coverage_bias.png)

## Interpretation boundary

Coverage is the frequency with which the estimator's within-dataset bootstrap normal interval contains the known E0. Independent outer datasets define the MC uncertainty. Bias intervals describe the mean estimator bias, not a physical systematic-error budget. Failures and local bootstrap failures remain reported. Any near-zero coverage reproduces a defect of this synthetic estimator under the declared generator; it does not establish the failure rate for physical correlators or a corrected GEVP method.

The raw dataset-level estimates, standard errors, coverage indicators, failure counts/reasons, seed rules, protocol/source hashes, and artifact hashes are stored in this directory. Verify with `python -B -m tasks.pion_projection.gevp_ground_failure_expanded --verify`.
