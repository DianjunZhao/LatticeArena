"""CPU convergence diagnostics for the matched operator-class experiment.

This is a method diagnostic for package C, not evidence about learned smearing
on production gauge ensembles.  It reuses the same synthetic links, probes,
operators, real coefficient domain, and independent test links as
``p3_crosslink_fair`` while adding exact objective-evaluation budgets and
multi-start optimizer traces.
"""
from __future__ import annotations

import hashlib
import json
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import minimize

from tasks.optimize_gaussian import p3_crosslink_fair as fair


OUT = Path("results/optimize_gaussian/cpu_close_20261119_C_convergence")
BUDGETS = (12, 25, 50, 100, 200, 400)  # objective calls allowed per start
N_STARTS = 5
EPSILONS = fair.EPSILONS
SEEDS = fair.SEEDS
METHODS = ("SLSQP", "Powell")
CLASSES = ("A_spectral", "B_nested")


class BudgetExhausted(Exception):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dataset(seed: int):
    """Recreate exactly the link/probe stream used by ``fair.run``."""
    rng = np.random.default_rng(seed)
    train_links = [fair.links(rng) for _ in range(3)]
    test_links = [fair.links(rng) for _ in range(2)]
    train_ops = [fair.build_operators(u) for u in train_links]
    test_ops = [fair.build_operators(u) for u in test_links]
    train_probes = [rng.choice(3 * fair.L**3, size=20, replace=False).tolist()
                    for _ in range(3)]
    test_probes = [rng.choice(3 * fair.L**3, size=12, replace=False).tolist()
                   for _ in range(2)]
    return train_ops, test_ops, train_probes, test_probes


def _projected_gradient_norm(Xscaled, Y, theta, scales):
    Xr, Yr = fair._real_system(Xscaled, Y)
    denom = max(float(Yr @ Yr), np.finfo(float).tiny)
    grad = 2 * Xr.T @ (Xr @ theta - Yr) / denom
    lo, hi = fair.COEFFICIENT_BOUNDS
    projected = theta - np.clip(theta - grad, lo * scales, hi * scales)
    return float(np.linalg.norm(projected))


def _solver_trial(X, Y, method, start, budget, scales, Xr, Yr, denom):
    """Run one bounded optimizer with a hard objective-call ceiling."""
    calls = 0
    visited = []

    def objective(theta):
        nonlocal calls
        if calls >= budget:
            raise BudgetExhausted
        calls += 1
        value = float(np.sum((Xr @ theta - Yr) ** 2) / denom)
        visited.append((value, np.asarray(theta, dtype=float).copy()))
        return value

    def gradient(theta):
        return 2 * Xr.T @ (Xr @ theta - Yr) / denom

    lo, hi = fair.COEFFICIENT_BOUNDS
    bounds = list(zip(lo * scales, hi * scales))
    options = {"maxiter": 5000, "ftol": 1e-12}
    if method == "Powell":
        options = {"maxiter": 5000, "xtol": 1e-9, "ftol": 1e-12}

    stopped_by_budget = False
    messages = []
    result_success = False
    result_message = "not_started"
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            result = minimize(objective, start, method=method, bounds=bounds,
                              jac=gradient if method == "SLSQP" else None,
                              options=options)
            result_success = bool(result.success)
            result_message = str(result.message)
        except BudgetExhausted:
            stopped_by_budget = True
            result_message = "objective_evaluation_budget_exhausted"
        messages = [str(w.message) for w in caught]

    # All evaluated points are feasible up to the optimizer's bound tolerance;
    # clip only roundoff-sized excursions before reporting the selected point.
    if not visited:
        theta = np.clip(np.asarray(start, dtype=float), lo * scales, hi * scales)
        train_objective = float(np.sum((Xr @ theta - Yr) ** 2) / denom)
    else:
        train_objective, theta = min(visited, key=lambda item: item[0])
        theta = np.clip(theta, lo * scales, hi * scales)
        train_objective = float(np.sum((Xr @ theta - Yr) ** 2) / denom)
    original = theta / scales
    test_error = float(np.linalg.norm(X @ original - Y) /
                       (np.linalg.norm(Y) + 1e-12))
    kkt = _projected_gradient_norm(X / scales, Y, theta, scales)
    return {
        "objective_calls": calls,
        "budget_per_start": budget,
        "budget_exhausted": stopped_by_budget,
        "solver_success": result_success,
        "solver_message": result_message,
        "warnings": messages,
        "relative_train_objective": train_objective,
        "projected_gradient_norm_scaled_variables": kkt,
        "test_error": test_error,
        "feasible": bool(np.all(original >= lo - 1e-9) and
                          np.all(original <= hi + 1e-9)),
        "coefficients": [float(v) for v in original],
    }


def _starts(scales, seed):
    lo, hi = fair.COEFFICIENT_BOUNDS
    rng = np.random.default_rng(900_000 + seed)
    return [np.zeros(scales.size), *[
        rng.uniform(lo, hi, size=scales.size) * scales
        for _ in range(N_STARTS - 1)]]


def _diagnose_cell(seed, epsilon, train_ops, test_ops, train_probes, test_probes):
    cell = {"epsilon": epsilon, "seed": seed, "classes": {}}
    for augmented, klass in ((False, "A_spectral"), (True, "B_nested")):
        X, Y = fair.design_ensembles(train_ops, epsilon, augmented, train_probes)
        Xt, Yt = fair.design_ensembles(test_ops, epsilon, augmented, test_probes)
        scales = np.sqrt(np.mean(np.abs(X) ** 2, axis=0))
        scales = np.where(scales > 1e-12, scales, 1.0)
        Xr, Yr = fair._real_system(X / scales, Y)
        singular = np.linalg.svd(Xr, compute_uv=False)
        tol = (singular[0] * max(Xr.shape) * np.finfo(float).eps
               if singular.size else 0.0)
        rank = int(np.count_nonzero(singular > tol))
        condition = (float(singular[0] / singular[-1])
                     if singular.size and rank == len(scales) and singular[-1] > 0
                     else None)
        oracle_theta, _, _, _ = fair.fit(X, Y, "oracle")
        oracle_train = fair._relative_objective(X, Y, oracle_theta)
        oracle_test = float(np.linalg.norm(Xt @ oracle_theta - Yt) /
                            (np.linalg.norm(Yt) + 1e-12))
        Xscaled = X / scales
        _, Yr_scaled = fair._real_system(Xscaled, Y)
        denom = max(float(Yr_scaled @ Yr_scaled), np.finfo(float).tiny)
        starts = _starts(scales, seed)
        klass_data = {
            "n_features": int(X.shape[1]),
            "realified_design_shape": [int(v) for v in Xr.shape],
            "rank_realified_design": rank,
            "singular_values_scaled": [float(v) for v in singular],
            "condition_number_scaled": condition,
            "feature_scales": [float(v) for v in scales],
            "oracle_train_objective": oracle_train,
            "oracle_test_error": oracle_test,
            "starts": [[float(v) for v in start] for start in starts],
            "methods": {},
        }
        for method in METHODS:
            previous_best = None
            traces = []
            for budget in BUDGETS:
                trials = [_solver_trial(X, Y, method, start, budget, scales,
                                        Xr, Yr, denom)
                          for start in starts]
                best = min(trials, key=lambda row: row["relative_train_objective"])
                total_calls = sum(row["objective_calls"] for row in trials)
                traces.append({
                    "budget_per_start": budget,
                    "max_total_objective_calls": budget * N_STARTS,
                    "actual_total_objective_calls": total_calls,
                    "best": best,
                    "all_starts": trials,
                    "best_so_far_monotone": (previous_best is None or
                        best["relative_train_objective"] <= previous_best + 1e-14),
                })
                previous_best = best["relative_train_objective"]
            klass_data["methods"][method] = traces
        cell["classes"][klass] = klass_data
    return cell


def _mean_se(values):
    values = np.asarray(values, dtype=float)
    return float(np.mean(values)), float(np.std(values, ddof=1) / np.sqrt(len(values)))


def _plot_condition(result, path):
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.5))
    colors = {"A_spectral": "#315a8a", "B_nested": "#b15b32"}
    offsets = {"A_spectral": -0.11, "B_nested": 0.11}
    for ei, epsilon in enumerate(EPSILONS):
        for klass in CLASSES:
            vals = [result["rows"][f"eps{epsilon}/seed{s}"]["classes"][klass]
                    for s in SEEDS]
            x = ei + offsets[klass]
            for item in vals:
                cond = item["condition_number_scaled"]
                if cond is not None:
                    axes[0].scatter(x, np.log10(cond), color=colors[klass], alpha=.65, s=28)
            means = [np.log10(item["condition_number_scaled"])
                     for item in vals if item["condition_number_scaled"] is not None]
            if means:
                axes[0].plot([x - .06, x + .06], [np.mean(means)] * 2,
                             color=colors[klass], linewidth=2.4)
            axes[1].scatter([x] * len(vals),
                            [item["rank_realified_design"] / item["n_features"]
                             for item in vals],
                            color=colors[klass], alpha=.75, s=32)
    axes[0].set(title="Column-scaled condition number", ylabel=r"$\log_{10}\kappa_2$")
    axes[1].set(title="Realified design rank", ylabel="rank / feature count (1 = full rank)")
    for ax in axes:
        ax.set_xticks(range(len(EPSILONS)), [str(v) for v in EPSILONS])
        ax.set_xlabel(r"$\epsilon$ in constructed target")
        ax.grid(alpha=.25)
    from matplotlib.lines import Line2D
    axes[0].legend(handles=[Line2D([0], [0], marker="o", color="w",
                                   markerfacecolor=colors[k], label=k)
                            for k in CLASSES], fontsize=8)
    fig.suptitle("C-package realified design conditioning (3 independent seeds)")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_convergence(result, path):
    fig, axes = plt.subplots(len(EPSILONS), 3, figsize=(14, 13), sharex="col")
    colors = {"A_spectral": "#315a8a", "B_nested": "#b15b32"}
    markers = {"SLSQP": "o", "Powell": "s"}
    metrics = (("relative_train_objective", "best relative train objective"),
               ("projected_gradient_norm_scaled_variables", "projected-gradient KKT residual"),
               ("test_error", "independent-link relative test error"))
    total_budgets = np.asarray(BUDGETS) * N_STARTS
    for ei, epsilon in enumerate(EPSILONS):
        for mi, (metric, ylabel) in enumerate(metrics):
            ax = axes[ei, mi]
            for klass in CLASSES:
                for method in METHODS:
                    means, errors = [], []
                    for budget_index in range(len(BUDGETS)):
                        samples = [result["rows"][f"eps{epsilon}/seed{s}"]["classes"][klass]
                                   ["methods"][method][budget_index]["best"][metric]
                                   for s in SEEDS]
                        mean, se = _mean_se(samples)
                        means.append(max(mean, 1e-16))
                        errors.append(se)
                    lower = np.maximum(np.asarray(means) - np.asarray(errors), 1e-16)
                    upper = np.asarray(means) + np.asarray(errors)
                    ax.errorbar(total_budgets, means,
                                yerr=[np.asarray(means) - lower, upper - means],
                                color=colors[klass], marker=markers[method],
                                linestyle="-" if method == "SLSQP" else "--",
                                capsize=2, linewidth=1.5,
                                label=f"{klass} / {method}")
            ax.set_yscale("log")
            ax.grid(alpha=.23, which="both")
            if mi == 0:
                ax.set_ylabel(f"epsilon={epsilon}\n{ylabel}")
            else:
                ax.set_ylabel(ylabel)
            if ei == len(EPSILONS) - 1:
                ax.set_xlabel("maximum objective calls across 5 starts")
            if ei == 0 and mi == 0:
                ax.legend(fontsize=7, ncol=2)
    fig.suptitle("Exact objective-call budgets; mean ± SE over three seeds", y=.995)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _summary(result):
    cells = []
    for epsilon in EPSILONS:
        for klass in CLASSES:
            for method in METHODS:
                last = [result["rows"][f"eps{epsilon}/seed{s}"]["classes"][klass]
                        ["methods"][method][-1] for s in SEEDS]
                cells.append({
                    "epsilon": epsilon,
                    "class": klass,
                    "method": method,
                    "mean_test_error": float(np.mean([x["best"]["test_error"] for x in last])),
                    "mean_train_objective": float(np.mean([x["best"]["relative_train_objective"] for x in last])),
                    "mean_kkt_residual": float(np.mean([x["best"]["projected_gradient_norm_scaled_variables"] for x in last])),
                    "mean_actual_total_objective_calls": float(np.mean([x["actual_total_objective_calls"] for x in last])),
                    "budget_limited_starts_at_largest_budget": sum(
                        not start["solver_success"] and start["budget_exhausted"]
                        for x in last for start in x["all_starts"]),
                    "unsuccessful_terminations_before_budget": sum(
                        not start["solver_success"] and not start["budget_exhausted"]
                        for x in last for start in x["all_starts"]),
                })
    return cells


def main():
    if OUT.exists() and any(OUT.iterdir()):
        raise FileExistsError(f"{OUT} already contains results; choose a new output directory")
    OUT.mkdir(parents=True, exist_ok=True)
    rows = {}
    for seed in SEEDS:
        train_ops, test_ops, train_probes, test_probes = _dataset(seed)
        for epsilon in EPSILONS:
            key = f"eps{epsilon}/seed{seed}"
            rows[key] = _diagnose_cell(seed, epsilon, train_ops, test_ops,
                                       train_probes, test_probes)
            print(key, "condition numbers", {
                klass: rows[key]["classes"][klass]["condition_number_scaled"]
                for klass in CLASSES})
    result = {
        "schema": "optgauss-cpu-convergence-v1",
        "scope": "synthetic CPU method diagnostic; not a production learned-smear comparison",
        "source_sha256": {
            "diagnostic": _sha256(Path(__file__)),
            "matched_experiment": _sha256(Path(fair.__file__)),
        },
        "design": {
            "same_generator_and_probe_stream_as": "p3_crosslink_fair.run(seed, epsilon)",
            "epsilon_values": list(EPSILONS),
            "seeds": list(SEEDS),
            "objective_budgets_per_start": list(BUDGETS),
            "number_of_starts": N_STARTS,
            "starts": "one zero start plus four deterministic shared random starts in the scaled coefficient box",
            "budget_semantics": "hard ceiling on objective calls for each optimizer start; actual calls are recorded",
            "methods": list(METHODS),
            "coefficient_domain": list(fair.COEFFICIENT_BOUNDS),
            "independent_test_links": True,
        },
        "rows": rows,
        "summary_at_largest_budget": _summary({"rows": rows}),
        "interpretation_limits": [
            "Only three synthetic seeds; standard errors are descriptive, not publication-grade uncertainty.",
            "Bounded least squares is the convex quadratic oracle for the same finite design, not a physical optimum.",
            "KKT residual is the box-projected gradient norm in scaled optimizer variables; its absolute scale depends on feature scaling and relative objective normalization.",
            "Budget-truncated optimizer runs are not failures; only pre-budget unsuccessful termination is a solver failure.",
        ],
    }
    (OUT / "convergence_diagnostic.json").write_text(json.dumps(result, indent=2) + "\n")
    _plot_condition(result, OUT / "fig_condition_number_rank.png")
    _plot_convergence(result, OUT / "fig_budget_convergence.png")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
