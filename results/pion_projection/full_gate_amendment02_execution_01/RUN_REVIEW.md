# Amendment02 execution review: duplicated source-hash discrepancy

## Result that completed

The driver completed all 2814 planned worlds (402 in each of seven scenarios). Its `parallel_driver_spec.json` records `source_hashes_match=true`; those hashes come from `executor_spec.json`, which the driver checked before scheduling workers. All rows have the planned seed and a terminal adapter receipt. The 2070 `PASS` receipts have statistical score level 0.05, zero direct/helper draw difference, matching gate parity, and all five identity mutations rejected. The other 744 receipts are the planned relative-error/nonfinite input rejections.

## Source identity discrepancy

The amendment02 high-level `preregistration.json` and `executor_spec.json` contain duplicate source identity records that disagree for one file:

| File | High-level preregistration | Execution spec | Receipt / current source |
| --- | --- | --- | --- |
| `synthetic_adapter.py` | `206cce77df19375fe79a02bc796806d572775c0f6a0e8df18b0b7ff0a9aa9f7d` | `26e76a5ecad5a56b7c2bf867715d4b68a237437953e0820981ca76b5ac6b3a41` | `26e76a5ecad5a56b7c2bf867715d4b68a237437953e0820981ca76b5ac6b3a41` |

All other overlapping preregistration/execution-spec hashes agree. The execution spec hash agrees with the current source and each receipt's `synthetic_adapter.py` hash; the driver used and verified this execution spec. The high-level preregistration's adapter hash is stale relative to the executed source. The old source bytes are not present in the accessible workspace, so this review cannot determine whether the difference was only a metadata/edit change or affected behavior.

## Classification and follow-up

Do not rewrite either frozen plan or delete the raw results. Keep this run as a complete execution with a **partial strict-preregistration provenance reconciliation**. Its rate estimates are reproducible against the execution-spec hash, but should not be described as fully source-consistent with every hash field in the high-level preregistration.

If a strict pre-registration claim is required, create a new amendment and output directory, use one canonical hash manifest for both preregistration and executor, record the executor-spec hash before launch, then rerun the full 402-per-cell design. Do not top up or pool this run with another amendment. Physical anchor and production measurement remain separate GPU/ensemble-dependent work.
