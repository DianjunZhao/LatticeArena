# Cross-chain HMC diagnostic comparison

**Status:** `DESCRIPTIVE_CROSS_CHAIN_CHECK`; `physical_status=NOT_RUN`.

Both runs used separate seeds and independently generated random starts. Each chain’s receipt, trajectory log, manifest, and every saved NERSC payload hash were verified by its own diagnostic.

| Quantity | Chain D | Chain E |
|---|---:|---:|
| Actual / production trajectories | 1396 / 996 | 896 / 496 |
| Configurations (payload hashes checked) | 200 (200) | 100 (100) |
| Acceptance | 0.98594 | 0.97379 |
| Plaquette mean | 0.59361062 | 0.59370738 |
| Plaquette τint (trajectories) | 3.756 | 4.026 |
| ΔH mean | 0.0011732 | 0.0032033 |
| ΔH SD | 0.061837 | 0.05585 |

The absolute plaquette-mean difference is `9.67576e-05`. Its ratio to the combined block-mean SE ranges from `1.01` to `3.29` over block lengths 1, 2, 5, 10, 20, 50 trajectories. At lengths 5, 10, 20 and 50 the ratios are 1.97, 1.60, 1.30 and 1.01. The shift below 2 as blocks lengthen shows why a naive per-trajectory error would overstate the discrepancy; the longest blocks also leave only 19 and 9 blocks, so this is a sensitivity display, not a calibrated test.

Both plaquette traces rise from the declared hot starts to a stable-looking production region. That visual settling, overlapping acceptance intervals, and similar ΔH summaries support a descriptive cross-chain consistency check. They do not establish equilibrium, topological tunneling, or a Pion reference gate.

![Acceptance, ΔH, plaquette, and block-size sensitivity](chain_comparison.png)

## Next measurements

Use D IDs 0–99 for the frozen Pion development set and E IDs 0–59 for the separate-chain anchor. The first 60 Pion anchor IDs are from E and the remaining 40 are reserved. D IDs 140–199 are a shared unopened holdout for Pion, Optimize, and a possible Wilson stout/APE comparison; freeze all participating task protocols and candidate sets before any task opens them, and never treat reuse across tasks as independent validation evidence. HMC diagnostics remain separate from Pion measurements and Wilson-loop/Stout–APE physics results.
