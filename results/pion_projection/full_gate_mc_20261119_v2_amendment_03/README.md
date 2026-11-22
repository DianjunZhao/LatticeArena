# Amendment03 source-aligned replay

This plan repeats amendment02's fixed seeds and seven 402-dataset scenarios to verify
the current source identity under one canonical manifest. It is a deterministic
reproducibility replay, **not an independent Monte Carlo sample**; do not pool it with
amendment02 or use it to narrow statistical intervals.

The complete source hash map is identical in `preregistration.json`, `executor_spec.json`,
and `source_manifest.json`. The runner checks both map equality and every current file hash
before the first dataset is scheduled. Amendment02 remains preserved with its original
partial provenance classification.

Prepare: `python -m tasks.pion_projection.source_aligned_mc --prepare`
Execute: `python -m tasks.pion_projection.source_aligned_mc --execute`
