"""Read-only crosswalk between the Wilson HMC snapshot and Pion GEVP200 receipts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "results/wilson_loop/hmc_quality_v1/manifest_snapshot.json"
PRIMARY = ROOT / "results/kunshan_logs/manifest.json"
PION_ROOT = ROOT / "results/pion_projection/s16t16_gevp200"
PION_V1_ROOT = ROOT / "results/pion_projection/s16t16_v1"
OUTPUT = ROOT / "results/kunshan_logs/pion_gevp200_snapshot_crosswalk_v1"
MEASURE_SHA256 = "6c41481e21640e88742054abdeda83843601bcfa8e97412f58b4e940665b03d4"
KERNEL_SHA256 = "f0e67f42d5418920e4f214286d67be13199f32a12ce2b714a41f00f41b6278a8"
RESIDUAL_TOLERANCE = 1e-10
PLAQUETTE_ATOL = 1e-12

INPUTS = [
    SNAPSHOT,
    PRIMARY,
    PION_ROOT / "development_provenance.json",
    PION_ROOT / "validation_provenance.json",
    PION_ROOT / "development.npz",
    PION_ROOT / "validation.npz",
    PION_ROOT / "validation_results.json",
    PION_V1_ROOT / "development_provenance.json",
    PION_V1_ROOT / "validation_provenance.json",
    ROOT / "tasks/pion_projection/measure.py",
    ROOT / "tasks/pion_projection/kernels.py",
]

CSV_COLUMNS = [
    "id",
    "snapshot_present",
    "pion_gevp200_development",
    "pion_gevp200_validation",
    "pion_gevp200_gauge_sha256",
    "snapshot_sha256",
    "gevp200_hash_matches_snapshot",
    "gevp200_plaquette_matches_snapshot",
    "primary_manifest_sha256",
    "gevp200_hash_matches_primary",
    "gevp200_plaquette_matches_primary",
    "pilot_v1_present",
    "pilot_v1_gauge_sha256",
    "gevp200_hash_matches_pilot_v1",
    "residual_max",
    "residual_within_tolerance",
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _git(args: list[str], input_bytes: bytes | None = None) -> bytes:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout


def find_git_blob_by_sha256(target: str) -> dict:
    """Find exact file bytes by content SHA-256 across all local Git blob objects."""
    metadata = _git(
        ["cat-file", "--batch-all-objects", "--batch-check=%(objectname) %(objecttype) %(objectsize)"]
    ).decode()
    blobs = [
        parts[0]
        for line in metadata.splitlines()
        if len(parts := line.split()) == 3 and parts[1] == "blob"
    ]
    matches: list[tuple[str, int]] = []
    for offset in range(0, len(blobs), 128):
        chunk = blobs[offset : offset + 128]
        payload = _git(["cat-file", "--batch"], ("\n".join(chunk) + "\n").encode())
        cursor = 0
        while cursor < len(payload):
            header_end = payload.index(b"\n", cursor)
            oid, object_type, size_text = payload[cursor:header_end].decode().split()
            cursor = header_end + 1
            size = int(size_text)
            body = payload[cursor : cursor + size]
            cursor += size + 1
            if object_type == "blob" and sha256_bytes(body) == target:
                matches.append((oid, size))

    reachable_lines = _git(["rev-list", "--objects", "--all"]).decode().splitlines()
    paths_by_oid: dict[str, list[str]] = {}
    for line in reachable_lines:
        parts = line.split(" ", 1)
        if len(parts) == 2:
            paths_by_oid.setdefault(parts[0], []).append(parts[1])

    entries = []
    for oid, size in matches:
        commits = _git(["log", "--all", f"--find-object={oid}", "--format=%H"]).decode().splitlines()
        entries.append(
            {
                "git_blob_oid": oid,
                "size_bytes": size,
                "reachable_paths": sorted(set(paths_by_oid.get(oid, []))),
                "commits_containing_change": sorted(set(commits)),
            }
        )
    return {"target_sha256": target, "blob_objects_scanned": len(blobs), "matches": entries}


def is_close(a: object, b: object, atol: float = PLAQUETTE_ATOL) -> bool:
    try:
        return abs(float(a) - float(b)) <= atol
    except (TypeError, ValueError):
        return False


def _provenance_records(paths: list[Path]) -> tuple[dict[int, dict], dict]:
    records: dict[int, dict] = {}
    shared_protocol = None
    shared_software = None
    for path in paths:
        obj = read_json(path)
        protocol = obj["protocol"]
        software = obj["software"]
        if shared_protocol is None:
            shared_protocol = protocol
            shared_software = software
        elif protocol != shared_protocol or software != shared_software:
            raise SystemExit(f"development/validation provenance disagree: {path}")
        for row in obj["records"]:
            config_id = int(row["id"])
            if config_id in records:
                raise SystemExit(f"duplicate Pion GEVP200 record ID: {config_id}")
            records[config_id] = row
    return records, {"protocol": shared_protocol, "software": shared_software}


def collect() -> tuple[list[dict], dict]:
    snapshot = read_json(SNAPSHOT)
    primary = read_json(PRIMARY)
    snapshot_by_id = {int(row["id"]): row for row in snapshot["configs"]}
    primary_by_id = {int(row["id"]): row for row in primary["configs"]}
    p200_dev_path = PION_ROOT / "development_provenance.json"
    p200_val_path = PION_ROOT / "validation_provenance.json"
    p200_by_id, p200_run = _provenance_records([p200_dev_path, p200_val_path])
    pilot_by_id, _ = _provenance_records(
        [
            PION_V1_ROOT / "development_provenance.json",
            PION_V1_ROOT / "validation_provenance.json",
        ]
    )

    with np.load(PION_ROOT / "development.npz", allow_pickle=False) as data:
        dev_array_ids = [int(value) for value in data["ids"]]
    with np.load(PION_ROOT / "validation.npz", allow_pickle=False) as data:
        val_array_ids = [int(value) for value in data["ids"]]
    dev_ids = {int(row["id"]) for row in read_json(p200_dev_path)["records"]}
    val_ids = {int(row["id"]) for row in read_json(p200_val_path)["records"]}
    if set(dev_array_ids) != dev_ids or set(val_array_ids) != val_ids:
        raise SystemExit("Pion GEVP200 provenance IDs do not match saved NPZ ID arrays")
    if dev_ids & val_ids:
        raise SystemExit("Pion GEVP200 development and validation IDs overlap")

    protocol = p200_run["protocol"]
    declared_dev = set(range(int(protocol["development"][0]), int(protocol["development"][1]) + 1))
    declared_gap = set(range(int(protocol["gap"][0]), int(protocol["gap"][1]) + 1))
    declared_val = set(range(int(protocol["validation"][0]), int(protocol["validation"][1]) + 1))
    if dev_ids != declared_dev or val_ids != declared_val or declared_gap & (dev_ids | val_ids):
        raise SystemExit("Pion GEVP200 records do not match the frozen split ranges")

    all_ids = sorted(set(snapshot_by_id) | set(primary_by_id) | set(p200_by_id) | set(pilot_by_id))
    rows = []
    for config_id in all_ids:
        snap = snapshot_by_id.get(config_id, {})
        main = primary_by_id.get(config_id, {})
        p200 = p200_by_id.get(config_id, {})
        pilot = pilot_by_id.get(config_id, {})
        is_dev = config_id in dev_ids
        is_val = config_id in val_ids
        residual = p200.get("residual_max")
        rows.append(
            {
                "id": config_id,
                "snapshot_present": bool(snap),
                "pion_gevp200_development": is_dev,
                "pion_gevp200_validation": is_val,
                "pion_gevp200_gauge_sha256": p200.get("gauge_sha256", ""),
                "snapshot_sha256": snap.get("sha256", ""),
                "gevp200_hash_matches_snapshot": bool(
                    p200 and snap and p200.get("gauge_sha256") == snap.get("sha256")
                ),
                "gevp200_plaquette_matches_snapshot": bool(
                    p200 and snap and is_close(p200.get("plaquette"), snap.get("plaquette"))
                ),
                "primary_manifest_sha256": main.get("sha256", ""),
                "gevp200_hash_matches_primary": bool(
                    p200 and main and p200.get("gauge_sha256") == main.get("sha256")
                ),
                "gevp200_plaquette_matches_primary": bool(
                    p200 and main and is_close(p200.get("plaquette"), main.get("plaquette"))
                ),
                "pilot_v1_present": bool(pilot),
                "pilot_v1_gauge_sha256": pilot.get("gauge_sha256", ""),
                "gevp200_hash_matches_pilot_v1": bool(
                    p200 and pilot and p200.get("gauge_sha256") == pilot.get("gauge_sha256")
                ),
                "residual_max": "" if residual is None else float(residual),
                "residual_within_tolerance": bool(
                    p200 and residual is not None and float(residual) <= RESIDUAL_TOLERANCE
                ),
            }
        )

    p200_snapshot_rows = [row for row in rows if row["pion_gevp200_gauge_sha256"] and row["snapshot_sha256"]]
    p200_primary_rows = [row for row in rows if row["pion_gevp200_gauge_sha256"] and row["primary_manifest_sha256"]]
    p200_pilot_rows = [row for row in rows if row["pion_gevp200_gauge_sha256"] and row["pilot_v1_gauge_sha256"]]
    pilot_primary_rows = [
        row for row in rows if row["pilot_v1_gauge_sha256"] and row["primary_manifest_sha256"]
    ]
    snapshot_primary_rows = [
        row for row in rows if row["snapshot_sha256"] and row["primary_manifest_sha256"]
    ]

    dev_source_sha = p200_run["software"]["measurement_sha256"]
    kernel_source_sha = p200_run["software"]["kernel_sha256"]
    historical_measure = find_git_blob_by_sha256(dev_source_sha)
    kernel_source = {
        "recorded_sha256": kernel_source_sha,
        "current_path": "tasks/pion_projection/kernels.py",
        "current_sha256": sha256_file(ROOT / "tasks/pion_projection/kernels.py"),
        "current_matches": sha256_file(ROOT / "tasks/pion_projection/kernels.py") == kernel_source_sha,
        "git_blob_search": find_git_blob_by_sha256(kernel_source_sha),
    }
    current_measure_sha = sha256_file(ROOT / "tasks/pion_projection/measure.py")

    validation_result = read_json(PION_ROOT / "validation_results.json")
    residuals = [float(row["residual_max"]) for row in p200_by_id.values()]
    summary = {
        "classification": "partial_identity_crosswalk_not_raw_gauge_rehash",
        "snapshot": {
            "rows": len(snapshot_by_id),
            "id_range": [min(snapshot_by_id), max(snapshot_by_id)],
            "ensemble_label": snapshot.get("ensemble"),
            "lattice": snapshot.get("lattice"),
            "beta": snapshot.get("beta"),
            "n_steps": snapshot.get("n_steps"),
            "seed": snapshot.get("seed"),
        },
        "primary_manifest": {
            "rows": len(primary_by_id),
            "id_range": [min(primary_by_id), max(primary_by_id)],
        },
        "pion_gevp200": {
            "protocol_version": protocol.get("version"),
            "ensemble_path": protocol.get("ensemble"),
            "geometry": protocol.get("geometry"),
            "development_ids": [protocol["development"][0], protocol["development"][1]],
            "gap_ids": [protocol["gap"][0], protocol["gap"][1]],
            "validation_ids": [protocol["validation"][0], protocol["validation"][1]],
            "development_records": len(dev_ids),
            "validation_records": len(val_ids),
            "validation_arrays_match_provenance_ids": set(val_array_ids) == val_ids,
            "all_measured_hashes_unique": len({r["gauge_sha256"] for r in p200_by_id.values()}) == len(p200_by_id),
            "residual_max": max(residuals),
            "residuals_over_tolerance": sum(value > RESIDUAL_TOLERANCE for value in residuals),
            "validation_reference_passed": validation_result.get("reference_passed"),
            "validation_score_status": validation_result.get("score_status"),
            "validation_reference": validation_result.get("reference"),
        },
        "crosswalks": {
            "gevp200_to_snapshot": {
                "overlap": len(p200_snapshot_rows),
                "exact_hash_matches": sum(row["gevp200_hash_matches_snapshot"] for row in p200_snapshot_rows),
                "plaquette_matches": sum(row["gevp200_plaquette_matches_snapshot"] for row in p200_snapshot_rows),
            },
            "gevp200_to_primary_manifest": {
                "overlap": len(p200_primary_rows),
                "exact_hash_matches": sum(row["gevp200_hash_matches_primary"] for row in p200_primary_rows),
                "plaquette_matches": sum(row["gevp200_plaquette_matches_primary"] for row in p200_primary_rows),
            },
            "gevp200_to_pilot_v1_same_id": {
                "overlap": len(p200_pilot_rows),
                "exact_hash_matches": sum(row["gevp200_hash_matches_pilot_v1"] for row in p200_pilot_rows),
            },
            "pilot_v1_to_primary_manifest": {
                "overlap": len(pilot_primary_rows),
                "exact_hash_matches": sum(
                    row["pilot_v1_gauge_sha256"] == row["primary_manifest_sha256"] for row in pilot_primary_rows
                ),
            },
            "snapshot_to_primary_manifest_prefix": {
                "overlap": len(snapshot_primary_rows),
                "id_plaquette_metadata_matches": sum(
                    is_close(
                        next(x for x in snapshot["configs"] if int(x["id"]) == row["id"])["plaquette"],
                        next(x for x in primary["configs"] if int(x["id"]) == row["id"])["plaquette"],
                    )
                    for row in snapshot_primary_rows
                ),
                "exact_hash_matches": sum(
                    row["snapshot_sha256"] == row["primary_manifest_sha256"] for row in snapshot_primary_rows
                ),
            },
        },
        "source_identity": {
            "measurement": {
                "recorded_sha256": dev_source_sha,
                "current_path": "tasks/pion_projection/measure.py",
                "current_sha256": current_measure_sha,
                "current_matches": current_measure_sha == dev_source_sha,
                "historical_git_blob_search": historical_measure,
            },
            "kernel": kernel_source,
        },
        "limits": [
            "The 180/180 hash agreement verifies matching digest fields between two archived artifacts, not an independent rehash of gauge bytes.",
            "The Pion GEVP200 protocol records an ensemble path ending in S16T16C, while the snapshot label is LatticeArena-pilot; geometry, beta, step count, seed, IDs, plaquettes, and the matching measured hashes are consistent, but this does not establish the full HMC run identity.",
            "The Pion GEVP200 validation reference failed and its score_status is unscored_reference_failed; it is not a physical anchor or accepted score.",
            "The IDs 0-99 have matching metadata but different hash fields between the Pion GEVP200 receipt and the primary Kunshan manifest. The reason is unresolved without the original gauge bytes and hash-generation receipt.",
            "Pion configuration labels are run-local: 90 IDs overlap between GEVP200 and pilot v1 but none of their recorded gauge hashes agree. Blindness and independence checks must use the full source identity, not ID labels alone.",
        ],
        "inputs_sha256": {str(path.relative_to(ROOT)): sha256_file(path) for path in INPUTS},
    }
    return rows, summary


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def make_plot(path: Path, rows: list[dict], summary: dict) -> None:
    ids = [int(row["id"]) for row in rows]
    lanes = [
        ("Wilson HMC snapshot", [1 if row["snapshot_present"] else 0 for row in rows]),
        (
            "Pion GEVP200 measured",
            [1 if row["pion_gevp200_development"] or row["pion_gevp200_validation"] else 0 for row in rows],
        ),
        ("GEVP200 ↔ snapshot hash", [2 if row["gevp200_hash_matches_snapshot"] else 0 for row in rows]),
        ("Kunshan primary manifest", [1 if row["primary_manifest_sha256"] else 0 for row in rows]),
        ("GEVP200 ↔ primary hash", [3 if row["pion_gevp200_gauge_sha256"] and row["primary_manifest_sha256"] else 0 for row in rows]),
        ("Pion pilot v1 measured", [1 if row["pilot_v1_present"] else 0 for row in rows]),
        ("GEVP200 ↔ pilot v1 hash", [3 if row["pion_gevp200_gauge_sha256"] and row["pilot_v1_gauge_sha256"] else 0 for row in rows]),
    ]
    matrix = np.asarray([lane[1] for lane in lanes], dtype=int)
    cmap = ListedColormap(["#ffffff", "#9ecae1", "#31a354", "#ef8a62"])
    norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5], cmap.N)
    fig, ax = plt.subplots(figsize=(13, 4.8), constrained_layout=True)
    ax.imshow(matrix, aspect="auto", interpolation="nearest", cmap=cmap, norm=norm, extent=(-0.5, 199.5, 6.5, -0.5))
    ax.set_yticks(range(len(lanes)), [lane[0] for lane in lanes])
    ax.set_xticks(range(0, 200, 10))
    ax.set_xlim(-0.5, 199.5)
    ax.set_xlabel("Configuration label in archived manifests")
    ax.set_title("GEVP200 receipts match 180 measured HMC snapshot hash fields")
    ax.grid(axis="x", color="#888888", linewidth=0.35, alpha=0.4)
    ax.legend(
        handles=[
            Patch(facecolor="#9ecae1", label="record exists"),
            Patch(facecolor="#31a354", label="exact SHA-256 field match"),
            Patch(facecolor="#ef8a62", label="same ID, SHA-256 fields differ"),
        ],
        loc="lower center",
        bbox_to_anchor=(0.5, -0.38),
        ncol=3,
        frameon=False,
    )
    ax.text(
        0.995,
        0.98,
        "Pion GEVP200: development 0–119, gap 120–139, validation 140–199\n"
        "GEVP200 ↔ snapshot: 180/180 hashes; GEVP200 ↔ primary: 0/100; GEVP200 ↔ pilot v1: 0/90",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=8,
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.92, "edgecolor": "#aaaaaa"},
    )
    fig.savefig(path, dpi=170)
    plt.close(fig)


def build(output: Path) -> dict:
    rows, summary = collect()
    output.mkdir(parents=True)
    protocol = {
        "purpose": "read-only crosswalk of archived gauge hash fields",
        "row_unit": "one configuration ID in the union of the snapshot, primary manifest, Pion GEVP200, and Pion pilot v1",
        "hash_rule": "exact equality of recorded SHA-256 strings; no raw gauge bytes are inferred or synthesized",
        "plaquette_absolute_tolerance": PLAQUETTE_ATOL,
        "residual_tolerance": RESIDUAL_TOLERANCE,
        "inputs": [str(path.relative_to(ROOT)) for path in INPUTS],
        "source_recovery": "scan local Git blob contents for recorded measurement and kernel SHA-256 values",
    }
    (output / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")
    write_csv(output / "crosswalk.csv", rows)
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    make_plot(output / "identity_crosswalk.png", rows, summary)

    cross = summary["crosswalks"]
    p200 = summary["pion_gevp200"]
    measurement = summary["source_identity"]["measurement"]
    kernel = summary["source_identity"]["kernel"]
    readme = f"""# Pion GEVP200 and Wilson HMC snapshot crosswalk

This read-only audit compares archived provenance hash fields by configuration ID. It does not read or regenerate gauge configurations.

## Directly observed

- The Wilson snapshot contains {summary["snapshot"]["rows"]} IDs ({summary["snapshot"]["id_range"][0]}–{summary["snapshot"]["id_range"][1]}). The Pion GEVP200 receipts contain {p200["development_records"]} development records ({p200["development_ids"][0]}–{p200["development_ids"][1]}) and {p200["validation_records"]} validation records ({p200["validation_ids"][0]}–{p200["validation_ids"][1]}), with a declared gap {p200["gap_ids"][0]}–{p200["gap_ids"][1]}. Saved NPZ ID arrays agree with the provenance record IDs.
- Pion GEVP200 and the Wilson snapshot have identical recorded gauge SHA-256 strings for {cross["gevp200_to_snapshot"]["exact_hash_matches"]}/{cross["gevp200_to_snapshot"]["overlap"]} overlapping measured IDs. Plaquettes also agree for {cross["gevp200_to_snapshot"]["plaquette_matches"]}/{cross["gevp200_to_snapshot"]["overlap"]}; all 180 measured residuals are at or below 1e-10, with maximum {p200["residual_max"]:.6g}.
- For IDs 0–99, Pion GEVP200 and the primary Kunshan manifest have matching plaquettes for {cross["gevp200_to_primary_manifest"]["plaquette_matches"]}/100 IDs but matching gauge hash fields for {cross["gevp200_to_primary_manifest"]["exact_hash_matches"]}/100. The older Pion pilot v1 matches the primary manifest for {cross["pilot_v1_to_primary_manifest"]["exact_hash_matches"]}/{cross["pilot_v1_to_primary_manifest"]["overlap"]} rows.
- Pion GEVP200 and pilot v1 reuse {cross["gevp200_to_pilot_v1_same_id"]["overlap"]} numeric ID labels, but their recorded gauge hashes match for {cross["gevp200_to_pilot_v1_same_id"]["exact_hash_matches"]} IDs. Thus configuration labels alone do not identify the gauge field across these archived runs.
- Pion GEVP200 records measurement source SHA-256 {measurement["recorded_sha256"]}. A byte-identical historical measure.py blob exists in local Git at {measurement["historical_git_blob_search"]["matches"][0]["reachable_paths"][0] if measurement["historical_git_blob_search"]["matches"] and measurement["historical_git_blob_search"]["matches"][0]["reachable_paths"] else "an unlabelled Git blob"}; its current file has hash {measurement["current_sha256"]}. The recorded kernel SHA-256 matches the current kernel: {kernel["current_matches"]}.

## Interpretation and limits

The exact 180/180 digest-field agreement is direct evidence that the archived Pion GEVP200 measurement provenance used the same declared gauge hashes as the Wilson snapshot for its measured IDs. This partially corroborates the snapshot's identity history. It does not rehash gauge bytes, prove the HMC SAVED files had those bytes, explain the primary-manifest conflict, or fully establish that the Wilson production log and Pion measurement were the same run.

The Pion GEVP200 validation report has reference_passed={p200["validation_reference_passed"]} and score_status={p200["validation_score_status"]}. Its 60 validation records therefore do not supply an accepted physical anchor or official score. The measurements are already archived and analyzed; do not call them a fresh blind validation for another model.

![Configuration ID and hash-field crosswalk](identity_crosswalk.png)

Per-ID values are in crosswalk.csv. Frozen input, source, and output hashes are in provenance.json; protocol rules are in protocol.json.
"""
    (output / "README.md").write_text(readme)

    output_names = ["protocol.json", "crosswalk.csv", "summary.json", "identity_crosswalk.png", "README.md"]
    provenance = {
        "input_sha256": summary["inputs_sha256"],
        "generator_sha256": sha256_file(Path(__file__).resolve()),
        "output_sha256": {name: sha256_file(output / name) for name in output_names},
        "git_blob_scan": {
            "measurement": measurement["historical_git_blob_search"],
            "kernel": kernel["git_blob_search"],
        },
    }
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    return summary


def verify(output: Path) -> None:
    provenance = read_json(output / "provenance.json")
    rows, expected_summary = collect()
    for relative, expected in provenance["input_sha256"].items():
        if sha256_file(ROOT / relative) != expected:
            raise SystemExit(f"input hash mismatch: {relative}")
    if provenance["input_sha256"] != expected_summary["inputs_sha256"]:
        raise SystemExit("input manifest does not cover the current source set")
    if sha256_file(Path(__file__).resolve()) != provenance["generator_sha256"]:
        raise SystemExit("generator hash mismatch")
    if read_json(output / "summary.json") != expected_summary:
        raise SystemExit("summary differs from current archived records")
    with (output / "crosswalk.csv").open(newline="") as stream:
        stored_rows = list(csv.DictReader(stream))
    if len(stored_rows) != len(rows):
        raise SystemExit("crosswalk row count mismatch")
    for expected_row, stored_row in zip(rows, stored_rows):
        for key in CSV_COLUMNS:
            expected_value = str(expected_row[key])
            if stored_row[key] != expected_value:
                raise SystemExit(f"crosswalk mismatch at ID {expected_row['id']} field {key}")
    for name, expected in provenance["output_sha256"].items():
        if sha256_file(output / name) != expected:
            raise SystemExit(f"output hash mismatch: {name}")
    print(
        "PASS: "
        f"GEVP200/snapshot hashes {expected_summary['crosswalks']['gevp200_to_snapshot']['exact_hash_matches']}/"
        f"{expected_summary['crosswalks']['gevp200_to_snapshot']['overlap']}; "
        f"primary-manifest hashes {expected_summary['crosswalks']['gevp200_to_primary_manifest']['exact_hash_matches']}/"
        f"{expected_summary['crosswalks']['gevp200_to_primary_manifest']['overlap']}; "
        f"rows {len(rows)}; frozen output hashes match"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["build", "verify"], nargs="?", default="build")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    if args.action == "verify":
        verify(output)
        return
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {output}")
    summary = build(output)
    print(
        json.dumps(
            {
                "gevp200_snapshot_hash_matches": summary["crosswalks"]["gevp200_to_snapshot"],
                "gevp200_primary_hash_matches": summary["crosswalks"]["gevp200_to_primary_manifest"],
                "p200_vs_pilot_hash_matches": summary["crosswalks"]["gevp200_to_pilot_v1_same_id"],
                "historical_measure_source_recovered": bool(
                    summary["source_identity"]["measurement"]["historical_git_blob_search"]["matches"]
                ),
                "output": str(output.relative_to(ROOT)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
