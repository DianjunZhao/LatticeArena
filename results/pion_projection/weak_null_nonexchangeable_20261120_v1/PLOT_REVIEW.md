# Plot review: weak-null tail stress test

The original analysis image had overlapping footer text and legend. This display-only review redraws the same frozen `summary.json`; it does not rerun the simulation, change any rate, interval, threshold, dataset, or protocol.

- Frozen summary SHA-256: `8510e48fd091b946cf5beb6eca4a13a78aba4c75999639bce58d754b34efec9d`
- Original analysis image SHA-256: `c3239e1be09062fa66802887bf0215b058794eda560d15e9000ade5335a4814d`
- Reviewed image SHA-256: `76c6fa0d0afed78349d589deb9d9627e92681d69ec74ed4e8eaf004b39037550`
- Data source: the 30-cell summary with exact pointwise Monte Carlo CP95 intervals and the 3000 outer datasets per cell.

![Reviewed weak-null size and power figure](weak_null_size_power_review.png)

The left panel shows that four plug-in/resampling procedures rise to roughly 9.4–16.6% false certification in the declared rare-tail mean-zero world, while they are near 5.5–7.0% in the Gaussian control. The right panel shows the deliberately strong +1.5 SD alternative; the known-variance MoM bound has 94.8% and 99.9% power at 24 and 48 blocks. This caption describes only this synthetic generator and the exact frozen summary.
