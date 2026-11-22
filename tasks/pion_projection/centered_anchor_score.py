"""Follow-up C3 study of centered/reflective bootstrap lower bounds."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import beta, norm

from .energy_experiment import protocol as data_protocol
from .energy_target import energy_delta
from .paired_block_anchor_score import (
    ALPHA, ANCHOR_BIASES, ARM_CORRELATIONS, BASELINE_NOISE, BLOCK_LENGTH,
    CONFIG_AR1, E0, KNOWN_BETTER_NOISE, N_BOOT, NCFG, N_DATASET,
    SCHEMES, ar1, fit_pair,
)
from .statistics import bootstrap_indices


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/pion_projection/centered_anchor_score_20261120_v1"
BASE_SEED = 2026112022
METHODS = ("percentile", "basic_reflected", "bootstrap_normal")
QUALITIES = ("equal_noise_null", "known_lower_noise")
SOURCE_FILES = (
    "tasks/pion_projection/centered_anchor_score.py",
    "tasks/pion_projection/paired_block_anchor_score.py",
    "tasks/pion_projection/energy_experiment.py",
    "tasks/pion_projection/energy_target.py",
    "tasks/pion_projection/statistics.py",
    "tasks/pion_projection/reference.py",
    "results/pion_projection/paired_block_anchor_score_20261120_v1/protocol.json",
)
OUTPUTS = ("raw_outcomes.json", "summary.json", "centered_bootstrap_diagnostics.png", "README.md")


def canonical(x: object) -> bytes:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_manifest() -> dict[str, str]:
    return {name: sha256(ROOT / name) for name in SOURCE_FILES}


def protocol() -> dict:
    p = data_protocol()
    return {
        "schema": "pion-c3-centered-bootstrap-null-power-v1",
        "classification": "synthetic CPU estimator comparison; not physical score validation",
        "motivation": "The preceding common-block-index study found the uncentered percentile rule anti-conservative in the declared matched-arm null. This follow-up tests two frozen lower-bound alternatives with independent dataset seeds.",
        "design": {
            "quality_worlds": {
                "equal_noise_null": "same two-state truth and equal marginal noise amplitude 0.02",
                "known_lower_noise": "same two-state truth; baseline noise 0.02, candidate noise 0.01",
            },
            "cross_arm_noise_correlation": list(ARM_CORRELATIONS),
            "configuration_AR1": CONFIG_AR1,
            "anchor_offsets": {"equal_noise_null": list(ANCHOR_BIASES), "known_lower_noise": [0.0]},
            "independent_dataset_ids_per_quality_correlation_cell": N_DATASET,
            "ncfg": NCFG,
            "block_length": BLOCK_LENGTH,
            "bootstrap_draws": N_BOOT,
            "score_alpha": ALPHA,
            "truth_energy": E0,
            "risk_scale_tau_energy": 0.01,
            "data_generation": "Same paired-configuration generator as paired_block_anchor_score.py; paired and independent bootstrap index matrices are frozen and reused across all three interval rules.",
        },
        "methods": {
            "percentile": "Lower bound q_0.05(delta_star).",
            "basic_reflected": "Lower bound 2*delta_hat - q_0.95(delta_star), where delta_hat uses the two full-sample fitted masses. This is the reflected/basic percentile interval.",
            "bootstrap_normal": "Lower bound delta_hat - z_0.95*sd(delta_star), with z_0.95 from the standard normal; no extra tuning.",
            "certification": "A method certifies only when its lower bound is strictly positive.",
            "resampling": "Compare common_block_indices and independent_arm_indices as frozen in the preceding protocol; this follow-up does not choose a resampling scheme from results.",
        },
        "families": "For every quality x anchor-offset condition, exact CP95 intervals cover 12 event rates (2 arm correlations x 2 resampling schemes x 3 lower-bound rules). Within-dataset method rate contrasts use an outer dataset bootstrap with family size 8 (2 method contrasts x 2 correlations x 2 resampling schemes).",
        "precision": "400 independent dataset IDs per quality x correlation cell; no top-up. Invalid fits remain in the planned denominator and are counted as non-certifications.",
        "seeds": {"base": BASE_SEED, "rule": "SeedSequence([BASE_SEED,quality_index,correlation_index,dataset_id,stream]); streams 0-5 generate the same AR(1) noise and three bootstrap index streams as the preceding implementation, with an independent base seed."},
        "frozen_fit_protocol": {key: p[key] for key in ("geometry", "reference_basis", "reference_windows", "reference_nominal_window", "mass_bounds", "covariance_shrinkage")},
        "outputs": list(OUTPUTS),
        "output_directory": str(OUT.relative_to(ROOT)),
        "frozen_sources": list(SOURCE_FILES),
    }


def cp_interval(k: int, n: int, family_size: int) -> list[float]:
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


def lower_bounds(delta: np.ndarray, delta_hat: float) -> dict[str, float]:
    return {
        "percentile": float(np.quantile(delta, ALPHA)),
        "basic_reflected": float(2 * delta_hat - np.quantile(delta, 1 - ALPHA)),
        "bootstrap_normal": float(delta_hat - norm.ppf(1 - ALPHA) * np.std(delta, ddof=1)),
    }


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
    template = None
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
                if template is None:
                    from .energy_experiment import correlators
                    template = correlators(np.random.default_rng(0), ncfg=1, noise=0.0)[0]
                common = ar1(rng_common, (NCFG, *template.shape), CONFIG_AR1)
                base_residual = ar1(rng_base, (NCFG, *template.shape), CONFIG_AR1)
                candidate_residual = ar1(rng_candidate, (NCFG, *template.shape), CONFIG_AR1)
                shared_weight = np.sqrt(arm_correlation)
                residual_weight = np.sqrt(1 - arm_correlation)
                raw_base = template[None] * (1 + BASELINE_NOISE * (shared_weight * common + residual_weight * base_residual))
                raw_candidate = template[None] * (1 + candidate_noise * (shared_weight * common + residual_weight * candidate_residual))
                nblocks = NCFG // BLOCK_LENGTH
                seed_ind_base = int(rng_ind_base.integers(2**31 - 1))
                seed_ind_candidate = int(rng_ind_candidate.integers(2**31 - 1))
                seed_common = int(rng_common_index.integers(2**31 - 1))
                idx_base = bootstrap_indices(nblocks, N_BOOT, seed_ind_base)
                idx_candidate = bootstrap_indices(nblocks, N_BOOT, seed_ind_candidate)
                idx_common = bootstrap_indices(nblocks, N_BOOT, seed_common)
                try:
                    fit = fit_pair(raw_base, raw_candidate, config, idx_base, idx_candidate, idx_common)
                    for anchor_bias in anchor_offsets:
                        anchor_value = E0 + anchor_bias
                        delta_hat = float(energy_delta(np.asarray([fit["base_point"]]),
                                                       np.asarray([fit["candidate_point"]]),
                                                       np.asarray([anchor_value]))[0])
                        for scheme in SCHEMES:
                            masses_base = fit["base_independent"] if scheme == "independent_arm_indices" else fit["base_common"]
                            masses_candidate = fit["candidate_independent"] if scheme == "independent_arm_indices" else fit["candidate_common"]
                            delta = energy_delta(masses_base, masses_candidate,
                                                np.full(N_BOOT, anchor_value), 0.01)
                            bounds = lower_bounds(delta, delta_hat)
                            for method, bound in bounds.items():
                                rows.append({
                                    "quality": quality,
                                    "arm_correlation": arm_correlation,
                                    "dataset_id": dataset_id,
                                    "anchor_bias": anchor_bias,
                                    "scheme": scheme,
                                    "method": method,
                                    "baseline_noise": BASELINE_NOISE,
                                    "candidate_noise": candidate_noise,
                                    "baseline_point_mass": fit["base_point"],
                                    "candidate_point_mass": fit["candidate_point"],
                                    "delta_hat": delta_hat,
                                    "bootstrap_delta_mean": float(np.mean(delta)),
                                    "bootstrap_delta_sd": float(np.std(delta, ddof=1)),
                                    "lower_bound": bound,
                                    "certified": bool(bound > 0),
                                    "status": "VALID",
                                    "seeds": {"streams": stream_seeds,
                                              "independent_baseline_index_seed": seed_ind_base,
                                              "independent_candidate_index_seed": seed_ind_candidate,
                                              "common_index_seed": seed_common},
                                })
                except Exception as exc:
                    for anchor_bias in anchor_offsets:
                        for scheme in SCHEMES:
                            for method in METHODS:
                                rows.append({"quality": quality, "arm_correlation": arm_correlation,
                                             "dataset_id": dataset_id, "anchor_bias": anchor_bias,
                                             "scheme": scheme, "method": method,
                                             "status": "INVALID", "reason": f"{type(exc).__name__}: {exc}",
                                             "seeds": {"streams": stream_seeds}})
                if (dataset_id + 1) % 100 == 0:
                    print(f"{quality}, arm_rho={arm_correlation}: {dataset_id+1}/{N_DATASET}", flush=True)

    summary = summarize(rows)
    (OUT / "raw_outcomes.json").write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    write_figure(summary)
    (OUT / "README.md").write_text(render_readme(summary))
    provenance = {"protocol_sha256": prereg["protocol_sha256"],
                  "preregistered_source_sha256": prereg["source_sha256"],
                  "current_source_sha256": source_manifest(),
                  "planned_dataset_ids": N_DATASET * len(QUALITIES) * len(ARM_CORRELATIONS),
                  "completed_rows": len(rows),
                  "artifact_sha256": {name: sha256(OUT / name) for name in OUTPUTS}}
    (OUT / "execution_provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    print("completed", OUT.relative_to(ROOT))


def summarize(rows: list[dict]) -> dict:
    cells = []
    for quality in QUALITIES:
        anchor_offsets = ANCHOR_BIASES if quality == "equal_noise_null" else (0.0,)
        for anchor_bias in anchor_offsets:
            for rho in ARM_CORRELATIONS:
                for scheme in SCHEMES:
                    for method in METHODS:
                        selected = [r for r in rows if r["quality"] == quality and r["anchor_bias"] == anchor_bias
                                    and r["arm_correlation"] == rho and r["scheme"] == scheme and r["method"] == method]
                        valid = [r for r in selected if r["status"] == "VALID"]
                        events = sum(r["certified"] for r in valid)
                        family_size = 12
                        values = np.asarray([r["delta_hat"] for r in valid], dtype=float)
                        cells.append({"quality": quality, "anchor_bias": anchor_bias,
                                      "arm_correlation": rho, "scheme": scheme, "method": method,
                                      "n_planned": N_DATASET, "n_valid": len(valid), "n_invalid": N_DATASET-len(valid),
                                      "certified": events, "rate_planned": events/N_DATASET,
                                      "rate_valid": events/len(valid) if valid else None,
                                      "cp95_marginal": cp_interval(events, len(valid), 1) if valid else None,
                                      "cp95_familywise": cp_interval(events, N_DATASET, family_size),
                                      "mean_delta_hat": float(values.mean()) if len(values) else None,
                                      "mean_delta_familywise_ci95": bootstrap_mean_ci(values, BASE_SEED+10000+len(cells), family_size) if len(values) else None})
    contrasts = []
    method_pairs = (("basic_reflected", "percentile"), ("bootstrap_normal", "percentile"))
    for quality in QUALITIES:
        anchor_offsets = ANCHOR_BIASES if quality == "equal_noise_null" else (0.0,)
        for anchor_bias in anchor_offsets:
            for rho in ARM_CORRELATIONS:
                for scheme in SCHEMES:
                    by_method = {m: {r["dataset_id"]: r for r in rows if r["quality"] == quality
                                     and r["anchor_bias"] == anchor_bias and r["arm_correlation"] == rho
                                     and r["scheme"] == scheme and r["method"] == m and r["status"] == "VALID"}
                                 for m in METHODS}
                    for method, reference in method_pairs:
                        ids = sorted(set(by_method[method]) & set(by_method[reference]))
                        differences = np.asarray([float(by_method[method][i]["certified"])
                                                  - float(by_method[reference][i]["certified"]) for i in ids])
                        contrasts.append({"quality": quality, "anchor_bias": anchor_bias,
                                          "arm_correlation": rho, "scheme": scheme,
                                          "method": method, "reference_method": reference,
                                          "n_paired": len(differences),
                                          "rate_difference": float(differences.mean()) if len(differences) else None,
                                          "familywise_dataset_bootstrap_ci95": bootstrap_mean_ci(differences, BASE_SEED+20000+len(contrasts), 8) if len(differences) else None,
                                          "method_only": int(np.sum(differences == 1)),
                                          "reference_only": int(np.sum(differences == -1))})
    return {"schema": "pion-c3-centered-bootstrap-summary-v1",
            "classification": "synthetic CPU estimator comparison; not physical score validation",
            "protocol_sha256": hashlib.sha256(canonical(protocol())).hexdigest(),
            "cells": cells, "method_contrasts": contrasts}


def write_figure(summary: dict) -> None:
    colors = {"percentile": "#4477AA", "basic_reflected": "#CC6677", "bootstrap_normal": "#228833"}
    labels = {"percentile": "Percentile", "basic_reflected": "Basic / reflected", "bootstrap_normal": "Bootstrap-normal"}
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2))
    for quality, ax, title in (("equal_noise_null", axes[0], "Null false-certification (anchor bias 0)"),
                                ("known_lower_noise", axes[1], "Known-improvement power")):
        subset = [c for c in summary["cells"] if c["quality"] == quality and c["anchor_bias"] == 0.0]
        x = np.arange(len(ARM_CORRELATIONS))
        for method in METHODS:
            for scheme, shift, alpha_line in ((SCHEMES[0], -0.04, 0.85), (SCHEMES[1], 0.04, 1.0)):
                chosen = [next(c for c in subset if c["arm_correlation"] == rho and c["scheme"] == scheme and c["method"] == method)
                          for rho in ARM_CORRELATIONS]
                values = np.asarray([c["rate_planned"] for c in chosen])
                intervals = [c["cp95_familywise"] for c in chosen]
                yerr = np.asarray([[v-ci[0] for v, ci in zip(values, intervals)],
                                   [ci[1]-v for v, ci in zip(values, intervals)]])
                ax.errorbar(x+shift, values, yerr=yerr, marker="o", capsize=2.5,
                            color=colors[method], alpha=alpha_line,
                            linestyle="-" if scheme == SCHEMES[1] else "--",
                            label=f"{labels[method]}, {'common' if scheme == SCHEMES[1] else 'independent'}")
        if quality == "equal_noise_null":
            ax.axhline(ALPHA, color="black", linestyle=":", linewidth=1, label="5% reference")
        ax.set(xticks=x, xticklabels=[f"{rho:.1f}" for rho in ARM_CORRELATIONS], xlabel="Matched-arm correlation",
               ylabel="Certification rate", title=title)
        ax.legend(fontsize=7, ncol=2)
    ax = axes[2]
    subset = [c for c in summary["cells"] if c["quality"] == "equal_noise_null" and c["scheme"] == "common_block_indices"]
    x = np.arange(len(ANCHOR_BIASES))
    for rho_index, rho in enumerate(ARM_CORRELATIONS):
        for method in METHODS:
            chosen = [next(c for c in subset if c["anchor_bias"] == bias and c["arm_correlation"] == rho and c["method"] == method)
                      for bias in ANCHOR_BIASES]
            values = np.asarray([c["rate_planned"] for c in chosen])
            intervals = [c["cp95_familywise"] for c in chosen]
            yerr = np.asarray([[v-ci[0] for v, ci in zip(values, intervals)],
                               [ci[1]-v for v, ci in zip(values, intervals)]])
            offset = (rho_index - 0.5) * 0.06
            ax.errorbar(x+offset, values, yerr=yerr, marker="o", capsize=2.5,
                        color=colors[method], linestyle="-" if rho_index else "--",
                        label=f"{labels[method]}, ρ={rho:.1f}")
    ax.axhline(ALPHA, color="black", linestyle=":", linewidth=1)
    ax.set(xticks=x, xticklabels=[f"{b:+.2f}" for b in ANCHOR_BIASES], xlabel="Fixed anchor offset",
           ylabel="False-certification rate", title="Common-block null sensitivity")
    ax.legend(fontsize=7)
    fig.suptitle("C3 lower-bound alternatives under matched configuration resampling")
    fig.tight_layout()
    fig.savefig(OUT / "centered_bootstrap_diagnostics.png", dpi=160)
    plt.close(fig)


def render_readme(summary: dict) -> str:
    lines = [
        "# Centered bootstrap lower bounds for the synthetic C3 score",
        "",
        "This is a follow-up to the common-block resampling study. It uses new independent dataset seeds, 400 dataset IDs per quality x cross-arm-correlation cell, the same paired configuration generator and the same two resampling schemes. The candidate lower-bound rules were frozen before this run: ordinary percentile, basic/reflected percentile, and a bootstrap-normal lower bound. All use the same energy-risk difference and certify only when the lower bound is positive.",
        "",
        "## Equal-noise null (anchor offset = 0)",
        "",
        "| rho | Resampling | Lower bound | Certified / planned | Rate | Familywise CP95 (12 rates) | Mean point delta |",
        "| ---: | --- | --- | ---: | ---: | --- | ---: |",
    ]
    for rho in ARM_CORRELATIONS:
        for scheme in SCHEMES:
            for method in METHODS:
                c = next(c for c in summary["cells"] if c["quality"] == "equal_noise_null" and c["anchor_bias"] == 0
                         and c["arm_correlation"] == rho and c["scheme"] == scheme and c["method"] == method)
                ci = c["cp95_familywise"]
                lines.append(f"| {rho:.1f} | {scheme} | {method} | {c['certified']}/{c['n_planned']} | {c['rate_planned']:.3f} | [{ci[0]:.3f},{ci[1]:.3f}] | {c['mean_delta_hat']:.5f} |")
    lines += ["", "## Known-improvement power", "",
              "| rho | Resampling | Lower bound | Certified / planned | Rate | Familywise CP95 (12 rates) |",
              "| ---: | --- | --- | ---: | ---: | --- |"]
    for rho in ARM_CORRELATIONS:
        for scheme in SCHEMES:
            for method in METHODS:
                c = next(c for c in summary["cells"] if c["quality"] == "known_lower_noise" and c["arm_correlation"] == rho
                         and c["scheme"] == scheme and c["method"] == method)
                ci = c["cp95_familywise"]
                lines.append(f"| {rho:.1f} | {scheme} | {method} | {c['certified']}/{c['n_planned']} | {c['rate_planned']:.3f} | [{ci[0]:.3f},{ci[1]:.3f}] |")
    lines += ["", "![Null size, power, and anchor sensitivity](centered_bootstrap_diagnostics.png)", "",
              "## Method contrasts", "",
              "Rate differences are paired by outer dataset ID. Positive values mean the alternative method certified more often than the percentile reference.",
              "", "| Quality | Anchor bias | rho | Resampling | Method | Difference vs percentile | Familywise dataset-bootstrap CI95 | Method-only / percentile-only |",
              "| --- | ---: | ---: | --- | --- | ---: | --- | ---: |"]
    for c in summary["method_contrasts"]:
        ci = c["familywise_dataset_bootstrap_ci95"]
        lines.append(f"| {c['quality']} | {c['anchor_bias']:+.2f} | {c['arm_correlation']:.1f} | {c['scheme']} | {c['method']} | {c['rate_difference']:+.4f} | [{ci[0]:+.4f},{ci[1]:+.4f}] | {c['method_only']} / {c['reference_only']} |")
    lines += ["", "## Interpretation boundary", "",
              "The basic/reflected and bootstrap-normal rules are candidates, not validated production replacements. This generator uses a fixed true anchor and a specific AR(1) correlated Gaussian model; passing a null cell would not establish physical coverage. Compare null size and known-improvement power together, and preserve all failures. The methods were motivated after the preceding v1 null result; the present run uses independent seeds but is still a targeted synthetic follow-up, not an independent physical confirmation.",
              "", "Raw dataset-level point estimates, bootstrap summaries, seeds, hashes, and failure states are retained. Verify with `python -B -m tasks.pion_projection.centered_anchor_score --verify`."]
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
    expected = N_DATASET * len(ARM_CORRELATIONS) * len(SCHEMES) * len(METHODS) * (len(ANCHOR_BIASES) + 1)
    if len(rows) != expected:
        raise RuntimeError("raw row count mismatch")
    for cell in summary["cells"]:
        selected = [r for r in rows if r["quality"] == cell["quality"] and r["anchor_bias"] == cell["anchor_bias"]
                    and r["arm_correlation"] == cell["arm_correlation"] and r["scheme"] == cell["scheme"] and r["method"] == cell["method"]]
        valid = [r for r in selected if r["status"] == "VALID"]
        if len(selected) != N_DATASET or len(valid) != cell["n_valid"]:
            raise RuntimeError("cell count mismatch")
        if sum(r["certified"] for r in valid) != cell["certified"]:
            raise RuntimeError("cell certification count mismatch")
    print(f"verified hashes, {len(QUALITIES)} worlds x {len(ARM_CORRELATIONS)} correlations x {N_DATASET} IDs/cell")


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
