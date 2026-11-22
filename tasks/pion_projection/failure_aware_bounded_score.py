"""Analytic failure-policy sensitivity for the bounded block-MSE score.

This module works only with dimensionless planning inputs. It does not read
correlators, infer a physical mass range, or produce a physical score.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "results/pion_projection/bounded_score_failure_policy_20261122_v2"
BLOCK_COUNTS = (12, 24, 100, 400)
FAILURE_FRACTIONS = np.linspace(0.0, 0.25, 101)
FAMILY = 2
ALPHA_S = 0.05


def lower_bound_with_failures(valid_deltas, *, planned_blocks: int,
                              range_width: float, family: int,
                              alpha_s: float, anchor_bound: float = 0.0,
                              failure_policy: str = "worst_case") -> dict:
    """Return a conditional Hoeffding lower bound with an explicit failure rule.

    ``valid_deltas`` are paired per-block improvements computed with the same
    independent anchor. Their range is ``[-range_width**2, +range_width**2]``.
    With ``worst_case``, every missing block is assigned the minimum possible
    improvement, ``-range_width**2``, and the denominator remains the number
    planned. This is a failure-augmented estimand. Its interpretation as a
    bound on the original latent MSE contrast additionally requires every
    failed block to have a well-defined counterfactual paired loss within the
    declared range. If solver failure means no such output exists, this is only
    an operational utility with an explicit failure penalty.

    ``abstain`` returns no bound whenever a planned block is missing. In either
    mode, a provenance/identity or run-wide infrastructure failure must be
    handled by an experiment-level abstention, not per-block imputation.
    """
    values = np.asarray(valid_deltas, dtype=float)
    if values.ndim != 1:
        raise ValueError("valid_deltas must be one-dimensional")
    if (isinstance(planned_blocks, bool)
            or not isinstance(planned_blocks, (int, np.integer))
            or planned_blocks < 1):
        raise ValueError("planned_blocks must be a positive integer")
    if (isinstance(family, bool) or not isinstance(family, (int, np.integer))
            or family < 1):
        raise ValueError("family must be a positive integer")
    if (not np.isfinite([range_width, alpha_s, anchor_bound]).all()
            or range_width <= 0 or not 0 < alpha_s < 1 or anchor_bound < 0):
        raise ValueError("invalid range width, alpha_s, or anchor bound")
    if failure_policy not in ("abstain", "worst_case"):
        raise ValueError("failure_policy must be 'abstain' or 'worst_case'")
    if len(values) > planned_blocks:
        raise ValueError("valid block count exceeds planned_blocks")
    if not np.isfinite(values).all():
        raise ValueError("valid_deltas must be finite")

    r2 = float(range_width) ** 2
    if np.any((values < -r2 - 1e-12) | (values > r2 + 1e-12)):
        raise ValueError("valid_deltas fall outside the declared [-R^2,R^2] range")

    failed = int(planned_blocks - len(values))
    if failed and failure_policy == "abstain":
        return {
            "status": "ABSTAIN_MISSING_BLOCKS",
            "classification": "diagnostic_only",
            "failure_policy": failure_policy,
            "planned_blocks": int(planned_blocks),
            "valid_blocks": int(len(values)),
            "failed_blocks": failed,
            "abstained": True,
            "mean_improvement_all_planned": None,
            "statistical_penalty": None,
            "anchor_penalty": None,
            "lower_bound": None,
        }

    observed_sum = float(values.sum())
    coded_sum = observed_sum - failed * r2
    all_planned_mean = coded_sum / planned_blocks
    statistical_penalty = r2 * math.sqrt(
        2.0 * math.log(int(family) / float(alpha_s)) / int(planned_blocks)
    )
    anchor_penalty = 2.0 * float(anchor_bound) * float(range_width)
    lower = all_planned_mean - statistical_penalty - anchor_penalty
    return {
        "status": "CONDITIONAL_BOUND",
        "classification": "diagnostic_only",
        "failure_policy": failure_policy,
        "planned_blocks": int(planned_blocks),
        "valid_blocks": int(len(values)),
        "failed_blocks": failed,
        "abstained": False,
        "mean_improvement_all_planned": float(all_planned_mean),
        "statistical_penalty": float(statistical_penalty),
        "anchor_penalty": float(anchor_penalty),
        "lower_bound": float(lower),
    }


def required_valid_mean(failure_fraction: float, *, blocks: int,
                        family: int = FAMILY, alpha_s: float = ALPHA_S,
                        relative_anchor_bound: float = 0.0,
                        normalized_threshold: float = 0.0) -> float:
    """Minimum valid-block mean divided by R^2 for a positive threshold margin.

    The analytic boundary solves
    ``(1-phi)*mu_valid - phi - sqrt(2 log(F/alpha_s)/n) - 2 B/R > delta/R^2``.
    This is a sensitivity formula, not an observed rate or recommended policy.
    """
    if (not math.isfinite(failure_fraction) or not 0 <= failure_fraction < 1
            or isinstance(blocks, bool) or not isinstance(blocks, (int, np.integer))
            or blocks < 1 or isinstance(family, bool)
            or not isinstance(family, (int, np.integer)) or family < 1
            or not math.isfinite(alpha_s) or not 0 < alpha_s < 1
            or not math.isfinite(relative_anchor_bound) or relative_anchor_bound < 0
            or not math.isfinite(normalized_threshold)):
        raise ValueError("planning inputs outside supported domain")
    stat = math.sqrt(2.0 * math.log(int(family) / alpha_s) / int(blocks))
    numerator = (normalized_threshold + stat + 2.0 * relative_anchor_bound
                 + failure_fraction)
    return numerator / (1.0 - failure_fraction)


def _plot(path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8.5, 5.5), layout="constrained")
    colors = plt.get_cmap("viridis")(np.linspace(0.12, 0.88, len(BLOCK_COUNTS)))
    for n, color in zip(BLOCK_COUNTS, colors):
        values = [required_valid_mean(phi, blocks=n) for phi in FAILURE_FRACTIONS]
        ax.plot(FAILURE_FRACTIONS, values, color=color, lw=2,
                label=f"n={n} planned blocks")
    ax.axhline(1.0, color="black", ls="--", lw=1.1,
               label=r"maximum possible $\bar d_{valid}/R^2=1$")
    ax.fill_between(FAILURE_FRACTIONS, 1.0, 1.6,
                    where=np.array([required_valid_mean(phi, blocks=12)
                                    for phi in FAILURE_FRACTIONS]) > 1.0,
                    color="#D55E00", alpha=0.08,
                    label="n=12 impossible region")
    ax.set(xlim=(0, 0.25), ylim=(0, 1.6),
           xlabel="planned-block failure fraction  $\\phi$",
           ylabel=r"required valid-block mean  $\bar d_{valid}/R^2$",
           title="Worst-case failure coding: algebraic sensitivity only")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, loc="upper left")
    ax.text(0.99, 0.02,
            r"Illustration: $F=2$, $\alpha_S=0.05$, $B/R=0$, $\delta_*/R^2=0$",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=8)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def build(output: str | Path = DEFAULT_OUT) -> dict:
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    table = []
    for n in BLOCK_COUNTS:
        for phi in (0.0, 0.05, 0.10, 0.20):
            table.append({
                "planned_blocks": n,
                "failure_fraction": phi,
                "family": FAMILY,
                "alpha_s": ALPHA_S,
                "relative_anchor_bound": 0.0,
                "normalized_threshold": 0.0,
                "required_valid_mean_over_R2": required_valid_mean(phi, blocks=n),
                "possible_within_mass_range": required_valid_mean(phi, blocks=n) <= 1.0,
                "interpretation": "illustrative algebra; not a physical or production threshold",
            })
    source_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    design_path = ROOT / "tasks/pion_projection/bounded_score_design_review_20261121.md"
    protocol = {
        "schema": "pion-bounded-score-failure-policy-sensitivity-v1",
        "classification": "deterministic analytic sensitivity; diagnostic_only; physical_score=null",
        "formula": "L/R^2=(1-phi)*mu_valid-phi-sqrt(2*log(F/alpha_s)/n)-2*B/R",
        "decision_boundary": "mu_valid > (delta_star/R^2 + sqrt(2*log(F/alpha_s)/n) + 2*B/R + phi)/(1-phi)",
        "illustration_only": {
            "family": FAMILY,
            "alpha_s": ALPHA_S,
            "relative_anchor_bound": 0.0,
            "normalized_threshold": 0.0,
            "note": "Exact-anchor/zero-threshold illustration is optimistic; none of these values is frozen for Pion.",
        },
        "planned_blocks": list(BLOCK_COUNTS),
        "failure_fraction_grid": [float(x) for x in FAILURE_FRACTIONS],
        "policy_options": {
            "abstain": "Any missing block yields no score; preserves the conditional target but can make the full-run estimand unavailable.",
            "worst_case": "Code each failed block as -R^2 and retain the all-planned denominator; this is a failure-augmented estimand unless latent bounded outcomes exist.",
            "run_wide_or_identity_failure": "Always experiment-level abstention; never per-block imputation.",
        },
        "table": table,
        "source_sha256": source_hash,
        "design_review_sha256": hashlib.sha256(design_path.read_bytes()).hexdigest(),
    }
    (out / "summary.json").write_text(json.dumps(protocol, indent=2) + "\n")
    _plot(out / "failure_sensitivity.png")
    lines = [
        "# Bounded block-MSE: handling failed evaluation blocks",
        "",
        "**Status: analytic design sensitivity only. No correlator, production, GPU, anchor, validation, or holdout input was read. `physical_score=null`.**",
        "",
        "## Scope",
        "",
        "- Goal: make the missing-block rule explicit for the user-accepted bounded block-MSE estimand.",
        "- Inputs: the existing symbolic bound and user-required sealed-data boundary; no measured values.",
        "- Deliverable: two conditional policies, a pure CPU bound function, focused tests, and a dimensionless figure.",
        "- Acceptance: preserve all planned blocks, distinguish estimator failure from identity/run failure, and retain `NOT_READY`.",
        "",
        "## Formula",
        "",
        "Let `N` be planned independent evaluation blocks, `f` failed blocks, `phi=f/N`, `R=u-l`, and `mu_valid=mean(d_j over valid blocks)/R^2`, where `d_j=(b_j-A)^2-(c_j-A)^2`. If each failed block is assigned the minimum possible paired improvement `-R^2`, then the all-planned coded mean is `R^2[(1-phi) mu_valid-phi]`. A conditional one-sided bound is",
        "",
        "```text",
        "L/R^2 = (1-phi)*mu_valid - phi - sqrt(2*log(F/alpha_s)/N) - 2*(B/R)",
        "certify only if L/R^2 > delta_star/R^2",
        "```",
        "",
        "Solving for the valid-block mean gives `mu_valid > (delta_star/R^2 + sqrt(2*log(F/alpha_s)/N) + 2*B/R + phi)/(1-phi)`. At `phi=0`, this reduces to the existing bounded score. For `phi>0`, the missing-block penalty is added without shrinking the planned denominator.",
        "",
        "![Failure-policy sensitivity](failure_sensitivity.png)",
        "",
        "The plotted lines use only an algebraic illustration (`F=2`, `alpha_s=0.05`, `B/R=0`, `delta_star/R^2=0`). The horizontal `mu_valid/R^2=1` line is the largest possible improvement under the bounded range. Lines above it indicate that this illustrative bound cannot become positive, even with the best possible valid blocks. A nonzero anchor bound or practical threshold moves every line upward. At small `N`, failure fractions are discrete multiples of `1/N`; the continuous x-axis is for sensitivity visualization, not simulated observations.",
        "",
        "## Policy comparison and validity boundary",
        "",
        "| Policy | Missing block | Meaning |",
        "|---|---|---|",
        "| Hard abstention | Any planned block missing → no score | Retains the pure conditional MSE target; inference is unavailable for that run. |",
        "| Worst-case coding | Missing block contributes `-R^2`; keep denominator `N` | Defines a failure-augmented operational estimand. It bounds the original latent MSE contrast only if every failed block has a well-defined counterfactual pair inside `[l,u]`. |",
        "| Run-wide or identity failure | Abort the complete comparison | Invalid provenance, split overlap, hash mismatch, or common infrastructure failure is not a random block outcome and must never be imputed. |",
        "",
        "The anchor correction `2BR` is valid only for independently covered anchors and bounded successful block estimates. The Hoeffding term still requires independent planned blocks and a fixed family. If convergence failure means the estimator has no defined output, worst-case coding is a new deployment utility; it must not be described as physical mass MSE. The current D source–sink identity/reference failures remain hard gates.",
        "",
        "## Decision flow",
        "",
        "```text",
        "protocol / split / input identity failure?",
        "  yes -> abort whole comparison; no imputation; physical_score=null",
        "  no  -> block-level method failure?",
        "           none -> use the existing bounded block-MSE rule",
        "           any  -> does a bounded counterfactual estimate exist for every failed block?",
        "                    yes -> worst-case code -R^2; report it as a changed estimand",
        "                    no  -> hard abstain, or approve a separate failure-utility target",
        "```",
        "",
        "This analysis does not choose the Pion mass range, clipping rule, physical block identity, anchor source/bias bound, `delta_star`, or production failure policy. It does not change `single-cosh FAIL`, M2 `ABSTAIN/NOT_READY`, sealed E/D splits, or the physical score. Keep the TODO open until those scientific inputs and measurement-stream identity gates are reviewed.",
        "",
        "Rebuild this deterministic artifact into a new directory with `python3 -B -m tasks.pion_projection.failure_aware_bounded_score --output NEW_DIRECTORY`.",
    ]
    (out / "README.md").write_text("\n".join(lines) + "\n")
    hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (out / "summary.json", out / "failure_sensitivity.png", out / "README.md")
    }
    (out / "artifact_hashes.json").write_text(json.dumps(hashes, indent=2) + "\n")
    return protocol


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    result = build(args.output)
    print(json.dumps({"output": str(args.output), "rows": len(result["table"]),
                      "classification": result["classification"]}))


if __name__ == "__main__":
    main()
