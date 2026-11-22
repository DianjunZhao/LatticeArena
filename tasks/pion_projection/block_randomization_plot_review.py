"""Readable post-run plots for the frozen block-randomization summary.

This utility only rearranges existing summary/raw outcomes; it does not rerun
the simulation or change any test, threshold, estimate, or interval.
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
RUN = ROOT / "results/pion_projection/block_randomization_score_20261120_v1"
OUT = RUN / "plot_review"
METHODS = ("block_signflip_studentized", "paired_block_t", "paired_block_bootstrap")
COLORS = {METHODS[0]: "#228833", METHODS[1]: "#4477AA", METHODS[2]: "#CC6677"}
METHOD_LABELS = {METHODS[0]: "Studentized sign-flip", METHODS[1]: "Paired block t",
                 METHODS[2]: "Paired block bootstrap"}
NULL_WORLDS = ("equal_gaussian_null", "common_truth_shift_null",
               "equal_student_t5_null", "uncertain_anchor_null")
WORLD_CODES = {"equal_gaussian_null": "G", "common_truth_shift_null": "S",
               "equal_student_t5_null": "T", "uncertain_anchor_null": "A"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cell(summary: dict, world: str, rho: float, method: str, bias: float = 0.0) -> dict:
    return next(x for x in summary["cells"] if x["world"] == world and x["arm_correlation"] == rho
                and x["method"] == method and x["anchor_bias"] == bias)


def contrast(summary: dict, world: str, rho: float, method: str, bias: float = 0.0) -> dict:
    return next(x for x in summary["method_contrasts"] if x["world"] == world
                and x["arm_correlation"] == rho and x["method"] == method and x["anchor_bias"] == bias)


def plot_main(summary: dict, path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(18, 6.2))
    ax = axes[0]
    categories = [(world, rho) for world in NULL_WORLDS for rho in (0.5, 0.9)]
    x = np.arange(len(categories))
    offsets = {METHODS[0]: -0.19, METHODS[1]: 0.0, METHODS[2]: 0.19}
    for method in METHODS:
        values, low, high = [], [], []
        for world, rho in categories:
            c = cell(summary, world, rho, method)
            values.append(c["rate_planned"])
            low.append(c["cp95_familywise"][0])
            high.append(c["cp95_familywise"][1])
        values = np.asarray(values)
        ax.errorbar(x + offsets[method], values,
                    yerr=np.asarray([values-np.asarray(low), np.asarray(high)-values]),
                    marker="o", capsize=2.5, linewidth=1.3, color=COLORS[method],
                    label=METHOD_LABELS[method])
    ax.axhline(0.05, color="black", linestyle=":", linewidth=1)
    ax.set(xticks=x, xticklabels=[f"{WORLD_CODES[w]}\nρ={rho:.1f}" for w, rho in categories],
           ylabel="False-certification rate", title="Null size (familywise CP95)")
    ax.tick_params(axis="x", labelsize=8)
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(axis="y", alpha=0.2)

    ax = axes[1]
    for method in METHODS:
        for rho, linestyle, shift in ((0.5, "--", -0.0008), (0.9, "-", 0.0008)):
            vals, low, high = [], [], []
            for bias in (-0.02, 0.0, 0.02):
                c = cell(summary, "equal_gaussian_null", rho, method, bias)
                vals.append(c["rate_planned"])
                low.append(c["cp95_familywise"][0])
                high.append(c["cp95_familywise"][1])
            vals = np.asarray(vals)
            ax.errorbar(np.asarray([-0.02, 0.0, 0.02])+shift, vals,
                        yerr=np.asarray([vals-np.asarray(low), np.asarray(high)-vals]),
                        marker="o", markersize=4, linestyle=linestyle, linewidth=1.2,
                        capsize=2, color=COLORS[method],
                        label=f"{METHOD_LABELS[method]}, ρ={rho:.1f}")
    ax.axhline(0.05, color="black", linestyle=":", linewidth=1)
    ax.set(xlabel="Fixed anchor offset", ylabel="False-certification rate",
           title="Anchor sensitivity (familywise CP95)")
    ax.legend(fontsize=7, ncol=2)
    ax.grid(alpha=0.2)

    ax = axes[2]
    x = np.arange(2)
    offsets = {METHODS[0]: -0.12, METHODS[1]: 0.0, METHODS[2]: 0.12}
    for method in METHODS:
        vals, low, high = [], [], []
        for rho in (0.5, 0.9):
            c = cell(summary, "known_lower_noise", rho, method)
            vals.append(c["rate_planned"])
            low.append(c["cp95_familywise"][0])
            high.append(c["cp95_familywise"][1])
        vals = np.asarray(vals)
        ax.errorbar(x+offsets[method], vals,
                    yerr=np.asarray([vals-np.asarray(low), np.asarray(high)-vals]),
                    marker="o", capsize=3, color=COLORS[method],
                    label=METHOD_LABELS[method])
    ax.set(xticks=x, xticklabels=["ρ=0.5", "ρ=0.9"],
           ylabel="Certification rate", title="Known lower-noise power (familywise CP95)")
    ax.tick_params(axis="x", labelsize=8)
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(axis="y", alpha=0.2)
    fig.suptitle("Pion C3 block randomization: readable view of frozen results", fontsize=15)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_paired_differences(summary: dict, path: Path) -> None:
    comparisons = (("paired_block_t", "Paired block t − sign-flip", "#4477AA"),
                   ("paired_block_bootstrap", "Paired block bootstrap − sign-flip", "#CC6677"))
    fig, axes = plt.subplots(1, 2, figsize=(16, 6.5))
    cases = [[(world, rho) for world in NULL_WORLDS for rho in (0.5, 0.9)],
             [("known_lower_noise", rho) for rho in (0.5, 0.9)]]
    titles = ["Null certification-rate difference", "Known-improvement power difference"]
    for ax, selected_cases, title in zip(axes, cases, titles):
        x = np.arange(len(selected_cases))
        for j, (method, label, color) in enumerate(comparisons):
            vals, low, high = [], [], []
            for world, rho in selected_cases:
                c = contrast(summary, world, rho, method)
                vals.append(100*c["rate_difference"])
                ci = c["familywise_dataset_bootstrap_ci95"]
                low.append(100*ci[0])
                high.append(100*ci[1])
            vals = np.asarray(vals)
            offset = -0.10 if j == 0 else 0.10
            ax.errorbar(x+offset, vals,
                        yerr=np.asarray([vals-np.asarray(low), np.asarray(high)-vals]),
                        marker="o", capsize=2.5, color=color, label=label)
        ax.axhline(0, color="black", linestyle=":", linewidth=1)
        labels = [f"{WORLD_CODES.get(w, 'Imp.')}\nρ={rho:.1f}" for w, rho in selected_cases]
        ax.set(xticks=x, xticklabels=labels, ylabel="Paired rate difference (percentage points)",
               title=title)
        ax.tick_params(axis="x", labelsize=8)
        ax.grid(axis="y", alpha=0.2)
        ax.legend(fontsize=8)
    fig.suptitle("Paired method contrasts with familywise dataset-bootstrap CI95", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def render_report(summary: dict, plot_main_name: str, plot_diff_name: str,
                  source_hash: str, protocol_file_hash: str, protocol_fingerprint: str,
                  execution_provenance_hash: str, raw_hash: str, summary_hash: str,
                  main_hash: str, diff_hash: str) -> str:
    def fmt_ci(interval: list[float]) -> str:
        return f"[{100*interval[0]:.2f}, {100*interval[1]:.2f}] pp"

    lines = [
        "# Block-randomization diagnostics: plot review",
        "",
        "This companion report only reformats the frozen `summary.json` and raw outcomes. It does not rerun datasets, change a method or threshold, or recalculate any interval. The original preregistered result directory and hashes remain unchanged.",
        "",
        f"- Main figure: [`{plot_main_name}`]({plot_main_name})",
        f"- Paired contrast figure: [`{plot_diff_name}`]({plot_diff_name})",
        f"- Canonical frozen-protocol fingerprint: `{protocol_fingerprint}`; protocol JSON file SHA256: `{protocol_file_hash}`",
        f"- Execution provenance SHA256: `{execution_provenance_hash}`",
        f"- Raw outcomes SHA256: `{raw_hash}`; summary SHA256: `{summary_hash}`",
        f"- Plot-review script SHA256: `{source_hash}`",
        f"- Main figure SHA256: `{main_hash}`; paired contrast figure SHA256: `{diff_hash}`",
        "",
        "## Interpretation",
        "",
        "Figure label codes: G = equal-Gaussian null; S = common truth-shift null; T = equal Student-t5 null; A = uncertain-anchor null; Imp. = known lower-noise alternative.",
        "",
        "The studentized sign-flip test is theoretically exact for the declared sharp null of independently sampled paired blocks that are exchangeable under swapping arm labels, with the pooled reference held invariant. The 400-dataset/cell Monte Carlo results are compatible with nominal 5% in the displayed cells, but the familywise intervals remain too broad to certify close calibration. The estimated power is only 10.0% at arm noise correlation 0.5 and 21.0% at 0.9 for the declared lower-noise alternative.",
        "",
        "At zero anchor offset, sign-flip and paired-t certification rates are close. Relative to sign-flip, the paired-t rate differences in the two lower-noise cells are -0.25 pp "
        + fmt_ci(contrast(summary, "known_lower_noise", 0.5, "paired_block_t")["familywise_dataset_bootstrap_ci95"])
        + " and +0.25 pp "
        + fmt_ci(contrast(summary, "known_lower_noise", 0.9, "paired_block_t")["familywise_dataset_bootstrap_ci95"])
        + "; both intervals include zero. The paired-block bootstrap has higher estimated power by +6.00 pp "
        + fmt_ci(contrast(summary, "known_lower_noise", 0.5, "paired_block_bootstrap")["familywise_dataset_bootstrap_ci95"])
        + " and +5.75 pp "
        + fmt_ci(contrast(summary, "known_lower_noise", 0.9, "paired_block_bootstrap")["familywise_dataset_bootstrap_ci95"])
        + ". It also certifies more often in equal-Gaussian null cells (+1.50 pp at ρ=0.5 and +3.00 pp at ρ=0.9); the latter paired CI is "
        + fmt_ci(contrast(summary, "equal_gaussian_null", 0.9, "paired_block_bootstrap")["familywise_dataset_bootstrap_ci95"])
        + ". Higher certification is not evidence of better calibration.",
        "",
        "The anchor-offset curves vary across cells, with wide familywise intervals; they do not establish monotonicity or a robust-score correction. Common truth shift is a relative-effect null under shared model/anchor misspecification, so passing it only supports no detectable arm difference under that generator. No method detects common model/state bias by design.",
        "",
        "All 4,000 outer dataset/correlation cases produced valid block fits; anchor-offset reuse yields 7,200 rows. These are synthetic CPU results, not physical coverage. The experiment cannot establish validity for weak nulls with nonexchangeable arms, gauge-ensemble autocorrelation, or a full-ensemble `improvement_certificate` estimand. Keep physical score `null` until an independent production anchor is available.",
        "",
        "![Readable null, anchor, and power diagnostics](" + plot_main_name + ")",
        "",
        "![Paired method contrasts](" + plot_diff_name + ")",
        "",
        "The next decision should remain the independent physical anchor / held-out measurement in `tasks/pion_projection/todo.md`; do not select a production score from these same calibration outcomes.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite {OUT}")
    OUT.mkdir(parents=True)
    summary_path = RUN / "summary.json"
    raw_path = RUN / "raw_outcomes.json"
    protocol_path = RUN / "protocol.json"
    preregistration_path = RUN / "preregistration.json"
    execution_provenance_path = RUN / "execution_provenance.json"
    summary = json.loads(summary_path.read_text())
    preregistration = json.loads(preregistration_path.read_text())
    main_name, diff_name = "readable_diagnostics.png", "paired_method_differences.png"
    main_path, diff_path = OUT / main_name, OUT / diff_name
    plot_main(summary, main_path)
    plot_paired_differences(summary, diff_path)
    report = render_report(summary, main_name, diff_name, sha256(Path(__file__)),
                           sha256(protocol_path), preregistration["protocol_sha256"],
                           sha256(execution_provenance_path), sha256(raw_path), sha256(summary_path),
                           sha256(main_path), sha256(diff_path))
    (OUT / "PLOT_REVIEW.md").write_text(report)
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
