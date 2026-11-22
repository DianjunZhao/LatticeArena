"""Render compact heatmaps for the frozen independent GEVP expansion."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/pion_projection/gevp_ground_failure_expanded_20261120_v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    summary = json.loads((OUT / "summary.json").read_text())
    rows = summary["cells"]
    ylabels = [f"noise={r['noise']}, gap={r['gap']}, t0={r['t0']}" for r in rows if r["cutoff"] == 1e-8]
    cutoffs = [1e-8, 1e-5]
    coverage = np.array([[next(r["coverage"] for r in rows if r["noise"] == n and r["gap"] == g and r["t0"] == t and r["cutoff"] == c)
                          for c in cutoffs]
                         for n, g, t in [(0.01,0.1,1),(0.01,0.1,2),(0.01,0.5,1),(0.01,0.5,2),
                                         (0.05,0.1,1),(0.05,0.1,2),(0.05,0.5,1),(0.05,0.5,2)]])
    bias = np.array([[next(r["bias_mean"] for r in rows if r["noise"] == n and r["gap"] == g and r["t0"] == t and r["cutoff"] == c)
                      for c in cutoffs]
                     for n, g, t in [(0.01,0.1,1),(0.01,0.1,2),(0.01,0.5,1),(0.01,0.5,2),
                                     (0.05,0.1,1),(0.05,0.1,2),(0.05,0.5,1),(0.05,0.5,2)]])
    outer_failures = sum(r["n_outer_failures"] for r in rows)
    local_failures = sum(sum(r["failure_reasons"].values()) for r in rows)
    coverage_nonzero = int(np.count_nonzero(coverage))
    se_range = (min(r["mean_within_dataset_bootstrap_se"] for r in rows),
                max(r["mean_within_dataset_bootstrap_se"] for r in rows))

    fig, axes = plt.subplots(1, 2, figsize=(14, 7.5), sharey=True, gridspec_kw={"width_ratios": [1, 1]})
    im0 = axes[0].imshow(coverage, vmin=0, vmax=.05, cmap="Blues", aspect="auto")
    axes[0].set(title="Coverage zoom: 0–5%\nnominal 95% is off scale", xlabel="Cutoff", ylabel="Noise / gap / t0")
    axes[0].set_xticks(range(2), ["1e-8", "1e-5"])
    axes[0].set_yticks(range(8), ylabels, fontsize=8)
    for i in range(coverage.shape[0]):
        for j in range(coverage.shape[1]):
            axes[0].text(j, i, f"{coverage[i,j]*100:.1f}%", ha="center", va="center",
                         color="white" if coverage[i,j] > .025 else "black", fontsize=8)
    fig.colorbar(im0, ax=axes[0], fraction=.045, pad=.03, label="Coverage fraction")

    im1 = axes[1].imshow(bias, cmap="YlOrRd", aspect="auto")
    axes[1].set(title="Mean bias (lattice units)", xlabel="Cutoff", ylabel="Noise / gap / t0")
    axes[1].set_xticks(range(2), ["1e-8", "1e-5"])
    axes[1].set_ylabel("")
    axes[1].tick_params(axis="y", labelleft=False, left=False)
    for i in range(bias.shape[0]):
        for j in range(bias.shape[1]):
            axes[1].text(j, i, f"{bias[i,j]:.4f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im1, ax=axes[1], fraction=.045, pad=.03, label="Bias")

    fig.suptitle("Independent N=400/cell GEVP replication")
    fig.text(.5, .015,
             f"{summary['total_independent_datasets']:,} independent datasets; coverage > 0 in {coverage_nonzero}/16 cells (max {coverage.max()*100:.1f}%); "
             f"outer failures={outer_failures}, recorded GEVP failure events={local_failures}; "
             f"mean bias={bias.min():.4f}–{bias.max():.4f}, mean within-dataset bootstrap SE={se_range[0]:.5f}–{se_range[1]:.5f}.",
             ha="center", va="bottom", fontsize=10)
    fig.tight_layout()
    fig.subplots_adjust(bottom=.13, top=.88, wspace=.28)
    out_image = OUT / "gevp_coverage_bias_review.png"
    fig.savefig(out_image, dpi=160)
    plt.close(fig)

    provenance = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "plot_script_sha256": sha256(Path(__file__)),
        "input_summary_sha256": sha256(OUT / "summary.json"),
        "output_figure_sha256": sha256(out_image),
        "note": "Supplemental readability plot; frozen primary outputs and outcomes are unchanged.",
    }
    (OUT / "plot_review_provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    (OUT / "PLOT_REVIEW.md").write_text(
        "# Supplemental GEVP figure review\n\n"
        "The preregistered primary plot is retained. This supplemental version replaces long 16-cell x-axis labels with coverage and bias heatmaps, displays the low-coverage range explicitly, and includes failure accounting. All 16 cells have zero outer failures and zero recorded GEVP failure events; coverage is nonzero in 4 cells and never exceeds 4.0%. The plot script, input summary hash, and image hash are in `plot_review_provenance.json`.\n\n"
        "![Reviewed expanded GEVP diagnostic](gevp_coverage_bias_review.png)\n"
    )
    print("wrote supplemental plot review", out_image.relative_to(ROOT))


if __name__ == "__main__":
    main()
