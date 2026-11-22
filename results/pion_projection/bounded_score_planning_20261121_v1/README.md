# Bounded block-MSE planning sensitivity

**Deterministic formula analysis; no new Monte Carlo data and no physical values assumed.**

For loss range width `R=u-l`, block-difference range `[-R^2,R^2]`,
`F` fixed candidates, statistical error allocation `alpha_s`, anchor bias bound `B`,
and practical threshold `delta_star`, the lower-bound rule is

```text
L = d_bar - R^2*sqrt(2*log(F/alpha_s)/n) - 2*B*R
certify only if L > delta_star
```

Writing `beta=B/R` and `g=(d_bar-delta_star)/R^2` makes the planning condition
`g > sqrt(2*log(F/alpha_s)/n) + 2*beta`. The image shows this required normalized
signal across the previously used `n=12/24/100/400` and `F=1/2/4` grid, for the
exact-anchor and uncertain-anchor allocations from the frozen calibration.
The color surface is a deterministic consequence of the bound, not a simulated
power curve or a claim that any plotted `beta` is physically plausible.

![Dimensionless bounded-score planning map](planning_map.png)

As `n` grows, only the statistical term falls; the anchor floor `2B/R` remains.
If the normalized effect gap `g` is no larger than `2B/R`, no block count can
make this certificate positive. When `g>2B/R`, the smallest integer block count
is `floor(2*log(F/alpha_s)/(g-2B/R)^2)+1`.

The table in `summary.json` includes `beta=0.05` only as a labeled algebraic
example to make the anchor penalty visible; it is not a recommended or measured
physical anchor error. Select `R`, `B`, `delta_star`, and `g` from an approved
Pion observable/normalization contract before using the formula for sample-size
planning. The [504000-dataset synthetic calibration](../bounded_score_calibration_20261121_v1/README.md)
remains a separate conditional calibration; this sensitivity map does not
repair the failed reference gate, establish block independence, or create a
physical score.
