"""Independent N=400 expansion of the synthetic C2 J=2/K=2 family check.

The study repeats the original certificate_calibration.run_family estimand with
independent dataset seeds. Two-state design matrices are cached within each
dataset; the fit grid, linear solves, gate, bootstrap draws, and certificate
implementation are unchanged. A seed-matched parity smoke is available before
the frozen run.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import beta

from . import certificate_calibration as original
from .experiment import late_metric
from .reference import make_reference
from .reference_twostate import TwoStateFit
from .scoring import improvement_certificate
from .statistics import blocks, risk


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/pion_projection/certificate_family_expanded_20261120_v1"
N_DATASET = 400
OUTER = 40
INNER = 16
BASE_SEED = 2026112200
ALPHA = 0.05
FAMILY_SIZE_FOR_PRIMARY_RATES = 4
PARITY_SEED = 7654321
SOURCE_FILES = (
    "tasks/pion_projection/certificate_family_expanded.py",
    "tasks/pion_projection/certificate_calibration.py",
    "tasks/pion_projection/experiment.py",
    "tasks/pion_projection/gate.py",
    "tasks/pion_projection/reference.py",
    "tasks/pion_projection/reference_twostate.py",
    "tasks/pion_projection/scoring.py",
    "tasks/pion_projection/statistics.py",
    "core/comparator.py",
    "results/pion_projection/s16t16_gevp200/development_provenance.json",
)
OUTPUTS = ("raw_outcomes.json", "summary.json", "c2_family_diagnostics.png", "README.md")

_DESIGN_CACHE: dict[tuple[Any, ...], np.ndarray] = {}
_ORIGINAL_DESIGN = None


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_manifest() -> dict[str, str]:
    return {name: sha256(ROOT / name) for name in SOURCE_FILES}


def install_design_cache() -> None:
    """Cache only deterministic design matrices; preserve production arithmetic."""
    global _ORIGINAL_DESIGN
    if _ORIGINAL_DESIGN is not None:
        TwoStateFit.design = cached_design
        return
    _ORIGINAL_DESIGN = TwoStateFit.design
    TwoStateFit.design = cached_design


def cached_design(self, m0: float, m1: float) -> np.ndarray:
    key = (tuple(int(x) for x in self.window), self.nchan, self.ntime,
           int(self.p["geometry"][3]), float(m0), float(m1))
    matrix = _DESIGN_CACHE.get(key)
    if matrix is None:
        if _ORIGINAL_DESIGN is None:
            raise RuntimeError("design cache was not initialized")
        matrix = _ORIGINAL_DESIGN(self, m0, m1)
        _DESIGN_CACHE[key] = matrix
    return matrix


def protocol() -> dict[str, Any]:
    p = original.PROTOCOL
    return {
        "schema": "pion-c2-j2-k2-family-independent-expansion-v1",
        "classification": "synthetic CPU family-subgate calibration; not physical score validation",
        "purpose": "Estimate family false-certification, power, and gate abstention for the frozen synthetic J=2/K=2 certificate benchmark with independent outer datasets.",
        "n_independent_datasets": N_DATASET,
        "outer_draws_per_dataset": OUTER,
        "inner_mass_draws_per_outer_draw": INNER,
        "development_blocks": 24,
        "validation_blocks": 12,
        "block_length": p["block_length"],
        "family": {"candidate_ids": ["null", "better"], "accepted_models": ["single", "twostate"],
                   "family_alpha": ALPHA, "certificate_level": ALPHA / 4},
        "world": {
            "ground_energy": original.E0,
            "excited_energy": original.E1,
            "reference_channels": [0, 3, 4],
            "baseline_channel": 1,
            "null_candidate_channel": 2,
            "better_candidate_channel": 5,
            "reference_excited_contamination": 0.0,
            "baseline_and_null_contamination": 0.5,
            "better_contamination": 0.2,
            "measurement_noise": 0.02,
            "configuration_noise_sigma": 0.01,
            "time_noise_rho": 0.5,
        },
        "analysis": {
            "gate": "Use certificate_calibration.gate and model_gate; both accepted models must pass their chi-square gate, and the two-state fit must not be at a mass boundary.",
            "candidate_estimand": "Use certificate_calibration.run_family's conditional risk draws and improvement_certificate with one null and one known-better candidate across two accepted models.",
            "primary_rates": ["unconditional null certification / all planned datasets",
                              "conditional null certification / gate-valid datasets",
                              "conditional better-candidate power / gate-valid datasets",
                              "non-evaluable rate (abstain or invalid) / all planned datasets"],
            "confidence_intervals": "Exact two-sided Clopper-Pearson; familywise 95% intervals Bonferroni-adjusted over four primary rates; marginal intervals are also retained.",
            "no_top_up": True,
        },
        "precision_target": "N=400 gives worst-case marginal CP95 half-width about 0.049 for unconditional rates; conditional rates are reported with their actual valid denominator and marked INCONCLUSIVE if their marginal half-width exceeds 0.05. No post-hoc top-up.",
        "seeds": {"base": BASE_SEED, "rule": "dataset_id i uses numpy.default_rng(BASE_SEED+i); all 400 IDs are independent outer worlds and do not reuse the prior 8-dataset stream."},
        "fit_acceleration": {
            "method": "Cache deterministic TwoStateFit.design matrices within each dataset process.",
            "invariant": "No changes to mass grid, local coordinate search, covariance, normal equations, objective, gate, or bootstrap draw counts.",
            "parity_seed": PARITY_SEED,
            "parity_seed_excluded_from_main_run": True,
        },
        "frozen_fit_protocol": {key: p[key] for key in ("geometry", "block_length", "reference_basis",
                                                          "reference_windows", "reference_nominal_window",
                                                          "mass_bounds", "covariance_shrinkage")},
        "output_directory": str(OUT.relative_to(ROOT)),
        "outputs": list(OUTPUTS),
        "frozen_sources": list(SOURCE_FILES),
    }


def cp_interval(k: int, n: int, familywise: bool = False) -> list[float] | None:
    if n <= 0:
        return None
    alpha = 0.05 / FAMILY_SIZE_FOR_PRIMARY_RATES if familywise else 0.05
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return [lo, hi]


def cache_worker_init() -> None:
    install_design_cache()


def simulate_one(task: tuple[int, int, int, int]) -> dict[str, Any]:
    dataset_id, seed, outer, inner = task
    _DESIGN_CACHE.clear()
    rng = np.random.default_rng(seed)
    p = original.PROTOCOL
    contamination = np.zeros(7)
    contamination[[0, 3, 4]] = 0.0
    contamination[1] = contamination[2] = 0.5
    contamination[5] = 0.2
    ncfg = 24 * p["block_length"]
    window = p["reference_windows"][p["reference_nominal_window"]]
    try:
        # Preserve the original J=2/K=2 benchmark's raw-to-blocks path: unlike
        # run_simulation above it does not fold the family-world correlators.
        dev = blocks(original.world(rng, ncfg, contamination), p["block_length"])
        val = blocks(original.world(rng, 12 * p["block_length"], contamination), p["block_length"])
        _, _, p_single = original.gate(dev)
        gates = {kind: original.model_gate(dev, kind) for kind in ("single", "twostate")}
        reasons = []
        if p_single < ALPHA:
            reasons.append("single_reference_chi2")
        if not gates["single"]["passed"]:
            reasons.append("single_model_gate")
        if not gates["twostate"]["passed"]:
            reasons.append("twostate_model_gate")
        if gates["twostate"].get("at_boundary", False):
            reasons.append("twostate_mass_boundary")
        if reasons:
            return {"dataset_id": dataset_id, "seed": seed, "status": "ABSTAIN",
                    "reason_codes": sorted(set(reasons)), "single_reference_p": float(p_single),
                    "model_gates": gates, "n_outer": outer, "n_inner": inner}

        weights = {"base": np.eye(len(original.AMPS))[1],
                   "null": np.eye(len(original.AMPS))[2],
                   "better": np.eye(len(original.AMPS))[5]}
        risks = {model: {name: np.zeros(outer) for name in weights}
                 for model in ("single", "twostate")}
        for b in range(outer):
            dev_idx = rng.integers(0, len(dev), len(dev))
            val_idx = rng.integers(0, len(val), len(val))
            inner_idx = rng.integers(0, len(val), (inner, len(val)))
            for model in ("single", "twostate"):
                ref_b = make_reference(dev[dev_idx], p, window, model)
                fit_b, masses = ref_b.bootstrap(rng.integers(0, len(dev), (inner, len(dev))))
                for name, candidate_weights in weights.items():
                    late = late_metric(dev[dev_idx], candidate_weights, p)
                    risks[model][name][b] = risk(
                        val[val_idx], candidate_weights, fit_b["mass"], masses, inner_idx,
                        p, require_valid=False, late_inverse=late)["risk"]
        spec = {"schema": "pion-score-v1", "version": "c2-family", "estimand": "conditional",
                "baseline_id": "base", "accepted_models": ["single", "twostate"],
                "candidate_ids": ["null", "better"], "analysis_version": "c2-family",
                "alpha": ALPHA, "comparison_family": {"candidates": 2, "models": 2},
                "min_baseline_risk": 1e-9, "invalid_tolerance": 0.05,
                "min_improvement": 1.0, "risk_floor": 0.0, "require_draw_ids": True}
        draw_ids = np.arange(outer)
        spec["draw_ids_hash"] = hashlib.sha256(draw_ids.astype(np.int64).tobytes()).hexdigest()
        certificate = improvement_certificate(risks, spec, draw_ids=draw_ids)
        candidates = {}
        for name in ("null", "better"):
            row = certificate["candidates"][name]
            candidates[name] = {"certified": bool(row["certified"]),
                                "lower_bound": float(row["lower_bound"]),
                                "improvement_lower_bound": float(row["improvement_lower_bound"]),
                                "per_model_lower_bound": row["per_model_lower_bound"],
                                "invalid_draws": int(row["invalid_draws"])}
        return {"dataset_id": dataset_id, "seed": seed, "status": "VALID",
                "reason_codes": [], "single_reference_p": float(p_single),
                "model_gates": gates, "certificate_abstain": bool(certificate["abstain"]),
                "certificate_status": certificate["status"], "candidates": candidates,
                "family_false_certification": candidates["null"]["certified"],
                "better_power_event": candidates["better"]["certified"],
                "any_candidate_certified": any(row["certified"] for row in candidates.values()),
                "n_outer": outer, "n_inner": inner}
    except (ValueError, np.linalg.LinAlgError, FloatingPointError, OverflowError) as exc:
        return {"dataset_id": dataset_id, "seed": seed, "status": "INVALID",
                "reason_codes": [f"{type(exc).__name__}: {exc}"],
                "n_outer": outer, "n_inner": inner}


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    valid = [row for row in rows if row["status"] == "VALID"]
    abstain = [row for row in rows if row["status"] == "ABSTAIN"]
    invalid = [row for row in rows if row["status"] == "INVALID"]
    null_k = sum(row["family_false_certification"] for row in valid)
    better_k = sum(row["better_power_event"] for row in valid)
    any_k = sum(row["any_candidate_certified"] for row in valid)
    non_eval_k = len(abstain) + len(invalid)
    rates = {
        "unconditional_null_certification": {"k": null_k, "n": n, "rate": null_k / n,
            "marginal_cp95": cp_interval(null_k, n), "familywise_cp95": cp_interval(null_k, n, True)},
        "conditional_null_certification": {"k": null_k, "n": len(valid),
            "rate": null_k / len(valid) if valid else None,
            "marginal_cp95": cp_interval(null_k, len(valid)),
            "familywise_cp95": cp_interval(null_k, len(valid), True)},
        "conditional_better_power": {"k": better_k, "n": len(valid),
            "rate": better_k / len(valid) if valid else None,
            "marginal_cp95": cp_interval(better_k, len(valid)),
            "familywise_cp95": cp_interval(better_k, len(valid), True)},
        "non_evaluable": {"k": non_eval_k, "n": n, "rate": non_eval_k / n,
            "marginal_cp95": cp_interval(non_eval_k, n),
            "familywise_cp95": cp_interval(non_eval_k, n, True)},
        "unconditional_better_power": {"k": better_k, "n": n, "rate": better_k / n,
            "marginal_cp95": cp_interval(better_k, n),
            "familywise_cp95": cp_interval(better_k, n, True)},
        "conditional_any_candidate_certified": {"k": any_k, "n": len(valid),
            "rate": any_k / len(valid) if valid else None,
            "marginal_cp95": cp_interval(any_k, len(valid)),
            "familywise_cp95": cp_interval(any_k, len(valid), True)},
    }
    precision = {}
    for key in ("unconditional_null_certification", "conditional_null_certification",
                "conditional_better_power", "non_evaluable"):
        ci = rates[key]["marginal_cp95"]
        half_width = (ci[1] - ci[0]) / 2 if ci else None
        precision[key] = {"marginal_cp95_half_width": half_width,
                          "status": "PASS" if half_width is not None and half_width <= 0.05 else "INCONCLUSIVE"}
    reason_counts: dict[str, int] = {}
    boundary_count = 0
    for row in rows:
        for reason in row.get("reason_codes", []):
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        gates = row.get("model_gates", {})
        if gates.get("twostate", {}).get("at_boundary"):
            boundary_count += 1
    return {
        "schema": "pion-c2-j2-k2-family-expansion-summary-v1",
        "classification": "synthetic CPU family-subgate calibration; not physical score validation",
        "n_planned": n, "n_valid": len(valid), "n_abstain": len(abstain), "n_invalid": len(invalid),
        "rates": rates, "marginal_precision": precision,
        "two_state_mass_boundary_count": boundary_count,
        "reason_counts": reason_counts,
        "primary_family_size_for_intervals": FAMILY_SIZE_FOR_PRIMARY_RATES,
        "protocol_sha256": hashlib.sha256(canonical(protocol())).hexdigest(),
        "source_sha256": source_manifest(),
    }


def write_figure(rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    keys = ("unconditional_null_certification", "conditional_null_certification",
            "conditional_better_power", "non_evaluable")
    labels = ("Null cert\n(all planned)", "Null cert\n(gate-valid)",
              "Better power\n(gate-valid)", "Abstain/invalid\n(all planned)")
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.4))
    rates = summary["rates"]
    x = np.arange(len(keys))
    values = [rates[key]["rate"] for key in keys]
    cis = [rates[key]["familywise_cp95"] for key in keys]
    lo = [value - ci[0] for value, ci in zip(values, cis)]
    hi = [ci[1] - value for value, ci in zip(values, cis)]
    axes[0].errorbar(x, values, yerr=[lo, hi], fmt="o", capsize=4, color="#4477AA")
    axes[0].set(xticks=x, xticklabels=labels, ylabel="Dataset event rate",
                title="C2 J=2/K=2 family outcomes")
    axes[0].set_ylim(bottom=0)
    axes[0].grid(axis="y", alpha=.2)

    for model, color in (("single", "#4477AA"), ("twostate", "#CC6677")):
        pvals = [row["model_gates"][model]["p"] for row in rows if row.get("model_gates")]
        if pvals:
            axes[1].hist(pvals, bins=np.linspace(0, 1, 21), alpha=.5, density=True,
                         color=color, label=f"{model} gate p-value")
    axes[1].axvline(ALPHA, color="black", linestyle="--", label="gate threshold 0.05")
    axes[1].set(xlabel="Approximate chi-square p-value", ylabel="Density",
                title="Reference-model gate p-values")
    axes[1].legend(fontsize=8)
    fig.suptitle("Independent synthetic family expansion (400 datasets)")
    fig.tight_layout()
    fig.savefig(OUT / "c2_family_diagnostics.png", dpi=160)
    plt.close(fig)


def render_readme(summary: dict[str, Any]) -> str:
    rates = summary["rates"]
    lines = [
        "# Independent expansion of the synthetic C2 J=2/K=2 family benchmark",
        "",
        "This run uses 400 independent dataset seeds. It repeats the original two-candidate (null/better), two-model (single/twostate) certificate subgate benchmark with 40 outer risk draws and 16 inner mass-bootstrap draws. The family claim is conditional on both reference-model gates passing and the two-state fit not landing on a mass boundary.",
        "",
        "The study uses the same synthetic generator and implementation as `certificate_calibration.run_family`; it is not a full physical gate calibration. Design-matrix caching only avoids rebuilding identical deterministic matrices. The mass search grid, objective, covariance, gate, risk, and certificate calls are unchanged. A seed-matched parity smoke against the original function is recorded in `execution_provenance.json`.",
        "",
        "| Outcome | Count | Rate | Marginal CP95 | Four-rate familywise CP95 | MC precision |",
        "| --- | ---: | ---: | --- | --- | --- |",
    ]
    row_info = (
        ("unconditional_null_certification", "Null candidate certified / all planned"),
        ("conditional_null_certification", "Null candidate certified / gate-valid"),
        ("conditional_better_power", "Better candidate certified / gate-valid"),
        ("non_evaluable", "Abstain or invalid / all planned"),
    )
    for key, label in row_info:
        rec = rates[key]
        marginal = rec["marginal_cp95"]
        familywise = rec["familywise_cp95"]
        precision = summary["marginal_precision"][key]["status"]
        lines.append(f"| {label} | {rec['k']}/{rec['n']} | {rec['rate']:.4f} | [{marginal[0]:.4f},{marginal[1]:.4f}] | [{familywise[0]:.4f},{familywise[1]:.4f}] | {precision} |")
    lines.extend([
        "",
        f"Valid datasets: {summary['n_valid']}/{summary['n_planned']}; gate abstentions: {summary['n_abstain']}; invalid: {summary['n_invalid']}; two-state boundary fits: {summary['two_state_mass_boundary_count']}/{summary['n_planned']}.",
        f"Abstention reasons: `{json.dumps(summary['reason_counts'], sort_keys=True)}`.",
        "",
        "![C2 family outcomes and gate p-values](c2_family_diagnostics.png)",
        "",
        "## Interpretation boundary",
        "",
        "This is a synthetic family-subgate calibration for the declared C2 generator. It does not establish physical-state identity, validate a real anchor, or replace the source-limited 402/cell full-gate runs. The null-candidate family event is directly counted; conditional rates use only datasets passing both model gates. Any conditional interval whose marginal CP95 half-width exceeds 0.05 is marked INCONCLUSIVE. No post-hoc top-up is permitted.",
        "",
        "Raw per-dataset outcomes, seeds, gate p-values, boundary flags, certificate lower bounds, protocol/source hashes, and artifact digests are retained. Verify with `python -B -m tasks.pion_projection.certificate_family_expanded --verify`.",
    ])
    return "\n".join(lines) + "\n"


def parity_smoke() -> dict[str, Any]:
    """Compare one independent seed against the original production benchmark."""
    base = original.run_family(np.random.default_rng(PARITY_SEED), n_dataset=1,
                               outer=OUTER, inner=INNER)
    install_design_cache()
    fast = simulate_one((0, PARITY_SEED, OUTER, INNER))
    compare = {
        "seed": PARITY_SEED,
        "excluded_from_main_run": True,
        "original_abstain": base["abstain"],
        "cached_status": fast["status"],
        "original_certified_null": base["certified_null"],
        "cached_certified_null": int(fast.get("family_false_certification", False)),
        "original_certified_better": base["certified_better"],
        "cached_certified_better": int(fast.get("better_power_event", False)),
        "original_model_gates": base["model_gates_last"],
        "cached_model_gates": fast.get("model_gates"),
    }
    passed = (base["abstain"] == int(fast["status"] != "VALID")
              and base["certified_null"] == compare["cached_certified_null"]
              and base["certified_better"] == compare["cached_certified_better"]
              and base["model_gates_last"] == fast.get("model_gates"))
    compare["passed"] = bool(passed)
    if not passed:
        raise RuntimeError(f"cached fit parity failed: {compare}")
    return compare


def prepare() -> None:
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite {OUT}")
    parity = parity_smoke()
    OUT.mkdir(parents=True)
    frozen = protocol()
    (OUT / "protocol.json").write_text(json.dumps(frozen, indent=2, sort_keys=True) + "\n")
    prereg = {"protocol_sha256": hashlib.sha256(canonical(frozen)).hexdigest(),
              "source_sha256": source_manifest(), "parity_smoke": parity}
    (OUT / "preregistration.json").write_text(json.dumps(prereg, indent=2, sort_keys=True) + "\n")
    print("prepared", OUT.relative_to(ROOT), prereg["protocol_sha256"], "parity=PASS")


def run(workers: int = 4) -> None:
    frozen = json.loads((OUT / "protocol.json").read_text())
    prereg = json.loads((OUT / "preregistration.json").read_text())
    if hashlib.sha256(canonical(frozen)).hexdigest() != prereg["protocol_sha256"]:
        raise RuntimeError("protocol hash mismatch")
    if prereg["source_sha256"] != source_manifest():
        raise RuntimeError("analysis source hash mismatch")
    if any((OUT / name).exists() for name in OUTPUTS):
        raise FileExistsError("final outputs exist; refusing overwrite")
    tasks = [(i, BASE_SEED + i, OUTER, INNER) for i in range(N_DATASET)]
    rows: list[dict[str, Any]] = []
    context = mp.get_context("spawn")
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers, mp_context=context,
                                                initializer=cache_worker_init) as pool:
        for i, row in enumerate(pool.map(simulate_one, tasks, chunksize=1), start=1):
            rows.append(row)
            if i % 25 == 0:
                print(f"completed {i}/{N_DATASET}", flush=True)
    summary = summarize(rows)
    summary["protocol_sha256"] = prereg["protocol_sha256"]
    summary["source_sha256"] = prereg["source_sha256"]
    (OUT / "raw_outcomes.json").write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    write_figure(rows, summary)
    (OUT / "README.md").write_text(render_readme(summary))
    provenance = {
        "protocol_sha256": prereg["protocol_sha256"],
        "preregistered_source_sha256": prereg["source_sha256"],
        "current_source_sha256": source_manifest(),
        "parity_smoke": prereg["parity_smoke"],
        "planned_datasets": N_DATASET,
        "completed_datasets": len(rows),
        "worker_count": workers,
        "outer_draws_per_dataset": OUTER,
        "inner_mass_draws_per_outer_draw": INNER,
        "artifact_sha256": {name: sha256(OUT / name) for name in OUTPUTS},
    }
    (OUT / "execution_provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"valid": summary["n_valid"], "abstain": summary["n_abstain"],
                      "invalid": summary["n_invalid"],
                      "null_false_cert": summary["rates"]["conditional_null_certification"],
                      "better_power": summary["rates"]["conditional_better_power"]}, indent=2))


def verify() -> None:
    frozen = json.loads((OUT / "protocol.json").read_text())
    prereg = json.loads((OUT / "preregistration.json").read_text())
    if hashlib.sha256(canonical(frozen)).hexdigest() != prereg["protocol_sha256"]:
        raise RuntimeError("protocol hash mismatch")
    if prereg["source_sha256"] != source_manifest():
        raise RuntimeError("source hash mismatch")
    provenance = json.loads((OUT / "execution_provenance.json").read_text())
    if provenance["current_source_sha256"] != source_manifest():
        raise RuntimeError("execution source hash mismatch")
    for name, digest in provenance["artifact_sha256"].items():
        if sha256(OUT / name) != digest:
            raise RuntimeError(f"artifact hash mismatch: {name}")
    rows = json.loads((OUT / "raw_outcomes.json").read_text())
    summary = json.loads((OUT / "summary.json").read_text())
    if len(rows) != N_DATASET or len({row["dataset_id"] for row in rows}) != N_DATASET:
        raise RuntimeError("dataset ID/count mismatch")
    for row in rows:
        if row["seed"] != BASE_SEED + row["dataset_id"]:
            raise RuntimeError(f"seed mismatch for dataset {row['dataset_id']}")
    rebuilt = summarize(rows)
    for key in ("n_planned", "n_valid", "n_abstain", "n_invalid", "rates", "reason_counts"):
        if rebuilt[key] != summary[key]:
            raise RuntimeError(f"summary mismatch: {key}")
    print(f"verified hashes, {summary['n_valid']} valid + {summary['n_abstain']} abstain + {summary['n_invalid']} invalid; {N_DATASET} independent datasets")


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check-fast-parity", action="store_true")
    group.add_argument("--prepare", action="store_true")
    group.add_argument("--run", action="store_true")
    group.add_argument("--verify", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.check_fast_parity:
        print(json.dumps(parity_smoke(), indent=2))
    elif args.prepare:
        prepare()
    elif args.run:
        if args.workers < 1:
            raise ValueError("workers must be positive")
        run(args.workers)
    else:
        verify()


if __name__ == "__main__":
    main()
