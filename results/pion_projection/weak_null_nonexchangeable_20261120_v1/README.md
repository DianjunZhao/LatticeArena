# Weak-null tail diagnostic for the pion block-risk score

## Question and scope

This independent CPU experiment asks whether the existing studentized paired-block sign-flip result extends from a sharp exchangeable null to a weak null that only fixes the mean risk improvement. Each row is an independent block contribution `d_j`; positive values favor the candidate. It is a method-level diagnostic, not the full ensemble `improvement_certificate`, a physical coverage result, or a selected production score.

The rare-tail null has 90% common blocks centered at +0.30 and 10% rare blocks centered at -2.70, plus independent Gaussian noise of SD 0.20, all divided by SD sqrt(0.85). Thus E[d]=0 and Var(d)=1 exactly, but individual block labels are not sign-exchangeable. At N=24, the probability of seeing no rare negative block is 0.9^24=7.98%; this provides a predeclared high-risk regime for any method that relies on the observed sample to reveal the tail.

## Methods and theoretical boundary

- Paired t: one-sided Student t test of mean block improvement.
- Raw studentized sign-flip: the existing C3 method; its finite-sample randomization rationale is tied to the sharp exchangeable null.
- Centered wild sign-flip t: Rademacher multipliers applied to centered block residuals, with the same studentization. This is a weak-null resampling candidate; this simulation does not prove its general validity.
- Block bootstrap percentile: resamples independent paired blocks and certifies only if the 5th-percentile mean is positive.
- Median-of-means (MoM) bound: nine disjoint groups and known variance upper bound sigma<=1. With group size at least m_min, Chebyshev gives each group a <=1/4 chance of deviating by 2/sqrt(m_min); the median's one-sided failure probability is bounded by P[Binomial(9,1/4)>=5]=0.04893. This is a conservative finite-sample comparator under iid independent blocks and a valid external variance bound. The bound is oracle here: a variance bound estimated from the same small sample does not inherit this guarantee.

The statistical distinction is established in primary literature: [Chung & Romano (2013)](https://doi.org/10.1214/13-AOS1090) distinguish finite-sample exactness under identical distributions from asymptotic validity for equality of parameters with appropriate studentization. [Minsker (2024)](https://doi.org/10.4171/MSL/43) studies median-of-means guarantees for iid finite-variance observations. Neither source validates this pion-specific risk construction or its physical use.

## Monte Carlo size and power

Rates use all planned independent outer datasets; all planned rows are retained. Intervals are exact binomial Monte Carlo intervals, with both pointwise CP95 and Bonferroni-simultaneous CP95 over 30 method-by-cell rates. The four method-vs-sign-flip contrasts use paired dataset-level differences and a simultaneous t interval over 24 contrasts.

| World | Blocks | Method | Certified / planned | Rate | Pointwise CP95 | Simultaneous CP95 |
| --- | ---: | --- | ---: | ---: | --- | --- |
| symmetric_gaussian_null | 24 | paired_t | 177/3000 | 0.0590 | [0.0508, 0.0680] | [0.0463, 0.0737] |
| symmetric_gaussian_null | 24 | raw_studentized_signflip | 171/3000 | 0.0570 | [0.0490, 0.0659] | [0.0446, 0.0715] |
| symmetric_gaussian_null | 24 | centered_wild_signflip_t | 172/3000 | 0.0573 | [0.0493, 0.0663] | [0.0449, 0.0719] |
| symmetric_gaussian_null | 24 | block_bootstrap_percentile | 209/3000 | 0.0697 | [0.0608, 0.0794] | [0.0559, 0.0855] |
| symmetric_gaussian_null | 24 | mom_known_variance_bound | 0/3000 | 0.0000 | [0.0000, 0.0012] | [0.0000, 0.0024] |
| symmetric_gaussian_null | 48 | paired_t | 166/3000 | 0.0553 | [0.0474, 0.0641] | [0.0431, 0.0697] |
| symmetric_gaussian_null | 48 | raw_studentized_signflip | 170/3000 | 0.0567 | [0.0487, 0.0655] | [0.0443, 0.0712] |
| symmetric_gaussian_null | 48 | centered_wild_signflip_t | 164/3000 | 0.0547 | [0.0468, 0.0634] | [0.0425, 0.0689] |
| symmetric_gaussian_null | 48 | block_bootstrap_percentile | 185/3000 | 0.0617 | [0.0533, 0.0709] | [0.0487, 0.0767] |
| symmetric_gaussian_null | 48 | mom_known_variance_bound | 0/3000 | 0.0000 | [0.0000, 0.0012] | [0.0000, 0.0024] |
| rare_tail_weak_null | 24 | paired_t | 319/3000 | 0.1063 | [0.0955, 0.1179] | [0.0894, 0.1251] |
| rare_tail_weak_null | 24 | raw_studentized_signflip | 372/3000 | 0.1240 | [0.1124, 0.1363] | [0.1058, 0.1440] |
| rare_tail_weak_null | 24 | centered_wild_signflip_t | 499/3000 | 0.1663 | [0.1532, 0.1801] | [0.1456, 0.1886] |
| rare_tail_weak_null | 24 | block_bootstrap_percentile | 283/3000 | 0.0943 | [0.0841, 0.1054] | [0.0783, 0.1122] |
| rare_tail_weak_null | 24 | mom_known_variance_bound | 0/3000 | 0.0000 | [0.0000, 0.0012] | [0.0000, 0.0024] |
| rare_tail_weak_null | 48 | paired_t | 316/3000 | 0.1053 | [0.0946, 0.1169] | [0.0885, 0.1240] |
| rare_tail_weak_null | 48 | raw_studentized_signflip | 314/3000 | 0.1047 | [0.0939, 0.1162] | [0.0879, 0.1233] |
| rare_tail_weak_null | 48 | centered_wild_signflip_t | 319/3000 | 0.1063 | [0.0955, 0.1179] | [0.0894, 0.1251] |
| rare_tail_weak_null | 48 | block_bootstrap_percentile | 281/3000 | 0.0937 | [0.0835, 0.1047] | [0.0777, 0.1115] |
| rare_tail_weak_null | 48 | mom_known_variance_bound | 0/3000 | 0.0000 | [0.0000, 0.0012] | [0.0000, 0.0024] |
| rare_tail_improvement_1p5 | 24 | paired_t | 2999/3000 | 0.9997 | [0.9981, 1.0000] | [0.9969, 1.0000] |
| rare_tail_improvement_1p5 | 24 | raw_studentized_signflip | 2999/3000 | 0.9997 | [0.9981, 1.0000] | [0.9969, 1.0000] |
| rare_tail_improvement_1p5 | 24 | centered_wild_signflip_t | 2999/3000 | 0.9997 | [0.9981, 1.0000] | [0.9969, 1.0000] |
| rare_tail_improvement_1p5 | 24 | block_bootstrap_percentile | 3000/3000 | 1.0000 | [0.9988, 1.0000] | [0.9976, 1.0000] |
| rare_tail_improvement_1p5 | 24 | mom_known_variance_bound | 2844/3000 | 0.9480 | [0.9394, 0.9557] | [0.9340, 0.9599] |
| rare_tail_improvement_1p5 | 48 | paired_t | 3000/3000 | 1.0000 | [0.9988, 1.0000] | [0.9976, 1.0000] |
| rare_tail_improvement_1p5 | 48 | raw_studentized_signflip | 3000/3000 | 1.0000 | [0.9988, 1.0000] | [0.9976, 1.0000] |
| rare_tail_improvement_1p5 | 48 | centered_wild_signflip_t | 3000/3000 | 1.0000 | [0.9988, 1.0000] | [0.9976, 1.0000] |
| rare_tail_improvement_1p5 | 48 | block_bootstrap_percentile | 3000/3000 | 1.0000 | [0.9988, 1.0000] | [0.9976, 1.0000] |
| rare_tail_improvement_1p5 | 48 | mom_known_variance_bound | 2996/3000 | 0.9987 | [0.9966, 0.9996] | [0.9950, 0.9999] |

## Paired method differences vs raw sign-flip

Positive values mean the comparison method certifies more often than raw sign-flip; these are paired differences on the same generated dataset IDs. They do not rank methods without respecting the null-size results.

| World | Blocks | Method | Difference | Simultaneous CI95 | Method only | Sign-flip only |
| --- | ---: | --- | ---: | --- | ---: | ---: |
| symmetric_gaussian_null | 24 | paired_t | 0.0020 | [-0.0018, 0.0058] | 10 | 4 |
| symmetric_gaussian_null | 24 | centered_wild_signflip_t | 0.0003 | [-0.0027, 0.0034] | 5 | 4 |
| symmetric_gaussian_null | 24 | block_bootstrap_percentile | 0.0127 | [0.0062, 0.0191] | 39 | 1 |
| symmetric_gaussian_null | 24 | mom_known_variance_bound | -0.0570 | [-0.0700, -0.0440] | 0 | 171 |
| symmetric_gaussian_null | 48 | paired_t | -0.0013 | [-0.0057, 0.0030] | 7 | 11 |
| symmetric_gaussian_null | 48 | centered_wild_signflip_t | -0.0020 | [-0.0056, 0.0016] | 3 | 9 |
| symmetric_gaussian_null | 48 | block_bootstrap_percentile | 0.0050 | [0.0001, 0.0099] | 19 | 4 |
| symmetric_gaussian_null | 48 | mom_known_variance_bound | -0.0567 | [-0.0697, -0.0437] | 0 | 170 |
| rare_tail_weak_null | 24 | paired_t | -0.0177 | [-0.0251, -0.0103] | 0 | 53 |
| rare_tail_weak_null | 24 | centered_wild_signflip_t | 0.0423 | [0.0310, 0.0537] | 127 | 0 |
| rare_tail_weak_null | 24 | block_bootstrap_percentile | -0.0297 | [-0.0392, -0.0201] | 0 | 89 |
| rare_tail_weak_null | 24 | mom_known_variance_bound | -0.1240 | [-0.1425, -0.1055] | 0 | 372 |
| rare_tail_weak_null | 48 | paired_t | 0.0007 | [-0.0026, 0.0039] | 6 | 4 |
| rare_tail_weak_null | 48 | centered_wild_signflip_t | 0.0017 | [-0.0017, 0.0051] | 8 | 3 |
| rare_tail_weak_null | 48 | block_bootstrap_percentile | -0.0110 | [-0.0170, -0.0050] | 1 | 34 |
| rare_tail_weak_null | 48 | mom_known_variance_bound | -0.1047 | [-0.1219, -0.0874] | 0 | 314 |
| rare_tail_improvement_1p5 | 24 | paired_t | 0.0000 | [0.0000, 0.0000] | 0 | 0 |
| rare_tail_improvement_1p5 | 24 | centered_wild_signflip_t | 0.0000 | [0.0000, 0.0000] | 0 | 0 |
| rare_tail_improvement_1p5 | 24 | block_bootstrap_percentile | 0.0003 | [-0.0007, 0.0014] | 1 | 0 |
| rare_tail_improvement_1p5 | 24 | mom_known_variance_bound | -0.0517 | [-0.0641, -0.0392] | 0 | 155 |
| rare_tail_improvement_1p5 | 48 | paired_t | 0.0000 | [0.0000, 0.0000] | 0 | 0 |
| rare_tail_improvement_1p5 | 48 | centered_wild_signflip_t | 0.0000 | [0.0000, 0.0000] | 0 | 0 |
| rare_tail_improvement_1p5 | 48 | block_bootstrap_percentile | 0.0000 | [0.0000, 0.0000] | 0 | 0 |
| rare_tail_improvement_1p5 | 48 | mom_known_variance_bound | -0.0013 | [-0.0034, 0.0007] | 0 | 4 |

![Reviewed weak-null false-certification and strong-effect power figure](weak_null_size_power_review.png)

The figure is display-reviewed without changing the frozen data; see [PLOT_REVIEW](PLOT_REVIEW.md) for the image hashes and review notes.

## Interpretation rule

The symmetric Gaussian null checks the nominal baseline. The rare-tail weak null asks whether finite-sample certification changes when E[d]=0 but sign symmetry fails. The shifted rare-tail world is a strong positive control. A method is not accepted merely because it abstains more: interpret type-I rate and power together. The MoM result only supports the declared iid finite-variance model with the known variance bound; dependence across blocks or an invalid bound voids its guarantee. None of these methods can detect shared reference/state bias, and none replaces a fresh physical anchor.

All 18,000 planned datasets are written to `raw_block_deltas.npz`; per-dataset seeds, observed means, decisions, p-values, lower bounds, and failure status are in `dataset_outcomes.csv`. Verify hashes and row counts with `python -B -m tasks.pion_projection.weak_null_nonexchangeable --verify`.
