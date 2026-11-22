# Pion family-wise robust-score synthetic calibration

This is a new, independent CPU method experiment. It does not modify the production score, does not validate the pion physical state, and does not use amendment02/amendment03 trials as independent data.

## Frozen design

- 2500 independent outer trials per scenario; each trial contains 30 independent synthetic datasets.
- Four candidates are compared across four frozen branches: two fit windows times two reference models. Candidate branches are correlated within each dataset.
- A robust certificate requires every branch for that candidate to clear the same frozen minimum improvement.
- Compare dataset-level paired absolute risk differences and log risk ratios. For each, compare unadjusted one-sided Student-t bounds, Bonferroni bounds over all 16 candidate/branch contrasts, and a dataset-level Rademacher max-t multiplier bootstrap.
- The relative method abstains when median baseline risk is at or below 0.05. The absolute margin is 5% of the predeclared scenario risk scale; this scale-relative choice is a controlled synthetic comparison, not a physical margin.
- Every interval below is a 95% exact Clopper-Pearson Monte Carlo interval across outer trials. It is not a physical coverage interval.

## Results

| Scenario | Method | Any null candidate falsely certified | Power for each truly improved candidate | Abstain |
| --- | --- | --- | --- | --- |
| gaussian_null | Abs pointwise t | 0/2500=0.000 [0.000, 0.001] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| gaussian_null | Abs Bonferroni | 0/2500=0.000 [0.000, 0.001] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| gaussian_null | Abs max-t | 0/2500=0.000 [0.000, 0.001] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| gaussian_null | Log-ratio pointwise t | 0/2500=0.000 [0.000, 0.001] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| gaussian_null | Log-ratio Bonferroni | 0/2500=0.000 [0.000, 0.001] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| gaussian_null | Log-ratio max-t | 0/2500=0.000 [0.000, 0.001] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| one_candidate_improved | Abs pointwise t | 0/2500=0.000 [0.000, 0.001] | candidate_0: 2500/2500=1.000 [0.999, 1.000] | 0/2500=0.000 [0.000, 0.001] |
| one_candidate_improved | Abs Bonferroni | 0/2500=0.000 [0.000, 0.001] | candidate_0: 2499/2500=1.000 [0.998, 1.000] | 0/2500=0.000 [0.000, 0.001] |
| one_candidate_improved | Abs max-t | 0/2500=0.000 [0.000, 0.001] | candidate_0: 2500/2500=1.000 [0.999, 1.000] | 0/2500=0.000 [0.000, 0.001] |
| one_candidate_improved | Log-ratio pointwise t | 0/2500=0.000 [0.000, 0.001] | candidate_0: 2500/2500=1.000 [0.999, 1.000] | 0/2500=0.000 [0.000, 0.001] |
| one_candidate_improved | Log-ratio Bonferroni | 0/2500=0.000 [0.000, 0.001] | candidate_0: 2500/2500=1.000 [0.999, 1.000] | 0/2500=0.000 [0.000, 0.001] |
| one_candidate_improved | Log-ratio max-t | 0/2500=0.000 [0.000, 0.001] | candidate_0: 2500/2500=1.000 [0.999, 1.000] | 0/2500=0.000 [0.000, 0.001] |
| heavy_tail_null | Abs pointwise t | 0/2500=0.000 [0.000, 0.001] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| heavy_tail_null | Abs Bonferroni | 0/2500=0.000 [0.000, 0.001] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| heavy_tail_null | Abs max-t | 0/2500=0.000 [0.000, 0.001] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| heavy_tail_null | Log-ratio pointwise t | 0/2500=0.000 [0.000, 0.001] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| heavy_tail_null | Log-ratio Bonferroni | 0/2500=0.000 [0.000, 0.001] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| heavy_tail_null | Log-ratio max-t | 0/2500=0.000 [0.000, 0.001] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| one_dataset_outlier_null | Abs pointwise t | 0/2500=0.000 [0.000, 0.001] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| one_dataset_outlier_null | Abs Bonferroni | 0/2500=0.000 [0.000, 0.001] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| one_dataset_outlier_null | Abs max-t | 0/2500=0.000 [0.000, 0.001] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| one_dataset_outlier_null | Log-ratio pointwise t | 0/2500=0.000 [0.000, 0.001] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| one_dataset_outlier_null | Log-ratio Bonferroni | 0/2500=0.000 [0.000, 0.001] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| one_dataset_outlier_null | Log-ratio max-t | 0/2500=0.000 [0.000, 0.001] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| near_zero_baseline | Abs pointwise t | 0/2500=0.000 [0.000, 0.001] | candidate_0: 2500/2500=1.000 [0.999, 1.000] | 0/2500=0.000 [0.000, 0.001] |
| near_zero_baseline | Abs Bonferroni | 0/2500=0.000 [0.000, 0.001] | candidate_0: 2500/2500=1.000 [0.999, 1.000] | 0/2500=0.000 [0.000, 0.001] |
| near_zero_baseline | Abs max-t | 0/2500=0.000 [0.000, 0.001] | candidate_0: 2500/2500=1.000 [0.999, 1.000] | 0/2500=0.000 [0.000, 0.001] |
| near_zero_baseline | Log-ratio pointwise t | 0/2500=0.000 [0.000, 0.001] | candidate_0: 0/2500=0.000 [0.000, 0.001] | 2500/2500=1.000 [0.999, 1.000] |
| near_zero_baseline | Log-ratio Bonferroni | 0/2500=0.000 [0.000, 0.001] | candidate_0: 0/2500=0.000 [0.000, 0.001] | 2500/2500=1.000 [0.999, 1.000] |
| near_zero_baseline | Log-ratio max-t | 0/2500=0.000 [0.000, 0.001] | candidate_0: 0/2500=0.000 [0.000, 0.001] | 2500/2500=1.000 [0.999, 1.000] |
| reference_window_conflict | Abs pointwise t | 0/2500=0.000 [0.000, 0.001] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| reference_window_conflict | Abs Bonferroni | 0/2500=0.000 [0.000, 0.001] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| reference_window_conflict | Abs max-t | 0/2500=0.000 [0.000, 0.001] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| reference_window_conflict | Log-ratio pointwise t | 0/2500=0.000 [0.000, 0.001] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| reference_window_conflict | Log-ratio Bonferroni | 0/2500=0.000 [0.000, 0.001] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| reference_window_conflict | Log-ratio max-t | 0/2500=0.000 [0.000, 0.001] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| common_bias_null | Abs pointwise t | 2500/2500=1.000 [0.999, 1.000] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| common_bias_null | Abs Bonferroni | 2500/2500=1.000 [0.999, 1.000] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| common_bias_null | Abs max-t | 2500/2500=1.000 [0.999, 1.000] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| common_bias_null | Log-ratio pointwise t | 2500/2500=1.000 [0.999, 1.000] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| common_bias_null | Log-ratio Bonferroni | 2500/2500=1.000 [0.999, 1.000] | not applicable | 0/2500=0.000 [0.000, 0.001] |
| common_bias_null | Log-ratio max-t | 2500/2500=1.000 [0.999, 1.000] | not applicable | 0/2500=0.000 [0.000, 0.001] |

![Family-wise false certification and partial-null power](familywise_calibration.png)

![Abstention, branch conflict, and common-bias diagnostics](abstention_bias_diagnostics.png)

## Interpretation

The Gaussian-null table is the direct calibration check. Pointwise testing leaves the full candidate/branch family unadjusted; Bonferroni gives a conservative reference; max-t uses observed branch correlation and must be judged by its repeated-trial CP interval. The partial-null scenario reports power for candidate A separately from false certification among null candidates B–D.

The heavy-tail and one-dataset-outlier scenarios are stress tests. If a mean-based rule certifies an outlier-contaminated candidate, multiplicity correction has not made the score robust to influential datasets; the next CPU method comparison should add a predeclared robust estimator such as a trimmed paired mean or Huber score, recalibrated on independent datasets.

At the near-zero baseline, relative methods must abstain under the frozen risk floor. The conflict scenario checks whether a certificate survives every window/reference branch. The common-bias scenario deliberately makes all candidates look improved while the physical truth is null; no statistical correction can detect that without an independent anchor or model-validity diagnostic.

The absolute threshold is proportional to the synthetic baseline scale. A production study must choose an absolute risk margin from physical units before seeing outcomes, and must use independent anchor data to test common reference bias. Until then physical_score remains null.

## Reproduction and provenance

Run commands: first register the frozen protocol with python -m tasks.pion_projection.familywise_score_mc --preregister, then execute python -m tasks.pion_projection.familywise_score_mc --run. Verify saved hashes and raw archive shapes with python -m tasks.pion_projection.familywise_score_mc --verify.

The protocol and source hashes were frozen before simulation. Raw paired baseline/candidate risk arrays are saved in the scenario NPZ files; trial-level certification outcomes are in trial_outcomes.csv.gz. The output hashes and runtime versions are listed in execution_provenance.json.

Protocol SHA-256: e99d5c91fc96fffb8a1e42f42ca81389f5057de9ba412e9ed1a0ace254157493
Source SHA-256: 5de4797a64508e9a575df16b11a4972c13e670ca4ad5ae94c97b166dac66ab17
