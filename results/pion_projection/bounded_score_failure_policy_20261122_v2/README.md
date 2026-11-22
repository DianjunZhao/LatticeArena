# Bounded block-MSE: handling failed evaluation blocks

**Status: analytic design sensitivity only. No correlator, production, GPU, anchor, validation, or holdout input was read. `physical_score=null`.**

## Scope

- Goal: make the missing-block rule explicit for the user-accepted bounded block-MSE estimand.
- Inputs: the existing symbolic bound and user-required sealed-data boundary; no measured values.
- Deliverable: two conditional policies, a pure CPU bound function, focused tests, and a dimensionless figure.
- Acceptance: preserve all planned blocks, distinguish estimator failure from identity/run failure, and retain `NOT_READY`.

## Formula

Let `N` be planned independent evaluation blocks, `f` failed blocks, `phi=f/N`, `R=u-l`, and `mu_valid=mean(d_j over valid blocks)/R^2`, where `d_j=(b_j-A)^2-(c_j-A)^2`. If each failed block is assigned the minimum possible paired improvement `-R^2`, then the all-planned coded mean is `R^2[(1-phi) mu_valid-phi]`. A conditional one-sided bound is

```text
L/R^2 = (1-phi)*mu_valid - phi - sqrt(2*log(F/alpha_s)/N) - 2*(B/R)
certify only if L/R^2 > delta_star/R^2
```

Solving for the valid-block mean gives `mu_valid > (delta_star/R^2 + sqrt(2*log(F/alpha_s)/N) + 2*B/R + phi)/(1-phi)`. At `phi=0`, this reduces to the existing bounded score. For `phi>0`, the missing-block penalty is added without shrinking the planned denominator.

![Failure-policy sensitivity](failure_sensitivity.png)

The plotted lines use only an algebraic illustration (`F=2`, `alpha_s=0.05`, `B/R=0`, `delta_star/R^2=0`). The horizontal `mu_valid/R^2=1` line is the largest possible improvement under the bounded range. Lines above it indicate that this illustrative bound cannot become positive, even with the best possible valid blocks. A nonzero anchor bound or practical threshold moves every line upward. At small `N`, failure fractions are discrete multiples of `1/N`; the continuous x-axis is for sensitivity visualization, not simulated observations.

## Policy comparison and validity boundary

| Policy | Missing block | Meaning |
|---|---|---|
| Hard abstention | Any planned block missing → no score | Retains the pure conditional MSE target; inference is unavailable for that run. |
| Worst-case coding | Missing block contributes `-R^2`; keep denominator `N` | Defines a failure-augmented operational estimand. It bounds the original latent MSE contrast only if every failed block has a well-defined counterfactual pair inside `[l,u]`. |
| Run-wide or identity failure | Abort the complete comparison | Invalid provenance, split overlap, hash mismatch, or common infrastructure failure is not a random block outcome and must never be imputed. |

The anchor correction `2BR` is valid only for independently covered anchors and bounded successful block estimates. The Hoeffding term still requires independent planned blocks and a fixed family. If convergence failure means the estimator has no defined output, worst-case coding is a new deployment utility; it must not be described as physical mass MSE. The current D source–sink identity/reference failures remain hard gates.

## Decision flow

```text
protocol / split / input identity failure?
  yes -> abort whole comparison; no imputation; physical_score=null
  no  -> block-level method failure?
           none -> use the existing bounded block-MSE rule
           any  -> does a bounded counterfactual estimate exist for every failed block?
                    yes -> worst-case code -R^2; report it as a changed estimand
                    no  -> hard abstain, or approve a separate failure-utility target
```

This analysis does not choose the Pion mass range, clipping rule, physical block identity, anchor source/bias bound, `delta_star`, or production failure policy. It does not change `single-cosh FAIL`, M2 `ABSTAIN/NOT_READY`, sealed E/D splits, or the physical score. Keep the TODO open until those scientific inputs and measurement-stream identity gates are reviewed.

Rebuild this deterministic artifact into a new directory with `python3 -B -m tasks.pion_projection.failure_aware_bounded_score --output NEW_DIRECTORY`.
