"""Independent N=400/cell replication of the pion GEVP ground-mode grid."""
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

from .gevp_stats import bootstrap_gevp, summarise
from .statistics import bootstrap_indices, blocks
from .gevp_grid import world


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/pion_projection/gevp_ground_failure_expanded_20261120_v1"
NOISE = (0.01, 0.05)
GAP = (0.1, 0.5)
T0 = (1, 2)
CUTOFF = (1e-8, 1e-5)
N_DATASET = 400
N_BOOT = 200
NCFG = 120
BLOCK_LENGTH = 5
BASE_SEED = 2026112700
MASS = 1.0
RANK = 2
PLATEAU_OFFSET = (1, 2, 3)
SOURCE_FILES = (
    "tasks/pion_projection/gevp_ground_failure_expanded.py",
    "tasks/pion_projection/gevp_grid.py",
    "tasks/pion_projection/gevp_stats.py",
    "tasks/pion_projection/statistics.py",
)
OUTPUTS = ("raw_outcomes.json", "summary.json", "gevp_coverage_bias.png", "README.md")


def canonical(x: object) -> bytes:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_manifest() -> dict[str, str]:
    return {name: sha256(ROOT / name) for name in SOURCE_FILES}


def protocol() -> dict:
    return {
        "schema": "pion-gevp-ground-grid-independent-replication-v1",
        "classification": "synthetic CPU method replication; not ground-state/physical certification",
        "purpose": "Resolve the Monte Carlo uncertainty of the earlier 20-dataset/cell grid using independent dataset seeds and independent bootstrap-index seeds.",
        "factor_grid": {"noise": list(NOISE), "gap": list(GAP), "t0": list(T0), "cutoff": list(CUTOFF)},
        "n_independent_datasets_per_cell": N_DATASET,
        "n_bootstrap_draws_per_dataset": N_BOOT,
        "sample": {"ncfg": NCFG, "block_length": BLOCK_LENGTH, "n_blocks": NCFG // BLOCK_LENGTH},
        "truth_mass": MASS,
        "estimator": {"matrix_dimension": 2, "rank": RANK, "plateau_times": "t0 + offsets 1,2,3", "coverage_interval": "dataset point estimate +/- 1.96 times within-dataset bootstrap SD; whole-replica validity rule from gevp_stats.summarise"},
        "precision_target": "N=400 gives worst-case marginal binomial CP95 half-width approximately 0.05; no post-hoc top-up.",
        "seed": {"base": BASE_SEED, "rule": "SeedSequence([BASE_SEED, noise_index, gap_index, t0_index, cutoff_index, dataset_id, stream]); stream=0 generates configurations and stream=1 generates independent bootstrap indices."},
        "intervals": "Exact CP95 for dataset-level coverage and outer failure rates; percentile bootstrap CI95 over independent dataset IDs for mean bias.",
        "outputs": list(OUTPUTS),
        "output_directory": str(OUT.relative_to(ROOT)),
        "frozen_sources": list(SOURCE_FILES),
    }


def cp95(k: int, n: int) -> list[float]:
    if n <= 0:
        return [0.0, 1.0]
    return [0.0 if k == 0 else float(beta.ppf(.025, k, n-k+1)),
            1.0 if k == n else float(beta.ppf(.975, k+1, n-k))]


def bias_ci(values: np.ndarray, seed: int) -> list[float]:
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(values), size=(10000, len(values)))
    means = values[idx].mean(axis=1)
    return [float(np.quantile(means, .025)), float(np.quantile(means, .975))]


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
    if prereg["source_sha256"] != source_manifest():
        raise RuntimeError("source hash differs from preregistration")
    if prereg["protocol_sha256"] != hashlib.sha256(canonical(frozen)).hexdigest():
        raise RuntimeError("protocol hash differs from preregistration")
    if any((OUT / name).exists() for name in OUTPUTS):
        raise FileExistsError("final output exists; refusing overwrite")

    raw_rows = []
    summary_rows = []
    factor_indices = {"noise": {x: i for i, x in enumerate(NOISE)},
                      "gap": {x: i for i, x in enumerate(GAP)},
                      "t0": {x: i for i, x in enumerate(T0)},
                      "cutoff": {x: i for i, x in enumerate(CUTOFF)}}
    for noise in NOISE:
        for gap in GAP:
            for t0 in T0:
                for cutoff in CUTOFF:
                    i_noise, i_gap = factor_indices["noise"][noise], factor_indices["gap"][gap]
                    i_t0, i_cut = factor_indices["t0"][t0], factor_indices["cutoff"][cutoff]
                    cell_rows = []
                    fail_reasons: dict[str, int] = {}
                    estimates, ses, cover_flags = [], [], []
                    for dataset_id in range(N_DATASET):
                        rng_data = np.random.default_rng(np.random.SeedSequence(
                            [BASE_SEED, i_noise, i_gap, i_t0, i_cut, dataset_id, 0]))
                        rng_boot = np.random.default_rng(np.random.SeedSequence(
                            [BASE_SEED, i_noise, i_gap, i_t0, i_cut, dataset_id, 1]))
                        data = blocks(world(rng_data, NCFG, MASS, gap, noise), BLOCK_LENGTH)
                        mix = np.array([[1.0, 0.3], [0.3, 1.0]])
                        matrix = np.einsum("ab,nbt,cb->nact", mix, data, mix)
                        index = rng_boot.integers(0, len(data), size=(N_BOOT, len(data)))
                        times = tuple(t0 + offset for offset in PLATEAU_OFFSET)
                        energies, failures = bootstrap_gevp(matrix, index, t0=t0, times=times,
                                                           rank=RANK, cutoff=cutoff)
                        fit = summarise(energies, times)
                        for item in failures:
                            reason = item.get("reason", "unspecified")
                            fail_reasons[reason] = fail_reasons.get(reason, 0) + 1
                        ok = bool(np.isfinite(fit["energy"]) and np.isfinite(fit["se"]))
                        if ok:
                            bias = float(fit["energy"] - MASS)
                            covered = abs(bias) <= 1.96 * fit["se"]
                            estimates.append(float(fit["energy"]))
                            ses.append(float(fit["se"]))
                            cover_flags.append(int(covered))
                        else:
                            bias = None
                            covered = None
                        row = {"dataset_id": dataset_id, "noise": noise, "gap": gap,
                               "t0": t0, "cutoff": cutoff, "estimate": float(fit["energy"]) if ok else None,
                               "se": float(fit["se"]) if ok else None, "bias": bias,
                               "covered": covered, "outer_valid": ok,
                               "valid_bootstrap_replicas": int(fit["replicas"]),
                               "bootstrap_replicas_failed": int(fit["failures"]),
                               "bootstrap_local_failures": int(fit["local_failures"]),
                               "failure_reasons": [item.get("reason", "unspecified") for item in failures]}
                        cell_rows.append(row)
                        raw_rows.append(row)
                    valid = len(estimates)
                    n_cov = sum(cover_flags)
                    biases = np.asarray(estimates) - MASS
                    cell_summary = {
                        "noise": noise, "gap": gap, "t0": t0, "cutoff": cutoff,
                        "n_planned": N_DATASET, "n_valid": valid, "n_outer_failures": N_DATASET-valid,
                        "outer_failure_cp95": cp95(N_DATASET-valid, N_DATASET),
                        "n_covered": int(n_cov), "coverage": n_cov/valid if valid else None,
                        "coverage_cp95": cp95(n_cov, valid),
                        "bias_mean": float(biases.mean()) if valid else None,
                        "bias_dataset_bootstrap_ci95": bias_ci(biases, BASE_SEED+i_noise*100000+i_gap*10000+i_t0*1000+i_cut) if valid else None,
                        "mean_within_dataset_bootstrap_se": float(np.mean(ses)) if ses else None,
                        "failure_reasons": fail_reasons,
                        "n_bootstrap_draws_per_dataset": N_BOOT,
                    }
                    summary_rows.append(cell_summary)
                    print(f"noise={noise} gap={gap} t0={t0} cutoff={cutoff}: coverage={n_cov}/{valid}, failures={N_DATASET-valid}", flush=True)

    summary = {"schema": "pion-gevp-ground-grid-independent-replication-summary-v1",
               "classification": frozen["classification"],
               "protocol_sha256": prereg["protocol_sha256"], "source_sha256": prereg["source_sha256"],
               "n_cells": len(summary_rows), "n_datasets_per_cell": N_DATASET,
               "total_independent_datasets": len(summary_rows)*N_DATASET,
               "cells": summary_rows}
    (OUT / "raw_outcomes.json").write_text(json.dumps(raw_rows, indent=2, sort_keys=True) + "\n")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    write_figure(summary)
    (OUT / "README.md").write_text(render_readme(summary))
    prov = {"protocol_sha256": prereg["protocol_sha256"],
            "preregistered_source_sha256": prereg["source_sha256"],
            "current_source_sha256": source_manifest(),
            "planned_datasets": N_DATASET*len(summary_rows),
            "completed_datasets": len(raw_rows),
            "planned_bootstrap_draws": N_DATASET*N_BOOT*len(summary_rows),
            "artifact_sha256": {name: sha256(OUT/name) for name in OUTPUTS}}
    (OUT / "execution_provenance.json").write_text(json.dumps(prov, indent=2, sort_keys=True) + "\n")
    print("completed", OUT.relative_to(ROOT))


def write_figure(summary: dict) -> None:
    rows = summary["cells"]
    labels = [f"n{r['noise']}/g{r['gap']}/t{r['t0']}/c{r['cutoff']:.0e}" for r in rows]
    coverage = np.array([r["coverage"] for r in rows])
    lower = np.array([r["coverage_cp95"][0] for r in rows])
    upper = np.array([r["coverage_cp95"][1] for r in rows])
    bias = np.array([r["bias_mean"] for r in rows])
    bias_lo = np.array([r["bias_dataset_bootstrap_ci95"][0] for r in rows])
    bias_hi = np.array([r["bias_dataset_bootstrap_ci95"][1] for r in rows])
    fig, axes = plt.subplots(2, 1, figsize=(15, 9), sharex=True)
    x = np.arange(len(rows))
    axes[0].errorbar(x, coverage, yerr=[coverage-lower, upper-coverage], fmt="o", capsize=2, color="#4477AA")
    axes[0].axhline(.95, color="#CC6677", linestyle="--", label="nominal 95%")
    axes[0].set(ylabel="Empirical coverage", title="N=400 independent datasets/cell; exact CP95 for coverage")
    axes[0].set_ylim(-.01, 1.02)
    axes[0].legend()
    axes[1].errorbar(x, bias, yerr=[bias-bias_lo, bias_hi-bias], fmt="o", capsize=2, color="#228833")
    axes[1].axhline(0, color="black", linestyle="--")
    axes[1].set(ylabel="Mean energy bias", title="Dataset-bootstrap CI95; true ground-state energy = 1")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=65, ha="right", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "gevp_coverage_bias.png", dpi=160)
    plt.close(fig)


def render_readme(summary: dict) -> str:
    lines = [
        "# Independent expansion of the pion GEVP ground-mode grid",
        "",
        "This new independent-seed CPU replication expands the earlier 20-dataset/cell grid to 400 datasets/cell and uses independent bootstrap-index seeds per dataset. It estimates Monte Carlo uncertainty for the specified synthetic GEVP estimator; it is not physical ground-state certification.",
        "",
        "The 2x2 matrix, rank=2, 120 configurations blocked by 5, plateau times t0+1..t0+3, noise/gap/t0/cutoff grid, and whole-replica validity rule are held fixed. Each dataset uses 200 bootstrap draws. At N=400, the worst-case binomial CP95 half-width is approximately 0.05; no top-up is allowed.",
        "",
        "| Noise | Gap | t0 | Cutoff | Valid / planned | Coverage / CP95 | Mean bias / dataset-bootstrap CI95 | Mean within-dataset bootstrap SE | Failure reasons |",
        "| ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | --- |",
    ]
    for r in summary["cells"]:
        cov_ci = r["coverage_cp95"]
        bci = r["bias_dataset_bootstrap_ci95"]
        lines.append(f"| {r['noise']} | {r['gap']} | {r['t0']} | {r['cutoff']:.0e} | {r['n_valid']}/{r['n_planned']} | {r['coverage']:.3f} [{cov_ci[0]:.3f}, {cov_ci[1]:.3f}] | {r['bias_mean']:.5f} [{bci[0]:.5f}, {bci[1]:.5f}] | {r['mean_within_dataset_bootstrap_se']:.5f} | `{json.dumps(r['failure_reasons'], sort_keys=True)}` |")
    lines += [
        "",
        "![Expanded GEVP coverage and bias](gevp_coverage_bias.png)",
        "",
        "## Interpretation boundary",
        "",
        "Coverage is the frequency with which the estimator's within-dataset bootstrap normal interval contains the known E0. Independent outer datasets define the MC uncertainty. Bias intervals describe the mean estimator bias, not a physical systematic-error budget. Failures and local bootstrap failures remain reported. Any near-zero coverage reproduces a defect of this synthetic estimator under the declared generator; it does not establish the failure rate for physical correlators or a corrected GEVP method.",
        "",
        "The raw dataset-level estimates, standard errors, coverage indicators, failure counts/reasons, seed rules, protocol/source hashes, and artifact hashes are stored in this directory. Verify with `python -B -m tasks.pion_projection.gevp_ground_failure_expanded --verify`.",
    ]
    return "\n".join(lines) + "\n"


def verify() -> None:
    frozen = json.loads((OUT/"protocol.json").read_text())
    prereg = json.loads((OUT/"preregistration.json").read_text())
    if hashlib.sha256(canonical(frozen)).hexdigest() != prereg["protocol_sha256"]:
        raise RuntimeError("protocol hash mismatch")
    if source_manifest() != prereg["source_sha256"]:
        raise RuntimeError("source hash mismatch")
    prov = json.loads((OUT/"execution_provenance.json").read_text())
    if prov["current_source_sha256"] != source_manifest():
        raise RuntimeError("execution source hash mismatch")
    for name, digest in prov["artifact_sha256"].items():
        if sha256(OUT/name) != digest:
            raise RuntimeError(f"artifact hash mismatch: {name}")
    raw = json.loads((OUT/"raw_outcomes.json").read_text())
    summary = json.loads((OUT/"summary.json").read_text())
    if len(raw) != N_DATASET*len(NOISE)*len(GAP)*len(T0)*len(CUTOFF):
        raise RuntimeError("raw dataset count mismatch")
    for cell in summary["cells"]:
        items = [r for r in raw if r["noise"] == cell["noise"] and r["gap"] == cell["gap"] and r["t0"] == cell["t0"] and r["cutoff"] == cell["cutoff"]]
        valid = [r for r in items if r["outer_valid"]]
        if len(items) != N_DATASET or len(valid) != cell["n_valid"]:
            raise RuntimeError("cell row count mismatch")
        covered = sum(bool(r["covered"]) for r in valid)
        if covered != cell["n_covered"]:
            raise RuntimeError("coverage count mismatch")
    print(f"verified hashes, {len(summary['cells'])} cells x {N_DATASET} datasets, {N_BOOT} bootstraps/dataset")


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
