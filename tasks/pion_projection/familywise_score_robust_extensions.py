"""Candidate-level multiplicity and robust-location score calibration."""
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

OUT = Path("results/pion_projection/familywise_score_cpu_20261120_v3")
RHOS = (0.05, 0.35, 0.65)
SCENARIOS = (
    "gaussian_boundary_null",
    "one_candidate_improved",
    "weak_candidate_improved",
    "heavy_tail_boundary_null",
    "one_dataset_outlier_boundary_null",
    "reference_window_conflict",
    "wrong_state_proxy_improvement",
    "common_bias_null",
)
METHODS = (
    "mean_iut_pointwise",
    "mean_iut_bonferroni4",
    "mean_iut_holm4",
    "mean_branch_bonferroni16",
    "mean_max_t16",
    "trimmed_iut_holm4",
    "huber_iut_holm4",
)
LABELS = {
    "mean_iut_pointwise": "Mean IUT pointwise",
    "mean_iut_bonferroni4": "Mean IUT Bonferroni-4",
    "mean_iut_holm4": "Mean IUT Holm-4",
    "mean_branch_bonferroni16": "Mean branch Bonferroni-16",
    "mean_max_t16": "Mean max-t-16",
    "trimmed_iut_holm4": "20% trimmed IUT Holm-4",
    "huber_iut_holm4": "Huber IUT Holm-4",
}


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_hash(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def protocol():
    margin = math.log(1.05)
    return {
        "schema": "pion-familywise-robust-extensions-v1",
        "classification": "synthetic CPU method calibration; not a production or physical score",
        "independent_datasets_per_trial": 30,
        "outer_trials_per_cell": 2500,
        "candidates": ["A", "B", "C", "D"],
        "branches": [
            "short/single-state", "short/two-state",
            "wide/single-state", "wide/two-state",
        ],
        "family_alpha": 0.05,
        "minimum_log_improvement": margin,
        "candidate_common_noise_correlations": list(RHOS),
        "within_candidate_branch_correlation": "rho_candidate_common + 0.25",
        "noise_design": {
            "log_improvement_noise_sigma": 0.10,
            "candidate_common_variance": 0.25,
            "branch_specific_variance": "0.75 - rho_candidate_common",
            "shared_family_variance": "rho_candidate_common",
            "heavy_tail": "standardized multivariate t(3) scale mixture, clipped at +/-3.5 SD",
            "outlier": "one randomly selected candidate and independent dataset receives +8 log-risk-improvement units on all four branches",
        },
        "estimators": {
            "mean": "arithmetic mean of paired dataset-level log risk improvements",
            "trimmed": "20% symmetric trimmed mean; n=30, trim 6 observations at each tail; Yuen winsorized standard error",
            "huber": "Huber M-location, tuning c=1.345, scale=1.4826*MAD; sandwich standard error from psi and psi-prime",
        },
        "candidate_level_inference": {
            "robust_candidate_p": "maximum of four branch-wise one-sided p-values (intersection-union test)",
            "pointwise": "candidate p <= alpha; no correction across four candidates",
            "bonferroni4": "candidate p <= alpha/4",
            "holm4": "Holm step-down over the four candidate-level intersection-union p-values",
            "branch_bonferroni16": "each of 16 branch p-values <= alpha/16; candidate passes only if all four branches pass",
            "max_t16": "Rademacher multiplier max-t critical value over all 16 mean contrasts, resampling independent dataset rows jointly",
        },
        "robust_methods": "Trimmed and Huber branch p-values use their predeclared robust sandwich/Yuen standard errors with one-sided t reference; empirical outer-trial calibration is reported and no asymptotic validity is assumed.",
        "bootstrap": {
            "multipliers": 399,
            "seed_offset": 919,
            "quantile": "higher empirical 95th percentile of maximum studentized multiplier mean",
        },
        "scenario_definitions": {
            "gaussian_boundary_null": "all 16 physical log effects equal log(1.05), the least-favorable boundary for requiring improvement strictly above 5%",
            "one_candidate_improved": "candidate A has log effect 0.10 on all branches; B-D are at the null boundary",
            "weak_candidate_improved": "candidate A has log effect 0.06 on all branches; B-D are at the null boundary",
            "heavy_tail_boundary_null": "all candidates are at the null boundary under clipped standardized t(3) noise",
            "one_dataset_outlier_boundary_null": "all candidates are at the null boundary; one candidate/dataset has +8 log-improvement contamination",
            "reference_window_conflict": "candidate A has [0.10, 0.10, -0.12, -0.12]; B-D are at the null boundary",
            "wrong_state_proxy_improvement": "ground-state physical effects are zero; candidate A has an apparent +0.22 improvement only in the wrong-state proxy",
            "common_bias_null": "physical log effects are zero, but every observed branch is shifted to +0.22",
        },
        "seed": 20261121,
        "rho_order": list(RHOS),
        "scenario_order": list(SCENARIOS),
        "mc_precision_target": "2500 outer trials per cell; report exact two-sided 95% Clopper-Pearson intervals for all family-wise events and power",
        "limitations": [
            "This is a synthetic estimator/inference comparison and cannot validate the physical state or common reference bias.",
            "The max-t multiplier bootstrap is approximate and is judged by empirical outer-trial rates.",
            "Candidate-level Holm/Bonferroni treats each candidate claim as an intersection-union test across its four frozen branches.",
            "The robust-estimator p-values use approximate sandwich/Yuen standard errors; calibration results apply only to these declared data-generating processes.",
            "All six scenarios share the declared rho design; they do not span every possible candidate dependence or correlator noise process.",
        ],
    }


def _cp(successes, n):
    tail = 0.025
    lo = 0.0 if successes == 0 else float(beta.ppf(tail, successes, n - successes + 1))
    hi = 1.0 if successes == n else float(beta.ppf(1.0 - tail, successes + 1, n - successes))
    return [lo, hi]


def _rate(values):
    values = np.asarray(values, dtype=bool)
    count, n = int(values.sum()), int(values.size)
    return {"count": count, "n": n, "rate": count / n, "cp95": _cp(count, n)}


def _scenario_truth(name):
    margin = math.log(1.05)
    physical = np.full((4, 4), margin)
    observed = physical.copy()
    heavy, outlier = False, False
    if name == "one_candidate_improved":
        physical[0, :] = 0.10
        observed[:] = physical
    elif name == "weak_candidate_improved":
        physical[0, :] = 0.06
        observed[:] = physical
    elif name == "heavy_tail_boundary_null":
        heavy = True
    elif name == "one_dataset_outlier_boundary_null":
        outlier = True
    elif name == "reference_window_conflict":
        physical[0, :] = [0.10, 0.10, -0.12, -0.12]
        observed[:] = physical
    elif name == "wrong_state_proxy_improvement":
        physical[:] = 0.0
        observed[:] = 0.0
        observed[0, :] = 0.22
    elif name == "common_bias_null":
        physical[:] = 0.0
        observed[:] = 0.22
    elif name != "gaussian_boundary_null":
        raise ValueError(f"unknown scenario {name}")
    robust_truth = np.min(physical, axis=1) > margin
    return physical, observed, robust_truth, heavy, outlier


def _generate(rng, rho, name, trials, n):
    physical, observed, robust_truth, heavy, outlier = _scenario_truth(name)
    candidates, branches = 4, 4
    shared = rng.normal(size=(trials, n, 1, 1))
    candidate = rng.normal(size=(trials, n, candidates, 1))
    branch = rng.normal(size=(trials, n, candidates, branches))
    noise = (math.sqrt(rho) * shared + math.sqrt(0.25) * candidate
             + math.sqrt(0.75 - rho) * branch)
    if heavy:
        multiplier = np.sqrt((3.0 - 2.0) / rng.chisquare(3.0, size=(trials, n, 1, 1)))
        noise = np.clip(noise * multiplier, -3.5, 3.5)
    values = observed[None, None, :, :] + 0.10 * noise
    if outlier:
        for trial in range(trials):
            cand = int(rng.integers(0, candidates))
            row = int(rng.integers(0, n))
            values[trial, row, cand, :] += 8.0
    return values, {
        "physical_effects": physical.tolist(),
        "observed_effects": observed.tolist(),
        "robust_candidate_truth": robust_truth.tolist(),
        "heavy_tail": heavy,
        "outlier": outlier,
        "rho_candidate_common": rho,
    }


def _pvalues_mean(x, delta):
    n = x.shape[1]
    mean = np.mean(x, axis=1)
    sd = np.std(x, axis=1, ddof=1)
    se = np.maximum(sd / math.sqrt(n), np.finfo(float).tiny)
    return t.sf((mean - delta) / se, df=n - 1), mean, se


def _pvalues_trimmed(x, delta):
    n = x.shape[1]
    g = int(math.floor(0.20 * n))
    ordered = np.sort(x, axis=1)
    kept = ordered[:, g:n - g, :]
    estimate = np.mean(kept, axis=1)
    lower = ordered[:, g, :]
    upper = ordered[:, n - g - 1, :]
    winsor = np.clip(x, lower[:, None, :], upper[:, None, :])
    winsor_sd = np.std(winsor, axis=1, ddof=1)
    h = n - 2 * g
    se = winsor_sd * math.sqrt((n - 1) / (h * (h - 1)))
    se = np.maximum(se, np.finfo(float).tiny)
    return t.sf((estimate - delta) / se, df=h - 1), estimate, se


def _huber_location(x, c=1.345):
    n = x.shape[1]
    median = np.median(x, axis=1)
    scale = 1.4826 * np.median(np.abs(x - median[:, None, :]), axis=1)
    scale = np.maximum(scale, 1e-10)
    location = median.copy()
    for _ in range(30):
        standardized = (x - location[:, None, :]) / scale[:, None, :]
        weights = np.minimum(1.0, c / np.maximum(np.abs(standardized), 1e-12))
        updated = np.sum(weights * x, axis=1) / np.sum(weights, axis=1)
        if float(np.max(np.abs(updated - location))) < 1e-10:
            location = updated
            break
        location = updated
    standardized = (x - location[:, None, :]) / scale[:, None, :]
    psi = np.clip(standardized, -c, c)
    psi_prime = np.mean(np.abs(standardized) < c, axis=1)
    variance_psi = np.mean((psi - np.mean(psi, axis=1, keepdims=True)) ** 2, axis=1)
    se = scale * np.sqrt(np.maximum(variance_psi, 0.0) / n) / np.maximum(psi_prime, 1e-8)
    return location, np.maximum(se, np.finfo(float).tiny)


def _max_t_critical(x, multipliers, alpha=0.05, chunk=40):
    trials, n, m = x.shape
    critical = np.empty(trials)
    for start in range(0, trials, chunk):
        stop = min(start + chunk, trials)
        part = x[start:stop]
        centered = part - np.mean(part, axis=1, keepdims=True)
        sd = np.std(part, axis=1, ddof=1)
        denominator = np.maximum(sd * math.sqrt(n), np.finfo(float).tiny)
        boot = np.einsum("kn,tnm->tkm", multipliers, centered, optimize=True)
        maxima = np.max(boot / denominator[:, None, :], axis=2)
        critical[start:stop] = np.quantile(maxima, 1 - alpha, axis=1, method="higher")
    return critical


def _holm(candidate_p, alpha=0.05):
    trials, candidates = candidate_p.shape
    order = np.argsort(candidate_p, axis=1)
    rows = np.arange(trials)
    rejected = np.zeros((trials, candidates), dtype=bool)
    active = np.ones(trials, dtype=bool)
    for rank in range(candidates):
        chosen = order[:, rank]
        pvalue = candidate_p[rows, chosen]
        passes = pvalue <= alpha / (candidates - rank)
        select = active & passes
        rejected[rows[select], chosen[select]] = True
        active &= passes
    return rejected


def _candidate_flags(branch_p, alpha=0.05):
    trials, candidates, branches = branch_p.shape
    candidate_p = np.max(branch_p, axis=2)
    return {
        "mean_iut_pointwise": candidate_p <= alpha,
        "mean_iut_bonferroni4": candidate_p <= alpha / candidates,
        "mean_iut_holm4": _holm(candidate_p, alpha),
        "mean_branch_bonferroni16": np.all(
            branch_p <= alpha / (candidates * branches), axis=2
        ),
    }


def _evaluate(values, truth, multipliers, protocol_value):
    trials, n, candidates, branches = values.shape
    delta = float(protocol_value["minimum_log_improvement"])
    x = values.reshape(trials, n, candidates * branches)
    mean_p, mean, mean_se = _pvalues_mean(x, delta)
    flags = _candidate_flags(mean_p.reshape(trials, candidates, branches))
    critical = _max_t_critical(x, multipliers)
    max_t_pass = (mean - critical[:, None] * mean_se > delta).reshape(
        trials, candidates, branches
    )
    flags["mean_max_t16"] = np.all(max_t_pass, axis=2)

    trimmed_p, _, _ = _pvalues_trimmed(x, delta)
    flags["trimmed_iut_holm4"] = _holm(
        np.max(trimmed_p.reshape(trials, candidates, branches), axis=2)
    )

    huber_estimate, huber_se = _huber_location(x)
    huber_p = t.sf((huber_estimate - delta) / huber_se, df=n - 1)
    flags["huber_iut_holm4"] = _holm(
        np.max(huber_p.reshape(trials, candidates, branches), axis=2)
    )

    robust_truth = np.asarray(truth["robust_candidate_truth"], dtype=bool)
    null_mask = ~robust_truth
    result, rows = {}, []
    for method in METHODS:
        certified = flags[method]
        false_family = (np.any(certified[:, null_mask], axis=1)
                        if np.any(null_mask) else np.zeros(trials, dtype=bool))
        power = {
            f"candidate_{idx}": _rate(certified[:, idx])
            for idx in np.flatnonzero(robust_truth)
        }
        result[method] = {
            "familywise_false_certification": _rate(false_family),
            "any_candidate_certification": _rate(np.any(certified, axis=1)),
            "true_candidate_power": power,
            "certified_by_candidate": [int(v) for v in certified.sum(axis=0)],
            "abstention": _rate(np.zeros(trials, dtype=bool)),
        }
        for trial in range(trials):
            rows.append({
                "trial": trial,
                "method": method,
                "familywise_false_certification": int(false_family[trial]),
                "any_candidate_certification": int(np.any(certified[trial])),
                "candidate_mask": "".join("1" if v else "0" for v in certified[trial]),
                "true_robust_candidate_mask": "".join(
                    "1" if v else "0" for v in certified[trial, robust_truth]
                ),
            })
    return result, rows


def _write_plots(summary, root):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = ["#bd634e", "#d99b57", "#4d7c9f", "#8d6c9f", "#57917d", "#385f7f", "#bd9b4e"]
    rho_labels = [f"{x:.2f}" for x in RHOS]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    panels = [
        ("gaussian_boundary_null", "Gaussian least-favorable boundary"),
        ("one_dataset_outlier_boundary_null", "One outlier at boundary"),
    ]
    x = np.arange(len(RHOS))
    for ax, (scenario, title) in zip(axes, panels):
        for color, method in zip(colors, METHODS):
            rate, lo, hi = [], [], []
            for rho in RHOS:
                rec = summary["scenario_results"][f"rho_{rho:.2f}"][scenario][method]["familywise_false_certification"]
                low, high = rec["cp95"]
                rate.append(rec["rate"])
                lo.append(rec["rate"] - low)
                hi.append(high - rec["rate"])
            ax.errorbar(x, rate, yerr=np.array([lo, hi]), marker="o", capsize=2,
                        color=color, label=LABELS[method])
        ax.axhline(0.05, color="black", linestyle="--", linewidth=1, label="Nominal 5%")
        ax.set_xticks(x, rho_labels)
        ax.set_ylim(0, 0.08)
        ax.set_xlabel("Candidate-level common correlation")
        ax.set_ylabel("Any null candidate falsely certified")
        ax.set_title(title)
        ax.grid(alpha=0.25)
    axes[1].legend(frameon=False, fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(root / "correlation_fwer_diagnostics.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    scenario_titles = [
        ("one_candidate_improved", "10% true effect"),
        ("weak_candidate_improved", "6% true effect"),
    ]
    x = np.arange(len(METHODS))
    width = 0.23
    for ax, (scenario, title) in zip(axes, scenario_titles):
        for r_idx, (rho, color) in enumerate(zip(RHOS, ("#4777a8", "#57917d", "#bd634e"))):
            values, lo, hi = [], [], []
            for method in METHODS:
                rec = summary["scenario_results"][f"rho_{rho:.2f}"][scenario][method]["true_candidate_power"]["candidate_0"]
                values.append(rec["rate"])
                lo.append(rec["rate"] - rec["cp95"][0])
                hi.append(rec["cp95"][1] - rec["rate"])
            ax.bar(x + (r_idx - 1) * width, values, width, yerr=np.array([lo, hi]),
                   capsize=2, color=color, label=f"rho={rho:.2f}")
        ax.set_xticks(x, [LABELS[m] for m in METHODS], rotation=55, ha="right")
        ax.set_ylim(0, 1.0)
        ax.set_ylabel("True candidate A certification rate")
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.25)
    axes[1].legend(frameon=False)
    fig.tight_layout()
    fig.savefig(root / "robust_estimator_power.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 5.2))
    rho_key = "rho_0.35"
    structural = (
        ("reference_window_conflict", "Window conflict"),
        ("wrong_state_proxy_improvement", "Wrong-state proxy"),
        ("common_bias_null", "Common bias"),
    )
    x = np.arange(len(structural))
    width = 0.11
    for j, method in enumerate(METHODS):
        rates, lo, hi = [], [], []
        for scenario, _ in structural:
            rec = summary["scenario_results"][rho_key][scenario][method]["any_candidate_certification"]
            rates.append(rec["rate"])
            lo.append(rec["rate"] - rec["cp95"][0])
            hi.append(rec["cp95"][1] - rec["rate"])
        ax.bar(x + (j - 3) * width, rates, width, yerr=np.array([lo, hi]),
               capsize=2, color=colors[j], label=LABELS[method])
    ax.set_xticks(x, [label for _, label in structural])
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Any candidate certified although no physical improvement is true")
    ax.set_title("Structural negative controls at candidate correlation 0.35")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False, fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(root / "structural_negative_controls.png", dpi=180)
    plt.close(fig)


def _write_readme(summary, root, provenance):
    lines = [
        "# Pion family-wise robust-score extensions",
        "",
        "This independently pre-registered CPU experiment extends v2. It compares candidate-level intersection-union inference, Holm/Bonferroni selection correction, candidate-correlation sensitivity, and robust paired estimators. It does not modify the production score or validate a physical anchor.",
        "",
        "## Frozen design and candidate inference",
        "",
        "- Each cell uses 2500 outer trials; each trial contains 30 independent synthetic dataset-level paired log-risk improvements for 4 candidates and 4 frozen window/reference branches.",
        "- Candidate common correlations are 0.05, 0.35, and 0.65. All primary null effects are exactly log(1.05), the boundary of the requirement to exceed a 5% improvement.",
        "- For each candidate, the intersection-union p-value is the maximum of the four branch p-values. Compare no candidate-family correction, Bonferroni-4, Holm-4, branch Bonferroni-16, and max-t-16.",
        "- Compare the arithmetic mean with a 20% trimmed mean and a Huber M-location. Robust methods use predeclared approximate Yuen/sandwich standard errors; their empirical size and power are measured by the outer simulation.",
        "- All event-rate intervals are exact 95% Clopper-Pearson Monte Carlo intervals. Independent datasets, not branches, are the sampling units.",
        "",
        "## Boundary error and candidate dependence",
        "",
        "| Candidate correlation | Scenario | Method | Family-wise false certification |",
        "| ---: | --- | --- | --- |",
    ]
    for rho in RHOS:
        for scenario in ("gaussian_boundary_null", "heavy_tail_boundary_null", "one_dataset_outlier_boundary_null"):
            for method in METHODS:
                rec = summary["scenario_results"][f"rho_{rho:.2f}"][scenario][method]["familywise_false_certification"]
                lines.append(
                    f'| {rho:.2f} | {scenario} | {LABELS[method]} | {rec["count"]}/{rec["n"]}={rec["rate"]:.3f} [{rec["cp95"][0]:.3f}, {rec["cp95"][1]:.3f}] |'
                )
    lines.extend([
        "",
        "![Boundary family-wise error versus candidate correlation](correlation_fwer_diagnostics.png)",
        "",
        "## Power and robust estimators",
        "",
        "| Candidate correlation | True effect | Method | Candidate A power | Null-candidate FWER |",
        "| ---: | --- | --- | --- | --- |",
    ])
    for rho in RHOS:
        for scenario in ("one_candidate_improved", "weak_candidate_improved"):
            for method in METHODS:
                rec = summary["scenario_results"][f"rho_{rho:.2f}"][scenario][method]
                power = rec["true_candidate_power"]["candidate_0"]
                fwer = rec["familywise_false_certification"]
                lines.append(
                    f'| {rho:.2f} | {scenario} | {LABELS[method]} | {power["count"]}/{power["n"]}={power["rate"]:.3f} [{power["cp95"][0]:.3f}, {power["cp95"][1]:.3f}] | {fwer["count"]}/{fwer["n"]}={fwer["rate"]:.3f} [{fwer["cp95"][0]:.3f}, {fwer["cp95"][1]:.3f}] |'
                )
    lines.extend([
        "",
        "![Certification power for 10% and 6% effects](robust_estimator_power.png)",
        "",
        "## Wrong-state and shared-bias controls",
        "",
        "At rho=0.35, the wrong-state scenario gives candidate A a strong apparent risk improvement while its ground-state physical effect remains null. The common-bias scenario shifts every candidate together. These controls distinguish candidate-specific proxy failure from a shared reference shift; neither can be resolved by a risk-only score without an independent state/anchor check.",
        "",
        "| Scenario at rho=0.35 | Method | Any physically null candidate certified |",
        "| --- | --- | --- |",
    ])
    for scenario in ("reference_window_conflict", "wrong_state_proxy_improvement", "common_bias_null"):
        for method in METHODS:
            rec = summary["scenario_results"]["rho_0.35"][scenario][method]["any_candidate_certification"]
            lines.append(
                f'| {scenario} | {LABELS[method]} | {rec["count"]}/{rec["n"]}={rec["rate"]:.3f} [{rec["cp95"][0]:.3f}, {rec["cp95"][1]:.3f}] |'
            )
    lines.extend([
        "",
        "![Window conflict, wrong-state proxy, and common-bias controls](structural_negative_controls.png)",
        "",
        "## Interpretation and limits",
        "",
        "Read Holm/Bonferroni-4 as correction over candidate-level intersection-union claims; branch Bonferroni-16 is more conservative because it corrects every branch as a separate claim. The max-t line uses the empirical covariance of all 16 mean contrasts. Selection rates can move with candidate correlation, so one covariance setting cannot support a general FWER claim.",
        "",
        "The outlier and heavy-tail rows show whether trimming/Huber reduces false certification while preserving power. The reference-window conflict requires all four branches to pass, so a robust candidate should not be certified. The common-bias case is intentionally unidentifiable statistically: methods may certify a biased score, which still requires an independent physical anchor.",
        "",
        "This synthetic experiment tests estimator and multiplicity behavior only. It does not resolve wrong-state contamination, physical calibration, or correlated correlator noise in the archive. See scenario-specific outcomes in familywise_score_summary.json and trial_outcomes.csv.gz.",
        "",
        "## Reproduction and provenance",
        "",
        "Register with python -B -m tasks.pion_projection.familywise_score_robust_extensions --preregister, execute with --run, and verify hashes with --verify. The exact source/protocol/output hashes are in execution_provenance.json.",
        f'Protocol SHA-256: {provenance["protocol_sha256"]}',
        f'Source SHA-256: {provenance["source_sha256"]}',
        "",
    ])
    (root / "README.md").write_text("\n".join(lines))


def _preregister():
    if OUT.exists():
        raise FileExistsError(f"{OUT} exists; preregistration does not overwrite")
    OUT.mkdir(parents=True)
    p = protocol()
    (OUT / "protocol.json").write_text(json.dumps(p, indent=2, sort_keys=True) + "\n")
    context = [
        Path("tasks/pion_projection/familywise_score_mc_v2.py"),
        Path("tasks/pion_projection/robust_score_diagnostic.py"),
    ]
    record = {
        "protocol_sha256": _canonical_hash(p),
        "source_sha256": _sha256(Path(__file__).resolve()),
        "registered_before_simulation": True,
        "registered_on": "2026-11-20",
        "context_hashes": {str(p): _sha256(p) for p in context if p.exists()},
        "context_note": "Context sources informed score-method selection; this experiment uses an independent synthetic paired-log-risk generator.",
    }
    (OUT / "preregistration.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(f"preregistered {OUT}")


def _run():
    if not OUT.is_dir():
        raise FileNotFoundError("run --preregister first")
    allowed = {"protocol.json", "preregistration.json"}
    extra = [p.name for p in OUT.iterdir() if p.name not in allowed]
    if extra:
        raise FileExistsError(f"output directory already contains products: {extra}")
    p = json.loads((OUT / "protocol.json").read_text())
    reg = json.loads((OUT / "preregistration.json").read_text())
    if _canonical_hash(p) != reg["protocol_sha256"]:
        raise ValueError("protocol changed after registration")
    if _sha256(Path(__file__).resolve()) != reg["source_sha256"]:
        raise ValueError("source changed after registration")
    trials = int(p["outer_trials_per_cell"])
    n = int(p["independent_datasets_per_trial"])
    ss = np.random.SeedSequence(int(p["seed"]))
    children = ss.spawn(1 + len(RHOS) * len(SCENARIOS))
    boot_seed = int(children[0].generate_state(1)[0]) + int(p["bootstrap"]["seed_offset"])
    boot_rng = np.random.default_rng(boot_seed)
    multipliers = boot_rng.choice([-1.0, 1.0], size=(int(p["bootstrap"]["multipliers"]), n))

    records, truths, rows, seeds = {}, {}, [], {}
    cell_index = 0
    for rho in RHOS:
        rho_key = f"rho_{rho:.2f}"
        records[rho_key] = {}
        for scenario in SCENARIOS:
            seed_value = int(children[1 + cell_index].generate_state(1)[0])
            cell_index += 1
            seeds[f"{rho_key}/{scenario}"] = seed_value
            rng = np.random.default_rng(seed_value)
            values, truth = _generate(rng, rho, scenario, trials, n)
            result, cell_rows = _evaluate(values, truth, multipliers, p)
            records[rho_key][scenario] = result
            truths[f"{rho_key}/{scenario}"] = truth
            for row in cell_rows:
                row["rho"] = rho
                row["scenario"] = scenario
            rows.extend(cell_rows)

    summary = {
        "schema": "pion-familywise-robust-extensions-summary-v1",
        "classification": "synthetic CPU calibration; not physical validation",
        "design": p,
        "scenario_truth": truths,
        "scenario_results": records,
        "cell_seeds": seeds,
        "bootstrap_seed": boot_seed,
    }
    (OUT / "familywise_score_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    with gzip.open(OUT / "trial_outcomes.csv.gz", "wt", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    _write_plots(summary, OUT)
    prov = {
        "protocol_sha256": reg["protocol_sha256"],
        "source_sha256": reg["source_sha256"],
        "preregistration_sha256": _sha256(OUT / "preregistration.json"),
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scipy": __import__("scipy").__version__,
        "cell_seeds": seeds,
        "bootstrap_seed": boot_seed,
        "context_hashes": reg["context_hashes"],
        "output_sha256": {},
    }
    for path in sorted(OUT.iterdir()):
        if path.is_file():
            prov["output_sha256"][path.name] = _sha256(path)
    _write_readme(summary, OUT, prov)
    prov["output_sha256"]["README.md"] = _sha256(OUT / "README.md")
    (OUT / "execution_provenance.json").write_text(json.dumps(prov, indent=2, sort_keys=True) + "\n")
    print(f"completed {OUT}")


def _verify():
    prov = json.loads((OUT / "execution_provenance.json").read_text())
    if _sha256(Path(__file__).resolve()) != prov["source_sha256"]:
        raise ValueError("current source does not match execution receipt")
    if _canonical_hash(json.loads((OUT / "protocol.json").read_text())) != prov["protocol_sha256"]:
        raise ValueError("protocol hash mismatch")
    failures = []
    for name, expected in prov["output_sha256"].items():
        path = OUT / name
        if not path.is_file() or _sha256(path) != expected:
            failures.append(name)
    summary = json.loads((OUT / "familywise_score_summary.json").read_text())
    expected_trials = int(summary["design"]["outer_trials_per_cell"])
    for rho in RHOS:
        for scenario in SCENARIOS:
            for method in METHODS:
                rec = summary["scenario_results"][f"rho_{rho:.2f}"][scenario][method]
                if rec["familywise_false_certification"]["n"] != expected_trials:
                    failures.append(f"{rho:.2f}/{scenario}/{method}:trial-count")
                if rec["any_candidate_certification"]["n"] != expected_trials:
                    failures.append(f"{rho:.2f}/{scenario}/{method}:any-count")
    if failures:
        raise ValueError("verification failed: " + ", ".join(failures))
    print(f"verified source/protocol/output hashes and {len(RHOS)*len(SCENARIOS)} scenario-correlation cells")


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
