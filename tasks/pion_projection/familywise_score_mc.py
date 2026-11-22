"""Pre-registered synthetic calibration for family-wise paired risk scores.

All Monte Carlo units are independent synthetic datasets. This is a method
diagnostic; it does not modify the production score or validate a physical
anchor.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import platform
import sys
from pathlib import Path

import numpy as np
from scipy.stats import beta, t

OUT = Path("results/pion_projection/familywise_score_cpu_20261120_v1")
SCENARIOS = (
    "gaussian_null",
    "one_candidate_improved",
    "heavy_tail_null",
    "one_dataset_outlier_null",
    "near_zero_baseline",
    "reference_window_conflict",
    "common_bias_null",
)
METHODS = (
    "absolute_pointwise_t",
    "absolute_bonferroni_t",
    "absolute_max_t_bootstrap",
    "relative_pointwise_t",
    "relative_bonferroni_t",
    "relative_max_t_bootstrap",
)
METHOD_LABELS = {
    "absolute_pointwise_t": "Abs pointwise t",
    "absolute_bonferroni_t": "Abs Bonferroni",
    "absolute_max_t_bootstrap": "Abs max-t",
    "relative_pointwise_t": "Log-ratio pointwise t",
    "relative_bonferroni_t": "Log-ratio Bonferroni",
    "relative_max_t_bootstrap": "Log-ratio max-t",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_hash(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def protocol():
    return {
        "schema": "pion-familywise-score-mc-v1",
        "classification": "synthetic CPU method calibration; not a physical score",
        "independent_datasets_per_trial": 30,
        "outer_trials_per_scenario": 2500,
        "candidates": ["A", "B", "C", "D"],
        "frozen_branches": [
            "short/single-state", "short/two-state",
            "wide/single-state", "wide/two-state",
        ],
        "family_size": 16,
        "alpha_family": 0.05,
        "minimum_relative_improvement": 0.05,
        "minimum_log_improvement": math.log(1.05),
        "minimum_absolute_improvement": "0.05 * protocol baseline scale",
        "relative_score_abstain_rule": "abstain when median paired baseline risk across all datasets and branches is <= 0.05",
        "baseline_scales": {"ordinary": 1.0, "near_zero": 0.01},
        "additive_risk_noise_fraction": 0.10,
        "risk_error_correlation_design": {
            "paired_component_variance_fraction": 0.25,
            "candidate_common_variance_fraction": 0.25,
            "candidate_specific_variance_fraction": 0.35,
            "branch_specific_variance_fraction": 0.15,
            "baseline_branch_variance_fraction": 0.75,
        },
        "max_t_bootstrap": {
            "method": "Rademacher multiplier bootstrap over independent datasets",
            "multipliers_per_trial": 399,
            "seed_offset": 919,
            "quantile": "higher empirical 0.95 quantile of max positive studentized statistic over all 16 branches",
        },
        "pointwise_method": "one-sided Student t lower bound at alpha=0.05 for each of 16 branches; candidate passes only if all four branch lower bounds exceed the frozen threshold",
        "bonferroni_method": "one-sided Student t lower bounds at alpha=0.05/16 for each branch; candidate passes only if all four branch lower bounds exceed the frozen threshold",
        "max_t_method": "one-sided simultaneous lower bounds using the 0.95 max-t multiplier-bootstrap critical value over all candidate/branch contrasts",
        "metrics": {
            "absolute": "dataset-level paired baseline risk minus candidate risk; threshold is 5% of the scenario baseline scale",
            "relative": "dataset-level log(baseline risk / candidate risk); threshold is log(1.05), subject to the frozen low-baseline abstain rule",
        },
        "stress_scenarios": {
            "gaussian_null": "all candidates have zero improvement; additive Gaussian risk errors with positive risks",
            "one_candidate_improved": "candidate A has log improvement 0.22 on every branch; B-D are null",
            "heavy_tail_null": "all candidates null; standardized Student-t(3) risk errors clipped at 3.5 SD to preserve positive risks",
            "one_dataset_outlier_null": "all candidates physically null; one randomly selected candidate has one dataset with candidate risk multiplied by exp(-8) on all branches",
            "near_zero_baseline": "baseline scale 0.01; candidate A true log improvement 0.22; relative methods must abstain under the 0.05 risk floor",
            "reference_window_conflict": "candidate A branch effects are [0.22, 0.22, -0.12, -0.12]; no candidate is robust across all frozen branches",
            "common_bias_null": "physical effects are zero, but every observed candidate risk is shifted to mimic log improvement 0.22; statistical procedures cannot identify this unmeasured common bias",
        },
        "seed": 20261120,
        "scenario_order": list(SCENARIOS),
        "outputs": [
            "dataset_risks_<scenario>.npz",
            "trial_outcomes.csv.gz",
            "familywise_score_summary.json",
            "familywise_calibration.png",
            "abstention_bias_diagnostics.png",
            "README.md",
        ],
        "interpretation_limits": [
            "Each outer trial contains 30 independent synthetic datasets; within-dataset branches are correlated and are not counted as independent MC units.",
            "Bonferroni and max-t bounds target simultaneous coverage of all 16 branch contrasts; pointwise bounds do not adjust the family.",
            "Clopper-Pearson intervals describe repeated synthetic trial events, not physical coverage.",
            "A common bias shared by all candidates and branches is not identified by statistical multiplicity correction; it needs an independent anchor or external validity check.",
            "A fixed scale-relative absolute threshold is only a controlled illustration; a production analysis needs a physically meaningful absolute margin fixed before looking at data.",
            "The heavy-tail clipping and one-dataset outlier are explicit stress models, not claims about the actual correlator noise law.",
            "Under the Gaussian null, absolute paired risk differences are exactly normal by construction; log-ratio contrasts are close to normal at the frozen 10% noise level but retain the exact risk transformation.",
        ],
    }


def _cp_interval(successes: int, trials: int, confidence: float = 0.95):
    tail = (1.0 - confidence) / 2.0
    lower = 0.0 if successes == 0 else float(beta.ppf(tail, successes, trials - successes + 1))
    upper = 1.0 if successes == trials else float(beta.ppf(1.0 - tail, successes + 1, trials - successes))
    return [lower, upper]


def _rate(values):
    vals = [bool(x) for x in values]
    count, n = sum(vals), len(vals)
    return {"count": int(count), "n": n, "rate": count / n if n else None,
            "cp95": _cp_interval(int(count), n) if n else [None, None]}


def _effects(scenario: str):
    physical = np.zeros((4, 4), dtype=float)
    observed = physical.copy()
    scale = 1.0
    heavy_tail = False
    outlier = False
    if scenario == "one_candidate_improved":
        physical[0, :] = 0.22
        observed[:] = physical
    elif scenario == "heavy_tail_null":
        heavy_tail = True
    elif scenario == "one_dataset_outlier_null":
        outlier = True
    elif scenario == "near_zero_baseline":
        scale = 0.01
        physical[0, :] = 0.22
        observed[:] = physical
    elif scenario == "reference_window_conflict":
        physical[0, :] = [0.22, 0.22, -0.12, -0.12]
        observed[:] = physical
    elif scenario == "common_bias_null":
        observed[:] = 0.22
    elif scenario != "gaussian_null":
        raise ValueError(f"unknown scenario: {scenario}")
    return physical, observed, scale, heavy_tail, outlier


def _noise(rng, trials, n, *, heavy_tail):
    candidates, branches = 4, 4
    paired = rng.normal(size=(trials, n, 1, 1))
    base_branch = rng.normal(size=(trials, n, 1, branches))
    cand_common = rng.normal(size=(trials, n, 1, 1))
    cand_specific = rng.normal(size=(trials, n, candidates, 1))
    cand_branch = rng.normal(size=(trials, n, candidates, branches))

    base = math.sqrt(0.25) * paired + math.sqrt(0.75) * base_branch
    cand = (math.sqrt(0.25) * paired + math.sqrt(0.25) * cand_common
            + math.sqrt(0.35) * cand_specific + math.sqrt(0.15) * cand_branch)
    if heavy_tail:
        df, clip = 3, 3.5
        multiplier = np.sqrt((df - 2.0) / rng.chisquare(df, size=(trials, n, 1, 1)))
        base = np.clip(base * multiplier, -clip, clip)
        cand = np.clip(cand * multiplier, -clip, clip)
    return base[:, :, 0, :], cand


def _generate_risks(rng, scenario, trials, n, noise_fraction):
    physical, observed, scale, heavy_tail, outlier = _effects(scenario)
    base_noise, cand_noise = _noise(rng, trials, n, heavy_tail=heavy_tail)
    baseline = scale * (1.0 + noise_fraction * base_noise)
    candidate = scale * np.exp(-observed[None, None, :, :]) * (1.0 + noise_fraction * cand_noise)
    if outlier:
        for trial in range(trials):
            c = int(rng.integers(0, 4))
            row = int(rng.integers(0, n))
            candidate[trial, row, c, :] *= math.exp(-8.0)
    truth = {
        "physical_effects": physical.tolist(),
        "observed_effects": observed.tolist(),
        "robust_candidate_truth": [bool(float(np.min(row)) > math.log(1.05)) for row in physical],
        "baseline_scale": scale,
        "outlier_injected_per_trial": bool(outlier),
        "heavy_tail": bool(heavy_tail),
    }
    return baseline, candidate, truth


def _max_t_critical(x, multipliers, alpha, chunk_size=50):
    trials, n, m = x.shape
    critical = np.empty(trials, dtype=float)
    for first in range(0, trials, chunk_size):
        last = min(first + chunk_size, trials)
        part = x[first:last]
        means = np.mean(part, axis=1)
        centered = part - means[:, None, :]
        sd = np.std(part, axis=1, ddof=1)
        denom = np.maximum(sd * math.sqrt(n), np.finfo(float).tiny)
        boot = np.einsum("kn,tnm->tkm", multipliers, centered, optimize=True) / denom[:, None, :]
        maxima = np.max(boot, axis=2)
        critical[first:last] = np.quantile(maxima, 1.0 - alpha, axis=1, method="higher")
    return critical


def _evaluate_metric(x, baseline, scale, metric, multipliers, protocol_value):
    trials, n, m = x.shape
    candidates, branches = 4, 4
    alpha = float(protocol_value["alpha_family"])
    rel_floor = 0.05
    abstain = np.zeros(trials, dtype=bool)
    if metric == "relative":
        baseline_median = np.median(baseline, axis=(1, 2))
        abstain = baseline_median <= rel_floor
        threshold = math.log(1.05)
    else:
        baseline_median = np.median(baseline, axis=(1, 2))
        threshold = 0.05 * scale

    sd = np.std(x, axis=1, ddof=1)
    se = np.maximum(sd / math.sqrt(n), np.finfo(float).tiny)
    mean = np.mean(x, axis=1)
    point_critical = float(t.ppf(1.0 - alpha, n - 1))
    bonf_critical = float(t.ppf(1.0 - alpha / m, n - 1))
    max_critical = _max_t_critical(x, multipliers, alpha)
    lowers = {
        "pointwise_t": mean - point_critical * se,
        "bonferroni_t": mean - bonf_critical * se,
        "max_t_bootstrap": mean - max_critical[:, None] * se,
    }
    results = {}
    for adjustment, lower in lowers.items():
        certified = np.all((lower > threshold).reshape(trials, candidates, branches), axis=2)
        certified[abstain, :] = False
        results[adjustment] = {
            "candidate_certified": certified,
            "abstained": abstain.copy(),
            "threshold": threshold,
            "critical_mean": float(np.mean({
                "pointwise_t": point_critical,
                "bonferroni_t": bonf_critical,
                "max_t_bootstrap": max_critical,
            }[adjustment])),
            "min_lower_bound_mean": np.min(lower.reshape(trials, candidates, branches), axis=2).mean(axis=0).tolist(),
            "baseline_median_mean": float(np.mean(baseline_median)),
        }
    return results


def _scenario_trial_results(baseline, candidate, truth, multipliers, protocol_value):
    trials, n, candidates, branches = candidate.shape
    relative = np.log(baseline[:, :, None, :]) - np.log(candidate)
    absolute = baseline[:, :, None, :] - candidate
    arrays = {
        "absolute": absolute.reshape(trials, n, candidates * branches),
        "relative": relative.reshape(trials, n, candidates * branches),
    }
    result = {}
    true_robust = np.asarray(truth["robust_candidate_truth"], dtype=bool)
    true_null = ~true_robust
    rows = []
    for metric, x in arrays.items():
        assessed = _evaluate_metric(x, baseline, truth["baseline_scale"], metric, multipliers, protocol_value)
        for adjustment, detail in assessed.items():
            name = f"{metric}_{adjustment}"
            cert = detail["candidate_certified"]
            false_family = np.any(cert[:, true_null], axis=1) if np.any(true_null) else np.zeros(trials, dtype=bool)
            true_cert = cert[:, true_robust] if np.any(true_robust) else np.empty((trials, 0), dtype=bool)
            result[name] = {
                "familywise_false_certification": _rate(false_family),
                "any_candidate_certification": _rate(np.any(cert, axis=1)),
                "abstention": _rate(detail["abstained"]),
                "true_candidate_power": {
                    f"candidate_{idx}": _rate(cert[:, idx])
                    for idx in np.flatnonzero(true_robust)
                },
                "critical_value_mean": detail["critical_mean"],
                "mean_min_branch_lower_bound_by_candidate": detail["min_lower_bound_mean"],
                "mean_baseline_median": detail["baseline_median_mean"],
                "candidate_certification_count_by_candidate": [
                    int(x) for x in np.sum(cert, axis=0)
                ],
            }
            for trial in range(trials):
                rows.append({
                    "scenario": None,
                    "trial": trial,
                    "method": name,
                    "familywise_false_certification": bool(false_family[trial]),
                    "any_candidate_certification": bool(np.any(cert[trial])),
                    "candidate_certified": "".join("1" if x else "0" for x in cert[trial]),
                    "true_candidate_certified": "".join(
                        "1" if x else "0" for x in cert[trial, true_robust]
                    ),
                    "abstained": bool(detail["abstained"][trial]),
                })
    return result, rows, arrays


def _summarize_trials(scenario_records, truths, protocol_value):
    summary = {
        "schema": "pion-familywise-score-summary-v1",
        "classification": "synthetic CPU method calibration; not physical validation",
        "design": protocol_value,
        "scenario_truth": truths,
        "scenario_results": scenario_records,
        "conclusions": [],
    }
    null = scenario_records["gaussian_null"]
    null_fwer = [null[m]["familywise_false_certification"]["rate"] for m in METHODS]
    summary["conclusions"].append(
        "Gaussian-null family-wise event rates are reported with exact Monte Carlo intervals; "
        f"the six metric/adjustment procedures range {min(null_fwer):.3f}–{max(null_fwer):.3f}."
    )
    if "one_candidate_improved" in scenario_records:
        selection = scenario_records["one_candidate_improved"]
        power = {
            m: selection[m]["true_candidate_power"].get("candidate_0", {}).get("rate")
            for m in METHODS
        }
        summary["conclusions"].append(
            "The one-improved-candidate scenario reports candidate A power separately from false certification among null candidates; "
            + "pointwise, Bonferroni, and max-t results are not pooled."
        )
    if "near_zero_baseline" in scenario_records:
        summary["conclusions"].append(
            "The relative-score methods abstain at the frozen low-baseline floor; absolute-score behavior uses a separately frozen scale-relative margin."
        )
    if "common_bias_null" in scenario_records:
        summary["conclusions"].append(
            "The common-bias scenario is a structural identifiability stress: it violates the unbiased-score model, so high certification is not a statistical calibration failure that multiplicity adjustment can fix."
        )
    return summary


def _plot(summary, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = ["#bd634e", "#d99b57", "#4d7c9f", "#8d6c9f", "#57917d", "#385f7f"]
    labels = [METHOD_LABELS[x] for x in METHODS]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2))
    scenarios = ["gaussian_null", "heavy_tail_null", "one_dataset_outlier_null"]
    short = ["Gaussian null", "Heavy-tail null", "One outlier"]
    x = np.arange(len(scenarios))
    width = 0.12
    for j, method in enumerate(METHODS):
        rates, lo, hi = [], [], []
        for scenario in scenarios:
            rec = summary["scenario_results"][scenario][method]["familywise_false_certification"]
            a, b = rec["cp95"]
            rates.append(rec["rate"])
            lo.append(rec["rate"] - a)
            hi.append(b - rec["rate"])
        axes[0].bar(x + (j - 2.5) * width, rates, width, color=colors[j],
                    yerr=np.array([lo, hi]), capsize=2, label=labels[j])
    axes[0].axhline(0.05, color="black", linestyle="--", linewidth=1, label="nominal 5%")
    axes[0].set_xticks(x, short)
    axes[0].set_ylim(0, 1.0)
    axes[0].set_ylabel("Any null candidate certified")
    axes[0].set_title("Family-wise false certification\n95% exact Monte Carlo intervals")
    axes[0].grid(axis="y", alpha=0.25)
    axes[0].legend(frameon=False, fontsize=7, ncol=2)

    selected = summary["scenario_results"]["one_candidate_improved"]
    power, p_lo, p_hi, fwer, f_lo, f_hi = [], [], [], [], [], []
    for method in METHODS:
        p = selected[method]["true_candidate_power"]["candidate_0"]
        q = selected[method]["familywise_false_certification"]
        power.append(p["rate"])
        p_lo.append(p["rate"] - p["cp95"][0])
        p_hi.append(p["cp95"][1] - p["rate"])
        fwer.append(q["rate"])
        f_lo.append(q["rate"] - q["cp95"][0])
        f_hi.append(q["cp95"][1] - q["rate"])
    xx = np.arange(len(METHODS))
    w = 0.36
    axes[1].bar(xx - w / 2, power, w, color="#4777a8", label="Power for true candidate A",
                yerr=np.array([p_lo, p_hi]), capsize=2)
    axes[1].bar(xx + w / 2, fwer, w, color="#bd634e", label="False certification among B–D",
                yerr=np.array([f_lo, f_hi]), capsize=2)
    axes[1].set_xticks(xx, labels, rotation=35, ha="right")
    axes[1].set_ylim(0, 1.0)
    axes[1].set_ylabel("Rate across independent trials")
    axes[1].set_title("One truly improved candidate\npower and partial-null FWER")
    axes[1].grid(axis="y", alpha=0.25)
    axes[1].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "familywise_calibration.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
    low = summary["scenario_results"]["near_zero_baseline"]
    x = np.arange(len(METHODS))
    abstain = [low[m]["abstention"]["rate"] for m in METHODS]
    cert = [low[m]["true_candidate_power"].get("candidate_0", {}).get("rate", 0.0) for m in METHODS]
    w = 0.38
    axes[0].bar(x - w / 2, abstain, w, color="#8d6c9f", label="Abstain")
    axes[0].bar(x + w / 2, cert, w, color="#57917d", label="Certify true A")
    axes[0].set_xticks(x, labels, rotation=55, ha="right")
    axes[0].set_ylim(0, 1.0)
    axes[0].set_title("Near-zero baseline\nrelative risk must abstain")
    axes[0].legend(frameon=False, fontsize=8)
    axes[0].grid(axis="y", alpha=0.25)

    conflict = summary["scenario_results"]["reference_window_conflict"]
    conf = [conflict[m]["any_candidate_certification"]["rate"] for m in METHODS]
    axes[1].bar(x, conf, color=colors)
    axes[1].set_xticks(x, labels, rotation=55, ha="right")
    axes[1].set_ylim(0, 1.0)
    axes[1].set_title("Window/reference conflict\nrobust certification rate")
    axes[1].grid(axis="y", alpha=0.25)

    bias = summary["scenario_results"]["common_bias_null"]
    bias_rate = [bias[m]["any_candidate_certification"]["rate"] for m in METHODS]
    axes[2].bar(x, bias_rate, color=colors)
    axes[2].set_xticks(x, labels, rotation=55, ha="right")
    axes[2].set_ylim(0, 1.0)
    axes[2].set_title("Common unmeasured bias\nphysical false-certificate rate")
    axes[2].grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(out / "abstention_bias_diagnostics.png", dpi=180)
    plt.close(fig)


def _format_rate(value):
    interval = value["cp95"]
    return f'{value["count"]}/{value["n"]}={value["rate"]:.3f} [{interval[0]:.3f}, {interval[1]:.3f}]'


def _write_readme(summary, out, provenance):
    lines = [
        "# Pion family-wise robust-score synthetic calibration",
        "",
        "This is a new, independent CPU method experiment. It does not modify the production score, does not validate the pion physical state, and does not use amendment02/amendment03 trials as independent data.",
        "",
        "## Frozen design",
        "",
        f'- {summary["design"]["outer_trials_per_scenario"]} independent outer trials per scenario; each trial contains {summary["design"]["independent_datasets_per_trial"]} independent synthetic datasets.',
        "- Four candidates are compared across four frozen branches: two fit windows times two reference models. Candidate branches are correlated within each dataset.",
        "- A robust certificate requires every branch for that candidate to clear the same frozen minimum improvement.",
        "- Compare dataset-level paired absolute risk differences and log risk ratios. For each, compare unadjusted one-sided Student-t bounds, Bonferroni bounds over all 16 candidate/branch contrasts, and a dataset-level Rademacher max-t multiplier bootstrap.",
        "- The relative method abstains when median baseline risk is at or below 0.05. The absolute margin is 5% of the predeclared scenario risk scale; this scale-relative choice is a controlled synthetic comparison, not a physical margin.",
        "- Every interval below is a 95% exact Clopper-Pearson Monte Carlo interval across outer trials. It is not a physical coverage interval.",
        "",
        "## Results",
        "",
        "| Scenario | Method | Any null candidate falsely certified | Power for each truly improved candidate | Abstain |",
        "| --- | --- | --- | --- | --- |",
    ]
    for scenario in SCENARIOS:
        for method in METHODS:
            rec = summary["scenario_results"][scenario][method]
            powers = rec["true_candidate_power"]
            power_text = ", ".join(f"{name}: {_format_rate(value)}" for name, value in powers.items()) or "not applicable"
            lines.append(
                f'| {scenario} | {METHOD_LABELS[method]} | {_format_rate(rec["familywise_false_certification"])} | {power_text} | {_format_rate(rec["abstention"])} |'
            )
    lines.extend([
        "",
        "![Family-wise false certification and partial-null power](familywise_calibration.png)",
        "",
        "![Abstention, branch conflict, and common-bias diagnostics](abstention_bias_diagnostics.png)",
        "",
        "## Interpretation",
        "",
        "The Gaussian-null table is the direct calibration check. Pointwise testing leaves the full candidate/branch family unadjusted; Bonferroni gives a conservative reference; max-t uses observed branch correlation and must be judged by its repeated-trial CP interval. The partial-null scenario reports power for candidate A separately from false certification among null candidates B–D.",
        "",
        "The heavy-tail and one-dataset-outlier scenarios are stress tests. If a mean-based rule certifies an outlier-contaminated candidate, multiplicity correction has not made the score robust to influential datasets; the next CPU method comparison should add a predeclared robust estimator such as a trimmed paired mean or Huber score, recalibrated on independent datasets.",
        "",
        "At the near-zero baseline, relative methods must abstain under the frozen risk floor. The conflict scenario checks whether a certificate survives every window/reference branch. The common-bias scenario deliberately makes all candidates look improved while the physical truth is null; no statistical correction can detect that without an independent anchor or model-validity diagnostic.",
        "",
        "The absolute threshold is proportional to the synthetic baseline scale. A production study must choose an absolute risk margin from physical units before seeing outcomes, and must use independent anchor data to test common reference bias. Until then physical_score remains null.",
        "",
        "## Reproduction and provenance",
        "",
        "Run commands: first register the frozen protocol with python -m tasks.pion_projection.familywise_score_mc --preregister, then execute python -m tasks.pion_projection.familywise_score_mc --run. Verify saved hashes and raw archive shapes with python -m tasks.pion_projection.familywise_score_mc --verify.",
        "",
        "The protocol and source hashes were frozen before simulation. Raw paired baseline/candidate risk arrays are saved in the scenario NPZ files; trial-level certification outcomes are in trial_outcomes.csv.gz. The output hashes and runtime versions are listed in execution_provenance.json.",
        "",
        f'Protocol SHA-256: {provenance["protocol_sha256"]}',
        f'Source SHA-256: {provenance["source_sha256"]}',
        "",
    ])
    (out / "README.md").write_text("\n".join(lines))


def _preregister():
    out = OUT
    if out.exists():
        raise FileExistsError(f"{out} already exists; preregistration never overwrites")
    out.mkdir(parents=True)
    p = protocol()
    (out / "protocol.json").write_text(json.dumps(p, indent=2, sort_keys=True) + "\n")
    record = {
        "protocol_sha256": _canonical_hash(p),
        "source_sha256": _sha256(Path(__file__).resolve()),
        "registered_before_simulation": True,
        "experiment_source": str(Path(__file__).resolve()),
        "created_utc_date": "2026-11-20",
        "context_hashes": {
            str(path): _sha256(path)
            for path in (
                Path("tasks/pion_projection/robust_score_diagnostic.py"),
                Path("tasks/pion_projection/experiment.py"),
                Path("core/comparator.py"),
            )
            if path.exists()
        },
        "context_hash_note": "Context hashes identify the pre-existing score implementation reviewed for this method experiment; the simulator does not import or modify these files.",
    }
    (out / "preregistration.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(f"preregistered {out}")


def _run():
    if not OUT.is_dir():
        raise FileNotFoundError(f"run --preregister first: {OUT}")
    allowed = {"protocol.json", "preregistration.json"}
    unexpected = sorted(x.name for x in OUT.iterdir() if x.name not in allowed)
    if unexpected:
        raise FileExistsError(f"output directory already contains run products: {unexpected}")
    p = json.loads((OUT / "protocol.json").read_text())
    reg = json.loads((OUT / "preregistration.json").read_text())
    if _canonical_hash(p) != reg["protocol_sha256"]:
        raise ValueError("protocol hash mismatch")
    if _sha256(Path(__file__).resolve()) != reg["source_sha256"]:
        raise ValueError("source changed after preregistration")

    n_trials = int(p["outer_trials_per_scenario"])
    n = int(p["independent_datasets_per_trial"])
    sigma = float(p["additive_risk_noise_fraction"])
    ss = np.random.SeedSequence(int(p["seed"]))
    children = ss.spawn(len(SCENARIOS) + 1)
    boot_seed = int(children[0].generate_state(1)[0]) + int(p["max_t_bootstrap"]["seed_offset"])
    boot_rng = np.random.default_rng(boot_seed)
    multipliers = boot_rng.choice(
        np.array([-1.0, 1.0]),
        size=(int(p["max_t_bootstrap"]["multipliers_per_trial"]), n),
    )

    scenario_results, truths, trial_rows = {}, {}, []
    scenario_seed_records = {}
    for index, scenario in enumerate(SCENARIOS):
        seed_value = int(children[index + 1].generate_state(1)[0])
        scenario_seed_records[scenario] = seed_value
        rng = np.random.default_rng(seed_value)
        baseline, candidate, truth = _generate_risks(rng, scenario, n_trials, n, sigma)
        truths[scenario] = truth
        np.savez_compressed(
            OUT / f"dataset_risks_{scenario}.npz",
            baseline_risk=baseline,
            candidate_risk=candidate,
            physical_effects=np.asarray(truth["physical_effects"]),
            observed_effects=np.asarray(truth["observed_effects"]),
            scenario=np.asarray(scenario),
            scenario_seed=np.asarray(seed_value, dtype=np.uint64),
        )
        result, rows, _ = _scenario_trial_results(baseline, candidate, truth, multipliers, p)
        scenario_results[scenario] = result
        for row in rows:
            row["scenario"] = scenario
        trial_rows.extend(rows)

    summary = _summarize_trials(scenario_results, truths, p)
    summary["scenario_seeds"] = scenario_seed_records
    summary["bootstrap_multiplier_seed"] = boot_seed
    (OUT / "familywise_score_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    with gzip.open(OUT / "trial_outcomes.csv.gz", "wt", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(trial_rows[0]))
        writer.writeheader()
        writer.writerows(trial_rows)
    _plot(summary, OUT)

    prov = {
        "protocol_sha256": reg["protocol_sha256"],
        "source_sha256": reg["source_sha256"],
        "preregistration_sha256": _sha256(OUT / "preregistration.json"),
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scipy": __import__("scipy").__version__,
        "scenario_seeds": scenario_seed_records,
        "bootstrap_multiplier_seed": boot_seed,
        "context_hashes": reg["context_hashes"],
        "output_sha256": {},
    }
    for path in sorted(OUT.iterdir()):
        if path.name != "execution_provenance.json" and path.is_file():
            prov["output_sha256"][path.name] = _sha256(path)
    (OUT / "execution_provenance.json").write_text(json.dumps(prov, indent=2, sort_keys=True) + "\n")
    _write_readme(summary, OUT, prov)
    prov["output_sha256"]["README.md"] = _sha256(OUT / "README.md")
    (OUT / "execution_provenance.json").write_text(json.dumps(prov, indent=2, sort_keys=True) + "\n")
    print(f"completed {OUT}")


def _verify():
    prov_path = OUT / "execution_provenance.json"
    prov = json.loads(prov_path.read_text())
    if _sha256(Path(__file__).resolve()) != prov["source_sha256"]:
        raise ValueError("current source does not match execution receipt")
    if _canonical_hash(json.loads((OUT / "protocol.json").read_text())) != prov["protocol_sha256"]:
        raise ValueError("protocol hash mismatch")
    failures = []
    for name, expected in prov["output_sha256"].items():
        path = OUT / name
        if not path.is_file() or _sha256(path) != expected:
            failures.append(name)
    for scenario in SCENARIOS:
        path = OUT / f"dataset_risks_{scenario}.npz"
        with np.load(path) as raw:
            base = raw["baseline_risk"]
            candidate = raw["candidate_risk"]
            if base.shape != (2500, 30, 4) or candidate.shape != (2500, 30, 4, 4):
                failures.append(path.name + ":shape")
            if not np.all(np.isfinite(base)) or not np.all(np.isfinite(candidate)):
                failures.append(path.name + ":finite")
    summary = json.loads((OUT / "familywise_score_summary.json").read_text())
    for scenario in SCENARIOS:
        for method in METHODS:
            rec = summary["scenario_results"][scenario][method]["any_candidate_certification"]
            if rec["n"] != 2500 or rec["count"] != int(round(rec["rate"] * rec["n"])):
                failures.append(f"{scenario}:{method}:count")
    if failures:
        raise ValueError("verification failed: " + ", ".join(failures))
    print(f"verified source/protocol/output hashes and {len(SCENARIOS)} raw scenario archives")


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preregister", action="store_true")
    group.add_argument("--run", action="store_true")
    group.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.preregister:
        _preregister()
    elif args.run:
        _run()
    else:
        _verify()


if __name__ == "__main__":
    main()
