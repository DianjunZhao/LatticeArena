# LatticeArena framework: verified extension map

This note maps the extension points present in the current checkout and separates
working interfaces from integration work that a new task still needs. It is a
source review, not a claim that all modules already form one generic runtime.

## Current component map

```mermaid
flowchart LR
  TS[TaskSpec / RunSpec] --> OC[OperatorContract / CandidateSpec]
  MC[MeasurementBundle + capability flags] --> EV[Task evaluator]
  OC --> EV
  PR[Agent or optimizer proposals] --> SV[Shared search validator + budget]
  SV --> EV
  EV --> CP[Paired comparator]
  EV --> ST[RunState gates]
  EV --> LG[Cost ledger]
  TS --> IO[Hash / fingerprint / JSON I/O]
  IO --> ST
  IO --> LG
```

The boxes are reusable components, while the arrows show a useful task-level
assembly. The Pion pipeline is the implemented end-to-end example. New task
folders still need to connect their own measurement and estimator to these
contracts; declaring a schema alone does not create an evaluator.

## Extension points confirmed in source

| Need | Existing hook | What a new task must add |
|---|---|---|
| Describe a scientific problem | [`core/specs.py`](../core/specs.py): `task_spec` includes observable, geometry, boundary, source, splits, reference, metric, budget, dependencies | Freeze units, operator conventions, split identity, reference and invalid-result rules; strengthen checks for disjoint splits and permitted data capabilities where needed |
| Declare an operator/candidate | `operator_contract` and `candidate_spec` bind axes, dtype, transformation, support, parameters, builder and dependencies | Add an explicit versioned contract and builder validator. The current candidate registry only accepts `pion-kernel-v1` and `wilson-kernel-v1`; Optimize needs its own candidate schema before production integration |
| Add a measurement backend | [`core/measurement.py`](../core/measurement.py): arrays, manifest, dtype and declared `linear_response`, `cross_matrix`, `new_source` capabilities | Implement the task-owned CPU/GPU/MPI measurement route, bind inputs and software identity in the manifest, and reject unavailable capabilities before measurement. Current bundle validation checks finite nonempty arrays; it does not provide storage isolation or verify all provenance hashes by itself |
| Add a search method | [`core/search.py`](../core/search.py): common validate → budget → evaluate → record path | Adapt LLM, deterministic optimizer, evolutionary search or learned initializer to emit proposals; count invalid attempts according to the frozen budget and retain every rejection reason |
| Add a score or paired estimand | [`core/comparator.py`](../core/comparator.py): shared draw-length checks, optional unique draw IDs, positive paired risk ratio and a log lower bound | Implement the task estimand and failure policy; preserve common draw/configuration identity, planned denominators and multiplicity. A new formula must not silently inherit the current ratio's positivity or interval semantics |
| Plan diagnostics and retain denominators | The Pion bounded-risk feasibility grid/known-graph coverage MC and Optimize/Wilson CPU reports show reproducible seeds, explicit scenarios, source-bound raw rows, coverage intervals, and separate planned/valid/failed/abstained counts; these are task scripts, not a shared API yet | Add a versioned `ScenarioSpec`/seed plan and `RunReceipt` that distinguish panel, measurement, optimizer-fit, and stencil denominators. Keep cap-stop/non-success and abstention reasons rather than folding them into `valid` or dropping them |
| Track evidence readiness | [`core/state.py`](../core/state.py): operator, reference, numerical, statistical and comparison states; validation observation is permanent; a score is available only when all states have hash-bound validation | Provide evidence hashes and allowed transitions for each task. Keep diagnostic/physical output labels explicit and make abstention a first-class terminal result |
| Compare learned/iterative methods fairly | `core/ledger.py` has generic setup/solve/residual phases; the Optimize stress report keeps call cap, optimizer seconds, fit selection and postchecks separate | Add `BudgetSpec` fields for objective/gradient calls, setup, training, inference, I/O, recovery and amortization count. Enforce shared fit/heldout IDs, initialization policy and restart count; report call-budget and total-walltime estimands separately |
| Preserve artifacts | [`core/io.py`](../core/io.py): content digest, canonical fingerprint and JSON writing; the CPU diagnostics additionally retain raw synthetic arrays, source snapshots, plots and hash manifests | Bind protocol, code, environment, input, output, plot and report identities; use no-clobber run directories and retain failure receipts. A manifest proves byte identity, not scientific validity or input independence |

`agents/operator_search.py` illustrates repeated agent proposals against the
Pion development evaluator. `agents/optimization_benchmark.py` illustrates
paired synthetic episodes with development selection and a separate test draw.
These are task examples, not automatic plug-ins for every task family.

## Task-specific opportunities

- **Pion:** retain the current `MeasurementBundle` and sink-builder boundary;
  add an independent dependence/anchor evidence contract before any physical
  score gate can validate. The accepted bounded block-risk calibration belongs
  behind a versioned score specification, not in the generic comparator. Its
  finite planned-block denominator, failure-as-worst rule, `alpha_s/alpha_A`
  split and graph-color/mixing assumptions should be explicit contract fields;
  clipping changes the estimand and must be frozen before confirmation data.
  The synthetic coverage MC shows the cost of a wrong IID assumption under one
  known finite-dependence generator, and the conservatism of the graph bound;
  it does not establish the real score graph or anchor coverage.
- **Optimize Gaussian:** add a task-specific run specification that binds the
  same objective, reference, fit IDs, W/v/c constraints, SLSQP comparison,
  fixed spectral baseline, dual contrasts, equal-parameter-count arm, budgets
  and full failure receipts. The 36-panel synthetic grid demonstrates how to
  retain a paired heldout-loss plot and separate solver stops from failed fits;
  its small descriptive cells do not resolve physical reference or minimum
  effect size. The generic optimizer hook does not define those choices.
- **Wilson loop:** add versioned estimand contracts for finite-`T` Creutz and
  ground-state discrete force separately. Both can share block IDs and paired
  draws while using different systematic-error gates. The fixed q/h/x toy and
  randomized positive-spectrum stress validate the four-point algebra and
  envelope propagation over the declared synthetic ranges, but supply no
  physical contamination envelope. The generic `RunState` does not infer
  spectral, thermal or mixed-sector bounds.

## Practical implementation order for a new task

1. Define its observable, units, geometry, boundary/source convention, splits,
   reference, budget and failure states in a versioned task protocol.
2. Add operator/candidate and measurement-capability contracts; reject malformed
   plans before opening data or initializing a device.
3. Implement a task evaluator that emits raw measurements, paired draws,
   planned/valid/failed/abstained denominators and source-bound receipts.
4. Connect candidate generators through the shared validator and explicit cost
   ledger; keep training, search, measurement and inference costs separable.
5. Add CPU contract tests and synthetic checks for mathematical/software
   behavior, then authorize and verify the actual backend separately. CPU tests
   do not certify GPU/MPI physics behavior.
6. Add task-specific comparison and reporting; verify formulas, interval
   assumptions, identities, plots, artifact hashes and negative results.

Each diagnostic or confirmation report should include either a figure or a
textual data-flow/decision diagram, plus planned/valid/failed/abstained
denominators at every relevant unit of analysis. Solver cap-stops, statistical
failures and protocol abstentions are distinct states and should stay visible.

## Current integration boundary

The current `main` has a full Pion pilot. Pion dependence calibration and the
Optimize/Wilson additions are isolated analytic/synthetic CPU diagnostics and
theory artifacts; none is a production measurement pipeline. Pion's bounded
risk reports include a 1,728-scenario feasibility surface and a known-graph
coverage MC; the companion Optimize/Wilson PR reports the 36-panel trainable-W
stress grid and finite-`N_t` Creutz toy identity check, all with figures and
source/artifact hashes. Their TODOs
remain until the open scientific reference, effect/tolerance, confirmation
family, dependence/anchor bounds and data/compute authorization gates are
resolved. CPU tests establish software/algebra behavior only, not GPU/MPI
physics validation.
