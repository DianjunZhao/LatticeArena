"""Conditional Gaussian parametric-bootstrap diagnostic for the pion reference gate."""
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

from .certificate_calibration import PROTOCOL as DATA_PROTOCOL
from .certificate_calibration import world
from .gate import fit_reference_gate
from .statistics import blocks, fold, shape


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/pion_projection/certificate_subgate_bootstrap_20261120_v1"
BLOCKS = (6, 12, 24)
TIME_RHOS = (0.5, 0.8)
N_OUTER = 250
N_BOOT = 399
BASE_SEED = 2026112600
ALPHA = 0.05
SHRINKAGE = float(DATA_PROTOCOL["covariance_shrinkage"])
EIGEN_FLOOR_REL = 1e-10
SOURCE_FILES = (
    "tasks/pion_projection/certificate_subgate_bootstrap.py",
    "tasks/pion_projection/certificate_calibration.py",
    "tasks/pion_projection/gate.py",
    "tasks/pion_projection/reference.py",
    "tasks/pion_projection/statistics.py",
    "results/pion_projection/s16t16_v1/development_provenance.json",
)
OUTPUTS = ("raw_outcomes.json", "summary.json", "bootstrap_calibration.png", "README.md")


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_manifest() -> dict[str, str]:
    return {name: sha256(ROOT / name) for name in SOURCE_FILES}


def protocol() -> dict:
    return {
        "schema": "pion-chi2-conditional-bootstrap-v1",
        "classification": "synthetic CPU method diagnostic; conditional plug-in bootstrap, not physical/full-certificate validation",
        "purpose": "Compare nominal chi-square p-values with a conditional Gaussian parametric-bootstrap p-value for the actual single-state reference-fit implementation, under baseline and time-correlation-shifted synthetic nulls.",
        "null_world": "certificate_calibration.world with zero excited-state contamination, noise=0.02, cfg_sigma=0.01, block length from frozen data protocol; baseline time AR rho=0.5 and generator-shift rho=0.8.",
        "blocks_per_dataset": list(BLOCKS),
        "time_rho_worlds": list(TIME_RHOS),
        "n_independent_outer_datasets_per_cell": N_OUTER,
        "conditional_bootstrap_draws_per_outer_dataset": N_BOOT,
        "bootstrap_model": "Fit the actual production reference gate; in its normalized selected reference-vector space, use the fitted single-cosh mean and the empirical block covariance regularized with production diagonal shrinkage 0.25 and relative eigen floor 1e-10; draw B Gaussian block vectors; remap into block data and rerun fit_reference_gate including covariance re-estimation and nonlinear mass fit.",
        "bootstrap_p_value": "(1 + number of bootstrap chi-square statistics >= observed statistic + invalid bootstrap draws)/(N_BOOT + 1); invalid draws are conservatively counted in the upper tail, never dropped.",
        "gate_rule": "p < 0.05 is REJECT; original fit failures remain INVALID; every planned outer dataset stays in the denominator table.",
        "intervals": "Exact two-sided marginal CP95 rejection intervals among valid observed fits; planned/invalid counts are reported separately. Paired nominal-vs-bootstrap difference intervals use dataset bootstrap with Bonferroni family coverage over six scenario-by-block cells.",
        "seeds": {"base": BASE_SEED, "outer_rule": "SeedSequence([BASE_SEED, round(time_rho*10), blocks, dataset_id, 0])", "bootstrap_rule": "SeedSequence([BASE_SEED, round(time_rho*10), blocks, dataset_id, 1])", "contrast_bootstrap_seed": BASE_SEED + 99, "contrast_bootstrap_draws": 10000},
        "frozen_data_protocol": {key: DATA_PROTOCOL[key] for key in ("geometry", "reference_basis", "reference_windows", "reference_nominal_window", "block_length", "covariance_shrinkage", "mass_bounds")},
        "outputs": list(OUTPUTS),
        "output_directory": str(OUT.relative_to(ROOT)),
        "frozen_sources": list(SOURCE_FILES),
    }


def cp95(k: int, n: int) -> list[float]:
    if n <= 0:
        return [0.0, 1.0]
    lo = 0.0 if k == 0 else float(beta.ppf(0.025, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(0.975, k + 1, n - k))
    return [lo, hi]


def fitted_mean_and_covariance(ref, mass: float, p: dict) -> tuple[np.ndarray, np.ndarray]:
    mean = ref.samples.mean(axis=0)
    nchan = len(p["reference_basis"])
    times = p["reference_windows"][p["reference_nominal_window"]]
    temporal = p["geometry"][3]
    f = shape(mass, times, temporal)
    design = np.kron(np.eye(nchan), f[:, None])
    amp = np.linalg.solve(design.T @ ref.inv @ design, design.T @ ref.inv @ mean)
    fitted_mean = design @ amp

    samples = ref.samples
    cov = np.atleast_2d(np.cov(samples, rowvar=False, ddof=1))
    cov = (1 - SHRINKAGE) * cov + SHRINKAGE * np.diag(np.diag(cov))
    eig, vec = np.linalg.eigh(cov)
    scale = float(np.max(eig))
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError("bootstrap covariance is unidentifiable")
    eig = np.maximum(eig, scale * EIGEN_FLOOR_REL)
    cov_regularized = (vec * eig) @ vec.T
    return fitted_mean, cov_regularized


def remap_normalized_samples(samples: np.ndarray, ref) -> np.ndarray:
    b = len(samples)
    basis = DATA_PROTOCOL["reference_basis"]
    window = DATA_PROTOCOL["reference_windows"][DATA_PROTOCOL["reference_nominal_window"]]
    ntime = len(window)
    channel_time = samples.reshape(b, len(basis), ntime)
    data = np.zeros((b, len(DATA_PROTOCOL["reference_basis"]) + 4, DATA_PROTOCOL["geometry"][3] // 2 + 1))
    for ch_index, channel in enumerate(basis):
        for time_index, time in enumerate(window):
            data[:, channel, time] = channel_time[:, ch_index, time_index] * ref.scales[ch_index]
    return data


def run_one_dataset(dev: np.ndarray, rng_boot: np.random.Generator) -> dict:
    try:
        ref, mass, observed_q, dof, p_chi = fit_reference_gate(dev, DATA_PROTOCOL, "single")
        if not np.isfinite(p_chi) or not np.isfinite(observed_q):
            return {"status": "INVALID_OBSERVED", "reason": "nonfinite_gate_output"}
        fitted_mean, cov = fitted_mean_and_covariance(ref, mass, DATA_PROTOCOL)
    except Exception as exc:
        return {"status": "INVALID_OBSERVED", "reason": f"{type(exc).__name__}: {exc}"}

    boot_q = []
    invalid_boot = 0
    nblocks = len(dev)
    try:
        for _ in range(N_BOOT):
            samples = rng_boot.multivariate_normal(fitted_mean, cov, size=nblocks, check_valid="raise")
            boot_dev = remap_normalized_samples(samples, ref)
            try:
                _, _, q, _, _ = fit_reference_gate(boot_dev, DATA_PROTOCOL, "single")
                if np.isfinite(q):
                    boot_q.append(float(q))
                else:
                    invalid_boot += 1
            except Exception:
                invalid_boot += 1
    except Exception as exc:
        return {
            "status": "INVALID_BOOTSTRAP_GENERATION",
            "reason": f"{type(exc).__name__}: {exc}",
            "p_chi2": float(p_chi), "observed_chi2": float(observed_q),
            "dof": int(dof), "n_boot_valid": len(boot_q), "n_boot_invalid": invalid_boot,
        }
    n_extreme = sum(q >= observed_q for q in boot_q) + invalid_boot
    p_boot = (1 + n_extreme) / (N_BOOT + 1)
    return {
        "status": "VALID",
        "p_chi2": float(p_chi),
        "p_bootstrap": float(p_boot),
        "observed_chi2": float(observed_q),
        "dof": int(dof),
        "bootstrap_extreme_valid": int(sum(q >= observed_q for q in boot_q)),
        "bootstrap_invalid_conservative_extreme": int(invalid_boot),
        "n_boot_valid": len(boot_q),
        "n_boot_invalid": int(invalid_boot),
        "bootstrap_q_median": float(np.median(boot_q)) if boot_q else None,
        "bootstrap_q95": float(np.quantile(boot_q, 0.95)) if boot_q else None,
    }


def paired_ci(values: np.ndarray, rng: np.random.Generator) -> list[float]:
    n = len(values)
    draws = rng.integers(0, n, size=(10000, n))
    means = values[draws].mean(axis=1)
    tail = 0.05 / (2 * len(BLOCKS) * len(TIME_RHOS))
    return [float(np.quantile(means, tail)), float(np.quantile(means, 1 - tail))]


def prepare() -> None:
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite {OUT}")
    OUT.mkdir(parents=True)
    frozen = protocol()
    (OUT / "protocol.json").write_text(json.dumps(frozen, indent=2, sort_keys=True) + "\n")
    registration = {
        "protocol_sha256": hashlib.sha256(canonical(frozen)).hexdigest(),
        "source_sha256": source_manifest(),
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

    contamination = np.zeros(len(DATA_PROTOCOL["reference_basis"]) + 4)
    raw = {}
    cells = []
    for time_rho in TIME_RHOS:
        for nblocks in BLOCKS:
            outcomes = []
            for dataset_id in range(N_OUTER):
                rng_world = np.random.default_rng(np.random.SeedSequence(
                    [BASE_SEED, round(time_rho * 10), nblocks, dataset_id, 0]))
                rng_boot = np.random.default_rng(np.random.SeedSequence(
                    [BASE_SEED, round(time_rho * 10), nblocks, dataset_id, 1]))
                ncfg = nblocks * DATA_PROTOCOL["block_length"]
                data = world(rng_world, ncfg, contamination, time_rho=time_rho)
                dev = blocks(fold(data), DATA_PROTOCOL["block_length"])
                row = {"dataset_id": dataset_id, **run_one_dataset(dev, rng_boot)}
                outcomes.append(row)
                if (dataset_id + 1) % 50 == 0:
                    print(f"rho={time_rho} blocks={nblocks} datasets={dataset_id+1}/{N_OUTER}", flush=True)
            key = f"rho_{time_rho}_blocks_{nblocks}"
            raw[key] = outcomes

            valid = [row for row in outcomes if row["status"] == "VALID"]
            nvalid = len(valid)
            k_chi = sum(row["p_chi2"] < ALPHA for row in valid)
            k_boot = sum(row["p_bootstrap"] < ALPHA for row in valid)
            invalid_boot = sum(row.get("n_boot_invalid", 0) for row in valid)
            d_chi = {
                "reject": k_chi, "n_valid_observed": nvalid, "n_planned": N_OUTER,
                "rate_valid": k_chi / nvalid if nvalid else None,
                "cp95_valid": cp95(k_chi, nvalid),
            }
            d_boot = {
                "reject": k_boot, "n_valid_observed": nvalid, "n_planned": N_OUTER,
                "rate_valid": k_boot / nvalid if nvalid else None,
                "cp95_valid": cp95(k_boot, nvalid),
                "invalid_bootstrap_draws_total": invalid_boot,
                "planned_bootstrap_draws": N_OUTER * N_BOOT,
            }
            paired = np.array([(row["p_bootstrap"] < ALPHA) - (row["p_chi2"] < ALPHA) for row in valid], dtype=float)
            contrast = {
                "bootstrap_minus_chi2_rejection_rate": float(paired.mean()) if nvalid else None,
                "n_paired_valid_datasets": nvalid,
                "familywise_cp_bootstrap_ci95": paired_ci(paired, np.random.default_rng(BASE_SEED + 99 + nblocks + int(time_rho * 1000))) if nvalid else None,
                "bootstrap_only_reject": int(np.sum(paired > 0)),
                "chi2_only_reject": int(np.sum(paired < 0)),
            }
            cell = {
                "time_rho": time_rho,
                "blocks": nblocks,
                "n_planned_outer": N_OUTER,
                "n_invalid_observed": N_OUTER - nvalid,
                "nominal_chi2": d_chi,
                "conditional_parametric_bootstrap": d_boot,
                "paired_contrast": contrast,
                "median_p_chi2": float(np.median([r["p_chi2"] for r in valid])) if valid else None,
                "median_p_bootstrap": float(np.median([r["p_bootstrap"] for r in valid])) if valid else None,
                "mean_bootstrap_invalid_per_dataset": invalid_boot / nvalid if nvalid else None,
            }
            cells.append(cell)
            print(f"cell rho={time_rho} B={nblocks}: chi2={k_chi}/{nvalid}, bootstrap={k_boot}/{nvalid}, invalid_boot={invalid_boot}", flush=True)

    summary = {
        "schema": "pion-chi2-conditional-bootstrap-summary-v1",
        "classification": frozen["classification"],
        "protocol_sha256": registration["protocol_sha256"],
        "source_sha256": registration["source_sha256"],
        "n_outer_per_cell": N_OUTER,
        "n_bootstrap_per_outer": N_BOOT,
        "cells": cells,
    }
    (OUT / "raw_outcomes.json").write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    write_figure(summary, raw)
    (OUT / "README.md").write_text(render_readme(summary))
    provenance = {
        "protocol_sha256": registration["protocol_sha256"],
        "preregistered_source_sha256": registration["source_sha256"],
        "current_source_sha256": source_manifest(),
        "planned_outer_datasets": N_OUTER * len(BLOCKS) * len(TIME_RHOS),
        "completed_outer_datasets": sum(len(values) for values in raw.values()),
        "planned_bootstrap_fits": N_OUTER * N_BOOT * len(BLOCKS) * len(TIME_RHOS),
        "artifact_sha256": {name: sha256(OUT / name) for name in OUTPUTS},
    }
    (OUT / "execution_provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    print("completed", OUT.relative_to(ROOT))


def write_figure(summary: dict, raw: dict) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.5))
    colors = {"chi2": "#4477AA", "bootstrap": "#CC6677"}
    titles = {0.5: "Baseline generator: time AR rho=0.5", 0.8: "Shifted generator: time AR rho=0.8"}
    for col, rho in enumerate(TIME_RHOS):
        for method, key in (("chi2", "nominal_chi2"), ("bootstrap", "conditional_parametric_bootstrap")):
            cells = [c for c in summary["cells"] if c["time_rho"] == rho]
            rates = [c[key]["rate_valid"] for c in cells]
            lower = [c[key]["cp95_valid"][0] for c in cells]
            upper = [c[key]["cp95_valid"][1] for c in cells]
            axes[0, col].errorbar(BLOCKS, rates,
                                  yerr=[np.array(rates)-lower, np.array(upper)-rates],
                                  marker="o", capsize=3, color=colors[method], label=method)
        axes[0, col].axhline(ALPHA, color="black", linestyle="--", linewidth=1)
        axes[0, col].set(title=titles[rho], xlabel="Independent blocks B", ylabel="Null rejection rate")
        axes[0, col].legend()

    b = 12
    bins = np.linspace(0, 1, 11)
    for rho, style in ((0.5, "-"), (0.8, "--")):
        rows = raw[f"rho_{rho}_blocks_{b}"]
        pchi = [r["p_chi2"] for r in rows if r["status"] == "VALID"]
        pboot = [r["p_bootstrap"] for r in rows if r["status"] == "VALID"]
        axes[1, 0].hist(pchi, bins=bins, density=True, histtype="step", linestyle=style,
                        color=colors["chi2"], linewidth=1.5, label=f"chi2, rho={rho}")
        axes[1, 0].hist(pboot, bins=bins, density=True, histtype="step", linestyle=style,
                        color=colors["bootstrap"], linewidth=1.5, label=f"bootstrap, rho={rho}")
    axes[1, 0].axhline(1, color="black", linestyle=":", linewidth=1)
    axes[1, 0].set(title="Observed p-values (B=12)", xlabel="p-value", ylabel="Density", ylim=(0, 2.5))
    axes[1, 0].legend(fontsize=7)

    invalid_rate = [c["conditional_parametric_bootstrap"]["invalid_bootstrap_draws_total"] /
                    max(1, c["conditional_parametric_bootstrap"]["planned_bootstrap_draws"])
                    for c in summary["cells"]]
    labels = [f"{c['time_rho']}/{c['blocks']}" for c in summary["cells"]]
    axes[1, 1].bar(np.arange(len(labels)), invalid_rate, color="#999999")
    axes[1, 1].set(title="Invalid bootstrap draw fraction", xlabel="time rho / blocks", ylabel="Invalid / planned", xticks=np.arange(len(labels)), xticklabels=labels)
    axes[1, 1].tick_params(axis="x", labelrotation=45)
    fig.suptitle("Conditional parametric bootstrap for production pion reference fit")
    fig.tight_layout()
    fig.savefig(OUT / "bootstrap_calibration.png", dpi=160)
    plt.close(fig)


def render_readme(summary: dict) -> str:
    lines = [
        "# Conditional parametric bootstrap of the pion chi-square subgate",
        "",
        "This preregistered CPU diagnostic reruns the actual single-state reference fit and chi-square gate. It compares nominal chi-square p-values to a plug-in Gaussian parametric bootstrap in the normalized selected reference-vector space. It is not physical validation or a full-certificate test.",
        "",
        f"The two synthetic null generators use time AR rho=0.5 (baseline) and rho=0.8 (shift), {N_OUTER} independent outer datasets per block-count cell, and {N_BOOT} bootstrap draws per outer dataset. The bootstrap uses the fitted mass/amplitudes, empirical block covariance, production shrinkage {SHRINKAGE}, and the production relative eigen floor {EIGEN_FLOOR_REL:g}; every bootstrap sample is refit through `fit_reference_gate`.",
        "",
        "Bootstrap p-values count invalid bootstrap draws conservatively in the upper tail. Invalid original fits are retained and reported separately. Confidence intervals are marginal CP95 among valid observed fits; paired differences use a six-cell familywise bootstrap interval.",
        "",
        "| time AR rho | Blocks | Valid / planned | chi-square rejects | Bootstrap rejects | Paired bootstrap−chi2 rate difference (familywise CI95) | Invalid bootstrap draws / planned |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for cell in summary["cells"]:
        chi = cell["nominal_chi2"]
        boot = cell["conditional_parametric_bootstrap"]
        pair = cell["paired_contrast"]
        planned_boot = boot["planned_bootstrap_draws"]
        diff_ci = pair["familywise_cp_bootstrap_ci95"]
        diff_text = "NA" if diff_ci is None else f"{pair['bootstrap_minus_chi2_rejection_rate']:+.3f} [{diff_ci[0]:+.3f}, {diff_ci[1]:+.3f}]"
        lines.append(
            f"| {cell['time_rho']} | {cell['blocks']} | {chi['n_valid_observed']}/{chi['n_planned']} | "
            f"{chi['reject']}/{chi['n_valid_observed']} ({chi['rate_valid']:.3f}, CP95 [{chi['cp95_valid'][0]:.3f}, {chi['cp95_valid'][1]:.3f}]) | "
            f"{boot['reject']}/{boot['n_valid_observed']} ({boot['rate_valid']:.3f}, CP95 [{boot['cp95_valid'][0]:.3f}, {boot['cp95_valid'][1]:.3f}]) | "
            f"{diff_text} | {boot['invalid_bootstrap_draws_total']}/{planned_boot} |"
        )
    lines += [
        "",
        "![Conditional bootstrap calibration](bootstrap_calibration.png)",
        "",
        "## Interpretation and limits",
        "",
        "The bootstrap conditions on a fitted Gaussian mean and regularized covariance estimated from each observed dataset, then re-estimates covariance and refits the nonlinear mass for every resample. It is therefore sensitive to model misspecification and small-sample covariance estimation. The rho=0.8 generator is a limited time-correlation shift; it does not reproduce arbitrary lattice autocorrelation or physical correlator covariance.",
        "",
        "Do not use this comparison to select shrinkage or claim universal p-value calibration. A difference from chi-square supports further model-specific calibration only if it changes the gate decision; otherwise prioritize the independent physical anchor. Raw outer outcomes, bootstrap exceedance counts, failures, seeds, frozen source/protocol hashes, and artifact hashes are retained beside this report.",
        "",
        "Verify with `python -B -m tasks.pion_projection.certificate_subgate_bootstrap --verify`.",
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
    raw = json.loads((OUT / "raw_outcomes.json").read_text())
    if len(summary["cells"]) != len(BLOCKS) * len(TIME_RHOS):
        raise RuntimeError("cell count mismatch")
    for cell in summary["cells"]:
        key = f"rho_{cell['time_rho']}_blocks_{cell['blocks']}"
        rows = raw[key]
        if len(rows) != N_OUTER:
            raise RuntimeError(f"outer row count mismatch: {key}")
        valid = [r for r in rows if r["status"] == "VALID"]
        dchi = cell["nominal_chi2"]
        dboot = cell["conditional_parametric_bootstrap"]
        if len(valid) != dchi["n_valid_observed"] or len(valid) != dboot["n_valid_observed"]:
            raise RuntimeError(f"valid count mismatch: {key}")
        if sum(r["p_chi2"] < ALPHA for r in valid) != dchi["reject"]:
            raise RuntimeError(f"chi-square rejection mismatch: {key}")
        if sum(r["p_bootstrap"] < ALPHA for r in valid) != dboot["reject"]:
            raise RuntimeError(f"bootstrap rejection mismatch: {key}")
        if any(r.get("n_boot_valid", 0) + r.get("n_boot_invalid", 0) != N_BOOT for r in valid):
            raise RuntimeError(f"bootstrap draw accounting mismatch: {key}")
    print(f"verified hashes, {len(summary['cells'])} cells, {N_OUTER} outer datasets x {N_BOOT} bootstrap draws/cell")


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
