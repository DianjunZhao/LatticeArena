# Time-correlation synthetic CPU stress

Preregistration was saved before dataset generation. See preregistration.json and raw.json.

True mass=.5, configuration AR rho=.5; time rho scanned; independent datasets, paired reference offsets on identical data and bootstrap indices. All-profile coverage is not nominal pointwise 95% coverage. Reference validity is known by construction, not inferred from coverage. Conditional target truth_profile differs from q=1 for misspecified reference.

|time rho|offset|all q=1 coverage|CP95|failures|
|---|---|---|---|---|
|0.0|0.0|0.6125|[0.5628175545377294, 0.6605047839078363]|0|
|0.0|0.03|0.0|[0.0, 0.00917980458366526]|0|
|0.5|0.0|0.65|[0.6010313375281027, 0.696730227994681]|0|
|0.5|0.03|0.0|[0.0, 0.00917980458366526]|0|
|0.8|0.0|0.655|[0.6061498222178268, 0.701536871101427]|0|
|0.8|0.03|0.0|[0.0, 0.00917980458366526]|0|

The JSON summary legacy key mass denotes time rho, not physical mass. Physical mass is fixed at 0.5 in preregistration. No failed amplitudes were silently dropped. No abstention gate is implemented: known-wrong references remain diagnostic_only. No learned kernel, SLSQP superiority, GPU evidence, or blind physical test is claimed. Amplitude uses declared unweighted late-window fitting, not production covariance fitting; fixed mass uncertainty is excluded. Paired intervals resample independent dataset risk differences and describe this synthetic design only.

![Paired risk intervals and all-window coverage](paired_coverage.png)

![q=1 reference shape](q_reference_shape.png)

Frozen design clarification: the inherited spec field masses lists scanned time AR coefficients (0, .5, .8); true_mass=.5 and configuration_rho=.5 are fixed. Summary/paired field mass likewise denotes time rho; row-level field time_rho is explicit. The reference-validity text offset=.03 remains the same known mismatch at all rho. No mass scan was performed.

Correct-reference all-window coverage is .6125/.65/.655; pointwise coverage is .8325–.8825, showing undercoverage even for a correct reference with finite correlated configuration blocks. Wrong-reference all-window coverage is zero/400 (CP95 upper .00918). These facts do not establish a reference-validity test. Zero abstentions means no gate implemented, not universal valid references.

|time rho|paired wrong-correct risk delta|dataset bootstrap CI95|
|---|---|---|
|0.0|0.004248412571754235|[0.004181664251648666, 0.004314140778026829]|
|0.5|0.004291569811185947|[0.004214343576217359, 0.004369755046315249]|
|0.8|0.004276386786273467|[0.004216145847641769, 0.004338789529741163]|
