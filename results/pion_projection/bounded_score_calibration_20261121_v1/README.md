# Bounded block-MSE score: synthetic conditional calibration

**COMPLETE / SYNTHETIC_ONLY. `physical_score=null`.** The researcher accepted this distinct block-MSE estimand for exploration; no physical Pion reference, anchor or block-independence claim is established. No GPU/QUDA or E/validation/holdout data used.

## Formula audit

With masses in [0,1], d=(b−A)²−(c−A)²∈[−1,1]. Conditional on independent A, Δtrue=E[d|A]+2(A−m*)E[b−c]. Anchor coverage |A−m*|≤B gives Δtrue≥E[d|A]−2B. Hoeffding on width 2 gives P(E[d|A]<mean(d)−sqrt(2log(F/αS)/n))≤αS/F. Union over F, then add anchor failure αA. Result: joint noncoverage≤αS+αA=.05. F counts fixed candidates here (K=1), not datasets; candidates may be correlated.

## Frozen experiment

168 cells × 3000 independent outer datasets. n=12/24/100/400; F=1/2/4; δ*=0.1. [protocol.json](protocol.json) was written before generation and binds source/design hashes, seeds and environment. The whole cell stream is deterministic; source hashes must match for replay. New output paths refuse existing directories.

Endpoint Bernoulli masses produce exact sufficient statistics by binomial draws. In max-variance null, b=X,c=1−X,p=.5,A=0 gives d=±1 and Var(d)=1, saturating the variance bound for [−1,1]; F candidates are identical in this world. Shared-baseline null and alternatives use independent candidate Bernoulli arms with a common baseline. Threshold null has Δ=.1, exactly the practical threshold. Anchor-sensitive null has b~Bernoulli(.25),c=.5: equal true MSE=.25 but different mean masses. This is a new bounded-mass/squared-loss experiment; it does not repeat the older unbounded rare-tail direct-delta grid.

Exact anchor: A=0,B=0,αS=.05,αA=0. Valid uncertain anchor: independent A~U(0,.04) with probability .99 and A=1 with probability .01, B=.04,αS=.04,αA=.01. Its coverage is exactly .99. Undercoverage stress always A=1 while still declaring B=.04; dependence stress repeats one Bernoulli draw n times while using nominal n. Both stresses intentionally violate the theorem: every dataset is ineligible/abstained; crossings are hypothetical diagnostics only.

## Results and denominators

Planned 504000; valid 504000; failed 0; abstained 72000 (all assumption-violation stress datasets). Eligible cells: 144. Failed rows, if any, count as noncertification and conservative coverage failure in the all-planned denominator. A valid numerical stress row does not become an eligible inference.

Largest observed eligible family noncoverage: 0.01233 in anchor_sensitive_null, uncertain, n=100, F=2. Every cell below retains its own MC interval; rates are not pooled.

All outcome events are family-level per independent dataset: joint coverage means every lower bound covers its true Δ; false certification means at least one true Δ≤δ* has L>δ*. Power is any-candidate certification when all candidates truly improve beyond δ*. CP95 is marginal exact binomial MC uncertainty, not physical coverage. summary.json additionally supplies simultaneous Bonferroni CP95 across four metrics × all cells. Noncoverage and false certification are distinct metrics.

![Calibration](calibration.png)

The low eligible error rates must be read with power and block count. A conservative bound can certify few practical improvements with n=12/24; a small error count alone is not success. The stress plot shows why oracle mass bounds cannot repair an invalid anchor or nonexistent independent blocks.

| World | Anchor | Dependence | n | F | planned/valid/failed/abstained | Joint coverage [CP95] | False crossing [CP95] | Power [CP95] |
|---|---|---|---:|---:|---|---|---|---|
| max_variance_null | exact | iid | 12 | 1 | 3000/3000/0/0 | 2986/3000=0.9953 [0.9922,0.9974] | 14/3000=0.0047 [0.0026,0.0078] | — |
| max_variance_null | exact | iid | 12 | 2 | 3000/3000/0/0 | 2997/3000=0.9990 [0.9971,0.9998] | 1/3000=0.0003 [0.0000,0.0019] | — |
| max_variance_null | exact | iid | 12 | 4 | 3000/3000/0/0 | 2998/3000=0.9993 [0.9976,0.9999] | 2/3000=0.0007 [0.0001,0.0024] | — |
| max_variance_null | exact | iid | 24 | 1 | 3000/3000/0/0 | 2968/3000=0.9893 [0.9850,0.9927] | 4/3000=0.0013 [0.0004,0.0034] | — |
| max_variance_null | exact | iid | 24 | 2 | 3000/3000/0/0 | 2993/3000=0.9977 [0.9952,0.9991] | 3/3000=0.0010 [0.0002,0.0029] | — |
| max_variance_null | exact | iid | 24 | 4 | 3000/3000/0/0 | 2998/3000=0.9993 [0.9976,0.9999] | 1/3000=0.0003 [0.0000,0.0019] | — |
| max_variance_null | exact | iid | 100 | 1 | 3000/3000/0/0 | 2983/3000=0.9943 [0.9909,0.9967] | 1/3000=0.0003 [0.0000,0.0019] | — |
| max_variance_null | exact | iid | 100 | 2 | 3000/3000/0/0 | 2989/3000=0.9963 [0.9934,0.9982] | 1/3000=0.0003 [0.0000,0.0019] | — |
| max_variance_null | exact | iid | 100 | 4 | 3000/3000/0/0 | 2994/3000=0.9980 [0.9957,0.9993] | 0/3000=0.0000 [0.0000,0.0012] | — |
| max_variance_null | exact | iid | 400 | 1 | 3000/3000/0/0 | 2982/3000=0.9940 [0.9905,0.9964] | 0/3000=0.0000 [0.0000,0.0012] | — |
| max_variance_null | exact | iid | 400 | 2 | 3000/3000/0/0 | 2989/3000=0.9963 [0.9934,0.9982] | 0/3000=0.0000 [0.0000,0.0012] | — |
| max_variance_null | exact | iid | 400 | 4 | 3000/3000/0/0 | 2995/3000=0.9983 [0.9961,0.9995] | 0/3000=0.0000 [0.0000,0.0012] | — |
| max_variance_null | uncertain | iid | 12 | 1 | 3000/3000/0/0 | 2999/3000=0.9997 [0.9981,1.0000] | 1/3000=0.0003 [0.0000,0.0019] | — |
| max_variance_null | uncertain | iid | 12 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| max_variance_null | uncertain | iid | 12 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| max_variance_null | uncertain | iid | 24 | 1 | 3000/3000/0/0 | 2993/3000=0.9977 [0.9952,0.9991] | 0/3000=0.0000 [0.0000,0.0012] | — |
| max_variance_null | uncertain | iid | 24 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| max_variance_null | uncertain | iid | 24 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| max_variance_null | uncertain | iid | 100 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| max_variance_null | uncertain | iid | 100 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| max_variance_null | uncertain | iid | 100 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| max_variance_null | uncertain | iid | 400 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| max_variance_null | uncertain | iid | 400 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| max_variance_null | uncertain | iid | 400 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| shared_baseline_null | exact | iid | 12 | 1 | 3000/3000/0/0 | 2999/3000=0.9997 [0.9981,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| shared_baseline_null | exact | iid | 12 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| shared_baseline_null | exact | iid | 12 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| shared_baseline_null | exact | iid | 24 | 1 | 3000/3000/0/0 | 2999/3000=0.9997 [0.9981,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| shared_baseline_null | exact | iid | 24 | 2 | 3000/3000/0/0 | 2999/3000=0.9997 [0.9981,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| shared_baseline_null | exact | iid | 24 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| shared_baseline_null | exact | iid | 100 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| shared_baseline_null | exact | iid | 100 | 2 | 3000/3000/0/0 | 2998/3000=0.9993 [0.9976,0.9999] | 0/3000=0.0000 [0.0000,0.0012] | — |
| shared_baseline_null | exact | iid | 100 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| shared_baseline_null | exact | iid | 400 | 1 | 3000/3000/0/0 | 2997/3000=0.9990 [0.9971,0.9998] | 0/3000=0.0000 [0.0000,0.0012] | — |
| shared_baseline_null | exact | iid | 400 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| shared_baseline_null | exact | iid | 400 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| shared_baseline_null | uncertain | iid | 12 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| shared_baseline_null | uncertain | iid | 12 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| shared_baseline_null | uncertain | iid | 12 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| shared_baseline_null | uncertain | iid | 24 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| shared_baseline_null | uncertain | iid | 24 | 2 | 3000/3000/0/0 | 2999/3000=0.9997 [0.9981,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| shared_baseline_null | uncertain | iid | 24 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| shared_baseline_null | uncertain | iid | 100 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| shared_baseline_null | uncertain | iid | 100 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| shared_baseline_null | uncertain | iid | 100 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| shared_baseline_null | uncertain | iid | 400 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| shared_baseline_null | uncertain | iid | 400 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| shared_baseline_null | uncertain | iid | 400 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| threshold_null | exact | iid | 12 | 1 | 3000/3000/0/0 | 2975/3000=0.9917 [0.9877,0.9946] | 25/3000=0.0083 [0.0054,0.0123] | — |
| threshold_null | exact | iid | 12 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| threshold_null | exact | iid | 12 | 4 | 3000/3000/0/0 | 2995/3000=0.9983 [0.9961,0.9995] | 5/3000=0.0017 [0.0005,0.0039] | — |
| threshold_null | exact | iid | 24 | 1 | 3000/3000/0/0 | 2989/3000=0.9963 [0.9934,0.9982] | 11/3000=0.0037 [0.0018,0.0066] | — |
| threshold_null | exact | iid | 24 | 2 | 3000/3000/0/0 | 2993/3000=0.9977 [0.9952,0.9991] | 7/3000=0.0023 [0.0009,0.0048] | — |
| threshold_null | exact | iid | 24 | 4 | 3000/3000/0/0 | 2997/3000=0.9990 [0.9971,0.9998] | 3/3000=0.0010 [0.0002,0.0029] | — |
| threshold_null | exact | iid | 100 | 1 | 3000/3000/0/0 | 2981/3000=0.9937 [0.9901,0.9962] | 19/3000=0.0063 [0.0038,0.0099] | — |
| threshold_null | exact | iid | 100 | 2 | 3000/3000/0/0 | 2992/3000=0.9973 [0.9948,0.9988] | 8/3000=0.0027 [0.0012,0.0052] | — |
| threshold_null | exact | iid | 100 | 4 | 3000/3000/0/0 | 2994/3000=0.9980 [0.9957,0.9993] | 6/3000=0.0020 [0.0007,0.0043] | — |
| threshold_null | exact | iid | 400 | 1 | 3000/3000/0/0 | 2980/3000=0.9933 [0.9897,0.9959] | 20/3000=0.0067 [0.0041,0.0103] | — |
| threshold_null | exact | iid | 400 | 2 | 3000/3000/0/0 | 2989/3000=0.9963 [0.9934,0.9982] | 11/3000=0.0037 [0.0018,0.0066] | — |
| threshold_null | exact | iid | 400 | 4 | 3000/3000/0/0 | 2996/3000=0.9987 [0.9966,0.9996] | 4/3000=0.0013 [0.0004,0.0034] | — |
| threshold_null | uncertain | iid | 12 | 1 | 3000/3000/0/0 | 2996/3000=0.9987 [0.9966,0.9996] | 4/3000=0.0013 [0.0004,0.0034] | — |
| threshold_null | uncertain | iid | 12 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| threshold_null | uncertain | iid | 12 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| threshold_null | uncertain | iid | 24 | 1 | 3000/3000/0/0 | 2998/3000=0.9993 [0.9976,0.9999] | 2/3000=0.0007 [0.0001,0.0024] | — |
| threshold_null | uncertain | iid | 24 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| threshold_null | uncertain | iid | 24 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| threshold_null | uncertain | iid | 100 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| threshold_null | uncertain | iid | 100 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| threshold_null | uncertain | iid | 100 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| threshold_null | uncertain | iid | 400 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| threshold_null | uncertain | iid | 400 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| threshold_null | uncertain | iid | 400 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| practical_improvement | exact | iid | 12 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 2/3000=0.0007 [0.0001,0.0024] |
| practical_improvement | exact | iid | 12 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 0/3000=0.0000 [0.0000,0.0012] |
| practical_improvement | exact | iid | 12 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 0/3000=0.0000 [0.0000,0.0012] |
| practical_improvement | exact | iid | 24 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 4/3000=0.0013 [0.0004,0.0034] |
| practical_improvement | exact | iid | 24 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 2/3000=0.0007 [0.0001,0.0024] |
| practical_improvement | exact | iid | 24 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 1/3000=0.0003 [0.0000,0.0019] |
| practical_improvement | exact | iid | 100 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 46/3000=0.0153 [0.0112,0.0204] |
| practical_improvement | exact | iid | 100 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 36/3000=0.0120 [0.0084,0.0166] |
| practical_improvement | exact | iid | 100 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 28/3000=0.0093 [0.0062,0.0135] |
| practical_improvement | exact | iid | 400 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 794/3000=0.2647 [0.2489,0.2808] |
| practical_improvement | exact | iid | 400 | 2 | 3000/3000/0/0 | 2999/3000=0.9997 [0.9981,1.0000] | — | 694/3000=0.2313 [0.2163,0.2468] |
| practical_improvement | exact | iid | 400 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 652/3000=0.2173 [0.2027,0.2325] |
| practical_improvement | uncertain | iid | 12 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 0/3000=0.0000 [0.0000,0.0012] |
| practical_improvement | uncertain | iid | 12 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 0/3000=0.0000 [0.0000,0.0012] |
| practical_improvement | uncertain | iid | 12 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 0/3000=0.0000 [0.0000,0.0012] |
| practical_improvement | uncertain | iid | 24 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 2/3000=0.0007 [0.0001,0.0024] |
| practical_improvement | uncertain | iid | 24 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 0/3000=0.0000 [0.0000,0.0012] |
| practical_improvement | uncertain | iid | 24 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 0/3000=0.0000 [0.0000,0.0012] |
| practical_improvement | uncertain | iid | 100 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 2/3000=0.0007 [0.0001,0.0024] |
| practical_improvement | uncertain | iid | 100 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 0/3000=0.0000 [0.0000,0.0012] |
| practical_improvement | uncertain | iid | 100 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 0/3000=0.0000 [0.0000,0.0012] |
| practical_improvement | uncertain | iid | 400 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 0/3000=0.0000 [0.0000,0.0012] |
| practical_improvement | uncertain | iid | 400 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 0/3000=0.0000 [0.0000,0.0012] |
| practical_improvement | uncertain | iid | 400 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 0/3000=0.0000 [0.0000,0.0012] |
| strong_improvement | exact | iid | 12 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 31/3000=0.0103 [0.0070,0.0146] |
| strong_improvement | exact | iid | 12 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 14/3000=0.0047 [0.0026,0.0078] |
| strong_improvement | exact | iid | 12 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 0/3000=0.0000 [0.0000,0.0012] |
| strong_improvement | exact | iid | 24 | 1 | 3000/3000/0/0 | 2999/3000=0.9997 [0.9981,1.0000] | — | 170/3000=0.0567 [0.0487,0.0655] |
| strong_improvement | exact | iid | 24 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 153/3000=0.0510 [0.0434,0.0595] |
| strong_improvement | exact | iid | 24 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 127/3000=0.0423 [0.0354,0.0502] |
| strong_improvement | exact | iid | 100 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 2439/3000=0.8130 [0.7986,0.8268] |
| strong_improvement | exact | iid | 100 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 2442/3000=0.8140 [0.7996,0.8278] |
| strong_improvement | exact | iid | 100 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 2480/3000=0.8267 [0.8126,0.8401] |
| strong_improvement | exact | iid | 400 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 3000/3000=1.0000 [0.9988,1.0000] |
| strong_improvement | exact | iid | 400 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 3000/3000=1.0000 [0.9988,1.0000] |
| strong_improvement | exact | iid | 400 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 3000/3000=1.0000 [0.9988,1.0000] |
| strong_improvement | uncertain | iid | 12 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 2/3000=0.0007 [0.0001,0.0024] |
| strong_improvement | uncertain | iid | 12 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 0/3000=0.0000 [0.0000,0.0012] |
| strong_improvement | uncertain | iid | 12 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 0/3000=0.0000 [0.0000,0.0012] |
| strong_improvement | uncertain | iid | 24 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 14/3000=0.0047 [0.0026,0.0078] |
| strong_improvement | uncertain | iid | 24 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 2/3000=0.0007 [0.0001,0.0024] |
| strong_improvement | uncertain | iid | 24 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 4/3000=0.0013 [0.0004,0.0034] |
| strong_improvement | uncertain | iid | 100 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 650/3000=0.2167 [0.2020,0.2318] |
| strong_improvement | uncertain | iid | 100 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 552/3000=0.1840 [0.1703,0.1983] |
| strong_improvement | uncertain | iid | 100 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 481/3000=0.1603 [0.1474,0.1740] |
| strong_improvement | uncertain | iid | 400 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 2951/3000=0.9837 [0.9785,0.9879] |
| strong_improvement | uncertain | iid | 400 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 2967/3000=0.9890 [0.9846,0.9924] |
| strong_improvement | uncertain | iid | 400 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | — | 2941/3000=0.9803 [0.9747,0.9850] |
| anchor_sensitive_null | exact | iid | 12 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| anchor_sensitive_null | exact | iid | 12 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| anchor_sensitive_null | exact | iid | 12 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| anchor_sensitive_null | exact | iid | 24 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| anchor_sensitive_null | exact | iid | 24 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| anchor_sensitive_null | exact | iid | 24 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| anchor_sensitive_null | exact | iid | 100 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| anchor_sensitive_null | exact | iid | 100 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| anchor_sensitive_null | exact | iid | 100 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| anchor_sensitive_null | exact | iid | 400 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| anchor_sensitive_null | exact | iid | 400 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| anchor_sensitive_null | exact | iid | 400 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| anchor_sensitive_null | uncertain | iid | 12 | 1 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| anchor_sensitive_null | uncertain | iid | 12 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| anchor_sensitive_null | uncertain | iid | 12 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| anchor_sensitive_null | uncertain | iid | 24 | 1 | 3000/3000/0/0 | 2997/3000=0.9990 [0.9971,0.9998] | 0/3000=0.0000 [0.0000,0.0012] | — |
| anchor_sensitive_null | uncertain | iid | 24 | 2 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| anchor_sensitive_null | uncertain | iid | 24 | 4 | 3000/3000/0/0 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| anchor_sensitive_null | uncertain | iid | 100 | 1 | 3000/3000/0/0 | 2973/3000=0.9910 [0.9869,0.9941] | 23/3000=0.0077 [0.0049,0.0115] | — |
| anchor_sensitive_null | uncertain | iid | 100 | 2 | 3000/3000/0/0 | 2963/3000=0.9877 [0.9830,0.9913] | 35/3000=0.0117 [0.0081,0.0162] | — |
| anchor_sensitive_null | uncertain | iid | 100 | 4 | 3000/3000/0/0 | 2971/3000=0.9903 [0.9861,0.9935] | 18/3000=0.0060 [0.0036,0.0095] | — |
| anchor_sensitive_null | uncertain | iid | 400 | 1 | 3000/3000/0/0 | 2971/3000=0.9903 [0.9861,0.9935] | 29/3000=0.0097 [0.0065,0.0139] | — |
| anchor_sensitive_null | uncertain | iid | 400 | 2 | 3000/3000/0/0 | 2967/3000=0.9890 [0.9846,0.9924] | 33/3000=0.0110 [0.0076,0.0154] | — |
| anchor_sensitive_null | uncertain | iid | 400 | 4 | 3000/3000/0/0 | 2966/3000=0.9887 [0.9842,0.9921] | 34/3000=0.0113 [0.0079,0.0158] | — |
| anchor_sensitive_null | undercoverage | iid | 12 | 1 | 3000/3000/0/3000 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| max_variance_null | exact | perfect | 12 | 1 | 3000/3000/0/3000 | 1531/3000=0.5103 [0.4923,0.5284] | 1469/3000=0.4897 [0.4716,0.5077] | — |
| anchor_sensitive_null | undercoverage | iid | 12 | 2 | 3000/3000/0/3000 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| max_variance_null | exact | perfect | 12 | 2 | 3000/3000/0/3000 | 1490/3000=0.4967 [0.4786,0.5147] | 1510/3000=0.5033 [0.4853,0.5214] | — |
| anchor_sensitive_null | undercoverage | iid | 12 | 4 | 3000/3000/0/3000 | 3000/3000=1.0000 [0.9988,1.0000] | 0/3000=0.0000 [0.0000,0.0012] | — |
| max_variance_null | exact | perfect | 12 | 4 | 3000/3000/0/3000 | 1472/3000=0.4907 [0.4726,0.5087] | 1528/3000=0.5093 [0.4913,0.5274] | — |
| anchor_sensitive_null | undercoverage | iid | 24 | 1 | 3000/3000/0/3000 | 2672/3000=0.8907 [0.8790,0.9016] | 23/3000=0.0077 [0.0049,0.0115] | — |
| max_variance_null | exact | perfect | 24 | 1 | 3000/3000/0/3000 | 1504/3000=0.5013 [0.4833,0.5194] | 1496/3000=0.4987 [0.4806,0.5167] | — |
| anchor_sensitive_null | undercoverage | iid | 24 | 2 | 3000/3000/0/3000 | 2885/3000=0.9617 [0.9542,0.9683] | 0/3000=0.0000 [0.0000,0.0012] | — |
| max_variance_null | exact | perfect | 24 | 2 | 3000/3000/0/3000 | 1510/3000=0.5033 [0.4853,0.5214] | 1490/3000=0.4967 [0.4786,0.5147] | — |
| anchor_sensitive_null | undercoverage | iid | 24 | 4 | 3000/3000/0/3000 | 2969/3000=0.9897 [0.9854,0.9930] | 0/3000=0.0000 [0.0000,0.0012] | — |
| max_variance_null | exact | perfect | 24 | 4 | 3000/3000/0/3000 | 1506/3000=0.5020 [0.4839,0.5200] | 1494/3000=0.4980 [0.4800,0.5161] | — |
| anchor_sensitive_null | undercoverage | iid | 100 | 1 | 3000/3000/0/3000 | 0/3000=0.0000 [0.0000,0.0012] | 2784/3000=0.9280 [0.9182,0.9370] | — |
| max_variance_null | exact | perfect | 100 | 1 | 3000/3000/0/3000 | 1487/3000=0.4957 [0.4776,0.5137] | 1513/3000=0.5043 [0.4863,0.5224] | — |
| anchor_sensitive_null | undercoverage | iid | 100 | 2 | 3000/3000/0/3000 | 4/3000=0.0013 [0.0004,0.0034] | 2550/3000=0.8500 [0.8367,0.8626] | — |
| max_variance_null | exact | perfect | 100 | 2 | 3000/3000/0/3000 | 1465/3000=0.4883 [0.4703,0.5064] | 1535/3000=0.5117 [0.4936,0.5297] | — |
| anchor_sensitive_null | undercoverage | iid | 100 | 4 | 3000/3000/0/3000 | 12/3000=0.0040 [0.0021,0.0070] | 1881/3000=0.6270 [0.6094,0.6443] | — |
| max_variance_null | exact | perfect | 100 | 4 | 3000/3000/0/3000 | 1464/3000=0.4880 [0.4700,0.5061] | 1536/3000=0.5120 [0.4939,0.5300] | — |
| anchor_sensitive_null | undercoverage | iid | 400 | 1 | 3000/3000/0/3000 | 0/3000=0.0000 [0.0000,0.0012] | 3000/3000=1.0000 [0.9988,1.0000] | — |
| max_variance_null | exact | perfect | 400 | 1 | 3000/3000/0/3000 | 1498/3000=0.4993 [0.4813,0.5174] | 1502/3000=0.5007 [0.4826,0.5187] | — |
| anchor_sensitive_null | undercoverage | iid | 400 | 2 | 3000/3000/0/3000 | 0/3000=0.0000 [0.0000,0.0012] | 3000/3000=1.0000 [0.9988,1.0000] | — |
| max_variance_null | exact | perfect | 400 | 2 | 3000/3000/0/3000 | 1493/3000=0.4977 [0.4796,0.5157] | 1507/3000=0.5023 [0.4843,0.5204] | — |
| anchor_sensitive_null | undercoverage | iid | 400 | 4 | 3000/3000/0/3000 | 0/3000=0.0000 [0.0000,0.0012] | 3000/3000=1.0000 [0.9988,1.0000] | — |
| max_variance_null | exact | perfect | 400 | 4 | 3000/3000/0/3000 | 1525/3000=0.5083 [0.4903,0.5264] | 1475/3000=0.4917 [0.4736,0.5097] | — |

## Raw evidence and limits

[raw_datasets.csv.gz](raw_datasets.csv.gz) contains every planned dataset: cell/dataset IDs, baseline and candidate first/second moments, anchor, per-candidate lower bounds, truth, coverage, crossing, eligibility and issued-certificate/failed status. These are sufficient statistics for exactly recomputing the score; the binomial/anchor seed recipe regenerates the synthetic inputs. [summary.json](summary.json) contains counts and intervals per cell; [artifact_hashes.json](artifact_hashes.json) binds artifacts.

These results check a conditional bound in finitely many declared DGPs, not exhaustive calibration, proof of sharpness or validation of physical block formation. The theorem relies on the predeclared range and true block independence, plus independent anchor coverage including model/systematic bias. Current Pion D blocks and failed reference do not meet that contract. Existing single-cosh FAIL and M2 NOT_READY remain, E/new validation/shared holdout stay closed. Next physical work must establish bounds/clipping policy, block-estimator interpretation, independent block provenance and a defensible anchor with systematic-error coverage before any physical scoring.

Reproduce into a fresh directory: `python3 -B -m tasks.pion_projection.bounded_score_calibration --output NEW_DIRECTORY`. This does not run measurement or open data.
