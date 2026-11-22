"""Read-only provenance audit for archived Kunshan HMC and pion pilot logs.

The audit keeps three identity levels separate: matching trajectory/plaquette
metadata, matching manifest hash fields, and re-hashing the unavailable gauge
bytes. Only the first two can be checked from the archived files in this repo.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
LOG_ROOT = ROOT / "results/kunshan_logs"
HMC_LOG = LOG_ROOT / "hmc_production.log"
MANIFEST = LOG_ROOT / "manifest.json"
SNAPSHOT = ROOT / "results/wilson_loop/hmc_quality_v1/manifest_snapshot.json"
DEVELOPMENT_LOG = LOG_ROOT / "pipe_127946355.log"
VALIDATION_MEASURE_LOG = LOG_ROOT / "pipe_127946906.log"
VALIDATION_REPORT_LOG = LOG_ROOT / "pipe_127947039.log"
CALIBRATION_LOG = LOG_ROOT / "pipe_127946768.log"
PION_DEVELOPMENT_PROVENANCE = ROOT / "results/pion_projection/s16t16_v1/development_provenance.json"
PION_VALIDATION_PROVENANCE = ROOT / "results/pion_projection/s16t16_v1/validation_provenance.json"
OPTIMIZE_V9_MANIFEST = ROOT / "results/optimize_gaussian/v9/manifest.json"
OUTPUT = LOG_ROOT / "archive_audit_v1"

SAVED_RE = re.compile(r"^SAVED (\S+) id=(\d+) traj=(\d+) plaquette=([^ ]+)")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl_rows(path: Path) -> tuple[list[dict], list[str]]:
    rows = []
    lines = path.read_text(errors="replace").splitlines()
    for line_no, line in enumerate(lines, start=1):
        value = line.strip()
        if not value.startswith("{"):
            continue
        try:
            record = json.loads(value)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and "id" in record and "gauge_sha256" in record:
            rows.append({"log": path.name, "line": line_no, **record})
    return rows, lines


def read_tagged_json(lines: list[str], tag: str) -> dict | None:
    prefix = f"{tag} "
    for line in lines:
        if line.startswith(prefix):
            return json.loads(line[len(prefix) :])
    return None


def read_hmc_saved(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(errors="replace").splitlines():
        match = SAVED_RE.match(line)
        if match:
            rows.append(
                {
                    "output_path": match.group(1),
                    "id": int(match.group(2)),
                    "trajectory": int(match.group(3)),
                    "plaquette": float(match.group(4)),
                }
            )
    return rows


def metadata_match(row: dict, manifest_row: dict, atol: float = 1e-7) -> bool:
    return (
        int(row["id"]) == int(manifest_row["id"])
        and int(row["trajectory"]) == int(manifest_row["trajectory"])
        and math.isclose(
            float(row["plaquette"]), float(manifest_row["plaquette"]), rel_tol=0.0, abs_tol=atol
        )
    )


def stats(values: list[float]) -> dict:
    return {
        "n": len(values),
        "min": min(values),
        "median": statistics.median(values),
        "mean": statistics.mean(values),
        "max": max(values),
    }


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def make_plot(path: Path, rows: list[dict], summary: dict) -> None:
    rows = sorted(rows, key=lambda row: int(row["id"]))
    ids = [int(row["id"]) for row in rows]
    residuals = [float(row["residual_max"]) for row in rows]
    total = [float(row["total_seconds"]) for row in rows]
    colors = ["#276FBF" if row["log"] == DEVELOPMENT_LOG.name else "#E07A32" for row in rows]

    fig, axes = plt.subplots(2, 1, figsize=(10.5, 7.4), sharex=True, constrained_layout=True)
    axes[0].scatter(ids, residuals, c=colors, s=20, alpha=0.85)
    axes[0].axhline(1e-10, color="#B33A3A", linestyle="--", linewidth=1,
                    label=r"declared residual target $10^{-10}$")
    axes[0].set_ylabel("max residual")
    axes[0].set_title("Archived GPU pion-pilot solve records (90 configurations)")
    axes[0].legend(loc="lower right", fontsize=8)

    axes[1].scatter(ids, total, c=colors, s=20, alpha=0.85)
    axes[1].set_ylabel("total seconds / configuration")
    axes[1].set_xlabel("configuration ID")
    axes[1].set_xlim(-2, 101)
    axes[1].set_xticks(range(0, 100, 10))
    axes[1].grid(alpha=0.2)
    axes[0].grid(alpha=0.2)

    for axis in axes:
        axis.axvspan(59.5, 69.5, color="#888888", alpha=0.12)
    axes[1].text(
        0.99,
        0.96,
        "Blue: development 0–59; orange: validation 70–99; gray: unused gap 60–69.\n"
        f"Manifest hash matches: {summary['pipeline_manifest_crosswalk']['hash_matches']}/"
        f"{summary['pipeline_manifest_crosswalk']['rows_checked']}; "
        f"snapshot prefix hash matches: {summary['manifest_snapshot_crosswalk']['hash_matches']}/"
        f"{summary['manifest_snapshot_crosswalk']['rows_checked']}",
        transform=axes[1].transAxes,
        ha="right",
        va="top",
        fontsize=8,
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85, "edgecolor": "#aaaaaa"},
    )
    fig.savefig(path, dpi=170)
    plt.close(fig)


def build(output: Path) -> dict:
    manifest = json.loads(MANIFEST.read_text())
    manifest_rows = manifest["configs"]
    manifest_by_id = {int(row["id"]): row for row in manifest_rows}
    snapshot = json.loads(SNAPSHOT.read_text())
    snapshot_rows = snapshot["configs"]
    snapshot_by_id = {int(row["id"]): row for row in snapshot_rows}
    pion_development = json.loads(PION_DEVELOPMENT_PROVENANCE.read_text())
    pion_validation = json.loads(PION_VALIDATION_PROVENANCE.read_text())
    optimize_v9 = json.loads(OPTIMIZE_V9_MANIFEST.read_text())

    dev_rows, dev_lines = read_jsonl_rows(DEVELOPMENT_LOG)
    val_rows, val_lines = read_jsonl_rows(VALIDATION_MEASURE_LOG)
    pipeline_rows = sorted(dev_rows + val_rows, key=lambda row: int(row["id"]))
    hmc_rows = read_hmc_saved(HMC_LOG)
    pion_records = {
        int(row["id"]): row
        for provenance in (pion_development, pion_validation)
        for row in provenance["records"]
    }

    pipeline_crosswalk = []
    for row in pipeline_rows:
        item = manifest_by_id.get(int(row["id"]))
        same_id_plaquette = bool(
            item
            and int(row["id"]) == int(item["id"])
            and math.isclose(
                float(row["plaquette"]), float(item["plaquette"]), rel_tol=0.0, abs_tol=1e-12
            )
        )
        pipeline_crosswalk.append(
            {
                "id": row["id"],
                "pipeline_log": row["log"],
                "id_plaquette_match_manifest": same_id_plaquette,
                "trajectory_logged": "trajectory" in row,
                "gauge_hash_matches_manifest": bool(item and row["gauge_sha256"] == item["sha256"]),
                "gauge_hash_matches_snapshot": bool(
                    int(row["id"]) in snapshot_by_id
                    and row["gauge_sha256"] == snapshot_by_id[int(row["id"])]["sha256"]
                ),
                "matches_pion_provenance_record": bool(
                    int(row["id"]) in pion_records
                    and all(
                        row[key] == pion_records[int(row["id"])][key]
                        for key in (
                            "gauge_sha256", "plaquette", "residual_max", "cache_key", "cache_hit",
                            "solve_and_residual_seconds", "sink_seconds", "total_seconds",
                            "cupy_pool_peak_reserved_bytes",
                        )
                    )
                ),
            }
        )

    hmc_crosswalk = []
    for row in hmc_rows:
        manifest_item = manifest_by_id.get(row["id"])
        snapshot_item = snapshot_by_id.get(row["id"])
        hmc_crosswalk.append(
            {
                **row,
                "manifest_metadata_matches": bool(manifest_item and metadata_match(row, manifest_item)),
                "snapshot_metadata_matches": bool(snapshot_item and metadata_match(row, snapshot_item)),
                "manifest_sha256": manifest_item.get("sha256", "") if manifest_item else "",
                "snapshot_sha256": snapshot_item.get("sha256", "") if snapshot_item else "",
                "hashes_comparable_from_hmc_log": False,
            }
        )

    validation_lines = VALIDATION_REPORT_LOG.read_text(errors="replace").splitlines()
    validation_record = read_tagged_json(validation_lines, "VALIDATION")
    calibration_lines = CALIBRATION_LOG.read_text(errors="replace").splitlines()
    calibration_record = read_tagged_json(calibration_lines, "CALIBRATION")
    frozen_submission = read_tagged_json(calibration_lines, "FROZEN_SUBMISSION")

    manifest_meta_matches = sum(row["manifest_metadata_matches"] for row in hmc_crosswalk)
    snapshot_meta_matches = sum(row["snapshot_metadata_matches"] for row in hmc_crosswalk)
    primary_snapshot_prefix_hash_matches = sum(
        manifest_by_id[i]["sha256"] == snapshot_by_id[i]["sha256"]
        for i in range(min(len(manifest_rows), len(snapshot_rows)))
    )
    pipeline_hash_matches = sum(row["gauge_hash_matches_manifest"] for row in pipeline_crosswalk)
    pipeline_snapshot_matches = sum(row["gauge_hash_matches_snapshot"] for row in pipeline_crosswalk)
    pion_record_matches = sum(row["matches_pion_provenance_record"] for row in pipeline_crosswalk)
    v9_protocol = optimize_v9["protocol"]
    v9_validation_ids = [int(value) for value in optimize_v9["ids"]["test"]]
    pion_validation_ids = [int(row["id"]) for row in pion_validation["records"]]
    v9_reuses_pion_validation = (
        v9_protocol.get("validation_manifest")
        == "results/pion_projection/s16t16_v1/validation_provenance.json"
        and v9_validation_ids == pion_validation_ids
    )

    environments = {}
    for path in (DEVELOPMENT_LOG, VALIDATION_MEASURE_LOG, VALIDATION_REPORT_LOG):
        lines = path.read_text(errors="replace").splitlines()
        environments[path.name] = {
            "python_line": next((line for line in lines if line.startswith("Python:")), None),
            "quda_line": next((line for line in lines if line.startswith("QUDA ")), None),
            "hip_driver": next((line.partition("=")[2].strip() for line in lines if line.startswith("HIP Driver version")), None),
            "hip_runtime": next((line.partition("=")[2].strip() for line in lines if line.startswith("HIP Runtime version")), None),
            "device_line": next((line for line in lines if line.startswith("Found device")), None),
        }

    residuals = [float(row["residual_max"]) for row in pipeline_rows]
    solve_times = [float(row["solve_and_residual_seconds"]) for row in pipeline_rows]
    sink_times = [float(row["sink_seconds"]) for row in pipeline_rows]
    total_times = [float(row["total_seconds"]) for row in pipeline_rows]
    memory = [int(row["cupy_pool_peak_reserved_bytes"]) for row in pipeline_rows]
    validation_results = validation_record["results"]

    summary = {
        "classification": "archived_partial_kunshan_gpu_and_hmc_evidence",
        "source_artifacts": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in (
                HMC_LOG, MANIFEST, SNAPSHOT, DEVELOPMENT_LOG, VALIDATION_MEASURE_LOG,
                VALIDATION_REPORT_LOG, CALIBRATION_LOG, PION_DEVELOPMENT_PROVENANCE,
                PION_VALIDATION_PROVENANCE, OPTIMIZE_V9_MANIFEST,
            )
        },
        "hmc_log": {
            "saved_rows": len(hmc_rows),
            "first_last_id": [hmc_rows[0]["id"], hmc_rows[-1]["id"]],
            "manifest_metadata_matches": manifest_meta_matches,
            "snapshot_metadata_matches": snapshot_meta_matches,
            "hash_check": "unavailable: HMC SAVED records contain no gauge hash; local gauge bytes are absent",
        },
        "manifest_snapshot_crosswalk": {
            "primary_manifest_configs": len(manifest_rows),
            "snapshot_configs": len(snapshot_rows),
            "metadata_matches_for_primary_prefix": sum(
                metadata_match(manifest_by_id[i], snapshot_by_id[i])
                for i in range(min(len(manifest_rows), len(snapshot_rows)))
            ),
            "hash_matches": primary_snapshot_prefix_hash_matches,
            "rows_checked": min(len(manifest_rows), len(snapshot_rows)),
        },
        "pipeline_manifest_crosswalk": {
            "rows_checked": len(pipeline_crosswalk),
            "hash_matches": pipeline_hash_matches,
            "id_plaquette_matches": sum(row["id_plaquette_match_manifest"] for row in pipeline_crosswalk),
            "snapshot_hash_matches": pipeline_snapshot_matches,
            "missing_ids": sorted(set(manifest_by_id) - {int(row["id"]) for row in pipeline_rows}),
            "rows_by_log": {
                DEVELOPMENT_LOG.name: len(dev_rows),
                VALIDATION_MEASURE_LOG.name: len(val_rows),
            },
        },
        "pipeline_pion_provenance_crosswalk": {
            "rows_checked": len(pipeline_crosswalk),
            "full_record_matches": pion_record_matches,
            "development_records": len(pion_development["records"]),
            "validation_records": len(pion_validation["records"]),
        },
        "optimize_gaussian_v9_linkage": {
            "protocol_version": v9_protocol["version"],
            "test_ids": [v9_validation_ids[0], v9_validation_ids[-1]],
            "test_id_count": len(v9_validation_ids),
            "validation_manifest": v9_protocol.get("validation_manifest"),
            "reuses_pion_pilot_validation_ids": v9_reuses_pion_validation,
            "fresh_blind_test": not v9_reuses_pion_validation,
        },
        "pipeline_measurements": {
            "residual_max": stats(residuals),
            "residuals_over_1e-10": sum(value > 1e-10 for value in residuals),
            "solve_and_residual_seconds": stats(solve_times),
            "sink_seconds": stats(sink_times),
            "total_seconds": stats(total_times),
            "cupy_pool_peak_reserved_bytes_unique": sorted(set(memory)),
            "cache_hits": sum(bool(row["cache_hit"]) for row in pipeline_rows),
            "cache_misses": sum(not bool(row["cache_hit"]) for row in pipeline_rows),
        },
        "environment": environments,
        "validation": {
            "protocol": validation_record["protocol"],
            "reference_passed": validation_record["reference_passed"],
            "score_status": validation_record["score_status"],
            "reference": validation_record["reference"],
            "agent_vs_tuned_gaussian": validation_record["agent_vs_tuned_gaussian"],
            "risk_by_candidate": {
                name: {
                    "risk": result["risk"],
                    "risk_95_interval": result["risk_95_interval"],
                    "score": result["score"],
                }
                for name, result in validation_results.items()
            },
            "calibration_reference_passed": calibration_record["reference_passed"],
            "calibration_reference": calibration_record["reference"],
            "calibration_windows": calibration_record["windows"],
            "calibration_failure_reasons": calibration_record["failure_reasons"],
            "frozen_submission_sha256": validation_record["submission_sha256"],
            "validation_sha256": validation_record["validation_sha256"],
            "calibration_frozen_submission_fields": sorted(frozen_submission),
        },
        "limits": [
            "Pipeline row gauge_sha256 values match the 100-config Kunshan manifest by ID for all 90 measured IDs; gauge bytes are absent locally, so these hashes cannot be recomputed here.",
            "All per-configuration pipeline fields also match the repository's pion development/validation provenance records; that confirms archive consistency, not a rehash of the absent gauge bytes.",
            "The hmc_production.log SAVED rows match manifest and snapshot IDs, trajectories, and plaquettes within 1e-7, but the log has no gauge hashes.",
            "The 100-entry primary manifest and 200-entry hmc_quality snapshot match metadata on the first 100 rows but their SHA-256 fields match 0/100; this identity conflict is unresolved.",
            "Validation uses protocol s16t16-pilot-v1 with IDs 70-99; optimize_gaussian v9 reuses this same 30-ID validation provenance, so it is not a fresh blind test. This older signed-mixture pilot is not itself the v9 trainable-W experiment or a Wilson protocol_v4 S16T16B receipt.",
            "The reference fit failed; the diagnostic risk ratio is not an official/physical score.",
            "HMC coverage is still sparse: 45 Delta-H checkpoints, rounded aggregate acceptance, no full per-trajectory accept/reject list, and no declared autocorrelation-aware thermalization receipt.",
        ],
    }

    output.mkdir(parents=True)
    write_csv(
        output / "pipeline_rows.csv",
        pipeline_rows,
        ["id", "log", "line", "gauge_sha256", "plaquette", "residual_max", "cache_key",
         "cache_hit", "solve_and_residual_seconds", "sink_seconds", "total_seconds",
         "cupy_pool_peak_reserved_bytes"],
    )
    write_csv(
        output / "hmc_manifest_crosswalk.csv",
        hmc_crosswalk,
        ["output_path", "id", "trajectory", "plaquette", "manifest_metadata_matches",
         "snapshot_metadata_matches", "manifest_sha256", "snapshot_sha256", "hashes_comparable_from_hmc_log"],
    )
    write_csv(
        output / "pipeline_manifest_crosswalk.csv",
        pipeline_crosswalk,
        ["id", "pipeline_log", "id_plaquette_match_manifest", "trajectory_logged",
         "gauge_hash_matches_manifest", "gauge_hash_matches_snapshot", "matches_pion_provenance_record"],
    )
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    make_plot(output / "archive_receipt_diagnostic.png", pipeline_rows, summary)

    readme = f"""# Kunshan archived HMC and pion-pilot receipt audit

This read-only audit joins the archived HMC log, two manifests, and archived GPU pipeline logs. It does not regenerate measurements or infer missing HMC trajectory records.

## Directly observed

- `pipe_127946355.log` has {len(dev_rows)} per-configuration rows for development IDs 0–59; `pipe_127946906.log` has {len(val_rows)} rows for validation IDs 70–99. IDs 60–69 are the declared unused gap.
- All {pipeline_hash_matches}/{len(pipeline_rows)} logged `gauge_sha256` values match the same-ID `sha256` entries in `results/kunshan_logs/manifest.json`. The maximum recorded residual is {max(residuals):.4g}; {summary['pipeline_measurements']['residuals_over_1e-10']} rows exceed 1e-10. Median solve-plus-residual time is {statistics.median(solve_times):.3f} s and median total configuration time is {statistics.median(total_times):.3f} s. These are archived run values, not a current-hardware benchmark.
- All {pion_record_matches}/{len(pipeline_rows)} rows also match the repository's `s16t16_v1` development/validation provenance records field by field. The optimize_gaussian v9 manifest points to the same validation provenance and lists the same {len(v9_validation_ids)} test IDs ({v9_validation_ids[0]}–{v9_validation_ids[-1]}), so that set is already observed and cannot be treated as a fresh blind test.
- The log headers record QUDA/HIP device information; details and input hashes are in `summary.json`.
- The validation JSON reports `score_status={validation_record['score_status']}` and `reference_passed=false`: nominal mass {validation_record['reference']['mass']:.5f} (SE {validation_record['reference']['se']:.5f}), $\\chi^2/\\mathrm{{dof}}={validation_record['reference']['chi2']:.2f}/{validation_record['reference']['dof']}$, approximate $p={validation_record['reference']['p_approx']:.2g}$. The two alternative reference windows shift by {calibration_record['windows'][0]['paired_shift_z']:.2f}σ and {calibration_record['windows'][2]['paired_shift_z']:.2f}σ. The reported improvement factor is `R_tuned_gaussian/R_agent={validation_record['agent_vs_tuned_gaussian']['risk_ratio']:.3f}` with 95% interval {validation_record['agent_vs_tuned_gaussian']['risk_ratio_95_interval']}; this remains an unscored diagnostic because the reference gate failed.
- The 100 saved rows in `hmc_production.log` match both manifests by ID, trajectory, and plaquette within 1e-7. The HMC log has no per-configuration gauge hash, so that crosswalk is metadata-only.

## Identity conflict

The 100-entry `results/kunshan_logs/manifest.json` and the first 100 rows of the 200-entry `hmc_quality_v1/manifest_snapshot.json` match on ID, trajectory, and plaquette, but their hash fields match **{primary_snapshot_prefix_hash_matches}/{min(len(manifest_rows), len(snapshot_rows))}** rows. The pipeline logs match the primary Kunshan manifest for all 90 measured IDs, and match **{pipeline_snapshot_matches}/{len(pipeline_rows)}** snapshot hashes. This could reflect different hash inputs or a stale/incorrect snapshot; the archived files do not establish which explanation is correct. No local gauge bytes are available to recompute either hash.

![Residual and timing diagnostics](archive_receipt_diagnostic.png)

## Status boundary

This closes an archive-discovery gap: real historical GPU measurement receipts exist for the pion pilot, and they can be cross-linked to the primary 100-configuration manifest at the hash-field level. It does not authenticate the HMC log's gauge bytes, resolve the conflicting snapshot hashes, make the failed reference score valid, reproduce the optimize-gaussian v9 training result or confirm that its $W$ was trained, or satisfy Wilson protocol_v4 / S16T16B production gates.

The source logs and manifests are unchanged. To verify frozen inputs/outputs run:

```bash
python3 -B -m tasks.kunshan_archive_audit --verify
```
"""
    (output / "README.md").write_text(readme)

    outputs = [
        "pipeline_rows.csv", "hmc_manifest_crosswalk.csv", "pipeline_manifest_crosswalk.csv",
        "summary.json", "archive_receipt_diagnostic.png", "README.md",
    ]
    provenance = {
        "input_sha256": summary["source_artifacts"],
        "generator_sha256": sha256(Path(__file__).resolve()),
        "output_sha256": {name: sha256(output / name) for name in outputs},
    }
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    return summary


def verify(output: Path) -> None:
    provenance = json.loads((output / "provenance.json").read_text())
    for relative, expected in provenance["input_sha256"].items():
        if sha256(ROOT / relative) != expected:
            raise SystemExit(f"input hash mismatch: {relative}")
    if sha256(Path(__file__).resolve()) != provenance["generator_sha256"]:
        raise SystemExit("generator hash mismatch")
    for name, expected in provenance["output_sha256"].items():
        if sha256(output / name) != expected:
            raise SystemExit(f"output hash mismatch: {name}")
    print("PASS: Kunshan archive audit input and output hashes match")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    if args.verify:
        verify(output)
        return
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {output}")
    summary = build(output)
    print(json.dumps({
        "hmc_saved": summary["hmc_log"]["saved_rows"],
        "pipeline_rows": summary["pipeline_manifest_crosswalk"]["rows_checked"],
        "pipeline_hash_matches": summary["pipeline_manifest_crosswalk"]["hash_matches"],
        "snapshot_prefix_hash_matches": summary["manifest_snapshot_crosswalk"]["hash_matches"],
        "reference_passed": summary["validation"]["reference_passed"],
        "output": str(output.relative_to(ROOT)),
    }, indent=2))


if __name__ == "__main__":
    main()
