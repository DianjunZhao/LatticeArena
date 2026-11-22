"""Factorized finite-sample calibration diagnostic for the pion chi-square subgate.

This controlled Gaussian linear-model study separates known-covariance behavior
from estimated-covariance effects. It is a synthetic method diagnostic, not a
replacement production gate or a physical validation.
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
from scipy.stats import beta, chi2

from .statistics import inverse_covariance


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/pion_projection/certificate_subgate_factorized_20261120_v1"
BLOCKS = (6, 12, 24)
SHRINKAGES = (0.0, 0.25, 0.5)
METHODS = ("known_covariance", "shrink_0.0", "shrink_0.25", "shrink_0.5")
N_CAL = 5000
N_EVAL = 5000
BASE_SEED = 2026112500
ALPHA = 0.05
P = 12
Q = 4
DF = P - Q
RHO = 0.60
EIGEN_FLOOR_REL = 1e-10
SOURCE_FILES = (
    "tasks/pion_projection/certificate_subgate_factorized.py",
    "tasks/pion_projection/statistics.py",
)
OUTPUTS = ("raw_scores.npz", "summary.json", "factorized_calibration.png", "README.md")


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_manifest() -> dict[str, str]:
    return {name: sha256(ROOT / name) for name in SOURCE_FILES}


def design_matrix() -> np.ndarray:
    i = np.arange(P, dtype=float)
    cols = [np.ones(P) / np.sqrt(P)]
    cols += [np.sqrt(2 / P) * np.cos(2 * np.pi * i / P)]
    cols += [np.sqrt(2 / P) * np.sin(2 * np.pi * i / P)]
    cols += [np.sqrt(2 / P) * np.cos(4 * np.pi * i / P)]
    return np.column_stack(cols)


def protocol() -> dict:
    x = design_matrix()
    sigma = RHO ** np.abs(np.subtract.outer(np.arange(P), np.arange(P)))
    return {
        "schema": "pion-chi2-factorized-calibration-v1",
        "classification": "pre-registered synthetic CPU method diagnostic; not physical or full-certificate validation",
        "purpose": "Separate nominal chi-square reference behavior with known covariance from estimated covariance, rank deficiency, shrinkage, and eigenvalue-floor effects.",
        "model": {
            "data": "B independent Gaussian block vectors y_b = X beta + epsilon_b",
            "dimension": P,
            "fitted_parameters": Q,
            "nominal_dof": DF,
            "design_matrix": x.tolist(),
            "design_gram_max_abs_error": float(np.max(np.abs(x.T @ x - np.eye(Q)))),
            "beta": [0.2, -0.4, 0.1, 0.3],
            "covariance": sigma.tolist(),
            "covariance_definition": f"Sigma[i,j] = {RHO} ** abs(i-j), marginal variance 1",
            "covariance_condition_number": float(np.linalg.cond(sigma)),
        },
        "blocks_per_dataset": list(BLOCKS),
        "covariance_methods": [
            {"name": "known_covariance", "description": "Use the exact Sigma/B; control for nominal chi-square behavior."},
            {"name": "shrink_0.0", "shrinkage": 0.0},
            {"name": "shrink_0.25", "shrinkage": 0.25, "description": "Production shrinkage value."},
            {"name": "shrink_0.5", "shrinkage": 0.5},
        ],
        "estimated_covariance": "Sample covariance across the B block vectors divided by B, using tasks.pion_projection.statistics.inverse_covariance.",
        "eigen_floor_relative_to_largest_eigenvalue": EIGEN_FLOOR_REL,
        "primary_test": "Reject if chi-square survival probability with df=8 is below 0.05.",
        "secondary_calibration": "For each B and covariance method, use an independent N_CAL null calibration sample to form upper-tail Monte Carlo rank p-values, then evaluate rejection on independent N_EVAL datasets. This checks transfer under the same declared Gaussian DGP and is not a conditional production bootstrap.",
        "independent_dataset_counts": {"calibration": N_CAL, "evaluation": N_EVAL},
        "intervals": "Two-sided exact Clopper-Pearson 95% intervals for held-out rejection rates; calibration critical values are point estimates.",
        "alpha": ALPHA,
        "seed": {"base": BASE_SEED, "rule": "SeedSequence([BASE_SEED, block_count, split_id]); split_id=0 calibration, split_id=1 evaluation. Methods are paired on identical block samples."},
        "outputs": list(OUTPUTS),
        "output_directory": str(OUT.relative_to(ROOT)),
        "frozen_sources": list(SOURCE_FILES),
    }


def cp95(k: int, n: int) -> list[float]:
    lo = 0.0 if k == 0 else float(beta.ppf(0.025, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(0.975, k + 1, n - k))
    return [lo, hi]


def sample_batch(rng: np.random.Generator, b: int, n: int, x: np.ndarray,
                 beta_true: np.ndarray, chol: np.ndarray) -> np.ndarray:
    mean = x @ beta_true
    noise = rng.normal(size=(n, b, P)) @ chol.T
    return mean[None, None, :] + noise


def statistic(block_vectors: np.ndarray, method: str, x: np.ndarray,
              beta_true: np.ndarray, sigma: np.ndarray) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Return fitted quadratic forms and covariance diagnostics for a batch."""
    n, b, _ = block_vectors.shape
    means = block_vectors.mean(axis=1)
    q_values = np.empty(n)
    ranks = np.full(n, np.nan)
    floor_fractions = np.full(n, np.nan)
    conditions = np.full(n, np.nan)
    if method == "known_covariance":
        weight = np.linalg.inv(sigma / b)
        xtw = x.T @ weight
        normal_inverse = np.linalg.inv(xtw @ x)
        for j in range(n):
            fitted = x @ (normal_inverse @ (xtw @ means[j]))
            residual = means[j] - fitted
            q_values[j] = residual @ weight @ residual
        return q_values, {"rank": ranks, "floor_fraction": floor_fractions, "condition": conditions}

    shrink = float(method.removeprefix("shrink_"))
    for j, rows in enumerate(block_vectors):
        raw_cov = np.atleast_2d(np.cov(rows, rowvar=False, ddof=1))
        eig_raw = np.linalg.eigvalsh(raw_cov)
        scale_raw = float(np.max(eig_raw))
        ranks[j] = float(np.linalg.matrix_rank(raw_cov, tol=scale_raw * EIGEN_FLOOR_REL))
        shrunk = (1 - shrink) * raw_cov + shrink * np.diag(np.diag(raw_cov))
        eig, _ = np.linalg.eigh(shrunk)
        scale = float(np.max(eig))
        floor = scale * EIGEN_FLOOR_REL
        floor_fractions[j] = float(np.mean(eig <= floor))
        conditions[j] = scale / max(float(np.min(eig)), floor)
        weight = inverse_covariance(rows, shrink=shrink)
        normal = x.T @ weight @ x
        fitted = x @ np.linalg.solve(normal, x.T @ weight @ means[j])
        residual = means[j] - fitted
        q_values[j] = residual @ weight @ residual
    return q_values, {"rank": ranks, "floor_fraction": floor_fractions, "condition": conditions}


def prepare() -> None:
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite {OUT}")
    OUT.mkdir(parents=True)
    frozen = protocol()
    (OUT / "protocol.json").write_text(json.dumps(frozen, indent=2, sort_keys=True) + "\n")
    registration = {
        "protocol_sha256": hashlib.sha256(canonical(frozen)).hexdigest(),
        "source_sha256": source_manifest(),
        "prepared_utc": "2026-11-20T00:00:00Z",
    }
    (OUT / "preregistration.json").write_text(json.dumps(registration, indent=2, sort_keys=True) + "\n")
    print("prepared", OUT.relative_to(ROOT), registration["protocol_sha256"])


def run() -> None:
    frozen = json.loads((OUT / "protocol.json").read_text())
    registration = json.loads((OUT / "preregistration.json").read_text())
    if registration["source_sha256"] != source_manifest():
        raise RuntimeError("source hash differs from preregistration")
    if registration["protocol_sha256"] != hashlib.sha256(canonical(frozen)).hexdigest():
        raise RuntimeError("protocol hash differs from preregistration")
    if any((OUT / name).exists() for name in OUTPUTS):
        raise FileExistsError("final outputs already exist; refusing overwrite")

    x = np.asarray(frozen["model"]["design_matrix"], dtype=float)
    sigma = np.asarray(frozen["model"]["covariance"], dtype=float)
    beta_true = np.asarray(frozen["model"]["beta"], dtype=float)
    chol = np.linalg.cholesky(sigma)
    chi2_cut = float(chi2.ppf(1 - ALPHA, DF))
    arrays: dict[str, np.ndarray] = {}
    cells = []

    for b in BLOCKS:
        rng_cal = np.random.default_rng(np.random.SeedSequence([BASE_SEED, b, 0]))
        rng_eval = np.random.default_rng(np.random.SeedSequence([BASE_SEED, b, 1]))
        cal_data = sample_batch(rng_cal, b, N_CAL, x, beta_true, chol)
        eval_data = sample_batch(rng_eval, b, N_EVAL, x, beta_true, chol)
        by_method = {}
        eval_nominal_flags = {}
        for method in METHODS:
            q_cal, diag_cal = statistic(cal_data, method, x, beta_true, sigma)
            q_eval, diag_eval = statistic(eval_data, method, x, beta_true, sigma)
            sorted_cal = np.sort(q_cal)
            mc_p = (1 + N_CAL - np.searchsorted(sorted_cal, q_eval, side="left")) / (N_CAL + 1)
            nominal_p = chi2.sf(q_eval, DF)
            nominal_reject = nominal_p < ALPHA
            calibrated_reject = mc_p < ALPHA
            eval_nominal_flags[method] = nominal_reject
            k_nominal = int(nominal_reject.sum())
            k_calibrated = int(calibrated_reject.sum())
            critical = float(np.quantile(q_cal, 1 - ALPHA, method="higher"))
            by_method[method] = {
                "n_calibration": N_CAL,
                "n_evaluation": N_EVAL,
                "nominal_chi2_reject": k_nominal,
                "nominal_chi2_rate": k_nominal / N_EVAL,
                "nominal_chi2_cp95": cp95(k_nominal, N_EVAL),
                "rank_calibrated_reject": k_calibrated,
                "rank_calibrated_rate": k_calibrated / N_EVAL,
                "rank_calibrated_cp95": cp95(k_calibrated, N_EVAL),
                "calibration_q95": critical,
                "q95_over_nominal_chi2_q95": critical / chi2_cut,
                "calibration_median_q": float(np.median(q_cal)),
            }
            arrays[f"blocks_{b}_{method}_q_cal"] = q_cal
            arrays[f"blocks_{b}_{method}_q_eval"] = q_eval
            arrays[f"blocks_{b}_{method}_mc_p_eval"] = mc_p
            arrays[f"blocks_{b}_{method}_rank_eval"] = diag_eval["rank"]
            arrays[f"blocks_{b}_{method}_floor_fraction_eval"] = diag_eval["floor_fraction"]
            arrays[f"blocks_{b}_{method}_condition_eval"] = diag_eval["condition"]

        for method in METHODS[1:]:
            d = by_method[method]
            d["median_raw_covariance_rank"] = float(np.nanmedian(arrays[f"blocks_{b}_{method}_rank_eval"]))
            d["median_eigen_floor_fraction"] = float(np.nanmedian(arrays[f"blocks_{b}_{method}_floor_fraction_eval"]))
            d["median_regularized_condition_number"] = float(np.nanmedian(arrays[f"blocks_{b}_{method}_condition_eval"]))
        cells.append({"blocks": b, "nominal_chi2_critical_value": chi2_cut, "methods": by_method})
        print(f"blocks={b}", {m: by_method[m]["nominal_chi2_reject"] for m in METHODS})

    summary = {
        "schema": "pion-chi2-factorized-calibration-summary-v1",
        "classification": frozen["classification"],
        "protocol_sha256": registration["protocol_sha256"],
        "source_sha256": registration["source_sha256"],
        "independent_dataset_counts": {"calibration": N_CAL, "evaluation": N_EVAL},
        "cells": cells,
    }
    np.savez_compressed(OUT / "raw_scores.npz", **arrays)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    write_figure(summary, arrays)
    (OUT / "README.md").write_text(render_readme(summary))
    provenance = {
        "protocol_sha256": registration["protocol_sha256"],
        "preregistered_source_sha256": registration["source_sha256"],
        "current_source_sha256": source_manifest(),
        "planned_calibration_datasets": N_CAL * len(BLOCKS) * len(METHODS),
        "planned_evaluation_datasets": N_EVAL * len(BLOCKS) * len(METHODS),
        "completed_cells": len(cells) * len(METHODS),
        "artifact_sha256": {name: sha256(OUT / name) for name in OUTPUTS},
    }
    (OUT / "execution_provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    print("completed", OUT.relative_to(ROOT))


def write_figure(summary: dict, arrays: dict[str, np.ndarray]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.5))
    colors = {"known_covariance": "#222222", "shrink_0.0": "#4477AA",
              "shrink_0.25": "#CC6677", "shrink_0.5": "#228833"}
    labels = {"known_covariance": "Known covariance", "shrink_0.0": "Shrinkage 0",
              "shrink_0.25": "Production 0.25", "shrink_0.5": "Shrinkage 0.5"}
    for method in METHODS:
        y, lo, hi = [], [], []
        for cell in summary["cells"]:
            d = cell["methods"][method]
            y.append(d["nominal_chi2_rate"])
            lo.append(d["nominal_chi2_cp95"][0])
            hi.append(d["nominal_chi2_cp95"][1])
        axes[0, 0].errorbar(BLOCKS, y, yerr=[np.array(y)-lo, hi-np.array(y)],
                            marker="o", capsize=3, color=colors[method], label=labels[method])
    axes[0, 0].axhline(ALPHA, color="black", linestyle="--", linewidth=1)
    axes[0, 0].set(title="Nominal chi-square size", xlabel="Independent blocks B", ylabel="Held-out rejection rate")
    axes[0, 0].legend(fontsize=8)

    for method in METHODS:
        ratios = [cell["methods"][method]["q95_over_nominal_chi2_q95"] for cell in summary["cells"]]
        axes[0, 1].plot(BLOCKS, ratios, marker="o", color=colors[method], label=labels[method])
    axes[0, 1].axhline(1, color="black", linestyle="--", linewidth=1)
    axes[0, 1].set(title="Empirical calibration q95 / chi-square q95", xlabel="Independent blocks B", ylabel="Critical-value ratio", yscale="log")

    b = 12
    bins = np.linspace(0, 1, 11)
    for method in METHODS:
        pvals = arrays[f"blocks_{b}_{method}_mc_p_eval"]
        axes[1, 0].hist(pvals, bins=bins, density=True, histtype="step", linewidth=1.5,
                        color=colors[method], label=labels[method])
    axes[1, 0].axhline(1, color="black", linestyle="--", linewidth=1)
    axes[1, 0].set(title="Independent rank-calibrated p-values (B=12)", xlabel="Monte Carlo p-value", ylabel="Density", ylim=(0, 2.2))
    axes[1, 0].legend(fontsize=8)

    for method in METHODS[1:]:
        rank = [cell["methods"][method]["median_raw_covariance_rank"] for cell in summary["cells"]]
        axes[1, 1].plot(BLOCKS, rank, marker="o", color=colors[method], label=labels[method])
    axes[1, 1].axhline(P, color="black", linestyle="--", linewidth=1, label="Dimension p=12")
    axes[1, 1].set(title="Median raw sample-covariance rank", xlabel="Independent blocks B", ylabel="Numerical rank", ylim=(0, P+1))
    axes[1, 1].legend(fontsize=8)
    fig.suptitle("Factorized finite-sample calibration diagnostic (synthetic Gaussian linear null)")
    fig.tight_layout()
    fig.savefig(OUT / "factorized_calibration.png", dpi=160)
    plt.close(fig)


def render_readme(summary: dict) -> str:
    lines = [
        "# Factorized calibration of the pion chi-square subgate",
        "",
        "This preregistered controlled Gaussian linear-model study separates nominal chi-square behavior with known covariance from finite-sample effects caused by estimating covariance, shrinkage, rank deficiency, and the eigenvalue floor. It is not an end-to-end `fit_reference_gate` test, a physical validation, or a replacement production gate.",
        "",
        "## Design and method",
        "",
        f"The model has p={P} data components, q={Q} fitted linear parameters, and nominal df={DF}. The covariance is AR(1)-like with rho={RHO}; 6, 12, and 24 independent blocks are used. Each B/method cell has {N_CAL} independent calibration datasets and a separate {N_EVAL}-dataset evaluation sample. Four methods are compared on paired raw datasets: known covariance, and estimated covariance with shrinkage 0, 0.25, and 0.5. The production relative eigen floor is {EIGEN_FLOOR_REL:g}.",
        "",
        "The nominal rule uses the chi-square(df=8) 95% critical value. The second rule ranks each held-out statistic against the independent calibration sample for the same declared B/method/DGP; it is an unconditional Monte Carlo rank calibration under a known synthetic null, not a conditional parametric bootstrap from observed correlators.",
        "",
        "## Held-out results",
        "",
        "Rates include exact marginal CP95 intervals. The empirical q95 is estimated from the independent calibration sample; no uncertainty interval is attached to that critical-value estimate.",
        "",
        "| Blocks | Method | Nominal chi-square rejects | Rank-calibrated rejects | Calibration q95 / nominal q95 | Median raw covariance rank | Median eigen-floor fraction |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for cell in summary["cells"]:
        for method in METHODS:
            d = cell["methods"][method]
            nominal_ci = d["nominal_chi2_cp95"]
            calibrated_ci = d["rank_calibrated_cp95"]
            rank = "—" if method == "known_covariance" else f"{d['median_raw_covariance_rank']:.1f}"
            floor = "—" if method == "known_covariance" else f"{d['median_eigen_floor_fraction']:.3f}"
            lines.append(
                f"| {cell['blocks']} | {method} | {d['nominal_chi2_reject']}/{N_EVAL} "
                f"({d['nominal_chi2_rate']:.3f}, [{nominal_ci[0]:.3f}, {nominal_ci[1]:.3f}]) | "
                f"{d['rank_calibrated_reject']}/{N_EVAL} ({d['rank_calibrated_rate']:.3f}, "
                f"[{calibrated_ci[0]:.3f}, {calibrated_ci[1]:.3f}]) | "
                f"{d['q95_over_nominal_chi2_q95']:.3g} | {rank} | {floor} |"
            )
    lines += [
        "",
        "![Factorized finite-sample calibration diagnostic](factorized_calibration.png)",
        "",
        "## Interpretation boundary",
        "",
        "Known covariance is a control for the nominal chi-square reference in this fixed linear-Gaussian model. Estimated-covariance results expose finite-B behavior in a controlled p=12, q=4 setting. Independent rank calibration should be near 5% under the same generator by construction; it does not establish transfer to time-correlated lattice correlators, nonlinear mass fits, the production certificate, or physical ensembles.",
        "",
        "The next method step, only if it could change the production gate decision, is to compare this controlled result against the real reference-fit model using a separately preregistered conditional parametric/block bootstrap and generator-shift controls. Keep failures, ill-conditioned cases, rank, and abstentions visible. Never tune shrinkage on this synthetic null to force nominal size.",
        "",
        "Raw calibration/evaluation statistics, Monte Carlo p-values, ranks, floor fractions, conditions, frozen protocol, and hashes are stored alongside this report. Verify with `python -B -m tasks.pion_projection.certificate_subgate_factorized --verify`.",
    ]
    return "\n".join(lines) + "\n"


def verify() -> None:
    frozen = json.loads((OUT / "protocol.json").read_text())
    registration = json.loads((OUT / "preregistration.json").read_text())
    if registration["protocol_sha256"] != hashlib.sha256(canonical(frozen)).hexdigest():
        raise RuntimeError("protocol hash mismatch")
    if registration["source_sha256"] != source_manifest():
        raise RuntimeError("source hash mismatch")
    provenance = json.loads((OUT / "execution_provenance.json").read_text())
    if provenance["current_source_sha256"] != source_manifest():
        raise RuntimeError("execution source hash mismatch")
    for name, expected in provenance["artifact_sha256"].items():
        if sha256(OUT / name) != expected:
            raise RuntimeError(f"artifact hash mismatch: {name}")
    summary = json.loads((OUT / "summary.json").read_text())
    with np.load(OUT / "raw_scores.npz") as data:
        if len(summary["cells"]) != len(BLOCKS):
            raise RuntimeError("summary cell count mismatch")
        for cell in summary["cells"]:
            b = cell["blocks"]
            for method in METHODS:
                d = cell["methods"][method]
                q_eval = data[f"blocks_{b}_{method}_q_eval"]
                p_eval = data[f"blocks_{b}_{method}_mc_p_eval"]
                if len(q_eval) != N_EVAL or len(p_eval) != N_EVAL:
                    raise RuntimeError(f"row count mismatch for B={b}, method={method}")
                if not np.all(np.isfinite(q_eval)) or not np.all(np.isfinite(p_eval)):
                    raise RuntimeError(f"nonfinite scores for B={b}, method={method}")
                if int(np.sum(chi2.sf(q_eval, DF) < ALPHA)) != d["nominal_chi2_reject"]:
                    raise RuntimeError(f"nominal count mismatch for B={b}, method={method}")
                if int(np.sum(p_eval < ALPHA)) != d["rank_calibrated_reject"]:
                    raise RuntimeError(f"calibrated count mismatch for B={b}, method={method}")
    print(f"verified hashes, {len(BLOCKS)*len(METHODS)} cells, {N_CAL} calibration + {N_EVAL} evaluation datasets/cell")


def main() -> None:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--prepare", action="store_true")
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.prepare:
        prepare()
    elif args.run:
        run()
    else:
        verify()


if __name__ == "__main__":
    main()
