# Pion χ² reference-subgate CPU calibration

This independent run expands the C2 smoke only for the 5% χ² reference subgate. It does not run the full certificate and does not establish physical coverage.

## Frozen design and outcomes

Each of the nine scenario × block cells has 1000 independent synthetic development datasets. A failed/non-finite fit remains in the denominator as INVALID; valid-p conditional rates are also reported. Intervals are exact two-sided 95% Clopper–Pearson intervals.

| Scenario | Blocks | Reject | Pass | Invalid | Reject rate over planned N (CP95) | Pass rate over planned N (CP95) |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| ground_state_null | 6 | 151 | 849 | 0 | 0.151 [0.129, 0.175] | 0.849 [0.825, 0.871] |
| ground_state_null | 12 | 54 | 946 | 0 | 0.054 [0.041, 0.070] | 0.946 [0.930, 0.959] |
| ground_state_null | 24 | 18 | 982 | 0 | 0.018 [0.011, 0.028] | 0.982 [0.972, 0.989] |
| single_cosh_misspecified | 6 | 769 | 231 | 0 | 0.769 [0.742, 0.795] | 0.231 [0.205, 0.258] |
| single_cosh_misspecified | 12 | 921 | 79 | 0 | 0.921 [0.903, 0.937] | 0.079 [0.063, 0.097] |
| single_cosh_misspecified | 24 | 998 | 2 | 0 | 0.998 [0.993, 1.000] | 0.002 [0.000, 0.007] |
| pure_excited_wrong_state | 6 | 249 | 751 | 0 | 0.249 [0.222, 0.277] | 0.751 [0.723, 0.778] |
| pure_excited_wrong_state | 12 | 88 | 912 | 0 | 0.088 [0.071, 0.107] | 0.912 [0.893, 0.929] |
| pure_excited_wrong_state | 24 | 33 | 967 | 0 | 0.033 [0.023, 0.046] | 0.967 [0.954, 0.977] |

![Subgate calibration and structural negative control](subgate_calibration_diagnostic.png)

## Interpretation and limits

The correctly specified ground-state null estimates rejection calibration for this generator and the frozen covariance/fit settings. The misspecified single-cosh scenario probes rejection sensitivity. The pure-E1 scenario checks state identifiability: a good single-cosh fit can accept the wrong energy. These are synthetic results; none validates a production anchor or the complete reference gate.

Do not combine this independent run with `certificate_calibration_v1`, full-gate amendment02/03, or family-wise v1–v3. See `protocol.json`, `preregistration.json`, `raw_outcomes.json`, and `execution_provenance.json` for the frozen design, per-dataset records, seeds, hashes, and artifact digests.

Reproduce with `python -B -m tasks.pion_projection.certificate_subgate_mc --run`; verify with `python -B -m tasks.pion_projection.certificate_subgate_mc --verify`.
