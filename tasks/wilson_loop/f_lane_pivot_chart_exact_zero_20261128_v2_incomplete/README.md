# Aborted exact-zero multi-noise attempt

This folder records a startup failure from the first execution of the nine-panel exact-zero screen. All nine open synthetic panels were captured and validated, but the driver raised a `NameError` because `cholesky` had not been imported. The run stopped before the first optimizer call: **0/54 fits attempted**, with no fit counted as valid, failed, or abstained.

The corrected run is in [`../f_lane_pivot_chart_exact_zero_20261128_v2/`](../f_lane_pivot_chart_exact_zero_20261128_v2/). The 27 source-package files from this aborted attempt were byte-identical to those in the corrected report (verified by SHA-256), so they are not duplicated here. `execution_status.json` is the authoritative process receipt; this folder contributes no fit outcome or model evidence.
