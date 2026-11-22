# C3 anchor-bias-only null (synthetic CPU diagnostic)

This preregistered extension uses **400 independent dataset IDs**. In every ID, baseline and candidate are generated from the same spectrum and the same noise law (`noise=0.02`); only the common anchor is shifted by -0.02, 0, or +0.02 from the known synthetic truth. The ±0.02 magnitude was inherited from the prior C3 anchor-bias sensitivity. Each arm has 200 mass-bootstrap draws. The same fitted mass draws are evaluated at all three anchor offsets, so offset contrasts are paired by dataset ID.

The two frozen rules are the existing naive normal lower bound (`sd/sqrt(Nboot)`, retained as a negative-method control) and the existing paired 5th-percentile rule. Invalid fits are retained and treated as non-certifications for the planned-denominator rate. Reported intervals are marginal CP95 and six-rate Bonferroni familywise CP95; independent-repeat means and four paired certification-rate contrasts use dataset-bootstrap familywise intervals.

| Anchor offset | Valid / planned | Naive certified | Paired certified | Independent-repeat mean delta | Familywise CI95 for mean delta |
| ---: | ---: | ---: | ---: | ---: | --- |
| -0.02 | 400/400 | 178/400 (0.445; marginal CP95 [0.396,0.495]) | 45/400 (0.113; marginal CP95 [0.083,0.148]) | -0.02389 | [-0.06207,0.01565] |
| +0.00 | 400/400 | 176/400 (0.440; marginal CP95 [0.391,0.490]) | 45/400 (0.113; marginal CP95 [0.083,0.148]) | -0.00578 | [-0.01531,0.00391] |
| +0.02 | 400/400 | 186/400 (0.465; marginal CP95 [0.415,0.515]) | 62/400 (0.155; marginal CP95 [0.121,0.194]) | 0.01232 | [-0.00754,0.03184] |

![False-certification and dataset-outcome diagnostics](anchor_bias_null_diagnostics.png)

## Paired bias contrasts

| Anchor offset | Rule | Rate difference vs zero bias | Familywise dataset-bootstrap CI95 | 0→1 / 1→0 switches |
| ---: | --- | ---: | --- | ---: |
| -0.02 | naive | +0.0050 | [+0.0000,+0.0150] | 2 / 0 |
| -0.02 | paired | +0.0000 | [+0.0000,+0.0000] | 0 / 0 |
| +0.02 | naive | +0.0250 | [-0.0925,+0.1425] | 186 / 176 |
| +0.02 | paired | +0.0425 | [-0.0225,+0.1075] | 62 / 45 |

## Interpretation boundary

This is an equal-noise synthetic null under a fixed two-state correlator generator and oracle-known truth. It tests whether the current scalar risk rule is sensitive to a common fixed anchor offset in this model. It does not estimate real anchor bias, lattice autocorrelation, family-wise physical-score coverage, or the behavior of other generators. A certification rate above 5% is evidence against nominal size only for this declared DGP; a rate near 5% does not validate the physical score. No threshold was tuned and no post-hoc top-up was performed.

Raw per-dataset masses, deltas, certification events, seeds, source/protocol hashes, and output hashes are retained. Verify with `python -B -m tasks.pion_projection.anchor_bias_only_null --verify`.
