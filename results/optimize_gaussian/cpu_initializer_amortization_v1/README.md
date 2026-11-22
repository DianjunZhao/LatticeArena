# Learned initializer CPU cost amortization

**Classification: exploratory post-processing of frozen synthetic data. No simulation was rerun and the source results were not modified.**

## Calculation

The source run reports one-time training and selection cost of **1.339 CPU seconds**. For N later deployments, this report uses

    T_learned(N) = T_train_and_select + N × mean learned deployment wall time
    T_baseline(N) = N × mean baseline deployment wall time

The break-even count is the first integer N at which the learned method's amortized total CPU time is no greater than zero/random SLSQP. This is a direct arithmetic transform of the frozen per-case wall times, not a statistical estimate. Timing summaries are means and medians over 40 already-observed test links per cell; no timing confidence interval is claimed.

## Cost and paired-risk table

Times are mean / median milliseconds per deployment. Risk is comparator minus learned; positive values mean the learned initializer had lower error in the source run. Risk intervals are copied from that run's paired-bootstrap summary and are not recalculated here.

| Population | Objective-call budget | Learned ms mean / median | SLSQP ms mean / median | Spectral ms mean / median | Break-even deployments vs SLSQP | vs spectral | SLSQP risk delta [CI95] | Spectral risk delta [CI95] |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| IID | 25 | 1.131 / 1.105 | 1.592 / 1.533 | 0.163 / 0.153 | 2,906 | none | 0.049072 [0.045075,0.053154] | -0.000190 [-0.000216,-0.000163] |
| IID | 100 | 1.052 / 1.110 | 4.733 / 4.539 | 0.147 / 0.145 | 364 | none | 0.002351 [0.002172,0.002532] | -0.000191 [-0.000216,-0.000163] |
| IID | 400 | 1.024 / 1.022 | 8.003 / 7.697 | 0.157 / 0.148 | 192 | none | -0.000243 [-0.000286,-0.000194] | -0.000191 [-0.000216,-0.000164] |
| epsilon-shift | 25 | 1.290 / 1.243 | 1.547 / 1.504 | 0.156 / 0.154 | 5,203 | none | 0.048681 [0.044313,0.053288] | 0.000408 [0.000355,0.000464] |
| epsilon-shift | 100 | 1.471 / 1.350 | 4.691 / 4.609 | 0.154 / 0.150 | 416 | none | 0.002038 [0.001907,0.002177] | 0.000411 [0.000357,0.000467] |
| epsilon-shift | 400 | 1.504 / 1.392 | 7.720 / 7.648 | 0.154 / 0.151 | 216 | none | -0.000243 [-0.000282,-0.000204] | 0.000411 [0.000353,0.000465] |

![Total CPU time versus repeated deployments](cost_amortization.png)

The vertical dotted line in each panel marks the estimated break-even against zero/random SLSQP. No crossover against the spectral baseline occurs in these cells because its measured mean deployment time is below the learned method's; a learned model's training cost cannot be amortized against a method that is already cheaper per deployment under this timing setup.

## Interpretation and limits

- Compared with zero/random SLSQP, the initializer has lower mean deployment time in all six population/budget cells, but amortizing its 1.339-second training/selection cost requires roughly **192–5,203 repeated deployments**, depending on budget and population.
- Compared with the spectral baseline, there is no CPU-time break-even. The paired-risk results also vary by population: the spectral baseline slightly outperforms the initializer in IID cells, while the initializer has lower risk in the epsilon-shift cells. This is an accuracy-cost trade-off in the declared toy benchmark, not evidence that either method dominates.
- At high budgets, the source results report lower held-out error for SLSQP than for the learned initializer. At low budgets, an initializer can improve the fixed-budget optimization path; this supports an amortized warm-start hypothesis only.
- The source test links were already observed. The shift changes epsilon only; the spectral implementation is a feasible clipped polynomial fit, not an optimally constrained Chebyshev solver. CPU timings do not predict GPU training or inference cost.
- This is not a learned smear kernel, not a trainable-W test, and not physical evidence. The next decisive comparison remains a fresh-gauge blind run with matched objective-call and walltime budgets, Gaussian, SLSQP, and a stronger spectral baseline.

Frozen source: [CPU operator initializer report](../cpu_operator_initializer_v1/README.md). Reproduce this descriptive calculation with:

    python3 -B -m tasks.optimize_gaussian.initializer_amortization run

Verify the frozen inputs and output hashes with:

    python3 -B -m tasks.optimize_gaussian.initializer_amortization verify
