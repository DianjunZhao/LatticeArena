"""Matched-block randomization inference for a synthetic C3 energy score.

The primary test is a studentized sign-flip randomization test on independent
paired configuration blocks. It is exact for the declared sharp exchangeable
null, not for every weak null of equal expected risk.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import beta, t as student_t

from .energy_experiment import correlators, protocol as data_protocol
from .energy_target import energy_delta
from .statistics import ReferenceFit, blocks, fold, bootstrap_indices


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/pion_projection/block_randomization_score_20261120_v1"
BASE_SEED = 2026112023
N_DATASET = 400
N_BLOCKS = 24
BLOCK_LENGTH = 5
N_PERM = 999
N_BOOT = 999
E0 = 0.80
TAU_E = 0.01
ALPHA = 0.05
NOISE = 0.02
BETTER_NOISE = 0.01
ARM_CORRELATIONS = (0.5, 0.9)
ANCHOR_BIASES = (-0.02, 0.0, 0.02)
METHODS = ("block_signflip_studentized", "paired_block_t", "paired_block_bootstrap")
WORLD_SPECS = {
    "equal_gaussian_null": {"energies": (0.80, 1.30), "noise": 0.02, "candidate_noise": 0.02,
                             "innovation": "gaussian", "anchor_sigma": 0.0,
                             "anchor_biases": ANCHOR_BIASES},
    "known_lower_noise": {"energies": (0.80, 1.30), "noise": 0.02, "candidate_noise": 0.01,
                          "innovation": "gaussian", "anchor_sigma": 0.0,
                          "anchor_biases": (0.0,)},
    "common_truth_shift_null": {"energies": (0.82, 1.30), "noise": 0.02, "candidate_noise": 0.02,
                                "innovation": "gaussian", "anchor_sigma": 0.0,
                                "anchor_biases": (0.0,)},
    "equal_student_t5_null": {"energies": (0.80, 1.30), "noise": 0.02, "candidate_noise": 0.02,
                              "innovation": "student_t5", "anchor_sigma": 0.0,
                              "anchor_biases": ANCHOR_BIASES},
    "uncertain_anchor_null": {"energies": (0.80, 1.30), "noise": 0.02, "candidate_noise": 0.02,
                              "innovation": "gaussian", "anchor_sigma": 0.01,
                              "anchor_biases": (0.0,)},
}
SOURCE_FILES = (
    "tasks/pion_projection/block_randomization_score.py",
    "tasks/pion_projection/energy_experiment.py",
    "tasks/pion_projection/energy_target.py",
    "tasks/pion_projection/statistics.py",
    "tasks/pion_projection/reference.py",
    "results/pion_projection/s16t16_gevp200/development_provenance.json",
)
OUTPUTS = ("raw_outcomes.json", "summary.json", "block_randomization_diagnostics.png", "README.md")


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_manifest() -> dict[str, str]:
    return {name: sha256(ROOT / name) for name in SOURCE_FILES}


def protocol() -> dict:
    p = data_protocol()
    return {
        "schema": "pion-c3-paired-block-randomization-score-v1",
        "classification": "synthetic CPU method comparison; not physical score validation",
        "primary_question": "Does studentized block-level label randomization control false certification under the declared exchangeable sharp null, and what power does it retain under lower candidate noise?",
        "estimand": "Mean paired block energy-risk improvement: mean_j[((E_base,j-E_anchor)^2-(E_candidate,j-E_anchor)^2)/tau_E^2], where each E is a single-cosh fit to one independent configuration block using one pooled, label-invariant reference covariance.",
        "design": {
            "independent_dataset_ids_per_world_correlation_cell": N_DATASET,
            "worlds": WORLD_SPECS,
            "matched_arm_noise_correlations": list(ARM_CORRELATIONS),
            "independent_paired_blocks": N_BLOCKS,
            "configurations_per_block": BLOCK_LENGTH,
            "configuration_AR1_within_block": 0.5,
            "cross_block_correlation": 0.0,
            "studentized_signflip_randomizations_per_dataset": N_PERM,
            "paired_block_bootstrap_draws_per_dataset": N_BOOT,
            "true_ground_energy_anchor_center": E0,
            "tau_energy": TAU_E,
            "alpha": ALPHA,
            "block_generation": "Each block has an independent shared latent noise vector and independent arm residuals. Within a block, config-index noise is AR(1) rho=0.5 and resets at the next block. Student-t5 innovations are scaled to unit variance. Under equal-arm worlds, the full paired block vectors are exchangeable under arm-label swap.",
            "anchor_rule": "Fixed offsets are evaluated on the same fitted block masses; uncertain_anchor_null samples one independent anchor per outer dataset and holds it fixed across both arms, blocks, and all randomizations.",
        },
        "methods": {
            "block_signflip_studentized": "Primary. T=mean(d_j)/(sd(d_j)/sqrt(J)); randomly swap baseline/candidate labels for whole paired blocks, equivalently sign-flip d_j. Monte Carlo p=(1+#(T_perm>=T_obs))/(N_PERM+1); certify iff p<=0.05.",
            "paired_block_t": "One-sided Student-t test of the same J paired block contributions; benchmark only.",
            "paired_block_bootstrap": "Resample the J paired block contributions with replacement; certify iff the 5th percentile of bootstrap means is positive.",
            "sharp_null_assumption": "The sign-flip test is finite-sample valid only when paired block labels are exchangeable under the sharp no-arm-effect null and blocks are independent. It does not guarantee type-I control for every weak null with equal mean risk but nonexchangeable arms.",
            "multiplicity_intervals": "Exact two-sided CP95 intervals use Bonferroni families within each world: 18 rates for worlds with three anchor offsets, otherwise 6 rates. They quantify Monte Carlo uncertainty; the per-cell test itself uses alpha=0.05.",
        },
        "precision": "N=400 outer datasets per world x correlation cell, no top-up. At event rate 0.05, marginal binomial CP95 half-width is about 0.022; familywise intervals are wider. Invalid fits remain in planned denominators and count as non-certifications.",
        "seeds": {"base": BASE_SEED, "rule": "SeedSequence([BASE_SEED,world_index,correlation_index,dataset_id,stream]); streams 0-3 generate shared noise, baseline residual, candidate residual, sign-flip masks; stream 4 generates and records an explicit bootstrap-index seed; stream 5 generates the uncertain anchor."},
        "evaluation": "All 400 dataset IDs per world/correlation cell are generated after the protocol and source hashes are frozen. No method threshold or tuning parameter is selected from these outcomes; they are held-out evaluation data for the fully specified tests.",
        "frozen_fit_protocol": {key: p[key] for key in ("geometry", "reference_basis", "reference_windows", "reference_nominal_window", "mass_bounds", "covariance_shrinkage")},
        "outputs": list(OUTPUTS),
        "output_directory": str(OUT.relative_to(ROOT)),
        "frozen_sources": list(SOURCE_FILES),
    }


def cp_interval(k: int, n: int, family_size: int = 1) -> list[float]:
    alpha = 0.05 / family_size
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return [lo, hi]


def bootstrap_mean_ci(values: np.ndarray, seed: int, family_size: int) -> list[float]:
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(values), size=(10000, len(values)))
    means = values[idx].mean(axis=1)
    tail = 0.05 / (2 * family_size)
    return [float(np.quantile(means, tail)), float(np.quantile(means, 1 - tail))]


def innovations(rng: np.random.Generator, shape_: tuple[int, ...], kind: str) -> np.ndarray:
    if kind == "gaussian":
        return rng.normal(size=shape_)
    if kind == "student_t5":
        return rng.standard_t(df=5, size=shape_) * np.sqrt(3 / 5)
    raise ValueError(f"unknown innovation distribution: {kind}")


def blocked_ar1(rng: np.random.Generator, kind: str, rho: float = 0.5) -> np.ndarray:
    eps = innovations(rng, (N_BLOCKS, BLOCK_LENGTH, 7, 16), kind)
    out = np.empty_like(eps)
    out[:, 0] = eps[:, 0]
    scale = np.sqrt(1 - rho * rho)
    for i in range(1, BLOCK_LENGTH):
        out[:, i] = rho * out[:, i - 1] + scale * eps[:, i]
    return out


def make_paired_blocks(rngs: list[np.random.Generator], world: str,
                       arm_correlation: float) -> tuple[np.ndarray, np.ndarray, float]:
    spec = WORLD_SPECS[world]
    template = correlators(np.random.default_rng(0), ncfg=1,
                           energies=spec["energies"], noise=0.0)[0]
    common = blocked_ar1(rngs[0], spec["innovation"])
    residual_base = blocked_ar1(rngs[1], spec["innovation"])
    residual_candidate = blocked_ar1(rngs[2], spec["innovation"])
    shared_weight = np.sqrt(arm_correlation)
    residual_weight = np.sqrt(1 - arm_correlation)
    base_noise = shared_weight * common + residual_weight * residual_base
    candidate_noise = shared_weight * common + residual_weight * residual_candidate
    base_raw = template[None, None] * (1 + spec["noise"] * base_noise)
    candidate_raw = template[None, None] * (1 + spec["candidate_noise"] * candidate_noise)
    base_raw = base_raw.reshape(N_BLOCKS * BLOCK_LENGTH, *template.shape)
    candidate_raw = candidate_raw.reshape(N_BLOCKS * BLOCK_LENGTH, *template.shape)
    anchor_rng = rngs[5]
    anchor = E0 + (anchor_rng.normal(0, spec["anchor_sigma"]) if spec["anchor_sigma"] else 0.0)
    return base_raw, candidate_raw, float(anchor)


def block_masses(base_raw: np.ndarray, candidate_raw: np.ndarray, config: dict) -> tuple[np.ndarray, np.ndarray]:
    base_blocks = blocks(fold(base_raw), BLOCK_LENGTH)
    candidate_blocks = blocks(fold(candidate_raw), BLOCK_LENGTH)
    pooled_reference = ReferenceFit(np.concatenate((base_blocks, candidate_blocks), axis=0), config,
                                   config["reference_windows"][config["reference_nominal_window"]])

    def fit_rows(samples: np.ndarray) -> np.ndarray:
        masses = []
        for sample in samples:
            selected = sample[pooled_reference.basis][:, pooled_reference.window]
            normalized = (selected / pooled_reference.scales[:, None]).reshape(-1)
            mass, _ = pooled_reference.fit(normalized)
            masses.append(float(mass))
        return np.asarray(masses)

    return fit_rows(base_blocks), fit_rows(candidate_blocks)


def statistics_for_anchor(d: np.ndarray, sign_matrix: np.ndarray, bootstrap_matrix: np.ndarray) -> dict:
    n = len(d)
    mean = float(d.mean())
    sd = float(d.std(ddof=1))
    se = sd / np.sqrt(n)
    t_obs = mean / se if se > 0 else (np.inf if mean > 0 else (-np.inf if mean < 0 else 0.0))
    p_t = (float(student_t.sf(t_obs, df=n - 1)) if np.isfinite(t_obs)
           else (0.0 if t_obs > 0 else 1.0))

    signed = sign_matrix * d[None, :]
    perm_mean = signed.mean(axis=1)
    perm_sd = signed.std(axis=1, ddof=1)
    perm_se = perm_sd / np.sqrt(n)
    perm_t = np.empty_like(perm_mean)
    nonzero_se = perm_se > 0
    perm_t[nonzero_se] = perm_mean[nonzero_se] / perm_se[nonzero_se]
    zero_se_mean = perm_mean[~nonzero_se]
    perm_t[~nonzero_se] = np.where(zero_se_mean > 0, np.inf,
                                    np.where(zero_se_mean < 0, -np.inf, 0.0))
    p_signflip = float((1 + np.sum(perm_t >= t_obs - 1e-12)) / (len(perm_t) + 1))

    boot_mean = d[bootstrap_matrix].mean(axis=1)
    lower = float(np.quantile(boot_mean, ALPHA))
    return {
        "mean_block_delta": mean,
        "sd_block_delta": sd,
        "studentized_t": float(t_obs),
        "signflip_p": p_signflip,
        "paired_t_p": p_t,
        "bootstrap_lower_05": lower,
        "certified": {
            "block_signflip_studentized": bool(p_signflip <= ALPHA),
            "paired_block_t": bool(p_t <= ALPHA),
            "paired_block_bootstrap": bool(lower > 0),
        },
    }


def prepare() -> None:
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite {OUT}")
    OUT.mkdir(parents=True)
    frozen = protocol()
    (OUT / "protocol.json").write_text(json.dumps(frozen, indent=2, sort_keys=True) + "\n")
    prereg = {"protocol_sha256": hashlib.sha256(canonical(frozen)).hexdigest(),
              "source_sha256": source_manifest()}
    (OUT / "preregistration.json").write_text(json.dumps(prereg, indent=2, sort_keys=True) + "\n")
    print("prepared", OUT.relative_to(ROOT), prereg["protocol_sha256"])


def run() -> None:
    frozen = json.loads((OUT / "protocol.json").read_text())
    prereg = json.loads((OUT / "preregistration.json").read_text())
    if prereg["protocol_sha256"] != hashlib.sha256(canonical(frozen)).hexdigest():
        raise RuntimeError("protocol hash mismatch")
    if prereg["source_sha256"] != source_manifest():
        raise RuntimeError("source hash mismatch")
    if any((OUT / name).exists() for name in OUTPUTS):
        raise FileExistsError("final outputs exist; refusing overwrite")

    config = data_protocol()
    rows: list[dict] = []
    world_names = tuple(WORLD_SPECS)
    for world_index, world in enumerate(world_names):
        spec = WORLD_SPECS[world]
        for correlation_index, arm_corr in enumerate(ARM_CORRELATIONS):
            for dataset_id in range(N_DATASET):
                stream_seeds = [[BASE_SEED, world_index, correlation_index, dataset_id, stream]
                                for stream in range(6)]
                rngs = [np.random.default_rng(np.random.SeedSequence(seed)) for seed in stream_seeds]
                try:
                    raw_base, raw_candidate, uncertain_anchor = make_paired_blocks(rngs, world, arm_corr)
                    base_mass, candidate_mass = block_masses(raw_base, raw_candidate, config)
                    sign_rng = np.random.default_rng(np.random.SeedSequence(stream_seeds[3]))
                    sign_matrix = sign_rng.choice(np.asarray([-1.0, 1.0]), size=(N_PERM, N_BLOCKS))
                    bootstrap_index_seed = int(rngs[4].integers(0, 2**31 - 1))
                    bootstrap_matrix = bootstrap_indices(N_BLOCKS, N_BOOT, bootstrap_index_seed)
                    offsets = spec["anchor_biases"]
                    for offset in offsets:
                        anchor = uncertain_anchor + offset
                        d = energy_delta(base_mass, candidate_mass,
                                         np.full(N_BLOCKS, anchor), TAU_E)
                        outcome = statistics_for_anchor(d, sign_matrix, bootstrap_matrix)
                        rows.append({
                            "world": world,
                            "arm_correlation": arm_corr,
                            "dataset_id": dataset_id,
                            "anchor_bias": float(offset),
                            "anchor_sigma": spec["anchor_sigma"],
                            "anchor_realized": anchor,
                            "innovation": spec["innovation"],
                            "baseline_noise": spec["noise"],
                            "candidate_noise": spec["candidate_noise"],
                            "nblocks": N_BLOCKS,
                            "status": "VALID",
                            "base_block_masses": base_mass.tolist(),
                            "candidate_block_masses": candidate_mass.tolist(),
                            "block_delta": d.tolist(),
                            **outcome,
                            "seeds": {"streams": stream_seeds,
                                      "signflip_matrix": "generated by stream 3",
                                      "bootstrap_index_seed": bootstrap_index_seed,
                                      "anchor_stream": stream_seeds[5]},
                        })
                except Exception as exc:
                    for offset in spec["anchor_biases"]:
                        rows.append({"world": world, "arm_correlation": arm_corr,
                                     "dataset_id": dataset_id, "anchor_bias": float(offset),
                                     "anchor_sigma": spec["anchor_sigma"], "status": "INVALID",
                                     "reason": f"{type(exc).__name__}: {exc}",
                                     "seeds": {"streams": stream_seeds}})
                if (dataset_id + 1) % 100 == 0:
                    print(f"{world}, arm_rho={arm_corr}: {dataset_id+1}/{N_DATASET}", flush=True)

    summary = summarize(rows)
    (OUT / "raw_outcomes.json").write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    write_figure(summary)
    (OUT / "README.md").write_text(render_readme(summary))
    provenance = {
        "protocol_sha256": prereg["protocol_sha256"],
        "preregistered_source_sha256": prereg["source_sha256"],
        "current_source_sha256": source_manifest(),
        "planned_datasets": N_DATASET * len(WORLD_SPECS) * len(ARM_CORRELATIONS),
        "completed_rows": len(rows),
        "artifact_sha256": {name: sha256(OUT / name) for name in OUTPUTS},
    }
    (OUT / "execution_provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    print("completed", OUT.relative_to(ROOT))


def family_size(world: str) -> int:
    return len(ARM_CORRELATIONS) * len(METHODS) * len(WORLD_SPECS[world]["anchor_biases"])


def summarize(rows: list[dict]) -> dict:
    cells = []
    for world, spec in WORLD_SPECS.items():
        for anchor_bias in spec["anchor_biases"]:
            for rho in ARM_CORRELATIONS:
                for method in METHODS:
                    selected = [r for r in rows if r["world"] == world and r["anchor_bias"] == anchor_bias
                                and r["arm_correlation"] == rho]
                    valid = [r for r in selected if r["status"] == "VALID"]
                    events = sum(r["certified"][method] for r in valid)
                    values = np.asarray([r["mean_block_delta"] for r in valid], dtype=float)
                    cells.append({
                        "world": world, "anchor_bias": anchor_bias, "arm_correlation": rho,
                        "method": method, "n_planned": N_DATASET, "n_valid": len(valid),
                        "n_invalid": N_DATASET-len(valid), "certified": events,
                        "rate_planned": events/N_DATASET,
                        "rate_valid": events/len(valid) if valid else None,
                        "cp95_marginal": cp_interval(events, len(valid), 1) if valid else None,
                        "cp95_familywise": cp_interval(events, N_DATASET, family_size(world)),
                        "mean_block_delta": float(values.mean()) if len(values) else None,
                        "mean_delta_familywise_dataset_ci95": bootstrap_mean_ci(
                            values, BASE_SEED+50000+len(cells),
                            max(1, len(spec["anchor_biases"])*len(ARM_CORRELATIONS))) if len(values) else None,
                    })
    contrasts = []
    method_pairs = (("paired_block_t", "block_signflip_studentized"),
                    ("paired_block_bootstrap", "block_signflip_studentized"))
    global_family = 2 * len(ARM_CORRELATIONS) * sum(len(spec["anchor_biases"]) for spec in WORLD_SPECS.values())
    for world, spec in WORLD_SPECS.items():
        for anchor_bias in spec["anchor_biases"]:
            for rho in ARM_CORRELATIONS:
                selected = [r for r in rows if r["world"] == world and r["anchor_bias"] == anchor_bias
                            and r["arm_correlation"] == rho and r["status"] == "VALID"]
                by_id = {r["dataset_id"]: r for r in selected}
                for method, reference in method_pairs:
                    differences = np.asarray([
                        float(by_id[i]["certified"][method])-
                        float(by_id[i]["certified"][reference])
                        for i in sorted(by_id)
                    ])
                    contrasts.append({
                        "world": world, "anchor_bias": anchor_bias, "arm_correlation": rho,
                        "method": method, "reference_method": reference,
                        "n_paired": len(differences),
                        "rate_difference": float(differences.mean()) if len(differences) else None,
                        "familywise_dataset_bootstrap_ci95": bootstrap_mean_ci(
                            differences, BASE_SEED+70000+len(contrasts), global_family)
                        if len(differences) else None,
                        "method_only": int(np.sum(differences == 1)),
                        "signflip_only": int(np.sum(differences == -1)),
                    })
    return {"schema": "pion-c3-block-randomization-summary-v1",
            "classification": "synthetic CPU method comparison; not physical score validation",
            "protocol_sha256": hashlib.sha256(canonical(protocol())).hexdigest(),
            "cells": cells, "method_contrasts": contrasts}


def write_figure(summary: dict) -> None:
    colors = {"block_signflip_studentized": "#228833", "paired_block_t": "#4477AA",
              "paired_block_bootstrap": "#CC6677"}
    labels = {"block_signflip_studentized": "Studentized block sign-flip",
              "paired_block_t": "Paired block t-test",
              "paired_block_bootstrap": "Paired block bootstrap"}
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    ax = axes[0, 0]
    null_worlds = ("equal_gaussian_null", "common_truth_shift_null",
                   "equal_student_t5_null", "uncertain_anchor_null")
    categories = []
    for world in null_worlds:
        bias = 0.0
        for rho in ARM_CORRELATIONS:
            categories.append((world, rho, bias))
    x = np.arange(len(categories))
    for method in METHODS:
        values, lows, highs = [], [], []
        for world, rho, bias in categories:
            cell = next(c for c in summary["cells"] if c["world"] == world and c["anchor_bias"] == bias
                        and c["arm_correlation"] == rho and c["method"] == method)
            values.append(cell["rate_planned"])
            lows.append(cell["cp95_familywise"][0])
            highs.append(cell["cp95_familywise"][1])
        values = np.asarray(values)
        shift = {METHODS[0]: -0.22, METHODS[1]: 0.0, METHODS[2]: 0.22}[method]
        ax.errorbar(x+shift, values,
                    yerr=np.asarray([values-np.asarray(lows), np.asarray(highs)-values]),
                    marker="o", capsize=2, color=colors[method], label=labels[method])
    ax.axhline(ALPHA, color="black", linestyle=":", linewidth=1)
    ax.set(xticks=x, xticklabels=[f"{w.replace('_null','').replace('_','\\n')}\nρ={r:.1f}"
                                  for w, r, _ in categories],
           ylabel="Certification rate", title="Sharp-null size across synthetic worlds")
    ax.tick_params(axis="x", labelsize=7)
    ax.legend(fontsize=8)

    ax = axes[0, 1]
    for method in METHODS:
        for rho, linestyle in ((0.5, "--"), (0.9, "-")):
            chosen = [next(c for c in summary["cells"] if c["world"] == "equal_gaussian_null"
                           and c["anchor_bias"] == bias and c["arm_correlation"] == rho
                           and c["method"] == method) for bias in ANCHOR_BIASES]
            y = np.asarray([c["rate_planned"] for c in chosen])
            ci = [c["cp95_familywise"] for c in chosen]
            ax.errorbar(np.asarray(ANCHOR_BIASES)+(rho-0.7)*0.007, y,
                        yerr=np.asarray([[v-c[0] for v,c in zip(y,ci)],
                                         [c[1]-v for v,c in zip(y,ci)]]),
                        marker="o", linestyle=linestyle, color=colors[method],
                        label=f"{labels[method]}, ρ={rho:.1f}")
    ax.axhline(ALPHA, color="black", linestyle=":", linewidth=1)
    ax.set(xlabel="Fixed anchor offset", ylabel="False-certification rate",
           title="Anchor sensitivity under Gaussian equal-arm null")
    ax.legend(fontsize=7, ncol=2)

    ax = axes[1, 0]
    power_cells = [c for c in summary["cells"] if c["world"] == "known_lower_noise"]
    x = np.arange(len(ARM_CORRELATIONS))
    for method in METHODS:
        chosen = [next(c for c in power_cells if c["arm_correlation"] == rho and c["method"] == method)
                  for rho in ARM_CORRELATIONS]
        y = np.asarray([c["rate_planned"] for c in chosen])
        ci = [c["cp95_familywise"] for c in chosen]
        ax.errorbar(x, y,
                    yerr=np.asarray([[v-c[0] for v,c in zip(y,ci)],
                                     [c[1]-v for v,c in zip(y,ci)]]),
                    marker="o", capsize=3, color=colors[method], label=labels[method])
    ax.set(xticks=x, xticklabels=[f"ρ={r:.1f}" for r in ARM_CORRELATIONS],
           ylabel="Certification rate", title="Known lower-noise candidate power")
    ax.legend(fontsize=8)

    ax = axes[1, 1]
    display_worlds = ("equal_gaussian_null", "common_truth_shift_null",
                      "equal_student_t5_null", "known_lower_noise")
    data, ticklabels = [], []
    for world in display_worlds:
        for rho in ARM_CORRELATIONS:
            rows = [r for r in json.loads((OUT / "raw_outcomes.json").read_text())
                    if r["world"] == world and r["anchor_bias"] == 0.0 and r["arm_correlation"] == rho
                    and r["status"] == "VALID"]
            data.append([r["mean_block_delta"] for r in rows])
            ticklabels.append(world.replace("_null", "").replace("_", "\n")+f"\nρ={rho:.1f}")
    ax.boxplot(data, tick_labels=ticklabels, showfliers=False, whis=(2.5, 97.5))
    ax.axhline(0, color="black", linestyle=":", linewidth=1)
    ax.set(ylabel="Mean paired block risk improvement", title="Outer-dataset score distribution")
    ax.tick_params(axis="x", labelsize=7)
    fig.suptitle("Pion C3: studentized block randomization under exchangeable paired blocks")
    fig.tight_layout()
    fig.savefig(OUT / "block_randomization_diagnostics.png", dpi=160)
    plt.close(fig)


def render_readme(summary: dict) -> str:
    lines = [
        "# Studentized paired-block randomization for the synthetic C3 score",
        "",
        "The primary method is a studentized sign-flip randomization test on paired block-level energy-risk contributions. Each dataset has 24 independent paired blocks of 5 configurations; within-block configuration noise is AR(1) with rho=0.5 and resets between blocks. The common block covariance is estimated from both arms together and held fixed, so swapping arm labels leaves the reference fit unchanged. Under equal-arm worlds, paired block labels are exchangeable by construction.",
        "",
        "This test has finite-sample type-I control only for the declared sharp exchangeable null. It does not guarantee control for every weak null with equal expected risk but nonexchangeable arms, and cannot detect a common model/state bias shared by both methods. The paired block score uses one mass fit per independent block, so it is a different estimand from a single full-ensemble fit certificate.",
        "",
        "## Null size at anchor offset zero",
        "",
        "| World | rho | Method | Certified / planned | Rate | Familywise CP95 | Mean block delta | Dataset-bootstrap CI95 |",
        "| --- | ---: | --- | ---: | ---: | --- | ---: | --- |",
    ]
    for world in ("equal_gaussian_null", "common_truth_shift_null", "equal_student_t5_null", "uncertain_anchor_null"):
        for rho in ARM_CORRELATIONS:
            for method in METHODS:
                c = next(c for c in summary["cells"] if c["world"] == world and c["anchor_bias"] == 0.0
                         and c["arm_correlation"] == rho and c["method"] == method)
                ci, dci = c["cp95_familywise"], c["mean_delta_familywise_dataset_ci95"]
                lines.append(f"| {world} | {rho:.1f} | {method} | {c['certified']}/{c['n_planned']} | {c['rate_planned']:.3f} | [{ci[0]:.3f},{ci[1]:.3f}] | {c['mean_block_delta']:.5f} | [{dci[0]:.5f},{dci[1]:.5f}] |")
    lines += ["", "## Known lower-noise candidate power", "",
              "| rho | Method | Certified / planned | Rate | Familywise CP95 |",
              "| ---: | --- | ---: | ---: | --- |"]
    for rho in ARM_CORRELATIONS:
        for method in METHODS:
            c = next(c for c in summary["cells"] if c["world"] == "known_lower_noise"
                     and c["arm_correlation"] == rho and c["method"] == method)
            ci = c["cp95_familywise"]
            lines.append(f"| {rho:.1f} | {method} | {c['certified']}/{c['n_planned']} | {c['rate_planned']:.3f} | [{ci[0]:.3f},{ci[1]:.3f}] |")
    lines += ["", "![Null size, anchor sensitivity, power, and score distributions](block_randomization_diagnostics.png)",
              "", "## Interpretation", "",
              "Compare the sign-flip result with the paired t and paired block-bootstrap controls, but do not select a method by the same calibration outcomes. The common-truth-shift world tests label symmetry under an anchor/model mismatch; a valid null result there is evidence only for no relative arm effect, not for physical accuracy. The Student-t5 world tests heavier-tailed innovations while retaining independent exchangeable blocks. The uncertain-anchor world samples one anchor independently per outer dataset and holds it common across both arms and all randomizations.",
              "", "All event-rate intervals are Monte Carlo intervals for the declared generator, not physical coverage. Invalid fits are retained in the planned denominator. Raw block masses, block deltas, randomization seeds, protocol/source hashes, and failure reasons are stored. Verify with `python -B -m tasks.pion_projection.block_randomization_score --verify`."]
    return "\n".join(lines) + "\n"


def verify() -> None:
    frozen = json.loads((OUT / "protocol.json").read_text())
    prereg = json.loads((OUT / "preregistration.json").read_text())
    if hashlib.sha256(canonical(frozen)).hexdigest() != prereg["protocol_sha256"]:
        raise RuntimeError("protocol hash mismatch")
    if prereg["source_sha256"] != source_manifest():
        raise RuntimeError("source hash mismatch")
    provenance = json.loads((OUT / "execution_provenance.json").read_text())
    if provenance["current_source_sha256"] != source_manifest():
        raise RuntimeError("source changed after run")
    for name, digest in provenance["artifact_sha256"].items():
        if sha256(OUT / name) != digest:
            raise RuntimeError(f"artifact hash mismatch: {name}")
    rows = json.loads((OUT / "raw_outcomes.json").read_text())
    summary = json.loads((OUT / "summary.json").read_text())
    expected = sum(len(spec["anchor_biases"]) for spec in WORLD_SPECS.values()) * \
        len(ARM_CORRELATIONS) * N_DATASET
    if len(rows) != expected:
        raise RuntimeError(f"raw row count mismatch: {len(rows)} != {expected}")
    for c in summary["cells"]:
        selected = [r for r in rows if r["world"] == c["world"] and r["anchor_bias"] == c["anchor_bias"]
                    and r["arm_correlation"] == c["arm_correlation"]]
        valid = [r for r in selected if r["status"] == "VALID"]
        if len(selected) != N_DATASET or len(valid) != c["n_valid"]:
            raise RuntimeError("cell planned/valid count mismatch")
        count = sum(r["certified"][c["method"]] for r in valid)
        if count != c["certified"]:
            raise RuntimeError("cell certification count mismatch")
    print(f"verified hashes, {len(WORLD_SPECS)} worlds x {len(ARM_CORRELATIONS)} correlations x {N_DATASET} datasets/cell")


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", action="store_true")
    group.add_argument("--run", action="store_true")
    group.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.prepare:
        prepare()
    elif args.run:
        run()
    else:
        verify()


if __name__ == "__main__":
    main()
