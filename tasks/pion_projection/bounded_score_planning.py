"""Dimensionless planning curves for the bounded paired-block score.

This is a deterministic sensitivity calculation, not a Monte Carlo run and
not a source of physical mass-range or anchor-error values.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np


BLOCK_COUNTS = (12, 24, 100, 400)
FAMILIES = (1, 2, 4)
ANCHORS = (("exact", 0.05, 0.0), ("uncertain", 0.04, 0.01))
BETA_GRID = np.linspace(0.0, 0.5, 101)  # beta = B/R; dimensionless
BETA_EDGES = np.linspace(0.0, 0.5, 102)
DEFAULT_OUT = (Path(__file__).resolve().parents[2]
               / "results/pion_projection/bounded_score_planning_20261121_v1")


def _valid_integer(value: int, label: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < minimum:
        raise ValueError(f"{label} must be an integer >= {minimum}")
    return int(value)


def required_normalized_effect(blocks: int, family: int, alpha_s: float,
                               beta: float) -> float:
    """Return the excess signal d/R^2 needed for a positive lower bound.

    With R=u-l, beta=B/R, and eta=delta_star/R^2, certification requires
    E[d]/R^2 - eta > sqrt(2 log(F/alpha_s)/n) + 2 beta.
    """
    n = _valid_integer(blocks, "blocks", 1)
    f = _valid_integer(family, "family", 1)
    if (not math.isfinite(alpha_s) or not 0 < alpha_s < 1
            or not math.isfinite(beta) or beta < 0):
        raise ValueError("alpha_s must be in (0,1) and beta must be finite/nonnegative")
    return math.sqrt(2.0 * math.log(f / alpha_s) / n) + 2.0 * beta


def minimum_blocks(normalized_excess_signal: float, family: int,
                   alpha_s: float, beta: float) -> int | None:
    """Smallest integer n making the Hoeffding/anchor penalty strictly smaller.

    Return None when the anchor term alone is at least as large as the signal.
    """
    f = _valid_integer(family, "family", 1)
    if (not math.isfinite(normalized_excess_signal) or normalized_excess_signal <= 0
            or not math.isfinite(alpha_s) or not 0 < alpha_s < 1
            or not math.isfinite(beta) or beta < 0):
        raise ValueError("signal, alpha_s, or beta outside the supported domain")
    remaining = normalized_excess_signal - 2.0 * beta
    if remaining <= 0:
        return None
    crossing = 2.0 * math.log(f / alpha_s) / (remaining * remaining)
    return math.floor(crossing) + 1  # strict inequality: n must exceed crossing


def _plot(path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n = np.asarray(BLOCK_COUNTS, dtype=float)
    # Geometric edges keep the discrete planned n values legible on a log axis.
    edges = np.sqrt(n[:-1] * n[1:])
    x_edges = np.concatenate(([n[0] ** 2 / edges[0]], edges,
                              [n[-1] ** 2 / edges[-1]]))
    fig, axes = plt.subplots(2, 3, figsize=(12, 7), sharex=True, sharey=True,
                             layout="constrained")
    last = None
    for row, (anchor_name, alpha_s, alpha_a) in enumerate(ANCHORS):
        for col, family in enumerate(FAMILIES):
            z = np.asarray([
                [required_normalized_effect(int(count), family, alpha_s, float(beta))
                 for count in BLOCK_COUNTS]
                for beta in BETA_GRID
            ])
            ax = axes[row, col]
            last = ax.pcolormesh(x_edges, BETA_EDGES, z, shading="flat",
                                 cmap="viridis")
            ax.set_xscale("log")
            ax.set_xticks(BLOCK_COUNTS, [str(x) for x in BLOCK_COUNTS])
            ax.set_title(f"{anchor_name} anchor, F={family}")
            ax.set_xlabel("independent blocks n")
            ax.grid(axis="x", alpha=0.18)
            if col == 0:
                ax.set_ylabel(r"relative anchor bound $\beta=B/R$")
    fig.colorbar(last, ax=axes, label=r"required $(\bar d-\delta_*)/R^2$", shrink=0.92)
    fig.suptitle("Bounded block-MSE: deterministic sample-size and anchor sensitivity\n"
                 "dimensionless planning map only; no physical bounds assumed")
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plan(output: str | Path = DEFAULT_OUT) -> dict:
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    rows = []
    for anchor_name, alpha_s, alpha_a in ANCHORS:
        for family in FAMILIES:
            for n in BLOCK_COUNTS:
                rows.append({
                    "anchor": anchor_name,
                    "alpha_s": alpha_s,
                    "alpha_a": alpha_a,
                    "family": family,
                    "blocks": n,
                    "required_excess_over_threshold_at_beta_0":
                        required_normalized_effect(n, family, alpha_s, 0.0),
                    "required_excess_over_threshold_at_beta_0_05":
                        required_normalized_effect(n, family, alpha_s, 0.05),
                    "beta_0_05_is_illustrative_only": True,
                })
    source = Path(__file__)
    summary = {
        "classification": "deterministic dimensionless sensitivity; no physical calibration",
        "formula": "required (mean_d-delta_star)/R^2 = sqrt(2 log(F/alpha_s)/n) + 2 B/R",
        "anchor_allocations": [
            {"name": name, "alpha_s": a_s, "alpha_a": a_a}
            for name, a_s, a_a in ANCHORS
        ],
        "block_counts": list(BLOCK_COUNTS),
        "families": list(FAMILIES),
        "rows": rows,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    _plot(out / "planning_map.png")
    report = [
        "# Bounded block-MSE planning sensitivity",
        "",
        "**Deterministic formula analysis; no new Monte Carlo data and no physical values assumed.**",
        "",
        "For loss range width `R=u-l`, block-difference range `[-R^2,R^2]`,",
        "`F` fixed candidates, statistical error allocation `alpha_s`, anchor bias bound `B`,",
        "and practical threshold `delta_star`, the lower-bound rule is",
        "",
        "```text",
        "L = d_bar - R^2*sqrt(2*log(F/alpha_s)/n) - 2*B*R",
        "certify only if L > delta_star",
        "```",
        "",
        "Writing `beta=B/R` and `g=(d_bar-delta_star)/R^2` makes the planning condition",
        "`g > sqrt(2*log(F/alpha_s)/n) + 2*beta`. The image shows this required normalized",
        "signal across the previously used `n=12/24/100/400` and `F=1/2/4` grid, for the",
        "exact-anchor and uncertain-anchor allocations from the frozen calibration.",
        "The color surface is a deterministic consequence of the bound, not a simulated",
        "power curve or a claim that any plotted `beta` is physically plausible.",
        "",
        "![Dimensionless bounded-score planning map](planning_map.png)",
        "",
        "As `n` grows, only the statistical term falls; the anchor floor `2B/R` remains.",
        "If the normalized effect gap `g` is no larger than `2B/R`, no block count can",
        "make this certificate positive. When `g>2B/R`, the smallest integer block count",
        "is `floor(2*log(F/alpha_s)/(g-2B/R)^2)+1`.",
        "",
        "The table in `summary.json` includes `beta=0.05` only as a labeled algebraic",
        "example to make the anchor penalty visible; it is not a recommended or measured",
        "physical anchor error. Select `R`, `B`, `delta_star`, and `g` from an approved",
        "Pion observable/normalization contract before using the formula for sample-size",
        "planning. The [504000-dataset synthetic calibration](../bounded_score_calibration_20261121_v1/README.md)",
        "remains a separate conditional calibration; this sensitivity map does not",
        "repair the failed reference gate, establish block independence, or create a",
        "physical score.",
    ]
    (out / "README.md").write_text("\n".join(report) + "\n")
    hashes = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (out / "README.md", out / "summary.json", out / "planning_map.png")
    }
    (out / "artifact_hashes.json").write_text(json.dumps(hashes, indent=2) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    result = plan(args.output)
    print(json.dumps({"output": str(args.output), "rows": len(result["rows"]),
                      "classification": result["classification"]}))


if __name__ == "__main__":
    main()
