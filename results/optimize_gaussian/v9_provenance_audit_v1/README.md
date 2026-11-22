# Archived optimize_gaussian v9 provenance audit

**Classification: source hashes recovered; run environment and original raw-input receipt remain incomplete.**

## Source closure

The v9 manifest declares 4 optimizer source dependencies plus the pion statistics source. The current hashes match for the following sources; the historical train.py hash is recoverable exactly from Git commit ea83f9ed0934. The recorded statistics hash also matches the current statistics.py.

| Source | Matches current file | Exact historical commit containing expected bytes |
| --- | --- | --- |
| tasks/optimize_gaussian/features.py | yes | 7d3b0229b9ea49fd3b921793e4400c086e02552f |
| tasks/optimize_gaussian/kernels.py | yes | 78512c0d9e6dbb1d575bf458199779123dbde821 |
| tasks/optimize_gaussian/submission.py | yes | 97143d8f4f4c591e81841110c605ec754e123332 |
| tasks/optimize_gaussian/train.py | no | ea83f9ed0934ce79d6ac8c41e4a89744390e06fd |
| tasks/pion_projection/statistics.py | yes | 3a88b10eb4588887ee690498c55b8be88a4f5a84 |

This recovers the source bytes required by the manifest. It does not establish which interpreter, package versions, GPU, driver, command line, or built extension executed the run.

## Split and archive identity

| Check | Result |
| --- | --- |
| Fit / dev-val / test IDs | 20 / 40 / 30 |
| Pairwise split disjointness | True |
| Test IDs equal archived pion validation IDs | True (30 IDs overlap) |
| Propagator cache keys match the split ID union | True (90 keys) |
| Training environment / hardware fields in manifest | none |
| Top-level workspace data/ directory | False |

The test set was already used by the pion pilot, so it cannot serve as a fresh blind set. The manifest records cache keys and split IDs but does not itself bind raw gauge/propagator bytes or the v9 output files.

## Referenced provenance files

| Manifest field | Referenced file | Workspace status |
| --- | --- | --- |
| cache_manifest | results/pion_projection/s16t16_v1/development_provenance.json | present |
| validation_manifest | results/pion_projection/s16t16_v1/validation_provenance.json | present |
| reference_bootstrap | results/pion_projection/s16t16_v1/reference_bootstrap.npz | present |

## Archived output inventory

| File | Bytes | SHA-256 prefix | Hash bound in original manifest |
| --- | ---: | --- | --- |
| results/optimize_gaussian/v9/basis_s20261117.npz | 73655 | 59532678d605bf72… | no |
| results/optimize_gaussian/v9/basis_s20261118.npz | 73959 | 0bd416163ef9d16b… | no |
| results/optimize_gaussian/v9/basis_s20261119.npz | 74294 | 8158bd1a215d6b96… | no |
| results/optimize_gaussian/v9/data.npz | 100744 | bbf8f0bbb7ae7d73… | no |
| results/optimize_gaussian/v9/fig_coeff.png | 37020 | 30d1427a71946b1a… | no |
| results/optimize_gaussian/v9/fig_q.png | 48287 | 0e99af26c88d4bb5… | no |
| results/optimize_gaussian/v9/fig_risk.png | 55787 | 9834e8c06819ecfa… | no |
| results/optimize_gaussian/v9/manifest.json | 10794 | a338c40953a093de… | no |
| results/optimize_gaussian/v9/results.json | 2126 | 66c0983af14deea6… | no |
| results/optimize_gaussian/v9/submission.json | 1017 | 4ff609eebc7970af… | no |

These hashes identify the files present during this audit; the original manifest has no per-output hash map. Do not treat this inventory as a retroactive run receipt.

## What this closes and what remains

- The four source dependency digests declared by v9 are all recoverable from the current tree or Git history (4/4); the statistics source digest is also resolved.
- The original training environment, exact run command/device receipt, and raw gauge/propagator bytes are still unavailable in the local archive.
- The manifest points to the same archived pion validation IDs 70–99. Those results are observed and do not count as an independent blind evaluation.
- The v9 result remains a historical fixed-random-W coefficient fit; it is not evidence that W was trained or that a learned smear beats SLSQP.

The next agent should preserve this partial boundary, seek the original training receipt and raw inputs, and use fresh gauge IDs for any new learned-W comparison. If those records cannot be recovered, mark the missing fields explicitly and proceed only with a newly frozen production plan. The required paired-risk, convergence, total-cost, and failure diagnostics are listed in tasks/optimize_gaussian/todo.md.

Reproduce the read-only audit with:

    python3 -B -m tasks.optimize_gaussian.v9_provenance_audit run

Verify the frozen audit inputs and output hashes with:

    python3 -B -m tasks.optimize_gaussian.v9_provenance_audit verify
