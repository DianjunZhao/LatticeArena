"""C3 synthetic null with fixed anchor bias and equal baseline/candidate noise."""
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
from .energy_target import energy_delta, lower_bound


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/pion_projection/anchor_bias_null_20261120_v1"
N_DATASET = 400
N_BOOT = 200
NCFG = 120
E0 = 0.80
TAU_E = 0.01
ALPHA = 0.05
NOISE = 0.02
ANCHOR_BIASES = (-0.02, 0.0, 0.02)
BASE_SEED = 2026112020
SOURCE_FILES = (
    "tasks/pion_projection/anchor_bias_only_null.py",
    "tasks/pion_projection/energy_experiment.py",
    "tasks/pion_projection/energy_target.py",
    "tasks/pion_projection/statistics.py",
    "tasks/pion_projection/reference.py",
    "results/pion_projection/s16t16_gevp200/development_provenance.json",
    "tasks/pion_projection/anchor_calibration_expanded.py",
)
OUTPUTS = ("raw_outcomes.json", "summary.json", "anchor_bias_null_diagnostics.png", "README.md")


def canonical(x: object) -> bytes:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_manifest() -> dict[str, str]:
    return {name: sha256(ROOT / name) for name in SOURCE_FILES}


def protocol() -> dict:
    p = data_protocol()
    return {
        "schema": "pion-c3-anchor-bias-only-null-v1",
        "classification": "synthetic CPU null calibration; not physical anchor validation",
        "question": "Under equal baseline/candidate data-generating distributions, does a fixed common anchor offset change the false-certification frequency of the existing naive and paired rules?",
        "design": {
            "independent_dataset_ids": N_DATASET,
            "anchor_biases": list(ANCHOR_BIASES),
            "baseline_noise": NOISE,
            "candidate_noise": NOISE,
            "anchor_sigma": 0.0,
            "truth_energy": E0,
            "configurations": NCFG,
            "mass_bootstrap_draws_per_arm": N_BOOT,
            "risk_scale_tau_energy": TAU_E,
            "alpha": ALPHA,
            "equal_noise_null": "Both arms use the unchanged energy_experiment.correlators generator with noise=0.02; candidate and baseline have the same true spectrum and noise law. Each dataset is fit once per arm, then the same mass draws are evaluated at anchor biases -0.02, 0, +0.02.",
            "anchor_bias_choice": "The absolute offset 0.02 is inherited from the earlier frozen C3 anchor-bias sensitivity; both signs are included to expose direction dependence, with no tuning after outcomes.",
        },
        "estimands_and_rules": {
            "delta": "[(E_base-E_anchor)^2-(E_candidate-E_anchor)^2]/tau_E^2",
            "naive_rule": "Existing lower_bound(delta, alpha=0.05), retaining the sd/sqrt(N_boot) pseudo-replication rule as a diagnostic control.",
            "paired_rule": "Existing 5th percentile of delta > 0, with no post-hoc threshold change.",
            "independent_repeat": "Mean dataset-level delta across the 400 independent dataset IDs; dataset bootstrap CI.",
            "paired_bias_contrast": "For each rule, compare each biased-anchor certification indicator with its zero-bias indicator on the same dataset ID; bootstrap the mean paired difference.",
        },
        "precision": "400 independent IDs; report marginal CP95 and six-rate Bonferroni familywise CP95. No top-up. Invalid fit rows remain recorded and count as non-certifications for the planned-denominator rate.",
        "seeds": {"base": BASE_SEED, "rule": "SeedSequence([BASE_SEED,dataset_id,stream]); streams 0/1/2 generate correlator data, baseline bootstrap indices, and candidate bootstrap indices."},
        "frozen_fit_protocol": {key: p[key] for key in ("geometry", "block_length", "reference_basis", "reference_windows", "reference_nominal_window", "mass_bounds")},
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

    fit_protocol = data_protocol()
    window = fit_protocol["reference_windows"][fit_protocol["reference_nominal_window"]]
    rows: list[dict] = []
    for dataset_id in range(N_DATASET):
        data_seed = [BASE_SEED, dataset_id, 0]
        base_boot_seed = [BASE_SEED, dataset_id, 1]
        candidate_boot_seed = [BASE_SEED, dataset_id, 2]
        rng_data = np.random.default_rng(np.random.SeedSequence(data_seed))
        raw_base = correlators(rng_data, ncfg=NCFG, noise=NOISE)
        raw_candidate = correlators(rng_data, ncfg=NCFG, noise=NOISE)
        base_boot_int = int(np.random.SeedSequence(base_boot_seed).generate_state(1)[0] % (2**31 - 1))
        candidate_boot_int = int(np.random.SeedSequence(candidate_boot_seed).generate_state(1)[0] % (2**31 - 1))
        try:
            base_point, base_draws = estimate(raw_base, fit_protocol, "single", nboot=N_BOOT, seed=base_boot_int)
            candidate_point, candidate_draws = estimate(raw_candidate, fit_protocol, "single", nboot=N_BOOT, seed=candidate_boot_int)
            for anchor_bias in ANCHOR_BIASES:
                anchor = np.full(N_BOOT, E0 + anchor_bias)
                delta = energy_delta(base_draws, candidate_draws, anchor, TAU_E)
                naive_bound = lower_bound(delta, ALPHA)
                paired_bound = float(np.quantile(delta, ALPHA))
                rows.append({
                    "dataset_id": dataset_id,
                    "anchor_bias": anchor_bias,
                    "anchor_value": E0 + anchor_bias,
                    "baseline_noise": NOISE,
                    "candidate_noise": NOISE,
                    "baseline_point_mass": base_point,
                    "candidate_point_mass": candidate_point,
                    "dataset_delta_mean": float(np.mean(delta)),
                    "dataset_delta_sd": float(np.std(delta, ddof=1)),
                    "naive_lower_bound": naive_bound,
                    "paired_lower_quantile": paired_bound,
                    "naive_certified": bool(naive_bound > 0),
                    "paired_certified": bool(paired_bound > 0),
                    "status": "VALID",
                    "seeds": {"data": data_seed, "baseline_bootstrap_sequence": base_boot_seed,
                              "baseline_bootstrap_integer": base_boot_int,
                              "candidate_bootstrap_sequence": candidate_boot_seed,
                              "candidate_bootstrap_integer": candidate_boot_int},
                })
        except Exception as exc:
            for anchor_bias in ANCHOR_BIASES:
                rows.append({"dataset_id": dataset_id, "anchor_bias": anchor_bias,
                             "baseline_noise": NOISE, "candidate_noise": NOISE,
                             "status": "INVALID", "reason": f"{type(exc).__name__}: {exc}",
                             "seeds": {"data": data_seed, "baseline_bootstrap_sequence": base_boot_seed,
                                       "candidate_bootstrap_sequence": candidate_boot_seed}})
        if (dataset_id + 1) % 50 == 0:
            print(f"datasets={dataset_id + 1}/{N_DATASET}", flush=True)

    summaries = []
    for bias_index, anchor_bias in enumerate(ANCHOR_BIASES):
        cell = [r for r in rows if r["anchor_bias"] == anchor_bias]
        valid = [r for r in cell if r["status"] == "VALID"]
        item: dict = {"anchor_bias": anchor_bias, "anchor_value": E0 + anchor_bias,
                      "n_planned": N_DATASET, "n_valid": len(valid), "n_invalid": N_DATASET - len(valid)}
        for method in ("naive", "paired"):
            events = sum(r[f"{method}_certified"] for r in valid)
            planned_events = events  # Invalid fits are non-certifications by the frozen fail-closed rule.
            item[f"{method}_certified_valid"] = events
            item[f"{method}_rate_valid"] = events / len(valid) if valid else None
            item[f"{method}_cp95_marginal"] = cp_interval(events, len(valid)) if valid else None
            item[f"{method}_certified_planned"] = planned_events
            item[f"{method}_rate_planned"] = planned_events / N_DATASET
            item[f"{method}_cp95_familywise"] = cp_interval(planned_events, N_DATASET, 6)
        means = np.array([r["dataset_delta_mean"] for r in valid])
        item["independent_repeat_mean_delta"] = float(means.mean()) if len(means) else None
        item["independent_repeat_ci95_familywise"] = bootstrap_mean_ci(means, BASE_SEED + 10000 + bias_index, 3) if len(means) else None
        item["independent_repeat_se"] = float(means.std(ddof=1) / np.sqrt(len(means))) if len(means) > 1 else None
        item["median_dataset_delta"] = float(np.median(means)) if len(means) else None
        summaries.append(item)

    contrasts = []
    zero_rows = {r["dataset_id"]: r for r in rows if r["anchor_bias"] == 0.0}
    for bias_index, anchor_bias in ((0, -0.02), (1, 0.02)):
        biased = {r["dataset_id"]: r for r in rows if r["anchor_bias"] == anchor_bias}
        for method in ("naive", "paired"):
            differences = np.array([
                float(biased[i][f"{method}_certified"]) - float(zero_rows[i][f"{method}_certified"])
                for i in range(N_DATASET)
                if biased[i]["status"] == "VALID" and zero_rows[i]["status"] == "VALID"
            ])
            contrasts.append({
                "anchor_bias": anchor_bias,
                "method": method,
                "n_paired": len(differences),
                "mean_rate_difference_vs_zero_bias": float(differences.mean()) if len(differences) else None,
                "familywise_paired_dataset_bootstrap_ci95": None,
            })
            # Keep the familywise paired interval alongside direction-switch counts.
            contrasts[-1]["familywise_paired_dataset_bootstrap_ci95"] = bootstrap_mean_ci(
                differences, BASE_SEED + 20000 + 2 * bias_index + int(method == "paired"), 4
            ) if len(differences) else None
            contrasts[-1]["certification_switches_0_to_1"] = int(np.sum(differences == 1))
            contrasts[-1]["certification_switches_1_to_0"] = int(np.sum(differences == -1))

    summary = {"schema": "pion-c3-anchor-bias-only-null-summary-v1",
               "classification": frozen["classification"],
               "protocol_sha256": prereg["protocol_sha256"],
               "source_sha256": prereg["source_sha256"],
               "n_independent_dataset_ids": N_DATASET,
               "n_dataset_bias_rows": len(rows),
               "alpha": ALPHA,
               "scenarios": summaries,
               "paired_bias_contrasts": contrasts}
    (OUT / "raw_outcomes.json").write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    write_figure(summary, rows)
    (OUT / "README.md").write_text(render_readme(summary))
    provenance = {"protocol_sha256": prereg["protocol_sha256"],
                  "preregistered_source_sha256": prereg["source_sha256"],
                  "current_source_sha256": source_manifest(),
                  "planned_dataset_ids": N_DATASET,
                  "completed_dataset_bias_rows": len(rows),
                  "planned_mass_bootstrap_fits": N_DATASET * N_BOOT * 2,
                  "artifact_sha256": {name: sha256(OUT / name) for name in OUTPUTS}}
    (OUT / "execution_provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    print("completed", OUT.relative_to(ROOT))


def write_figure(summary: dict, rows: list[dict]) -> None:
    scenarios = summary["scenarios"]
    biases = [s["anchor_bias"] for s in scenarios]
    labels = [f"{x:+.2f}" for x in biases]
    x = np.arange(len(biases))
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
    for method, shift, color, label in (("naive", -0.035, "#CC6677", "Naive sd/√Nboot"),
                                         ("paired", 0.035, "#4477AA", "Paired 5th percentile")):
        values = np.array([s[f"{method}_rate_planned"] for s in scenarios])
        cis = [s[f"{method}_cp95_familywise"] for s in scenarios]
        lo = np.array([v - ci[0] for v, ci in zip(values, cis)])
        hi = np.array([ci[1] - v for v, ci in zip(values, cis)])
        axes[0].errorbar(x + shift, values, yerr=np.vstack((lo, hi)), fmt="o-", capsize=3, color=color, label=label)
    axes[0].axhline(ALPHA, color="black", linestyle="--", linewidth=1, label="5% reference")
    axes[0].set(xticks=x, xticklabels=labels, xlabel="Fixed anchor offset from true E0", ylabel="False-certification rate / planned dataset",
                title="Equal-noise null across independent datasets")
    axes[0].legend(fontsize=8)
    data = [[r["dataset_delta_mean"] for r in rows if r["anchor_bias"] == b and r["status"] == "VALID"] for b in ANCHOR_BIASES]
    axes[1].boxplot(data, tick_labels=labels, showfliers=False, whis=(2.5, 97.5))
    axes[1].axhline(0, color="black", linestyle="--", linewidth=1)
    axes[1].set(xlabel="Fixed anchor offset from true E0", ylabel="Per-dataset mean paired delta",
                title="Distribution of 400 independent outcomes")
    fig.suptitle("C3 anchor-bias-only null: baseline and candidate have equal noise")
    fig.tight_layout()
    fig.savefig(OUT / "anchor_bias_null_diagnostics.png", dpi=160)
    plt.close(fig)


def render_readme(summary: dict) -> str:
    lines = [
        "# C3 anchor-bias-only null (synthetic CPU diagnostic)",
        "",
        "This preregistered extension uses **400 independent dataset IDs**. In every ID, baseline and candidate are generated from the same spectrum and the same noise law (`noise=0.02`); only the common anchor is shifted by -0.02, 0, or +0.02 from the known synthetic truth. The ±0.02 magnitude was inherited from the prior C3 anchor-bias sensitivity. Each arm has 200 mass-bootstrap draws. The same fitted mass draws are evaluated at all three anchor offsets, so offset contrasts are paired by dataset ID.",
        "",
        "The two frozen rules are the existing naive normal lower bound (`sd/sqrt(Nboot)`, retained as a negative-method control) and the existing paired 5th-percentile rule. Invalid fits are retained and treated as non-certifications for the planned-denominator rate. Reported intervals are marginal CP95 and six-rate Bonferroni familywise CP95; independent-repeat means and four paired certification-rate contrasts use dataset-bootstrap familywise intervals.",
        "",
        "| Anchor offset | Valid / planned | Naive certified | Paired certified | Independent-repeat mean delta | Familywise CI95 for mean delta |",
        "| ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for s in summary["scenarios"]:
        ci = s["independent_repeat_ci95_familywise"]
        lines.append(f"| {s['anchor_bias']:+.2f} | {s['n_valid']}/{s['n_planned']} | {s['naive_certified_valid']}/{s['n_valid']} ({s['naive_rate_valid']:.3f}; marginal CP95 [{s['naive_cp95_marginal'][0]:.3f},{s['naive_cp95_marginal'][1]:.3f}]) | {s['paired_certified_valid']}/{s['n_valid']} ({s['paired_rate_valid']:.3f}; marginal CP95 [{s['paired_cp95_marginal'][0]:.3f},{s['paired_cp95_marginal'][1]:.3f}]) | {s['independent_repeat_mean_delta']:.5f} | [{ci[0]:.5f},{ci[1]:.5f}] |")
    lines += ["", "![False-certification and dataset-outcome diagnostics](anchor_bias_null_diagnostics.png)", "",
              "## Paired bias contrasts", "",
              "| Anchor offset | Rule | Rate difference vs zero bias | Familywise dataset-bootstrap CI95 | 0→1 / 1→0 switches |",
              "| ---: | --- | ---: | --- | ---: |"]
    for c in summary["paired_bias_contrasts"]:
        ci = c["familywise_paired_dataset_bootstrap_ci95"]
        lines.append(f"| {c['anchor_bias']:+.2f} | {c['method']} | {c['mean_rate_difference_vs_zero_bias']:+.4f} | [{ci[0]:+.4f},{ci[1]:+.4f}] | {c['certification_switches_0_to_1']} / {c['certification_switches_1_to_0']} |")
    lines += ["", "## Interpretation boundary", "",
              "This is an equal-noise synthetic null under a fixed two-state correlator generator and oracle-known truth. It tests whether the current scalar risk rule is sensitive to a common fixed anchor offset in this model. It does not estimate real anchor bias, lattice autocorrelation, family-wise physical-score coverage, or the behavior of other generators. A certification rate above 5% is evidence against nominal size only for this declared DGP; a rate near 5% does not validate the physical score. No threshold was tuned and no post-hoc top-up was performed.",
              "", "Raw per-dataset masses, deltas, certification events, seeds, source/protocol hashes, and output hashes are retained. Verify with `python -B -m tasks.pion_projection.anchor_bias_only_null --verify`."]
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
        raise RuntimeError("execution source hash mismatch")
    for name, digest in provenance["artifact_sha256"].items():
        if sha256(OUT / name) != digest:
            raise RuntimeError(f"artifact hash mismatch: {name}")
    raw = json.loads((OUT / "raw_outcomes.json").read_text())
    summary = json.loads((OUT / "summary.json").read_text())
    if len(raw) != N_DATASET * len(ANCHOR_BIASES):
        raise RuntimeError("raw outcome count mismatch")
    for scenario in summary["scenarios"]:
        cell = [r for r in raw if r["anchor_bias"] == scenario["anchor_bias"]]
        valid = [r for r in cell if r["status"] == "VALID"]
        if len(cell) != N_DATASET or len(valid) != scenario["n_valid"]:
            raise RuntimeError(f"dataset count mismatch at bias {scenario['anchor_bias']}")
        for method in ("naive", "paired"):
            if sum(r[f"{method}_certified"] for r in valid) != scenario[f"{method}_certified_valid"]:
                raise RuntimeError(f"certification count mismatch at bias {scenario['anchor_bias']}, method {method}")
    print(f"verified hashes, {len(ANCHOR_BIASES)} biases x {N_DATASET} paired dataset IDs")


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
