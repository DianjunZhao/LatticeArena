# Run review: invalid protocol-field attempt

This directory is retained for audit and is not a valid known-improvement calibration.

- The run generated all 402 planned input datasets, but `run_dataset` raised `KeyError: 'reference_nominal_window'` for every row. The field is not present in the frozen base protocol; the nominal window index is 1.
- No risk estimate or gate outcome was computed. The 402/402 failure count is an implementation failure, not a gate failure or missed-improvement rate.
- The original runner mislabeled the execution `COMPLETED`. That status has been corrected to `FAILED_PROTOCOL_FIELD` in `run_metadata.json`; the original raw rows and summary are retained.
- The runner now uses an explicit frozen nominal-window index, increments the protocol version and seed, writes a fresh v2 plan, and refuses to reuse this directory.

No results from this attempt are pooled with the corrected v2 run.
