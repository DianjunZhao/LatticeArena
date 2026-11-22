"""Create a read-only diagnostic of the archived Kunshan HMC log.

The log contains sparse trajectory checkpoints.  This script deliberately does
not expand those checkpoints into per-trajectory records or infer missing
accept/reject decisions.
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


ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "results/kunshan_logs/hmc_production.log"
SNAPSHOT = ROOT / "results/wilson_loop/hmc_quality_v1/manifest_snapshot.json"
OUTPUT = ROOT / "results/wilson_loop/hmc_log_archive_diagnostic_v1"

TRAJECTORY_RE = re.compile(
    r"^TRAJ (\d+)/(\d+) acc=(True|False) plaquette=([^ ]+) "
    r"dE=([^ ]+) sec=([^ ]+) acc_rate=([^ ]+)"
)
SAVED_RE = re.compile(r"^SAVED (\S+) id=(\d+) traj=(\d+) plaquette=([^ ]+)")
INIT_RE = re.compile(
    r"^INIT lattice=(\[[^]]+\]) beta=([^ ]+) n_steps=(\d+) "
    r"seed=(\d+) tau=([^ ]+) plaquette=([^ ]+)"
)
DONE_RE = re.compile(
    r"^DONE saved=(\d+) trajectories=(\d+) accept_rate=([^ ]+) "
    r"wall_seconds=([^ ]+) sec_per_traj=([^ ]+)"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_log(path: Path) -> tuple[dict, list[dict], list[dict], str]:
    lines = path.read_text().splitlines()
    init = None
    done = None
    trajectory_rows = []
    saved_rows = []
    for line in lines:
        if match := INIT_RE.match(line):
            init = {
                "lattice": json.loads(match.group(1)),
                "beta": float(match.group(2)),
                "n_steps": int(match.group(3)),
                "seed": int(match.group(4)),
                "tau": float(match.group(5)),
                "initial_plaquette": float(match.group(6)),
            }
        elif match := TRAJECTORY_RE.match(line):
            trajectory_rows.append(
                {
                    "trajectory": int(match.group(1)),
                    "planned_trajectories": int(match.group(2)),
                    "checkpoint_accept": match.group(3) == "True",
                    "plaquette": float(match.group(4)),
                    "delta_h": float(match.group(5)),
                    "seconds": float(match.group(6)),
                    "cumulative_accept_rate": float(match.group(7)),
                }
            )
        elif match := SAVED_RE.match(line):
            saved_rows.append(
                {
                    "output_path": match.group(1),
                    "id": int(match.group(2)),
                    "trajectory": int(match.group(3)),
                    "plaquette": float(match.group(4)),
                }
            )
        elif match := DONE_RE.match(line):
            done = {
                "saved": int(match.group(1)),
                "trajectories": int(match.group(2)),
                "accept_rate_reported": float(match.group(3)),
                "wall_seconds": float(match.group(4)),
                "seconds_per_trajectory": float(match.group(5)),
            }
    if init is None or done is None:
        raise ValueError("required INIT or DONE record is absent")
    if len(saved_rows) != done["saved"]:
        raise ValueError("SAVED row count disagrees with DONE record")
    if not trajectory_rows or not saved_rows:
        raise ValueError("no trajectory checkpoints or saved configurations found")
    return init, trajectory_rows, saved_rows, lines[0]


def validate_snapshot(saved_rows: list[dict], snapshot_path: Path) -> dict:
    snapshot = json.loads(snapshot_path.read_text())
    configs = snapshot.get("configs", [])
    matches = []
    for row in saved_rows:
        if row["id"] >= len(configs):
            matches.append(False)
            continue
        item = configs[row["id"]]
        matches.append(
            item.get("id") == row["id"]
            and item.get("trajectory") == row["trajectory"]
            and math.isclose(
                float(item.get("plaquette", math.nan)),
                row["plaquette"],
                rel_tol=0.0,
                abs_tol=1e-7,
            )
        )
    return {
        "snapshot_ensemble_label": snapshot.get("ensemble"),
        "snapshot_configuration_count": len(configs),
        "log_rows_matching_snapshot_by_id_trajectory_plaquette": sum(matches),
        "log_rows_checked": len(matches),
        "extra_snapshot_rows_not_covered_by_this_log": max(0, len(configs) - len(saved_rows)),
        "matches": all(matches),
    }


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def make_plot(path: Path, init: dict, done: dict, checkpoints: list[dict], saved: list[dict]) -> None:
    fig, axes = plt.subplots(4, 1, figsize=(10.5, 12), sharex=False, constrained_layout=True)
    trajectories = [row["trajectory"] for row in checkpoints]
    production_boundary = saved[0]["trajectory"] - 1

    axes[0].axhline(0.0, color="0.35", linewidth=0.9)
    axes[0].scatter(trajectories, [row["delta_h"] for row in checkpoints], s=24, color="#276FBF")
    axes[0].set_ylabel(r"checkpoint $\Delta H$")
    axes[0].set_title(f"All {len(checkpoints)} sparse ΔH checkpoints (trajectory 1 outlier retained)")

    production_delta_h = [row for row in checkpoints if row["trajectory"] >= saved[0]["trajectory"]]
    axes[1].axhline(0.0, color="0.35", linewidth=0.9)
    axes[1].scatter([row["trajectory"] for row in production_delta_h],
                    [row["delta_h"] for row in production_delta_h], s=24, color="#276FBF")
    axes[1].set_ylabel(r"checkpoint $\Delta H$")
    axes[1].set_title(
        f"At/after first save: {len(production_delta_h)} checkpoints; "
        "zoomed view (dotted line is inferred save boundary)"
    )

    axes[2].plot(trajectories, [row["plaquette"] for row in checkpoints], "o-", ms=3, lw=0.8,
                 color="#A23B72", label="logged trajectory checkpoints")
    axes[2].scatter([row["trajectory"] for row in saved], [row["plaquette"] for row in saved],
                    s=13, color="#2A9D8F", alpha=0.75, label="saved configurations (100)")
    axes[2].set_ylabel("plaquette")
    axes[2].legend(loc="lower right", fontsize=8)

    axes[3].plot(trajectories, [row["cumulative_accept_rate"] for row in checkpoints],
                 "o-", ms=3, lw=0.8, color="#F18F01", label="logged cumulative rate")
    axes[3].axhline(done["accept_rate_reported"], color="#333333", linestyle="--", linewidth=1,
                    label="DONE aggregate")
    axes[3].set_ylabel("acceptance rate")
    axes[3].set_xlabel("trajectory")
    axes[3].set_ylim(0.94, 1.005)
    axes[3].legend(loc="lower right", fontsize=8)

    for axis in axes:
        axis.axvline(production_boundary, color="#777777", linestyle=":", linewidth=1)
        axis.grid(alpha=0.2)
    axes[1].set_xlim(380, done["trajectories"] + 10)
    post_values = [row["delta_h"] for row in production_delta_h]
    padding = max(0.015, 0.12 * (max(post_values) - min(post_values)))
    axes[1].set_ylim(min(post_values) - padding, max(post_values) + padding)
    axes[3].text(
        0.01,
        0.05,
        f"dotted line: first saved configuration at traj={saved[0]['trajectory']} "
        "(inferred boundary, not a declared thermalization cut)",
        transform=axes[2].transAxes,
        va="bottom",
        fontsize=8,
    )
    fig.suptitle(
        f"Archived HMC log: {init['lattice']}, β={init['beta']}, "
        f"{done['trajectories']} trajectories, reported acceptance={done['accept_rate_reported']:.3f} (rounded)",
        fontsize=14,
    )
    fig.savefig(path, dpi=170)
    plt.close(fig)


def build_summary(init: dict, checkpoints: list[dict], saved: list[dict], done: dict,
                  snapshot_audit: dict, log_path: Path, snapshot_path: Path) -> dict:
    first_saved_traj = saved[0]["trajectory"]
    pre = [row["delta_h"] for row in checkpoints if row["trajectory"] < first_saved_traj]
    post = [row["delta_h"] for row in checkpoints if row["trajectory"] >= first_saved_traj]
    saved_plaquettes = [row["plaquette"] for row in saved]

    def sample_stats(values: list[float]) -> dict:
        return {
            "n": len(values),
            "mean": statistics.mean(values),
            "sample_sd": statistics.stdev(values) if len(values) > 1 else None,
            "min": min(values),
            "max": max(values),
        }

    return {
        "classification": "archived_partial_hmc_log_diagnostic",
        "sources": {
            "log": str(log_path.relative_to(ROOT)),
            "log_sha256": sha256(log_path),
            "snapshot": str(snapshot_path.relative_to(ROOT)),
            "snapshot_sha256": sha256(snapshot_path),
            "generator": str(Path(__file__).resolve().relative_to(ROOT)),
            "generator_sha256": sha256(Path(__file__).resolve()),
        },
        "run_header": init,
        "run_done": done,
        "trajectory_checkpoint_count": len(checkpoints),
        "trajectory_checkpoint_first_last": [checkpoints[0]["trajectory"], checkpoints[-1]["trajectory"]],
        "delta_h_checkpoint_all_stats": sample_stats([row["delta_h"] for row in checkpoints]),
        "delta_h_checkpoint_before_first_save_stats": sample_stats(pre),
        "delta_h_checkpoint_at_or_after_first_save_stats": sample_stats(post),
        "saved_configuration_count_in_log": len(saved),
        "saved_configuration_first_last_id": [saved[0]["id"], saved[-1]["id"]],
        "saved_configuration_first_last_trajectory": [saved[0]["trajectory"], saved[-1]["trajectory"]],
        "saved_plaquette_descriptive_stats": sample_stats(saved_plaquettes),
        "snapshot_crosscheck": snapshot_audit,
        "limits": [
            "Delta H is printed only at sparse checkpoints, not for all trajectories.",
            "The log contains a rounded aggregate acceptance rate, not all accept/reject decisions.",
            "The first saved configuration is a boundary inferred from output; no thermalization cut is declared.",
            "This log ends at trajectory 900 and covers only 100 of the snapshot's 200 configurations.",
            "Gauge files are absent locally, so configuration hashes cannot be rechecked against bytes.",
            "The logged path and pilot snapshot do not establish identity with protocol_v4's S16T16B ensemble.",
        ],
    }


def verify(output: Path, log_path: Path, snapshot_path: Path) -> None:
    provenance_path = output / "provenance.json"
    provenance = json.loads(provenance_path.read_text())
    actual_inputs = {
        "log": sha256(log_path),
        "snapshot": sha256(snapshot_path),
        "generator": sha256(Path(__file__).resolve()),
    }
    if actual_inputs != provenance["input_sha256"]:
        raise SystemExit("input hash mismatch")
    for name, expected in provenance["output_sha256"].items():
        if sha256(output / name) != expected:
            raise SystemExit(f"output hash mismatch: {name}")
    print("PASS: archived HMC log diagnostic input and output hashes match")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, default=LOG)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    if args.verify:
        verify(args.output, args.log, args.snapshot)
        return
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {args.output}")

    init, checkpoints, saved, _ = parse_log(args.log)
    lines = args.log.read_text().splitlines()
    done_match = next(DONE_RE.match(line) for line in lines if DONE_RE.match(line))
    done = {
        "saved": int(done_match.group(1)),
        "trajectories": int(done_match.group(2)),
        "accept_rate_reported": float(done_match.group(3)),
        "wall_seconds": float(done_match.group(4)),
        "seconds_per_trajectory": float(done_match.group(5)),
    }
    snapshot_audit = validate_snapshot(saved, args.snapshot)
    if not snapshot_audit["matches"]:
        raise SystemExit("logged saved configurations do not match snapshot prefix")
    args.output.mkdir(parents=True)

    write_csv(
        args.output / "trajectory_checkpoints.csv",
        checkpoints,
        ["trajectory", "planned_trajectories", "checkpoint_accept", "plaquette", "delta_h", "seconds",
         "cumulative_accept_rate"],
    )
    write_csv(
        args.output / "saved_configurations.csv",
        saved,
        ["output_path", "id", "trajectory", "plaquette"],
    )
    summary = build_summary(init, checkpoints, saved, done, snapshot_audit, args.log, args.snapshot)
    summary_path = args.output / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    make_plot(args.output / "hmc_log_diagnostic.png", init, done, checkpoints, saved)

    output_names = ["trajectory_checkpoints.csv", "saved_configurations.csv", "summary.json", "hmc_log_diagnostic.png"]
    provenance = {
        "input_sha256": {
            "log": sha256(args.log),
            "snapshot": sha256(args.snapshot),
            "generator": sha256(Path(__file__).resolve()),
        },
        "output_sha256": {name: sha256(args.output / name) for name in output_names},
        "trajectory_checkpoint_count": len(checkpoints),
        "saved_configuration_count": len(saved),
        "snapshot_rows_matched": snapshot_audit["log_rows_matching_snapshot_by_id_trajectory_plaquette"],
    }
    (args.output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
