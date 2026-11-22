# Learned-smear comparison: production protocol freeze draft

**Status:** `DRAFT_NOT_FROZEN`; no production RunSpec or GPU authorization. This draft separates constraints already supported by the repository from decisions that require researcher review. Any run using the current failed Pion reference remains `diagnostic_only` with `physical_score=null`.

## 1. Primary question and scope

The user has fixed two confirmatory contrasts (F=2): **C1: trainable-W smear versus same-budget SLSQP; C2: trainable-W smear versus one fixed strong spectral baseline**, using one frozen held-out objective and common paired configuration IDs. Gaussian and fixed-W are secondary/mechanism controls. Additional confirmatory claims about them require an explicitly enlarged family before blind access. The primary implementation must train the smear parameters from fit configurations. A fixed random $W$ with fitted coefficients, a learned initializer, and a learned restart policy are separate methods; they may be secondary arms but cannot be reported as learned-smear evidence.

The P3 seven-power/nested-$Q$ × SLSQP/Powell 2×2 is a separate operator-class/optimizer experiment. It cannot answer this learned-smear question and must not replace the two fixed confirmatory contrasts.

### 1.1 Concrete trainable-$W$ candidate and current code boundary

The current v9 implementation is **not** a trainable-$W$ model. In `train.py`, `model_space()` draws $W$ from a seeded Gaussian and `main()` keeps it fixed while `optimize()` adjusts only $\theta=(c,v_1,\ldots,v_H)$ with Powell. `features.py` constructs two link-centered plaquette invariants per spatial direction, applies $\tanh(W_h\cdot z_\mu(x))$, and subtracts each feature's spatial mean. This is a learned coefficient field over a fixed random feature map; v9's IDs 70–99 are also already observed.

Current source snapshot hashes (for locating the implementation only; re-compute and bind all dependencies when freezing a new RunSpec):

| File | SHA-256 |
| --- | --- |
| `tasks/optimize_gaussian/train.py` | `e969db11bebba374e5617026f3c8f38aa129d7be4fa66167e98dae889c81fb27` |
| `tasks/optimize_gaussian/features.py` | `2c2f7d37fedbd101ed67377545f737580c88c61be84a7498cc8cfa464af33cf0` |
| `tasks/optimize_gaussian/kernels.py` | `9b95f4d1207041f15cdddfaf18ad341c43a4c80f4e9c6071cfeac4d20fd4fc77` |

A minimally changed trainable-$W$ candidate can reuse that feature/kernel contract:

\[
z_\mu(x)=\big(s_\mu(x),p_\mu(x)\big),\quad
\phi_h(\mu,x;W_h)=\tanh\!\left(W_h\cdot z_\mu(x)\right),\quad
\widetilde\phi_h=\phi_h-\langle\phi_h\rangle_{\vec x},\quad
a_\mu(x)=c+\sum_{h=1}^{H}v_h\widetilde\phi_h(\mu,x;W_h),
\]

where $s_\mu,p_\mu$ are the sum and product of the two link-centered plaquette scalars already emitted by `directional_features`. Share each $W_h$ and $v_h$ across all three spatial directions. The candidate operator remains

\[
K(W,v,c)=G^m\!\left[I+\sum_\mu\left(M_{a_\mu}T_\mu+M_{\tau_{-\mu}a_\mu}T_\mu^\dagger\right)\right]G^m.
\]

The inputs $z_\mu$ are gauge-invariant scalars; the shared direction map preserves the existing cubic-symmetry construction. For real $a_\mu$, pairing the backward coefficient as $a_\mu(x-\hat\mu)$ makes the hop correction Hermitian, and the two-sided $G^m$ sandwich preserves Hermiticity when $G$ is Hermitian. These are algebraic properties to recheck in the new implementation, not evidence that the kernel is positive or physically superior. Positivity, normalization, parameter bounds, feature scaling, and $W$ regularization remain protocol decisions.

One possible training path is joint differentiable optimization of $(W,v,c)$ on fit IDs, followed by a constrained SLSQP polish of $(v,c)$ with $W$ frozen. An alternating profile optimizer is a separate arm because its inner-solver and hypergradient costs differ. For either path, count feature construction, gradient/Jacobian probes, training, polishing, inference, and GPU synchronization in the same cost ledger. Include a fixed-random-$W$ / fitted-$\theta$ arm with the same feature family to isolate the effect of learning $W$; also compare against Gaussian, the existing $H^n$ / SLSQP candidate, and a specified Chebyshev/spectral baseline. The two fixed primary contrasts are trainable-$W$ versus the strong spectral and SLSQP baselines; trainable-$W$ versus fixed-$W$ is a mechanism check.

**Theory boundary:** if the trainable class contains every allowed fixed-$W$ candidate and uses the same training objective, its exact global training minimum cannot be higher than the fixed-$W$ minimum. This does not order held-out risk: additional $W$ degrees of freedom can overfit. Nor does it prove superiority over $H^n$ / SLSQP, whose feasible function class is different. A defensible advantage therefore requires paired held-out gauge configurations, complete failure/abstention denominators, and total-cost accounting; better training risk alone is not evidence.

The isolated [CPU trainable-$W$ prototype and diagnostic](trainable_w_cpu_prototype_20261121/README.md) now verify analytic versus finite-difference gradients, a nonzero $W$ update, gauge/kernel covariance, all 48 cubic/parity signed permutations with reversed-link anchor handling, Hermiticity, and a deterministic same-family teacher fit. It is deliberately only a synthetic coefficient-fit: it does not test the Gaussian sandwich, positivity, physical risk, SLSQP, or held-out gauge-ensemble generalization. The actual production `train.main` path remains fixed-$W$ and this prototype is not integrated. Before production use, the real measurement objective, reference, paired split, fixed-$W$ mechanism arm, shuffle/null controls, solver gate, and cost budget still need a researcher-reviewed protocol; the failed Pion reference keeps any current score `diagnostic_only`.

### Fixed strong-baseline recommendation and accounting

Recommend degree-4 Chebyshev for C2 based on the [CPU operator-level diagnostic](trainable_w_operator_cpu_20261121_final/README.md). Its heat-kernel target favors spectral functions; the result does not prove physical optimality. The reviewed protocol must freeze degree=4, spectral scaling/operator definition, coefficient domain, constraints, normalization and fitting rule before blind access. No blind tuning of degree or baseline is allowed. The exact physical contract remains subject to review; reference, r_star, α, sample size and physical effect are not set here.

C1/C2 use the same frozen objective/reference, paired IDs/source/probe/precision and accounting rules. Freeze common objective-call and walltime caps separately, including restarts and hyperparameter selection; count feature/basis construction, gradients/Jacobians, setup/training/inference/solve and failed attempts. A direct spectral solve has distinct linear-algebra cost and cannot be declared equivalent to one expensive black-box call. Report parameter counts, operator range and admissible domains: equal budgets do not imply equal capacity. Preserve common block resampling for both contrasts; recommend Bonferroni simultaneous bounds with α still TBD, or another explicitly calibrated family-wise procedure.

## 2. Evidence and constraints already established

| Item | Current evidence | Consequence for a new run |
| --- | --- | --- |
| Historical v9 model | Refit coefficients over a fixed random $W$; its test IDs 70–99 were already observed and overlap Pion validation | Do not call it trainable $W$ and do not reuse it as a blind comparison |
| CPU initializer studies | Short-budget gains over zero/random SLSQP are conditional; the spectral baseline is slightly better in IID cells and high-budget SLSQP is better; total-cost advantage is not stable | Do not repeat the same synthetic labels; preserve these as feasibility diagnostics only |
| Pion reference | D0–99 single-cosh reference gate fails; M2 confirmation remains `ABSTAIN/NOT_READY` | Any score using it is `diagnostic_only`; no physical superiority claim |
| D-chain point propagators | Existing D0–99 inputs and trajectory identity were verified by the adapter audit | Reuse verified point propagators where protocol-compatible; do not repeat the same inversion |
| Shared split | D0–59 fit, D60–99 development, D100–139 embargo/gap, D140–199 shared sealed holdout; all three tasks must freeze their candidates and endpoint before shared access | Keep D140–199 unopened until joint hashes and one-time unblinding plan are frozen |

Supporting records: [v9 provenance audit](../../results/optimize_gaussian/v9_provenance_audit_v1/README.md), [CPU operator initializer](../../results/optimize_gaussian/cpu_operator_initializer_v1/README.md), [cost amortization](../../results/optimize_gaussian/cpu_initializer_amortization_v1/README.md), [D-chain propagator audit](../../results/optimize_gaussian/d_chain_propagator_reuse_audit_20261120/README.md), and [Pion closure](../../results/pion_projection/s16t16d_closure_20261120/README.md).

## 3. Freeze table

`TBD` entries are deliberate. Do not fill them from old pilot values, CPU toys, or observed test outcomes.

| Protocol field | Draft constraint or recommendation | Researcher decision still required |
| --- | --- | --- |
| Primary arm | Trainable $W$ is primary; fixed C1 versus same-budget SLSQP and C2 versus a fixed strong spectral baseline (F=2). Gaussian/fixed-W are secondary/mechanism controls. | Freeze the actual parameterization, feature family, symmetry constraints, and whether any learned initializer/restart is a separately powered secondary arm. |
| Objective and reference | Use one identical frozen objective and target in every arm. Until an independent reference passes, the result remains `diagnostic_only`. | Freeze the physics target, reference model/data, fit window, amplitude treatment, covariance, and reference pass/abstention gate. |
| Split | Fit 0–59; development 60–99; embargo 100–139; shared holdout 140–199 sealed. v9 IDs 70–99 are already observed. | Confirm whether existing D0–99 data are protocol-compatible for development; define the independent-block unit and any new measurement IDs before execution. |
| Pairing | Same configuration IDs, gauge inputs, source/probe, target, precision, and stopping rule in every arm; preserve complete ordered ID lists. | Freeze the paired estimand (risk ratio or difference), resampling hierarchy/block length, confidence level, zero-denominator rule, and incomplete-pair handling. |
| Practical effect | Improvement must exceed a preregistered minimum, with failures and cost considered. | Freeze the minimum meaningful effect $r_\star$, direction, interval rule, and whether the primary bound is multiplicity-adjusted. Do not reuse the old illustrative 1.2 value without approval. |
| Solver acceptance | Explicit protocol fields: objective-call cap, walltime cap, KKT residual definition/tolerance, solver-success rule. Current KKT is a finite-difference diagnostic, not a QUDA residual. | Decide whether KKT is a valid gate for this objective, its tolerance, treatment of nonsmooth points, success criteria, and whether a separate physical residual is required. |
| Fair budgets | Report objective-call and total walltime comparisons separately. Count setup, training, inference, solve, I/O and teardown according to a single frozen rule; show GPU memory. | Freeze per-arm caps, gradient/probe accounting, restart allocation, cold/warm cache treatment, and training-amortization deployment count. |
| Statistics and multiplicity | F=2 fixed contrasts; independent configurations/blocks are sampling units. Recommend Bonferroni one-sided (1−α/2) bounds for family-wise simultaneous coverage at least 1−α, without requiring independent contrasts. | α remains TBD; freeze method, estimand, thresholds, CI precision/power, sample size and stop rule. Gaussian/fixed-W claims require an enlarged predeclared family; descriptive CIs do not replace simultaneous bounds. |
| Failure/abstention | Preserve every planned arm and denominator; distinguish input mismatch, reference failure, solver failure, nonfinite output, timeout, residual rejection, and missing paired result. | Freeze per-case handling and the run-level status mapping (`PASS`, `FAIL`, `INCONCLUSIVE`, `ABSTAIN`, `NOT_RUN`). |
| Provenance | Hash protocol, source, gauge/propagator inputs, reference, environment, device, and outputs in a no-clobber RunSpec/receipt chain. | Freeze required device/runtime fields and the exact artifact list before launch. Missing historical v9 propagator bytes/receipt remain missing; do not backfill them. |

## 4. Execution gates

1. **Protocol review:** complete the decision column above and bind protocol/source hashes. No sealed IDs are read.
2. **Input preflight:** build a no-clobber RunSpec; verify exact per-arm IDs, links/probes, source/sink conventions, propagator hashes, residual receipts, precision and environment. A valid CPU preflight is not execution authorization.
3. **Authorized runtime smoke:** in an approved GPU environment, run one bounded start/interruption/recovery smoke and retain device cleanup, memory, and elapsed-time evidence.
4. **Production comparison:** only after reference approval, statistical freeze, data authorization, and successful smoke. Keep the 2×2 P3 experiment separate from the learned-smear comparison.
5. **Blind evaluation:** open D140–199 only once after Pion/Optimize/Wilson candidates, scoring endpoints, exclusions, and analysis code hashes are jointly frozen.

## 5. Required diagnostic package

Every CPU design diagnostic and production result must include a readable text report. For method-comparison diagnostics and production comparisons, include:

- paired held-out risk differences/ratios with intervals and the number of complete/incomplete pairs;
- best-so-far objective and residual against both objective calls and elapsed time;
- setup, training, inference, solve, total walltime, and memory cost by arm;
- KKT/physical residuals, solver status, timeouts, budget truncations, nonfinite values, and abstentions with full denominators;
- one paragraph stating which claim the result supports, which it cannot support, and why.

For a negative or inconclusive result, retain the same plots and denominator tables. Do not report a physical score while the reference gate is failed.

For software integration or preflight-only checks, report the data/control flow, identity and artifact receipts, relevant objective/residual trace, status, and scope limits. Do not manufacture a paired-risk comparison or physical cost breakdown when no paired methods or physical execution were run.

## 6. Current handoff

The CPU training entry has a synthetic `train.main` → real Powell/solver-contract → worker process → parent artifact-hash smoke ([report](../../results/optimize_gaussian/cpu_train_main_supervisor_v2/README.md)); the separate trainable-$W$ parameterization prototype is linked above. Both are software-path evidence only. D01 C1/C2 are fixed by the user; the degree-4 baseline now has a concrete CPU candidate in §7. The user has asked to keep `NOT_READY/UNCERTIFIED` and sealed-data status, so D04 reference, D06 minimum meaningful effect and other scientific values remain unresolved; this draft stays a review proposal. Continue with mathematical/interface review and the D01–D19 alternative table. Integrate trainable-$W$ into the real measurement/objective path only after the protocol choices are approved; stop before production launch whenever reference, statistics, input identity, or authorization gates are unresolved.

## 7. 2026-11-22 D11 spectral baseline candidate; no freeze

The user selected the two-contrast family (C1 trainable-W vs same-budget SLSQP; C2 trainable-W vs one fixed strong spectral baseline) and requested the current status and data seal be preserved. The D11 CPU proposal is documented with a response plot in [the degree-4 Chebyshev contract report](../../results/optimize_gaussian/degree4_chebyshev_contract_20261122_v4/README.md), implemented in [`chebyshev_baseline.py`](chebyshev_baseline.py), and has **19 focused tests passing**.

For the existing periodic three-dimensional covariant hopping operator, the candidate assumes unitary SU(3) links and periodic boundaries, with spectrum `H∈[-12,0]`. Define `y=I+H/12∈[0,1]` and

```text
P4(y) = Σ_{i=0}^4 b_i C(4,i) y^i (1-y)^(4-i)
0 ≤ b0 ≤ b1 ≤ b2 ≤ b3 ≤ b4 = 1
```

The Bernstein controls bound the response to `[0,1]`, normalize `P4(1)=1`, and make it nondecreasing in `y` (thus nonincreasing with `−H`). Conversion to Chebyshev form uses the same polynomial for evaluation; it does not add degrees of freedom. These properties are conditional on the operator/spectrum assumptions. They do not establish physical optimality or fair production cost; conditional sandwich positivity is reviewed below.

#### Algebraic compatibility with the current Gaussian sandwich

The current `train.py::gaussian` calls `apply_kernel` repeatedly with a spatially constant coefficient `alpha`. Under periodic spatial boundaries and unitary links, that kernel is Hermitian. With `H=sum_i(U_iT_i+(U_iT_i)^†-2I)`, the one-step Gaussian map is `G=I+alpha*sum_i(U_iT_i+(U_iT_i)^†)=(1+6*alpha)I+alpha*H`, so it is also a polynomial in `H`. Since the proposed `P4(H)` is positive semidefinite, the identical two-sided sandwich obeys

```text
<psi | G^m P4(H) G^m | psi> = <G^m psi | P4(H) | G^m psi> >= 0
```

This remains true without assuming that `G` itself is positive. The current trainable-W path likewise forms a Gaussian-preprocessed field and then evaluates the candidate correlator, so a spectral arm can reuse the same preprocessed fields. This establishes conditional algebraic compatibility only. The existing code does not normalize each Gaussian step: its zero-mode eigenvalue is `1+6*alpha`, so the outer factor changes full-kernel normalization by `(1+6*alpha)^(2m)`. `alpha`, `m`, any compensating normalization, and whether the production estimand should include that scale remain unresolved protocol choices. The CPU filter prototype applies only `P4(H)` and has not integrated the sandwich.

```text
same frozen objective, links/source/probes, fit/dev/test IDs
  ├─ trainable-W arm: fit W,v,c on fit IDs
  ├─ SLSQP arm: optimize the predeclared common parameterization/restarts
  └─ spectral arm: fit b0..b3 under monotone box constraints, fix b4=1
       → compare trainable-W with SLSQP (C1) and spectrum (C2)
       → account separately for objective calls and end-to-end walltime
       → retain every planned arm, timeout, solver failure, missing pair and abstention
```

This is a review-ready candidate, not an approved fixed baseline. The common physics objective/reference, D06 `r_star`, alpha, sample size, solver thresholds, budgets and target normalization remain undecided. Do not use the heat-kernel toy ranking as evidence for this constrained family. No production RunSpec, GPU, new measurement, validation or sealed data were used here. The current full CPU/GPU-free suite is **418 passed, 1 skipped, 1 warning**; see `doc/todo_coverage.md` §12 for the exact command and environment boundary.

### C1 comparability rule

The default interpretation of the user's C1 is an optimizer comparison, so the SLSQP arm must use the same trainable-W function family and fitted variables as the learned arm (currently the CPU prototype is `H=2`, seven real W/v/c scalars), with identical fit IDs, objective, coefficient domain, regularization and stopping semantics. The start/restart scheme is frozen before evaluation and is charged to both objective-call and end-to-end walltime budgets. A learned gauge-to-kernel network or changed basis is a different model class; pairing it against the old SLSQP family would conflate model and solver effects and must be labeled as a composite contrast with an added mechanism control. This is a comparability constraint, not a decision about which learned architecture or domain to use.

| Arm | Model family | Role in the selected family | Required matching |
|---|---|---|---|
| Trainable-W | Shared real W/v/c on common fit IDs | Reference arm for C1 and C2 | Frozen parameterization, objective, precision, failure mapping |
| SLSQP | The same W/v/c family and feasible domain | C1 optimizer comparator | Same fit IDs/objective/regularization, predeclared starts/restarts, objective-call cap and walltime cap |
| Degree-4 spectral | Fixed Chebyshev basis with four monotone Bernstein controls | C2 strong spectral comparator candidate | Same objective/IDs/precision and both budget ledgers; report its different dimension/operator range |

The arms share a target and evaluation IDs; they do not need equal parameter counts. Report setup, basis construction, training/selection, each application, inference/solve, I/O, teardown, failures and abstentions by arm. C1 and C2 stay the only confirmatory contrasts (`F=2`). If C1's parameterization changes, revise its interpretation and the comparison family before any blind access.
