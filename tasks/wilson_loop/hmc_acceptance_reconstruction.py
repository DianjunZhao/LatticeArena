"""Source-assisted reconstruction of aggregate acceptance in an archived HMC run.

The archived log prints cumulative acceptance only every 20 trajectories, while
the shipped generator records a rounded DONE rate using the planned trajectory
count even if max-save causes an earlier break. This audit reconstructs
cumulative/window counts without inventing per-trajectory decisions.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "results/kunshan_logs/hmc_production.log"
GENERATOR = ROOT / "pilot/hmc_generate.py"
RUN_NOTE = ROOT / "doc/kunshan_dcu_run.md"
OUT = ROOT / "results/wilson_loop/hmc_acceptance_reconstruction_v2"
SOURCE = Path(__file__).resolve()

TRAJ_RE = re.compile(
    r"^TRAJ (?P<traj>\d+)/(?P<planned>\d+) acc=(?P<acc>True|False) "
    r"plaquette=(?P<plaquette>[^ ]+) dE=(?P<delta_h>[^ ]+) "
    r"sec=(?P<seconds>[^ ]+) acc_rate=(?P<rate>\d+\.\d{3})$"
)
SAVED_RE = re.compile(r"^SAVED \S+ id=(\d+) traj=(\d+) plaquette=([^ ]+)$")
DONE_RE = re.compile(
    r"^DONE saved=(\d+) trajectories=(\d+) accept_rate=(\d+\.\d{3}) "
    r"wall_seconds=([^ ]+) sec_per_traj=([^ ]+)$"
)

PLAN = {
    "schema": "hmc-acceptance-source-reconstruction-v1",
    "parameters_from_run_note": {
        "thermal": 400,
        "planned_trajectories": 900,
        "save_every": 5,
        "max_save": 100,
    },
    "reported_rate_format": "Python f-string fixed-point with 3 decimal places, as in current pilot/hmc_generate.py",
    "reconstruction_rule": "enumerate integer accepted counts whose formatted ratio reproduces each logged cumulative rate",
    "infer_actual_stop": "thermal + 1 + (max_save - 1) * save_every, then source break when saved reaches max_save",
    "explicit_nonclaims": [
        "No individual acceptance decisions are imputed for unlogged trajectories.",
        "No confidence interval assumes independent Bernoulli decisions.",
        "Current repository generator is not bound to the historical run by a run-specific source hash.",
        "This does not resolve ensemble identity, gauge-byte hashes, thermalization, or protocol_v4 F4.",
    ],
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def frozen_protocol() -> dict:
    payload = dict(PLAN)
    payload["input_sha256"] = {
        "log": sha256(LOG),
        "generator": sha256(GENERATOR),
        "run_note": sha256(RUN_NOTE),
    }
    payload["source_sha256"] = sha256(SOURCE)
    payload["protocol_sha256"] = hashlib.sha256(canonical_json(payload)).hexdigest()
    return payload


def require_source_contract() -> None:
    generator = GENERATOR.read_text()
    run_note = RUN_NOTE.read_text()
    required_source = (
        "accepted += int(acc)",
        "acc_rate={accepted / (traj + 1):.3f}",
        "accept_rate={accepted / args.trajectories:.3f}",
        "if saved >= args.max_save:",
    )
    missing = [snippet for snippet in required_source if snippet not in generator]
    if missing:
        raise RuntimeError(f"generator source no longer matches reconstruction contract: {missing}")
    if "--thermal 400 --trajectories 900 --save-every 5 --max-save 100" not in run_note:
        raise RuntimeError("documented run settings do not match frozen reconstruction settings")


def parse_inputs() -> tuple[list[dict], list[dict], dict]:
    require_source_contract()
    checkpoint_rows = []
    saved_rows = []
    done = None
    for line in LOG.read_text().splitlines():
        if match := TRAJ_RE.match(line):
            checkpoint_rows.append({
                "trajectory": int(match.group("traj")),
                "planned_trajectories": int(match.group("planned")),
                "checkpoint_accept": match.group("acc") == "True",
                "reported_cumulative_rate": match.group("rate"),
                "plaquette": float(match.group("plaquette")),
                "delta_h": float(match.group("delta_h")),
                "seconds": float(match.group("seconds")),
            })
        elif match := SAVED_RE.match(line):
            saved_rows.append({
                "id": int(match.group(1)),
                "trajectory": int(match.group(2)),
                "plaquette": float(match.group(3)),
            })
        elif match := DONE_RE.match(line):
            done = {
                "saved": int(match.group(1)),
                "planned_trajectories": int(match.group(2)),
                "reported_accept_rate": match.group(3),
                "wall_seconds": float(match.group(4)),
                "seconds_per_trajectory": float(match.group(5)),
            }
    if done is None or len(checkpoint_rows) != 45 or len(saved_rows) != done["saved"]:
        raise RuntimeError("archived record counts do not satisfy the frozen source reconstruction")
    if any(row["planned_trajectories"] != PLAN["parameters_from_run_note"]["planned_trajectories"] for row in checkpoint_rows):
        raise RuntimeError("checkpoint planned-trajectory field changed")
    return checkpoint_rows, saved_rows, done


def infer_count(denominator: int, token: str) -> list[int]:
    """Return all integer counts that reproduce the source's : .3f token."""
    return [count for count in range(denominator + 1) if f"{count / denominator:.3f}" == token]


def reconstruct(checkpoints: list[dict], saved: list[dict], done: dict) -> tuple[list[dict], list[dict], dict]:
    cfg = PLAN["parameters_from_run_note"]
    final_candidates = infer_count(done["planned_trajectories"], done["reported_accept_rate"])
    if len(final_candidates) != 1:
        raise RuntimeError(f"DONE count is ambiguous under the frozen formatting rule: {final_candidates}")
    accepted_total = final_candidates[0]

    checkpoint_counts = []
    for row in checkpoints:
        candidates = infer_count(row["trajectory"], row["reported_cumulative_rate"])
        if len(candidates) != 1:
            raise RuntimeError(f"cumulative count is ambiguous at trajectory {row['trajectory']}: {candidates}")
        row = dict(row)
        row["inferred_cumulative_accepted"] = candidates[0]
        row["inferred_cumulative_rejected"] = row["trajectory"] - candidates[0]
        checkpoint_counts.append(row)

    actual_stop = cfg["thermal"] + 1 + (cfg["max_save"] - 1) * cfg["save_every"]
    if len(saved) != cfg["max_save"] or saved[-1]["id"] != cfg["max_save"] - 1 or saved[-1]["trajectory"] != actual_stop:
        raise RuntimeError("final saved row does not match the documented max-save stop schedule")
    if checkpoints[-1]["trajectory"] >= actual_stop or accepted_total < checkpoint_counts[-1]["inferred_cumulative_accepted"]:
        raise RuntimeError("checkpoint and final aggregate counts are not chronologically compatible")

    windows = []
    previous_n = 0
    previous_accepted = 0
    for row in checkpoint_counts:
        end = row["trajectory"]
        count = row["inferred_cumulative_accepted"]
        accepted = count - previous_accepted
        length = end - previous_n
        if not (0 <= accepted <= length) or accepted < int(row["checkpoint_accept"]):
            raise RuntimeError(f"incompatible cumulative count at checkpoint {end}")
        windows.append({
            "start_trajectory": previous_n + 1,
            "end_trajectory": end,
            "n_trajectories": length,
            "inferred_accepted": accepted,
            "inferred_rejected": length - accepted,
            "acceptance_rate": accepted / length,
            "basis": "cumulative checkpoint difference",
        })
        previous_n, previous_accepted = end, count

    tail_n = actual_stop - previous_n
    tail_accepted = accepted_total - previous_accepted
    if not (0 <= tail_accepted <= tail_n):
        raise RuntimeError("final DONE aggregate is incompatible with last checkpoint and stop trajectory")
    windows.append({
        "start_trajectory": previous_n + 1,
        "end_trajectory": actual_stop,
        "n_trajectories": tail_n,
        "inferred_accepted": tail_accepted,
        "inferred_rejected": tail_n - tail_accepted,
        "acceptance_rate": tail_accepted / tail_n,
        "basis": "DONE aggregate plus source-derived early stop",
    })

    actual_rate = accepted_total / actual_stop
    reported_denominator_rate = accepted_total / done["planned_trajectories"]
    alternative_count_candidates = infer_count(actual_stop, done["reported_accept_rate"])
    if len(alternative_count_candidates) != 1:
        raise RuntimeError(f"DONE token is ambiguous if its denominator was actual stop {actual_stop}: {alternative_count_candidates}")
    alternative_accepted = alternative_count_candidates[0]
    alternative_rate = alternative_accepted / actual_stop
    alternative_tail_accepted = alternative_accepted - checkpoint_counts[-1]["inferred_cumulative_accepted"]
    summary = {
        "classification": "source_assisted_archival_acceptance_reconstruction",
        "logged_checkpoint_count": len(checkpoints),
        "saved_configuration_count": len(saved),
        "last_saved_trajectory": saved[-1]["trajectory"],
        "source_derived_actual_stop_trajectory": actual_stop,
        "planned_trajectory_denominator_in_DONE": done["planned_trajectories"],
        "reported_DONE_rate_token": done["reported_accept_rate"],
        "reconstructed_accepted_count": accepted_total,
        "reconstructed_rejected_count": actual_stop - accepted_total,
        "reconstructed_acceptance_rate_actual_executed": actual_rate,
        "rate_if_using_planned_denominator": reported_denominator_rate,
        "reported_minus_actual_percentage_points": 100 * (reported_denominator_rate - actual_rate),
        "alternative_accepted_count_if_DONE_denominator_was_actual_stop": alternative_accepted,
        "alternative_rejected_count_if_DONE_denominator_was_actual_stop": actual_stop - alternative_accepted,
        "alternative_acceptance_rate_if_DONE_denominator_was_actual_stop": alternative_rate,
        "alternative_accepts_in_final_tail_if_DONE_denominator_was_actual_stop": alternative_tail_accepted,
        "checkpoint_rate_candidates_unique": all(len(infer_count(r["trajectory"], r["reported_cumulative_rate"])) == 1 for r in checkpoints),
        "checkpoint_acc_true_count": sum(row["checkpoint_accept"] for row in checkpoints),
        "checkpoint_acc_rows": len(checkpoints),
        "window_count": len(windows),
        "window_acceptance_rate_min": min(row["acceptance_rate"] for row in windows),
        "window_acceptance_rate_max": max(row["acceptance_rate"] for row in windows),
        "tail_after_last_checkpoint": {
            "start": windows[-1]["start_trajectory"],
            "stop": windows[-1]["end_trajectory"],
            "n": windows[-1]["n_trajectories"],
            "accepted": windows[-1]["inferred_accepted"],
        },
        "run_done_record": done,
        "confidence_interval": None,
        "confidence_interval_note": "Not reported: per-trajectory decisions are absent and no dependence model for acceptance indicators was declared.",
        "limitations": [
            "The run has no per-trajectory source hash; reconstruction assumes the committed pilot/hmc_generate.py formulas match the executed script, as documented in doc/kunshan_dcu_run.md.",
            "Only cumulative counts at sparse checkpoints and window totals are reconstructed; unknown individual accept/reject decisions remain unknown.",
            "The script prints the planned count (900) in DONE even though max_save causes exit after the 100th saved configuration at trajectory 896.",
            "No binomial confidence interval is claimed because the acceptance sequence dependence structure is not established.",
            "This partial archived run does not establish S16T16B identity, gauge-byte identity, thermalization, autocorrelation, or full protocol_v4 F4.",
        ],
    }
    return checkpoint_counts, windows, summary


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def make_plot(checkpoints: list[dict], windows: list[dict], summary: dict, path: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(11, 7.4), constrained_layout=True)
    x = [row["trajectory"] for row in checkpoints] + [summary["source_derived_actual_stop_trajectory"]]
    k = [row["inferred_cumulative_accepted"] for row in checkpoints] + [summary["reconstructed_accepted_count"]]
    rates = [accepted / trajectory for accepted, trajectory in zip(k, x)]
    axes[0].plot(x, rates, "o-", ms=3.5, lw=1.0, color="#2166AC", label="reconstructed cumulative accepted / executed")
    axes[0].scatter([summary["source_derived_actual_stop_trajectory"]],
                    [summary["alternative_acceptance_rate_if_DONE_denominator_was_actual_stop"]],
                    marker="D", s=40, color="#EF8A62", zorder=5,
                    label="sensitivity if DONE denominator was actual stop")
    axes[0].axhline(float(summary["reported_DONE_rate_token"]), color="#B2182B", ls="--", lw=1.2,
                    label="DONE token (uses planned denominator)")
    axes[0].axvline(400, color="#666666", ls=":", lw=1, label="thermal=400 from run note")
    axes[0].axvline(summary["source_derived_actual_stop_trajectory"], color="#4D9221", ls=":", lw=1,
                    label="max-save stop inferred at trajectory 896")
    axes[0].set(xlabel="trajectory", ylabel="cumulative acceptance rate", ylim=(0.94, 1.005),
                title="Source-assisted cumulative acceptance reconstruction")
    axes[0].grid(alpha=0.25)
    axes[0].legend(fontsize=8, ncol=2)

    ends = [row["end_trajectory"] for row in windows]
    block_rates = [row["acceptance_rate"] for row in windows]
    colors = ["#67A9CF" if row["n_trajectories"] == 20 else "#EF8A62" for row in windows]
    axes[1].bar(ends, block_rates, width=13 if max(row["n_trajectories"] for row in windows) == 20 else 10,
                color=colors, edgecolor="white", linewidth=0.35)
    axes[1].axhline(summary["reconstructed_acceptance_rate_actual_executed"], color="#2166AC", ls="--",
                    label=f"overall inferred = {summary['reconstructed_acceptance_rate_actual_executed']:.5f}")
    axes[1].set(xlabel="window end trajectory", ylabel="accepted / window length", ylim=(0.80, 1.02),
                title="Disjoint acceptance totals: 20-trajectory checkpoints, then final 15")
    axes[1].grid(axis="y", alpha=0.25)
    axes[1].legend(fontsize=8)
    axes[1].scatter([windows[-1]["end_trajectory"]],
                    [summary["alternative_accepts_in_final_tail_if_DONE_denominator_was_actual_stop"] / windows[-1]["n_trajectories"]],
                    marker="D", s=38, color="#B2182B", zorder=5,
                    label="alternative final-tail rate (no run source hash)")
    axes[1].legend(fontsize=7.5)
    fig.savefig(path, dpi=175)
    plt.close(fig)


def render_readme(summary: dict, windows: list[dict]) -> str:
    pct = 100 * summary["reconstructed_acceptance_rate_actual_executed"]
    reported = 100 * summary["rate_if_using_planned_denominator"]
    lines = [
        "# Archived HMC acceptance reconstruction (source-assisted)",
        "",
        "**Classification: partial archival reconstruction, not a production receipt.** The log has only 45 cumulative acceptance checkpoints, but their printed three-decimal rates map to unique integer cumulative counts under the formatting logic in the repository's `pilot/hmc_generate.py`. The run note records the generation parameters. No per-trajectory decision is invented.",
        "",
        "## Reconstructed counts",
        "",
        f"- The 45 sparse checkpoints uniquely imply **860 accepted trajectories through trajectory 881**; all 45 logged checkpoint trajectories themselves report `acc=True`.",
        f"- If the current source's `accepted / args.trajectories` formula was used, the `DONE` token `0.972` uniquely implies **875 accepted / planned 900**. Since the loop stopped at trajectory 896, the preferred source-assisted rate is **875/896 = {pct:.3f}%**, with 21 rejections; the printed ratio is **{reported:.3f}%**, lower by {abs(summary['reported_minus_actual_percentage_points']):.3f} percentage points.",
        f"- Without a run-specific source hash, the denominator is not historically proven. If the same `0.972` token instead divided by the actual stop 896, it uniquely implies **{summary['alternative_accepted_count_if_DONE_denominator_was_actual_stop']}/896 = {100*summary['alternative_acceptance_rate_if_DONE_denominator_was_actual_stop']:.3f}%**, with {summary['alternative_rejected_count_if_DONE_denominator_was_actual_stop']} rejections; the final 882–896 segment would contain {summary['alternative_accepts_in_final_tail_if_DONE_denominator_was_actual_stop']}/15 accepts instead of 15/15. The current repository generator and run note favor the planned-denominator interpretation, but cannot rule out the alternative for the historical executable.",
        "- The 44 checkpoint-to-checkpoint windows are 20 trajectories each and contain 17–20 inferred accepts; the terminal window has 15 trajectories. These are aggregate counts, not recovered event positions. See `acceptance_windows.csv`.",
        "",
        "The generator's relevant logic is `accepted += int(acc)`, checkpoint rate `accepted / (traj + 1)`, final rate `accepted / args.trajectories`, and an early `break` once `saved >= args.max_save`. The run settings are documented in `doc/kunshan_dcu_run.md`. The audit records hashes of those files, but the historical run itself contains no source hash; this is therefore source-assisted and conditional on the repository version matching the executed version.",
        "",
        "## Plot and interpretation",
        "",
        "![Cumulative and windowed HMC acceptance reconstruction](hmc_acceptance_reconstruction.png)",
        "",
        "The top panel compares the preferred source-assisted cumulative rate with the `DONE` token and marks the alternative denominator interpretation. The bottom panel shows disjoint window counts inferred from rounded cumulative checkpoints; diamonds mark the alternative final-window rate. Bar heights are descriptive and do not reveal which unlogged trajectories were rejected. We do not report a binomial confidence interval because the raw event sequence and an independence/dependence model are unavailable.",
        "",
        "## Limits and next work",
        "",
        "This improves on the old statement that the acceptance numerator is unreconstructable, but it remains weaker than a receipt generated by the exact historical executable: no run-specific source hash or all 896 decisions are present. The log still lacks per-trajectory ΔH, and HMC ensemble identity / gauge-byte hashes conflict with other local manifests. It does not declare a thermalization cut or τ_int rule and does not identify the run as protocol_v4 `S16T16B`. Keep F4 `PARTIAL`/`NOT_RUN` until authoritative gauge-byte/source identity and full trajectory evidence are recovered or a new frozen production run is made.",
        "",
        "Verify input and output hashes and independently derived integer counts with `python -B -m tasks.wilson_loop.hmc_acceptance_reconstruction verify`.",
    ]
    return "\n".join(lines) + "\n"


def prepare() -> None:
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite {OUT}")
    OUT.mkdir(parents=True)
    record = frozen_protocol()
    (OUT / "protocol.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"prepared": str(OUT.relative_to(ROOT)), "protocol_sha256": record["protocol_sha256"]}, indent=2))


def execute() -> None:
    protocol_path = OUT / "protocol.json"
    protocol = json.loads(protocol_path.read_text())
    if protocol != frozen_protocol():
        raise RuntimeError("input/source hashes or frozen protocol changed after prepare")
    names = ("acceptance_checkpoints.csv", "acceptance_windows.csv", "summary.json", "hmc_acceptance_reconstruction.png", "README.md")
    if any((OUT / name).exists() for name in names):
        raise FileExistsError("output already exists; preserve it and use a new versioned directory")
    checkpoints, saved, done = parse_inputs()
    checkpoint_counts, windows, summary = reconstruct(checkpoints, saved, done)
    write_csv(OUT / "acceptance_checkpoints.csv", checkpoint_counts, [
        "trajectory", "planned_trajectories", "checkpoint_accept", "reported_cumulative_rate",
        "inferred_cumulative_accepted", "inferred_cumulative_rejected", "plaquette", "delta_h", "seconds",
    ])
    write_csv(OUT / "acceptance_windows.csv", windows, [
        "start_trajectory", "end_trajectory", "n_trajectories", "inferred_accepted",
        "inferred_rejected", "acceptance_rate", "basis",
    ])
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    make_plot(checkpoint_counts, windows, summary, OUT / "hmc_acceptance_reconstruction.png")
    (OUT / "README.md").write_text(render_readme(summary, windows))
    artifacts = (*names, "protocol.json")
    provenance = {
        "schema": "hmc-acceptance-reconstruction-provenance-v1",
        "protocol_sha256": protocol["protocol_sha256"],
        "input_sha256": protocol["input_sha256"],
        "generator_sha256": protocol["source_sha256"],
        "artifact_sha256": {name: sha256(OUT / name) for name in artifacts},
        "checkpoint_rows": len(checkpoint_counts),
        "window_rows": len(windows),
        "source_run_identity": "not independently bound; source-assisted only",
        "status": "PARTIAL_SOURCE_ASSISTED_RECONSTRUCTION",
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: summary[key] for key in (
        "source_derived_actual_stop_trajectory", "reconstructed_accepted_count",
        "reconstructed_rejected_count", "reconstructed_acceptance_rate_actual_executed",
        "rate_if_using_planned_denominator", "reported_minus_actual_percentage_points",
    )}, indent=2))


def verify() -> None:
    protocol = json.loads((OUT / "protocol.json").read_text())
    if protocol != frozen_protocol():
        raise RuntimeError("frozen protocol/current input hash mismatch")
    provenance = json.loads((OUT / "provenance.json").read_text())
    if provenance["protocol_sha256"] != protocol["protocol_sha256"]:
        raise RuntimeError("protocol hash mismatch")
    for name, expected in provenance["artifact_sha256"].items():
        if sha256(OUT / name) != expected:
            raise RuntimeError(f"artifact hash mismatch: {name}")
    checkpoints, saved, done = parse_inputs()
    checkpoint_counts, windows, summary = reconstruct(checkpoints, saved, done)
    disk_summary = json.loads((OUT / "summary.json").read_text())
    if summary != disk_summary:
        raise RuntimeError("reconstructed summary differs from saved result")
    if len(checkpoint_counts) != 45 or len(windows) != 46 or summary["reconstructed_accepted_count"] != 875 or summary["alternative_accepted_count_if_DONE_denominator_was_actual_stop"] != 871 or summary["source_derived_actual_stop_trajectory"] != 896:
        raise RuntimeError("derived counts or row totals failed their expected consistency checks")
    print(json.dumps({"verification": "PASS", "checkpoints": len(checkpoint_counts), "windows": len(windows),
                      "accepted_if_planned_denominator": 875, "accepted_if_actual_denominator": 871,
                      "executed_trajectories": 896,
                      "classification": "source-assisted partial reconstruction"}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "execute", "verify"))
    args = parser.parse_args()
    {"prepare": prepare, "execute": execute, "verify": verify}[args.mode]()


if __name__ == "__main__":
    main()
