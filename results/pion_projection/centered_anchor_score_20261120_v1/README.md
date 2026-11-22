# Centered bootstrap lower bounds for the synthetic C3 score

This is a follow-up to the common-block resampling study. It uses new independent dataset seeds, 400 dataset IDs per quality x cross-arm-correlation cell, the same paired configuration generator and the same two resampling schemes. The candidate lower-bound rules were frozen before this run: ordinary percentile, basic/reflected percentile, and a bootstrap-normal lower bound. All use the same energy-risk difference and certify only when the lower bound is positive.

## Equal-noise null (anchor offset = 0)

| rho | Resampling | Lower bound | Certified / planned | Rate | Familywise CP95 (12 rates) | Mean point delta |
| ---: | --- | --- | ---: | ---: | --- | ---: |
| 0.5 | independent_arm_indices | percentile | 49/400 | 0.122 | [0.080,0.176] | 0.00362 |
| 0.5 | independent_arm_indices | basic_reflected | 47/400 | 0.117 | [0.076,0.170] | 0.00362 |
| 0.5 | independent_arm_indices | bootstrap_normal | 47/400 | 0.117 | [0.076,0.170] | 0.00362 |
| 0.5 | common_block_indices | percentile | 72/400 | 0.180 | [0.129,0.241] | 0.00362 |
| 0.5 | common_block_indices | basic_reflected | 77/400 | 0.193 | [0.140,0.255] | 0.00362 |
| 0.5 | common_block_indices | bootstrap_normal | 72/400 | 0.180 | [0.129,0.241] | 0.00362 |
| 0.9 | independent_arm_indices | percentile | 4/400 | 0.010 | [0.001,0.034] | -0.00141 |
| 0.9 | independent_arm_indices | basic_reflected | 2/400 | 0.005 | [0.000,0.026] | -0.00141 |
| 0.9 | independent_arm_indices | bootstrap_normal | 2/400 | 0.005 | [0.000,0.026] | -0.00141 |
| 0.9 | common_block_indices | percentile | 72/400 | 0.180 | [0.129,0.241] | -0.00141 |
| 0.9 | common_block_indices | basic_reflected | 65/400 | 0.163 | [0.114,0.221] | -0.00141 |
| 0.9 | common_block_indices | bootstrap_normal | 67/400 | 0.168 | [0.118,0.227] | -0.00141 |

## Known-improvement power

| rho | Resampling | Lower bound | Certified / planned | Rate | Familywise CP95 (12 rates) |
| ---: | --- | --- | ---: | ---: | --- |
| 0.5 | independent_arm_indices | percentile | 51/400 | 0.128 | [0.084,0.182] |
| 0.5 | independent_arm_indices | basic_reflected | 42/400 | 0.105 | [0.066,0.156] |
| 0.5 | independent_arm_indices | bootstrap_normal | 44/400 | 0.110 | [0.070,0.162] |
| 0.5 | common_block_indices | percentile | 73/400 | 0.182 | [0.131,0.244] |
| 0.5 | common_block_indices | basic_reflected | 65/400 | 0.163 | [0.114,0.221] |
| 0.5 | common_block_indices | bootstrap_normal | 66/400 | 0.165 | [0.116,0.224] |
| 0.9 | independent_arm_indices | percentile | 20/400 | 0.050 | [0.024,0.089] |
| 0.9 | independent_arm_indices | basic_reflected | 18/400 | 0.045 | [0.021,0.083] |
| 0.9 | independent_arm_indices | bootstrap_normal | 18/400 | 0.045 | [0.021,0.083] |
| 0.9 | common_block_indices | percentile | 65/400 | 0.163 | [0.114,0.221] |
| 0.9 | common_block_indices | basic_reflected | 56/400 | 0.140 | [0.095,0.196] |
| 0.9 | common_block_indices | bootstrap_normal | 57/400 | 0.142 | [0.097,0.199] |

![Null size, power, and anchor sensitivity](centered_bootstrap_diagnostics.png)

## Method contrasts

Rate differences are paired by outer dataset ID. Positive values mean the alternative method certified more often than the percentile reference.

| Quality | Anchor bias | rho | Resampling | Method | Difference vs percentile | Familywise dataset-bootstrap CI95 | Method-only / percentile-only |
| --- | ---: | ---: | --- | --- | ---: | --- | ---: |
| equal_noise_null | -0.02 | 0.5 | independent_arm_indices | basic_reflected | +0.0000 | [-0.0200,+0.0175] | 4 / 4 |
| equal_noise_null | -0.02 | 0.5 | independent_arm_indices | bootstrap_normal | +0.0025 | [-0.0175,+0.0250] | 5 / 4 |
| equal_noise_null | -0.02 | 0.5 | common_block_indices | basic_reflected | +0.0150 | [-0.0050,+0.0375] | 8 / 2 |
| equal_noise_null | -0.02 | 0.5 | common_block_indices | bootstrap_normal | +0.0050 | [+0.0000,+0.0175] | 2 / 0 |
| equal_noise_null | -0.02 | 0.9 | independent_arm_indices | basic_reflected | -0.0025 | [-0.0150,+0.0100] | 1 / 2 |
| equal_noise_null | -0.02 | 0.9 | independent_arm_indices | bootstrap_normal | -0.0025 | [-0.0125,+0.0000] | 0 / 1 |
| equal_noise_null | -0.02 | 0.9 | common_block_indices | basic_reflected | -0.0125 | [-0.0350,+0.0075] | 2 / 7 |
| equal_noise_null | -0.02 | 0.9 | common_block_indices | bootstrap_normal | -0.0150 | [-0.0325,-0.0025] | 0 / 6 |
| equal_noise_null | +0.00 | 0.5 | independent_arm_indices | basic_reflected | -0.0050 | [-0.0275,+0.0175] | 4 / 6 |
| equal_noise_null | +0.00 | 0.5 | independent_arm_indices | bootstrap_normal | -0.0050 | [-0.0250,+0.0125] | 3 / 5 |
| equal_noise_null | +0.00 | 0.5 | common_block_indices | basic_reflected | +0.0125 | [-0.0100,+0.0375] | 8 / 3 |
| equal_noise_null | +0.00 | 0.5 | common_block_indices | bootstrap_normal | +0.0000 | [-0.0175,+0.0175] | 3 / 3 |
| equal_noise_null | +0.00 | 0.9 | independent_arm_indices | basic_reflected | -0.0050 | [-0.0175,+0.0000] | 0 / 2 |
| equal_noise_null | +0.00 | 0.9 | independent_arm_indices | bootstrap_normal | -0.0050 | [-0.0175,+0.0000] | 0 / 2 |
| equal_noise_null | +0.00 | 0.9 | common_block_indices | basic_reflected | -0.0175 | [-0.0375,-0.0025] | 0 / 7 |
| equal_noise_null | +0.00 | 0.9 | common_block_indices | bootstrap_normal | -0.0125 | [-0.0300,+0.0000] | 0 / 5 |
| equal_noise_null | +0.02 | 0.5 | independent_arm_indices | basic_reflected | +0.0150 | [-0.0075,+0.0400] | 9 / 3 |
| equal_noise_null | +0.02 | 0.5 | independent_arm_indices | bootstrap_normal | +0.0075 | [-0.0100,+0.0275] | 5 / 2 |
| equal_noise_null | +0.02 | 0.5 | common_block_indices | basic_reflected | +0.0075 | [-0.0175,+0.0350] | 9 / 6 |
| equal_noise_null | +0.02 | 0.5 | common_block_indices | bootstrap_normal | +0.0000 | [-0.0200,+0.0200] | 4 / 4 |
| equal_noise_null | +0.02 | 0.9 | independent_arm_indices | basic_reflected | +0.0125 | [+0.0000,+0.0300] | 5 / 0 |
| equal_noise_null | +0.02 | 0.9 | independent_arm_indices | bootstrap_normal | +0.0050 | [+0.0000,+0.0175] | 2 / 0 |
| equal_noise_null | +0.02 | 0.9 | common_block_indices | basic_reflected | +0.0075 | [-0.0125,+0.0300] | 6 / 3 |
| equal_noise_null | +0.02 | 0.9 | common_block_indices | bootstrap_normal | +0.0025 | [-0.0125,+0.0188] | 3 / 2 |
| known_lower_noise | +0.00 | 0.5 | independent_arm_indices | basic_reflected | -0.0225 | [-0.0475,-0.0025] | 1 / 10 |
| known_lower_noise | +0.00 | 0.5 | independent_arm_indices | bootstrap_normal | -0.0175 | [-0.0375,-0.0025] | 0 / 7 |
| known_lower_noise | +0.00 | 0.5 | common_block_indices | basic_reflected | -0.0200 | [-0.0450,+0.0025] | 2 / 10 |
| known_lower_noise | +0.00 | 0.5 | common_block_indices | bootstrap_normal | -0.0175 | [-0.0375,-0.0025] | 0 / 7 |
| known_lower_noise | +0.00 | 0.9 | independent_arm_indices | basic_reflected | -0.0050 | [-0.0225,+0.0125] | 2 / 4 |
| known_lower_noise | +0.00 | 0.9 | independent_arm_indices | bootstrap_normal | -0.0050 | [-0.0175,+0.0000] | 0 / 2 |
| known_lower_noise | +0.00 | 0.9 | common_block_indices | basic_reflected | -0.0225 | [-0.0500,+0.0000] | 2 / 11 |
| known_lower_noise | +0.00 | 0.9 | common_block_indices | bootstrap_normal | -0.0200 | [-0.0425,+0.0000] | 1 / 9 |

## Interpretation boundary

The basic/reflected and bootstrap-normal rules are candidates, not validated production replacements. This generator uses a fixed true anchor and a specific AR(1) correlated Gaussian model; passing a null cell would not establish physical coverage. Compare null size and known-improvement power together, and preserve all failures. The methods were motivated after the preceding v1 null result; the present run uses independent seeds but is still a targeted synthetic follow-up, not an independent physical confirmation.

Raw dataset-level point estimates, bootstrap summaries, seeds, hashes, and failure states are retained. Verify with `python -B -m tasks.pion_projection.centered_anchor_score --verify`.
