"""Independent N=400/cell expansion of the synthetic C3 anchor experiment."""
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

from .energy_experiment import correlators, estimate, protocol as data_protocol
from .energy_target import lower_bound


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/pion_projection/anchor_calibration_expanded_20261120_v1"
N_DATASET = 400
N_BOOT = 200
NCFG = 120
E0 = 0.80
TAU_E = 0.01
ALPHA = 0.05
BASE_SEED = 2026112800
SCENARIOS = (
    {"name": "improvement", "candidate_noise": 0.01, "anchor_sigma": 0.01, "anchor_bias": 0.0},
    {"name": "null", "candidate_noise": 0.02, "anchor_sigma": 0.01, "anchor_bias": 0.0},
    {"name": "anchor_bias", "candidate_noise": 0.01, "anchor_sigma": 0.0, "anchor_bias": 0.02},
)
SOURCE_FILES = (
    "tasks/pion_projection/anchor_calibration_expanded.py",
    "tasks/pion_projection/energy_experiment.py",
    "tasks/pion_projection/energy_target.py",
    "tasks/pion_projection/statistics.py",
    "tasks/pion_projection/reference.py",
    "results/pion_projection/s16t16_gevp200/development_provenance.json",
)
OUTPUTS = ("raw_outcomes.json", "summary.json", "anchor_expansion.png", "README.md")


def canonical(x: object) -> bytes:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_manifest() -> dict[str, str]:
    return {name: sha256(ROOT / name) for name in SOURCE_FILES}


def protocol() -> dict:
    p = data_protocol()
    return {
        "schema": "pion-c3-anchor-calibration-independent-expansion-v1",
        "classification": "synthetic CPU method replication; oracle-anchor worlds are not physical validation",
        "purpose": "Reduce Monte Carlo uncertainty in the C3 comparison of naive pseudo-replicated, single-dataset paired-bootstrap, and independent-repeat inference.",
        "n_independent_datasets_per_scenario": N_DATASET,
        "n_bootstrap_draws_per_dataset_arm": N_BOOT,
        "ncfg": NCFG,
        "truth_energy": E0,
        "tau_energy": TAU_E,
        "scenarios": [dict(x) for x in SCENARIOS],
        "estimand_and_methods": {
            "delta_draw": "[(E_base - E_anchor)^2 - (E_candidate - E_anchor)^2] / tau_E^2; same anchor draw is shared between baseline and candidate within a dataset",
            "naive_pseudoreplication": "within-dataset lower_bound(delta_draw, alpha=0.05) uses sd/sqrt(N_BOOT), treating bootstrap draws as independent; included as negative-method control",
            "single_dataset_paired": "5th percentile of paired delta_draws > 0; no extra division by sqrt(N_BOOT)",
            "independent_repeat": "mean of one delta_draw mean per independently generated dataset; dataset-level bootstrap CI across outer IDs",
            "anchor": "oracle E0 plus scenario-specific Gaussian bias/noise; anchor draws are common to both arms within dataset",
        },
        "precision_target": "N=400 gives worst-case marginal binomial CP95 half-width approximately 0.05; no top-up.",
        "intervals": "Familywise 95% CP intervals over six certification rates use Bonferroni-adjusted exact intervals; familywise 95% dataset-bootstrap intervals over three independent-repeat means.",
        "seeds": {"base": BASE_SEED, "rule": "Each RNG is initialized from SeedSequence([BASE_SEED, scenario_index, dataset_id, stream]); streams 0/1/2/3 denote data, shared anchor, baseline bootstrap indices, and candidate bootstrap indices. The full seed tuple and generated bootstrap integer are retained."},
        "frozen_fit_protocol": {key: p[key] for key in ("geometry", "block_length", "reference_basis", "reference_windows", "reference_nominal_window", "mass_bounds")},
        "outputs": list(OUTPUTS),
        "output_directory": str(OUT.relative_to(ROOT)),
        "frozen_sources": list(SOURCE_FILES),
    }


def cp_interval(k: int, n: int, family_size: int) -> list[float]:
    alpha = 0.05 / family_size
    lo = 0.0 if k == 0 else float(beta.ppf(alpha/2, k, n-k+1))
    hi = 1.0 if k == n else float(beta.ppf(1-alpha/2, k+1, n-k))
    return [lo, hi]


def mean_ci(values: np.ndarray, seed: int, family_size: int = 3) -> list[float]:
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(values), size=(20000, len(values)))
    means = values[idx].mean(axis=1)
    tail = 0.05 / (2 * family_size)
    return [float(np.quantile(means, tail)), float(np.quantile(means, 1-tail))]


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
    frozen = json.loads((OUT/"protocol.json").read_text())
    prereg = json.loads((OUT/"preregistration.json").read_text())
    if prereg["protocol_sha256"] != hashlib.sha256(canonical(frozen)).hexdigest():
        raise RuntimeError("protocol hash mismatch")
    if prereg["source_sha256"] != source_manifest():
        raise RuntimeError("source hash mismatch")
    if any((OUT/name).exists() for name in OUTPUTS):
        raise FileExistsError("final outputs exist; refusing overwrite")

    p = data_protocol()
    raw = []
    summaries = []
    for scenario_index, scenario in enumerate(SCENARIOS):
        rows = []
        for dataset_id in range(N_DATASET):
            data_seed = [BASE_SEED, scenario_index, dataset_id, 0]
            anchor_seed = [BASE_SEED, scenario_index, dataset_id, 1]
            base_boot_seed = [BASE_SEED, scenario_index, dataset_id, 2]
            cand_boot_seed = [BASE_SEED, scenario_index, dataset_id, 3]
            rng_data = np.random.default_rng(np.random.SeedSequence(data_seed))
            rng_anchor = np.random.default_rng(np.random.SeedSequence(anchor_seed))
            base_raw = correlators(rng_data, ncfg=NCFG, noise=0.02)
            cand_raw = correlators(rng_data, ncfg=NCFG, noise=scenario["candidate_noise"])
            base_boot_value = int(np.random.SeedSequence(base_boot_seed).generate_state(1)[0] % (2**31-1))
            cand_boot_value = int(np.random.SeedSequence(cand_boot_seed).generate_state(1)[0] % (2**31-1))
            try:
                e_base, base_draws = estimate(base_raw, p, "single", nboot=N_BOOT, seed=base_boot_value)
                e_cand, cand_draws = estimate(cand_raw, p, "single", nboot=N_BOOT, seed=cand_boot_value)
                anchor = E0 + scenario["anchor_bias"] + rng_anchor.normal(0, scenario["anchor_sigma"], N_BOOT)
                delta = ((base_draws - anchor)**2 - (cand_draws - anchor)**2) / TAU_E**2
                naive_lower = lower_bound(delta, ALPHA)
                paired_lower = float(np.quantile(delta, ALPHA))
                row = {
                    "scenario": scenario["name"], "dataset_id": dataset_id,
                    "candidate_noise": scenario["candidate_noise"],
                    "anchor_sigma": scenario["anchor_sigma"], "anchor_bias": scenario["anchor_bias"],
                    "baseline_point_mass": e_base, "candidate_point_mass": e_cand,
                    "dataset_delta_mean": float(np.mean(delta)),
                    "dataset_delta_sd": float(np.std(delta, ddof=1)),
                    "naive_pseudorep_lower_bound": float(naive_lower),
                    "paired_lower_quantile": paired_lower,
                    "naive_certified": bool(naive_lower > 0),
                    "paired_certified": bool(paired_lower > 0),
                    "status": "VALID",
                    "seeds": {"data": data_seed, "anchor": anchor_seed,
                              "baseline_bootstrap_sequence": base_boot_seed,
                              "baseline_bootstrap_integer": base_boot_value,
                              "candidate_bootstrap_sequence": cand_boot_seed,
                              "candidate_bootstrap_integer": cand_boot_value},
                }
            except Exception as exc:
                row = {"scenario": scenario["name"], "dataset_id": dataset_id,
                       "candidate_noise": scenario["candidate_noise"],
                       "anchor_sigma": scenario["anchor_sigma"], "anchor_bias": scenario["anchor_bias"],
                       "status": "INVALID", "reason": f"{type(exc).__name__}: {exc}"}
            rows.append(row)
            raw.append(row)
            if (dataset_id + 1) % 50 == 0:
                print(f"{scenario['name']}: {dataset_id+1}/{N_DATASET}", flush=True)

        valid = [r for r in rows if r["status"] == "VALID"]
        nvalid = len(valid)
        naive_n = sum(r["naive_certified"] for r in valid)
        paired_n = sum(r["paired_certified"] for r in valid)
        deltas = np.array([r["dataset_delta_mean"] for r in valid])
        summaries.append({
            **scenario,
            "n_planned": N_DATASET, "n_valid": nvalid, "n_invalid": N_DATASET-nvalid,
            "naive_pseudorep_certified": naive_n,
            "naive_pseudorep_rate": naive_n/nvalid if nvalid else None,
            "naive_familywise_cp95": cp_interval(naive_n, nvalid, 6) if nvalid else None,
            "single_dataset_paired_certified": paired_n,
            "single_dataset_paired_rate": paired_n/nvalid if nvalid else None,
            "paired_familywise_cp95": cp_interval(paired_n, nvalid, 6) if nvalid else None,
            "independent_repeat_mean_delta": float(deltas.mean()) if nvalid else None,
            "independent_repeat_familywise_dataset_bootstrap_ci95": mean_ci(deltas, BASE_SEED+scenario_index+5000) if nvalid else None,
            "independent_repeat_se": float(deltas.std(ddof=1)/np.sqrt(nvalid)) if nvalid > 1 else None,
            "median_dataset_delta": float(np.median(deltas)) if nvalid else None,
        })
        print(f"scenario={scenario['name']}: naive={naive_n}/{nvalid}, paired={paired_n}/{nvalid}", flush=True)

    summary = {"schema": "pion-c3-anchor-independent-expansion-summary-v1",
               "classification": frozen["classification"],
               "protocol_sha256": prereg["protocol_sha256"], "source_sha256": prereg["source_sha256"],
               "n_datasets_per_scenario": N_DATASET, "n_bootstrap_draws_per_arm": N_BOOT,
               "total_datasets": len(raw), "scenarios": summaries}
    (OUT/"raw_outcomes.json").write_text(json.dumps(raw, indent=2, sort_keys=True)+"\n")
    (OUT/"summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True)+"\n")
    write_figure(summary, raw)
    (OUT/"README.md").write_text(render_readme(summary))
    prov = {"protocol_sha256": prereg["protocol_sha256"],
            "preregistered_source_sha256": prereg["source_sha256"],
            "current_source_sha256": source_manifest(),
            "planned_datasets": N_DATASET*len(SCENARIOS),
            "completed_datasets": len(raw),
            "planned_bootstrap_mass_fits": N_DATASET*len(SCENARIOS)*N_BOOT*2,
            "artifact_sha256": {name: sha256(OUT/name) for name in OUTPUTS}}
    (OUT/"execution_provenance.json").write_text(json.dumps(prov, indent=2, sort_keys=True)+"\n")
    print("completed", OUT.relative_to(ROOT))


def write_figure(summary: dict, raw: list[dict]) -> None:
    names = [x["name"] for x in SCENARIOS]
    rates_naive = [x["naive_pseudorep_rate"] for x in summary["scenarios"]]
    rates_paired = [x["single_dataset_paired_rate"] for x in summary["scenarios"]]
    cis_naive = [x["naive_familywise_cp95"] for x in summary["scenarios"]]
    cis_paired = [x["paired_familywise_cp95"] for x in summary["scenarios"]]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
    x = np.arange(len(names))
    for vals, cis, shift, label, color in ((rates_naive, cis_naive, -.08, "Naive sd/sqrt(Nboot)", "#CC6677"),
                                          (rates_paired, cis_paired, .08, "Paired 5th percentile", "#4477AA")):
        lo = np.array([v-c[0] for v,c in zip(vals,cis)])
        hi = np.array([c[1]-v for v,c in zip(vals,cis)])
        axes[0].errorbar(x+shift, vals, yerr=[lo,hi], marker="o", capsize=3, label=label, color=color)
    axes[0].axhline(.05, color="black", linestyle="--", linewidth=1, label="5% reference")
    axes[0].set(xticks=x, xticklabels=names, ylabel="Certification frequency", title="Across 400 independent datasets")
    axes[0].legend(fontsize=8)

    data = [[r["dataset_delta_mean"] for r in raw if r["scenario"] == name and r["status"] == "VALID"] for name in names]
    axes[1].boxplot(data, labels=names, showfliers=False, whis=(2.5,97.5))
    axes[1].axhline(0, color="black", linestyle="--", linewidth=1)
    axes[1].set(ylabel="Per-dataset paired mean delta", title="Independent-repeat dataset outcomes")
    fig.suptitle("C3 anchor interval semantics: independent synthetic expansion")
    fig.tight_layout()
    fig.savefig(OUT/"anchor_expansion.png", dpi=160)
    plt.close(fig)


def render_readme(summary: dict) -> str:
    lines = [
        "# Independent expansion of synthetic C3 anchor calibration",
        "",
        "This new independent-seed run expands three decision-relevant C3 scenarios to 400 datasets each. Every dataset has 200 baseline and candidate mass-bootstrap draws; anchor uncertainty is shared between the two arms within that dataset. The anchor is an oracle-centered synthetic value, not a measured physical anchor.",
        "",
        "The naive rule uses sd/sqrt(N_boot) and is retained as a pseudo-replication negative control. The single-ensemble paired rule uses the 5th percentile of the paired delta draws without an extra 1/sqrt(N_boot). The independent-repeat estimand is the average per-dataset delta across outer independent datasets. Familywise intervals cover six certification rates and three independent-repeat mean intervals, respectively.",
        "",
        "| Scenario | Valid / planned | Naive certified | Paired certified | Independent-repeat mean delta | Familywise dataset-bootstrap CI95 | Independent-repeat SE |",
        "| --- | ---: | ---: | ---: | ---: | --- | ---: |",
    ]
    for s in summary["scenarios"]:
        ci = s["independent_repeat_familywise_dataset_bootstrap_ci95"]
        naive_ci, paired_ci = s["naive_familywise_cp95"], s["paired_familywise_cp95"]
        lines.append(f"| {s['name']} | {s['n_valid']}/{s['n_planned']} | {s['naive_pseudorep_certified']}/{s['n_valid']} ({s['naive_pseudorep_rate']:.3f}, FW-CP95 [{naive_ci[0]:.3f},{naive_ci[1]:.3f}]) | {s['single_dataset_paired_certified']}/{s['n_valid']} ({s['single_dataset_paired_rate']:.3f}, FW-CP95 [{paired_ci[0]:.3f},{paired_ci[1]:.3f}]) | {s['independent_repeat_mean_delta']:.5f} | [{ci[0]:.5f},{ci[1]:.5f}] | {s['independent_repeat_se']:.5f} |")
    lines += [
        "",
        "![C3 independent expansion](anchor_expansion.png)",
        "",
        "## Interpretation boundary",
        "",
        "This run tests statistical behavior in the frozen synthetic correlator and oracle-anchor worlds. It can quantify outer Monte Carlo uncertainty and compare interval semantics; it does not measure physical anchor reliability, lattice autocorrelation, or a physical score. An anchor-bias scenario is a structural sensitivity, not an estimate of the real anchor bias.",
        "",
        "Raw dataset-level masses, delta summaries, certification indicators, seeds, frozen fit protocol/source hashes, and artifact hashes are retained. Verify with `python -B -m tasks.pion_projection.anchor_calibration_expanded --verify`.",
    ]
    return "\n".join(lines)+"\n"


def verify() -> None:
    frozen = json.loads((OUT/"protocol.json").read_text())
    prereg = json.loads((OUT/"preregistration.json").read_text())
    if hashlib.sha256(canonical(frozen)).hexdigest() != prereg["protocol_sha256"]:
        raise RuntimeError("protocol hash mismatch")
    if prereg["source_sha256"] != source_manifest():
        raise RuntimeError("source hash mismatch")
    prov = json.loads((OUT/"execution_provenance.json").read_text())
    if prov["current_source_sha256"] != source_manifest():
        raise RuntimeError("execution source hash mismatch")
    for name, digest in prov["artifact_sha256"].items():
        if sha256(OUT/name) != digest:
            raise RuntimeError(f"artifact hash mismatch: {name}")
    raw = json.loads((OUT/"raw_outcomes.json").read_text())
    summary = json.loads((OUT/"summary.json").read_text())
    if len(raw) != N_DATASET*len(SCENARIOS):
        raise RuntimeError("raw count mismatch")
    for s in summary["scenarios"]:
        rows = [r for r in raw if r["scenario"] == s["name"]]
        valid = [r for r in rows if r["status"] == "VALID"]
        if len(rows) != N_DATASET or len(valid) != s["n_valid"]:
            raise RuntimeError(f"dataset count mismatch: {s['name']}")
        if sum(r["naive_certified"] for r in valid) != s["naive_pseudorep_certified"]:
            raise RuntimeError(f"naive count mismatch: {s['name']}")
        if sum(r["paired_certified"] for r in valid) != s["single_dataset_paired_certified"]:
            raise RuntimeError(f"paired count mismatch: {s['name']}")
    print(f"verified hashes, {len(SCENARIOS)} scenarios x {N_DATASET} datasets, {N_BOOT} mass draws/arm")


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
