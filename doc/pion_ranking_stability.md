# Pion pilot ranking stability

On the RTX 3060 run, changing the common-mass fit window reverses the point ranking of the two strongest frozen kernels. Kunshan preserves their ordering across the three protocol windows. Both original reference gates failed. These diagnostics support prioritizing a better independent reference measurement before using the score to judge new operators.

## Replaying the frozen kernels

Each entry is held-out tuned Gaussian risk divided by signed-mixture risk, with a paired conditional 95% interval. Values above one favor the signed mixture. The signed mixture in both archives came from SLSQP. The local kernel ranked last in every window.

| Reference time window | RTX 3060 mass | RTX 3060 ratio | Kunshan mass | Kunshan ratio |
| --- | ---: | ---: | ---: | ---: |
| 4–8 | 1.10337 | 0.471 [0.360, 1.045] | 1.11205 | 1.290 [1.212, 1.434] |
| 5–8 (nominal) | 1.07671 | 7.026 [0.978, 14.093] | 1.08617 | 1.630 [1.396, 2.190] |
| 6–8 | 1.06009 | 3.703 [2.537, 7.983] | 1.07220 | 2.008 [1.039, 2.280] |

The local reversal is driven by the squared departure from the reference shape. At the nominal window that term is 0.00350 for Gaussian and 0.000138 for the mixture. At 4–8 it is 0.00238 and 0.00568 respectively. The mixture has the smaller variance term in both windows. On Kunshan the mixture has the larger variance term in all three windows, and its smaller shape departure accounts for its lower total risk.

The replay used 6 development / 3 validation blocks locally and 12 / 6 on Kunshan. It checked the archived nominal results before scanning, rebuilt candidate covariance metrics on development, and kept the weights and bootstrap seeds fixed. Each interval is conditional on its own reference model and window. The intervals do not account for window selection. Both datasets have previously been inspected.

The [machine summaries](../examples/README.md) record the original validation report hashes. Kunshan's matching arrays are available in the [pinned PR archive](https://github.com/Greyyy-HJC/LatticeArena/tree/b3f03a7c3dd110bf272b4d09f823b9c75cd03b7c/results/pion_projection/s16t16_v1). The CLI checks the data and frozen submission against the report.

## Checking the proxy against known energies

The CPU fixtures use periodic cosh spectra at T=16 with true ground energy 0.8. There are 48 independent blocks per split, with Gaussian noise correlated across time as 0.65 raised to the time separation. Cases share noise draws for paired comparisons. The reference mass is fixed at truth to isolate the scoring rule. A separate one-cosh energy fit on times 2–5 uses a development covariance and 256 validation bootstrap replicas. The bias column evaluates this estimator on the exact noiseless correlator; SE measures its uncertainty on noisy data.

| Case | v1 risk | Noiseless early energy bias | Bootstrap SE |
| --- | ---: | ---: | ---: |
| One state | 0.0001674 | ≈0 | 0.00210 |
| One state, quarter noise | 0.00001051 | ≈0 | 0.000521 |
| Positive excited contribution | 0.05996 | +0.08074 | 0.00162 |
| Reduced excited amplitude | 0.0005799 | +0.01267 | 0.00202 |
| Two signed excited contributions | 0.03159 | −0.13552 | 0.00203 |
| Near-zero ground overlap | rejected, amplitude z = 0.382 | ≈0 | 0.578 |

The signed example keeps the positive excited amplitude and adds a heavier state with opposite sign, chosen to cancel the two terms at time 3. The risk improves from 0.05996 to 0.03159 while the absolute energy bias increases from 0.08074 to 0.13552. This is a concrete failure mode even with an exact reference mass. For the nearly invisible single state the noiseless shape is correct, but 19 of 256 noisy fit replicas hit a mass bound; the amplitude gate properly withholds a risk. These seeded examples exercise mechanisms. They do not estimate their prevalence on real ensembles.

## Development-only search on the RTX 3060 archive

All methods used the same reference, amplitude scales, seven single-channel diagnostics and development data. The best single channel had risk 0.003586. Each of four rounds allowed three proposal slots. Random search used seed 20261109, sampled a zero-sum direction about the best basis vector and varied its L1 radius. The LLM saw development curves, loss components, time-resolved channel correlations and feedback from earlier proposals.

| Proposal slots used | Best Codex risk including basis | Best random risk including basis |
| ---: | ---: | ---: |
| 3 | 0.0011174 | 0.0033348 |
| 6 | 0.0005059 | 0.0033348 |
| 9 | 0.0003371 | 0.0033348 |
| 12 | 0.0003012 | 0.0017754 |

The eight-start SLSQP pilot minimizes risk plus a ridge penalty. It took 1,256 objective calls and achieved raw risk 0.0004512. Removing the ridge for a same-objective comparison gave 0.0002170 in 5,273 calls. The seven shared basis diagnostics and final risk readouts are separate from these optimizer counts.

The Codex session supplied the twelve proposals through the terminal adapter. It had prior conversation context about this historical experiment, including the archived mixture. The command read development data only. This is one exploratory trial with one random seed; model generalization and blind discovery efficiency remain open. The [four replies](../examples/pion_projection/rtx3060/search_replies.jsonl) reproduce the trajectory offline. [Commands and inputs](../tasks/pion_projection/README.md#ranking-diagnostics-and-search-comparison)

## Transfer to fresh synthetic correlators

A CPU-only control run (12 episodes, seed 20261118) tested whether the archived
proposals transfer to different spectra under the same 12-slot budget. Each
method selected on development; all comparisons use the independently drawn
blocks for the same episode. Every pair had valid test risks on all 12 episodes.
The ratios below divide the comparator's held-out risk by the method's.

| Method | Comparator | Wins / ties / losses | Median paired ratio | Smaller absolute noiseless energy bias |
| --- | --- | ---: | ---: | ---: |
| Curve fit using development diagnostics | Best single channel on development | 11 / 0 / 1 | 5.60 | 10 / 12 |
| Adaptive random search | Fixed-center random search | 3 / 5 / 4 | 1.00 | 4 / 12 |
| Archived Codex proposals | Best single channel on development | 4 / 7 / 1 | 1.00 | 5 / 12 |
| Curve fit using development diagnostics | Archived Codex proposals | 11 / 0 / 1 | 3.82 | 9 / 12 |

The archived vectors gave useful improvements in some cases. The simple curve fit
used the diagnostics of each new case and achieved a lower test risk in 11 of the
12 comparisons against those vectors. These comparisons measure transfer of an
existing proposal set. Measuring a model's ability to adapt requires fresh
responses, including the paired feedback ablation. The synthetic instances share
a generator and assume a known reference mass; success here covers a narrower
question than designing and validating a new sink on a gauge ensemble.
