# Pion projection on two machines

Each directory contains a diagnostic figure and selected fields from one frozen validation report. The JSON includes the SHA-256 of its source report, the split IDs, candidate risks and the reference failure reasons.

| Run | Development / gap / validation | Tuned Gaussian risk divided by signed-mixture risk (95% interval) |
| --- | --- | --- |
| Local RTX 3060 · [summary](pion_projection/rtx3060/summary.json) · [figure](pion_projection/rtx3060/pilot_results.png) | 30 / 5 / 15 | 7.03 [0.98, 14.09] |
| Kunshan DCU · [summary](pion_projection/kunshan-dcu/summary.json) · [figure](pion_projection/kunshan-dcu/pilot_results.png) | 60 / 10 / 30 | 1.63 [1.40, 2.19] |

Both runs used a quenched 16⁴ ensemble and an SLSQP-optimized signed mixture. Both failed the reference checks, so every official score is null. The ensembles and splits differ; the ratios describe within-run comparisons.

The local run is described in the [pilot report](../doc/pion_projection_results.md). The Kunshan example comes from the [archived run at the reviewed revision](https://github.com/Greyyy-HJC/LatticeArena/tree/b3f03a7c3dd110bf272b4d09f823b9c75cd03b7c/results/pion_projection/s16t16_v1). Use an ignored directory under `results/` for working data, frozen submissions and generated reports.

### A spatial operator designed by a coding agent

On the RTX 3060, Codex submitted one [bent-shell operator](../tasks/pion_projection/submissions/bent_shell.json)
through the terminal interface. Its weights were −0.08 on the local term, 0.52
on the straight three-link orbit and 0.56 on the bent three-link orbit. Each of
the 45 correlators was computed from the cached point propagator and spatial
gauge links. The operator was frozen after 30 development configurations.

On the 15 previously used validation configurations (three blocks), its risk was
0.00482. The baseline-to-candidate risk ratios were 103.0 for the local sink
(95% paired interval 38.8–507.2), 0.834 for the tuned Gaussian (0.198–8.73),
and 0.119 for the signed mixture (0.0715–1.48). The latter two intervals include
one. The common reference failed its checks, so these are pilot diagnostics.
The [normalized 2pt curves](pion_projection/rtx3060/bent_shell_2pt.png) and
[folded correlators, errors and risk components](pion_projection/rtx3060/bent_shell.json)
show how the three extended sinks differ at early times.

### Local axial-current cross-check

On the same 30 RTX 3060 development configurations, the paired A4P minus PP
effective-mass difference at `t/a = 7` was −0.0031 (95% interval −0.0119 to
0.0057). Both masses continued to fall from 6 to 7, by 0.0409 for A4P and
0.0513 for PP. These six blocks give no evidence of a common stable plateau
over that range. [Effective masses and paired intervals](pion_projection/rtx3060/axial_check.json).
