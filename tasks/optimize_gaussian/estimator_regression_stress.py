"""Stress tests for optimize package B's fit-state estimator.

Adds configuration/time-correlated noise, wrong-reference mass, block-length
sensitivity, and train-amplitude uncertainty propagation.  It reuses the
production point/replica estimator and is a synthetic CPU diagnostic only.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import beta

from tasks.pion_projection.statistics import blocks, inverse_covariance, shape
from .estimator_regression import PROTOCOL, f0
from .unified import risk_with_fixed_amplitude


OUT = Path("results/optimize_gaussian/cpu_close_20261119_B_stress_v2")
N_DATASET = 200
N_BOOT = 200
NCFG = 80
NOISE = 0.03
TRUE_MASS = 0.5
TRUE_AMPLITUDE = 1.0
MASS_BOOT_SIGMA = 0.002
BLOCK_LENGTHS = (2, 5, 10)
CONFIG_RHOS = (0.0, 0.5, 0.8)
WRONG_MASS_OFFSETS = (0.0, 0.02, 0.05)
TIME_RHO = 0.5


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(rng, *, config_rho, time_rho=TIME_RHO, noise=NOISE,
             ncfg=NCFG, true_mass=TRUE_MASS, amplitude=TRUE_AMPLITUDE):
    """Multiplicative noise with separable AR(1) structure over configs/time."""
    t = np.arange(PROTOCOL["geometry"][3])
    signal = amplitude * f0(t, true_mass, t.size)
    eps = rng.normal(size=(ncfg, 1, t.size))
    if config_rho:
        scale = np.sqrt(1 - config_rho**2)
        for i in range(1, ncfg):
            eps[i] = config_rho * eps[i - 1] + scale * rng.normal(size=(1, t.size))
    if time_rho:
        scale = np.sqrt(1 - time_rho**2)
        for ti in range(1, t.size):
            eps[:, :, ti] = time_rho * eps[:, :, ti - 1] + scale * rng.normal(size=(ncfg, 1))
    return signal[None, None, :] * (1 + noise * eps)


def _amplitude(values, mass, inv):
    late = PROTOCOL["amplitude_window"]
    ff = shape(mass, np.arange(values.shape[-1]), PROTOCOL["geometry"][3])
    numerator = ff[late] @ inv @ values[late]
    denominator = ff[late] @ inv @ ff[late]
    if not np.isfinite(numerator) or not np.isfinite(denominator) or denominator <= 0:
        raise ValueError("invalid amplitude fit")
    return float(numerator / denominator)


def _train_amplitudes(train_blocks, weights, reference_mass, mass_draws, rng, n_boot):
    values = np.einsum("nbt,b->nt", train_blocks, weights)
    inv = inverse_covariance(values[:, PROTOCOL["amplitude_window"]],
                             PROTOCOL["covariance_shrinkage"])
    point_amp = _amplitude(values.mean(axis=0), reference_mass, inv)
    indices = rng.integers(0, len(values), size=(n_boot, len(values)))
    replicas = np.empty(n_boot)
    for b, idx in enumerate(indices):
        replicas[b] = _amplitude(values[idx].mean(axis=0), mass_draws[b], inv)
    amp_se = float(replicas.std(ddof=1))
    return point_amp, replicas, amp_se, indices


def _q_target(amplitude_fit, reference_mass):
    times = np.asarray(PROTOCOL["score_window"], dtype=int)
    truth = TRUE_AMPLITUDE * f0(times, TRUE_MASS, PROTOCOL["geometry"][3])
    reference = f0(times, reference_mass, PROTOCOL["geometry"][3])
    return truth / (amplitude_fit * reference)


def _coverage(boot_q, target):
    interval = np.quantile(boot_q, [0.025, 0.975], axis=0)
    covered = (interval[0] <= target) & (target <= interval[1])
    width = interval[1] - interval[0]
    return covered, width


def one_dataset(rng, *, block_length, config_rho, reference_offset,
                time_rho=TIME_RHO, n_boot=N_BOOT):
    raw = generate(rng, config_rho=config_rho, time_rho=time_rho)
    data = blocks(raw, block_length)
    if len(data) < 8:
        raise ValueError("need at least eight blocks for train/embargo/validation split")
    # Preserve configuration order. Leave a two-block embargo so nearby AR
    # samples do not leak directly across a random interleaving split.
    train_count = (len(data) - 2) // 2
    val_start = train_count + 2
    train, val = data[:train_count], data[val_start:]
    if len(train) < 3 or len(val) < 3:
        raise ValueError("need at least three train and validation blocks after embargo")
    reference_mass = TRUE_MASS + reference_offset
    mass_draws = reference_mass + rng.normal(0, MASS_BOOT_SIGMA, n_boot)
    weights = np.ones(1)
    train_amp, train_amp_draws, train_amp_se, train_indices = _train_amplitudes(
        train, weights, reference_mass, mass_draws, rng, n_boot)
    val_indices = rng.integers(0, len(val), size=(n_boot, len(val)))
    target_frozen = _q_target(train_amp, reference_mass)

    frozen = risk_with_fixed_amplitude(
        val, weights, reference_mass, mass_draws, val_indices, PROTOCOL,
        train_amp, train_amp_se, amplitude_source="train", return_draws=True)
    qboot_frozen = np.asarray(frozen["q_boot"])

    # Propagate the independently resampled training amplitude in each paired
    # validation replica while retaining the same point estimate.
    values_val = np.einsum("nbt,b->nt", val, weights)
    boot_val_mean = values_val[val_indices].mean(axis=1)
    fb = shape(mass_draws, np.arange(values_val.shape[-1]), PROTOCOL["geometry"][3])
    qboot_propagated = boot_val_mean[:, PROTOCOL["score_window"]] / (
        train_amp_draws[:, None] * fb[:, PROTOCOL["score_window"]])

    refit = risk_with_fixed_amplitude(
        val, weights, reference_mass, mass_draws, val_indices, PROTOCOL,
        train_amp, train_amp_se, amplitude_source="test", return_draws=True)
    target_refit = _q_target(refit["amplitude"], reference_mass)

    methods = {}
    for name, point, qboot, target, risk_value in (
            ("train_frozen_conditional", np.asarray(frozen["q"]), qboot_frozen,
             target_frozen, frozen["risk"]),
            ("train_amplitude_propagated", np.asarray(frozen["q"]), qboot_propagated,
             target_frozen, float(np.mean(qboot_propagated.var(axis=0, ddof=1))
                                  + np.mean((np.asarray(frozen["q"]) - 1)**2))),
            ("validation_refit", np.asarray(refit["q"]), np.asarray(refit["q_boot"]),
             target_refit, refit["risk"])):
        covered, width = _coverage(qboot, target)
        interval = np.quantile(qboot, [0.025, 0.975], axis=0)
        unity_covered = (interval[0] <= 1.0) & (1.0 <= interval[1])
        methods[name] = {
            "timepoint_coverage": covered.astype(bool).tolist(),
            "all_windows_covered": bool(np.all(covered)),
            "reference_unity_all_windows_in_interval": bool(np.all(unity_covered)),
            "mean_true_q_shape_rms_departure_from_one": float(np.sqrt(np.mean((target - 1) ** 2))),
            "mean_timepoint_coverage": float(np.mean(covered)),
            "mean_interval_width": float(np.mean(width)),
            "point_minus_replica_mean": float(np.mean(point - qboot.mean(axis=0))),
            "risk": float(risk_value),
            "target_q": target.tolist(),
        }
    return {
        "n_train_blocks": int(len(train)), "n_validation_blocks": int(len(val)),
        "reference_mass": float(reference_mass), "true_mass": TRUE_MASS,
        "reference_offset": float(reference_offset),
        "train_amplitude": float(train_amp), "train_amplitude_bootstrap_se": train_amp_se,
        "train_amplitude_bootstrap_draws": train_amp_draws.tolist(),
        "train_amplitude_z": float(abs(train_amp) / train_amp_se) if train_amp_se else None,
        "methods": methods,
    }


def _cp(successes, total):
    alpha = 0.05
    lo = 0.0 if successes == 0 else float(beta.ppf(alpha / 2, successes, total - successes + 1))
    hi = 1.0 if successes == total else float(beta.ppf(1 - alpha / 2, successes + 1, total - successes))
    return [lo, hi]


def _summarize(samples):
    n = len(samples)
    methods = {}
    for name in ("train_frozen_conditional", "train_amplitude_propagated", "validation_refit"):
        rows = [row["methods"][name] for row in samples]
        covered = sum(row["all_windows_covered"] for row in rows)
        point_bias = np.asarray([row["point_minus_replica_mean"] for row in rows])
        time_cov = np.asarray([row["mean_timepoint_coverage"] for row in rows])
        widths = np.asarray([row["mean_interval_width"] for row in rows])
        methods[name] = {
            "n_dataset": n,
            "all_windows_covered": covered,
            "all_windows_coverage": covered / n,
            "all_windows_cp95": _cp(covered, n),
            "reference_unity_all_windows_in_interval_count": int(sum(
                row["reference_unity_all_windows_in_interval"] for row in rows)),
            "reference_unity_all_windows_in_interval_fraction": float(np.mean([
                row["reference_unity_all_windows_in_interval"] for row in rows])),
            "reference_unity_all_windows_cp95": _cp(sum(
                row["reference_unity_all_windows_in_interval"] for row in rows), n),
            "mean_true_q_shape_rms_departure_from_one": float(np.mean([
                row["mean_true_q_shape_rms_departure_from_one"] for row in rows])),
            "mean_timepoint_coverage": float(time_cov.mean()),
            "mean_timepoint_coverage_se_across_datasets": float(time_cov.std(ddof=1) / np.sqrt(n)),
            "point_minus_replica_bias_mean": float(point_bias.mean()),
            "point_minus_replica_bias_se": float(point_bias.std(ddof=1) / np.sqrt(n)),
            "mean_interval_width": float(widths.mean()),
            "mean_interval_width_se": float(widths.std(ddof=1) / np.sqrt(n)),
        }
    amps = np.asarray([row["train_amplitude_bootstrap_se"] for row in samples])
    return {"methods": methods,
            "mean_train_amplitude_bootstrap_se": float(amps.mean()),
            "mean_train_amplitude_bootstrap_se_mc_se": float(amps.std(ddof=1) / np.sqrt(n))}


def run(seed=20261119, n_dataset=N_DATASET, n_boot=N_BOOT):
    root_seed = int(seed)
    rows = {}
    scenarios = []
    for rho in CONFIG_RHOS:
        for block_length in BLOCK_LENGTHS:
            scenarios.append((f"correlated/rho_{rho}/block_{block_length}",
                              rho, block_length, 0.0))
    for offset in WRONG_MASS_OFFSETS:
        scenarios.append((f"wrong_reference/offset_{offset}", 0.5, 5, offset))
    for i, (key, rho, block_length, offset) in enumerate(scenarios):
        rng = np.random.default_rng(root_seed + 1009 * (i + 1))
        samples = [one_dataset(rng, block_length=block_length, config_rho=rho,
                               reference_offset=offset, n_boot=n_boot) for _ in range(n_dataset)]
        rows[key] = {
            "config_rho": rho, "time_rho": TIME_RHO,
            "block_length": block_length, "reference_offset": offset,
            "n_dataset": n_dataset, "n_boot": n_boot,
            "summary": _summarize(samples), "datasets": samples,
        }
        print(key, {m: round(v["all_windows_coverage"], 3)
                    for m, v in rows[key]["summary"]["methods"].items()})
    return {
        "schema": "optgauss-fit-state-stress-v1",
        "scope": "synthetic CPU stress test; no production gauge data or physical calibration",
        "seed": root_seed,
        "design": {
            "independent_datasets_per_cell": n_dataset,
            "bootstrap_draws_per_dataset": n_boot,
            "configurations_per_dataset": NCFG,
            "noise_fraction": NOISE,
            "true_mass": TRUE_MASS,
            "true_amplitude": TRUE_AMPLITUDE,
            "temporal_ar1_rho": TIME_RHO,
            "configuration_ar1_values": list(CONFIG_RHOS),
            "block_lengths": list(BLOCK_LENGTHS),
            "wrong_reference_mass_offsets": list(WRONG_MASS_OFFSETS),
            "train_validation_split": "ordered first/last block segments with a two-block embargo",
            "training_amplitude_propagation": "paired bootstrap resample of training blocks and mass draw per validation replica",
            "sample_size_goal": "200 independent datasets per cell; exact dataset-level CP interval reported; near 95% coverage half-width is about 0.03",
        },
        "source_sha256": {
            "stress_script": _sha256(Path(__file__)),
            "estimator_script": _sha256(Path(__file__).with_name("estimator_regression.py")),
            "fixed_amplitude_estimator": _sha256(Path(__file__).with_name("unified.py")),
        },
        "rows": rows,
        "interpretation_limits": [
            "Synthetic smooth single-state correlator and one smear channel only.",
            "Wrong-reference targets use the known true signal profile divided by the fitted wrong-reference normalization; this measures conditional q-window coverage, not whether the reference model is physically valid.",
            "Time points within one dataset are correlated; exact binomial intervals use one all-score-window-covered indicator per independent dataset.",
            "Non-overlapping block means only approximate decorrelation; the configuration AR scans intentionally show sensitivity to this choice.",
        ],
    }


def _plot_block_coverage(result, path):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    styles = {"train_frozen_conditional": ("#315a8a", "-", "o"),
              "train_amplitude_propagated": ("#b15b32", "--", "s"),
              "validation_refit": ("#39806a", ":", "^")}
    for ax, metric in zip(axes, ("all_windows_coverage", "mean_timepoint_coverage")):
        for rho in CONFIG_RHOS:
            for method, (color, linestyle, marker) in styles.items():
                means, lows, highs = [], [], []
                for block_length in BLOCK_LENGTHS:
                    key = f"correlated/rho_{rho}/block_{block_length}"
                    summary = result["rows"][key]["summary"]["methods"][method]
                    if metric == "all_windows_coverage":
                        value = summary[metric]
                        lo, hi = summary["all_windows_cp95"]
                    else:
                        value = summary[metric]
                        se = summary["mean_timepoint_coverage_se_across_datasets"]
                        lo, hi = max(0.0, value - 1.96 * se), min(1.0, value + 1.96 * se)
                    means.append(value); lows.append(lo); highs.append(hi)
                ax.errorbar(BLOCK_LENGTHS, means,
                            yerr=[np.asarray(means)-lows, np.asarray(highs)-means],
                            color=color, linestyle=linestyle, marker=marker, capsize=2,
                            alpha=0.9, label=f"rho={rho}, {method}")
        ax.axhline(0.95, color="black", linewidth=1, alpha=.55, linestyle="--")
        ax.set_xticks(BLOCK_LENGTHS)
        ax.set_ylim(0, 1.04)
        ax.grid(alpha=.25)
    axes[0].set(title="All score-window times covered", ylabel="fraction of independent datasets")
    axes[1].set(title="Mean per-time coverage")
    for ax in axes:
        ax.set_xlabel("configuration block length")
    axes[1].legend(fontsize=7, bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.suptitle("Correlated-noise and block-length sensitivity (200 datasets/cell)")
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _plot_wrong_reference(result, path):
    fig, axes = plt.subplots(1, 3, figsize=(15.0, 4.2))
    methods = ("train_frozen_conditional", "train_amplitude_propagated", "validation_refit")
    colors = ("#315a8a", "#b15b32", "#39806a")
    for method, color in zip(methods, colors):
        rows = [result["rows"][f"wrong_reference/offset_{offset}"]["summary"]["methods"][method]
                for offset in WRONG_MASS_OFFSETS]
        axes[0].errorbar(WRONG_MASS_OFFSETS,
                         [row["all_windows_coverage"] for row in rows],
                         yerr=[[row["all_windows_coverage"]-row["all_windows_cp95"][0] for row in rows],
                               [row["all_windows_cp95"][1]-row["all_windows_coverage"] for row in rows]],
                         color=color, marker="o", capsize=3, label=method)
        axes[1].plot(WRONG_MASS_OFFSETS,
                     [row["mean_true_q_shape_rms_departure_from_one"] for row in rows],
                     color=color, marker="o", label=method)
        axes[2].errorbar(WRONG_MASS_OFFSETS,
                         [row["reference_unity_all_windows_in_interval_fraction"] for row in rows],
                         yerr=[[row["reference_unity_all_windows_in_interval_fraction"]-row["reference_unity_all_windows_cp95"][0] for row in rows],
                               [row["reference_unity_all_windows_cp95"][1]-row["reference_unity_all_windows_in_interval_fraction"] for row in rows]],
                         color=color, marker="o", capsize=3, label=method)
    axes[0].axhline(.95, color="black", linestyle="--", linewidth=1, alpha=.55)
    axes[2].axhline(.95, color="black", linestyle="--", linewidth=1, alpha=.55)
    for ax in axes:
        ax.set_xlabel("assumed reference mass − true mass")
        ax.grid(alpha=.25)
    axes[0].set(title="Coverage of true q profile", ylabel="fraction of datasets", ylim=(0, 1.04))
    axes[1].set(title="True q shape departure", ylabel="RMS of q_true(t) - 1")
    axes[2].set(title="Does interval contain q=1?", ylabel="fraction of datasets", ylim=(0, 1.04))
    axes[2].legend(fontsize=8)
    fig.suptitle("Coverage under a deliberately wrong reference (rho_config=0.5, block=5)")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main():
    if OUT.exists() and any(OUT.iterdir()):
        raise FileExistsError(f"{OUT} already contains results; choose a new output directory")
    result = run()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "stress_regression.json").write_text(json.dumps(result, indent=2) + "\n")
    _plot_block_coverage(result, OUT / "fig_correlated_block_sensitivity.png")
    _plot_wrong_reference(result, OUT / "fig_wrong_reference_coverage.png")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
