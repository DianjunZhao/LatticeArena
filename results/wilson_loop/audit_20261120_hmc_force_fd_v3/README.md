# CPU analytic-force finite-difference audit

**Status: `PASS_TOY_CPU_CHECKS`.** This is a derivative and integrator check of the local Python Wilson plaquette action on a periodic $2^4$ SU(3) toy lattice. It is not a production PyQUDA/QUDA force, a GPU/MPI HMC run, or a physical ensemble validation.

## Frozen convention and coverage

The action is the `tasks/wilson_loop/hmc_quality.py` implementation with $\beta=6$. Links are indexed `(mu,x0,x1,x2,x3)` and all four directions are periodic. A link is varied on the left as $U_\mu(x;\delta)=e^{i\delta T_a}U_\mu(x)$. The eight repository generators are Hermitian, traceless, and normalized by $\mathrm{Tr}(T_aT_b)=\delta_{ab}$; the reported force is $F=-\partial S/\partial\theta$ projected in that basis.

Two deterministic fields were used: independent Haar-distributed SU(3) links and near-identity links $e^{i0.15H}$ with random Hermitian traceless $H$. For both fields, every one of the $4\times2^4$ links and all eight generators was checked at five central-difference steps (5120 scalar derivative comparisons total). The action implementation was also compared with a separate explicit coordinate-loop implementation.

## Results

| Field | δ | Components | normalized error q95 | normalized error max |
| --- | ---: | ---: | ---: | ---: |
| haar_links | 1e-03 | 512 | 8.456e-08 | 2.554e-07 |
| haar_links | 3e-04 | 512 | 7.639e-09 | 2.305e-08 |
| haar_links | 1e-04 | 512 | 1.044e-09 | 2.492e-09 |
| haar_links | 3e-05 | 512 | 7.658e-10 | 1.439e-09 |
| haar_links | 1e-05 | 512 | 2.436e-09 | 4.120e-09 |
| near_identity | 1e-03 | 512 | 8.338e-08 | 9.272e-08 |
| near_identity | 3e-04 | 512 | 7.605e-09 | 8.278e-09 |
| near_identity | 1e-04 | 512 | 1.073e-09 | 1.596e-09 |
| near_identity | 3e-05 | 512 | 1.578e-09 | 2.908e-09 |
| near_identity | 1e-05 | 512 | 5.778e-09 | 8.772e-09 |

The normalized error is $|F_{FD}-F|/\max(1,|F|)$, so components near zero do not acquire unstable relative errors. Its q95 decreases by approximately the expected $\delta^2$ factor from $10^{-3}$ to $10^{-4}$, then floating-point cancellation starts to limit gains at the smallest steps. Full component-level data are in `force_fd_components.csv`.

The existing action uses the additive zero point $\beta(6L^3)$ on this isotropic code path, whereas the explicit coordinate implementation uses $\beta(6V)$. For $L=2$, their measured gauge-independent offset is `-288.0` (expected `-288.0`); after subtracting it, the maximum variable-part residual is `2.558e-13`. This offset cancels in force derivatives and $\Delta H$. Across both fields, the maximum force Hermiticity residual was `0.000e+00` and maximum trace residual was `4.441e-16`.

### Leapfrog control

| ε | Steps | |ΔH| | ΔH ratio to previous | Link reversibility max | Momentum reversibility max |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.0400 | 5 | 1.104e-01 | — | 6.866e-16 | 4.965e-16 |
| 0.0200 | 10 | 2.776e-02 | 3.977 | 1.030e-15 | 7.216e-16 |
| 0.0100 | 20 | 6.949e-03 | 3.994 | 1.001e-15 | 1.332e-15 |
| 0.0050 | 40 | 1.738e-03 | 3.999 | 1.747e-15 | 1.159e-15 |

The trajectory length is fixed at 0.2 and the momenta are one deterministic canonical Gaussian draw in the declared orthonormal generator basis. Halving ε gives an approximately fourfold reduction in |ΔH|, consistent with the leapfrog second-order trend; reversing momenta returns links and momenta to floating-point precision.

![Force finite-difference and leapfrog diagnostics](hmc_force_fd.png)

## Interpretation and limits

This closes the CPU analytic-force finite-difference item for the local toy action and strengthens the integrator check by using that analytic force. It does not verify that this toy action, staple convention, link layout, normalization, or force matches the target production HMC implementation. The random link fields are numerical stress controls, not equilibrium gauge configurations. Production ΔH/acceptance, thermalization, autocorrelation, provenance identity, MPI/GPU behavior, and protocol_v4 remain open.

Recheck artifact hashes and derived row counts with `python -B -m tasks.wilson_loop.hmc_force_fd verify`.
