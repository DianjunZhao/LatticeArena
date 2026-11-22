"""Create a zoomed view of saved family-wise calibration rates."""
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path("results/pion_projection/familywise_score_cpu_20261120_v2")
METHODS = (
    "absolute_pointwise_t",
    "absolute_bonferroni_t",
    "absolute_max_t_bootstrap",
    "relative_pointwise_t",
    "relative_bonferroni_t",
    "relative_max_t_bootstrap",
)
LABELS = (
    "Abs pointwise",
    "Abs Bonferroni",
    "Abs max-t",
    "Relative pointwise",
    "Relative Bonferroni",
    "Relative max-t",
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    summary_path = ROOT / "familywise_score_summary.json"
    summary = json.loads(summary_path.read_text())
    scenarios = (
        "gaussian_boundary_null",
        "heavy_tail_boundary_null",
        "one_dataset_outlier_boundary_null",
    )
    titles = ("Gaussian boundary", "Heavy-tail boundary", "One outlier")
    colors = ("#bd634e", "#d99b57", "#4d7c9f", "#8d6c9f", "#57917d", "#385f7f")
    fig, ax = plt.subplots(figsize=(10, 5.3))
    x = np.arange(len(scenarios))
    width = 0.115
    for j, (method, label, color) in enumerate(zip(METHODS, LABELS, colors)):
        rates, err_low, err_high = [], [], []
        for scenario in scenarios:
            record = summary["scenario_results"][scenario][method]["familywise_false_certification"]
            lo, hi = record["cp95"]
            rates.append(record["rate"])
            err_low.append(record["rate"] - lo)
            err_high.append(hi - record["rate"])
        ax.bar(
            x + (j - 2.5) * width,
            rates,
            width,
            color=color,
            label=label,
            yerr=np.asarray([err_low, err_high]),
            capsize=3,
        )
    ax.axhline(0.05, color="black", linestyle="--", linewidth=1.2, label="Nominal 5%")
    ax.set_xticks(x, titles)
    ax.set_ylim(0, 0.08)
    ax.set_ylabel("Any boundary-null candidate falsely certified")
    ax.set_title("Family-wise false certification at the 5% improvement boundary")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False, ncol=2)
    fig.tight_layout()
    target = ROOT / "familywise_calibration_zoom.png"
    fig.savefig(target, dpi=190)
    plt.close(fig)
    (ROOT / "figure_review_provenance.json").write_text(json.dumps({
        "summary_sha256": sha256(summary_path),
        "protocol_sha256": sha256(ROOT / "protocol.json"),
        "plot_sha256": sha256(target),
        "plot_source_sha256": sha256(Path(__file__).resolve()),
        "description": "Zoomed family-wise event-rate figure; same counts and CP intervals as familywise_score_summary.json.",
    }, indent=2, sort_keys=True) + "\n")
    print(target)


if __name__ == "__main__":
    main()
