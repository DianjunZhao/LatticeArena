"""Compare common-block and independent-arm bootstrap for a synthetic C3 score."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import beta

from .energy_experiment import correlators, protocol as data_protocol
from .energy_target import energy_delta
from .statistics import ReferenceFit, blocks, bootstrap_indices, fold


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/pion_projection/paired_block_anchor_score_20261120_v1"
N_DATASET = 400
N_BOOT = 200
NCFG = 120
BLOCK_LENGTH = 5
E0 = 0.80
TAU_E = 0.01
ALPHA = 0.05
BASELINE_NOISE = 0.02
KNOWN_BETTER_NOISE = 0.01
ARM_CORRELATIONS = (0.5, 0.9)
CONFIG_AR1 = 0.5
ANCHOR_BIASES = (-0.02, 0.0, 0.02)
BASE_SEED = 2026112021
SCHEMES = ("independent_arm_indices", "common_block_indices")
QUALITIES = ("equal_noise_null", "known_lower_noise")
SOURCE_FILES = (
    "tasks/pion_projection/paired_block_anchor_score.py",
    "tasks/pion_projection/energy_experiment.py",
    "tasks/pion_projection/energy_target.py",
    "tasks/pion_projection/statistics.py",
    "tasks/pion_projection/reference.py",
    "tasks/pion_projection/anchor_bias_only_null.py",
    "results/pion_projection/s16t16_gevp200/development_provenance.json",
)
OUTPUTS = ("raw_outcomes.json", "summary.json", "paired_block_diagnostics.png", "README.md")


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_manifest() -> dict[str, str]:
    return {name: sha256(ROOT / name) for name in SOURCE_FILES}


def protocol() -> dict:
    p = data_protocol()
    return {
        "schema": "pion-c3-common-block-bootstrap-null-power-v1",
        "classification": "synthetic CPU method comparison; not physical anchor or score validation",
        "question": "When baseline and candidate share configuration IDs and correlated noise, does common block-index resampling improve null calibration while retaining power relative to independent-arm bootstrap resampling?",
        "design": {
            "independent_dataset_ids_per_quality_correlation_cell": N_DATASET,
            "quality_worlds": {
                "equal_noise_null": "same two-state truth and equal marginal noise amplitude 0.02 for baseline and candidate",
                "known_lower_noise": "same two-state truth; baseline noise amplitude 0.02, candidate 0.01",
            },
            "cross_arm_noise_correlation": list(ARM_CORRELATIONS),
            "configuration_AR1": CONFIG_AR1,
            "anchor_offsets": {"equal_noise_null": list(ANCHOR_BIASES), "known_lower_noise": [0.0]},
            "ncfg": NCFG,
            "block_length": BLOCK_LENGTH,
            "n_blocks": NCFG // BLOCK_LENGTH,
            "bootstrap_draws_per_arm": N_BOOT,
            "true_energy": E0,
            "risk_scale_tau_energy": TAU_E,
            "score_alpha": ALPHA,
            "noise_model": "Within each arm, configuration-index noise is a stationary AR(1) Gaussian process with rho=0.5. Baseline and candidate have a shared AR(1) latent component plus independent AR(1) residuals; cross-arm correlation at matched configuration/channel/time is rho_arm. Both arms are measured on the same synthetic configuration IDs.",
        },
        "methods": {
            "independent_arm_indices": "Generate separate block-bootstrap index matrices for baseline and candidate; form the same energy-risk difference and certify by its 5th percentile.",
            "common_block_indices": "Use one block-bootstrap index matrix for baseline and candidate, preserving their shared configuration IDs; apply the same risk formula and alpha.",
            "certification_event": "Bootstrap 5th percentile of delta > 0. No thresholds are tuned after outcomes.",
            "primary_families": "For each quality world, familywise exact CP95 intervals cover four rates (two cross-arm correlations x two bootstrap schemes) at zero anchor offset. Null anchor-offset sensitivity uses a separate eight-rate family. Paired scheme-minus-independent scheme rate differences use dataset bootstrap CI95, family size equal to the number of correlation/offset contrasts.",
        },
        "precision": "N=400 independent dataset IDs per quality x cross-arm-correlation cell. Report marginal and familywise CP95 intervals; no top-up. Invalid fits are retained and count as non-certifications in planned-denominator rates.",
        "seeds": {"base": BASE_SEED, "rule": "SeedSequence([BASE_SEED,quality_index,correlation_index,dataset_id,stream]); streams 0-2 generate common/baseline-residual/candidate-residual AR(1) noise, and streams 3-5 generate independent-baseline, independent-candidate, and common block-index matrices."},
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
    idx = rng.integers(0, len(values), size=(20000, len(values)))
    means = values[idx].mean(axis=1)
    tail = 0.05 / (2 * family_size)
    return [float(np.quantile(means, tail)), float(np.quantile(means, 1 - tail))]


def ar1(rng: np.random.Generator, shape_: tuple[int, ...], rho: float) -> np.ndarray:
    innovations = rng.normal(size=shape_)
    out = np.empty_like(innovations)
    out[0] = innovations[0]
    scale = np.sqrt(1 - rho * rho)
    for i in range(1, shape_[0]):
        out[i] = rho * out[i - 1] + scale * innovations[i]
    return out


def fit_pair(raw_base: np.ndarray, raw_candidate: np.ndarray, config: dict,
             idx_base: np.ndarray, idx_candidate: np.ndarray,
             idx_common: np.ndarray) -> dict[str, np.ndarray | float]:
    window = config["reference_windows"][config["reference_nominal_window"]]
    base_blocks = blocks(fold(raw_base), BLOCK_LENGTH)
    candidate_blocks = blocks(fold(raw_candidate), BLOCK_LENGTH)
    ref_base = ReferenceFit(base_blocks, config, window)
    ref_candidate = ReferenceFit(candidate_blocks, config, window)
    base_fit, base_independent = ref_base.bootstrap(idx_base)
    candidate_fit, candidate_independent = ref_candidate.bootstrap(idx_candidate)
    _, base_common = ref_base.bootstrap(idx_common)
    _, candidate_common = ref_candidate.bootstrap(idx_common)
    return {
        "base_point": float(base_fit["mass"]),
        "candidate_point": float(candidate_fit["mass"]),
        "base_independent": np.asarray(base_independent),
        "candidate_independent": np.asarray(candidate_independent),
        "base_common": np.asarray(base_common),
        "candidate_common": np.asarray(candidate_common),
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
    raw_rows: list[dict] = []
    for quality_index, quality in enumerate(QUALITIES):
        candidate_noise = BASELINE_NOISE if quality == "equal_noise_null" else KNOWN_BETTER_NOISE
        anchor_offsets = ANCHOR_BIASES if quality == "equal_noise_null" else (0.0,)
        for correlation_index, arm_correlation in enumerate(ARM_CORRELATIONS):
            for dataset_id in range(N_DATASET):
                stream_seeds = [[BASE_SEED, quality_index, correlation_index, dataset_id, stream]
                                for stream in range(6)]
                rng_common, rng_base, rng_candidate, rng_ind_base, rng_ind_candidate, rng_common_index = [
                    np.random.default_rng(np.random.SeedSequence(seed)) for seed in stream_seeds
                ]
                template = correlators(np.random.default_rng(0), ncfg=1, noise=0.0)[0]
                base_residual = ar1(rng_base, (NCFG, *template.shape), CONFIG_AR1)
                candidate_residual = ar1(rng_candidate, (NCFG, *template.shape), CONFIG_AR1)
                common = ar1(rng_common, (NCFG, *template.shape), CONFIG_AR1)
                shared_weight = np.sqrt(arm_correlation)
                residual_weight = np.sqrt(1 - arm_correlation)
                raw_base = template[None] * (1 + BASELINE_NOISE * (shared_weight * common + residual_weight * base_residual))
                raw_candidate = template[None] * (1 + candidate_noise * (shared_weight * common + residual_weight * candidate_residual))
                nblocks = NCFG // BLOCK_LENGTH
                idx_base_seed = int(rng_ind_base.integers(2**31 - 1))
                idx_candidate_seed = int(rng_ind_candidate.integers(2**31 - 1))
                idx_common_seed = int(rng_common_index.integers(2**31 - 1))
                idx_base = bootstrap_indices(nblocks, N_BOOT, idx_base_seed)
                idx_candidate = bootstrap_indices(nblocks, N_BOOT, idx_candidate_seed)
                idx_common = bootstrap_indices(nblocks, N_BOOT, idx_common_seed)
                try:
                    fitted = fit_pair(raw_base, raw_candidate, config, idx_base, idx_candidate, idx_common)
                    for anchor_bias in anchor_offsets:
                        anchor = np.full(N_BOOT, E0 + anchor_bias)
                        for scheme in SCHEMES:
                            if scheme == "independent_arm_indices":
                                masses_base = fitted["base_independent"]
                                masses_candidate = fitted["candidate_independent"]
                            else:
                                masses_base = fitted["base_common"]
                                masses_candidate = fitted["candidate_common"]
                            delta = energy_delta(masses_base, masses_candidate, anchor, TAU_E)
                            lower = float(np.quantile(delta, ALPHA))
                            raw_rows.append({
                                "quality": quality,
                                "arm_correlation": arm_correlation,
                                "dataset_id": dataset_id,
                                "anchor_bias": anchor_bias,
                                "scheme": scheme,
                                "baseline_noise": BASELINE_NOISE,
                                "candidate_noise": candidate_noise,
                                "baseline_point_mass": fitted["base_point"],
                                "candidate_point_mass": fitted["candidate_point"],
                                "delta_mean": float(np.mean(delta)),
                                "delta_sd": float(np.std(delta, ddof=1)),
                                "delta_lower_q05": lower,
                                "certified": bool(lower > 0),
                                "status": "VALID",
                                "seeds": {"streams": stream_seeds,
                                          "independent_baseline_index_seed": idx_base_seed,
                                          "independent_candidate_index_seed": idx_candidate_seed,
                                          "common_index_seed": idx_common_seed},
                            })
                except Exception as exc:
                    for anchor_bias in anchor_offsets:
                        for scheme in SCHEMES:
                            raw_rows.append({"quality": quality, "arm_correlation": arm_correlation,
                                             "dataset_id": dataset_id, "anchor_bias": anchor_bias,
                                             "scheme": scheme, "status": "INVALID",
                                             "reason": f"{type(exc).__name__}: {exc}",
                                             "seeds": {"streams": stream_seeds}})
                if (dataset_id + 1) % 100 == 0:
                    print(f"{quality}, arm_rho={arm_correlation}: {dataset_id+1}/{N_DATASET}", flush=True)

    summary = summarize(raw_rows)
    (OUT / "raw_outcomes.json").write_text(json.dumps(raw_rows, indent=2, sort_keys=True) + "\n")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    write_figure(summary, raw_rows)
    (OUT / "README.md").write_text(render_readme(summary))
    provenance = {"protocol_sha256": prereg["protocol_sha256"],
                  "preregistered_source_sha256": prereg["source_sha256"],
                  "current_source_sha256": source_manifest(),
                  "planned_dataset_ids": N_DATASET * len(QUALITIES) * len(ARM_CORRELATIONS),
                  "completed_rows": len(raw_rows),
                  "artifact_sha256": {name: sha256(OUT / name) for name in OUTPUTS}}
    (OUT / "execution_provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    print("completed", OUT.relative_to(ROOT))


def summarize(rows: list[dict]) -> dict:
    cells = []
    for quality in QUALITIES:
        anchor_offsets = ANCHOR_BIASES if quality == "equal_noise_null" else (0.0,)
        for anchor_bias in anchor_offsets:
            family_size = 4 if anchor_bias == 0.0 else 8
            for correlation_index, arm_correlation in enumerate(ARM_CORRELATIONS):
                for scheme in SCHEMES:
                    cell = [r for r in rows if r["quality"] == quality and r["anchor_bias"] == anchor_bias
                            and r["arm_correlation"] == arm_correlation and r["scheme"] == scheme]
                    valid = [r for r in cell if r["status"] == "VALID"]
                    events = sum(r["certified"] for r in valid)
                    values = np.asarray([r["delta_mean"] for r in valid], dtype=float)
                    cells.append({
                        "quality": quality, "anchor_bias": anchor_bias,
                        "arm_correlation": arm_correlation, "scheme": scheme,
                        "n_planned": N_DATASET, "n_valid": len(valid), "n_invalid": N_DATASET-len(valid),
                        "certified": events, "rate_valid": events/len(valid) if valid else None,
                        "rate_planned": events/N_DATASET,
                        "cp95_marginal": cp_interval(events, len(valid)) if valid else None,
                        "cp95_familywise": cp_interval(events, N_DATASET, family_size),
                        "mean_delta": float(values.mean()) if len(values) else None,
                        "mean_delta_familywise_ci95": bootstrap_mean_ci(values, BASE_SEED + 5000 + len(cells), family_size) if len(values) else None,
                        "median_delta": float(np.median(values)) if len(values) else None,
                    })
    contrasts = []
    # The scheme contrast is paired on outer dataset IDs; separate bootstrap index streams
    # do not change that outer pairing.
    for quality in QUALITIES:
        anchor_offsets = ANCHOR_BIASES if quality == "equal_noise_null" else (0.0,)
        for anchor_bias in anchor_offsets:
            for arm_correlation in ARM_CORRELATIONS:
                by_scheme = {scheme: {r["dataset_id"]: r for r in rows if r["quality"] == quality
                                      and r["anchor_bias"] == anchor_bias and r["arm_correlation"] == arm_correlation
                                      and r["scheme"] == scheme and r["status"] == "VALID"}
                             for scheme in SCHEMES}
                paired_ids = sorted(set(by_scheme[SCHEMES[0]]) & set(by_scheme[SCHEMES[1]]))
                differences = np.asarray([float(by_scheme["common_block_indices"][i]["certified"])
                                          - float(by_scheme["independent_arm_indices"][i]["certified"])
                                          for i in paired_ids])
                family_size = 2 if quality == "known_lower_noise" else 6
                contrasts.append({
                    "quality": quality, "anchor_bias": anchor_bias,
                    "arm_correlation": arm_correlation, "n_paired": len(differences),
                    "rate_difference_common_minus_independent": float(differences.mean()) if len(differences) else None,
                    "familywise_dataset_bootstrap_ci95": bootstrap_mean_ci(differences, BASE_SEED + 9000 + len(contrasts), family_size) if len(differences) else None,
                    "common_only_certifications": int(np.sum(differences == 1)),
                    "independent_only_certifications": int(np.sum(differences == -1)),
                })
    return {"schema": "pion-c3-common-block-bootstrap-summary-v1",
            "classification": "synthetic CPU method comparison; not physical anchor or score validation",
            "protocol_sha256": hashlib.sha256(canonical(protocol())).hexdigest(),
            "n_dataset_ids_per_quality_correlation_cell": N_DATASET,
            "cells": cells, "scheme_contrasts": contrasts}


def write_figure(summary: dict, rows: list[dict]) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.5))
    colors = {"independent_arm_indices": "#CC6677", "common_block_indices": "#4477AA"}
    labels = {"independent_arm_indices": "Independent arm indices", "common_block_indices": "Common block indices"}
    for quality, ax, title in (("equal_noise_null", axes[0], "Null: false certification"),
                                ("known_lower_noise", axes[1], "Known improvement: power")):
        subset = [c for c in summary["cells"] if c["quality"] == quality]
        if quality == "equal_noise_null":
            subset = [c for c in subset if c["anchor_bias"] == 0.0]
        else:
            subset = [c for c in subset if c["anchor_bias"] == 0.0]
        x = np.arange(len(ARM_CORRELATIONS))
        for scheme in SCHEMES:
            selected = [next(c for c in subset if c["arm_correlation"] == rho and c["scheme"] == scheme)
                        for rho in ARM_CORRELATIONS]
            values = np.array([c["rate_planned"] for c in selected])
            cis = [c["cp95_familywise"] for c in selected]
            lower = np.array([v - ci[0] for v, ci in zip(values, cis)])
            upper = np.array([ci[1] - v for v, ci in zip(values, cis)])
            shift = -0.04 if scheme == SCHEMES[0] else 0.04
            ax.errorbar(x + shift, values, yerr=np.vstack((lower, upper)), marker="o", capsize=3,
                        color=colors[scheme], label=labels[scheme])
        ax.axhline(ALPHA, color="black", linestyle="--", linewidth=1, label="5% reference" if quality == "equal_noise_null" else None)
        ax.set(xticks=x, xticklabels=[f"{rho:.1f}" for rho in ARM_CORRELATIONS], xlabel="Matched-arm noise correlation",
               ylabel="Certification rate", title=title)
        ax.legend(fontsize=8)
    ax = axes[2]
    null_rows = [c for c in summary["cells"] if c["quality"] == "equal_noise_null"]
    x_positions = np.arange(len(ARM_CORRELATIONS) * len(ANCHOR_BIASES))
    tick_labels = []
    for rho_index, rho in enumerate(ARM_CORRELATIONS):
        for bias_index, bias in enumerate(ANCHOR_BIASES):
            x = rho_index * len(ANCHOR_BIASES) + bias_index
            tick_labels.append(f"ρ={rho:.1f}\nb={bias:+.2f}")
            for scheme in SCHEMES:
                cell = next(c for c in null_rows if c["arm_correlation"] == rho and c["anchor_bias"] == bias and c["scheme"] == scheme)
                lo, hi = cell["cp95_familywise"]
                offset = -0.06 if scheme == SCHEMES[0] else 0.06
                ax.errorbar(x + offset, cell["rate_valid"], yerr=[[cell["rate_valid"]-lo], [hi-cell["rate_valid"]]],
                            fmt="o", capsize=2, color=colors[scheme])
    ax.axhline(ALPHA, color="black", linestyle="--", linewidth=1)
    ax.set(xticks=x_positions, xticklabels=tick_labels, ylabel="False-certification rate", title="Null sensitivity to fixed anchor offset")
    ax.tick_params(axis="x", labelsize=7)
    fig.suptitle("C3: preserving shared configuration IDs in block resampling")
    fig.tight_layout()
    fig.savefig(OUT / "paired_block_diagnostics.png", dpi=160)
    plt.close(fig)


def render_readme(summary: dict) -> str:
    lines = [
        "# Common-block bootstrap for the synthetic C3 score",
        "",
        "This independent CPU study uses 400 dataset IDs in each equal-noise null / known-lower-noise world and each matched-arm noise-correlation cell (ρ=0.5, 0.9). The same synthetic configuration IDs feed baseline and candidate. Configuration noise has AR(1) ρ=0.5; each arm has the same marginal noise amplitude within a quality world, with a shared latent component controlling cross-arm correlation. The 120 configurations are resampled as 24 consecutive blocks of length 5.",
        "",
        "The only change between methods is bootstrap indexing: `independent_arm_indices` draws separate block indices for the two arms; `common_block_indices` applies the same block-index matrix to both arms. Both use the existing energy-risk difference and certify when its bootstrap 5th percentile is positive. No alpha or threshold was tuned. Under the null, the same fitted mass draws are evaluated at anchor offsets -0.02, 0, +0.02; the known-improvement control uses offset zero.",
        "",
        "## Null size at zero anchor offset",
        "",
        "| Matched-arm rho | Resampling | Certified / planned | Rate | Familywise CP95 (4 rates) | Mean delta | Familywise dataset-bootstrap CI95 |",
        "| ---: | --- | ---: | ---: | --- | ---: | --- |",
    ]
    for rho in ARM_CORRELATIONS:
        for scheme in SCHEMES:
            c = next(c for c in summary["cells"] if c["quality"] == "equal_noise_null" and c["anchor_bias"] == 0 and c["arm_correlation"] == rho and c["scheme"] == scheme)
            ci, mean_ci = c["cp95_familywise"], c["mean_delta_familywise_ci95"]
            lines.append(f"| {rho:.1f} | {scheme} | {c['certified']}/{c['n_planned']} | {c['rate_planned']:.3f} | [{ci[0]:.3f},{ci[1]:.3f}] | {c['mean_delta']:.5f} | [{mean_ci[0]:.5f},{mean_ci[1]:.5f}] |")
    lines += ["", "## Known-improvement power", "",
              "| Matched-arm rho | Resampling | Certified / planned | Rate | Familywise CP95 (4 rates) |",
              "| ---: | --- | ---: | ---: | --- |"]
    for rho in ARM_CORRELATIONS:
        for scheme in SCHEMES:
            c = next(c for c in summary["cells"] if c["quality"] == "known_lower_noise" and c["arm_correlation"] == rho and c["scheme"] == scheme)
            ci = c["cp95_familywise"]
            lines.append(f"| {rho:.1f} | {scheme} | {c['certified']}/{c['n_planned']} | {c['rate_planned']:.3f} | [{ci[0]:.3f},{ci[1]:.3f}] |")
    lines += ["", "## Paired resampling contrasts", "",
              "Rate differences below are paired by outer dataset ID; intervals resample those IDs. Positive values mean common-block resampling certified more often.",
              "", "| Quality | Anchor bias | rho | Common minus independent rate | Familywise dataset-bootstrap CI95 | Common-only / independent-only events |",
              "| --- | ---: | ---: | ---: | --- | ---: |"]
    for c in summary["scheme_contrasts"]:
        ci = c["familywise_dataset_bootstrap_ci95"]
        lines.append(f"| {c['quality']} | {c['anchor_bias']:+.2f} | {c['arm_correlation']:.1f} | {c['rate_difference_common_minus_independent']:+.4f} | [{ci[0]:+.4f},{ci[1]:+.4f}] | {c['common_only_certifications']} / {c['independent_only_certifications']} |")
    lines += ["", "![Null size, known-improvement power, and anchor sensitivity](paired_block_diagnostics.png)", "",
              "## Interpretation boundary", "",
              "This simulation directly tests matched configuration/block resampling under its declared correlated Gaussian noise model. It does not prove coverage for real gauge ensembles, production fit gates, a measured independent anchor, or arbitrary covariance structures. The common-block scheme is the structurally matched bootstrap when the two arms use the same configuration IDs; if the arms are independent samples, separate indices are appropriate. The prior C3 expansion reports used separate arm data / indices and should not be described as common-configuration paired bootstrap evidence. A physical score still requires a blind production test with real configuration-level IDs, anchor uncertainty, and null/known-signal controls.",
              "", "Raw dataset summaries, seeds, protocol/source hashes, and output hashes are retained. Verify with `python -B -m tasks.pion_projection.paired_block_anchor_score --verify`."]
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
    expected_rows = N_DATASET * len(ARM_CORRELATIONS) * len(SCHEMES) * (len(ANCHOR_BIASES) + 1)
    if len(rows) != expected_rows:
        raise RuntimeError("raw row count mismatch")
    for cell in summary["cells"]:
        selected = [r for r in rows if r["quality"] == cell["quality"] and r["arm_correlation"] == cell["arm_correlation"]
                    and r["anchor_bias"] == cell["anchor_bias"] and r["scheme"] == cell["scheme"]]
        valid = [r for r in selected if r["status"] == "VALID"]
        if len(selected) != N_DATASET or len(valid) != cell["n_valid"]:
            raise RuntimeError("cell denominator mismatch")
        if sum(r["certified"] for r in valid) != cell["certified"]:
            raise RuntimeError("cell event count mismatch")
    print(f"verified hashes, {len(QUALITIES)} quality worlds x {len(ARM_CORRELATIONS)} correlations x {N_DATASET} IDs/cell")


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
