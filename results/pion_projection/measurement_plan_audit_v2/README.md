# Pion measurement-plan audit v2

This CPU-only audit corrects the v1 summary-field bug. In v1, `ok` meant validator acceptance for schema cases but meant expected refusal for the draft preflight case; the aggregate therefore reported `all_expected=false` even though the individual outcomes matched the intended behavior.

The v2 report stores observed acceptance, expected acceptance, and per-case pass separately. It checks the current D/E split boundaries with synthetic hashes; it does not inspect remote manifests, gauge bytes, propagators, GPU execution, or physical score.

| Case | Operation | Expected acceptance | Observed acceptance | Pass | Diagnostic |
| --- | --- | ---: | ---: | ---: | --- |
| `legal_current_splits` | `validate_plan` | True | True | True | — |
| `overlapping_splits` | `validate_plan` | False | False | True | splits 'development' and 'validation' overlap |
| `invalid_protocol_hash` | `validate_plan` | False | False | True | protocol_sha256 must be a real SHA-256 for a READY plan |
| `missing_stop_rules` | `validate_plan` | False | False | True | stop_rules must be a non-empty list |
| `source_out_of_range` | `validate_plan` | False | False | True | split 'validation' exceeds the available configurations (180) |
| `draft_preflight` | `preflight` | False | False | True | plan status is NOT_RUN (draft); refusing to start a measurement |

Overall expected outcomes: **True** (6/6 cases).

Interpretation: a valid current split shape is accepted; split overlap, an invalid protocol hash, missing stop rules, and out-of-range IDs are rejected; a `NOT_RUN` draft is rejected before measurement setup. These checks do not make the measurement plan `READY` and do not certify any physical result.

The previous [v1 lifecycle report](../measurement_plan_audit_v1/README.md) is preserved as historical evidence. The new report fixes its aggregate interpretation without rewriting the old artifact.
