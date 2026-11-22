# Studentized paired-block randomization for the synthetic C3 score

The primary method is a studentized sign-flip randomization test on paired block-level energy-risk contributions. Each dataset has 24 independent paired blocks of 5 configurations; within-block configuration noise is AR(1) with rho=0.5 and resets between blocks. The common block covariance is estimated from both arms together and held fixed, so swapping arm labels leaves the reference fit unchanged. Under equal-arm worlds, paired block labels are exchangeable by construction.

This test has finite-sample type-I control only for the declared sharp exchangeable null. It does not guarantee control for every weak null with equal expected risk but nonexchangeable arms, and cannot detect a common model/state bias shared by both methods. The paired block score uses one mass fit per independent block, so it is a different estimand from a single full-ensemble fit certificate.

## Null size at anchor offset zero

| World | rho | Method | Certified / planned | Rate | Familywise CP95 | Mean block delta | Dataset-bootstrap CI95 |
| --- | ---: | --- | ---: | ---: | --- | ---: | --- |
| equal_gaussian_null | 0.5 | block_signflip_studentized | 14/400 | 0.035 | [0.014,0.072] | -0.00332 | [-0.01333,0.00646] |
| equal_gaussian_null | 0.5 | paired_block_t | 14/400 | 0.035 | [0.014,0.072] | -0.00332 | [-0.01311,0.00665] |
| equal_gaussian_null | 0.5 | paired_block_bootstrap | 20/400 | 0.050 | [0.023,0.091] | -0.00332 | [-0.01362,0.00668] |
| equal_gaussian_null | 0.9 | block_signflip_studentized | 17/400 | 0.043 | [0.018,0.082] | -0.00051 | [-0.00554,0.00471] |
| equal_gaussian_null | 0.9 | paired_block_t | 21/400 | 0.052 | [0.025,0.095] | -0.00051 | [-0.00559,0.00472] |
| equal_gaussian_null | 0.9 | paired_block_bootstrap | 29/400 | 0.072 | [0.039,0.120] | -0.00051 | [-0.00593,0.00458] |
| common_truth_shift_null | 0.5 | block_signflip_studentized | 21/400 | 0.052 | [0.028,0.089] | 0.01768 | [-0.01351,0.04986] |
| common_truth_shift_null | 0.5 | paired_block_t | 21/400 | 0.052 | [0.028,0.089] | 0.01768 | [-0.01411,0.04902] |
| common_truth_shift_null | 0.5 | paired_block_bootstrap | 23/400 | 0.058 | [0.031,0.095] | 0.01768 | [-0.01576,0.04924] |
| common_truth_shift_null | 0.9 | block_signflip_studentized | 16/400 | 0.040 | [0.019,0.073] | 0.00172 | [-0.01360,0.01744] |
| common_truth_shift_null | 0.9 | paired_block_t | 15/400 | 0.037 | [0.017,0.070] | 0.00172 | [-0.01391,0.01760] |
| common_truth_shift_null | 0.9 | paired_block_bootstrap | 19/400 | 0.048 | [0.024,0.083] | 0.00172 | [-0.01367,0.01780] |
| equal_student_t5_null | 0.5 | block_signflip_studentized | 22/400 | 0.055 | [0.027,0.098] | -0.00136 | [-0.01124,0.00849] |
| equal_student_t5_null | 0.5 | paired_block_t | 24/400 | 0.060 | [0.030,0.104] | -0.00136 | [-0.01148,0.00862] |
| equal_student_t5_null | 0.5 | paired_block_bootstrap | 26/400 | 0.065 | [0.034,0.110] | -0.00136 | [-0.01119,0.00814] |
| equal_student_t5_null | 0.9 | block_signflip_studentized | 16/400 | 0.040 | [0.017,0.078] | -0.00062 | [-0.00542,0.00409] |
| equal_student_t5_null | 0.9 | paired_block_t | 17/400 | 0.043 | [0.018,0.082] | -0.00062 | [-0.00552,0.00440] |
| equal_student_t5_null | 0.9 | paired_block_bootstrap | 24/400 | 0.060 | [0.030,0.104] | -0.00062 | [-0.00551,0.00428] |
| uncertain_anchor_null | 0.5 | block_signflip_studentized | 11/400 | 0.028 | [0.011,0.057] | -0.00655 | [-0.02147,0.00842] |
| uncertain_anchor_null | 0.5 | paired_block_t | 11/400 | 0.028 | [0.011,0.057] | -0.00655 | [-0.02109,0.00810] |
| uncertain_anchor_null | 0.5 | paired_block_bootstrap | 15/400 | 0.037 | [0.017,0.070] | -0.00655 | [-0.02149,0.00863] |
| uncertain_anchor_null | 0.9 | block_signflip_studentized | 24/400 | 0.060 | [0.033,0.098] | -0.00415 | [-0.01150,0.00316] |
| uncertain_anchor_null | 0.9 | paired_block_t | 24/400 | 0.060 | [0.033,0.098] | -0.00415 | [-0.01135,0.00311] |
| uncertain_anchor_null | 0.9 | paired_block_bootstrap | 27/400 | 0.068 | [0.039,0.108] | -0.00415 | [-0.01174,0.00314] |

## Known lower-noise candidate power

| rho | Method | Certified / planned | Rate | Familywise CP95 |
| ---: | --- | ---: | ---: | --- |
| 0.5 | block_signflip_studentized | 40/400 | 0.100 | [0.064,0.146] |
| 0.5 | paired_block_t | 39/400 | 0.098 | [0.062,0.143] |
| 0.5 | paired_block_bootstrap | 64/400 | 0.160 | [0.115,0.214] |
| 0.9 | block_signflip_studentized | 84/400 | 0.210 | [0.159,0.268] |
| 0.9 | paired_block_t | 85/400 | 0.212 | [0.161,0.271] |
| 0.9 | paired_block_bootstrap | 107/400 | 0.268 | [0.211,0.330] |

![Null size, anchor sensitivity, power, and score distributions](block_randomization_diagnostics.png)

## Interpretation

Compare the sign-flip result with the paired t and paired block-bootstrap controls, but do not select a method by the same calibration outcomes. The common-truth-shift world tests label symmetry under an anchor/model mismatch; a valid null result there is evidence only for no relative arm effect, not for physical accuracy. The Student-t5 world tests heavier-tailed innovations while retaining independent exchangeable blocks. The uncertain-anchor world samples one anchor independently per outer dataset and holds it common across both arms and all randomizations.

All event-rate intervals are Monte Carlo intervals for the declared generator, not physical coverage. Invalid fits are retained in the planned denominator. Raw block masses, block deltas, randomization seeds, protocol/source hashes, and failure reasons are stored. Verify with `python -B -m tasks.pion_projection.block_randomization_score --verify`.
