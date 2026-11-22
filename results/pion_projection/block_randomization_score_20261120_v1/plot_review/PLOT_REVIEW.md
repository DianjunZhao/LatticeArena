# Block-randomization diagnostics: plot review

This companion report only reformats the frozen `summary.json` and raw outcomes. It does not rerun datasets, change a method or threshold, or recalculate any interval. The original preregistered result directory and hashes remain unchanged.

- Main figure: [`readable_diagnostics.png`](readable_diagnostics.png)
- Paired contrast figure: [`paired_method_differences.png`](paired_method_differences.png)
- Canonical frozen-protocol fingerprint: `847f69b1391fc22a15d2b7c29ba6f16b5e0ed712aafdd239227fd47ea40202ee`; protocol JSON file SHA256: `a9aa5f64d970e242bc9f4a042d8c50b7b0ca0c0bf972eeb098b1ac9768c6da26`
- Execution provenance SHA256: `b71398f7351c58634746e41418923dbe80424f47294625c2d3bd325ab25189fe`
- Raw outcomes SHA256: `131da040790cb13a22597d928e20c5c28e58aeda0ba90d000cf9655493be0000`; summary SHA256: `13a155c7a527339448274846a50d13e04ff6d0c91255b3a473ed06e72c3aed8e`
- Plot-review script SHA256: `96e29730f73cf6a7ef35fad007d67487726ccda51309c95c10dd406ce78dbea5`
- Main figure SHA256: `dbd7e9eb796ed8375b492264eafad11c7d2cf15da44d33da1408e18d7adaaf56`; paired contrast figure SHA256: `db449c626bcc3fba4c60180ae8bb92d9dd51f0d117e14ab68c4729a6fe6d89e2`

## Interpretation

Figure label codes: G = equal-Gaussian null; S = common truth-shift null; T = equal Student-t5 null; A = uncertain-anchor null; Imp. = known lower-noise alternative.

The studentized sign-flip test is theoretically exact for the declared sharp null of independently sampled paired blocks that are exchangeable under swapping arm labels, with the pooled reference held invariant. The 400-dataset/cell Monte Carlo results are compatible with nominal 5% in the displayed cells, but the familywise intervals remain too broad to certify close calibration. The estimated power is only 10.0% at arm noise correlation 0.5 and 21.0% at 0.9 for the declared lower-noise alternative.

At zero anchor offset, sign-flip and paired-t certification rates are close. Relative to sign-flip, the paired-t rate differences in the two lower-noise cells are -0.25 pp [-2.50, 1.75] pp and +0.25 pp [-1.50, 2.00] pp; both intervals include zero. The paired-block bootstrap has higher estimated power by +6.00 pp [2.74, 10.26] pp and +5.75 pp [2.25, 9.76] pp. It also certifies more often in equal-Gaussian null cells (+1.50 pp at ρ=0.5 and +3.00 pp at ρ=0.9); the latter paired CI is [0.75, 6.25] pp. Higher certification is not evidence of better calibration.

The anchor-offset curves vary across cells, with wide familywise intervals; they do not establish monotonicity or a robust-score correction. Common truth shift is a relative-effect null under shared model/anchor misspecification, so passing it only supports no detectable arm difference under that generator. No method detects common model/state bias by design.

All 4,000 outer dataset/correlation cases produced valid block fits; anchor-offset reuse yields 7,200 rows. These are synthetic CPU results, not physical coverage. The experiment cannot establish validity for weak nulls with nonexchangeable arms, gauge-ensemble autocorrelation, or a full-ensemble `improvement_certificate` estimand. Keep physical score `null` until an independent production anchor is available.

![Readable null, anchor, and power diagnostics](readable_diagnostics.png)

![Paired method contrasts](paired_method_differences.png)

The next decision should remain the independent physical anchor / held-out measurement in `tasks/pion_projection/todo.md`; do not select a production score from these same calibration outcomes.
