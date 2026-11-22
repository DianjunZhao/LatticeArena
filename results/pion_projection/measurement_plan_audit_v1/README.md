# Pion measurement-plan preflight audit

This CPU-side audit covers plan schema, split identity, and checkpoint lifecycle. It does not claim a GPU measurement.

## Lifecycle contract

- `NOT_RUN` is a draft and is rejected before any accelerator import.
- `READY` is a frozen executable plan. It binds the measurement protocol SHA-256, requires a per-configuration trajectory manifest, and records a freeze timestamp.
- The run generation is SHA-256 over the frozen plan bytes, protocol fingerprint, split name, `measure.py`, and the submitted-kernel implementation. Each split stores that generation in both its `.npz` checkpoint and provenance JSON.
- Existing per-split checkpoints resume only when IDs are an exact prefix of the declared range, correlator shape and finite-value checks pass, and provenance has matching protocol and generation. Unrelated files in the output directory are allowed.
- Validation preflight verifies the trajectory map and frozen development submission/data hashes before `measure.py` imports CuPy, MPI, or PyQUDA.
- Each measurement record stores the raw gauge-file SHA-256, cached propagator byte SHA-256, HMC trajectory ID, 12-RHS residual maximum, and timing breakdown.

## CPU evidence

`measurement_plan_audit.json` records schema boundary checks. The focused tests additionally create a small temporary manifest and verify a partial checkpoint can be resumed, an already-complete split returns before accelerator imports, and validation preflight accepts a run directory that already contains the frozen development artifacts.

The frozen-plan test uses synthetic SHA values and a tiny temporary manifest. It verifies control flow and identity checks only. No real gauge file, QUDA residual, DCU measurement, or physical anchor was run. The independent physical measurement remains `NOT_RUN` until the plan is frozen against the actual new-ensemble protocol and executed on the cluster.
