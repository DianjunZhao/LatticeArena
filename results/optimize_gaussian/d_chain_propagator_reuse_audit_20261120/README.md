# Optimize D-chain propagator reuse audit

**Status: `VERIFIED_FOR_TRAIN_DEV_AFTER_RECEIPT_ADAPTER` for fit/development inputs; Optimize scoring remains diagnostic.**

- Pion point propagators: 100/100 byte hashes verified for D IDs 0-99.
- Metadata: geometry [16, 16, 16, 16], point source [0, 0, 0, 0], boundary -1, kappa [0.14], tolerance 1e-10, max iterations 10000.
- Maximum recorded inversion residual: `9.997510675285575e-11`; complex128 arrays: 100/100.
- Frozen D HMC manifest hash: `1ab67540cafe1ee12cafb3df653c47f30480e75b41b6b633dd7334c69cdd7f4d`; Pion reference gate: `False`.

The cache can avoid repeating point-source inversions for Optimize fit IDs 0-59 and development IDs 60-99 after an Optimize-specific RunSpec binds the same solver settings, cache hashes, objective, and code. Current `train.validate_inputs` needs a small adapter because the cache metadata JSON omits residual_max; the generation-bound Pion measurement provenance supplies the per-configuration residuals. The cache audit does not transfer a Pion score or validate the Optimize observable.

The Pion D-development reference gate failed. Any optimization risk that uses its single-cosh reference is therefore a method diagnostic only until an independently justified reference passes its gate. This report did not inspect D IDs 100-199; the embargo and shared blind range remain unopened.

See `reuse_audit.json` for per-ID mismatches and all source/input hashes.
