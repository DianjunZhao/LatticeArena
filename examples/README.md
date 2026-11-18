# Pion projection on two machines

Each directory contains a diagnostic figure and selected fields from one frozen validation report. The JSON includes the SHA-256 of its source report, the split IDs, candidate risks and the reference failure reasons.

| Run | Development / gap / validation | Tuned Gaussian risk divided by signed-mixture risk (95% interval) |
| --- | --- | --- |
| Local RTX 3060 · [summary](pion_projection/rtx3060/summary.json) · [figure](pion_projection/rtx3060/pilot_results.png) | 30 / 5 / 15 | 7.03 [0.98, 14.09] |
| Kunshan DCU · [summary](pion_projection/kunshan-dcu/summary.json) · [figure](pion_projection/kunshan-dcu/pilot_results.png) | 60 / 10 / 30 | 1.63 [1.40, 2.19] |

Both runs used a quenched 16⁴ ensemble and an SLSQP-optimized signed mixture. Both failed the reference checks, so every official score is null. The ensembles and splits differ; the ratios describe within-run comparisons.

The local run is described in the [pilot report](../doc/pion_projection_results.md). The Kunshan example comes from the [archived run at the reviewed revision](https://github.com/Greyyy-HJC/LatticeArena/tree/b3f03a7c3dd110bf272b4d09f823b9c75cd03b7c/results/pion_projection/s16t16_v1). Use an ignored directory under `results/` for working data, frozen submissions and generated reports.
