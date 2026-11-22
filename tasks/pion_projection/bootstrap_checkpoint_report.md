# Resumable M2 bootstrap executor: CPU implementation check

**Status: checkpoint mechanics pass; reference decision remains `ABSTAIN / NOT_READY`.** This report describes the bootstrap journal and its interruption tests. It does not run a new calibration, read E/validation/holdout data, or calculate a physical score.

## Data flow

```text
frozen block-index matrix + starts + fixed precision + fit configuration
                              │
                              ▼
                 hash-bound run manifest
                              │
            ┌─────────────────┴─────────────────┐
            ▼                                   ▼
       fit draw 0                           fit draw k
       retain every start                  retain every start
            │                                   │
            └── strict JSONL row + hash chain ──┘
                              │
                  append one row, then fsync
                              │
                              ▼
            complete receipt after all planned draws
```

On resume, the writer takes an exclusive directory lock, checks the exact manifest and verifies each committed row's draw ID and hash chain. A trailing partial row is truncated to the last newline and that draw is rerun. A complete but malformed or hash-mismatched row stops recovery. The first intact row is retained byte-for-byte. Outputs are limited to `manifest.json`, `draws.jsonl`, `status.json`, and a lock file in the caller-selected new directory; an existing directory is never reused unless `resume=True` is explicit.

The manifest binds the fitted block-sample matrix hash and shape, per-channel normalization scales, planned block-index matrix, ordered configuration IDs within every fitted block, starts, fixed precision, fit configuration, mass bounds, optimizer controls, executor source hash, and Python/NumPy/SciPy/platform metadata. Each JSONL row retains all multi-start endpoints, including solver failures, boundary classifications, and rank/condition diagnostics. Both completion status and runner receipt label the result `diagnostic_only` and set `physical_score` to null.

## Verification

`tests/test_pion_bootstrap_checkpoint.py` covers a simulated interruption after one committed draw, successful continuation without rewriting that draw, recovery from a torn final line, manifest mismatch, complete-row corruption, out-of-order draws, exclusive writer locking, and no-clobber creation. Combined with `tests/test_pion_twostate_stable.py`, the focused suite passes **16 tests**. The latest full CPU suite passes **270 tests**, with one unavailable-CuPy skip and one known Wilson rejection warning.

The tests use deterministic CPU fixtures. They do not calibrate false-acceptance or power, prove an optimizer global minimum, freeze the proposed N=60/12-block M2 protocol, or authorize E measurement. In-flight solver work is not checkpointed; an interrupted draw is rerun from its planned starts.

## Next decision

The current public-D feasibility review still says `ABSTAIN / NOT_READY`, so this machinery is a reusable execution component, not a reason to run a new M2 Monte Carlo. If a reviewer-approved physical redesign changes the stop decision, freeze the M1/M2 roles, start family, covariance/resampling policy, all failure denominators and thresholds first. Then run the exact-design null, wrong-state, known-improvement and common-bias calibration with Monte Carlo intervals and a result figure/table before considering E.
