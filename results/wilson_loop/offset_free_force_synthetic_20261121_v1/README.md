# Synthetic offset-free Wilson-force diagnostic

**Status:** `synthetic_method_diagnostic_only`; no production score or gate change.

## Text result

- A common potential shift δ=0.030 shifted every fitted V by δ; maximum numerical discrepancy from δ was `4.163e-16`.
- The corresponding discrete-force shift was unchanged to `6.661e-16` maximum absolute difference.
- The constructed R-dependent offset shifted adjacent-R force by 0.020, 0.030, 0.050 (expected 0.020, 0.030, 0.050).
- The figure shows the potential translation, overlap of the baseline/common-shift force curves, and the known R-dependent negative control.

![Synthetic offset-free force controls](offset_free_force.png)

## Scope and limitations

The data are 100 synthetic positive loops with 20 blocks of length 5 and 5000 shared block-bootstrap draws. The pointwise percentile intervals are descriptive. The test verifies algebra and code behavior under constructed controls; it does not establish a real-data bias detector, validate ground-state extraction, calibrate family-wise error, or approve changing the frozen absolute-potential target. A real force comparison would still need shared block indices, a frozen estimator, finite-T controls, lattice-spacing interpretation, and independent evaluation.

Raw per-R rows and hashes are in `force_rows.csv` and `summary.json`.
