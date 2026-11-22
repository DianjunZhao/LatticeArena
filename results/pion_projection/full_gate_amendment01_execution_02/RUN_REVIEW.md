# Run review: amendment 01 stopped after parameter-collision diagnosis

The executor process is no longer running. The last atomic checkpoint is **2026-11-19 20:00:41 +08:00**, 595 / 2814 worlds: `null_equal_candidate` 402 / 402 and `known_lower_excited_overlap` 193 / 402. The remaining five scenarios had not started. `checkpoint.json` is preserved as the last machine-written state (`RUNNING`); it does not mean a process is still live. Do not resume this output directory.

## Why this version is diagnostic only

The frozen measurement protocol's `alpha=0.2` is the smear coefficient in `H=(1+alpha*spatial_hopping)/(1+6*alpha)` (`tasks/pion_projection/kernels.py`). Before the correction, `experiment.develop` also copied that same value into `submission.score_spec.alpha`. A completed null receipt therefore used certificate quantile `level=0.2`, while [`score_spec.example.json`](../../../tasks/pion_projection/score_spec.example.json) specifies statistical `alpha=0.05`.

Under the declared equal-signal null, the completed cell recorded candidate certification in 92 / 402 worlds (22.9%, CP95 [0.189, 0.273]); reference acceptance was 342 / 402, abstention 60 / 402 and failure 0 / 402. The interval `precision_status=PASS` only means the CP95 half-width met the precision target. These numbers diagnose the alpha collision; they are not a valid calibration of the intended 0.05 certificate.

## Preservation and next run

- All completed receipts and incomplete attempts remain unchanged. The checkpoint's completed sample counts are retained as evidence of the misconfigured run.
- The code now builds `score_spec.alpha` from the separate `score_alpha` field (default 0.05), leaving the kernel coefficient recorded as `smear_alpha`.
- Re-run the full-budget seven-scene dry-run, verify `metric_results.level=0.05`, then create a new preregistration / executor spec and a new results directory for the corrected 402/cell MC. Do not change this directory or reuse its counts in the corrected run.
- `physical_score` remains `null`; this run contains synthetic data only.
