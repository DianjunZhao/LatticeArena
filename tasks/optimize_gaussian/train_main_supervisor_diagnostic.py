"""Run a synthetic CPU integration smoke through the real Optimize entry point.

This harness replaces only gauge/propagator collection and the risk observable.
It retains the real SciPy Powell optimizer, solver contract, train.main control
flow, RunSpec builder, subprocess supervisor, and parent artifact hashing.
Nothing in the output is a physics score or a learned-smear comparison.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import uuid

import numpy as np

from tasks.optimize_gaussian.runspec_builder import (
    build_optimize_runspec,
    write_optimize_runspec,
)
from tasks.optimize_gaussian.worker_runspec import run_frozen_worker
from tasks.pion_projection.common import digest


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "results/optimize_gaussian/cpu_train_main_supervisor_v2"


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")


def _worker_harness_source() -> str:
    return '''"""Synthetic response shim for train.main; never initializes QUDA."""
import sys
import numpy as np
from tasks.optimize_gaussian import train

def collect(protocol, ids, cache, W, steps):
    times = np.arange(16, dtype=float)
    base = 0.25 + 0.035 * np.cos(2 * np.pi * times / 16)
    offset = 0.040 * np.cos(2 * np.pi * times / 16)
    feature = 0.055 * np.cos(4 * np.pi * times / 16)
    data = np.empty((len(ids), 2 + protocol["hidden"], 16), dtype=float)
    for row, cfg_id in enumerate(ids):
        data[row, 0] = base + int(cfg_id) * 0.001
        data[row, 1] = offset
        data[row, 2] = feature
    return data

target = 0.25 + 0.020 * np.cos(2 * np.pi * np.arange(16) / 16)
def risk_of(protocol, correlator_values, masses):
    values = np.asarray(correlator_values, dtype=float)
    return float(np.mean((values - target[None, :]) ** 2))

def evaluate(protocol, ids, cache, W, theta, steps):
    values = collect(protocol, ids, cache, W, steps)
    return train.correlators(values, theta, protocol["hidden"])

def forbid_gpu(*args, **kwargs):
    raise RuntimeError("GPU initialization is forbidden in this CPU fixture")

train.collect = collect
train.risk_of = risk_of
train.evaluate = evaluate
train.init_quda = forbid_gpu
train.coefficient_map = lambda protocol, cfg, cache, W, theta, t=0: np.full(
    (3, 4, 4, 4), float(np.asarray(theta)[0]), dtype=float)
train.main(sys.argv[1:])
'''


def _make_fixture(output: Path):
    fixture = output / "fixture_inputs"
    ensemble = fixture / "ensemble"
    propagators = fixture / "propagators"
    inputs = fixture / "inputs"
    for directory in (ensemble, propagators, inputs):
        directory.mkdir(parents=True, exist_ok=False)

    cache_root = ROOT / ".cache/pion_projection/propagators"
    missing = []
    for candidate in (ROOT / ".cache", ROOT / ".cache/pion_projection", cache_root):
        if not candidate.exists():
            missing.append(candidate)
    cache_root.mkdir(parents=True, exist_ok=True)

    cache_keys = {}
    temporary_links = []
    for cfg_id in (0, 1, 2):
        key = f"cpu_train_main_{uuid.uuid4().hex}_{cfg_id}"
        gauge = ensemble / f"wilson_b6.{cfg_id}"
        gauge.write_text(f"synthetic gauge fixture {cfg_id}\n")
        gauge_hash = _sha256(gauge)

        prop = propagators / f"{key}.npy"
        np.save(prop, np.asarray([cfg_id + 1j, cfg_id + 2j], dtype=np.complex128))
        prop_hash = _sha256(prop)
        meta = propagators / f"{key}.json"
        _write_json(meta, {
            "array_sha256": prop_hash,
            "keydata": {
                "gauge": gauge_hash,
                "geometry": [4, 4, 4, 4],
                "boundary": -1,
                "tol": 1e-10,
                "maxiter": 100,
                "residual_max": 1e-12,
            },
        })

        for suffix, target in ((".npy", prop), (".json", meta)):
            link = cache_root / f"{key}{suffix}"
            if link.exists() or link.is_symlink():
                raise FileExistsError(f"refusing existing synthetic cache link: {link}")
            link.symlink_to(target.resolve())
            temporary_links.append(link)
        cache_keys[cfg_id] = key

    development_manifest = inputs / "development_manifest.json"
    validation_manifest = inputs / "validation_manifest.json"
    _write_json(development_manifest, {"records": [
        {"id": cfg_id, "cache_key": cache_keys[cfg_id]} for cfg_id in (0, 1)
    ]})
    _write_json(validation_manifest, {"records": [
        {"id": 2, "cache_key": cache_keys[2]}
    ]})
    masses_path = inputs / "reference_bootstrap.npz"
    np.savez_compressed(masses_path, masses=np.full(20, 0.35, dtype=float))

    protocol = {
        "version": "synthetic-train-main-supervisor-v1",
        "output": str(output / "training_output"),
        "ensemble": str(ensemble),
        "geometry": [4, 4, 4, 4],
        "t_boundary": -1,
        "tolerance": 1e-10,
        "max_iterations": 100,
        "fit": [0, 0],
        "dev_val": [1, 1],
        "test": [2, 2],
        "hidden": 1,
        "alpha": 0.0,
        "base_steps": 0,
        "base_alpha": 0.0,
        "seed": 20261121,
        "seeds": [20261121],
        "reference": {
            "m0": 0.35,
            "score_window": [2, 3, 4, 5],
            "amplitude_window": [6, 7, 8],
        },
        "risk": {
            "block_length": 1,
            "bootstrap_samples": 20,
            "covariance_shrinkage": 0.25,
            "amplitude_z_min": 3.0,
        },
        "l2_grid": [0.0],
        "v_max": 2.0,
        "optimizer": {
            "maxiter": 8,
            "solver_contract": {
                "objective_call_cap": 256,
                "walltime_cap_seconds": 30.0,
                "residual_field": "kkt_residual",
                "residual_tolerance": 10.0,
                "require_solver_success": False,
            },
        },
        "cache_manifest": str(development_manifest),
        "validation_manifest": str(validation_manifest),
        "reference_bootstrap": str(masses_path),
    }
    protocol_path = output / "protocol.json"
    _write_json(protocol_path, protocol)
    harness_path = output / "train_main_worker_harness.py"
    harness_path.write_text(_worker_harness_source())
    return protocol_path, harness_path, temporary_links, missing


def _write_trace_plot(output: Path, train_results: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    grid = train_results["grid"]
    if len(grid) != 1:
        raise ValueError("diagnostic expected exactly one frozen CPU fixture grid point")
    receipt = grid[0]["optimizer_receipt"]
    trace = receipt.get("objective_trace", [])
    finite = [row for row in trace if row.get("best_so_far") is not None]
    if not finite:
        raise ValueError("training receipt has no finite best-so-far observations")

    figure, axes = plt.subplots(1, 2, figsize=(10, 4.2), constrained_layout=True)
    axes[0].plot([row.get("call_index", row.get("index")) for row in finite],
                 [row["best_so_far"] for row in finite], marker="o", ms=3)
    axes[0].set_xlabel("Objective call")
    axes[0].set_ylabel("Synthetic best-so-far objective")
    axes[0].set_title("Actual Powell trace in train.main")
    axes[1].plot([row["elapsed_seconds"] for row in finite],
                 [row["best_so_far"] for row in finite], marker="o", ms=3)
    axes[1].set_xlabel("Elapsed seconds")
    axes[1].set_ylabel("Synthetic best-so-far objective")
    axes[1].set_title("CPU worker trajectory")
    for axis in axes:
        axis.grid(True, alpha=0.25)
    figure.suptitle("Synthetic CPU integration only; not a physics comparison")
    figure.savefig(output / "objective_trace.png", dpi=160)
    plt.close(figure)


def run(output: Path) -> dict:
    output = output.resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError(f"output must remain inside the repository: {output}")
    output.mkdir(parents=True, exist_ok=False)

    protocol_path, harness_path, links, missing_cache_dirs = _make_fixture(output)
    try:
        protocol_hash = _sha256(protocol_path)
        output_directory = output / "training_output"
        runspec = build_optimize_runspec(
            protocol_path,
            output_directory=output_directory,
            receipt_directory=output,
            run_id="synthetic-train-main-v1",
            timeout_seconds=60.0,
            terminate_grace_seconds=2.0,
            environment={
                "PYTHONPATH": str(ROOT),
                "OPENBLAS_NUM_THREADS": "1",
                "OMP_NUM_THREADS": "1",
                "MKL_NUM_THREADS": "1",
            },
            repo_root=ROOT,
            extra_input_files={"cpu_train_main_harness": harness_path},
        )
        runspec["command"] = [
            sys.executable, "-B", str(harness_path), str(output_directory),
            "--protocol", str(protocol_path), "--protocol-sha256", protocol_hash,
        ]
        runspec_path = output / "worker.runspec.json"
        write_optimize_runspec(runspec_path, runspec)

        worker_receipt = run_frozen_worker(runspec_path)
        receipt_path = output / "synthetic-train-main-v1.receipt.json"
        if not receipt_path.is_file():
            raise RuntimeError("supervisor returned without its declared receipt")
        saved_receipt = json.loads(receipt_path.read_text())
        training_results_path = output_directory / "results.json"
        if not training_results_path.is_file():
            raise RuntimeError("supervised train.main did not write results.json")
        train_results = json.loads(training_results_path.read_text())
        _write_trace_plot(output, train_results)

        optimizer = train_results["grid"][0]["optimizer_receipt"]
        contract = optimizer.get("solver_contract", {})
        manifest = json.loads((output_directory / "manifest.json").read_text())
        verified_input_count = sum(
            row.get("status") == "verified"
            for row in manifest.get("inputs", {}).get("detail", {}).values()
        )
        summary = {
            "status": "diagnostic_only",
            "physical_score": None,
            "evidence_class": "synthetic_cpu_integration",
            "worker_status": worker_receipt.get("status"),
            "artifact_output_status": worker_receipt.get("artifact_output_status"),
            "artifact_output_count": len(saved_receipt.get("artifact_outputs", {})),
            "verified_synthetic_input_count": verified_input_count,
            "protocol_sha256": protocol_hash,
            "runspec_sha256": _sha256(runspec_path),
            "harness_sha256": _sha256(harness_path),
            "optimizer": {
                "method": optimizer.get("method"),
                "solver_success": optimizer.get("success"),
                "solver_message": optimizer.get("message"),
                "objective_calls": contract.get("objective_calls"),
                "best_objective": contract.get("best_so_far"),
                "stop_reason": contract.get("stop_reason"),
                "residual_status": ((contract.get("residual_diagnostic") or {})
                                    .get("box_kkt_diagnostic") or {}).get("status"),
                "residual_value": contract.get("residual"),
            },
            "synthetic_split_ids": {"fit": [0], "dev_val": [1], "test": [2]},
            "artifacts": {
                str(path.relative_to(output)): _sha256(path)
                for path in sorted(output_directory.rglob("*")) if path.is_file()
            },
            "temporary_cache_links_removed": len(links),
            "cuda_or_quda_initialized": False,
        }
        _write_json(output / "summary.json", summary)
        readme = f"""# Optimize `train.main` under the worker supervisor: CPU integration

**Status:** `{summary['status']}`; `physical_score=null`. This is a small synthetic software-path diagnostic, not a learned-smear benchmark, physical result, or GPU hard-timeout proof.

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

- Worker status: `{summary['worker_status']}`; artifact status: `{summary['artifact_output_status']}`; declared training artifacts: {summary['artifact_output_count']}.
- Synthetic cache/input identity checks marked {verified_input_count}/3 fixture configurations `verified`.
- Powell returned `success={optimizer.get('success')}` after {optimizer.get('objective_calls')} counted objective calls; the box KKT diagnostic status is `{summary['optimizer']['residual_status']}` with scaled residual `{summary['optimizer']['residual_value']}`. These use the synthetic objective and the fixture-only policy.
- The real solver trace and best-so-far objective are plotted in `objective_trace.png`; all values belong to the synthetic risk function.
- The worker receipt records SHA-256 for the run outputs. Protocol SHA-256: `{protocol_hash}`; RunSpec SHA-256: `{summary['runspec_sha256']}`.

![Synthetic Powell objective trace](objective_trace.png)

## Limits

No archived gauge or propagator data, physical reference, blind split, CuPy, MPI, CUDA, or QUDA was loaded. The harness does not verify measurement kernels, real source/propagator integration, GPU cleanup, or whether learned $W$ outperforms Gaussian, SLSQP, or a strong spectral baseline. The one-point synthetic split cannot support statistical inference. Production thresholds, reference status, paired estimand, budget accounting, and authorization remain open.

## Reproduction

From the repository root, run `PYTHONDONTWRITEBYTECODE=1 python3 -B -m tasks.optimize_gaussian.train_main_supervisor_diagnostic`. The default output is no-clobber; supply `--output PATH` for a new result directory.
"""
        (output / "README.md").write_text(readme)
        return summary
    finally:
        for link in links:
            link.unlink(missing_ok=True)
        for directory in reversed(missing_cache_dirs):
            try:
                directory.rmdir()
            except OSError:
                pass


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    summary = run(args.output)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if (summary["worker_status"] == "completed"
                 and summary["artifact_output_status"] == "verified") else 1


if __name__ == "__main__":
    raise SystemExit(main())
