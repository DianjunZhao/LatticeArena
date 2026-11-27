"""Generate a no-data diagnostic for F-lane q/h/x force-budget propagation."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

from .force_budget import (
    COMPONENT_FRACTIONS,
    FORCE_CORNER_COUNT,
    propagate_force_budget,
    uniform_loop_cap,
)


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "results/wilson_loop/force_budget_propagation_cpu_20261125_v1"
CONTRACT = ROOT / "tasks/wilson_loop/lane_contract_v2.json"
CONTRACT_SOURCE = ROOT / "tasks/wilson_loop/lane_contract.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _plot(path: Path, rows: list[dict], naive: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    force = [row["reference_force_lower"] for row in rows]
    colors = {"q": "#1769aa", "h": "#e07a16", "x": "#388e3c"}
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.6))
    for component in ("q", "h", "x"):
        axes[0].plot(
            force,
            [row[f"max_uniform_{component}_loop_bound"] / row["reference_force_lower"]
             for row in rows],
            label=f"{component} per-corner cap / force lower bound",
            color=colors[component], linewidth=2,
        )
    axes[0].set_xscale("log")
    axes[0].set_yscale("log")
    axes[0].set_xlabel(r"positive reference-force lower bound $f_{L}$")
    axes[0].set_ylabel("maximum raw loop bound / $f_L$")
    axes[0].set_title("Input caps implied by force-level budgets")
    axes[0].grid(True, which="both", alpha=0.25)
    axes[0].legend(fontsize=8)

    names = ["q", "h", "x"]
    proposed = [naive["component_relative_bounds"][name] for name in names]
    target = [COMPONENT_FRACTIONS[name] for name in names]
    xpos = list(range(len(names)))
    width = 0.36
    axes[1].bar([x - width / 2 for x in xpos], target, width,
                label="force-level component budget", color="#729fcf")
    axes[1].bar([x + width / 2 for x in xpos], proposed, width,
                label="if 1.5/1.5/1% is used per loop corner", color="#ef6c63")
    axes[1].set_xticks(xpos, names)
    axes[1].set_ylabel("fraction of $f_L$")
    axes[1].set_title("At illustrative $f_L=1$")
    axes[1].grid(True, axis="y", alpha=0.25)
    axes[1].legend(fontsize=8)
    fig.suptitle("F-lane q/h/x propagation: 8 signed loop corners", fontsize=13)
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def build(output_dir: Path = DEFAULT_OUT) -> dict:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")
    output_dir.mkdir(parents=True)
    numerics_source = ROOT / "core/numerics.py"
    (output_dir / "snapshot_core_numerics.py").write_bytes(numerics_source.read_bytes())

    # Formula-only sensitivity. The range is deliberately illustrative; no
    # D-chain value is substituted for the missing positive reference bound.
    force_lowers = [10 ** (-2 + 2 * index / 49) for index in range(50)]
    rows: list[dict] = []
    for reference in force_lowers:
        row = {"reference_force_lower": reference}
        for component, fraction in COMPONENT_FRACTIONS.items():
            cap = uniform_loop_cap(fraction, reference)
            row[f"max_uniform_{component}_loop_bound"] = cap
            row[f"propagated_{component}_force_bound"] = (
                FORCE_CORNER_COUNT * math.log1p(cap)
            )
        rows.append(row)
    with (output_dir / "cap_sensitivity.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    # Reproduce the risky interpretation that the percentages are raw per-loop
    # caps, at a dimensionless reference lower bound of one.
    force_lower = 1.0
    assumed = {
        "q": [[COMPONENT_FRACTIONS["q"] * force_lower] * 4] * 2,
        "h": [[COMPONENT_FRACTIONS["h"] * force_lower] * 4] * 2,
        "x": [[COMPONENT_FRACTIONS["x"] * force_lower] * 4] * 2,
    }
    naive = propagate_force_budget(
        assumed, force_lower,
        model_truncation_bound=0.01 * force_lower,
        statistical_halfwidth=0.05 * force_lower,
    )
    max_caps = {
        component: uniform_loop_cap(fraction, force_lower)
        for component, fraction in COMPONENT_FRACTIONS.items()
    }
    cap_check = propagate_force_budget(
        {name: [[max_caps[name]] * 4] * 2 for name in ("q", "h", "x")},
        force_lower,
        model_truncation_bound=0.01 * force_lower,
        statistical_halfwidth=0.05 * force_lower,
    )
    protocol = {
        "schema": "wilson-force-budget-propagation-diagnostic-v1",
        "purpose": "formula-only translation from loop q/h/x envelopes to candidate-minus-reference force bounds",
        "inputs": {
            "kernel_count": 2,
            "loop_corners_per_kernel": 4,
            "force_corner_count": FORCE_CORNER_COUNT,
            "component_force_fraction_budgets": COMPONENT_FRACTIONS,
            "illustrative_reference_force_lower": force_lower,
            "reference_force_range_for_plot": [force_lowers[0], force_lowers[-1]],
            "assumed_raw_loop_caps_counterexample": COMPONENT_FRACTIONS,
        },
        "formula": {
            "loop_log_envelope": "delta=log(1+q+h+x), for nonnegative q,h,x",
            "force_contrast_bound": "sum over 8 kernel/R/t corners of delta",
            "component_bound": "sum over 8 corners log(1+q_component)",
            "uniform_raw_cap": "expm1(component_fraction * reference_force_lower / 8)",
        },
        "scenario_denominator": {
            "planned": len(rows), "valid": len(rows), "failed": 0, "abstained": 0,
            "meaning": "deterministic formula sensitivity rows; not measurements or Monte Carlo datasets",
        },
        "physical_evidence_denominator": {
            "planned": 1, "valid": 0, "failed": 0, "abstained": 1,
            "reason": "no independent q/h/x, positive reference-force, model-truncation, or review receipts",
        },
        "naive_per_loop_cap_counterexample": naive,
        "derived_uniform_cap_check": cap_check,
        "physical_score": None,
        "lane_status": "GROUND_STATE_FORCE_UNCERTIFIED",
        "input_hashes": {
            "lane_contract_v2.json": sha256(CONTRACT),
            "lane_contract.py": sha256(CONTRACT_SOURCE),
            "force_budget.py": sha256(Path(__file__).with_name("force_budget.py")),
            "core/numerics.py": sha256(ROOT / "core/numerics.py"),
            "force_budget_diagnostic.py": sha256(Path(__file__)),
        },
    }
    (output_dir / "protocol.json").write_text(
        json.dumps(protocol, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _plot(output_dir / "force_budget_caps.png", rows, naive)
    summary = {
        "schema": protocol["schema"],
        "physical_score": None,
        "lane_status": protocol["lane_status"],
        "scenario_denominator": protocol["scenario_denominator"],
        "physical_evidence_denominator": protocol["physical_evidence_denominator"],
        "naive_per_loop_cap_counterexample": naive,
        "derived_uniform_caps_at_reference_lower_1": max_caps,
        "derived_cap_numeric_gate_pass": cap_check["assumption_only_numeric_gate_pass"],
        "note": "conditional algebra only; no receipt, measurement, GPU, or QUDA evidence",
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    readme = f"""# Wilson F-lane q/h/x force-budget propagation

**Formula-only CPU diagnostic.** No Wilson loop data, sealed split, GPU or QUDA input was read. `physical_score=null`; the ground-state force remains `GROUND_STATE_FORCE_UNCERTIFIED`.

## Result

The F-lane candidate-minus-reference force contrast contains **8 signed loop corners**: two kernels (stout and identity), two separations (`R=2,3`), and two adjacent times (`t,t+1`) inside the effective-energy extraction. If each positive loop corner has `delta=log(1+q+h+x)`, then the conservative contrast bound is the sum of all 8 `delta` bounds. For separate component accounting, `log(1+q+h+x) <= log(1+q)+log(1+h)+log(1+x)` for nonnegative inputs, so the q/h/x force-unit envelopes are `sum_corner log(1+q)`, etc.

At the illustrative dimensionless reference-force lower bound `f_L=1`, interpreting the draft `1.5% / 1.5% / 1%` values as **raw per-loop-corner caps** gives q/h/x force-bound fractions `{naive['component_relative_bounds']['q']:.4f}`, `{naive['component_relative_bounds']['h']:.4f}`, `{naive['component_relative_bounds']['x']:.4f}`. Each exceeds its corresponding force-level budget. The combined exact log envelope is `{naive['combined_log_corner_bound']:.4f} f_L`; after the proposed model (`1%`) and statistical (`5%`) allowances, the total is `{naive['total_relative_bound']:.4f} f_L`, above the `10%` total tolerance. This demonstrates that the q/h/x percentages must be defined after full stencil propagation or translated into stricter raw loop caps.

For a uniform raw component cap `c` across all corners, requiring its propagated force contribution to be no larger than `epsilon*f_L` yields

```text
8 log(1+c) <= epsilon*f_L
c <= expm1(epsilon*f_L/8).
```

At `f_L=1`, the resulting raw loop caps are q=`{max_caps['q']:.7f}`, h=`{max_caps['h']:.7f}`, x=`{max_caps['x']:.7f}`. These are planning calculations, not measured q/h/x values or accepted production inputs. `cap_sensitivity.csv` and the figure show how the required raw caps change with the yet-unknown positive force lower bound.

![Force-level and raw loop-level bound relation](force_budget_caps.png)

## Denominators and flow

- Deterministic formula scenarios: planned/valid/failed/abstained = `{len(rows)}/{len(rows)}/0/0`.
- Physical evidence gate: `1/0/0/1`; independent loop envelopes, positive reference-force lower bound, propagated model bound and reviewer receipt are absent.

```text
independent positive force lower bound + q/h/x bounds at 8 corners
  -> log envelopes -> 8-term candidate-minus-reference force bound
  -> compare q/h/x component budgets in force units
  -> add model-truncation and statistical bounds
  -> <=10% total gate AND independent receipts/review
  -> otherwise ABSTAIN; physical_score remains null
```

The output is conditional algebra only. It neither verifies physical positivity nor establishes any q/h/x envelope, spectral-model error, statistical coverage, or reference-force lower bound. Source hashes and all output identities are in `protocol.json` and `artifact_hashes.json`; the shared numeric-conversion source is retained as `snapshot_core_numerics.py`.
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")
    artifacts = sorted(path for path in output_dir.iterdir() if path.is_file())
    hashes = {path.name: sha256(path) for path in artifacts}
    (output_dir / "artifact_hashes.json").write_text(
        json.dumps(hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    print(json.dumps(build(args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
