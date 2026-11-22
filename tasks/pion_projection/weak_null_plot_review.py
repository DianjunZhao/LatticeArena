"""Create a display-only, layout-reviewed figure from the frozen weak-null summary."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results/pion_projection/weak_null_nonexchangeable_20261120_v1"
SUMMARY = RESULTS / "summary.json"
OUTPUT = RESULTS / "weak_null_size_power_review.png"
REPORT = RESULTS / "PLOT_REVIEW.md"
PROVENANCE = RESULTS / "plot_review_provenance.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cell(summary: dict, world: str, nblocks: int, method: str) -> dict:
    return next(c for c in summary["cells"]
                if c["world"] == world and c["nblocks"] == nblocks and c["method"] == method)


def render(summary: dict) -> None:
    colors = {
        "paired_t": "#4477AA",
        "raw_studentized_signflip": "#EE6677",
        "centered_wild_signflip_t": "#228833",
        "block_bootstrap_percentile": "#AA3377",
        "mom_known_variance_bound": "#66CCEE",
    }
    labels = {
        "paired_t": "Paired t",
        "raw_studentized_signflip": "Raw sign-flip",
        "centered_wild_signflip_t": "Centered wild t",
        "block_bootstrap_percentile": "Block bootstrap",
        "mom_known_variance_bound": "MoM + known variance bound",
    }
    methods = tuple(labels)
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.8))
    size_ax, power_ax = axes
    null_cells = [
        ("symmetric_gaussian_null", 24, "Gaussian\nN=24"),
        ("rare_tail_weak_null", 24, "Weak null\nN=24"),
        ("symmetric_gaussian_null", 48, "Gaussian\nN=48"),
        ("rare_tail_weak_null", 48, "Weak null\nN=48"),
    ]
    x = np.arange(len(null_cells))
    width = 0.14
    offsets = (np.arange(len(methods)) - (len(methods) - 1) / 2) * width
    for mi, method in enumerate(methods):
        values = np.asarray([cell(summary, world, nblocks, method)["rate"]
                             for world, nblocks, _ in null_cells])
        lows = np.asarray([cell(summary, world, nblocks, method)["cp95_pointwise"][0]
                           for world, nblocks, _ in null_cells])
        highs = np.asarray([cell(summary, world, nblocks, method)["cp95_pointwise"][1]
                            for world, nblocks, _ in null_cells])
        size_ax.bar(x + offsets[mi], values, width=width, color=colors[method], alpha=0.9)
        size_ax.errorbar(x + offsets[mi], values,
                         yerr=np.asarray([values - lows, highs - values]),
                         fmt="none", ecolor="black", capsize=2, linewidth=0.8)
    size_ax.axhline(0.05, color="black", linestyle="--", linewidth=1.2)
    size_ax.set(xticks=x, xticklabels=[label for _, _, label in null_cells],
                ylabel="False-certification rate", ylim=(0, 0.195),
                title="Equal-mean nulls: symmetry changes")
    size_ax.grid(axis="y", alpha=0.22)

    alt_world = "rare_tail_improvement_1p5"
    alt_ns = (24, 48)
    xp = np.arange(len(alt_ns))
    line_offsets = (np.arange(len(methods)) - (len(methods) - 1) / 2) * 0.035
    for mi, method in enumerate(methods):
        values = np.asarray([cell(summary, alt_world, nblocks, method)["rate"] for nblocks in alt_ns])
        lows = np.asarray([cell(summary, alt_world, nblocks, method)["cp95_pointwise"][0] for nblocks in alt_ns])
        highs = np.asarray([cell(summary, alt_world, nblocks, method)["cp95_pointwise"][1] for nblocks in alt_ns])
        power_ax.errorbar(xp + line_offsets[mi], values,
                          yerr=np.asarray([values - lows, highs - values]),
                          marker="o", capsize=3, color=colors[method], linewidth=1.7)
    power_ax.set(xticks=xp, xticklabels=["N=24", "N=48"], ylabel="Certification power",
                 ylim=(0, 1.04), title="Strong-effect power: mean improvement = 1.5 SD")
    power_ax.grid(axis="y", alpha=0.22)

    fig.suptitle("Pion block-risk certificate: weak-null tail stress test", y=0.99, fontsize=15)
    fig.text(0.5, 0.955, "N=3000 outer datasets per cell; error bars are pointwise exact 95% Monte Carlo intervals.",
             ha="center", va="top", fontsize=9)
    handles = [plt.Line2D([0], [0], color=colors[m], linewidth=7, label=labels[m]) for m in methods]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, 0.015), columnspacing=2.0, handlelength=1.5)
    fig.tight_layout(rect=(0, 0.13, 1, 0.91))
    fig.savefig(OUTPUT, dpi=170)
    plt.close(fig)


def report(summary: dict, original_plot_sha256: str) -> None:
    lines = [
        "# Plot review: weak-null tail stress test",
        "",
        "The original analysis image had overlapping footer text and legend. This display-only review redraws the same frozen `summary.json`; it does not rerun the simulation, change any rate, interval, threshold, dataset, or protocol.",
        "",
        f"- Frozen summary SHA-256: `{sha256(SUMMARY)}`",
        f"- Original analysis image SHA-256: `{original_plot_sha256}`",
        f"- Reviewed image SHA-256: `{sha256(OUTPUT)}`",
        "- Data source: the 30-cell summary with exact pointwise Monte Carlo CP95 intervals and the 3000 outer datasets per cell.",
        "",
        "![Reviewed weak-null size and power figure](weak_null_size_power_review.png)",
        "",
        "The left panel shows that four plug-in/resampling procedures rise to roughly 9.4–16.6% false certification in the declared rare-tail mean-zero world, while they are near 5.5–7.0% in the Gaussian control. The right panel shows the deliberately strong +1.5 SD alternative; the known-variance MoM bound has 94.8% and 99.9% power at 24 and 48 blocks. This caption describes only this synthetic generator and the exact frozen summary.",
    ]
    REPORT.write_text("\n".join(lines) + "\n")


def run() -> None:
    if OUTPUT.exists() or REPORT.exists() or PROVENANCE.exists():
        raise FileExistsError("plot review outputs already exist; refusing overwrite")
    summary = json.loads(SUMMARY.read_text())
    original_plot = RESULTS / "weak_null_size_power.png"
    original_plot_sha256 = sha256(original_plot)
    render(summary)
    report(summary, original_plot_sha256)
    PROVENANCE.write_text(json.dumps({
        "classification": "display-only redraw; no simulation or summary changes",
        "summary_sha256": sha256(SUMMARY),
        "source_sha256": sha256(Path(__file__).resolve()),
        "original_analysis_plot_sha256": original_plot_sha256,
        "reviewed_plot_sha256": sha256(OUTPUT),
        "review_report_sha256": sha256(REPORT),
    }, indent=2, sort_keys=True) + "\n")
    print("wrote", OUTPUT.relative_to(ROOT))


def verify() -> None:
    provenance = json.loads(PROVENANCE.read_text())
    if sha256(SUMMARY) != provenance["summary_sha256"]:
        raise RuntimeError("frozen summary changed")
    if sha256(Path(__file__).resolve()) != provenance["source_sha256"]:
        raise RuntimeError("plot-review source changed")
    if sha256(RESULTS / "weak_null_size_power.png") != provenance["original_analysis_plot_sha256"]:
        raise RuntimeError("original plot changed")
    if sha256(OUTPUT) != provenance["reviewed_plot_sha256"]:
        raise RuntimeError("reviewed plot changed")
    if sha256(REPORT) != provenance["review_report_sha256"]:
        raise RuntimeError("review report changed")
    print("plot-review verification: PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("run", "verify"))
    action = parser.parse_args().action
    if action == "run":
        run()
    else:
        verify()


if __name__ == "__main__":
    main()
