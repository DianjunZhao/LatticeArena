"""Post-process the frozen CPU operator-initializer run into amortized costs.

This is descriptive only: it neither regenerates synthetic data nor modifies
the source run. It separates one-time training/selection cost from deployment
wall time and pairs cost with the risk contrasts already stored in raw.json.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = Path("results/optimize_gaussian/cpu_operator_initializer_v1")
RAW = SOURCE_DIR / "raw.json"
PREREG = SOURCE_DIR / "preregistration.json"
OUT = Path("results/optimize_gaussian/cpu_initializer_amortization_v1")
SCHEMA = "optgauss-initializer-amortization-v1"
POPULATIONS = ("iid", "shift")
METHODS = ("learned", "zero_random", "spectral")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def path_hash(relative: str | Path) -> str | None:
    path = ROOT / relative
    return sha256(path.read_bytes()) if path.is_file() else None


def read_raw() -> dict:
    return json.loads((ROOT / RAW).read_text())


def build_protocol() -> dict:
    return {
        "schema": SCHEMA,
        "purpose": "Descriptive one-time training plus repeated deployment cost calculation.",
        "source_raw_sha256": path_hash(RAW),
        "source_preregistration_sha256": path_hash(PREREG),
        "analysis_script_sha256": path_hash("tasks/optimize_gaussian/initializer_amortization.py"),
        "formula": {
            "learned_total_seconds": "training_and_selection_seconds + N * mean_learned_wall_seconds",
            "baseline_total_seconds": "N * mean_baseline_wall_seconds",
            "break_even_deployments": "ceil(training_seconds / (baseline_mean - learned_mean)) if baseline_mean > learned_mean",
        },
        "groups": {
            "populations": list(POPULATIONS),
            "budgets": [25, 100, 400],
            "methods": list(METHODS),
            "expected_rows_per_group": 40,
        },
        "interpretation": [
            "No Monte Carlo data are generated or altered.",
            "Single-host CPU wall times are descriptive and are not GPU or physical costs.",
            "No confidence interval is placed on timing means.",
            "Positive comparator-minus-learned risk differences mean lower risk for the learned initializer in the source synthetic benchmark.",
        ],
    }


def build_summary() -> dict:
    raw = read_raw()
    training = float(raw["training_and_selection_seconds"])
    rows = raw["rows"]
    paired = raw["paired"]
    paired_map = {
        (row["population"], int(row["budget"]), row["comparator"]): row
        for row in paired
    }
    groups = []
    for population in POPULATIONS:
        for budget in (25, 100, 400):
            times = {}
            counts = {}
            for method in METHODS:
                selected = [
                    float(row["wall_seconds"])
                    for row in rows
                    if row["population"] == population
                    and int(row["budget"]) == budget
                    and row["method"] == method
                ]
                if len(selected) != 40:
                    raise RuntimeError(
                        f"expected 40 timing rows for {population}/{budget}/{method}, got {len(selected)}"
                    )
                times[method] = {
                    "mean_seconds": float(np.mean(selected)),
                    "median_seconds": float(np.median(selected)),
                }
                counts[method] = len(selected)
            break_even = {}
            for comparator in ("zero_random", "spectral"):
                delta = times[comparator]["mean_seconds"] - times["learned"]["mean_seconds"]
                break_even[comparator] = (
                    int(math.ceil(training / delta)) if delta > 0 else None
                )
            risk = {}
            for comparator in ("zero_random", "spectral"):
                source = paired_map[(population, budget, comparator)]
                risk[comparator] = {
                    "comparator_minus_learned": float(source["delta"]),
                    "ci95": [float(x) for x in source["ci95"]],
                }
            groups.append(
                {
                    "population": population,
                    "budget": budget,
                    "n_per_method": counts,
                    "training_and_selection_seconds": training,
                    "deployment_wall_seconds": times,
                    "break_even_deployments": break_even,
                    "paired_risk": risk,
                }
            )
    return {
        "schema": SCHEMA,
        "classification": "exploratory_postprocess_of_frozen_synthetic_cpu_run",
        "source": SOURCE_DIR.as_posix(),
        "training_and_selection_seconds": training,
        "groups": groups,
        "limitations": [
            "The source run has 40 test links per population and budget; timing estimates are descriptive.",
            "The training cost is amortized over repeated deployments under the same synthetic task and is not a physical production cost estimate.",
            "The shifted population changes epsilon only and is not a general gauge-ensemble distribution shift.",
            "The learned method predicts coefficients for a fixed operator family; it is not a trained smear kernel W.",
            "The spectral comparator is the source run's feasible clipped polynomial fit, not an optimally constrained Chebyshev solver.",
            "The source test datasets are already observed and are not a blind physical evaluation.",
        ],
    }


def write_csv(path: Path, summary: dict) -> None:
    fields = [
        "population",
        "budget",
        "n_per_method",
        "training_and_selection_seconds",
        "learned_mean_ms",
        "learned_median_ms",
        "zero_random_mean_ms",
        "zero_random_median_ms",
        "spectral_mean_ms",
        "spectral_median_ms",
        "break_even_vs_zero_random",
        "break_even_vs_spectral",
        "zero_random_minus_learned_risk",
        "zero_random_risk_ci95",
        "spectral_minus_learned_risk",
        "spectral_risk_ci95",
    ]
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for group in summary["groups"]:
            times = group["deployment_wall_seconds"]
            risk = group["paired_risk"]
            writer.writerow(
                {
                    "population": group["population"],
                    "budget": group["budget"],
                    "n_per_method": 40,
                    "training_and_selection_seconds": group["training_and_selection_seconds"],
                    "learned_mean_ms": 1000 * times["learned"]["mean_seconds"],
                    "learned_median_ms": 1000 * times["learned"]["median_seconds"],
                    "zero_random_mean_ms": 1000 * times["zero_random"]["mean_seconds"],
                    "zero_random_median_ms": 1000 * times["zero_random"]["median_seconds"],
                    "spectral_mean_ms": 1000 * times["spectral"]["mean_seconds"],
                    "spectral_median_ms": 1000 * times["spectral"]["median_seconds"],
                    "break_even_vs_zero_random": group["break_even_deployments"]["zero_random"],
                    "break_even_vs_spectral": group["break_even_deployments"]["spectral"],
                    "zero_random_minus_learned_risk": risk["zero_random"]["comparator_minus_learned"],
                    "zero_random_risk_ci95": json.dumps(risk["zero_random"]["ci95"]),
                    "spectral_minus_learned_risk": risk["spectral"]["comparator_minus_learned"],
                    "spectral_risk_ci95": json.dumps(risk["spectral"]["ci95"]),
                }
            )


def write_plot(path: Path, summary: dict) -> None:
    deployments = np.logspace(0, 5, 240)
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 7.4), sharex=True, sharey=True)
    colors = {"learned": "#2463a6", "zero_random": "#d07c18", "spectral": "#388153"}
    labels = {
        "learned": "learned + one-time training",
        "zero_random": "zero/random SLSQP",
        "spectral": "fixed spectral baseline",
    }
    for ax, group in zip(axes.flat, summary["groups"]):
        times = group["deployment_wall_seconds"]
        train = group["training_and_selection_seconds"]
        ax.plot(
            deployments,
            train + deployments * times["learned"]["mean_seconds"],
            color=colors["learned"],
            label=labels["learned"],
            linewidth=2.0,
        )
        ax.plot(
            deployments,
            deployments * times["zero_random"]["mean_seconds"],
            color=colors["zero_random"],
            label=labels["zero_random"],
            linewidth=1.8,
        )
        ax.plot(
            deployments,
            deployments * times["spectral"]["mean_seconds"],
            color=colors["spectral"],
            label=labels["spectral"],
            linewidth=1.8,
        )
        cross = group["break_even_deployments"]["zero_random"]
        if cross is not None:
            ax.axvline(cross, color="#666666", linestyle=":", linewidth=1)
        population = group["population"]
        pop_label = "IID" if population == "iid" else "epsilon-shift"
        ax.set_title(f"{pop_label}, budget={group['budget']}")
        ax.text(
            0.04,
            0.95,
            f"break-even vs SLSQP: {cross:,}" if cross else "no SLSQP crossover",
            transform=ax.transAxes,
            va="top",
            fontsize=8.5,
        )
        ax.grid(True, which="both", alpha=0.22)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("number of repeated deployments")
        ax.set_ylabel("total CPU wall time (s)")
    fig.suptitle(
        "One-time training amortization on the frozen H/B initializer CPU benchmark",
        fontsize=13,
    )
    handles, legend_labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc="lower center", ncol=3, frameon=False)
    fig.tight_layout(rect=(0, 0.08, 1, 0.95))
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def render_readme(summary: dict) -> str:
    rows = []
    for group in summary["groups"]:
        times = group["deployment_wall_seconds"]
        risk = group["paired_risk"]
        iid = group["population"] == "iid"
        pop = "IID" if iid else "epsilon-shift"
        be_slsqp = group["break_even_deployments"]["zero_random"]
        be_spectral = group["break_even_deployments"]["spectral"]
        be_spectral_label = "none" if be_spectral is None else f"{be_spectral:,}"
        rows.append(
            f"| {pop} | {group['budget']} | "
            f"{times['learned']['mean_seconds']*1000:.3f} / {times['learned']['median_seconds']*1000:.3f} | "
            f"{times['zero_random']['mean_seconds']*1000:.3f} / {times['zero_random']['median_seconds']*1000:.3f} | "
            f"{times['spectral']['mean_seconds']*1000:.3f} / {times['spectral']['median_seconds']*1000:.3f} | "
            f"{be_slsqp:,} | {be_spectral_label} | "
            f"{risk['zero_random']['comparator_minus_learned']:.6f} "
            f"[{risk['zero_random']['ci95'][0]:.6f},{risk['zero_random']['ci95'][1]:.6f}] | "
            f"{risk['spectral']['comparator_minus_learned']:.6f} "
            f"[{risk['spectral']['ci95'][0]:.6f},{risk['spectral']['ci95'][1]:.6f}] |"
        )
    return f"""# Learned initializer CPU cost amortization

**Classification: exploratory post-processing of frozen synthetic data. No simulation was rerun and the source results were not modified.**

## Calculation

The source run reports one-time training and selection cost of **{summary['training_and_selection_seconds']:.3f} CPU seconds**. For N later deployments, this report uses

    T_learned(N) = T_train_and_select + N × mean learned deployment wall time
    T_baseline(N) = N × mean baseline deployment wall time

The break-even count is the first integer N at which the learned method's amortized total CPU time is no greater than zero/random SLSQP. This is a direct arithmetic transform of the frozen per-case wall times, not a statistical estimate. Timing summaries are means and medians over 40 already-observed test links per cell; no timing confidence interval is claimed.

## Cost and paired-risk table

Times are mean / median milliseconds per deployment. Risk is comparator minus learned; positive values mean the learned initializer had lower error in the source run. Risk intervals are copied from that run's paired-bootstrap summary and are not recalculated here.

| Population | Objective-call budget | Learned ms mean / median | SLSQP ms mean / median | Spectral ms mean / median | Break-even deployments vs SLSQP | vs spectral | SLSQP risk delta [CI95] | Spectral risk delta [CI95] |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
{chr(10).join(rows)}

![Total CPU time versus repeated deployments](cost_amortization.png)

The vertical dotted line in each panel marks the estimated break-even against zero/random SLSQP. No crossover against the spectral baseline occurs in these cells because its measured mean deployment time is below the learned method's; a learned model's training cost cannot be amortized against a method that is already cheaper per deployment under this timing setup.

## Interpretation and limits

- Compared with zero/random SLSQP, the initializer has lower mean deployment time in all six population/budget cells, but amortizing its 1.339-second training/selection cost requires roughly **192–5,203 repeated deployments**, depending on budget and population.
- Compared with the spectral baseline, there is no CPU-time break-even. The paired-risk results also vary by population: the spectral baseline slightly outperforms the initializer in IID cells, while the initializer has lower risk in the epsilon-shift cells. This is an accuracy-cost trade-off in the declared toy benchmark, not evidence that either method dominates.
- At high budgets, the source results report lower held-out error for SLSQP than for the learned initializer. At low budgets, an initializer can improve the fixed-budget optimization path; this supports an amortized warm-start hypothesis only.
- The source test links were already observed. The shift changes epsilon only; the spectral implementation is a feasible clipped polynomial fit, not an optimally constrained Chebyshev solver. CPU timings do not predict GPU training or inference cost.
- This is not a learned smear kernel, not a trainable-W test, and not physical evidence. The next decisive comparison remains a fresh-gauge blind run with matched objective-call and walltime budgets, Gaussian, SLSQP, and a stronger spectral baseline.

Frozen source: [CPU operator initializer report](../cpu_operator_initializer_v1/README.md). Reproduce this descriptive calculation with:

    python3 -B -m tasks.optimize_gaussian.initializer_amortization run

Verify the frozen inputs and output hashes with:

    python3 -B -m tasks.optimize_gaussian.initializer_amortization verify
"""


def output_hashes(directory: Path) -> dict[str, str]:
    return {
        path.name: sha256(path.read_bytes())
        for path in sorted(directory.iterdir())
        if path.is_file() and path.name != "provenance.json"
    }


def run() -> None:
    directory = ROOT / OUT
    if directory.exists():
        raise FileExistsError(directory)
    protocol = build_protocol()
    summary = build_summary()
    directory.mkdir(parents=True)
    (directory / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")
    (directory / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    write_csv(directory / "costs.csv", summary)
    write_plot(directory / "cost_amortization.png", summary)
    (directory / "README.md").write_text(render_readme(summary))
    provenance = {
        "protocol_sha256": sha256((directory / "protocol.json").read_bytes()),
        "outputs_sha256": output_hashes(directory),
    }
    (directory / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(f"wrote {OUT}")
    print(f"training_and_selection_seconds={summary['training_and_selection_seconds']:.6f}")
    for group in summary["groups"]:
        print(
            group["population"],
            group["budget"],
            group["break_even_deployments"],
        )


def verify() -> None:
    directory = ROOT / OUT
    protocol_path = directory / "protocol.json"
    provenance_path = directory / "provenance.json"
    if not protocol_path.is_file() or not provenance_path.is_file():
        raise FileNotFoundError("frozen protocol or provenance is missing")
    protocol = json.loads(protocol_path.read_text())
    if protocol != build_protocol():
        raise RuntimeError("frozen source inputs changed")
    provenance = json.loads(provenance_path.read_text())
    if provenance.get("protocol_sha256") != sha256(protocol_path.read_bytes()):
        raise RuntimeError("protocol hash mismatch")
    if provenance.get("outputs_sha256") != output_hashes(directory):
        raise RuntimeError("output hash mismatch")
    summary = json.loads((directory / "summary.json").read_text())
    if summary != build_summary():
        raise RuntimeError("recomputed summary differs from frozen output")
    print(json.dumps({
        "verification": "PASS",
        "groups": len(summary["groups"]),
        "source_rows": sum(group["n_per_method"]["learned"] for group in summary["groups"]),
        "output_files": len(provenance["outputs_sha256"]),
        "classification": summary["classification"],
    }, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("run", "verify"))
    args = parser.parse_args()
    ({"run": run, "verify": verify}[args.mode])()


if __name__ == "__main__":
    main()
