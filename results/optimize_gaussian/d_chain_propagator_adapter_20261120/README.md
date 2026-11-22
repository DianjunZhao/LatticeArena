# Optimize receipt-adapter integration check

**Status: `PASS`.**

- IDs: D 0–99 (100 configurations). Verified: 100/100; failures: 0.
- Maximum residual: `9.997510675285575e-11`; 100/100 accepted input rows carry a nonempty trajectory ID. This adapter receipt does not itself prove equality with the HMC manifest trajectory; that crosswalk was separately checked in the [propagator reuse audit](../d_chain_propagator_reuse_audit_20261120/README.md).
- Generation: `ab8a41d27e0488ca3646ac83475e680f677b17a913d05913f7731ec87a4448ce`; protocol: `18ed89c914be7d11522256e1b159e2037cd26e89dbd6f46521a442110088f442`.

The test passes the real Pion NPZ/provenance pair and actual remote cache files through `train.validate_inputs`. This confirms input identity and residual receipt reuse for the fit/development ranges; it does not run Optimize training, validate a physical score, or open any held-out ID.

See `adapter_check.json` for the failure list and exact hashes.
