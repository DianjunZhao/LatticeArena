"""Weak-null stress test for robust block-level risk certificates.

The estimand is the mean paired block risk improvement. The generator includes
an iid, mean-zero but strongly left-skewed distribution where most blocks show
a small positive improvement and a rare block contributes a larger negative
effect. This deliberately separates a weak mean null from sign-exchangeability.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy
from scipy.stats import beta, t as student_t


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/pion_projection/weak_null_nonexchangeable_20261120_v1"
BASE_SEED = 2026112020
N_DATASETS = 3000
N_BLOCKS = (24, 48)
N_PERMUTATIONS = 1999
N_BOOTSTRAPS = 1999
N_MOM_GROUPS = 9
ALPHA = 0.05
MOM_SIGMA_UPPER = 1.0
RARE_PROBABILITY = 0.10
COMMON_EFFECT = 0.30
RARE_EFFECT = -2.70
ADDED_GAUSSIAN_SD = 0.20
RARE_WORLD_SD = float(np.sqrt(
    RARE_PROBABILITY * RARE_EFFECT**2
    + (1 - RARE_PROBABILITY) * COMMON_EFFECT**2
    + ADDED_GAUSSIAN_SD**2
))
WORLD_SPECS = {
    "symmetric_gaussian_null": {
        "kind": "gaussian", "mean_shift": 0.0,
        "status": "null", "description": "iid N(0,1); symmetric sharp-null control",
    },
    "rare_tail_weak_null": {
        "kind": "rare_tail", "mean_shift": 0.0,
        "status": "null", "description": "iid, E[d]=0, Var[d]=1, asymmetric rare-negative mixture",
    },
    "rare_tail_improvement_1p5": {
        "kind": "rare_tail", "mean_shift": 1.5,
        "status": "alternative", "description": "same rare-tail distribution shifted by +1.5 SD",
    },
}
METHODS = (
    "paired_t",
    "raw_studentized_signflip",
    "centered_wild_signflip_t",
    "block_bootstrap_percentile",
    "mom_known_variance_bound",
)
SOURCE_FILES = ("tasks/pion_projection/weak_null_nonexchangeable.py",)
OUTPUTS = (
    "raw_block_deltas.npz",
    "dataset_outcomes.csv",
    "summary.json",
    "weak_null_size_power.png",
    "README.md",
)


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_manifest() -> dict[str, str]:
    return {name: sha256(ROOT / name) for name in SOURCE_FILES}


def protocol() -> dict:
    return {
        "schema": "pion-block-risk-weak-null-nonexchangeable-v1",
        "classification": "synthetic CPU inference-method diagnostic; not a production score or physical-coverage study",
        "estimand": "mean paired block risk improvement E[d_j], positive means lower candidate risk; d_j are independent block contributions",
        "design": {
            "worlds": WORLD_SPECS,
            "independent_block_counts": list(N_BLOCKS),
            "outer_datasets_per_world_block_count": N_DATASETS,
            "alpha_one_sided": ALPHA,
            "signflip_draws_per_dataset": N_PERMUTATIONS,
            "block_bootstrap_draws_per_dataset": N_BOOTSTRAPS,
            "mom_group_count": N_MOM_GROUPS,
            "mom_variance_upper_bound": MOM_SIGMA_UPPER,
            "rare_tail_generator": {
                "p_rare_negative": RARE_PROBABILITY,
                "common_location": COMMON_EFFECT,
                "rare_location": RARE_EFFECT,
                "additive_gaussian_sd": ADDED_GAUSSIAN_SD,
                "normalization_sd": RARE_WORLD_SD,
                "mean_before_shift": 0.0,
                "variance_before_shift": 1.0,
            },
            "methods": {
                "paired_t": "One-sided Student t test of mean(d)=0.",
                "raw_studentized_signflip": "Monte Carlo sign flips of the raw block contributions, studentized each draw; finite-sample exactness requires sign/exchangeability symmetry under a sharp null.",
                "centered_wild_signflip_t": "Rademacher wild bootstrap of d_j-mean(d), studentized; a weak-null candidate, not assumed finite-sample exact.",
                "block_bootstrap_percentile": "Resample independent block contributions with replacement; certify iff the 5th percentile of bootstrap means is positive.",
                "mom_known_variance_bound": "Median of 9 disjoint group means minus 2*sigma_upper/sqrt(min_group_size); uses a known variance upper bound of 1.0. Under iid blocks and Var(d)<=sigma_upper^2, Chebyshev gives per-group failure<=1/4; Pr[Binomial(9,1/4)>=5]=0.048927, so the one-sided bound is conservative at 95%. This is an oracle-bound comparator because physical sigma_upper is not available here.",
            },
            "seeds": {
                "base": BASE_SEED,
                "dataset": "SeedSequence([base, world_index, n_index, dataset_id, stream=0]); n_index=0/1 maps to N_BLOCKS=24/48",
                "resampling": "Each batch of 20 dataset IDs uses a deterministic batch seed: XOR-reduce the canonical JSON bytes of [base, world_index, n_index, batch_start, 'resampling']; child streams [batch_seed,1] and [batch_seed,2] generate independent sign-flip and bootstrap draws sequentially within the batch. MOM partitions use SeedSequence([base,world_index,n_index,991]).",
            },
            "primary_contrasts": [
                "MOM-known-variance minus raw-signflip certification rate in rare_tail_weak_null at nblocks=24 and 48",
                "MOM-known-variance minus raw-signflip certification rate in rare_tail_improvement_1p5 at nblocks=24 and 48",
            ],
            "precision": "N=3000 independent outer datasets per world and block count. At a 5% event rate, pointwise binomial 95% Monte Carlo half-width is approximately 0.008; simultaneous intervals are also reported across all 30 method-by-cell rates.",
            "failure_policy": "Retain every planned dataset; numerical method failures or degenerate variances are explicit and count as non-certifications. No top-up or post-hoc tuning.",
        },
        "outputs": list(OUTPUTS),
        "output_directory": str(OUT.relative_to(ROOT)),
        "frozen_sources": list(SOURCE_FILES),
    }


def generate_datasets(world: str, nblocks: int, world_index: int, n_index: int) -> tuple[np.ndarray, list[int]]:
    spec = WORLD_SPECS[world]
    datasets = np.empty((N_DATASETS, nblocks), dtype=np.float64)
    seeds = []
    for dataset_id in range(N_DATASETS):
        seed = [BASE_SEED, world_index, n_index, dataset_id, 0]
        rng = np.random.default_rng(np.random.SeedSequence(seed))
        if spec["kind"] == "gaussian":
            values = rng.normal(0.0, 1.0, size=nblocks)
        else:
            rare = rng.random(nblocks) < RARE_PROBABILITY
            mixture = np.where(rare, RARE_EFFECT, COMMON_EFFECT)
            values = (mixture + rng.normal(0.0, ADDED_GAUSSIAN_SD, size=nblocks)) / RARE_WORLD_SD
        datasets[dataset_id] = values + spec["mean_shift"]
        seeds.append(int(np.random.SeedSequence(seed).generate_state(1)[0]))
    return datasets, seeds


def studentized(mean: np.ndarray, variance: np.ndarray, n: int) -> np.ndarray:
    se = np.sqrt(np.maximum(variance, 0.0) / n)
    out = np.zeros_like(mean, dtype=np.float64)
    nonzero = se > 1e-14
    out[nonzero] = mean[nonzero] / se[nonzero]
    out[~nonzero & (mean > 0)] = np.inf
    out[~nonzero & (mean < 0)] = -np.inf
    return out


def evaluate_cell(datasets: np.ndarray, world_index: int, n_index: int) -> dict[str, np.ndarray]:
    nblocks = datasets.shape[1]
    means = datasets.mean(axis=1)
    variances = datasets.var(axis=1, ddof=1)
    observed_t = studentized(means, variances, nblocks)
    p_t = student_t.sf(observed_t, df=nblocks - 1)
    p_t[variances <= 1e-28] = 1.0
    certified_t = p_t <= ALPHA

    p_raw = np.empty(N_DATASETS, dtype=np.float64)
    p_wild = np.empty(N_DATASETS, dtype=np.float64)
    bootstrap_lower = np.empty(N_DATASETS, dtype=np.float64)
    batch_size = 20
    for start in range(0, N_DATASETS, batch_size):
        stop = min(start + batch_size, N_DATASETS)
        batch = datasets[start:stop]
        b = len(batch)
        seeds = [BASE_SEED, world_index, n_index, start, "resampling"]
        seed_material = np.frombuffer(canonical(seeds), dtype=np.uint8)
        batch_seed = int(np.bitwise_xor.reduce(seed_material.astype(np.uint64)))
        rng_sign = np.random.default_rng(np.random.SeedSequence([batch_seed, 1]))
        rng_boot = np.random.default_rng(np.random.SeedSequence([batch_seed, 2]))
        signs = rng_sign.choice(np.array([-1.0, 1.0], dtype=np.float32),
                                size=(b, N_PERMUTATIONS, nblocks))
        raw_sums = np.einsum("bmn,bn->bm", signs, batch, optimize=True)
        sign_sums = signs.sum(axis=2)
        batch_means = batch.mean(axis=1)
        centered = batch - batch_means[:, None]
        centered_sums = raw_sums - batch_means[:, None] * sign_sums

        raw_q = np.square(batch).sum(axis=1)
        raw_perm_mean = raw_sums / nblocks
        raw_perm_var = (raw_q[:, None] - nblocks * np.square(raw_perm_mean)) / (nblocks - 1)
        raw_perm_t = studentized(raw_perm_mean.reshape(-1), raw_perm_var.reshape(-1), nblocks).reshape(b, N_PERMUTATIONS)

        centered_q = np.square(centered).sum(axis=1)
        wild_perm_mean = centered_sums / nblocks
        wild_perm_var = (centered_q[:, None] - nblocks * np.square(wild_perm_mean)) / (nblocks - 1)
        wild_perm_t = studentized(wild_perm_mean.reshape(-1), wild_perm_var.reshape(-1), nblocks).reshape(b, N_PERMUTATIONS)

        obs = observed_t[start:stop, None]
        p_raw[start:stop] = (1 + np.sum(raw_perm_t >= obs, axis=1)) / (N_PERMUTATIONS + 1)
        p_wild[start:stop] = (1 + np.sum(wild_perm_t >= obs, axis=1)) / (N_PERMUTATIONS + 1)

        indices = rng_boot.integers(0, nblocks, size=(b, N_BOOTSTRAPS, nblocks), dtype=np.int16)
        boot = np.take_along_axis(batch[:, None, :], indices, axis=2).mean(axis=2)
        bootstrap_lower[start:stop] = np.quantile(boot, ALPHA, axis=1)

    sign_cert = (p_raw <= ALPHA) & (variances > 1e-28)
    wild_cert = (p_wild <= ALPHA) & (variances > 1e-28)
    boot_cert = bootstrap_lower > 0.0

    group_sizes = np.full(N_MOM_GROUPS, nblocks // N_MOM_GROUPS, dtype=int)
    group_sizes[: nblocks % N_MOM_GROUPS] += 1
    min_group_size = int(group_sizes.min())
    mom_lower = np.empty(N_DATASETS, dtype=np.float64)
    rng_mom = np.random.default_rng(np.random.SeedSequence([BASE_SEED, world_index, n_index, 991]))
    for i, sample in enumerate(datasets):
        order = rng_mom.permutation(nblocks)
        group_means = []
        cursor = 0
        for size in group_sizes:
            group_means.append(float(sample[order[cursor:cursor + size]].mean()))
            cursor += int(size)
        mom_lower[i] = float(np.median(group_means) - 2.0 * MOM_SIGMA_UPPER / np.sqrt(min_group_size))
    mom_cert = mom_lower > 0.0

    return {
        "means": means,
        "sample_sd": np.sqrt(variances),
        "paired_t_p": p_t,
        "raw_signflip_p": p_raw,
        "centered_wild_p": p_wild,
        "bootstrap_lower_05": bootstrap_lower,
        "mom_lower_95": mom_lower,
        "certified_paired_t": certified_t,
        "certified_raw_signflip": sign_cert,
        "certified_centered_wild": wild_cert,
        "certified_bootstrap": boot_cert,
        "certified_mom": mom_cert,
        "mom_group_sizes": group_sizes,
        "mom_min_group_size": min_group_size,
        "degenerate_variance": variances <= 1e-28,
    }


def cp_interval(k: int, n: int, family_size: int = 1) -> list[float]:
    tail = 0.05 / family_size
    lo = 0.0 if k == 0 else float(beta.ppf(tail / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - tail / 2, k + 1, n - k))
    return [lo, hi]


def summarize(rows: list[dict]) -> dict:
    all_cells = []
    for world in WORLD_SPECS:
        for nblocks in N_BLOCKS:
            selected = [row for row in rows if row["world"] == world and row["nblocks"] == nblocks]
            for method, key in zip(METHODS, (
                "certified_paired_t", "certified_raw_signflip", "certified_centered_wild",
                "certified_bootstrap", "certified_mom",
            )):
                events = sum(bool(row[key]) for row in selected)
                all_cells.append({
                    "world": world,
                    "world_status": WORLD_SPECS[world]["status"],
                    "nblocks": nblocks,
                    "method": method,
                    "n_planned": N_DATASETS,
                    "n_valid": len(selected),
                    "n_invalid": N_DATASETS - len(selected),
                    "certified": events,
                    "rate": events / len(selected),
                    "cp95_pointwise": cp_interval(events, len(selected)),
                    "cp95_familywise_30": cp_interval(events, len(selected), 30),
                    "mean_estimated_effect": float(np.mean([row["mean"] for row in selected])),
                    "degenerate_variance_datasets": sum(bool(row["degenerate_variance"]) for row in selected),
                })
    paired_contrasts = []
    for world in WORLD_SPECS:
        for nblocks in N_BLOCKS:
            selected = [row for row in rows if row["world"] == world and row["nblocks"] == nblocks]
            for method_key, method_name in (
                ("certified_paired_t", "paired_t"),
                ("certified_centered_wild", "centered_wild_signflip_t"),
                ("certified_bootstrap", "block_bootstrap_percentile"),
                ("certified_mom", "mom_known_variance_bound"),
            ):
                diffs = np.asarray([float(row[method_key]) - float(row["certified_raw_signflip"])
                                    for row in selected])
                mean = float(diffs.mean())
                se = float(diffs.std(ddof=1) / np.sqrt(len(diffs)))
                critical = float(student_t.ppf(1 - 0.05 / (2 * 24), len(diffs) - 1))
                paired_contrasts.append({
                    "world": world,
                    "nblocks": nblocks,
                    "method": method_name,
                    "reference": "raw_studentized_signflip",
                    "n_paired_datasets": len(diffs),
                    "rate_difference": mean,
                    "simultaneous_t_ci95_family_24": [mean - critical * se, mean + critical * se],
                    "method_only": int(np.sum(diffs > 0)),
                    "reference_only": int(np.sum(diffs < 0)),
                })
    return {
        "schema": "pion-block-risk-weak-null-summary-v1",
        "classification": "synthetic CPU inference-method diagnostic; not a production score or physical-coverage study",
        "protocol_sha256": hashlib.sha256(canonical(protocol())).hexdigest(),
        "cells": all_cells,
        "paired_dataset_contrasts": paired_contrasts,
    }


def method_key(method: str) -> str:
    return {
        "paired_t": "certified_paired_t",
        "raw_studentized_signflip": "certified_raw_signflip",
        "centered_wild_signflip_t": "certified_centered_wild",
        "block_bootstrap_percentile": "certified_bootstrap",
        "mom_known_variance_bound": "certified_mom",
    }[method]


def write_figure(summary: dict) -> None:
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
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.6))
    null_ax, power_ax = axes
    null_cells = [
        ("symmetric_gaussian_null", 24, "Gaussian\nN=24"),
        ("rare_tail_weak_null", 24, "Weak null\nN=24"),
        ("symmetric_gaussian_null", 48, "Gaussian\nN=48"),
        ("rare_tail_weak_null", 48, "Weak null\nN=48"),
    ]
    x = np.arange(len(null_cells))
    width = 0.14
    offsets = (np.arange(len(METHODS)) - (len(METHODS) - 1) / 2) * width
    for mi, method in enumerate(METHODS):
        ys, low, high = [], [], []
        for world, nblocks, _ in null_cells:
            cell = next(c for c in summary["cells"] if c["world"] == world and c["nblocks"] == nblocks and c["method"] == method)
            ys.append(cell["rate"])
            low.append(cell["cp95_pointwise"][0])
            high.append(cell["cp95_pointwise"][1])
        ys = np.asarray(ys)
        null_ax.bar(x + offsets[mi], ys, width=width, color=colors[method], label=labels[method], alpha=0.88)
        null_ax.errorbar(x + offsets[mi], ys,
                         yerr=np.asarray([ys - np.asarray(low), np.asarray(high) - ys]),
                         fmt="none", ecolor="black", capsize=2, linewidth=0.8)
    null_ax.axhline(ALPHA, color="black", linestyle="--", linewidth=1.2, label="Nominal 5%")
    null_ax.set(xticks=x, xticklabels=[label for _, _, label in null_cells],
                ylabel="False-certification rate", ylim=(0, None),
                title="Equal-mean nulls: symmetry changes")
    null_ax.grid(axis="y", alpha=0.22)

    alt_cells = [("rare_tail_improvement_1p5", 24), ("rare_tail_improvement_1p5", 48)]
    x2 = np.arange(len(alt_cells))
    for mi, method in enumerate(METHODS):
        ys, low, high = [], [], []
        for world, nblocks in alt_cells:
            cell = next(c for c in summary["cells"] if c["world"] == world and c["nblocks"] == nblocks and c["method"] == method)
            ys.append(cell["rate"])
            low.append(cell["cp95_pointwise"][0])
            high.append(cell["cp95_pointwise"][1])
        ys = np.asarray(ys)
        power_ax.errorbar(x2 + offsets[mi] * 1.5, ys,
                          yerr=np.asarray([ys - np.asarray(low), np.asarray(high) - ys]),
                          marker="o", capsize=3, color=colors[method], label=labels[method])
    power_ax.set(xticks=x2, xticklabels=["Mean improvement = 1.5 SD\nN=24", "Mean improvement = 1.5 SD\nN=48"],
                 ylabel="Certification power", ylim=(0, 1.04), title="Strong-effect power under the same tail model")
    power_ax.grid(axis="y", alpha=0.22)
    handles, legend_labels = null_ax.get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 0.045))
    fig.suptitle("Pion block-risk certificate: weak-null tail stress test", y=0.99)
    fig.text(0.5, 0.105, "Error bars: pointwise exact 95% Monte Carlo intervals; N=3000 datasets per cell.",
             ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.18, 1, 0.94))
    fig.savefig(OUT / "weak_null_size_power.png", dpi=170)
    plt.close(fig)


def render_readme(summary: dict) -> str:
    lines = [
        "# Weak-null tail diagnostic for the pion block-risk score",
        "",
        "## Question and scope",
        "",
        "This independent CPU experiment asks whether the existing studentized paired-block sign-flip result extends from a sharp exchangeable null to a weak null that only fixes the mean risk improvement. Each row is an independent block contribution `d_j`; positive values favor the candidate. It is a method-level diagnostic, not the full ensemble `improvement_certificate`, a physical coverage result, or a selected production score.",
        "",
        "The rare-tail null has 90% common blocks centered at +0.30 and 10% rare blocks centered at -2.70, plus independent Gaussian noise of SD 0.20, all divided by SD sqrt(0.85). Thus E[d]=0 and Var(d)=1 exactly, but individual block labels are not sign-exchangeable. At N=24, the probability of seeing no rare negative block is 0.9^24=7.98%; this provides a predeclared high-risk regime for any method that relies on the observed sample to reveal the tail.",
        "",
        "## Methods and theoretical boundary",
        "",
        "- Paired t: one-sided Student t test of mean block improvement.",
        "- Raw studentized sign-flip: the existing C3 method; its finite-sample randomization rationale is tied to the sharp exchangeable null.",
        "- Centered wild sign-flip t: Rademacher multipliers applied to centered block residuals, with the same studentization. This is a weak-null resampling candidate; this simulation does not prove its general validity.",
        "- Block bootstrap percentile: resamples independent paired blocks and certifies only if the 5th-percentile mean is positive.",
        "- Median-of-means (MoM) bound: nine disjoint groups and known variance upper bound sigma<=1. With group size at least m_min, Chebyshev gives each group a <=1/4 chance of deviating by 2/sqrt(m_min); the median's one-sided failure probability is bounded by P[Binomial(9,1/4)>=5]=0.04893. This is a conservative finite-sample comparator under iid independent blocks and a valid external variance bound. The bound is oracle here: a variance bound estimated from the same small sample does not inherit this guarantee.",
        "",
        "The statistical distinction is established in primary literature: [Chung & Romano (2013)](https://doi.org/10.1214/13-AOS1090) distinguish finite-sample exactness under identical distributions from asymptotic validity for equality of parameters with appropriate studentization. [Minsker (2024)](https://doi.org/10.4171/MSL/43) studies median-of-means guarantees for iid finite-variance observations. Neither source validates this pion-specific risk construction or its physical use.",
        "",
        "## Monte Carlo size and power",
        "",
        "Rates use all planned independent outer datasets; all planned rows are retained. Intervals are exact binomial Monte Carlo intervals, with both pointwise CP95 and Bonferroni-simultaneous CP95 over 30 method-by-cell rates. The four method-vs-sign-flip contrasts use paired dataset-level differences and a simultaneous t interval over 24 contrasts.",
        "",
        "| World | Blocks | Method | Certified / planned | Rate | Pointwise CP95 | Simultaneous CP95 |",
        "| --- | ---: | --- | ---: | ---: | --- | --- |",
    ]
    for world in WORLD_SPECS:
        for nblocks in N_BLOCKS:
            for method in METHODS:
                cell = next(c for c in summary["cells"] if c["world"] == world and c["nblocks"] == nblocks and c["method"] == method)
                lo, hi = cell["cp95_pointwise"]
                flo, fhi = cell["cp95_familywise_30"]
                lines.append(f"| {world} | {nblocks} | {method} | {cell['certified']}/{cell['n_planned']} | {cell['rate']:.4f} | [{lo:.4f}, {hi:.4f}] | [{flo:.4f}, {fhi:.4f}] |")
    lines += ["", "## Paired method differences vs raw sign-flip", "",
              "Positive values mean the comparison method certifies more often than raw sign-flip; these are paired differences on the same generated dataset IDs. They do not rank methods without respecting the null-size results.",
              "", "| World | Blocks | Method | Difference | Simultaneous CI95 | Method only | Sign-flip only |",
              "| --- | ---: | --- | ---: | --- | ---: | ---: |"]
    for contrast in summary["paired_dataset_contrasts"]:
        lo, hi = contrast["simultaneous_t_ci95_family_24"]
        lines.append(f"| {contrast['world']} | {contrast['nblocks']} | {contrast['method']} | {contrast['rate_difference']:.4f} | [{lo:.4f}, {hi:.4f}] | {contrast['method_only']} | {contrast['reference_only']} |")
    lines += [
        "",
        "![Weak-null false certification and strong-effect power](weak_null_size_power.png)",
        "",
        "## Interpretation rule",
        "",
        "The symmetric Gaussian null checks the nominal baseline. The rare-tail weak null asks whether finite-sample certification changes when E[d]=0 but sign symmetry fails. The shifted rare-tail world is a strong positive control. A method is not accepted merely because it abstains more: interpret type-I rate and power together. The MoM result only supports the declared iid finite-variance model with the known variance bound; dependence across blocks or an invalid bound voids its guarantee. None of these methods can detect shared reference/state bias, and none replaces a fresh physical anchor.",
        "",
        "All 18,000 planned datasets are written to `raw_block_deltas.npz`; per-dataset seeds, observed means, decisions, p-values, lower bounds, and failure status are in `dataset_outcomes.csv`. Verify hashes and row counts with `python -B -m tasks.pion_projection.weak_null_nonexchangeable --verify`.",
    ]
    return "\n".join(lines) + "\n"


def prepare() -> None:
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite {OUT}")
    OUT.mkdir(parents=True)
    frozen = protocol()
    (OUT / "protocol.json").write_text(json.dumps(frozen, indent=2, sort_keys=True) + "\n")
    prereg = {
        "protocol_sha256": hashlib.sha256(canonical(frozen)).hexdigest(),
        "source_sha256": source_manifest(),
    }
    (OUT / "preregistration.json").write_text(json.dumps(prereg, indent=2, sort_keys=True) + "\n")
    print("prepared", OUT.relative_to(ROOT), prereg["protocol_sha256"])


def run() -> None:
    frozen = json.loads((OUT / "protocol.json").read_text())
    prereg = json.loads((OUT / "preregistration.json").read_text())
    if hashlib.sha256(canonical(frozen)).hexdigest() != prereg["protocol_sha256"]:
        raise RuntimeError("protocol hash mismatch")
    if prereg["source_sha256"] != source_manifest():
        raise RuntimeError("source hash mismatch")
    if any((OUT / name).exists() for name in OUTPUTS):
        raise FileExistsError("final outputs exist; refusing overwrite")

    cell_datasets = {}
    all_rows = []
    world_names = tuple(WORLD_SPECS)
    for world_index, world in enumerate(world_names):
        for n_index, nblocks in enumerate(N_BLOCKS):
            datasets, seeds = generate_datasets(world, nblocks, world_index, n_index)
            outcome = evaluate_cell(datasets, world_index, n_index)
            cell_key = f"{world}_n{nblocks}"
            cell_datasets[cell_key] = datasets
            for dataset_id in range(N_DATASETS):
                row = {
                    "world": world,
                    "nblocks": nblocks,
                    "dataset_id": dataset_id,
                    "dataset_seed_uint32": seeds[dataset_id],
                    "mean": float(outcome["means"][dataset_id]),
                    "sample_sd": float(outcome["sample_sd"][dataset_id]),
                    "paired_t_p": float(outcome["paired_t_p"][dataset_id]),
                    "raw_signflip_p": float(outcome["raw_signflip_p"][dataset_id]),
                    "centered_wild_p": float(outcome["centered_wild_p"][dataset_id]),
                    "bootstrap_lower_05": float(outcome["bootstrap_lower_05"][dataset_id]),
                    "mom_lower_95": float(outcome["mom_lower_95"][dataset_id]),
                    "certified_paired_t": int(outcome["certified_paired_t"][dataset_id]),
                    "certified_raw_signflip": int(outcome["certified_raw_signflip"][dataset_id]),
                    "certified_centered_wild": int(outcome["certified_centered_wild"][dataset_id]),
                    "certified_bootstrap": int(outcome["certified_bootstrap"][dataset_id]),
                    "certified_mom": int(outcome["certified_mom"][dataset_id]),
                    "degenerate_variance": int(outcome["degenerate_variance"][dataset_id]),
                    "status": "VALID",
                }
                all_rows.append(row)
            print(f"{world}, nblocks={nblocks}: {N_DATASETS}/{N_DATASETS}", flush=True)

    np.savez_compressed(OUT / "raw_block_deltas.npz", **cell_datasets)
    with (OUT / "dataset_outcomes.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(all_rows[0]))
        writer.writeheader()
        writer.writerows(all_rows)
    summary = summarize(all_rows)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    write_figure(summary)
    (OUT / "README.md").write_text(render_readme(summary))
    provenance = {
        "protocol_sha256": prereg["protocol_sha256"],
        "preregistered_source_sha256": prereg["source_sha256"],
        "current_source_sha256": source_manifest(),
        "planned_datasets": N_DATASETS * len(WORLD_SPECS) * len(N_BLOCKS),
        "completed_rows": len(all_rows),
        "invalid_rows": sum(row["status"] != "VALID" for row in all_rows),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "matplotlib": matplotlib.__version__,
        "artifact_sha256": {name: sha256(OUT / name) for name in OUTPUTS},
    }
    (OUT / "execution_provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    print("completed", OUT.relative_to(ROOT))


def verify() -> None:
    frozen = json.loads((OUT / "protocol.json").read_text())
    prereg = json.loads((OUT / "preregistration.json").read_text())
    if hashlib.sha256(canonical(frozen)).hexdigest() != prereg["protocol_sha256"]:
        raise RuntimeError("protocol hash mismatch")
    if prereg["source_sha256"] != source_manifest():
        raise RuntimeError("source hash mismatch")
    provenance = json.loads((OUT / "execution_provenance.json").read_text())
    if provenance["current_source_sha256"] != source_manifest():
        raise RuntimeError("current source hash mismatch")
    if provenance["planned_datasets"] != N_DATASETS * len(WORLD_SPECS) * len(N_BLOCKS):
        raise RuntimeError("planned dataset count mismatch")
    if provenance["completed_rows"] != provenance["planned_datasets"] or provenance["invalid_rows"] != 0:
        raise RuntimeError("execution row count or status mismatch")
    for name, expected in provenance["artifact_sha256"].items():
        if sha256(OUT / name) != expected:
            raise RuntimeError(f"artifact hash mismatch: {name}")
    raw = np.load(OUT / "raw_block_deltas.npz", allow_pickle=False)
    if len(raw.files) != len(WORLD_SPECS) * len(N_BLOCKS):
        raise RuntimeError("raw dataset cell count mismatch")
    for world in WORLD_SPECS:
        for nblocks in N_BLOCKS:
            values = raw[f"{world}_n{nblocks}"]
            if values.shape != (N_DATASETS, nblocks) or not np.all(np.isfinite(values)):
                raise RuntimeError(f"raw input shape/value mismatch: {world}, {nblocks}")
    with (OUT / "dataset_outcomes.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != provenance["completed_rows"] or any(row["status"] != "VALID" for row in rows):
        raise RuntimeError("raw outcome rows invalid")
    summary = json.loads((OUT / "summary.json").read_text())
    if summary["protocol_sha256"] != prereg["protocol_sha256"] or len(summary["cells"]) != 30:
        raise RuntimeError("summary protocol/cell mismatch")
    print("verification: PASS")


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
