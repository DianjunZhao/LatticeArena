# P4 N=402 independent synthetic datasets per control

Frozen protocol.json was written before simulation; seed2026111902; 80 configurations/16 paired blocks per dataset,100 outer×100 inner. Two equal-quality estimator labels share80% noise variance; they are not physical stout/APE measurements. Null c1=0; common-bias c1=.5, E0=.5/E1=1.2. Gate thresholds and all event definitions are in protocol.json; no data-dependent tuning. raw.json retains block loops, both decisions, ratio draws/intervals and joint events. summary.json retains paired decision patterns. No old N=40 artifact overwritten.

Statistical unit is one independent dataset. Two within-dataset estimator decisions are one joint outcome, never804 independent trials. CP95 is exact pointwise binomial uncertainty across402 datasets, not a simultaneous family guarantee. Independent synthetic draws underlie this assumption; bootstrap draws do not enlarge denominator. Legacy false-pass is defined only for biased control (structural zero under null); use legacy_both_pass to inspect null acceptance. False improvement means a directional improvement declaration between exchangeable equal-quality labels after both oracle gates pass.

| control | joint event | count | rate [CP95] |
|---|---|---|---|
| null | legacy_both_pass | 402/402 | 1.00000 [0.99087, 1.00000] |
| null | legacy_any_pass | 402/402 | 1.00000 [0.99087, 1.00000] |
| null | legacy_false_pass | 0/402 | 0.00000 [0.00000, 0.00913] |
| null | oracle_any_abstain | 4/402 | 0.00995 [0.00272, 0.02528] |
| null | oracle_both_abstain | 0/402 | 0.00000 [0.00000, 0.00913] |
| null | false_improvement | 3/402 | 0.00746 [0.00154, 0.02165] |
| null | ratio_excludes_one | 6/402 | 0.01493 [0.00550, 0.03220] |
| null | any_failure | 0/402 | 0.00000 [0.00000, 0.00913] |
| two_state_common_bias | legacy_both_pass | 402/402 | 1.00000 [0.99087, 1.00000] |
| two_state_common_bias | legacy_any_pass | 402/402 | 1.00000 [0.99087, 1.00000] |
| two_state_common_bias | legacy_false_pass | 402/402 | 1.00000 [0.99087, 1.00000] |
| two_state_common_bias | oracle_any_abstain | 402/402 | 1.00000 [0.99087, 1.00000] |
| two_state_common_bias | oracle_both_abstain | 402/402 | 1.00000 [0.99087, 1.00000] |
| two_state_common_bias | false_improvement | 0/402 | 0.00000 [0.00000, 0.00913] |
| two_state_common_bias | ratio_excludes_one | 28/402 | 0.06965 [0.04678, 0.09909] |
| two_state_common_bias | any_failure | 0/402 | 0.00000 [0.00000, 0.00913] |

![Joint dataset rates](joint_rates.png)

Representative first occurrences, including ratio anomalies and false improvements if present, are in examples.json. Missing categories explicitly say no case observed. Any thrown numeric exception aborts this runner rather than silently deleting/replacing a dataset; this completed run had no exception. Zero failure here is not universal robustness. Common-bias abstention uses exact E0 supplied by the synthetic world, not an inferred real-data anchor. Null abstention is an oracle-gate false rejection; biased legacy acceptance exposes a spread-gate blind spot. The CP intervals quantify Monte Carlo event uncertainty only, not physics significance, actual gate certification or transferable production error control.

Physical/HMC/F4/GPU/MPI status remains NOT_RUN. These are synthetic loop controls, not gauge fields or stout/APE ensemble comparisons. Prior small-gauge kernel certification remains separate; real anchor availability, frozen candidate budget, production receipts, independent gauge samples and autocorrelation checks remain prerequisites. No production receipt generated or physical score issued. Reproduce into a fresh directory by changing only output path before rerun; the runner refuses an existing directory.
