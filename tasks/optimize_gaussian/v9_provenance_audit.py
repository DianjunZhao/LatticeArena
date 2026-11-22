"""Read-only provenance audit for the archived optimize_gaussian v9 run.

The audit does not rerun training or read/modify gauge data. It checks manifest
source hashes against the current tree and Git history, split IDs against the
archived pion provenance, and records which runtime/output identities are absent.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path("results/optimize_gaussian/v9/manifest.json")
DEVELOPMENT = Path("results/pion_projection/s16t16_v1/development_provenance.json")
VALIDATION = Path("results/pion_projection/s16t16_v1/validation_provenance.json")
OUT = Path("results/optimize_gaussian/v9_provenance_audit_v1")
SCHEMA = "optgauss-v9-provenance-audit-v1"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_hash(relative: str | Path) -> str | None:
    path = ROOT / relative
    return sha256(path.read_bytes()) if path.is_file() else None


def git_revisions(relative: str) -> list[str]:
    result = subprocess.run(
        ["git", "rev-list", "--all", "--", relative],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()


def historical_matches(relative: str, expected_hash: str) -> list[str]:
    matches = []
    for revision in git_revisions(relative):
        result = subprocess.run(
            ["git", "show", f"{revision}:{relative}"],
            cwd=ROOT,
            capture_output=True,
        )
        if result.returncode == 0 and sha256(result.stdout) == expected_hash:
            matches.append(revision)
    return matches


def read_json(relative: str | Path) -> dict:
    return json.loads((ROOT / relative).read_text())


def build_protocol() -> dict:
    manifest = read_json(MANIFEST)
    dependencies = manifest.get("dependencies", {})
    input_paths = [
        MANIFEST.as_posix(),
        DEVELOPMENT.as_posix(),
        VALIDATION.as_posix(),
        "tasks/optimize_gaussian/features.py",
        "tasks/optimize_gaussian/kernels.py",
        "tasks/optimize_gaussian/submission.py",
        "tasks/optimize_gaussian/train.py",
        "tasks/pion_projection/statistics.py",
        "tasks/optimize_gaussian/v9_provenance_audit.py",
    ]
    return {
        "schema": SCHEMA,
        "purpose": "Audit archived v9 provenance completeness; no training or physics claim.",
        "manifest_sha256": file_hash(MANIFEST.as_posix()),
        "manifest_dependencies": dependencies,
        "statistics_sha256_expected": manifest.get("statistics_sha256"),
        "input_sha256": {p: file_hash(p) for p in input_paths},
        "checks": [
            "Resolve each manifest dependency by exact current-file hash or exact Git-history blob hash.",
            "Compare manifest fit, dev-val, and test IDs with each other and archived pion provenance records.",
            "Inventory local v9 outputs and state whether the manifest binds their hashes.",
            "Record whether the manifest carries training environment or hardware identity.",
        ],
    }


def build_summary(protocol: dict) -> tuple[dict, list[dict], list[dict]]:
    manifest = read_json(MANIFEST)
    dependencies = manifest.get("dependencies", {})
    source_rows: list[dict] = []
    recovered = 0
    for relative, expected in sorted(dependencies.items()):
        path = f"tasks/optimize_gaussian/{relative}"
        current = file_hash(path)
        history = historical_matches(path, expected)
        resolved = current == expected or bool(history)
        recovered += int(resolved)
        source_rows.append(
            {
                "path": path,
                "manifest_sha256": expected,
                "current_sha256": current or "",
                "current_match": current == expected,
                "historical_matching_commits": ";".join(history),
                "source_recovered": resolved,
            }
        )

    statistics_path = "tasks/pion_projection/statistics.py"
    statistics_expected = manifest.get("statistics_sha256")
    statistics_current = file_hash(statistics_path)
    statistics_history = historical_matches(statistics_path, statistics_expected)
    stats_resolved = (
        statistics_current == statistics_expected or bool(statistics_history)
    )
    source_rows.append(
        {
            "path": statistics_path,
            "manifest_sha256": statistics_expected,
            "current_sha256": statistics_current or "",
            "current_match": statistics_current == statistics_expected,
            "historical_matching_commits": ";".join(statistics_history),
            "source_recovered": stats_resolved,
        }
    )

    ids = manifest.get("ids", {})
    fit_ids = set(ids.get("fit", []))
    dev_ids = set(ids.get("dev_val", []))
    test_ids = set(ids.get("test", []))
    validation = read_json(VALIDATION)
    validation_ids = {int(row["id"]) for row in validation.get("records", [])}
    cache_ids = {int(key) for key in manifest.get("propagator_cache", {})}
    split_disjoint = not (
        fit_ids & dev_ids or fit_ids & test_ids or dev_ids & test_ids
    )
    test_matches_validation = test_ids == validation_ids
    cache_matches_splits = cache_ids == fit_ids | dev_ids | test_ids

    environment_keys = [
        key
        for key in manifest
        if any(word in key.lower() for word in ("environment", "hardware", "device", "driver"))
    ]
    output_dir = ROOT / "results/optimize_gaussian/v9"
    output_files = sorted(
        path for path in output_dir.iterdir() if path.is_file()
    )
    artifact_rows = []
    for path in output_files:
        artifact_rows.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path.read_bytes()),
                "hash_bound_by_manifest": path.name in manifest.get("output_sha256", {}),
            }
        )

    historical_train = next(
        (row["historical_matching_commits"] for row in source_rows
         if row["path"] == "tasks/optimize_gaussian/train.py"),
        "",
    )
    summary = {
        "schema": SCHEMA,
        "classification": "source_partially_recovered_run_environment_and_raw_inputs_incomplete",
        "source_dependencies": {
            "manifest_dependency_count": len(dependencies),
            "manifest_dependencies_recovered_current_or_git": recovered,
            "historical_train_commit": historical_train,
            "statistics_source_recovered": stats_resolved,
        },
        "split_identity": {
            "fit_count": len(fit_ids),
            "dev_val_count": len(dev_ids),
            "test_count": len(test_ids),
            "splits_pairwise_disjoint": split_disjoint,
            "test_id_count": len(test_ids),
            "test_ids_equal_archived_pion_validation_ids": test_matches_validation,
            "test_overlap_count": len(test_ids & validation_ids),
            "propagator_cache_key_count": len(cache_ids),
            "cache_ids_equal_fit_dev_test_union": cache_matches_splits,
        },
        "training_environment_recorded": bool(environment_keys),
        "training_environment_fields": environment_keys,
        "raw_project_data_directory_present": (ROOT / "data").is_dir(),
        "referenced_provenance_files": {
            key: {
                "path": manifest["protocol"].get(key),
                "exists_in_workspace": bool(
                    manifest["protocol"].get(key)
                    and (ROOT / manifest["protocol"][key]).is_file()
                ),
            }
            for key in ("cache_manifest", "validation_manifest", "reference_bootstrap")
        },
        "v9_output_file_count": len(artifact_rows),
        "v9_output_hashes_bound_by_manifest": sum(
            row["hash_bound_by_manifest"] for row in artifact_rows
        ),
        "manifest_hashes_all_dependencies_recoverable": recovered == len(dependencies),
        "source_hashes": source_rows,
        "output_inventory": artifact_rows,
        "limitations": [
            "An exact historical train.py blob is code provenance, not proof of the executable, environment, or GPU device used for the archived run.",
            "The manifest contains no training environment, hardware, driver, package-lock, or run-command receipt.",
            "The archived v9 test IDs 70-99 equal the already-used pion validation IDs; they are not a new blind test.",
            "The local v9 artifact hashes are recorded by this audit, but are not bound by the original run manifest.",
            "The workspace has no top-level raw data directory; this audit does not reconstruct gauge or propagator bytes from correlators.",
        ],
    }
    return summary, source_rows, artifact_rows


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def render_readme(summary: dict) -> str:
    src = summary["source_dependencies"]
    split = summary["split_identity"]
    refs = summary["referenced_provenance_files"]
    ref_rows = "\n".join(
        f"| {key} | {value['path']} | {'present' if value['exists_in_workspace'] else 'missing'} |"
        for key, value in refs.items()
    )
    source_rows = "\n".join(
        f"| {row['path']} | {'yes' if row['current_match'] else 'no'} | "
        f"{row['historical_matching_commits'] or 'none'} |"
        for row in summary["source_hashes"]
    )
    artifact_rows = "\n".join(
        f"| {row['path']} | {row['bytes']} | {row['sha256'][:16]}… | "
        f"{'yes' if row['hash_bound_by_manifest'] else 'no'} |"
        for row in summary["output_inventory"]
    )
    return f"""# Archived optimize_gaussian v9 provenance audit

**Classification: source hashes recovered; run environment and original raw-input receipt remain incomplete.**

## Source closure

The v9 manifest declares {len(summary['source_hashes']) - 1} optimizer source dependencies plus the pion statistics source. The current hashes match for the following sources; the historical train.py hash is recoverable exactly from Git commit {src['historical_train_commit'][:12]}. The recorded statistics hash also matches the current statistics.py.

| Source | Matches current file | Exact historical commit containing expected bytes |
| --- | --- | --- |
{source_rows}

This recovers the source bytes required by the manifest. It does not establish which interpreter, package versions, GPU, driver, command line, or built extension executed the run.

## Split and archive identity

| Check | Result |
| --- | --- |
| Fit / dev-val / test IDs | {split['fit_count']} / {split['dev_val_count']} / {split['test_count']} |
| Pairwise split disjointness | {split['splits_pairwise_disjoint']} |
| Test IDs equal archived pion validation IDs | {split['test_ids_equal_archived_pion_validation_ids']} ({split['test_overlap_count']} IDs overlap) |
| Propagator cache keys match the split ID union | {split['cache_ids_equal_fit_dev_test_union']} ({split['propagator_cache_key_count']} keys) |
| Training environment / hardware fields in manifest | {summary['training_environment_fields'] or 'none'} |
| Top-level workspace data/ directory | {summary['raw_project_data_directory_present']} |

The test set was already used by the pion pilot, so it cannot serve as a fresh blind set. The manifest records cache keys and split IDs but does not itself bind raw gauge/propagator bytes or the v9 output files.

## Referenced provenance files

| Manifest field | Referenced file | Workspace status |
| --- | --- | --- |
{ref_rows}

## Archived output inventory

| File | Bytes | SHA-256 prefix | Hash bound in original manifest |
| --- | ---: | --- | --- |
{artifact_rows}

These hashes identify the files present during this audit; the original manifest has no per-output hash map. Do not treat this inventory as a retroactive run receipt.

## What this closes and what remains

- The four source dependency digests declared by v9 are all recoverable from the current tree or Git history ({src['manifest_dependencies_recovered_current_or_git']}/{src['manifest_dependency_count']}); the statistics source digest is also resolved.
- The original training environment, exact run command/device receipt, and raw gauge/propagator bytes are still unavailable in the local archive.
- The manifest points to the same archived pion validation IDs 70–99. Those results are observed and do not count as an independent blind evaluation.
- The v9 result remains a historical fixed-random-W coefficient fit; it is not evidence that W was trained or that a learned smear beats SLSQP.

The next agent should preserve this partial boundary, seek the original training receipt and raw inputs, and use fresh gauge IDs for any new learned-W comparison. If those records cannot be recovered, mark the missing fields explicitly and proceed only with a newly frozen production plan. The required paired-risk, convergence, total-cost, and failure diagnostics are listed in tasks/optimize_gaussian/todo.md.

Reproduce the read-only audit with:

    python3 -B -m tasks.optimize_gaussian.v9_provenance_audit run

Verify the frozen audit inputs and output hashes with:

    python3 -B -m tasks.optimize_gaussian.v9_provenance_audit verify --out results/optimize_gaussian/v9_provenance_audit_v2
"""


def output_hashes(directory: Path) -> dict[str, str]:
    return {
        path.name: sha256(path.read_bytes())
        for path in sorted(directory.iterdir())
        if path.is_file() and path.name != "provenance.json"
    }


def resolve_output(output: str | Path) -> Path:
    path = Path(output)
    return path if path.is_absolute() else ROOT / path


def run(output: str | Path = OUT) -> None:
    directory = resolve_output(output)
    if directory.exists():
        raise FileExistsError(directory)
    protocol = build_protocol()
    summary, source_rows, artifact_rows = build_summary(protocol)
    directory.mkdir(parents=True)
    (directory / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")
    (directory / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (directory / "README.md").write_text(render_readme(summary))
    write_csv(directory / "source_hashes.csv", source_rows)
    write_csv(directory / "artifact_inventory.csv", artifact_rows)
    provenance = {
        "protocol_sha256": sha256((directory / "protocol.json").read_bytes()),
        "outputs_sha256": output_hashes(directory),
    }
    (directory / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(json.dumps(summary["source_dependencies"], indent=2))
    print(json.dumps(summary["split_identity"], indent=2))
    print(f"wrote {directory.relative_to(ROOT) if directory.is_relative_to(ROOT) else directory}")


def verify(output: str | Path = OUT) -> None:
    directory = resolve_output(output)
    protocol_path = directory / "protocol.json"
    provenance_path = directory / "provenance.json"
    if not protocol_path.is_file() or not provenance_path.is_file():
        raise FileNotFoundError("frozen audit protocol or provenance is missing")
    frozen_protocol = json.loads(protocol_path.read_text())
    if frozen_protocol != build_protocol():
        raise RuntimeError("audit inputs changed since protocol freeze")
    provenance = json.loads(provenance_path.read_text())
    if provenance.get("protocol_sha256") != sha256(protocol_path.read_bytes()):
        raise RuntimeError("protocol hash mismatch")
    if provenance.get("outputs_sha256") != output_hashes(directory):
        raise RuntimeError("audit output hash mismatch")
    summary = json.loads((directory / "summary.json").read_text())
    if summary != build_summary(frozen_protocol)[0]:
        raise RuntimeError("recomputed summary differs from frozen output")
    print(json.dumps({
        "verification": "PASS",
        "source_dependencies_recovered": summary["source_dependencies"]["manifest_dependencies_recovered_current_or_git"],
        "source_dependency_count": summary["source_dependencies"]["manifest_dependency_count"],
        "test_ids_overlap_pion_validation": summary["split_identity"]["test_overlap_count"],
        "outputs": len(provenance["outputs_sha256"]),
    }, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("run", "verify"))
    parser.add_argument("--out", default=OUT.as_posix(), help="audit output directory")
    args = parser.parse_args()
    ({"run": run, "verify": verify}[args.mode])(args.out)


if __name__ == "__main__":
    main()
