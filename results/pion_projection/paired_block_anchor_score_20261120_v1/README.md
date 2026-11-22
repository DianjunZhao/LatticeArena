# Common-block bootstrap for the synthetic C3 score

This independent CPU study uses 400 dataset IDs in each equal-noise null / known-lower-noise world and each matched-arm noise-correlation cell (ρ=0.5, 0.9). The same synthetic configuration IDs feed baseline and candidate. Configuration noise has AR(1) ρ=0.5; each arm has the same marginal noise amplitude within a quality world, with a shared latent component controlling cross-arm correlation. The 120 configurations are resampled as 24 consecutive blocks of length 5.

The only change between methods is bootstrap indexing: `independent_arm_indices` draws separate block indices for the two arms; `common_block_indices` applies the same block-index matrix to both arms. Both use the existing energy-risk difference and certify when its bootstrap 5th percentile is positive. No alpha or threshold was tuned. Under the null, the same fitted mass draws are evaluated at anchor offsets -0.02, 0, +0.02; the known-improvement control uses offset zero.

## Null size at zero anchor offset

| Matched-arm rho | Resampling | Certified / planned | Rate | Familywise CP95 (4 rates) | Mean delta | Familywise dataset-bootstrap CI95 |
| ---: | --- | ---: | ---: | --- | ---: | --- |
| 0.5 | independent_arm_indices | 45/400 | 0.113 | [0.076,0.158] | 0.00262 | [-0.00997,0.01539] |
| 0.5 | common_block_indices | 76/400 | 0.190 | [0.144,0.244] | 0.00267 | [-0.01012,0.01540] |
| 0.9 | independent_arm_indices | 4/400 | 0.010 | [0.002,0.030] | -0.00202 | [-0.00884,0.00498] |
| 0.9 | common_block_indices | 77/400 | 0.193 | [0.146,0.246] | -0.00214 | [-0.00896,0.00473] |

## Known-improvement power

| Matched-arm rho | Resampling | Certified / planned | Rate | Familywise CP95 (4 rates) |
| ---: | --- | ---: | ---: | --- |
| 0.5 | independent_arm_indices | 62/400 | 0.155 | [0.113,0.205] |
| 0.5 | common_block_indices | 81/400 | 0.203 | [0.155,0.257] |
| 0.9 | independent_arm_indices | 21/400 | 0.052 | [0.029,0.087] |
| 0.9 | common_block_indices | 70/400 | 0.175 | [0.130,0.227] |

## Paired resampling contrasts

Rate differences below are paired by outer dataset ID; intervals resample those IDs. Positive values mean common-block resampling certified more often.

| Quality | Anchor bias | rho | Common minus independent rate | Familywise dataset-bootstrap CI95 | Common-only / independent-only events |
| --- | ---: | ---: | ---: | --- | ---: |
| equal_noise_null | -0.02 | 0.5 | +0.0775 | [+0.0425,+0.1150] | 32 / 1 |
| equal_noise_null | -0.02 | 0.9 | +0.1825 | [+0.1350,+0.2325] | 73 / 0 |
| equal_noise_null | +0.00 | 0.5 | +0.0775 | [+0.0425,+0.1150] | 32 / 1 |
| equal_noise_null | +0.00 | 0.9 | +0.1825 | [+0.1350,+0.2350] | 73 / 0 |
| equal_noise_null | +0.02 | 0.5 | +0.0700 | [+0.0350,+0.1100] | 31 / 3 |
| equal_noise_null | +0.02 | 0.9 | +0.2175 | [+0.1650,+0.2725] | 87 / 0 |
| known_lower_noise | +0.00 | 0.5 | +0.0475 | [+0.0225,+0.0750] | 21 / 2 |
| known_lower_noise | +0.00 | 0.9 | +0.1225 | [+0.0875,+0.1600] | 49 / 0 |

![Null size, known-improvement power, and anchor sensitivity](paired_block_diagnostics.png)

## Interpretation boundary

This simulation directly tests matched configuration/block resampling under its declared correlated Gaussian noise model. It does not prove coverage for real gauge ensembles, production fit gates, a measured independent anchor, or arbitrary covariance structures. The common-block scheme is the structurally matched bootstrap when the two arms use the same configuration IDs; if the arms are independent samples, separate indices are appropriate. The prior C3 expansion reports used separate arm data / indices and should not be described as common-configuration paired bootstrap evidence. A physical score still requires a blind production test with real configuration-level IDs, anchor uncertainty, and null/known-signal controls.

Raw dataset summaries, seeds, protocol/source hashes, and output hashes are retained. Verify with `python -B -m tasks.pion_projection.paired_block_anchor_score --verify`.
