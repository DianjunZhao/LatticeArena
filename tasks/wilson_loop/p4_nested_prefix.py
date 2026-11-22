"""Paired nested-prefix CPU sensitivity for Wilson P4 power versus budget.

Each independent synthetic dataset is generated once at the largest budget.
The 80/160/320-configuration cells use nested prefixes from that same dataset,
so budget differences can be estimated with paired dataset-level intervals.
This is an oracle-anchor method diagnostic, not a physical measurement.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import beta

from . import p4_controls as base
from .statistics import blocks, bootstrap_indices, risk


DEFAULT_OUT = Path("results/wilson_loop/audit_20261119_p4_nested_prefix_v2")
N_DATASETS = 402
BASE_SEED = 2026111930
BASELINE_NOISE = 0.005
BLOCK_LENGTH = 5
N_BLOCKS = (16, 32, 64)
AMPLITUDE_RATIOS = (0.75, 0.50, 0.35)
INNER_DRAWS = 100
OUTER_DRAWS = 100
NOMINAL_WINDOW_INDEX = 1
PAIRED_BOOTSTRAP_DRAWS = 20_000


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_manifest() -> dict[str, str]:
    return {
        "p4_nested_prefix.py": sha256(Path(__file__).resolve()),
        "p4_controls.py": sha256(Path(base.__file__).resolve()),
        "statistics.py": sha256(Path(base.risk.__code__.co_filename).resolve()),
    }


def protocol() -> dict:
    return {
        "schema": "wilson-p4-nested-prefix-v1",
        "scope": "synthetic_cpu_oracle_anchor_method_diagnostic",
        "physical_status": "NOT_RUN",
        "independent_datasets_per_effect": N_DATASETS,
        "effects": [
            {
                "candidate_to_baseline_noise_amplitude": ratio,
                "input_noise_variance_reduction": 1 / ratio**2,
            }
            for ratio in AMPLITUDE_RATIOS
        ],
        "nested_budgets": [
            {
                "blocks": n_blocks,
                "block_length": BLOCK_LENGTH,
                "configurations": n_blocks * BLOCK_LENGTH,
                "prefix": f"first {n_blocks * BLOCK_LENGTH} of 320 paired configurations",
            }
            for n_blocks in N_BLOCKS
        ],
        "seed": BASE_SEED,
        "seed_rule": "base seed + 100000 * effect index + independent dataset index",
        "noise": {
            "baseline_amplitude": BASELINE_NOISE,
            "common_fraction": float(base.PLAN["common_noise_fraction"]),
            "paired_common_noise_across_estimators": True,
            "same_configurations_reused_as_nested_prefixes": True,
        },
        "truth": {
            "E0": float(base.PLAN["E0"]),
            "signal": "single-state exp(-E0*t), exact E0 oracle anchor",
        },
        "bootstrap": {
            "inner_draws": INNER_DRAWS,
            "outer_ratio_draws": OUTER_DRAWS,
            "paired_dataset_bootstrap_draws_for_budget_contrasts": PAIRED_BOOTSTRAP_DRAWS,
            "budget_specific_seeded_indices": True,
        },
        "gate": {
            "spread_limit": float(base.PLAN["spread_limit"]),
            "oracle_anchor_z_limit": float(base.PLAN["anchor_z_limit"]),
            "decision": "both estimator gates pass and paired outer-bootstrap 95% risk-ratio lower bound > 1",
        },
        "primary_followup": "paired budget differences for amplitude_ratio=0.75 (input variance reduction 1.78x)",
        "paired_contrast": "dataset-level detection indicator at larger budget minus smaller budget; percentile bootstrap over paired dataset IDs",
        "failure_policy": "failed datasets remain non-detections in every budget denominator",
        "intervals": "pointwise exact Clopper-Pearson 95% for marginal detection rates; paired dataset-bootstrap 95% for budget differences",
        "exclusions": [
            "No physical gauge fields or stout/APE kernels",
            "No estimated-anchor uncertainty or common physical bias",
            "No family-wise correction across effects or contrasts",
            "Measured CPU time is not a GPU production cost estimate",
        ],
        "source_sha256": source_manifest(),
    }


def cp95(k: int, n: int) -> list[float]:
    return [
        float(beta.ppf(0.025, k, n - k + 1)) if k else 0.0,
        float(beta.ppf(0.975, k + 1, n - k)) if k < n else 1.0,
    ]


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def data_for_effect(seed: int, amplitude_ratio: float) -> np.ndarray:
    t_values = np.asarray(base.PLAN["t_values"], dtype=float)
    n_configurations = max(N_BLOCKS) * BLOCK_LENGTH
    signal = np.exp(-float(base.PLAN["E0"]) * t_values)
    rng = np.random.default_rng(seed)
    common = rng.normal(size=(n_configurations, 1, len(t_values)))
    common_fraction = float(base.PLAN["common_noise_fraction"])
    channels = []
    for amplitude in (BASELINE_NOISE, BASELINE_NOISE * amplitude_ratio):
        independent = rng.normal(size=common.shape)
        noise = (
            np.sqrt(common_fraction) * common
            + np.sqrt(1.0 - common_fraction) * independent
        )
        channels.append(signal[None, None, :] * (1.0 + amplitude * noise))
    return np.stack(channels, axis=1)


def evaluate_budget(configurations: np.ndarray, *, n_blocks: int, seed: int) -> dict:
    n_configurations = n_blocks * BLOCK_LENGTH
    prefix = configurations[:n_configurations]
    block_values = np.stack(
        [blocks(prefix[:, channel], BLOCK_LENGTH) for channel in range(2)], axis=1
    )
    if block_values.shape[0] != n_blocks:
        raise RuntimeError("prefix did not produce the planned number of blocks")

    t_values = np.asarray(base.PLAN["t_values"], dtype=float)
    windows = base.PLAN["windows"]
    truth_e0 = float(base.PLAN["E0"])
    inner = bootstrap_indices(n_blocks, INNER_DRAWS, seed + 10_000_000)
    estimates = [
        risk(
            block_values[:, channel], inner, windows, t_values,
            [truth_e0], nominal=NOMINAL_WINDOW_INDEX,
        )
        for channel in range(2)
    ]
    gates = {}
    for label, result in zip(("baseline", "candidate"), estimates):
        value = float(result["v"][0])
        se = float(result["se"][0])
        spread = float(result["spread"][0])
        anchor_z = abs(value - truth_e0) / se if se > 0 else float("inf")
        relative_spread = spread / abs(value) if value else float("inf")
        passes_spread = relative_spread <= float(base.PLAN["spread_limit"])
        passes_anchor = anchor_z <= float(base.PLAN["anchor_z_limit"])
        gates[label] = {
            "status": "PASS" if passes_spread and passes_anchor else "ABSTAIN",
            "spread_gate": bool(passes_spread),
            "anchor_gate": bool(passes_anchor),
            "relative_window_spread": relative_spread,
            "oracle_anchor_z": anchor_z,
            "value": value,
            "se": se,
            "window_spread": spread,
            "risk": float(result["risk"]),
        }

    outer_rng = np.random.default_rng(seed + 20_000_000)
    ratios = []
    for _ in range(OUTER_DRAWS):
        selected = outer_rng.integers(0, n_blocks, n_blocks)
        baseline_risk = risk(
            block_values[selected, 0], inner, windows, t_values,
            [truth_e0], nominal=NOMINAL_WINDOW_INDEX,
        )["risk"]
        candidate_risk = risk(
            block_values[selected, 1], inner, windows, t_values,
            [truth_e0], nominal=NOMINAL_WINDOW_INDEX,
        )["risk"]
        if candidate_risk <= 0 or not np.isfinite(candidate_risk):
            raise ValueError(f"invalid candidate risk: {candidate_risk!r}")
        ratios.append(float(baseline_risk / candidate_risk))
    ratio_ci = np.quantile(ratios, [0.025, 0.975]).tolist()
    detected = all(gate["status"] == "PASS" for gate in gates.values()) and ratio_ci[0] > 1.0
    return {
        "status": "OK",
        "n_blocks": int(n_blocks),
        "block_length": BLOCK_LENGTH,
        "configurations_per_dataset": n_configurations,
        "gates": gates,
        "ratio_point": float(estimates[0]["risk"] / estimates[1]["risk"]),
        "ratio_ci95": [float(value) for value in ratio_ci],
        "improvement_detected": bool(detected),
    }


def run_dataset(effect_index: int, dataset: int, ratio: float) -> dict:
    seed = BASE_SEED + 100_000 * effect_index + dataset
    configurations = data_for_effect(seed, ratio)
    budgets = {}
    for n_blocks in N_BLOCKS:
        budget_seed = seed + 1_000 * n_blocks
        budgets[str(n_blocks * BLOCK_LENGTH)] = evaluate_budget(
            configurations, n_blocks=n_blocks, seed=budget_seed,
        )
    return {
        "effect_index": effect_index,
        "dataset": dataset,
        "seed": seed,
        "candidate_to_baseline_noise_amplitude": ratio,
        "input_noise_variance_reduction": 1 / ratio**2,
        "budgets": budgets,
    }


def paired_contrast(rows: list[dict], lower: str, upper: str, seed: int) -> dict:
    differences = np.asarray([
        int(row["budgets"][upper]["improvement_detected"])
        - int(row["budgets"][lower]["improvement_detected"])
        for row in rows
    ], dtype=float)
    n = len(differences)
    rng = np.random.default_rng(seed)
    bootstrap = np.empty(PAIRED_BOOTSTRAP_DRAWS, dtype=float)
    for start in range(0, PAIRED_BOOTSTRAP_DRAWS, 200):
        count = min(200, PAIRED_BOOTSTRAP_DRAWS - start)
        indices = rng.integers(0, n, size=(count, n))
        bootstrap[start:start + count] = differences[indices].mean(axis=1)
    gains = int(np.count_nonzero(differences > 0))
    losses = int(np.count_nonzero(differences < 0))
    ties = n - gains - losses
    return {
        "lower_budget": int(lower),
        "upper_budget": int(upper),
        "n_paired_datasets": n,
        "point_difference": float(differences.mean()),
        "paired_bootstrap_ci95": [float(x) for x in np.quantile(bootstrap, [0.025, 0.975])],
        "higher_budget_only_detected": gains,
        "lower_budget_only_detected": losses,
        "both_same_outcome": ties,
    }


def summarize(rows: list[dict], protocol_hash: str) -> dict:
    ratios = list(AMPLITUDE_RATIOS)
    by_effect = {}
    for effect_index, ratio in enumerate(ratios):
        effect_rows = [row for row in rows if row["effect_index"] == effect_index]
        budgets = {}
        for configurations in (80, 160, 320):
            label = str(configurations)
            cell = [row["budgets"][label] for row in effect_rows]
            n = len(cell)
            detected = sum(item["improvement_detected"] for item in cell)
            failures = sum(item.get("status") != "OK" for item in cell)
            budgets[label] = {
                "configurations_per_dataset": configurations,
                "detected": detected,
                "n": n,
                "rate": detected / n if n else None,
                "cp95": cp95(detected, n) if n else None,
                "failure": failures,
                "both_gates_pass": sum(
                    bool(item.get("gates"))
                    and all(g["status"] == "PASS" for g in item["gates"].values())
                    for item in cell
                ),
                "any_abstain": sum(
                    any(g["status"] != "PASS" for g in item.get("gates", {}).values())
                    for item in cell
                ),
            }
        contrasts = {}
        for lo, hi in (("80", "160"), ("160", "320"), ("80", "320")):
            contrasts[f"{lo}_to_{hi}"] = paired_contrast(
                effect_rows, lo, hi,
                BASE_SEED + 50_000_000 + effect_index * 1_000 + int(lo) + int(hi),
            )
        by_effect[str(ratio)] = {
            "input_noise_variance_reduction": 1 / ratio**2,
            "budgets": budgets,
            "paired_budget_contrasts": contrasts,
        }
    return {
        "schema": "wilson-p4-nested-prefix-summary-v1",
        "status": "COMPLETE" if len(rows) == N_DATASETS * len(ratios) else "PARTIAL",
        "independent_datasets_per_effect": N_DATASETS,
        "n_rows": len(rows),
        "protocol_sha256": protocol_hash,
        "physical_status": "NOT_RUN",
        "effects": by_effect,
    }


def write_figure(out: Path, summary: dict) -> None:
    colors = {"0.75": "#4477aa", "0.5": "#228833", "0.35": "#cc6677"}
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.0))
    ax = axes[0]
    budgets = (80, 160, 320)
    for ratio, effect in summary["effects"].items():
        x = np.asarray(budgets, dtype=float)
        estimates = [effect["budgets"][str(n)] for n in budgets]
        y = np.asarray([item["rate"] for item in estimates], dtype=float)
        ci = np.asarray([item["cp95"] for item in estimates], dtype=float)
        ax.errorbar(
            x, y, yerr=np.vstack((y - ci[:, 0], ci[:, 1] - y)),
            marker="o", capsize=3, linewidth=1.7, color=colors[ratio],
            label=f"amplitude ratio={ratio} (variance reduction={effect['input_noise_variance_reduction']:.2g}x)",
        )
    ax.axhline(0.90, color="black", linestyle="--", linewidth=1, label="target=0.90")
    ax.set(xlabel="nested prefix configurations per dataset", ylabel="detected datasets / 402",
           title="Marginal detection rates (pointwise CP95)", ylim=(-0.03, 1.03))
    ax.grid(alpha=0.22)
    ax.legend(fontsize=8)

    ax = axes[1]
    contrasts = (("80_to_160", "160−80"), ("160_to_320", "320−160"), ("80_to_320", "320−80"))
    offsets = {"0.75": -0.18, "0.5": 0.0, "0.35": 0.18}
    base_x = np.arange(len(contrasts), dtype=float)
    for ratio, effect in summary["effects"].items():
        point, low, high = [], [], []
        for name, _ in contrasts:
            value = effect["paired_budget_contrasts"][name]
            point.append(value["point_difference"])
            low.append(value["point_difference"] - value["paired_bootstrap_ci95"][0])
            high.append(value["paired_bootstrap_ci95"][1] - value["point_difference"])
        ax.errorbar(
            base_x + offsets[ratio], point,
            yerr=np.vstack((low, high)), marker="o", capsize=3,
            color=colors[ratio], label=f"amplitude ratio={ratio}",
        )
    ax.axhline(0.0, color="black", linewidth=1)
    ax.set_xticks(base_x, [label for _, label in contrasts])
    ax.set(ylabel="paired detection-rate difference", title="Paired nested-budget contrasts")
    ax.grid(alpha=0.22)
    ax.legend(fontsize=8)
    fig.suptitle("Synthetic P4 nested-prefix power sensitivity; same datasets at each budget")
    fig.tight_layout()
    fig.savefig(out / "nested_prefix_diagnostics.png", dpi=170)
    plt.close(fig)


def write_readme(out: Path, summary: dict) -> None:
    lines = [
        "# Wilson P4 nested-prefix paired budget sensitivity",
        "",
        f"Status: **{summary['status']}**; {summary['independent_datasets_per_effect']} independent synthetic datasets per effect.",
        "",
        "Unlike the earlier independent-cell scan, each dataset is generated once at 320 paired configurations. The 80- and 160-configuration cells are literal prefixes of that same dataset. Budget contrasts therefore use paired dataset IDs and do not confuse independent-cell noise with a budget effect.",
        "",
        "The dataset is a known single-state signal with an exact synthetic E0 anchor. These results test only the gate and this generator; they do not measure real gauge fields, physical autocorrelation, stout/APE kernels, GPU time, or common model bias.",
        "",
        "## Marginal detection rates",
        "",
        "| amplitude ratio | variance reduction | configs | detected | CP95 | both gates pass | any abstain | failures |",
        "|---:|---:|---:|---:|---|---:|---:|---:|",
    ]
    for ratio, effect in summary["effects"].items():
        for budget, cell in effect["budgets"].items():
            lines.append(
                f"| {ratio} | {effect['input_noise_variance_reduction']:.3g}x | {budget} | "
                f"{cell['detected']}/{cell['n']} ({cell['rate']:.3f}) | "
                f"[{cell['cp95'][0]:.3f}, {cell['cp95'][1]:.3f}] | "
                f"{cell['both_gates_pass']}/{cell['n']} | {cell['any_abstain']}/{cell['n']} | {cell['failure']}/{cell['n']} |"
            )
    lines.extend([
        "",
        "## Paired budget differences",
        "",
        "Positive values mean the larger budget detected more datasets. The interval is a percentile bootstrap over paired independent dataset IDs; it is not a binomial interval and is not family-wise adjusted.",
        "",
        "| amplitude ratio | contrast | difference | paired bootstrap CI95 | higher-only / lower-only / ties |",
        "|---:|---|---:|---|---|",
    ])
    for ratio, effect in summary["effects"].items():
        for name, contrast in effect["paired_budget_contrasts"].items():
            lines.append(
                f"| {ratio} | {contrast['lower_budget']}→{contrast['upper_budget']} | "
                f"{contrast['point_difference']:.3f} | "
                f"[{contrast['paired_bootstrap_ci95'][0]:.3f}, {contrast['paired_bootstrap_ci95'][1]:.3f}] | "
                f"{contrast['higher_budget_only_detected']}/{contrast['lower_budget_only_detected']}/{contrast['both_same_outcome']} |"
            )
    lines.extend([
        "",
        "![Nested-prefix marginal rates and paired differences](nested_prefix_diagnostics.png)",
        "",
        "## Interpretation and limits",
        "",
        "The primary follow-up is the weak 1.78x input-variance reduction. The left panel gives its marginal power by budget; the right panel directly estimates how detection changes on the same dataset IDs. A contrast interval spanning zero means this synthetic run does not resolve the budget difference. The 402 datasets remain Monte Carlo realizations, not physical gauge configurations.",
        "",
        "Failures remain in every planned denominator as non-detections. Gate abstention, ratio-CI non-detection, and exceptions are kept separate in raw rows. The exact seed, full source manifest, per-dataset budget outcomes, and protocol hash are saved beside this report. `physical_status` remains `NOT_RUN`.",
    ])
    (out / "README.md").write_text("\n".join(lines) + "\n")


def prepare(out: Path) -> dict:
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    frozen = protocol()
    atomic_json(out / "protocol.json", frozen)
    return {
        "prepared": str(out),
        "protocol_sha256": sha256(out / "protocol.json"),
        "datasets_per_effect": N_DATASETS,
        "budgets": [n * BLOCK_LENGTH for n in N_BLOCKS],
        "effects": list(AMPLITUDE_RATIOS),
    }


def execute(out: Path, max_datasets: int | None = None) -> dict:
    out = out.resolve()
    frozen = json.loads((out / "protocol.json").read_text())
    if frozen != protocol():
        raise RuntimeError("protocol or source hashes changed after preparation")
    protocol_hash = sha256(out / "protocol.json")
    n_target = N_DATASETS if max_datasets is None else min(N_DATASETS, int(max_datasets))
    if n_target < 1:
        raise ValueError("max_datasets must be positive")
    rows_path = out / "dataset_rows.jsonl"
    rows_by_key = {}
    if rows_path.exists():
        with rows_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                row = json.loads(line)
                key = (int(row["effect_index"]), int(row["dataset"]))
                if row.get("protocol_sha256") != protocol_hash or key in rows_by_key:
                    raise RuntimeError(f"invalid or duplicate row at line {line_number}")
                expected_seed = BASE_SEED + 100_000 * key[0] + key[1]
                if row.get("seed") != expected_seed:
                    raise RuntimeError(f"unexpected seed at line {line_number}")
                rows_by_key[key] = row
    expected_keys = {
        (effect_index, dataset)
        for effect_index in range(len(AMPLITUDE_RATIOS))
        for dataset in range(n_target)
    }
    if any(effect_index >= len(AMPLITUDE_RATIOS) or dataset >= n_target for effect_index, dataset in rows_by_key):
        raise RuntimeError("saved rows exceed the requested target; use a new output directory")

    started = time.perf_counter()
    write_mode = "a" if rows_path.exists() else "w"
    completed = len(rows_by_key)
    with rows_path.open(write_mode, encoding="utf-8") as handle:
        for effect_index, ratio in enumerate(AMPLITUDE_RATIOS):
            for dataset in range(n_target):
                key = (effect_index, dataset)
                if key in rows_by_key:
                    continue
                seed = BASE_SEED + 100_000 * effect_index + dataset
                try:
                    row = run_dataset(effect_index, dataset, ratio)
                except Exception as exc:
                    row = {
                        "effect_index": effect_index,
                        "dataset": dataset,
                        "seed": seed,
                        "candidate_to_baseline_noise_amplitude": ratio,
                        "status": "FAIL",
                        "failure": f"{type(exc).__name__}: {exc}",
                        "budgets": {
                            str(n * BLOCK_LENGTH): {
                                "status": "FAIL",
                                "improvement_detected": False,
                                "n_blocks": n,
                                "block_length": BLOCK_LENGTH,
                                "configurations_per_dataset": n * BLOCK_LENGTH,
                            }
                            for n in N_BLOCKS
                        },
                    }
                row["protocol_sha256"] = protocol_hash
                handle.write(json.dumps(row, separators=(",", ":")) + "\n")
                handle.flush()
                rows_by_key[key] = row
                completed += 1
                if completed % 25 == 0:
                    atomic_json(out / "checkpoint.json", {
                        "status": "RUNNING",
                        "completed_rows": completed,
                        "planned_rows": len(AMPLITUDE_RATIOS) * n_target,
                        "protocol_sha256": protocol_hash,
                    })
    rows = [rows_by_key[key] for key in sorted(rows_by_key)]
    for row in rows:
        for budget in row["budgets"].values():
            budget.setdefault("status", row.get("status", "OK"))
            budget.setdefault("improvement_detected", False)
    # A partial smoke is never represented as a completed full design.
    summary = summarize(rows, protocol_hash)
    summary["status"] = "COMPLETE" if n_target == N_DATASETS and len(rows) == len(expected_keys) else "PARTIAL_SMOKE"
    summary["target_per_effect"] = N_DATASETS
    summary["completed_per_effect"] = n_target
    summary["total_wall_seconds_this_invocation"] = time.perf_counter() - started
    summary["python"] = platform.python_version()
    summary["platform"] = platform.platform()
    raw = {
        "scope": "synthetic_cpu_oracle_anchor_nested_prefix_method_diagnostic",
        "physical_status": "NOT_RUN",
        "protocol_sha256": protocol_hash,
        "protocol": frozen,
        "rows": rows,
    }
    atomic_json(out / "raw.json", raw)
    atomic_json(out / "summary.json", summary)
    write_figure(out, summary)
    write_readme(out, summary)
    atomic_json(out / "checkpoint.json", {
        "status": summary["status"],
        "completed_rows": len(rows),
        "planned_rows": len(AMPLITUDE_RATIOS) * N_DATASETS,
        "protocol_sha256": protocol_hash,
        "updated_utc": datetime.now(timezone.utc).isoformat(),
    })
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--max-datasets", type=int)
    args = parser.parse_args()
    result = prepare(args.out) if args.prepare else execute(args.out, args.max_datasets)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
