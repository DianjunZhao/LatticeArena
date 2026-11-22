# HMC chain diagnostic

**Status:** `DIAGNOSTIC_COMPLETE_PHYSICAL_UNCERTIFIED`; `physical_status=NOT_RUN`.

The HMC receipt, every trajectory row, saved-configuration manifest, and raw NERSC files passed identity checks.
The frozen thermalization cut is 400 trajectories. The analyzed production portion has 996 rows, acceptance 982/996 = 0.9859 (exact binomial CP95 [0.9765, 0.9923]).
Production ΔH mean=0.0011732, SD=0.061837; plaquette mean=0.59361062, SD=0.0005328.
The initial-positive-pair estimate gives plaquette τint=3.76 trajectories and a suggested block length ceil(2τ)=8. This is a single-observable finite-chain diagnostic; it is not proof of equilibrium or a physical-score gate.

| Block length (trajectories) | Complete blocks | Remainder dropped | Mean plaquette | SE of block means |
|---:|---:|---:|---:|---:|
| 1 | 996 | 0 | 0.59361062 | 1.69e-05 |
| 2 | 498 | 0 | 0.59361062 | 2.09e-05 |
| 5 | 199 | 1 | 0.59361069 | 2.61e-05 |
| 10 | 99 | 6 | 0.59360983 | 3.2e-05 |
| 20 | 49 | 16 | 0.59360445 | 3.72e-05 |
| 50 | 19 | 46 | 0.59359253 | 4.48e-05 |

## Figures

- `delta_h_histogram.png`: production Hamiltonian change distribution.
- `acceptance_by_trajectory.png`: rolling and overall Metropolis acceptance.
- `plaquette_trajectory.png`: thermalization cut, production trace, and saved configurations.
- `plaquette_autocorrelation.png`: production autocorrelation and initial-positive window.

## Limits

The autocorrelation rule is the initial-positive-pair truncation of the plaquette autocorrelation; the reported block-length table is sensitivity analysis, not an independently calibrated uncertainty prescription. A single chain and one observable do not establish ensemble independence, topological tunneling, or equilibrium. The plots and per-trajectory table are diagnostics only; Wilson-loop fit and stout/APE paired physical results remain separate gates.
