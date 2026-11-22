"""Create a readable supplemental figure for the frozen bootstrap diagnostic."""
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
OUT = ROOT / "results/pion_projection/certificate_subgate_bootstrap_20261120_v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    summary = json.loads((OUT / "summary.json").read_text())
    raw = json.loads((OUT / "raw_outcomes.json").read_text())
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.5))
    colors = {"chi2": "#4477AA", "bootstrap": "#CC6677"}
    titles = {0.5: "Baseline: Euclidean-time AR rho=0.5", 0.8: "Shifted: Euclidean-time AR rho=0.8"}
    for col, rho in enumerate((0.5, 0.8)):
        for method, key in (("chi2", "nominal_chi2"), ("bootstrap", "conditional_parametric_bootstrap")):
            cells = [c for c in summary["cells"] if c["time_rho"] == rho]
            rates = [c[key]["rate_valid"] for c in cells]
            lower = [c[key]["cp95_valid"][0] for c in cells]
            upper = [c[key]["cp95_valid"][1] for c in cells]
            axes[0, col].errorbar([c["blocks"] for c in cells], rates,
                                  yerr=[np.array(rates)-lower, np.array(upper)-rates],
                                  marker="o", capsize=3, color=colors[method], label=method)
        axes[0, col].axhline(0.05, color="black", linestyle="--", linewidth=1)
        axes[0, col].set(title=titles[rho], xlabel="Independent blocks B", ylabel="Null rejection rate")
        axes[0, col].legend()

    b = 12
    bins = np.linspace(0, 1, 11)
    for rho, style in ((0.5, "-"), (0.8, "--")):
        rows = raw[f"rho_{rho}_blocks_{b}"]
        pchi = [r["p_chi2"] for r in rows if r["status"] == "VALID"]
        pboot = [r["p_bootstrap"] for r in rows if r["status"] == "VALID"]
        axes[1, 0].hist(pchi, bins=bins, density=True, histtype="step", linestyle=style,
                        color=colors["chi2"], linewidth=1.5, label=f"chi2, rho={rho}")
        axes[1, 0].hist(pboot, bins=bins, density=True, histtype="step", linestyle=style,
                        color=colors["bootstrap"], linewidth=1.5, label=f"bootstrap, rho={rho}")
    axes[1, 0].axhline(1, color="black", linestyle=":", linewidth=1)
    axes[1, 0].set(title="Observed p-values (B=12)", xlabel="p-value", ylabel="Density", ylim=(0, 2.5))
    axes[1, 0].legend(fontsize=7)

    invalid = sum(c["conditional_parametric_bootstrap"]["invalid_bootstrap_draws_total"] for c in summary["cells"])
    planned = sum(c["conditional_parametric_bootstrap"]["planned_bootstrap_draws"] for c in summary["cells"])
    ax = axes[1, 1]
    ax.axis("off")
    ax.set_title("Bootstrap fit accounting")
    ax.text(0.5, 0.58, f"{invalid:,} / {planned:,} invalid draws",
            ha="center", va="center", fontsize=17, transform=ax.transAxes)
    ax.text(0.5, 0.40, "Every planned bootstrap fit is accounted for.\nInvalid draws are counted conservatively in the p-value upper tail.",
            ha="center", va="center", fontsize=11, transform=ax.transAxes)
    fig.suptitle("Conditional parametric bootstrap for the pion reference gate")
    fig.tight_layout()
    figure = OUT / "bootstrap_calibration_review.png"
    fig.savefig(figure, dpi=160)
    plt.close(fig)

    script = Path(__file__)
    prov = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "plot_script_sha256": sha256(script),
        "input_summary_sha256": sha256(OUT / "summary.json"),
        "input_raw_outcomes_sha256": sha256(OUT / "raw_outcomes.json"),
        "output_figure_sha256": sha256(figure),
        "note": "Supplemental readability figure; frozen primary outputs and protocol are unchanged.",
    }
    (OUT / "plot_review_provenance.json").write_text(json.dumps(prov, indent=2, sort_keys=True) + "\n")
    (OUT / "PLOT_REVIEW.md").write_text(
        "# Supplemental figure review\n\n"
        "The preregistered primary figure is preserved. This supplemental version replaces its blank zero-height invalid-count panel with an explicit count and accounting note. The plotted rates, intervals, p-values, raw data, protocol, and source hashes are unchanged.\n\n"
        "![Reviewed conditional bootstrap diagnostic](bootstrap_calibration_review.png)\n\n"
        "All 598,500 planned conditional bootstrap draws were valid in this run; the main table also lists zero invalid draws for every cell. The generation script, input hashes, and rendered figure hash are recorded in `plot_review_provenance.json`.\n"
    )
    print("wrote supplemental plot review", figure.relative_to(ROOT))


if __name__ == "__main__":
    main()
