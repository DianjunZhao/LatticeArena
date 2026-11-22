# Optimize worker artifact-receipt diagnostic v4

This CPU-only check exercised the optional `outputs.artifacts` field in a
synthetic worker RunSpec. The child process wrote tiny fixture files; no
training code, production cache, GPU, QUDA, or physical score was involved.

## Text flow

```text
RunSpec declares new artifact paths
  -> parent checks paths do not overwrite inputs or existing files
  -> child runs under the existing deadline supervisor
  -> supervisor closes leftover descendants before checking file stability
  -> only a zero-exit, completed child gets artifact SHA-256 values
  -> parent execution receipt records each path/hash
```

If the worker fails or times out, declared artifact paths receive
`artifact_output_status=not_accepted` and their hashes remain null. If a worker
exits successfully but omits a declared artifact, its process status remains
`completed`, while `artifact_output_status=incomplete_or_unreadable` prevents
the command-line runner from returning success. A pre-existing artifact is
rejected before logs or the execution receipt are created.

Artifact paths may live under a new training output directory. Preflight
requires an existing directory ancestor and rejects a pre-existing artifact;
the supervised child may create the new run directory. This matches
`train.main`, which creates its fresh output folder before writing
`results.json` and `manifest.json`.

Artifact paths may live under a new training output directory. Preflight
requires an existing directory ancestor and rejects a pre-existing artifact;
the supervised child may create the new run directory. This matches
`train.main`, which creates its fresh output folder before writing
`results.json` and `manifest.json`.

## Observed cases

| Synthetic case | Parent receipt | Artifact hash | Diagnostic meaning |
| --- | --- | --- | --- |
| Child writes results and manifest, exits 0 | `completed`, artifacts `verified` | Both present | Output hashes are linked to the same parent execution receipt. |
| Child writes a partial result, exits 7 | `worker_failed`, artifacts `not_accepted` | Null | A failed run cannot make a partial result look accepted. |
| Child exits 0 without writing its declared result | `completed`, artifacts `incomplete_or_unreadable` | Null with `FileNotFoundError` | Process completion and artifact completeness are distinct states. |
| Declared result already exists | Preflight rejection | Not computed | Existing files are preserved; the worker is not started. |
| Leader exits 0 but leaves a child in its process group | `worker_failed`, artifacts `not_accepted` | Null | The supervisor terminates the leftover group before hashing mutable files. |

The command-line status was checked too: an incomplete declared artifact makes
the CLI return failure even when the child exits with code 0; completed runs
without declared artifacts continue to return success.

Focused verification:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest -q -p no:cacheprovider \
  tests/test_optimize_hard_timeout.py tests/test_optimize_worker_runspec.py
24 passed
```

This closes only the generic CPU mechanism for linking declared child
artifacts to a parent receipt. It does not create or approve a task-specific
Optimize RunSpec, validate the Pion reference, certify solver gates, establish
GPU/QUDA interruption safety, or show that learned smear beats SLSQP or the
strong spectral baseline.
