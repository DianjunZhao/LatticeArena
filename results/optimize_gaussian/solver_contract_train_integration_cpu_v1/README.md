# Optimize solver contract train-path CPU diagnostic

**Status: `diagnostic_only`.** This report records a deterministic CPU integration check. It is not a solver benchmark, physical score, production receipt, or evidence that learned smearing outperforms SLSQP.

## Text flow

```text
explicit protocol + exact-byte SHA-256
  → require all solver policy fields
  → RunSpec hashes solver_contract.py and rejects a missing/invalid policy
  → child rechecks protocol hash before preparing output or reading inputs
  → Powell objective calls are checked against one shared call/time budget
  → independently reevaluate the returned parameters under that same budget
  → estimate box KKT residual; probes consume the same budget but do not
    change the optimizer's best-so-far trace
  → accepted receipt returns the fit to the training grid
  → rejected receipt is atomically published; no learned candidate dev-val
    score or test evaluation follows
  → the parent worker records an optional failure-diagnostic hash only after
    the child process group is confirmed stable; run status remains failed
```

The protocol policy fields are `objective_call_cap`, `walltime_cap_seconds`, `residual_field`, `residual_tolerance`, and `require_solver_success`. Optimize currently accepts only `residual_field="kkt_residual"`. The CPU fixtures use declared synthetic values to exercise both branches; none of those values is proposed as a production threshold.

## Deterministic integration cases

| Fixture | Call sequence | Observed outcome | What the check establishes |
| --- | --- | --- | --- |
| Accepted Powell fit | 1 solver objective + 1 final-point reevaluation + 5 two-parameter KKT probes = 7 counted calls | `contract_accepted`; five probe rows have phase `residual_diagnostic`; best-so-far is unchanged by probes | Final-point and KKT work share the explicit budgets; diagnostic probes do not make the search trace appear better |
| Call cap = 2 | 1 solver objective + 1 final-point reevaluation; the next KKT request is stopped before evaluation | `contract_rejected`; reason `objective_call_budget_exhausted`; no `results.json` or `manifest.json` | The training entry point emits a diagnostic-only no-clobber rejection receipt and does not score the learned candidate on dev-val or test |
| RunSpec missing policy | Protocol is parsed, then preflight checks policy before binding data inputs or writing a RunSpec | `ValueError`; no receipt or training output directory | A new explicit RunSpec cannot silently use the legacy unguarded solver path |
| Explicit protocol missing policy | Protocol bytes hash is valid, but `optimizer.solver_contract` is absent | CLI exits before creating output or initializing GPU | The child validates the contract before output preparation and GPU work |
| Parent observes rejection diagnostic | A failed child writes a declared optional diagnostic JSON and exits nonzero | Parent receipt records its SHA-256 under `failure_diagnostic_outputs`; the run remains `worker_failed`, with `physical_score=null` | The rejected fit can be audited without being classified as an accepted training artifact |

The rejected main-path fixture records three calls to the test's risk stub: one baseline dev-val diagnostic before fitting and the two permitted objective evaluations. It records no learned-candidate dev-val score after the rejection, and no test evaluation. The pre-fit baseline calculation is distinct from selecting or scoring the learned candidate.

The `train.main` rejection and parent failure-diagnostic hash are exercised by separate CPU fixtures: one calls the training entry point with controlled optimizer functions; the other launches a fake child that writes a diagnostic JSON and exits nonzero. No test launched a real `train.main` process under the supervisor.

## Verification performed

Command:

```text
python -m pytest -q tests/test_optimize_solver_contract.py tests/test_optimize_runspec_builder.py tests/test_optimize_training_protocol.py tests/test_optimize_gaussian.py tests/test_optimize_worker_runspec.py tests/test_optimize_hard_timeout.py
```

Result: **113 passed**. The four solver/train modules alone had **87 passed**; the timeout/worker/builder subset had **38 passed** and overlaps in the builder module. Checks use synthetic arrays, temporary JSON/NPZ files, controlled SciPy stand-ins, fake child processes, and monkeypatched risk evaluation. They do not load production gauge fields, propagator caches, physical references, blind IDs, CUDA, or QUDA. The whole repository test suite was not run.

The diagnostic is reproducible from the listed test modules. Relevant implementation files are `tasks/optimize_gaussian/solver_contract.py`, `tasks/optimize_gaussian/train.py`, `tasks/optimize_gaussian/runspec_builder.py`, `tasks/optimize_gaussian/worker_runspec.py`, and `tasks/optimize_gaussian/hard_timeout.py`; the RunSpec binds the solver contract source, and the parent keeps optional rejection diagnostics separate from successful training artifacts.

Implementation SHA-256 at this report revision:

| File | SHA-256 |
| --- | --- |
| `tasks/optimize_gaussian/solver_contract.py` | `a3aa621c8c28be2145d324934634e9376e0c4b8ae2749e18564e1e847531530d` |
| `tasks/optimize_gaussian/train.py` | `e969db11bebba374e5617026f3c8f38aa129d7be4fa66167e98dae889c81fb27` |
| `tasks/optimize_gaussian/runspec_builder.py` | `b99351ba83fbc8f7ae7c13e877f73a057e1f66bfa457a364f073cd6648d0029c` |
| `tasks/optimize_gaussian/worker_runspec.py` | `21443a93ec7f8f34e319fbe0af00553e86b89f4c9d9950109d2e2f18ab8065d5` |
| `tasks/optimize_gaussian/hard_timeout.py` | `ef8180bb7236c07f6b0415f20fc2b74b36873f869a190be4bc6f5616db35aa17` |

## Limits and next work

- The KKT quantity is a scaled finite-difference stationarity estimate. Its practical suitability and threshold remain undecided by the researcher.
- The call cap covers solver calls, final-point reevaluation, and KKT objective probes. Production policy still needs a reviewed definition of which outer setup, GPU initialization, model training, and teardown costs belong in the walltime comparison.
- The in-process walltime guard is cooperative. A slow objective or native/GPU call can overrun once before the run is rejected. The outer process supervisor is a separate execution boundary and has not been exercised here with a real Optimize/GPU worker.
- The bundled historical protocol has no solver policy and remains on the legacy diagnostic route. The RunSpec builder requires an explicit policy for all new frozen protocols.
- The Pion reference gate remains failed. Any later Optimize risk using that reference remains `diagnostic_only` until a reviewed reference and statistical decision protocol are frozen.

Next, freeze the estimand, paired comparison, residual policy, call/time accounting, failure and abstention rules, multiplicity, sample size, and stopping rule. Then build a hash-bound production RunSpec from authorized inputs, run a GPU startup/interruption smoke, and only after those checks execute the production 2×2 and learned-smear comparisons. Each report should retain a calls/time convergence plot or an equivalent trace table, paired uncertainty, cost decomposition, and failure/abstention descriptions.
