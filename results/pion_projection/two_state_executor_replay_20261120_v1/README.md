# Stable two-state executor replay on public D0–99

**Status: same-input numerical parity diagnostic only.** This run uses no new samples. It replays the exact archived deterministic starts on the already hash-audited D-development input, comparing the new `TwoStateFit.fit_full_multistart` implementation with the previous D-only multi-start rows.

Input audit: `READ_ONLY_COUNTS_VERIFIED`. Baseline multi-start receipt SHA-256: `6897094ca5c4af45814b1a39cd886c151c039f38db66dc72419815e24e8d2602`. Stable executor source SHA-256: `df37ef7a1b5c8f4cd27d91c2e2a0d0653911c1a4c1a09bff0fc8b647c2a99aca`.

![Archived versus stable-executor endpoint costs](executor_replay_parity.png)

| Window | Starts | Previous solver success | Replay solver success | Replay endpoint statuses | Max $|ΔC^2|$ | Max $|Δm_0|$ | Max $|Δm_1|$ | Best-found replay gap |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| [4, 5, 6, 7, 8] | 29 | 24/29 | 24/29 | converged_full_rank: 24, nested_m1_boundary: 5 | 0 | 0 | 0 | 0.683765 |
| [5, 6, 7, 8] | 29 | 24/29 | 24/29 | converged_full_rank: 23, near_nested_m1_boundary: 1, nested_m1_boundary: 5 | 0 | 0 | 0 | 0.628866 |
| [6, 7, 8] | 29 | 24/29 | 24/29 | converged_full_rank: 23, near_nested_m1_boundary: 2, nested_m1_boundary: 4 | 0 | 0 | 0 | 0.926454 |

The parity plot compares each archived endpoint objective to the replayed objective; the dashed line is equality. Non-success endpoints remain present and are colored separately. The CSV retains every start and both solver statuses.

## Limits

- Both analyses use the same D0–99 data, the same fixed covariance, the same SLSQP implementation, and the same starts; this is a code-path check, not an independent fit or Monte Carlo replication.
- A finite lower endpoint is only the best found among these starts. It is not a global-minimum certificate.
- `gap=0` is reported as the nested M1 boundary; failed SLSQP endpoints there remain nonconverged and cannot be called a two-state solution.
- This does not reopen the frozen single-cosh FAIL, approve the draft M2 plan, authorize E measurement, or create a physical score. `physical_score=null`.
- Reproduce with `PYTHONDONTWRITEBYTECODE=1 python3 -B -m tasks.pion_projection.two_state_executor_replay`; output includes the CSV, JSON summary, PNG and hash provenance. Existing output is refused unless `--refresh-owned-output` first verifies the script's own prior output hashes.
