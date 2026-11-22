# Amendment 02: full-budget seven-scene dry-run

This follow-up checks the corrected score-parameter wiring in the full file-entry path. It ran one synthetic world per scene at reference / outer / inner budgets 128 / 200 / 64. The five non-rejection paths completed `develop → evaluate → joint → improvement_certificate`, with 400 paired comparisons per receipt; each saved submission has `score_spec.alpha=0.05`, and `joint/metric_results.json` records `level=0.05`.

| Scene | Result | Reference / certificate outcome | Text diagnostic |
| --- | --- | --- | --- |
| `null_equal_candidate` | PASS | accepted / not certified | Equal-signal control completed the full chain; a single world is not a false-certification rate estimate. |
| `known_lower_excited_overlap` | PASS | accepted / certified | The constructed known-signal control was certified in this world. |
| `window_mismatch` | PASS | abstain | Reference gate rejected the mismatched-window world. |
| `reflection` | PASS | abstain | Reflection check rejected the world. |
| `relative_error` | EXPECTED_REJECTION | failure + abstain at `develop` | `Amplitude not identified: z=1.725`; seed and raw input retained. |
| `wrong_state` | PASS | abstain | Reference gate rejected the wrong-state world. |
| `nonfinite` | EXPECTED_REJECTION | failure + abstain at `develop` | `Nonfinite measurement`; seed and raw input retained. |

Every outcome-rate interval is `INCONCLUSIVE` at N=1. These receipts verify the exact statistical alpha, file-entry identity/gate parity, full budgets on paths that reach `joint`, and failure normalization. They do not calibrate the score, estimate power, or support a physical conclusion; `physical_score=null`.

See [`dataset_results.json`](dataset_results.json), the scenario receipts, and the frozen [`executor_spec.json`](executor_spec.json). The amendment 01 run with `level=0.2` is preserved separately as a parameter-collision diagnostic and is never pooled into the corrected run.
