# Amendment 01 follow-up: full-budget seven-scene dry-run

This is a one-world-per-scene execution check, not the registered 402/cell Monte Carlo. The frozen run used reference / outer / inner budgets 128 / 200 / 64 in the real `develop → evaluate → joint` file-entry path. All seven scenes finished (checkpoint `DRY_RUN_COMPLETE`, 7/7); five valid production paths returned `PASS`, and the two intentionally invalid inputs returned `EXPECTED_REJECTION`. Every record is synthetic and keeps `physical_score=null`.

| Scene | Budget | Result | Diagnostic |
| --- | --- | --- | --- |
| `null_equal_candidate` | 128 / 200 / 64 | PASS | 400 paired candidate draws; maximum helper/file-entry draw difference 0; reference accepted, candidate not certified. |
| `known_lower_excited_overlap` | 128 / 200 / 64 | PASS | 400 paired draws; parity passed; known-signal candidate certified in this single synthetic world. |
| `window_mismatch` | 128 / 200 / 64 | PASS | 400 paired draws; reference rejected and certificate abstained as intended. |
| `reflection` | 128 / 200 / 64 | PASS | 400 paired draws; reference rejected and certificate abstained as intended. |
| `relative_error` | 128 / 200 / 64 requested | EXPECTED_REJECTION | `develop` rejected the low-amplitude input: `Amplitude not identified: z=1.725`; recorded as `failure=true`, `abstain=true`, with seed and raw inputs. |
| `wrong_state` | 128 / 200 / 64 | PASS | 400 paired draws; the reference gate abstained on the wrong-state construction. |
| `nonfinite` | 128 / 200 / 64 requested | EXPECTED_REJECTION | `develop` rejected the nonfinite input; recorded as `failure=true`, `abstain=true`, with seed and raw inputs. |

Each cell has only one world, so all event-rate intervals are `INCONCLUSIVE` (for example, a 0/1 outcome has CP95 `[0, 0.975]`). The table verifies the execution path, frozen budgets, expected rejection schema, and retained inputs; it does not estimate false-certification, power, or physical performance. The two rejection scenes stop at `develop`, so their requested sampling budgets are recorded but their inner draws are not executed.

The authoritative per-world receipts, exact seeds, code hashes, gate parity and identity mutation checks are in [`dataset_results.json`](dataset_results.json) and the scenario subdirectories. This follow-up supersedes the initial smoke-only entries in [`full_gate_mc_20261119_v2_amendment_01/README.md`](../full_gate_mc_20261119_v2_amendment_01/README.md) for dry-run coverage; it does not supersede that directory's frozen amendment protocol.

The separate 402/cell run is resumable under [`full_gate_amendment01_execution_02/`](../full_gate_amendment01_execution_02/). Partial checkpoints must not be interpreted as final rates. A complete calibration requires 402 valid worlds in each of seven scenes, per-scene CP95 summaries and a candidate-rate plot.
