"""Paired shrinkage sensitivity of the pion chi-square subgate under null."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import beta

from .certificate_calibration import PROTOCOL as DATA_PROTOCOL
from .certificate_calibration import world
from .gate import fit_reference_gate
from .statistics import blocks, fold


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/pion_projection/certificate_subgate_shrinkage_20261120_v1"
N_DATASET = 1000
ALPHA = 0.05
BLOCKS = (6, 12, 24)
SHRINKAGES = (0.0, 0.25, 0.5)
BASE_SEED = 2026112300
BOOTSTRAP_SEED = 2026112399
BOOTSTRAP_DRAWS = 20000
SOURCE_FILES = (
    "tasks/pion_projection/certificate_subgate_shrinkage.py",
    "tasks/pion_projection/certificate_calibration.py",
    "tasks/pion_projection/gate.py",
    "tasks/pion_projection/reference.py",
    "tasks/pion_projection/statistics.py",
    "results/pion_projection/s16t16_v1/development_provenance.json",
)


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_manifest() -> dict[str, str]:
    return {name: sha256(ROOT / name) for name in SOURCE_FILES}


def protocol() -> dict:
    return {
        "schema": "pion-chi2-subgate-shrinkage-v1",
        "purpose": "Isolate the effect of covariance shrinkage on the empirical null rejection rate of the frozen chi-square subgate.",
        "scope": "synthetic CPU sensitivity study; not physical validation or a complete certificate test",
        "unit": "one independently generated null development dataset; all shrinkage levels are paired on the same dataset",
        "n_independent_datasets_per_block_count": N_DATASET,
        "blocks_per_dataset": list(BLOCKS),
        "block_length_configurations": DATA_PROTOCOL["block_length"],
        "shrinkage_values": list(SHRINKAGES),
        "production_shrinkage": DATA_PROTOCOL["covariance_shrinkage"],
        "gate_threshold": ALPHA,
        "decision_rule": "fit_reference_gate p_value < 0.05 is REJECT; p_value >= 0.05 is PASS; exception/nonfinite is INVALID and retained",
        "paired_contrast": "rejection indicator at shrinkage s minus rejection indicator at production shrinkage 0.25, denominator is all planned datasets, invalid counts are separately reported",
        "intervals": "exact two-sided 95% Clopper-Pearson marginal intervals; dataset-paired bootstrap for six shrinkage contrasts with 95% family coverage via Bonferroni (99.1667% pointwise percentile intervals), 20000 draws",
        "primary_precision_target": "n=1000 per block count; at nominal rejection 0.05 the exact CP95 half-width is 0.0140 at expected k=50",
        "world": "C2 ground_state_null generator: reference channels have no excited-state contamination; baseline/candidate channels share contamination 0.5; block length and all other protocol settings are frozen",
        "seed": {
            "base": BASE_SEED,
            "rule": "seed = base + blocks_per_dataset; each block count has a separate Generator; shrinkage levels share generated datasets",
            "paired_bootstrap_seed": BOOTSTRAP_SEED,
            "paired_bootstrap_draws": BOOTSTRAP_DRAWS,
        },
        "frozen_sources": list(SOURCE_FILES),
        "output": str(OUT.relative_to(ROOT)),
        "outputs": ["raw_outcomes.json", "summary.json", "shrinkage_sensitivity.png", "README.md", "execution_provenance.json"],
    }


def cp95(k: int, n: int) -> list[float]:
    if n <= 0:
        return [0.0, 1.0]
    lo = 0.0 if k == 0 else float(beta.ppf(0.025, k, n-k+1))
    hi = 1.0 if k == n else float(beta.ppf(0.975, k+1, n-k))
    return [lo, hi]


def paired_ci(values: np.ndarray, rng: np.random.Generator) -> list[float]:
    n = len(values)
    samples = rng.integers(0, n, size=(BOOTSTRAP_DRAWS, n))
    means = values[samples].mean(axis=1)
    tail = 0.05 / (2 * 6)  # six predeclared contrasts; Bonferroni family coverage >= 95%.
    return [float(np.quantile(means, tail)), float(np.quantile(means, 1-tail))]


def main_run() -> None:
    frozen = json.loads((OUT / "protocol.json").read_text())
    registration = json.loads((OUT / "preregistration.json").read_text())
    if registration["source_sha256"] != source_manifest():
        raise RuntimeError("source hash differs from preregistration")
    if registration["protocol_sha256"] != hashlib.sha256(canonical(frozen)).hexdigest():
        raise RuntimeError("protocol hash differs from preregistration")
    if any((OUT / name).exists() for name in frozen["outputs"]):
        raise FileExistsError("final outputs already exist; refusing overwrite")

    contamination = np.zeros(7)
    contamination[1] = contamination[2] = 0.5
    raw: dict[str, list[dict]] = {}
    cells = []
    for n_blocks in BLOCKS:
        rng = np.random.default_rng(BASE_SEED + n_blocks)
        ncfg = n_blocks * DATA_PROTOCOL["block_length"]
        outcomes = []
        config = {**DATA_PROTOCOL, "covariance_shrinkage": DATA_PROTOCOL["covariance_shrinkage"]}
        for dataset_id in range(N_DATASET):
            dev = blocks(fold(world(rng, ncfg, contamination)), DATA_PROTOCOL["block_length"])
            row = {"dataset_id": dataset_id, "shrinkage": {}}
            for shrinkage in SHRINKAGES:
                cfg = {**config, "covariance_shrinkage": shrinkage}
                try:
                    _, mass, cost, dof, p_value = fit_reference_gate(dev, cfg, "single")
                    if not np.isfinite(p_value):
                        row["shrinkage"][str(shrinkage)] = {"status": "INVALID", "reason": "nonfinite_p_value"}
                    else:
                        row["shrinkage"][str(shrinkage)] = {
                            "status": "REJECT" if p_value < ALPHA else "PASS",
                            "p_value": float(p_value), "mass": float(mass),
                            "chi2": float(cost), "dof": int(dof),
                        }
                except Exception as exc:
                    row["shrinkage"][str(shrinkage)] = {
                        "status": "INVALID", "reason": f"{type(exc).__name__}: {exc}"
                    }
            outcomes.append(row)
        key = f"blocks_{n_blocks}"
        raw[key] = outcomes
        by_shrink = {}
        flags = {}
        for shrinkage in SHRINKAGES:
            s = str(shrinkage)
            flags[s] = np.array([r["shrinkage"][s]["status"] == "REJECT" for r in outcomes], dtype=int)
            rejected = int(flags[s].sum())
            invalid = sum(r["shrinkage"][s]["status"] == "INVALID" for r in outcomes)
            valid = N_DATASET - invalid
            by_shrink[s] = {
                "n_planned": N_DATASET,
                "n_rejected": rejected,
                "n_passed": N_DATASET - rejected - invalid,
                "n_invalid": invalid,
                "reject_rate_all": rejected / N_DATASET,
                "reject_rate_all_cp95": cp95(rejected, N_DATASET),
                "reject_rate_valid": rejected / valid if valid else None,
                "reject_rate_valid_cp95": cp95(rejected, valid),
            }
        contrasts = {}
        ref = flags["0.25"]
        boot_rng = np.random.default_rng(BOOTSTRAP_SEED + n_blocks)
        for shrinkage in (0.0, 0.5):
            s = str(shrinkage)
            diff = flags[s] - ref
            contrasts[s] = {
                "versus_production_shrinkage": 0.25,
                "mean_rejection_rate_difference": float(diff.mean()),
                "dataset_pairs": N_DATASET,
                "familywise_95_bootstrap_ci": paired_ci(diff, boot_rng),
                "alt_only_reject": int(np.sum((flags[s] == 1) & (ref == 0))),
                "production_only_reject": int(np.sum((flags[s] == 0) & (ref == 1))),
            }
        cells.append({"blocks_per_dataset": n_blocks, "seed": BASE_SEED+n_blocks,
                      "by_shrinkage": by_shrink, "paired_contrasts": contrasts})
        print(key, {s: by_shrink[s]["n_rejected"] for s in by_shrink})

    summary = {
        "schema": "pion-chi2-subgate-shrinkage-summary-v1",
        "classification": "paired synthetic CPU sensitivity; not physical validation",
        "protocol_sha256": registration["protocol_sha256"],
        "source_sha256": registration["source_sha256"],
        "n_independent_datasets_per_block_count": N_DATASET,
        "cells": cells,
    }
    (OUT / "raw_outcomes.json").write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    write_figure(summary, raw)
    (OUT / "README.md").write_text(render_readme(summary))
    artifacts = ("raw_outcomes.json", "summary.json", "shrinkage_sensitivity.png", "README.md")
    provenance = {
        "protocol_sha256": registration["protocol_sha256"],
        "preregistered_source_sha256": registration["source_sha256"],
        "current_source_sha256": source_manifest(),
        "planned_datasets": N_DATASET * len(BLOCKS),
        "completed_datasets": sum(len(v) for v in raw.values()),
        "artifact_sha256": {name: sha256(OUT / name) for name in artifacts},
    }
    (OUT / "execution_provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    print("completed", OUT.relative_to(ROOT))


def write_figure(summary: dict, raw: dict) -> None:
    colors = {"0.0": "#4477AA", "0.25": "#CC6677", "0.5": "#228833"}
    labels = {"0.0": "No shrinkage", "0.25": "Production 0.25", "0.5": "Shrinkage 0.5"}
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    x = np.array(BLOCKS)
    for s in ("0.0", "0.25", "0.5"):
        cells = [next(c for c in summary["cells"] if c["blocks_per_dataset"] == b) for b in BLOCKS]
        y = np.array([c["by_shrinkage"][s]["reject_rate_all"] for c in cells])
        lo = np.array([c["by_shrinkage"][s]["reject_rate_all_cp95"][0] for c in cells])
        hi = np.array([c["by_shrinkage"][s]["reject_rate_all_cp95"][1] for c in cells])
        axes[0].errorbar(x, y, yerr=[y-lo, hi-y], fmt="o-", color=colors[s], capsize=3, label=labels[s])
    axes[0].axhline(ALPHA, color="black", ls="--", lw=1, label="Nominal 5%")
    axes[0].set(title="Null rejection vs block count", xlabel="Independent blocks", ylabel="Rejection rate", xticks=x)
    axes[0].legend(frameon=False, fontsize=8)

    offsets = {"0.0": -0.16, "0.5": 0.16}
    for s in ("0.0", "0.5"):
        y, lo, hi = [], [], []
        for c in summary["cells"]:
            contrast = c["paired_contrasts"][s]
            y.append(contrast["mean_rejection_rate_difference"])
            lo.append(contrast["familywise_95_bootstrap_ci"][0])
            hi.append(contrast["familywise_95_bootstrap_ci"][1])
        axes[1].errorbar(x + offsets[s], y, yerr=[np.array(y)-lo, np.array(hi)-y], fmt="o",
                         color=colors[s], capsize=3, label=f"{labels[s]} minus 0.25")
    axes[1].axhline(0, color="black", ls="--", lw=1)
    axes[1].set(title="Paired change in rejection rate", xlabel="Independent blocks", ylabel="Rate difference", xticks=x)
    axes[1].legend(frameon=False, fontsize=8)

    for b, color, label in ((6, "#4477AA", "6 blocks"), (12, "#CC6677", "12 blocks"), (24, "#228833", "24 blocks")):
        pvals = [r["shrinkage"]["0.25"]["p_value"] for r in raw[f"blocks_{b}"]
                 if r["shrinkage"]["0.25"]["p_value"] is not None]
        axes[2].hist(pvals, bins=np.linspace(0, 1, 11), density=True, histtype="step", linewidth=2,
                     color=color, label=label)
    axes[2].axhline(1, color="black", ls="--", lw=1, label="Uniform reference")
    axes[2].set(title="Production-shrinkage null p-values", xlabel="p-value", ylabel="Density")
    axes[2].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "shrinkage_sensitivity.png", dpi=160)
    plt.close(fig)


def render_readme(summary: dict) -> str:
    lines = [
        "# Paired covariance-shrinkage sensitivity of the pion χ² subgate",
        "",
        "This pre-registered follow-up uses 1000 independent ground-state-null datasets at each block count. Every dataset is fit under all three covariance shrinkage values, so the shrinkage comparison is paired. It isolates the subgate; it is not a full certificate or physical validation.",
        "",
        "## Marginal rejection rates",
        "",
        "| Blocks | Shrinkage | Reject | Invalid | Rejection rate (CP95) |",
        "| ---: | ---: | ---: | ---: | --- |",
    ]
    for c in summary["cells"]:
        for s in ("0.0", "0.25", "0.5"):
            x = c["by_shrinkage"][s]
            lo, hi = x["reject_rate_all_cp95"]
            lines.append(f"| {c['blocks_per_dataset']} | {s} | {x['n_rejected']}/{x['n_planned']} | {x['n_invalid']} | {x['reject_rate_all']:.3f} [{lo:.3f}, {hi:.3f}] |")
    lines += ["", "## Paired shrinkage contrasts", "", "Positive means the alternative shrinkage rejects more null datasets than production shrinkage 0.25. The six intervals have 95% family coverage by the predeclared Bonferroni adjustment.", "", "| Blocks | Alternative | Difference | Familywise bootstrap CI95 | Alt-only / production-only rejects |", "| ---: | ---: | ---: | --- | ---: |"]
    for c in summary["cells"]:
        for s in ("0.0", "0.5"):
            x = c["paired_contrasts"][s]
            lo, hi = x["familywise_95_bootstrap_ci"]
            lines.append(f"| {c['blocks_per_dataset']} | {s} | {x['mean_rejection_rate_difference']:.3f} | [{lo:.3f}, {hi:.3f}] | {x['alt_only_reject']} / {x['production_only_reject']} |")
    lines += [
        "",
        "![Covariance-shrinkage sensitivity](shrinkage_sensitivity.png)",
        "",
        "## Interpretation",
        "",
        "Read the paired contrasts together with invalid counts and marginal intervals. This study asks whether the fixed covariance shrinkage setting explains the block-count size distortion observed in certificate_subgate_mc_20261120_v1. It does not select a replacement shrinkage or imply chi-square calibration outside this generator.",
        "",
        "The per-dataset p-values, fitted masses, costs, statuses, seeds, frozen protocol, and hashes are stored beside this report. Reproduce with `python -B -m tasks.pion_projection.certificate_subgate_shrinkage --run`; verify with `python -B -m tasks.pion_projection.certificate_subgate_shrinkage --verify`.",
    ]
    return "\n".join(lines) + "\n"


def preregister() -> None:
    if OUT.exists() and any(OUT.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output directory: {OUT}")
    OUT.mkdir(parents=True, exist_ok=True)
    frozen = protocol()
    digest = hashlib.sha256(canonical(frozen)).hexdigest()
    (OUT / "protocol.json").write_text(json.dumps(frozen, indent=2, sort_keys=True) + "\n")
    (OUT / "preregistration.json").write_text(json.dumps({
        "protocol_sha256": digest,
        "source_sha256": source_manifest(),
        "registered_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "FROZEN_BEFORE_FULL_SIMULATION",
    }, indent=2, sort_keys=True) + "\n")
    print("preregistered", OUT.relative_to(ROOT), digest)


def verify() -> None:
    registration = json.loads((OUT / "preregistration.json").read_text())
    frozen = json.loads((OUT / "protocol.json").read_text())
    if registration["protocol_sha256"] != hashlib.sha256(canonical(frozen)).hexdigest():
        raise SystemExit("protocol hash mismatch")
    if registration["source_sha256"] != source_manifest():
        raise SystemExit("source hash mismatch")
    summary = json.loads((OUT / "summary.json").read_text())
    raw = json.loads((OUT / "raw_outcomes.json").read_text())
    if len(summary["cells"]) != 3 or set(raw) != {f"blocks_{b}" for b in BLOCKS}:
        raise SystemExit("cell count mismatch")
    if any(len(rows) != N_DATASET for rows in raw.values()):
        raise SystemExit("dataset denominator mismatch")
    provenance = json.loads((OUT / "execution_provenance.json").read_text())
    for name, digest in provenance["artifact_sha256"].items():
        if sha256(OUT / name) != digest:
            raise SystemExit(f"output hash mismatch: {name}")
    print("verified source/protocol/output hashes and 3 paired cells x 1000 datasets")


def smoke() -> None:
    contam = np.zeros(7)
    contam[1] = contam[2] = 0.5
    for n_blocks in BLOCKS:
        rng = np.random.default_rng(987654321+n_blocks)
        dev = blocks(fold(world(rng, n_blocks*DATA_PROTOCOL["block_length"], contam)), DATA_PROTOCOL["block_length"])
        statuses = []
        for s in SHRINKAGES:
            cfg = {**DATA_PROTOCOL, "covariance_shrinkage": s}
            try:
                p = fit_reference_gate(dev, cfg, "single")[-1]
                statuses.append("REJECT" if p < ALPHA else "PASS")
            except Exception:
                statuses.append("INVALID")
        print(n_blocks, statuses)


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--smoke", action="store_true")
    group.add_argument("--preregister", action="store_true")
    group.add_argument("--run", action="store_true")
    group.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.smoke:
        smoke()
    elif args.preregister:
        preregister()
    elif args.run:
        main_run()
    else:
        verify()


if __name__ == "__main__":
    main()
