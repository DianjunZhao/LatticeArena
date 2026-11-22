"""Finalize the frozen C3 anchor expansion after Matplotlib API drift.

The preregistered analysis completed all dataset calculations but the installed
Matplotlib rejected the old ``labels=`` boxplot keyword. This reviewer rebuilds
only the visualization and provenance artifacts; raw outcomes and summaries
are read-only.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from . import anchor_calibration_expanded as analysis


ROOT = Path(__file__).resolve().parents[2]
OUT = analysis.OUT


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    protocol = json.loads((OUT / "protocol.json").read_text())
    prereg = json.loads((OUT / "preregistration.json").read_text())
    raw = json.loads((OUT / "raw_outcomes.json").read_text())
    summary = json.loads((OUT / "summary.json").read_text())
    if hashlib.sha256(analysis.canonical(protocol)).hexdigest() != prereg["protocol_sha256"]:
        raise RuntimeError("frozen protocol hash mismatch")
    if analysis.source_manifest() != prereg["source_sha256"]:
        raise RuntimeError("frozen analysis source hash mismatch")
    if len(raw) != protocol["n_independent_datasets_per_scenario"] * len(protocol["scenarios"]):
        raise RuntimeError("raw dataset count mismatch")

    names = [item["name"] for item in summary["scenarios"]]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
    x = np.arange(len(names))
    for vals_key, ci_key, shift, label, color in (
        ("naive_pseudorep_rate", "naive_familywise_cp95", -.08, "Naive sd/sqrt(Nboot)", "#CC6677"),
        ("single_dataset_paired_rate", "paired_familywise_cp95", .08, "Paired 5th percentile", "#4477AA"),
    ):
        vals = np.array([row[vals_key] for row in summary["scenarios"]])
        cis = [row[ci_key] for row in summary["scenarios"]]
        lo = np.array([v - ci[0] for v, ci in zip(vals, cis)])
        hi = np.array([ci[1] - v for v, ci in zip(vals, cis)])
        axes[0].errorbar(x + shift, vals, yerr=[lo, hi], marker="o", capsize=3,
                         label=label, color=color)
    axes[0].axhline(.05, color="black", linestyle="--", linewidth=1, label="5% reference")
    axes[0].set(xticks=x, xticklabels=names, ylabel="Certification frequency",
                title="Across 400 independent datasets")
    axes[0].legend(fontsize=8)

    values = [[row["dataset_delta_mean"] for row in raw
               if row["scenario"] == name and row["status"] == "VALID"] for name in names]
    axes[1].boxplot(values, tick_labels=names, showfliers=False, whis=(2.5, 97.5))
    axes[1].axhline(0, color="black", linestyle="--", linewidth=1)
    axes[1].set(ylabel="Per-dataset paired mean delta",
                title="Independent-repeat dataset outcomes")
    fig.suptitle("C3 anchor interval semantics: independent synthetic expansion")
    fig.tight_layout()
    fig.savefig(OUT / "anchor_expansion.png", dpi=160)
    plt.close(fig)

    (OUT / "README.md").write_text(analysis.render_readme(summary))
    source = Path(__file__)
    review = {
        "reason": "Frozen analysis calculations completed, but final plotting failed because this Matplotlib version rejects the labels= keyword for boxplot.",
        "repair": "Re-rendered only the plot and documentation from frozen summary.json and raw_outcomes.json using tick_labels=.",
        "raw_outcomes_sha256": sha256(OUT / "raw_outcomes.json"),
        "summary_sha256": sha256(OUT / "summary.json"),
        "review_script_sha256": sha256(source),
        "modified_raw_or_summary": False,
    }
    (OUT / "PLOT_REVIEW.md").write_text(
        "# Plot finalization review\n\n"
        "The preregistered dataset calculations completed for all 1,200 planned datasets, "
        "but the original run stopped during figure creation because the installed Matplotlib "
        "version no longer accepts `labels=` in `Axes.boxplot`. The figure and README were "
        "re-rendered from the unchanged raw and summary JSON using `tick_labels=`. No dataset "
        "calculation or result value was changed. Hashes and the repair record are in "
        "`plot_review_provenance.json`.\n"
    )
    (OUT / "plot_review_provenance.json").write_text(json.dumps(review, indent=2, sort_keys=True) + "\n")
    prov = {
        "protocol_sha256": prereg["protocol_sha256"],
        "preregistered_source_sha256": prereg["source_sha256"],
        "current_source_sha256": analysis.source_manifest(),
        "planned_datasets": protocol["n_independent_datasets_per_scenario"] * len(protocol["scenarios"]),
        "completed_datasets": len(raw),
        "planned_bootstrap_mass_fits": (protocol["n_independent_datasets_per_scenario"] *
                                          len(protocol["scenarios"]) *
                                          protocol["n_bootstrap_draws_per_dataset_arm"] * 2),
        "artifact_sha256": {name: sha256(OUT / name) for name in analysis.OUTPUTS},
    }
    (OUT / "execution_provenance.json").write_text(json.dumps(prov, indent=2, sort_keys=True) + "\n")
    print("finalized frozen C3 artifacts from unchanged raw outcomes")


if __name__ == "__main__":
    main()
