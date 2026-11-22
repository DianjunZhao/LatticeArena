# Candidate certificate calibration: amendment 02

This version separates the Gaussian smear coefficient (`protocol.alpha`, currently 0.2) from the statistical certificate tail probability (`score_alpha`, frozen at 0.05). Amendment 01 used the smear value as the certificate alpha by mistake; its partial results are retained in `full_gate_amendment01_execution_02/RUN_REVIEW.md` and are excluded from this calibration.

## Frozen design

- Seven synthetic scenarios; 402 independent development/validation worlds per cell (2814 total), with 120 development and 60 validation configurations in each world.
- Full file-entry chain: synthetic MeasurementBundle → frozen development gate → evaluate → verified joint → `improvement_certificate`.
- Reference / outer / inner budgets: 128 / 200 / 64.
- Marginal, two-sided 95% Clopper–Pearson intervals per rate; target half-width ≤0.05. `PASS` on a precision field means only that this interval-width target was reached.
- Statistical score alpha 0.05 is independent of smear alpha 0.2. The output submission and joint metric receipt must both record 0.05.
- Shared random seeds are retained across amendment versions to compare the parameter correction on matched synthetic worlds. Amendment 01 counts are not pooled.
- Synthetic certificates keep `physical_score=null`; no GPU measurement or physical anchor is implied.

The seven-scene full-budget dry-run passed at [`full_gate_amendment02_full_dry_01/`](../full_gate_amendment02_full_dry_01/README.md). The resumable executor plan and code hashes are in [`executor_spec.json`](executor_spec.json). The main 402/cell run is separate at [`full_gate_amendment02_execution_01/`](../full_gate_amendment02_execution_01/); read its live `checkpoint.json`. At launch the checkpoint was 0/2814. Do not alter hash-bound sources while that executor is active.
