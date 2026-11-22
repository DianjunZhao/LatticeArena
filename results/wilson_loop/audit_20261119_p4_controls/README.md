# P4 synthetic gate controls (not stout or APE measurements)

Protocol was written before simulation to protocol.json. Budget: 40 independent datasets per control, 80 synthetic configurations/16 blocks each, two paired estimator labels; 100 outer ×100 inner. No hyperparameter search. raw.json retains block loops, potentials/SE/spread and every ratio draw. Seed is fixed; all numbers are synthetic_CPU, physical measurement NOT_RUN.

Hypothesis: exchangeable equal-noise labels should not show systematic improvement; common two-state contamination should cause abstention even when legacy spread passes. The two labels are **not implemented stout/APE operators**. The independent synthetic anchor E0=.5 is known exactly by construction and unavailable in real production. Anchor quality here is therefore an oracle stress control, not a certified production gate.

| control | PASS | ABSTAIN | FAIL | legacy PASS | improvement datasets | intervals containing 1 |
|---|---:|---:|---:|---:|---:|---:|
| null | 78 | 2 | 0 | 80 | 0 | 40 |
| two_state_common_bias | 0 | 80 | 0 | 80 | 0 | 36 |

Gate counts have denominator80 (two correlated label decisions per dataset), comparison counts denominator40. Do not treat bootstrap draws or the80 decisions as independent experiments. FAIL means invalid input; these finite Gaussian-noise realizations produced no invalid paths, so zero FAIL is not a general robustness proof. ABSTAIN is an expected successful detection in the bias control. Per-dataset intervals and failure/abstention examples are retained in raw.json. Rates from40 datasets have substantial Monte Carlo uncertainty; no claim of calibrated physical significance or general coverage.

Physical stop: no stout physical kernel or real gauge/HMC observable was generated. Synthetic loops cannot establish gauge covariance, overlap gains or cost of stout. Before GPU/production comparison require a frozen stout definition, CPU small-gauge covariance/unitarity/time-locality checks, actual F4 receipts, independent validation samples and external matched search/time budget. The present artifact closes only null/common-bias statistical preflight. If the real E0 anchor is unavailable, this oracle gate cannot be transferred; retain conditional-only/abstain instead of inventing an anchor. No new physics measurement started.
