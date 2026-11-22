"""Prepare and run a source-aligned replay of the amendment02 synthetic MC.

The replay uses the same seeds as amendment02 to audit source identity and
deterministic reproduction. It is not an independent Monte Carlo sample and
must not be pooled with the prior run.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .full_gate_executor import SCENARIOS


TASK_DIR = Path(__file__).resolve().parent
OLD_PLAN = Path("results/pion_projection/full_gate_mc_20261119_v2_amendment_02")
DEFAULT_PLAN = Path("results/pion_projection/full_gate_mc_20261119_v2_amendment_03")
DEFAULT_DEST = Path("results/pion_projection/full_gate_amendment03_execution_01")
SOURCE_FILES = (
    "common.py",
    "experiment.py",
    "full_gate_executor.py",
    "full_gate_mc.py",
    "full_gate_parallel_driver.py",
    "identity.py",
    "joint.py",
    "reference.py",
    "scoring.py",
    "source_aligned_mc.py",
    "statistics.py",
    "synthetic_adapter.py",
    "synthetic_worlds.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_manifest() -> dict[str, str]:
    return {name: sha256(TASK_DIR / name) for name in SOURCE_FILES}


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def prepare(plan_dir: Path) -> dict:
    plan_dir = plan_dir.resolve()
    if plan_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing plan: {plan_dir}")
    old_plan_dir = Path(OLD_PLAN)
    old_plan = json.loads((old_plan_dir / "preregistration.json").read_text())
    old_executor = json.loads((old_plan_dir / "executor_spec.json").read_text())
    hashes = source_manifest()

    preregistration = json.loads(json.dumps(old_plan))
    preregistration.update({
        "schema": "full-gate-candidate-mc-v2-amendment-03-source-aligned-replay",
        "status": "READY_FOR_SOURCE_ALIGNED_REPLAY",
        "code_sha256": hashes,
        "parent_plan": str(old_plan_dir / "preregistration.json"),
        "parent_plan_sha256": sha256(old_plan_dir / "preregistration.json"),
        "run_reason": (
            "Source-aligned reproducibility replay after amendment02 exposed a mismatch "
            "between the high-level preregistration adapter hash and the executor/receipt "
            "hash. Preserve the amendment02 seed and all design settings to replay the same "
            "synthetic worlds; this is a provenance audit, not an independent MC sample."
        ),
        "precision_status": "NOT_RUN; same-seed source-aligned replay",
        "required_outputs": [
            "launch_validation.json",
            "dataset_results.json",
            "aggregate.json",
            "candidate_rates_progress.png",
            "candidate_rates_diagnostic.png",
            "README.md",
            "ANALYSIS.md",
            "RUN_REVIEW.md",
        ],
        "amendment": (
            "Create one canonical code hash manifest shared by preregistration and executor; "
            "replay amendment02's same seeds and frozen design without pooling results."
        ),
    })

    executor = json.loads(json.dumps(old_executor))
    executor.update({
        "schema": "mc-executor-v2-amendment-03-source-aligned-replay",
        "code_hashes": hashes,
        "parent_plan": str(plan_dir / "preregistration.json"),
        "replay_relationship": (
            "same seed and synthetic worlds as amendment02; reproducibility/source audit only, "
            "not independent data and not poolable"
        ),
    })

    plan_dir.mkdir(parents=True, exist_ok=False)
    atomic_json(plan_dir / "preregistration.json", preregistration)
    atomic_json(plan_dir / "executor_spec.json", executor)
    atomic_json(plan_dir / "source_manifest.json", {
        "hashes": hashes,
        "purpose": "canonical manifest shared verbatim by preregistration and executor",
    })
    readme = f"""# Amendment03 source-aligned replay

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
"""
    (plan_dir / "README.md").write_text(readme)
    return {
        "plan_dir": str(plan_dir),
        "source_count": len(hashes),
        "manifest_sha256": sha256(plan_dir / "source_manifest.json"),
        "preregistration_sha256": sha256(plan_dir / "preregistration.json"),
        "executor_spec_sha256": sha256(plan_dir / "executor_spec.json"),
        "same_seed_as_amendment02": preregistration["seed"] == old_plan["seed"],
        "n_per_cell": executor["n_per_cell"],
        "scenarios": len(executor["scenarios"]),
    }


def validate(plan_dir: Path) -> dict:
    plan_dir = plan_dir.resolve()
    preregistration = json.loads((plan_dir / "preregistration.json").read_text())
    executor = json.loads((plan_dir / "executor_spec.json").read_text())
    frozen_manifest = json.loads((plan_dir / "source_manifest.json").read_text())["hashes"]
    if preregistration.get("code_sha256") != executor.get("code_hashes"):
        raise RuntimeError("preregistration and executor source manifests differ")
    if frozen_manifest != executor.get("code_hashes"):
        raise RuntimeError("canonical source_manifest differs from frozen plan files")
    current = source_manifest()
    if current != frozen_manifest:
        mismatches = sorted(
            name for name in frozen_manifest
            if current.get(name) != frozen_manifest[name]
        )
        raise RuntimeError(f"source hashes changed after preparation: {mismatches}")
    if executor.get("scenarios") != list(SCENARIOS):
        raise RuntimeError("executor scenario list differs from implementation")
    if preregistration.get("scenarios") != executor.get("scenarios"):
        raise RuntimeError("preregistration and executor scenario lists differ")
    if executor.get("n_per_cell") != preregistration["mc_target"]["n_independent_datasets_per_cell"]:
        raise RuntimeError("executor and preregistration sample sizes differ")
    if executor.get("seed") != preregistration.get("seed"):
        raise RuntimeError("preregistration and executor seeds differ")
    if executor.get("budgets") != [
        preregistration["bootstrap"]["reference"],
        preregistration["bootstrap"]["outer"],
        preregistration["bootstrap"]["inner"],
    ]:
        raise RuntimeError("preregistration and executor bootstrap budgets differ")
    if preregistration.get("score_alpha") != 0.05 or preregistration.get("kernel_alpha") != 0.2:
        raise RuntimeError("frozen score/kernel alpha separation is invalid")
    return {
        "schema": "source-aligned-replay-launch-validation-v1",
        "validated_utc": datetime.now(timezone.utc).isoformat(),
        "source_manifest_sha256": sha256(plan_dir / "source_manifest.json"),
        "preregistration_sha256": sha256(plan_dir / "preregistration.json"),
        "executor_spec_sha256": sha256(plan_dir / "executor_spec.json"),
        "source_count": len(current),
        "source_hashes_match": True,
        "plan_consistency": True,
        "same_seed_as_amendment02": True,
        "independent_mc_sample": False,
    }


def execute(plan_dir: Path, dest: Path, workers: int, max_per_cell: int | None) -> None:
    validation = validate(plan_dir)
    dest = dest.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    launch_validation = dest / "launch_validation.json"
    if launch_validation.exists():
        prior = json.loads(launch_validation.read_text())
        if any(prior.get(key) != validation.get(key) for key in (
            "source_manifest_sha256", "preregistration_sha256", "executor_spec_sha256",
        )):
            raise RuntimeError("existing launch validation belongs to a different plan")
    else:
        atomic_json(launch_validation, validation)

    from .full_gate_parallel_driver import main as driver_main

    driver_main(plan_dir, dest, workers=workers, max_per_cell=max_per_cell)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--plan-dir", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--max-per-cell", type=int)
    args = parser.parse_args()
    if args.prepare:
        print(json.dumps(prepare(args.plan_dir), indent=2))
    else:
        execute(args.plan_dir, args.dest, args.workers, args.max_per_cell)


if __name__ == "__main__":
    main()
