# Multiple-mass synthetic CPU stress

Preregistration was saved before dataset generation. See preregistration.json and raw.json.

Fixed relative time-correlated noise; independent datasets, paired reference offsets on identical data and bootstrap indices. All-profile coverage is not nominal pointwise 95% coverage. Reference validity is known by construction, not inferred from coverage. Conditional target truth_profile differs from q=1 for misspecified reference.

|mass|offset|all q=1 coverage|CP95|failures|
|---|---|---|---|---|
|0.25|0.0|0.73|[0.6836440009316515, 0.7729153041183727]|0|
|0.25|0.03|0.0|[0.0, 0.00917980458366526]|0|
|0.5|0.0|0.77|[0.7255919087673361, 0.8103611795952969]|0|
|0.5|0.03|0.0|[0.0, 0.00917980458366526]|0|
|0.9|0.0|0.7475|[0.7019376619265674, 0.7893569872991033]|0|
|0.9|0.03|0.0|[0.0, 0.00917980458366526]|0|

![Dataset-level all-profile coverage and paired risk change, with intervals](paired_coverage.png)

The left panel gives exact binomial intervals for the event that all four time points include $q=1$; the right panel gives a paired dataset-bootstrap interval for wrong-reference minus correct-reference risk. The coverage event is simultaneous across four times, not pointwise 95% coverage.

![Mean q profile at each mass for valid and shifted reference masses](q_reference_shape.png)

The profile plot makes the reference-shape shift visible as the mass changes; this is a synthetic diagnostic, not evidence that physical reference masses are known.

No failed amplitudes were silently dropped. No abstention gate is implemented: known-wrong references remain diagnostic_only. No learned kernel, SLSQP superiority, GPU evidence, or blind physical test is claimed. Amplitude uses declared unweighted late-window fitting, not production covariance fitting; fixed mass uncertainty is excluded. Paired intervals resample independent dataset risk differences and describe this synthetic design only.

The correct-reference pointwise coverage is only 0.8975–0.9275; this finite-block percentile bootstrap is undercovered even with a valid reference. All-profile coverage 0.73–0.77 must not be compared directly to nominal pointwise 0.95. Wrong-reference all-profile coverage is 0/400 at every mass (CP95 upper 0.00918). Thus failure to cover q=1 is sensitive to misspecification here, but coverage alone is not a validity gate. Mass-dependent first-time coverage is descriptive; no post-hoc significance claim.
