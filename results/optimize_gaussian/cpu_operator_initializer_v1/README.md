# Cross-link initializer CPU synthetic diagnostic

Preregistered train/validation/test/shift seeds and summaries. Labels come from actual bounded SLSQP, not analytic coefficients. Summary computation and label/search/validation training time are included in training_and_selection_seconds; deployment amortization is that value/N. Test walltime and inference are separate in raw.json.

Spectral baseline is a feasible clipped real least-squares polynomial, no extra teacher directions. It is a strong direct baseline but not an optimally constrained Chebyshev implementation. Initializer compares same operator class to zero/random; spectral has a different class. Calls do not account for analytic-gradient or direct-linear-algebra costs, so walltime must also be read.

![Budget](budget_cost.png)

![Paired](paired_intervals.png)

{'population': 'iid', 'budget': 25, 'comparator': 'zero_random', 'delta': 0.049072386989077316, 'ci95': [0.04507546031642661, 0.053153721079789586]}

{'population': 'iid', 'budget': 25, 'comparator': 'spectral', 'delta': -0.00019042291469492358, 'ci95': [-0.00021602010027931692, -0.0001633699565579691]}

{'population': 'iid', 'budget': 100, 'comparator': 'zero_random', 'delta': 0.0023512904674641926, 'ci95': [0.002172464545256147, 0.0025318050982670983]}

{'population': 'iid', 'budget': 100, 'comparator': 'spectral', 'delta': -0.00019059586013064797, 'ci95': [-0.00021593417618863688, -0.00016253245748377388]}

{'population': 'iid', 'budget': 400, 'comparator': 'zero_random', 'delta': -0.00024309245856734882, 'ci95': [-0.0002862574228887434, -0.0001944956978542234]}

{'population': 'iid', 'budget': 400, 'comparator': 'spectral', 'delta': -0.00019059586013064797, 'ci95': [-0.00021639491119207436, -0.00016432755584324817]}

{'population': 'shift', 'budget': 25, 'comparator': 'zero_random', 'delta': 0.04868098397381247, 'ci95': [0.0443130699736602, 0.053287854159951915]}

{'population': 'shift', 'budget': 25, 'comparator': 'spectral', 'delta': 0.0004083477576967299, 'ci95': [0.0003546825827148855, 0.0004636064200842672]}

{'population': 'shift', 'budget': 100, 'comparator': 'zero_random', 'delta': 0.0020381664814640363, 'ci95': [0.001907469035724958, 0.002177361803643183]}

{'population': 'shift', 'budget': 100, 'comparator': 'spectral', 'delta': 0.00041056081985444207, 'ci95': [0.0003570873948641495, 0.00046695787523638564]}

{'population': 'shift', 'budget': 400, 'comparator': 'zero_random', 'delta': -0.00024308502299062636, 'ci95': [-0.0002822933654162021, -0.0002044795877420513]}

{'population': 'shift', 'budget': 400, 'comparator': 'spectral', 'delta': 0.00041056081985444207, 'ci95': [0.00035319794977439306, 0.0004654553293946944]}

## Worst cases and truncations

learned: worst iid seed=515 budget=25, error=0.0004548382049911746; truncations=57.

zero_random: worst shift seed=634 budget=25, error=0.07844666240817463; truncations=160.

spectral: worst shift seed=609 budget=25, error=0.0011638511679598104; truncations=0.

B contains the teacher component explicitly, so low error is constructive and not a learned physical kernel result. Summaries never use test links; shift changes epsilon only and does not cover all gauge-distribution shifts. Paired intervals are descriptive independent-dataset bootstrap, unadjusted for multiplicity.

## Maximum-budget CPU cost/residual table

|population/method|wall seconds mean|inference seconds mean|PG mean|truncated|
|---|---|---|---|---|
|iid/learned|0.0010244404664263129|8.215522393584252e-06|4.11082764147044e-07|0|
|iid/zero_random|0.008002576907165349|0.0|4.250795233636302e-08|0|
|iid/spectral|0.00015654787421226501|0.0|not evaluated direct baseline|0|
|shift/learned|0.0015041896607726813|8.36774706840515e-06|4.839817751682025e-07|0|
|shift/zero_random|0.007720024953596294|0.0|2.9852722570857835e-08|0|
|shift/spectral|0.00015423852019011975|0.0|not evaluated direct baseline|0|

Budget figure plots convergence versus calls; CPU costs are in this numeric table rather than a walltime plot. Zero/random truncation flag describes selected start; other-start details are not retained, so do not interpret it as total failed-start count.
