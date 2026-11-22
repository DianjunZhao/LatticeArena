"""Pre-registered CPU calibration of the pion chi-square reference subgate.

This extends the small C2 smoke in certificate_calibration.py without modifying
or reusing its saved datasets. It estimates only the declared synthetic gate
size/power and preserves per-dataset p-values and failures.
"""
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
from .certificate_calibration import world, world_ground_weak
from .gate import fit_reference_gate
from .statistics import blocks, fold


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/pion_projection/certificate_subgate_mc_20261120_v1"
SCRIPT = Path(__file__).resolve()
N_DATASET = 1000
ALPHA = 0.05
BLOCKS = (6, 12, 24)
SCENARIOS = ("ground_state_null", "single_cosh_misspecified", "pure_excited_wrong_state")
BASE_SEED = 2026112200
SOURCE_FILES = (
    "tasks/pion_projection/certificate_subgate_mc.py",
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
    alpha = DATA_PROTOCOL["alpha"]
    assert alpha == 0.2  # kernel smear coefficient; the gate threshold is frozen separately below.
    return {
        "schema": "pion-chi2-subgate-mc-v1",
        "purpose": "Estimate empirical rejection/pass rates of the production chi-square reference subgate under three declared synthetic worlds.",
        "scope": "synthetic CPU method calibration only; not physical coverage or complete reference-gate validation",
        "unit": "one independently generated development dataset",
        "n_independent_datasets_per_cell": N_DATASET,
        "blocks_per_dataset": list(BLOCKS),
        "block_length_configurations": DATA_PROTOCOL["block_length"],
        "gate_threshold": ALPHA,
        "decision_rule": "production fit_reference_gate p_value < 0.05 is REJECT; p_value >= 0.05 is PASS; exception or non-finite p_value is INVALID and retained",
        "primary_precision_target": "For a correctly specified null at nominal rejection probability 0.05, n=1000 gives exact two-sided CP95 half-width 0.0141 at the planned count k=50; target <=0.015.",
        "confidence_intervals": "exact two-sided 95% Clopper-Pearson intervals; unconditional denominator is all 1000 planned datasets; conditional rates also use valid p-values only",
        "scenarios": {
            "ground_state_null": "same generator as C2 no-improvement control; reference channels have no excited-state contamination and baseline/candidate channels share contamination 0.5",
            "single_cosh_misspecified": "same generator as C2 misspecified-reference control; frozen reference channels contain excited-state contamination 0.5",
            "pure_excited_wrong_state": "same pure-E1 generator as C2 wrong-state control; ground-state amplitude is zero and a single-cosh fit may pass at E1",
        },
        "seed": {
            "base": BASE_SEED,
            "rule": "seed = base + 1000*scenario_index + blocks_per_dataset; each cell uses an independent NumPy Generator",
            "development_smoke_seed": 987654321,
            "development_smoke_not_included": True,
        },
        "frozen_sources": list(SOURCE_FILES),
        "output": str(OUT.relative_to(ROOT)),
        "outputs": ["raw_outcomes.json", "summary.json", "subgate_calibration_diagnostic.png", "README.md", "execution_provenance.json"],
    }


def cp95(k: int, n: int) -> list[float]:
    if n <= 0:
        return [0.0, 1.0]
    lo = 0.0 if k == 0 else float(beta.ppf(0.025, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(0.975, k + 1, n - k))
    return [lo, hi]


def contamination_for(scenario: str) -> np.ndarray:
    c = np.zeros(7)
    if scenario == "ground_state_null":
        c[1] = c[2] = 0.5
    elif scenario == "single_cosh_misspecified":
        c[[0, 3, 4, 1, 2]] = 0.5
    elif scenario != "pure_excited_wrong_state":
        raise ValueError(f"unknown scenario: {scenario}")
    return c


def one_dataset(scenario: str, n_blocks: int, rng: np.random.Generator) -> dict:
    ncfg = n_blocks * DATA_PROTOCOL["block_length"]
    try:
        if scenario == "pure_excited_wrong_state":
            raw = world_ground_weak(rng, ncfg)
        else:
            raw = fold(world(rng, ncfg, contamination_for(scenario)))
        dev = blocks(raw, DATA_PROTOCOL["block_length"])
        _, mass, cost, dof, p_value = fit_reference_gate(dev, DATA_PROTOCOL, "single")
        if not np.isfinite(p_value):
            return {"status": "INVALID", "reason": "nonfinite_p_value", "p_value": None}
        status = "REJECT" if p_value < ALPHA else "PASS"
        return {"status": status, "p_value": float(p_value), "mass": float(mass),
                "chi2": float(cost), "dof": int(dof)}
    except Exception as exc:  # retain failures instead of silently dropping a dataset
        return {"status": "INVALID", "reason": f"{type(exc).__name__}: {exc}", "p_value": None}


def summarize_cell(scenario: str, n_blocks: int, rows: list[dict]) -> dict:
    n = len(rows)
    rejected = sum(row["status"] == "REJECT" for row in rows)
    passed = sum(row["status"] == "PASS" for row in rows)
    invalid = n - rejected - passed
    valid = rejected + passed
    return {
        "scenario": scenario,
        "blocks_per_dataset": n_blocks,
        "n_planned": n,
        "n_valid_p_values": valid,
        "n_rejected": rejected,
        "n_passed": passed,
        "n_invalid": invalid,
        "reject_rate_all": rejected / n,
        "reject_rate_all_cp95": cp95(rejected, n),
        "reject_rate_valid": rejected / valid if valid else None,
        "reject_rate_valid_cp95": cp95(rejected, valid),
        "pass_rate_all": passed / n,
        "pass_rate_all_cp95": cp95(passed, n),
        "invalid_rate": invalid / n,
        "invalid_rate_cp95": cp95(invalid, n),
        "median_p_value": float(np.median([r["p_value"] for r in rows if r["p_value"] is not None])) if valid else None,
    }


def execute() -> None:
    frozen = json.loads((OUT / "protocol.json").read_text())
    registration = json.loads((OUT / "preregistration.json").read_text())
    if registration["source_sha256"] != source_manifest():
        raise RuntimeError("source hash differs from preregistration")
    if registration["protocol_sha256"] != hashlib.sha256(canonical(frozen)).hexdigest():
        raise RuntimeError("protocol hash differs from preregistration")
    if any((OUT / name).exists() for name in frozen["outputs"]):
        raise FileExistsError("final outputs already exist; refusing overwrite")

    all_rows: dict[str, list[dict]] = {}
    cells: list[dict] = []
    for sidx, scenario in enumerate(SCENARIOS):
        for n_blocks in BLOCKS:
            seed = BASE_SEED + 1000 * sidx + n_blocks
            rng = np.random.default_rng(seed)
            rows = [one_dataset(scenario, n_blocks, rng) for _ in range(N_DATASET)]
            key = f"{scenario}/blocks_{n_blocks}"
            all_rows[key] = rows
            cells.append({**summarize_cell(scenario, n_blocks, rows), "seed": seed})
            print(key, {k: cells[-1][k] for k in ("n_rejected", "n_passed", "n_invalid", "reject_rate_all")})

    summary = {
        "schema": "pion-chi2-subgate-summary-v1",
        "classification": "synthetic CPU calibration; not physical validation",
        "protocol_sha256": registration["protocol_sha256"],
        "source_sha256": registration["source_sha256"],
        "n_independent_datasets_per_cell": N_DATASET,
        "cells": cells,
    }
    (OUT / "raw_outcomes.json").write_text(json.dumps(all_rows, indent=2, sort_keys=True) + "\n")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    write_figure(OUT, summary, all_rows)
    (OUT / "README.md").write_text(render_readme(summary))
    artifacts = ("raw_outcomes.json", "summary.json", "subgate_calibration_diagnostic.png", "README.md")
    provenance = {
        "protocol_sha256": registration["protocol_sha256"],
        "preregistered_source_sha256": registration["source_sha256"],
        "current_source_sha256": source_manifest(),
        "planned_cells": len(cells),
        "planned_datasets": N_DATASET * len(cells),
        "completed_datasets": sum(len(v) for v in all_rows.values()),
        "statuses": {status: sum(r["status"] == status for rows in all_rows.values() for r in rows)
                     for status in ("PASS", "REJECT", "INVALID")},
        "artifact_sha256": {name: sha256(OUT / name) for name in artifacts},
    }
    (OUT / "execution_provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    print("completed", OUT.relative_to(ROOT))


def write_figure(out: Path, summary: dict, raw: dict) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.7))
    null_cells = [c for c in summary["cells"] if c["scenario"] == "ground_state_null"]
    colors = {6: "#4477AA", 12: "#EE6677", 24: "#228833"}
    for cell in null_cells:
        pvals = [r["p_value"] for r in raw[f"ground_state_null/blocks_{cell['blocks_per_dataset']}"]
                 if r["p_value"] is not None]
        axes[0].hist(pvals, bins=np.linspace(0, 1, 11), density=True, histtype="step", linewidth=2,
                     color=colors[cell["blocks_per_dataset"]], label=f"{cell['blocks_per_dataset']} blocks")
    axes[0].axhline(1.0, color="black", ls="--", lw=1, label="Uniform reference")
    axes[0].set(title="Null p-value calibration", xlabel="Reference-gate p-value", ylabel="Density")
    axes[0].legend(frameon=False)

    x = np.arange(len(summary["cells"]))
    labels = [f"{c['scenario'].replace('_', '\\n')}\nB={c['blocks_per_dataset']}" for c in summary["cells"]]
    rates = np.array([c["reject_rate_all"] for c in summary["cells"]])
    lo = np.array([c["reject_rate_all_cp95"][0] for c in summary["cells"]])
    hi = np.array([c["reject_rate_all_cp95"][1] for c in summary["cells"]])
    axes[1].errorbar(x, rates, yerr=[rates - lo, hi - rates], fmt="o", color="#4477AA", capsize=3)
    axes[1].axhline(ALPHA, color="black", ls="--", lw=1, label="Nominal 5%")
    axes[1].set(title="Gate rejection rate", ylabel="Fraction of all planned datasets", xticks=x, xticklabels=labels)
    axes[1].tick_params(axis="x", labelsize=7)
    axes[1].legend(frameon=False)

    wrong = [c for c in summary["cells"] if c["scenario"] == "pure_excited_wrong_state"]
    wx = [c["blocks_per_dataset"] for c in wrong]
    wp = np.array([c["pass_rate_all"] for c in wrong])
    wlo = np.array([c["pass_rate_all_cp95"][0] for c in wrong])
    whi = np.array([c["pass_rate_all_cp95"][1] for c in wrong])
    axes[2].errorbar(wx, wp, yerr=[wp - wlo, whi - wp], fmt="o-", color="#AA3377", capsize=3)
    axes[2].set(title="Pure-E1 gate acceptance", xlabel="Independent blocks per dataset", ylabel="Acceptance fraction")
    axes[2].set_ylim(0, 1.02)
    fig.suptitle("Pion χ² reference subgate: size, misspecification, and state ambiguity")
    fig.tight_layout()
    fig.savefig(out / "subgate_calibration_diagnostic.png", dpi=160)
    plt.close(fig)


def render_readme(summary: dict) -> str:
    lines = [
        "# Pion χ² reference-subgate CPU calibration",
        "",
        "This independent run expands the C2 smoke only for the 5% χ² reference subgate. It does not run the full certificate and does not establish physical coverage.",
        "",
        "## Frozen design and outcomes",
        "",
        "Each of the nine scenario × block cells has 1000 independent synthetic development datasets. A failed/non-finite fit remains in the denominator as INVALID; valid-p conditional rates are also reported. Intervals are exact two-sided 95% Clopper–Pearson intervals.",
        "",
        "| Scenario | Blocks | Reject | Pass | Invalid | Reject rate over planned N (CP95) | Pass rate over planned N (CP95) |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for c in summary["cells"]:
        lo, hi = c["reject_rate_all_cp95"]
        plo, phi = c["pass_rate_all_cp95"]
        lines.append(f"| {c['scenario']} | {c['blocks_per_dataset']} | {c['n_rejected']} | {c['n_passed']} | {c['n_invalid']} | {c['reject_rate_all']:.3f} [{lo:.3f}, {hi:.3f}] | {c['pass_rate_all']:.3f} [{plo:.3f}, {phi:.3f}] |")
    lines += [
        "",
        "![Subgate calibration and structural negative control](subgate_calibration_diagnostic.png)",
        "",
        "## Interpretation and limits",
        "",
        "The correctly specified ground-state null estimates rejection calibration for this generator and the frozen covariance/fit settings. The misspecified single-cosh scenario probes rejection sensitivity. The pure-E1 scenario checks state identifiability: a good single-cosh fit can accept the wrong energy. These are synthetic results; none validates a production anchor or the complete reference gate.",
        "",
        "Do not combine this independent run with `certificate_calibration_v1`, full-gate amendment02/03, or family-wise v1–v3. See `protocol.json`, `preregistration.json`, `raw_outcomes.json`, and `execution_provenance.json` for the frozen design, per-dataset records, seeds, hashes, and artifact digests.",
        "",
        "Reproduce with `python -B -m tasks.pion_projection.certificate_subgate_mc --run`; verify with `python -B -m tasks.pion_projection.certificate_subgate_mc --verify`.",
    ]
    return "\n".join(lines) + "\n"


def preregister() -> None:
    if OUT.exists() and any(OUT.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output directory: {OUT}")
    OUT.mkdir(parents=True, exist_ok=True)
    frozen = protocol()
    proto_hash = hashlib.sha256(canonical(frozen)).hexdigest()
    sources = source_manifest()
    (OUT / "protocol.json").write_text(json.dumps(frozen, indent=2, sort_keys=True) + "\n")
    (OUT / "preregistration.json").write_text(json.dumps({
        "protocol_sha256": proto_hash,
        "source_sha256": sources,
        "registered_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "FROZEN_BEFORE_FULL_SIMULATION",
    }, indent=2, sort_keys=True) + "\n")
    print("preregistered", OUT.relative_to(ROOT), proto_hash)


def verify() -> None:
    registration = json.loads((OUT / "preregistration.json").read_text())
    frozen = json.loads((OUT / "protocol.json").read_text())
    if registration["protocol_sha256"] != hashlib.sha256(canonical(frozen)).hexdigest():
        raise SystemExit("protocol hash mismatch")
    if registration["source_sha256"] != source_manifest():
        raise SystemExit("source hash mismatch")
    summary = json.loads((OUT / "summary.json").read_text())
    raw = json.loads((OUT / "raw_outcomes.json").read_text())
    if len(summary["cells"]) != 9 or len(raw) != 9:
        raise SystemExit("cell count mismatch")
    if any(len(rows) != N_DATASET for rows in raw.values()):
        raise SystemExit("dataset denominator mismatch")
    provenance = json.loads((OUT / "execution_provenance.json").read_text())
    for name, digest in provenance["artifact_sha256"].items():
        if sha256(OUT / name) != digest:
            raise SystemExit(f"output hash mismatch: {name}")
    if provenance["completed_datasets"] != N_DATASET * 9:
        raise SystemExit("completion count mismatch")
    print("verified source/protocol/output hashes and 9 cells x 1000 independent datasets")


def smoke() -> None:
    rows = []
    for sidx, scenario in enumerate(SCENARIOS):
        for n_blocks in BLOCKS:
            rng = np.random.default_rng(987654321 + 100 * sidx + n_blocks)
            rows.append(one_dataset(scenario, n_blocks, rng)["status"])
    print("smoke cells:", len(rows), "invalid:", rows.count("INVALID"))


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
        execute()
    else:
        verify()


if __name__ == "__main__":
    main()
