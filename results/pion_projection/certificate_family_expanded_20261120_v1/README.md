# Independent expansion of the synthetic C2 J=2/K=2 family benchmark

This run uses 400 independent dataset seeds. It repeats the original two-candidate (null/better), two-model (single/twostate) certificate subgate benchmark with 40 outer risk draws and 16 inner mass-bootstrap draws. The family claim is conditional on both reference-model gates passing and the two-state fit not landing on a mass boundary.

The study uses the same synthetic generator and implementation as `certificate_calibration.run_family`; it is not a full physical gate calibration. Design-matrix caching only avoids rebuilding identical deterministic matrices. The mass search grid, objective, covariance, gate, risk, and certificate calls are unchanged. A seed-matched parity smoke against the original function is recorded in `execution_provenance.json`.

| Outcome | Count | Rate | Marginal CP95 | Four-rate familywise CP95 | MC precision |
| --- | ---: | ---: | --- | --- | --- |
| Null candidate certified / all planned | 1/400 | 0.0025 | [0.0001,0.0138] | [0.0000,0.0178] | PASS |
| Null candidate certified / gate-valid | 1/183 | 0.0055 | [0.0001,0.0301] | [0.0000,0.0386] | PASS |
| Better candidate certified / gate-valid | 20/183 | 0.1093 | [0.0680,0.1637] | [0.0592,0.1795] | PASS |
| Abstain or invalid / all planned | 217/400 | 0.5425 | [0.4923,0.5921] | [0.4788,0.6052] | PASS |

Valid datasets: 183/400; gate abstentions: 217; invalid: 0; two-state boundary fits: 210/400.
Abstention reasons: `{"single_model_gate": 9, "single_reference_chi2": 9, "twostate_mass_boundary": 210, "twostate_model_gate": 213}`.

![C2 family outcomes and gate p-values](c2_family_diagnostics.png)

## Interpretation boundary

This is a synthetic family-subgate calibration for the declared C2 generator. It does not establish physical-state identity, validate a real anchor, or replace the source-limited 402/cell full-gate runs. The null-candidate family event is directly counted; conditional rates use only datasets passing both model gates. Any conditional interval whose marginal CP95 half-width exceeds 0.05 is marked INCONCLUSIVE. No post-hoc top-up is permitted.

Raw per-dataset outcomes, seeds, gate p-values, boundary flags, certificate lower bounds, protocol/source hashes, and artifact digests are retained. Verify with `python -B -m tasks.pion_projection.certificate_family_expanded --verify`.
