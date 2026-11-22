# Amendment03 source-aligned replay: run review

Status: complete synthetic reproducibility/source audit; not a new independent calibration.

## Acceptance checks

- Expected and observed worlds: 2814 (7 scenarios × 402); all same-seed identities matched amendment02.
- Plan manifest closure: True; current source bytes match frozen hashes: True.
- Launch / driver frozen-source checks: True / True.
- Receipt core-code hash check: True; expected-rejection receipts remain distinct from execution failures.
- Execution used 10 workers after a recorded resume from 6; the original driver spec is retained at `parallel_driver_spec_workers06.json`, with the change documented in `execution_amendment_01.json`.
- Receipt files audited: 2814; terminal statuses: `{'PASS': 2070, 'EXPECTED_REJECTION': 744}`.
- Primary outcome field disagreements across same-seed records: 0; all deterministic-field disagreements: 0.
- Exact raw input array comparisons: 2814/2814 datasets match; mismatches by scenario: `{'null_equal_candidate': 0, 'known_lower_excited_overlap': 0, 'window_mismatch': 0, 'reflection': 0, 'relative_error': 0, 'wrong_state': 0, 'nonfinite': 0}`.
- No physical score was generated; `physical_score=null`.

## Interpretation

A matching same-seed replay establishes that this new frozen source manifest can reproduce the recorded synthetic path to the extent captured by its receipts. It does not add independent MC information and must not be pooled with amendment02. The old amendment02 preregistration/executor hash discrepancy remains unresolved because the original source bytes were unavailable; this run does not retroactively repair it. The next scientific gate is an independently identified physical anchor / production measurement, which remains NOT_RUN without GPU/cluster inputs.
