# Optimize `train.main` under the worker supervisor: CPU integration

**Status:** `diagnostic_only`; `physical_score=null`. This is a small synthetic software-path diagnostic, not a learned-smear benchmark, physical result, or GPU hard-timeout proof.

## Text flow

```text
synthetic protocol and cache identities
  -> Optimize RunSpec builder binds protocol, inputs, sources, split IDs, outputs
  -> worker rechecks hashes and starts a separate process group
  -> CPU harness imports the actual tasks.optimize_gaussian.train module
  -> only collect/evaluate, risk_of, and coefficient_map are replaced by fixed synthetic functions
  -> actual train.main verifies protocol hash, creates the output, saves a basis,
     runs SciPy Powell through the solver contract, and writes results/manifest/data
  -> parent verifies the declared artifact hashes after the child exits
```

The synthetic fixture contains one configuration per split. The real SciPy Powell optimizer, `train.optimize`, `train.main`, RunSpec builder, and worker supervisor execute. GPU initialization is replaced with an explicit failure function and was not called. The protocol's residual and timeout policy values exist only to exercise this fixture; they are not proposed production thresholds.

## Observed result

- Worker status: `completed`; artifact status: `verified`; declared training artifacts: 4.
- Synthetic cache/input identity checks marked 3/3 fixture configurations `verified`.
- Powell returned `success=True` after 32 counted objective calls; the box KKT diagnostic status is `computed` with scaled residual `2.8622902867294357e-19`. These use the synthetic objective and the fixture-only policy.
- The real solver trace and best-so-far objective are plotted in `objective_trace.png`; all values belong to the synthetic risk function.
- The worker receipt records SHA-256 for the run outputs. Protocol SHA-256: `9d02aeb4d2074c329a819aa80556b247b9f81de7b7fc2455b6f7a900d8529214`; RunSpec SHA-256: `a8870834017aea3c926599e62e04cdddeb8315266becdfbef53968408d6db77a`.

![Synthetic Powell objective trace](objective_trace.png)

## Limits

No archived gauge or propagator data, physical reference, blind split, CuPy, MPI, CUDA, or QUDA was loaded. The harness does not verify measurement kernels, real source/propagator integration, GPU cleanup, or whether learned $W$ outperforms Gaussian, SLSQP, or a strong spectral baseline. The one-point synthetic split cannot support statistical inference. Production thresholds, reference status, paired estimand, budget accounting, and authorization remain open.

## Reproduction

From the repository root, run `PYTHONDONTWRITEBYTECODE=1 python3 -B -m tasks.optimize_gaussian.train_main_supervisor_diagnostic`. The default output is no-clobber; supply `--output PATH` for a new result directory.
