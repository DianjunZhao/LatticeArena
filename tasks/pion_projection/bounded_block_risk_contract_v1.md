# Pion bounded block-risk score contract v1

**Status: `DRAFT_NOT_READY`.** This is a versioned estimand/calibration draft, not a frozen physical scoring protocol. All study-specific quantities below remain unset. It reads no correlator, anchor, gap, validation, or holdout data; it never emits `physical_score`.

## Estimand and score map

For a predeclared candidate family and planned blocks, let `A` be the E-anchor estimate and `m*` the corresponding target value. The current candidate score component is the paired squared-error contrast

```text
D_i(A) = (A - y_reference,i)^2 - (A - y_candidate,i)^2
Z_i    = clip(D_i(A) / R^2, -1, 1)
theta_N = (1/N) sum_i E[Z_i | frozen protocol, shared anchor]
```

Positive `theta_N` favors the candidate on this **finite planned-block bounded estimand**. It is distinct from the original ensemble-risk and is not itself a physical score. The proposed clipping and failure policy are the current helper's behavior; both still require protocol freeze before confirmation data are examined.

Every planned block remains in `N`. A valid block uses its clipped `Z_i`; a failed block is assigned `-1`, the worst normalized improvement. With failure fraction `phi_hat`, the coded planned mean is `(1-phi_hat)*Zbar_valid - phi_hat`. An all-failed panel returns `ABSTAIN_NO_VALID_BLOCKS`; it has no lower bound.

## Conditional calibration

Let `F` be the fixed comparison family, `chi` a proven upper bound on the chromatic number of a score-specific dependency graph, `alpha_s` the score error budget, and `alpha_A` the anchor-coverage error budget. The graph's color classes must be jointly independent conditional on the frozen protocol and shared anchor. Under that condition, for `Z_i` in `[-1,1]`:

```text
epsilon = sqrt(2 * chi * log(F / alpha_s) / N)
```

For the squared-error component,

```text
D_i(A) - D_i(m*) = 2 * (A - m*) * (y_candidate,i - y_reference,i)
```

so an anchor bound `|A-m*| <= B` yields normalized correction `2B/R` only when the predeclared prediction difference also satisfies `|y_candidate-y_reference| <= R`. If the score adds variance, fit, or other terms, each needs its own valid range and Lipschitz bound before it enters this contract.

The candidate lower bound is

```text
LCB = (1-phi_hat)*Zbar_valid - phi_hat - epsilon - 2B/R
```

If `A` is covered only with probability at least `1-alpha_A`, require `alpha_s + alpha_A <= alpha_total`; multiple anchor targets need a predeclared allocation. A statistical certificate would require `LCB > delta_star/R^2` and a separately passing physical reference/model-identification gate. Missing assumptions or gates yield `ABSTAIN/NOT_READY`; `physical_score` remains null in this helper.

## Inputs that must be frozen or evidenced

|Field|Current value|Required decision/evidence|
|---|---|---|
|Target `m*`, observable, physical units and interpretation|`null`|Name the matched E-anchor target and units; identify what physical quantity it represents|
|Scale `R` and prediction-difference bound|`null`|Give units, range and a reason that `|y_candidate-y_reference| <= R` holds for every included score|
|Clipping interval and score components|candidate `[-1,1]`; not frozen|Confirm clipping before confirmation; enumerate all terms and their individual bounds|
|Failure coding|candidate `-1`; not frozen|Confirm which failures receive worst score and which invalidate/abstain a whole panel|
|Planned block count `N` and block identities|`null`|Specify the planned unit and preserve all planned/valid/failed/abstained denominators|
|Dependence graph and `chi`|`null`|Supply a score-specific proof and auditable upper bound, or a different finite-sample concentration theorem with explicit constants|
|Candidate family `F`|`null`|Freeze every comparison entering simultaneous inference|
|Anchor estimate `A`, bound `B`, coverage and independence|`null`|Provide matched E-correlator receipt, source of `B`, coverage model, shared-anchor dependence and conditional independence evidence|
|`alpha_total`, `alpha_s`, `alpha_A`|`null`|Choose in advance and enforce `alpha_s+alpha_A<=alpha_total`|
|Minimum effect `delta_star` and reference gate|`null`|State units, physical interpretation, threshold rationale and independent reference/model-identification pass rule|

## Text decision flow

```text
freeze score and planned blocks
  -> verify score-specific dependence bound and anchor coverage/bias bound
  -> compute coded planned mean - graph penalty - anchor correction
  -> compare LCB with delta_star / R^2
  -> separately require the physical reference/model-identification gate
  -> otherwise ABSTAIN / NOT_READY; physical_score remains null
```

Current analytic, Monte Carlo and exact-enumeration reports test formula behavior under declared synthetic assumptions only. They do not fill any `null` field above. In particular, trajectory spacing is not an independence proof, a bootstrap interval is not a finite-sample dependence theorem, and an assumed anchor support is not an E-anchor receipt.
