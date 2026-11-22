# HMC chain diagnostic

**Status:** `DIAGNOSTIC_COMPLETE_PHYSICAL_UNCERTIFIED`; `physical_status=NOT_RUN`.

The HMC receipt, every trajectory row, saved-configuration manifest, and raw NERSC files passed identity checks.
The frozen thermalization cut is 400 trajectories. The analyzed production portion has 496 rows, acceptance 483/496 = 0.9738 (exact binomial CP95 [0.9556, 0.9860]).
Production ΔH mean=0.0032033, SD=0.05585; plaquette mean=0.59370738, SD=0.0005366.
The initial-positive-pair estimate gives plaquette τint=4.03 trajectories and a suggested block length ceil(2τ)=9. This is a single-observable finite-chain diagnostic; it is not proof of equilibrium or a physical-score gate.

| Block length (trajectories) | Complete blocks | Remainder dropped | Mean plaquette | SE of block means |
|---:|---:|---:|---:|---:|
| 1 | 496 | 0 | 0.59370738 | 2.41e-05 |
| 2 | 248 | 0 | 0.59370738 | 3.1e-05 |
| 5 | 99 | 1 | 0.59370867 | 4.15e-05 |
| 10 | 49 | 6 | 0.59371542 | 5.12e-05 |
| 20 | 24 | 16 | 0.59371436 | 6.45e-05 |
| 50 | 9 | 46 | 0.59370389 | 8.45e-05 |

## Figures

- `delta_h_histogram.png`: production Hamiltonian change distribution.
- `acceptance_by_trajectory.png`: rolling and overall Metropolis acceptance.
- `plaquette_trajectory.png`: thermalization cut, production trace, and saved configurations.
- `plaquette_autocorrelation.png`: production autocorrelation and initial-positive window.

## Limits

The autocorrelation rule is the initial-positive-pair truncation of the plaquette autocorrelation; the reported block-length table is sensitivity analysis, not an independently calibrated uncertainty prescription. A single chain and one observable do not establish ensemble independence, topological tunneling, or equilibrium. The plots and per-trajectory table are diagnostics only; Wilson-loop fit and stout/APE paired physical results remain separate gates.
