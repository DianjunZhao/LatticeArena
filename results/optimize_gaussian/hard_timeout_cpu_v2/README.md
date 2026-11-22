# Optimize hard-timeout supervisor: CPU diagnostic

This is a deterministic process-control smoke using synthetic Python workers. It does not run Optimize training, SciPy fitting, GPU/MPI, real propagators, or a physics score.

Supervisor SHA-256: `c01bc4fa44387e1a569c5dcdf8bc15e81efa68535216d651edeb9c7ebaee438d`  
Diagnostic SHA-256: `6d004a82894b1bce24925d47dd070c9eaa9b88ea63ca6d38b6154e142e6ec10e`  
Focused test source SHA-256: `525b16a8d10d6e0e0e1717ecacce6814055d2236f37f332725e89df5d8874188`  
Focused tests: **9 passed**  
Physical score: `null`

| Case | Status | Cap (s) | Elapsed (s) | Exit code | Calls | Best so far | Cleanup | SIGKILL |
|---|---:|---:|---:|---:|---:|---:|---|---|
| normal | completed | 2.000 | 0.253 | 0 | 4 | 0.25 | n/a | not needed |
| timeout | hard_timeout | 0.220 | 0.239 | -15 | 2 | 0.5 | confirmed | not needed |
| term_resistant | hard_timeout | 0.220 | 0.314 | -9 | 4 | 0.25 | confirmed | sent |
| worker_failure | worker_failed | 2.000 | 0.042 | 7 | None | None | n/a | not needed |

## Event timeline (text diagnostic)

- `normal`: launch -> 4 durable checkpoint calls -> worker exit 0 at 0.253s.
- `timeout`: launch -> 2 durable checkpoint calls -> deadline 0.220s -> TERM sent -> grace 0.080s -> group exited during TERM grace -> cleanup confirmed -> supervisor done 0.239s.
- `term_resistant`: launch -> 4 durable checkpoint calls -> deadline 0.220s -> TERM sent -> grace 0.080s -> SIGKILL sent -> cleanup confirmed -> supervisor done 0.314s.
- `worker_failure`: launch -> None durable checkpoint calls -> worker exit 7 at 0.042s.

The timeout cases hash the last checkpoint only after cleanup is confirmed. If a worker group remains alive, the receipt status is `termination_failed` and mutable checkpoint/log hashes are withheld. A timed-out run remains an execution-control failure and cannot enter a risk comparison. Supervisor cleanup/grace time appears in elapsed time and may exceed the worker deadline.

## Boundary and next integration step

The supervisor is implemented and CPU-tested as a standalone command wrapper. The focused suite also injects a SIGKILL denial while a TERM-resistant descendant remains alive; the expected outcome is explicit `termination_failed` with mutable file hashes withheld. It is not yet wired into `train.optimize` or the production RunSpec; the synthetic worker writes its own checkpoint to exercise partial-output binding. GPU context setup, real optimizer interruption, startup overhead, and accelerator cleanup remain `NOT_RUN`.
