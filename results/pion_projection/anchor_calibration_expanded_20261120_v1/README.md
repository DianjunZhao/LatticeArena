# Independent expansion of synthetic C3 anchor calibration

This new independent-seed run expands three decision-relevant C3 scenarios to 400 datasets each. Every dataset has 200 baseline and candidate mass-bootstrap draws; anchor uncertainty is shared between the two arms within that dataset. The anchor is an oracle-centered synthetic value, not a measured physical anchor.

The naive rule uses sd/sqrt(N_boot) and is retained as a pseudo-replication negative control. The single-ensemble paired rule uses the 5th percentile of the paired delta draws without an extra 1/sqrt(N_boot). The independent-repeat estimand is the average per-dataset delta across outer independent datasets. Familywise intervals cover six certification rates and three independent-repeat mean intervals, respectively.

| Scenario | Valid / planned | Naive certified | Paired certified | Independent-repeat mean delta | Familywise dataset-bootstrap CI95 | Independent-repeat SE |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| improvement | 400/400 | 181/400 (0.453, FW-CP95 [0.387,0.520]) | 0/400 (0.000, FW-CP95 [0.000,0.014]) | 0.00406 | [-0.00432,0.01266] | 0.00354 |
| null | 400/400 | 146/400 (0.365, FW-CP95 [0.302,0.431]) | 0/400 (0.000, FW-CP95 [0.000,0.014]) | -0.00842 | [-0.01817,0.00139] | 0.00416 |
| anchor_bias | 400/400 | 199/400 (0.497, FW-CP95 [0.431,0.564]) | 73/400 (0.182, FW-CP95 [0.135,0.239]) | 0.00646 | [-0.01194,0.02478] | 0.00763 |

![C3 independent expansion](anchor_expansion.png)

## Interpretation boundary

This run tests statistical behavior in the frozen synthetic correlator and oracle-anchor worlds. It can quantify outer Monte Carlo uncertainty and compare interval semantics; it does not measure physical anchor reliability, lattice autocorrelation, or a physical score. An anchor-bias scenario is a structural sensitivity, not an estimate of the real anchor bias.

Raw dataset-level masses, delta summaries, certification indicators, seeds, frozen fit protocol/source hashes, and artifact hashes are retained. Verify with `python -B -m tasks.pion_projection.anchor_calibration_expanded --verify`.
