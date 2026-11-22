# Frozen worker RunSpec CPU diagnostic v3

This one-shot diagnostic uses only temporary synthetic protocol/source/input
files and a child Python process that prints a marker. It verifies the worker
launch boundary; it is not a training run, GPU smoke, solver comparison, or
physical score (`physical_score = null`).

## Text flow

```text
frozen RunSpec JSON
    -> parse strict JSON (duplicate keys and non-finite constants rejected)
    -> verify protocol/source/input SHA-256 and disjoint split IDs
    -> launch with only RunSpec environment variables; bind env hash and names
    -> verify no-clobber output paths
    -> start argv-only worker in a new process group
    -> bind RunSpec hash, verified files, logs, exit/timeout status in receipt
```

## Observed cases

| Case | Result | Worker started | Meaning |
| --- | --- | --- | --- |
| valid frozen spec | completed | yes | Verified protocol, source, synthetic input, and disjoint IDs before launch. |
| explicit environment | completed | yes | Child saw the RunSpec value and did not inherit an unbound parent variable. |
| mutated source | preflight rejected | no | Source drift was caught before any log or receipt was created. |
| mutated input | preflight rejected | no | Input drift was caught before any log or receipt was created. |
| overlapping split IDs | preflight rejected | no | Shared configuration IDs across fit and blind splits were refused. |

Raw case rows and hashes are in `cases.csv` and `summary.json`. The existing
standalone timeout tests cover child timeout, process-group cleanup, and
termination failure. This diagnostic does not show that SciPy, CUDA, QUDA,
or a live production RunSpec can be safely interrupted. Production thresholds,
reference validity, arm matching, and device-side cleanup still require a
reviewed task-specific RunSpec and an authorized GPU smoke.
