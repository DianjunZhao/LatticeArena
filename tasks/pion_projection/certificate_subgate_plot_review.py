"""Readable post-run figure for the frozen chi-square subgate MC outputs.

This script reads the already frozen raw outcomes only; it does not rerun or
change any inferential calculation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/pion_projection/certificate_subgate_mc_20261120_v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    summary_path = OUT / "summary.json"
    raw_path = OUT / "raw_outcomes.json"
    summary = json.loads(summary_path.read_text())
    raw = json.loads(raw_path.read_text())
    blocks = (6, 12, 24)
    scenarios = ("ground_state_null", "single_cosh_misspecified", "pure_excited_wrong_state")
    labels = {
        "ground_state_null": "Ground-state null",
        "single_cosh_misspecified": "Single-cosh mismatch",
        "pure_excited_wrong_state": "Pure E1 world",
    }
    colors = {
        "ground_state_null": "#4477AA",
        "single_cosh_misspecified": "#CC6677",
        "pure_excited_wrong_state": "#228833",
    }
    by_key = {(c["scenario"], c["blocks_per_dataset"]): c for c in summary["cells"]}

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
    for n_blocks, color, label in ((6, "#4477AA", "6 blocks"), (12, "#EE6677", "12 blocks"),
                                   (24, "#228833", "24 blocks")):
        pvals = [r["p_value"] for r in raw[f"ground_state_null/blocks_{n_blocks}"] if r["p_value"] is not None]
        axes[0].hist(pvals, bins=np.linspace(0, 1, 11), density=True, histtype="step", linewidth=2,
                     color=color, label=label)
    axes[0].axhline(1.0, color="black", ls="--", lw=1, label="Uniform reference")
    axes[0].set(title="Null p-value distribution", xlabel="Reference-gate p-value", ylabel="Density")
    axes[0].legend(frameon=False, fontsize=8)

    offsets = {"ground_state_null": -0.16, "single_cosh_misspecified": 0.0,
               "pure_excited_wrong_state": 0.16}
    markers = {6: "o", 12: "s", 24: "^"}
    for scenario in scenarios:
        xs, ys, lows, highs = [], [], [], []
        for n_blocks in blocks:
            cell = by_key[(scenario, n_blocks)]
            xs.append(n_blocks + offsets[scenario])
            ys.append(cell["reject_rate_all"])
            lows.append(cell["reject_rate_all_cp95"][0])
            highs.append(cell["reject_rate_all_cp95"][1])
        axes[1].errorbar(xs, ys, yerr=[np.array(ys) - lows, np.array(highs) - ys],
                         marker="o", color=colors[scenario], capsize=3, linewidth=1.5,
                         label=labels[scenario])
    axes[1].axhline(0.05, color="black", ls="--", lw=1, label="Nominal 5%")
    axes[1].set(title="Subgate rejection rate", xlabel="Independent blocks per dataset",
                ylabel="Rejection fraction (all planned datasets)", xticks=list(blocks))
    axes[1].legend(frameon=False, fontsize=8)

    wrong = [by_key[("pure_excited_wrong_state", n)] for n in blocks]
    rates = np.array([c["pass_rate_all"] for c in wrong])
    lo = np.array([c["pass_rate_all_cp95"][0] for c in wrong])
    hi = np.array([c["pass_rate_all_cp95"][1] for c in wrong])
    axes[2].errorbar(list(blocks), rates, yerr=[rates - lo, hi - rates], fmt="o-",
                     color=colors["pure_excited_wrong_state"], capsize=3)
    axes[2].set(title="Pure-E1 world passes the fit gate", xlabel="Independent blocks per dataset",
                ylabel="Acceptance fraction", xticks=list(blocks), ylim=(0, 1.02))
    fig.suptitle("χ² reference subgate: calibration, sensitivity, and state ambiguity")
    fig.tight_layout()
    figure = OUT / "subgate_calibration_diagnostic_review.png"
    fig.savefig(figure, dpi=170)
    plt.close(fig)

    inputs = {"summary.json": sha256(summary_path), "raw_outcomes.json": sha256(raw_path)}
    receipt = {
        "classification": "post-run presentation-only review; no statistics recomputed",
        "source_sha256": sha256(Path(__file__).resolve()),
        "input_sha256": inputs,
        "output_sha256": sha256(figure),
        "cells": len(summary["cells"]),
        "datasets_per_cell": summary["n_independent_datasets_per_cell"],
        "note": "The original frozen diagnostic figure is preserved; this supplemental version shortens labels and separates type-I rejection, alternative sensitivity, and pure-E1 acceptance.",
    }
    (OUT / "plot_review_provenance.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    review = """# Figure review: Pion chi-square subgate MC

The frozen simulation and statistics are unchanged. The original plot is preserved as the preregistered artifact. Its x-axis labels were too long to read clearly, so this supplemental figure uses shortened scenario labels and separates null rejection, misspecification sensitivity, and pure-E1 acceptance.

![Readable subgate diagnostic](subgate_calibration_diagnostic_review.png)

The right panel highlights the structural limit: a pure-E1 dataset can increasingly pass a single-cosh fit as the number of blocks grows. This fit-quality subgate does not identify the state as the ground state.

The figure is reproduced with `python -B -m tasks.pion_projection.certificate_subgate_plot_review`. Input and output hashes are in `plot_review_provenance.json`.
"""
    (OUT / "PLOT_REVIEW.md").write_text(review)
    print("wrote", figure.relative_to(ROOT))


if __name__ == "__main__":
    main()
