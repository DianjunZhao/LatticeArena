# C-package independent-link CPU follow-up (N=100)

Protocol and source hashes were frozen before data generation. This is a synthetic continuation of the class/optimizer convergence diagnostic, using 100 new deterministic dataset seeds (1100–1199), 3 shared starts, and budgets 25/100/400 objective calls per start. Each seed creates independent train and held-out links/probes through the existing generator; class A and B are evaluated on the same generated links.

The target worst-case Bernoulli Monte Carlo standard error is 0.05 at N=100. This is not a 95% interval half-width guarantee; all paired continuous-outcome intervals remain specific to this synthetic design. SLSQP gradients are analytic and not counted as objective calls, so equal objective-call budgets are not walltime equality.

| ε | class | budget/start | successful N | mean Powell−SLSQP test error | dataset bootstrap CI95 |
|---|---|---:|---:|---:|---:|
|0.0|A_spectral|25|100/100|0.889747|[0.8895667178119954, 0.8899270663429996]|
|0.0|A_spectral|100|100/100|0.134787|[0.13419022423753557, 0.1353778884246257]|
|0.0|A_spectral|400|100/100|0.0804122|[0.07916449529386421, 0.08179357916346622]|
|0.0|B_nested|25|100/100|0.881606|[0.8801188321812182, 0.8829922561710177]|
|0.0|B_nested|100|100/100|0.134598|[0.13400489651269573, 0.1352019039797546]|
|0.0|B_nested|400|100/100|0.110989|[0.11016664372922254, 0.11166535081823753]|
|0.1|A_spectral|25|100/100|0.88969|[0.8895116795246254, 0.8898743730257603]|
|0.1|A_spectral|100|100/100|0.134693|[0.1340861339067228, 0.1352868370006912]|
|0.1|A_spectral|400|100/100|0.0797367|[0.07854548425217876, 0.08103431921127936]|
|0.1|B_nested|25|100/100|0.882497|[0.8810757132510592, 0.8838517097289916]|
|0.1|B_nested|100|100/100|0.13481|[0.13423757287990462, 0.13542175802467563]|
|0.1|B_nested|400|100/100|0.110974|[0.1099136406500606, 0.11182731162106176]|

![Conditioning and convergence](condition_budget.png)

![Paired optimizer intervals](paired_optimizer_ci.png)

Across recorded trajectories, failure flags are: `{"budget_exhausted": 5165, "cell_failures": 0, "solver_non_success": 0, "success_large_residual": 0}`. Full flagged seed/start/residual rows are retained in `raw.json`; budget exhaustion is truncation, not solver failure. B's constructed teacher direction means near-zero oracle error is representability, not learned advantage. This result does not test real $W$, production links, learned smear or physical risk.
