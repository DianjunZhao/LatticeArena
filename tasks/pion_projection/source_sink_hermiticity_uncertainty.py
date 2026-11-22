"""Per-configuration and block-bootstrap audit of archived source-sink matrices.

This is a CPU-only reanalysis of already-observed IDs. It does not run a
measurement, change the arrays, or assign a physical score.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .source_sink_hermiticity_diagnostic import (
    ROOT,
    SELECTED_POWERS,
    SPLITS,
    THRESHOLD,
    TIMES,
    _sha256,
    load_split,
    relative_antihermitian_norm,
)


OUT_DIR = ROOT / "results/pion_projection/source_sink_hermiticity_per_config_20261121_v1"
BLOCK_LENGTHS = (1, 2, 5, 10)
N_BOOTSTRAP = 5000
BOOTSTRAP_SEED = 20261121


def source_sink_matrices(correlators: np.ndarray, powers: list[int]) -> np.ndarray:
    """Return per-configuration C matrices: (configuration, sink, source, t)."""
    data = np.asarray(correlators)
    if data.ndim != 4 or not np.isfinite(data).all():
        raise ValueError("correlators must be a finite (configuration, source, power, t) array")
    if len(powers) != data.shape[2]:
        raise ValueError("sink powers do not match the correlator power axis")
    if len(set(powers)) != len(powers):
        raise ValueError("sink powers must be unique")
    try:
        selected = [powers.index(power) for power in SELECTED_POWERS]
    except ValueError as exc:
        raise ValueError(f"required sink powers {SELECTED_POWERS} are missing") from exc
    # Input axes are (configuration, source smearing, sink power, t).
    # Transpose the selected source/power axes to rows=sink, columns=source.
    return data[:, :, selected, :].transpose(0, 2, 1, 3)


def per_configuration_metrics(matrices: np.ndarray, times: tuple[int, ...] = TIMES) -> dict[int, np.ndarray]:
    """Compute descriptive ratios for each configuration and requested t."""
    data = np.asarray(matrices)
    if data.ndim != 4 or data.shape[1:3] != (3, 3) or not np.isfinite(data).all():
        raise ValueError("matrices must be finite with shape (configuration, 3, 3, t)")
    result: dict[int, np.ndarray] = {}
    for t in times:
        if t < 0 or t >= data.shape[3]:
            raise ValueError(f"requested time {t} is outside the saved range")
        result[t] = np.asarray([relative_antihermitian_norm(m[:, :, t]) for m in data])
    return result


def block_bootstrap_metrics(
    matrices: np.ndarray,
    block_length: int,
    n_bootstrap: int,
    seed: int,
) -> tuple[np.ndarray, int]:
    """Resample contiguous non-overlapping blocks and evaluate the mean-matrix metric."""
    data = np.asarray(matrices)
    if data.ndim != 3 or data.shape[1] != data.shape[2] or not np.isfinite(data).all():
        raise ValueError("matrices must be finite square matrices indexed by configuration")
    if isinstance(block_length, bool) or not isinstance(block_length, int) or block_length <= 0:
        raise ValueError("block_length must be a positive integer")
    if data.shape[0] % block_length:
        raise ValueError("configuration count must be divisible by block_length")
    n_blocks = data.shape[0] // block_length
    if n_blocks < 2:
        raise ValueError("at least two contiguous blocks are required")
    if isinstance(n_bootstrap, bool) or not isinstance(n_bootstrap, int) or n_bootstrap < 2:
        raise ValueError("n_bootstrap must be an integer of at least two")

    blocks = data.reshape(n_blocks, block_length, data.shape[1], data.shape[2])
    rng = np.random.default_rng(seed)
    selected = rng.integers(0, n_blocks, size=(n_bootstrap, n_blocks))
    means = blocks[selected].mean(axis=(1, 2))
    denominator = np.abs(means).max(axis=(1, 2))
    numerator = np.abs(means - means.conj().transpose(0, 2, 1)).max(axis=(1, 2))
    valid = np.isfinite(denominator) & np.isfinite(numerator) & (denominator > 0.0)
    values = np.full(n_bootstrap, np.nan, dtype=float)
    values[valid] = numerator[valid] / denominator[valid]
    return values[valid], int((~valid).sum())


def analyze_split(result: dict[str, object], n_bootstrap: int = N_BOOTSTRAP) -> dict[str, object]:
    matrices = source_sink_matrices(np.asarray(result["correlators"]), list(result["powers"]))
    cfg_metrics = per_configuration_metrics(matrices)
    ids = [int(cfg) for cfg in result["ids"]]
    split_result: dict[str, object] = {
        "split": str(result["split"]),
        "archive_split": str(result["archive_split"]),
        "ids": ids,
        "n_configurations": len(ids),
        "per_configuration": {},
        "block_bootstrap": {},
        "ensemble_mean": {},
        "n_bootstrap": n_bootstrap,
        "bootstrap_seed": BOOTSTRAP_SEED,
    }
    for t in TIMES:
        vals = cfg_metrics[t]
        mean_matrix = matrices[:, :, :, t].mean(axis=0)
        split_result["ensemble_mean"][str(t)] = relative_antihermitian_norm(mean_matrix)
        split_result["per_configuration"][str(t)] = {
            "median": float(np.median(vals)),
            "q16": float(np.quantile(vals, 0.16)),
            "q84": float(np.quantile(vals, 0.84)),
            "minimum": float(vals.min()),
            "maximum": float(vals.max()),
            "below_5_percent_descriptive_count": int(np.sum(vals < THRESHOLD)),
            "n": int(len(vals)),
        }
        split_result["block_bootstrap"][str(t)] = {}
        for block_length in BLOCK_LENGTHS:
            draws, invalid = block_bootstrap_metrics(
                matrices[:, :, :, t], block_length, n_bootstrap,
                BOOTSTRAP_SEED + 1000 * block_length + t + (0 if split_result["archive_split"] == "development" else 100),
            )
            split_result["block_bootstrap"][str(t)][str(block_length)] = {
                "n_contiguous_blocks": len(ids) // block_length,
                "valid_draws": int(draws.size),
                "invalid_draws": invalid,
                "median": float(np.median(draws)),
                "ci95_low": float(np.quantile(draws, 0.025)),
                "ci95_high": float(np.quantile(draws, 0.975)),
                "fraction_ci_above_5_percent": float(np.mean(draws > THRESHOLD)),
            }
    return split_result


def _write_per_configuration_csv(path: Path, results: list[dict[str, object]]) -> None:
    rows = []
    for result in results:
        archive = next(r for r in results if r["split"] == result["split"])
        # Recompute from raw archived arrays so every saved configuration is explicit.
        matrices = source_sink_matrices(np.asarray(archive["correlators"]), list(archive["powers"]))
        cfg_metrics = per_configuration_metrics(matrices)
        for i, cfg in enumerate(result["ids"]):
            for t in TIMES:
                rows.append({
                    "split": result["split"],
                    "configuration_id": cfg,
                    "t": t,
                    "relative_antihermitian_max_norm": float(cfg_metrics[t][i]),
                    "below_5_percent_descriptive_only": bool(cfg_metrics[t][i] < THRESHOLD),
                })
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _save_plots(archive_results: list[dict[str, object]], summaries: list[dict[str, object]], output: Path) -> None:
    colors = {"development": "#2166ac", "validation": "#b2182b"}
    labels = {"development": "Development IDs 0–59", "validation": "Observed validation IDs 70–99"}

    fig, axes = plt.subplots(2, 4, figsize=(12.4, 7.0), sharey=True, constrained_layout=True)
    for row, (archive, summary) in enumerate(zip(archive_results, summaries)):
        matrices = source_sink_matrices(np.asarray(archive["correlators"]), list(archive["powers"]))
        metrics = per_configuration_metrics(matrices)
        for col, t in enumerate(TIMES):
            ax = axes[row, col]
            vals = metrics[t]
            rng = np.random.default_rng(BOOTSTRAP_SEED + 10 * row + t)
            ax.scatter(rng.normal(0.0, 0.045, size=len(vals)), vals, s=16, alpha=0.65,
                       color=colors["development" if row == 0 else "validation"])
            q16, med, q84 = np.quantile(vals, [0.16, 0.5, 0.84])
            ax.errorbar([0], [med], yerr=[[med - q16], [q84 - med]], fmt="D", color="black",
                        capsize=3, markersize=5, label="median and 16–84% range")
            ax.axhline(THRESHOLD, color="#444444", linestyle="--", linewidth=1.0)
            ax.set(title=f"t={t}", xlim=(-0.25, 0.25), xticks=[])
            ax.grid(axis="y", alpha=0.2)
            if col == 0:
                ax.set_ylabel(f"{labels['development' if row == 0 else 'validation']}\nratio")
            if row == 0 and col == 0:
                ax.legend(frameon=False, fontsize=7, loc="upper left")
    fig.suptitle("Per-configuration source–sink mismatch (descriptive; not the ensemble gate)")
    fig.savefig(output / "per_configuration_distribution.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(2, 4, figsize=(12.4, 7.0), sharey=True, constrained_layout=True)
    for row, summary in enumerate(summaries):
        for col, t in enumerate(TIMES):
            ax = axes[row, col]
            entries = summary["block_bootstrap"][str(t)]
            xs, medians, lows, highs = [], [], [], []
            for block_length in BLOCK_LENGTHS:
                entry = entries[str(block_length)]
                xs.append(block_length)
                medians.append(entry["median"])
                lows.append(entry["ci95_low"])
                highs.append(entry["ci95_high"])
            ax.errorbar(xs, medians, yerr=[np.asarray(medians) - np.asarray(lows),
                                           np.asarray(highs) - np.asarray(medians)],
                        fmt="o-", color=colors["development" if row == 0 else "validation"],
                        capsize=3, markersize=4)
            ax.axhline(THRESHOLD, color="#444444", linestyle="--", linewidth=1.0)
            mean_value = float(summary["ensemble_mean"][str(t)])
            ax.axhline(mean_value, color="#777777", linestyle=":", linewidth=1.0)
            ax.set(title=f"t={t}", xscale="log", xticks=list(BLOCK_LENGTHS),
                   xticklabels=[str(v) for v in BLOCK_LENGTHS])
            ax.grid(axis="y", alpha=0.2)
            if col == 0:
                ax.set_ylabel(f"{labels['development' if row == 0 else 'validation']}\nbootstrap 95% interval")
            if row == 0 and col == 0:
                ax.legend(["block bootstrap median and 95% interval", "5% threshold", "observed mean"],
                          frameon=False, fontsize=7, loc="upper right")
    fig.supxlabel("non-overlapping block length in saved-configuration order")
    fig.suptitle("Block-bootstrap sensitivity of the ensemble-mean matrix gate")
    fig.savefig(output / "block_bootstrap_interval_sensitivity.png", dpi=180)
    plt.close(fig)


def run(output_dir: Path = OUT_DIR, n_bootstrap: int = N_BOOTSTRAP) -> dict[str, object]:
    output_dir = Path(output_dir)
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"refusing to overwrite existing diagnostic directory: {output_dir}")
    archive_results = [load_split(split, expected_ids, display_name)
                       for display_name, split, expected_ids in SPLITS]
    summaries = [analyze_split(result, n_bootstrap=n_bootstrap) for result in archive_results]
    input_hashes = {}
    for result in archive_results:
        for key in ("npz_path", "provenance_path"):
            path = Path(result[key])
            input_hashes[str(path.relative_to(ROOT))] = _sha256(path)

    output_dir.mkdir(parents=True, exist_ok=False)
    try:
        summary = {
            "schema": "pion-source-sink-hermiticity-per-configuration-v1",
            "status": "diagnostic_only",
            "physical_score": None,
            "threshold": THRESHOLD,
            "threshold_rule": "ensemble-mean metric is required to be strictly less than 0.05",
            "per_configuration_metric_is_gate": False,
            "metric": "max(abs(C-C^dagger))/max(abs(C))",
            "row_column_convention": "rows=sink H0/H4/H16; columns=source point/H4/H16",
            "block_bootstrap": {
                "scheme": "resample non-overlapping contiguous blocks in saved-configuration-ID order",
                "block_lengths": list(BLOCK_LENGTHS),
                "replicates_per_cell": n_bootstrap,
                "seed_base": BOOTSTRAP_SEED,
                "interval": "percentile 95% interval",
                "limitations": [
                    "block length is measured in saved configurations, not HMC trajectories",
                    "validation has only 3 blocks at length 10, so its long-block interval is low-resolution",
                    "this sensitivity analysis does not calibrate the physical 5% gate or identify the historical cause",
                ],
            },
            "splits": {str(summary["split"]): summary for summary in summaries},
            "input_sha256": input_hashes,
            "source_sha256": {
                str(path.relative_to(ROOT)): _sha256(path)
                for path in (
                    Path(__file__).resolve(),
                    Path(__file__).with_name("source_sink_hermiticity_diagnostic.py").resolve(),
                    ROOT / "tests/test_pion_source_sink_hermiticity_uncertainty.py",
                    ROOT / "tests/test_pion_source_sink_hermiticity_diagnostic.py",
                )
            },
        }
        (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        _write_per_configuration_csv(output_dir / "per_configuration.csv", archive_results)
        bootstrap_rows = []
        for result in summaries:
            for t in TIMES:
                for block_length in BLOCK_LENGTHS:
                    row = dict(result["block_bootstrap"][str(t)][str(block_length)])
                    row.update({"split": result["split"], "t": t, "block_length": block_length})
                    bootstrap_rows.append(row)
        with (output_dir / "block_bootstrap.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(bootstrap_rows[0]))
            writer.writeheader()
            writer.writerows(bootstrap_rows)
        _save_plots(archive_results, summaries, output_dir)

        lines = [
            "# Per-configuration source–sink Hermiticity diagnostic",
            "",
            "This CPU-only report reanalyzes already-observed `s16t16_ms` IDs 0–59 and 70–99. It reads no new measurement, sealed split, or raw gauge data; it does not alter the archived arrays or assign a physical score.",
            "",
            "## Definitions and evidence",
            "",
            "For each configuration and Euclidean time, the descriptive ratio is `max|C-C†| / max|C|` after selecting sink powers H0/H4/H16 and arranging rows=sink, columns=source. The pre-existing 5% criterion applies to the ensemble-mean matrix. Per-configuration ratios are shown to expose spread and are **not** treated as separate pass/fail gate decisions.",
            "",
            "The uncertainty figure resamples contiguous, non-overlapping blocks in saved-configuration order at lengths 1, 2, 5, and 10, with 5,000 bootstrap draws per cell. Length 10 leaves only 3 blocks in the already-observed validation split; those intervals are intentionally shown as low-resolution. This is an exploratory uncertainty/sensitivity description, not a calibrated physical coverage statement.",
            "",
            "| Split | t | Ensemble mean | Per-config median [16%,84%] | Per-config min–max | L=5 block-bootstrap 95% interval | L=5 valid/invalid draws |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for result in summaries:
            for t in TIMES:
                per = result["per_configuration"][str(t)]
                boot = result["block_bootstrap"][str(t)]["5"]
                lines.append(
                    f"| {result['split']} | {t} | {result['ensemble_mean'][str(t)]:.4f} | "
                    f"{per['median']:.4f} [{per['q16']:.4f},{per['q84']:.4f}] | "
                    f"{per['minimum']:.4f}–{per['maximum']:.4f} | "
                    f"[{boot['ci95_low']:.4f},{boot['ci95_high']:.4f}] | "
                    f"{boot['valid_draws']}/{boot['invalid_draws']} |"
                )
        lines.extend([
            "",
            "![Per-configuration ratios](per_configuration_distribution.png)",
            "",
            "![Block-bootstrap interval sensitivity](block_bootstrap_interval_sensitivity.png)",
            "",
            "## Interpretation and limits",
            "",
            "The per-configuration ratios are tightly clustered around roughly 0.3 across both observed splits and all four times; the displayed 16–84% ranges are far above 0.05. This indicates that the ensemble-mean failure is not produced only by averaging a few large outliers in these saved configurations. The block-bootstrap intervals describe uncertainty in the same ensemble-mean matrix metric under the stated saved-configuration block resampling; they do not validate the physical gate or identify a unique cause.",
            "",
            "The validation IDs 70–99 were already read and are not blind. Non-overlapping saved-configuration blocks are a sensitivity convention here; the source receipt does not bind these block boundaries to trajectory spacing. The source/sink alpha mismatch remains a plausible mechanism, but this diagnostic cannot establish historical remote software identity or causal attribution. A new matched-kernel measurement is still required to test that mechanism.",
            "",
            "Input NPZ/provenance hashes are recorded in `summary.json`. Raw per-configuration ratios are in `per_configuration.csv`; bootstrap summaries are in `block_bootstrap.csv`.",
            "",
            "## Reproduction",
            "",
            "Run `PYTHONDONTWRITEBYTECODE=1 python3 -B -m tasks.pion_projection.source_sink_hermiticity_uncertainty` from the repository root. The command creates a new output directory and refuses to overwrite an existing one.",
        ])
        (output_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    except BaseException:
        import shutil

        shutil.rmtree(output_dir)
        raise
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT_DIR)
    parser.add_argument("--n-bootstrap", type=int, default=N_BOOTSTRAP)
    args = parser.parse_args()
    result = run(args.output, n_bootstrap=args.n_bootstrap)
    print(json.dumps({"status": result["status"], "output": str(args.output),
                      "splits": list(result["splits"])}, indent=2))


if __name__ == "__main__":
    main()
