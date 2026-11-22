# Optimize-specific RunSpec builder: CPU preflight diagnostic

**Status:** `synthetic_preflight_only`; no training worker, GPU, QUDA, production cache, or blind split was opened. `physical_score` is `null`.

## Text flow

```text
frozen protocol bytes
  -> parse fit / dev_val / test inclusive ranges and reject any overlap
  -> read development and validation cache manifests; require every planned ID
  -> bind each gauge, propagator .npy, and metadata sidecar by SHA-256
  -> bind reference/bootstrap, Pion measurement receipt (if declared), and
     exact Optimize / statistics / supervisor source files
  -> construct argv with --protocol and --protocol-sha256
  -> verify explicit child environment and fresh logs / results / manifest /
     data / per-seed basis-cache paths
  -> write a new RunSpec
  -> (separately) supervisor rechecks all hashes and starts the declared child
  -> after a fully exited successful child, hash every declared artifact
```

The builder is [`runspec_builder.py`](../../../tasks/optimize_gaussian/runspec_builder.py). Its CLI accepts a JSON request and writes a no-clobber RunSpec. Preparation records the protocol hash, source and input hashes, split IDs, child environment, timeout, output artifacts, and the child command. The final `_validate_spec` check uses the same generic RunSpec rules as the execution worker, but it does not start a child process.

## Synthetic CPU checks

`tests/test_optimize_runspec_builder.py` uses three synthetic configuration IDs and temporary fake gauge, propagator, sidecar, manifest, and bootstrap files:

| Case | Observed result | What it checks |
| --- | --- | --- |
| Valid synthetic protocol | RunSpec prepared; no training output directory created | Protocol SHA, required source/input bindings, split IDs, artifact paths, and no-clobber RunSpec write. |
| Builder CLI | `prepared_not_executed`; `physical_score=null` | The command-line generator writes the spec without launching its child command. |
| Pion measurement receipt supplied | Both measurement and provenance files are bound | Optional NPZ/provenance identities are included when the protocol declares them. |
| Overlapping `fit` / `dev_val` IDs | Rejected before any output is written | A configuration cannot enter two analysis splits. |
| Planned ID absent from both manifests | Rejected before any output is written | The protocol cannot silently reference an unbound cache configuration. |
| RunSpec path collides with receipt output | Rejected before writing | The prepared spec cannot consume its own worker receipt path. |
| Duplicate protocol JSON key | Rejected before writing | Split and input interpretation cannot silently diverge from last-key-wins parsing. |
| Negative or repeated seed; malformed extra-input list | Rejected before writing | Every declared training seed and additional input binding has a usable type and identity. |
| Builder-to-supervisor CPU fixture | `completed`; all declared artifact hashes verified; `physical_score=null` | A builder-produced spec passes through `run_frozen_worker`; only the child argv is replaced by a temporary Python fixture that writes the declared files. The fixture never imports training code or accesses data/GPU. |

Focused command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest -q -p no:cacheprovider \
  tests/test_optimize_runspec_builder.py
11 passed

PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest -q -p no:cacheprovider \
  tests/test_optimize_runspec_builder.py tests/test_optimize_worker_runspec.py
26 passed
```

## Scope boundary and next work

These tests prove the RunSpec construction-to-supervisor artifact path only on fixtures. The worker command emitted by the builder targets `python -B -m tasks.optimize_gaussian.train`; the end-to-end test verifies that command and then substitutes a fake child, so it does **not** run `train.main`, read production cache bytes, initialize GPU/QUDA, or prove GPU cleanup. This distinguishes an already connected process-level deadline from the still-unintegrated optimizer-level solver acceptance policy in `train.optimize`. It does not construct a production Optimize RunSpec, validate an external physics reference, or approve a score. The current bundled v9 protocol is not promoted to a new run: its test IDs have already been observed, and Pion's reference gate currently fails. Before a real RunSpec can be generated or executed, freeze a new reviewed protocol and its objective, reference status, budgets, stop/abstention rules, exact input/cache identities, and split authorization. The GPU smoke and paired learned-$W$ versus SLSQP / strong-spectral comparison remain `NOT_RUN`.
