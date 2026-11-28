"""Small multi-noise repeat screen for the exact-zero Wilson phase chart."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.linalg import cholesky

from tasks.wilson_loop import f_lane_absolute_force_bootstrap_diagnostic as snapshot_writer
from tasks.wilson_loop import f_lane_finite_nt_trace_diagnostic as toy
from tasks.wilson_loop import f_lane_pivot_chart_exact_zero_screen as exact_zero
from tasks.wilson_loop import f_lane_three_static_pivot_chart as pivot
from tasks.wilson_loop import f_lane_three_static_two_vacuum_candidate as current
from tasks.wilson_loop import f_lane_two_sector_fit_candidate as two_state
from tasks.wilson_loop import f_lane_two_sector_omitted_coverage_diagnostic as noise_source


TASK_DIR = Path(__file__).resolve().parent
DEFAULT_OUT = TASK_DIR / "f_lane_pivot_chart_exact_zero_20261128_v2"
PANEL_SEEDS = (202611281128, 202611281129, 202611281130)
NOISE_LEVELS = (0.0003, 0.003, 0.01)
STARTS = exact_zero.STARTS
METHODS = exact_zero.METHODS
NOISE_REFERENCE = exact_zero.RELATIVE_NOISE
N_BLOCKS = exact_zero.N_BLOCKS
AR1_RHO = exact_zero.AR1_RHO


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha_file(path: Path) -> str:
    return _sha(path.read_bytes())


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("cannot write an empty result table")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _mean_matrices() -> np.ndarray:
    static, overlaps, epsilon = exact_zero._truth()
    vacuum = np.asarray((0.0, epsilon), dtype=np.float64)
    means = np.empty(
        (len(two_state.NT_VALUES), len(two_state.R_VALUES), len(two_state.T_VALUES), 3, 3),
        dtype=np.complex128,
    )
    for r_index in range(len(two_state.R_VALUES)):
        for nt_index, nt in enumerate(two_state.NT_VALUES):
            partition = float(np.sum(np.exp(-vacuum * nt)))
            for t_index, time_extent in enumerate(two_state.T_VALUES):
                weights = np.exp(
                    -vacuum[:, None] * (nt - time_extent)
                    -static[r_index][None, :] * time_extent
                ) / partition
                means[nt_index, r_index, t_index] = np.einsum(
                    "mn,mni,mnj->ij", weights, overlaps[r_index],
                    overlaps[r_index].conj(), optimize=True,
                )
    return means


def _noise_scaled_panel(seed: int, relative_noise: float,
                        reference_panel: np.ndarray, means: np.ndarray) -> np.ndarray:
    # Same standardized AR(1) innovations are paired across noise levels for each seed.
    scale = relative_noise / NOISE_REFERENCE
    return means[None, ...] + (reference_panel - means[None, ...]) * scale


def _stratum_summary(rows: list[dict[str, Any]], noise: float, method: str) -> dict[str, Any]:
    selected = [row for row in rows
                if row["relative_noise"] == noise and row["method"] == method]
    valid = [row for row in selected if row["valid"]]
    return {
        "planned": len(selected),
        "valid": len(valid),
        "failed": sum(row["status"].startswith("FAILED") for row in selected),
        "abstained": sum(row["status"].startswith("ABSTAIN") for row in selected),
        "median_target_operator0_amplitude_abs": (
            float(np.median([row["target_operator0_amplitude_abs"] for row in valid]))
            if valid else None
        ),
        "min_target_operator0_amplitude_abs": (
            float(min(row["target_operator0_amplitude_abs"] for row in valid)) if valid else None
        ),
        "max_target_operator0_amplitude_abs": (
            float(max(row["target_operator0_amplitude_abs"] for row in valid)) if valid else None
        ),
        "median_absolute_force_error": (
            float(np.median([row["absolute_force_error"] for row in valid])) if valid else None
        ),
        "median_solver_evaluations": (
            float(np.median([row["solver_evaluations"] for row in valid])) if valid else None
        ),
    }


def build(output: str | Path = DEFAULT_OUT) -> dict[str, Any]:
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    means = _mean_matrices()
    contract_bytes = (TASK_DIR / "lane_contract_v2.json").read_bytes()
    base_panels: dict[int, np.ndarray] = {}
    for seed in PANEL_SEEDS:
        base_panels[seed], _ = exact_zero._generate_matrices(seed)

    panel_rows: list[dict[str, Any]] = []
    fit_rows: list[dict[str, Any]] = []
    capture_rows: list[dict[str, Any]] = []
    panel_inputs: dict[str, dict[str, str]] = {}
    snapshot_by_panel = {}
    matrices_by_panel = {}
    for relative_noise in NOISE_LEVELS:
        for seed in PANEL_SEEDS:
            panel_id = f"noise_{relative_noise:g}_seed_{seed}"
            matrices = _noise_scaled_panel(seed, relative_noise, base_panels[seed], means)
            panel_dir = out / "source_package" / panel_id
            snapshot, input_hashes = snapshot_writer._snapshot_from_matrices(
                panel_dir, matrices, contract_bytes,
                f"F-synthetic-open-exact-zero-{relative_noise:g}-{seed}",
            )
            _manifest, validated = two_state._validate_raw_snapshot(
                snapshot, manifest_name="manifest", matrix_name="raw_matrices",
                contract_name="lane_contract",
            )
            if not np.array_equal(validated, matrices):
                raise ValueError(f"captured raw matrix bytes differ for {panel_id}")
            panel_inputs[panel_id] = dict(input_hashes)
            snapshot_by_panel[panel_id] = snapshot
            matrices_by_panel[panel_id] = matrices
            capture_rows.extend(
                {"panel_id": panel_id, "source_name": name,
                 "status": entry["status"],
                 "expected_sha256": entry["expected_sha256"],
                 "observed_sha256": entry["observed_sha256"]}
                for name, entry in snapshot.capture_entries.items()
            )
            panel_rows.append({
                "panel_id": panel_id, "seed": seed,
                "relative_noise": relative_noise, "planned_fits_per_method": len(STARTS),
                "source_capture_valid": len(snapshot.capture_entries),
                "matrix_sha256": input_hashes["raw_matrices"],
            })

    protocol = {
        "schema": "wilson-f-exact-zero-pivot-multireplicate-screen-v1",
        "classification": "small open synthetic numerical-feasibility screen; not coverage calibration",
        "panel_count": len(panel_rows),
        "seed_ids": list(PANEL_SEEDS),
        "relative_noise_levels": list(NOISE_LEVELS),
        "blocks_per_panel": N_BLOCKS,
        "ar1_rho": AR1_RHO,
        "paired_noise_rule": (
            "For each seed, generate one 0.3%-relative-noise AR(1) panel and scale the same "
            "standardized noise realization linearly to each frozen noise level."
        ),
        "truth": {
            "model": "finite-Nt 2-vacuum x 3-static positive trace",
            "exact_zero_transition": {
                "R": 2, "vacuum_state_m": 0, "static_state_n": 2, "operator_index": 0,
            },
        },
        "methods": list(METHODS),
        "starts_epsilon_excited_scale": [list(row) for row in STARTS],
        "initialization": "same oracle toy energy/overlap components for each pair; fixed chart floors the exact-zero operator-0 component at log amplitude -12",
        "objective": "same covariance-of-block-mean estimate with fixed shrinkage and eigenvalue floor within each panel",
        "solver": "TRF, analytic chart Jacobian, x_scale=jac, max_nfev=2000, ftol=xtol=gtol=1e-10",
        "validity": "solver success, finite coordinates/residuals, numerical Jacobian rank 67/67",
        "primary_outputs": [
            "planned/valid/failed/abstained fits by chart, noise level, and panel",
            "target |Z_0|, force point error, objective, rank/condition and solver evaluations",
        ],
        "not_claimed": [
            "finite-sample interval coverage", "physical overlap identifiability",
            "production initializer behavior", "global chart ranking", "physical score",
        ],
        "physical_score": None,
        "certified": False,
    }
    _write_json(out / "protocol.json", protocol)
    _write_json(out / "dgp_design.json", {
        "truth": exact_zero._generate_matrices(PANEL_SEEDS[0])[1],
        "panel_seed_ids": list(PANEL_SEEDS), "noise_levels": list(NOISE_LEVELS),
        "panel_matrix_hashes": {
            panel_id: hashes["raw_matrices"] for panel_id, hashes in panel_inputs.items()
        },
    })
    progress_path = out / "execution_progress.jsonl"
    progress_path.write_text("", encoding="utf-8")
    lower, upper = exact_zero._bounds()
    dgp_truth = exact_zero._generate_matrices(PANEL_SEEDS[0])[1]
    truth_force = float(dgp_truth["truth_absolute_force_lattice_units"])
    static, overlaps, _epsilon = exact_zero._truth()

    for panel_index, panel in enumerate(panel_rows):
        panel_id = panel["panel_id"]
        relative_noise = float(panel["relative_noise"])
        seed = int(panel["seed"])
        matrices = matrices_by_panel[panel_id]
        blocks = two_state._observed_vectors(matrices)
        mean = blocks.mean(axis=0)
        covariance, covariance_diagnostics = two_state._regularized_mean_covariance(blocks)
        chol = cholesky(covariance, lower=True, check_finite=True)
        pair_rows = []
        for start_index, (epsilon_start, excited_scale) in enumerate(STARTS):
            initial_overlaps = overlaps.copy()
            initial_overlaps[:, 1, :, :] *= (
                excited_scale / exact_zero.BASE_EXCITED_SCALE
            )
            fixed_initial, floor_indices = exact_zero._fixed_encode(
                epsilon_start, static, initial_overlaps,
            )
            pivot_initial, pivot_map = pivot.encode_components(
                epsilon_start, static, initial_overlaps,
            )
            initial_difference = float(np.max(np.abs(
                current._model_vectors(fixed_initial)
                - pivot.model_vectors(pivot_initial, pivot_map)
            )))
            target_log_index = 1 + exact_zero.ZERO_TRANSITION[0] * (
                current.STATIC_STATES + current.VACUUM_STATES * current.STATIC_STATES * 5
            ) + current.STATIC_STATES
            target_log_index += (
                exact_zero.ZERO_TRANSITION[1] * current.STATIC_STATES
                + exact_zero.ZERO_TRANSITION[2]
            ) * 5
            for method, initial, pivot_map_value in (
                (METHODS[0], fixed_initial, None),
                (METHODS[1], pivot_initial, pivot_map),
            ):
                result = exact_zero._fit_one(
                    method, initial, pivot_map_value, mean, chol, lower, upper,
                    target_log_index,
                )
                row = {
                    "panel_id": panel_id, "panel_index": panel_index,
                    "seed": seed, "relative_noise": relative_noise,
                    "start_index": start_index, "epsilon_start": epsilon_start,
                    "excited_scale_start": excited_scale, "method": method,
                    "initial_model_max_abs_difference": initial_difference,
                    "fixed_floor_transition_parameter_indices": list(floor_indices),
                    "force_truth": truth_force,
                    "absolute_force_error": (
                        abs(float(result["force"]) - truth_force)
                        if result["force"] is not None else None
                    ),
                    **result,
                }
                fit_rows.append(row)
                pair_rows.append(row)
                progress = {
                    "completed_fits": len(fit_rows),
                    "planned_fits": len(panel_rows) * len(STARTS) * len(METHODS),
                    "panel_id": panel_id, "start_index": start_index,
                    "method": method, "status": result["status"],
                    "valid": result["valid"], "solver_evaluations": result["solver_evaluations"],
                }
                with progress_path.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(progress, sort_keys=True) + "\n")
                    stream.flush()
                print(
                    f"completed {len(fit_rows)}/{len(panel_rows) * len(STARTS) * len(METHODS)}: "
                    f"{panel_id} start={start_index} {method} {result['status']}",
                    flush=True,
                )
        for method in METHODS:
            selected = [row for row in pair_rows if row["method"] == method]
            panel[f"{method}_valid"] = sum(bool(row["valid"]) for row in selected)
            panel[f"{method}_failed"] = sum(row["status"].startswith("FAILED") for row in selected)
            panel[f"{method}_abstained"] = sum(row["status"].startswith("ABSTAIN") for row in selected)
        panel["covariance_condition_number"] = covariance_diagnostics["condition_number"]

    by_method = {
        method: {
            "planned": sum(row["method"] == method for row in fit_rows),
            "valid": sum(row["method"] == method and row["valid"] for row in fit_rows),
            "failed": sum(row["method"] == method and row["status"].startswith("FAILED")
                          for row in fit_rows),
            "abstained": sum(row["method"] == method and row["status"].startswith("ABSTAIN")
                             for row in fit_rows),
        }
        for method in METHODS
    }
    by_noise = {
        str(noise): {method: _stratum_summary(fit_rows, noise, method) for method in METHODS}
        for noise in NOISE_LEVELS
    }
    paired_both = sum(
        all(next(row for row in fit_rows if row["panel_id"] == panel["panel_id"]
                 and row["start_index"] == start and row["method"] == method)["valid"]
            for method in METHODS)
        for panel in panel_rows for start in range(len(STARTS))
    )
    summary = {
        "schema": "wilson-f-exact-zero-pivot-multireplicate-summary-v1",
        "status": "SMALL_MULTI_NOISE_SCREEN_COMPLETE",
        "classification": "nine-panel synthetic method-feasibility diagnostic; not coverage calibration",
        "certified": False,
        "physical_score": None,
        "panel_denominator": {
            "planned": len(panel_rows), "valid": len(panel_rows), "failed": 0, "abstained": 0,
        },
        "source_capture_denominator": {
            "planned": len(capture_rows),
            "valid": sum(row["status"] == "valid" for row in capture_rows),
            "failed": sum(row["status"] == "failed" for row in capture_rows),
            "abstained": sum(row["status"] == "abstained" for row in capture_rows),
        },
        "fit_denominators_by_method": by_method,
        "fit_denominators_by_noise": by_noise,
        "paired_starts_both_valid": paired_both,
        "paired_starts_planned": len(panel_rows) * len(STARTS),
        "target_truth_operator0_amplitude": 0.0,
        "fixed_chart_lower_bound": exact_zero.FIXED_LOG_AMPLITUDE_FLOOR,
        "fixed_chart_minimum_nonzero_target_amplitude": float(
            np.exp(exact_zero.FIXED_LOG_AMPLITUDE_FLOOR)
        ),
        "truth_absolute_force_lattice_units": truth_force,
        "scope_limits": [
            "only 3 paired seeds per noise level; no population or coverage inference",
            "same standardized noise realization is scaled across levels within each seed",
            "oracle-seeded chart fits; production initializer is not tested",
            "no interval coverage, physical contamination, production/sealed input, GPU, or QUDA",
        ],
    }
    _write_csv(out / "fit_results.csv", fit_rows)
    _write_csv(out / "panel_summary.csv", panel_rows)
    _write_csv(out / "source_capture.csv", capture_rows)
    _write_json(out / "summary.json", summary)
    _plot(out / "multi_noise_comparison.png", fit_rows, truth_force)
    _write_readme(out / "README.md", summary)

    source_paths = {
        "tasks/wilson_loop/f_lane_pivot_chart_exact_zero_multireplicate_screen.py": Path(__file__),
        "tasks/wilson_loop/f_lane_pivot_chart_exact_zero_screen.py": Path(exact_zero.__file__),
        "tasks/wilson_loop/f_lane_three_static_pivot_chart.py": Path(pivot.__file__),
        "tasks/wilson_loop/f_lane_three_static_two_vacuum_candidate.py": Path(current.__file__),
        "tasks/wilson_loop/f_lane_two_sector_fit_candidate.py": Path(two_state.__file__),
        "tasks/wilson_loop/f_lane_finite_nt_trace_diagnostic.py": Path(toy.__file__),
        "tasks/wilson_loop/f_lane_two_sector_omitted_coverage_diagnostic.py": Path(noise_source.__file__),
        "tasks/wilson_loop/f_lane_absolute_force_bootstrap_diagnostic.py": Path(snapshot_writer.__file__),
        "core/source_integrity.py": REPO_ROOT / "core/source_integrity.py",
        "core/npz_safety.py": REPO_ROOT / "core/npz_safety.py",
        "tasks/wilson_loop/lane_contract_v2.json": TASK_DIR / "lane_contract_v2.json",
    }
    _write_json(out / "source_hashes.json", {
        name: _sha_file(path) for name, path in source_paths.items()
    })
    artifact_files = [
        "README.md", "protocol.json", "dgp_design.json", "summary.json", "fit_results.csv",
        "panel_summary.csv", "source_capture.csv", "execution_progress.jsonl",
        "multi_noise_comparison.png", "source_hashes.json",
    ]
    for panel_id in panel_inputs:
        artifact_files.extend(
            f"source_package/{panel_id}/{filename}"
            for filename in ("manifest.json", "raw_matrices.npz", "lane_contract.json")
        )
    _write_json(out / "artifact_hashes.json", {
        name: _sha_file(out / name) for name in artifact_files
    })
    return summary


def _plot(path: Path, rows: list[dict[str, Any]], truth_force: float) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.7))
    width = 0.36
    noise_x = np.arange(len(NOISE_LEVELS))
    for offset, method, label, color in (
        (-width / 2, METHODS[0], "fixed operator 0", "#3978a8"),
        (width / 2, METHODS[1], "largest-component pivot", "#d07a2d"),
    ):
        rates = []
        for noise in NOISE_LEVELS:
            selected = [row for row in rows
                        if row["relative_noise"] == noise and row["method"] == method]
            rates.append(sum(bool(row["valid"]) for row in selected) / len(selected))
        axes[0].bar(noise_x + offset, rates, width, label=label, color=color)
    axes[0].set_xticks(noise_x, [f"{noise:g}" for noise in NOISE_LEVELS])
    axes[0].set_ylim(0, 1.05)
    axes[0].set_xlabel("relative matrix noise")
    axes[0].set_ylabel("valid fits / 9 planned")
    axes[0].set_title("Fit completion fraction")
    axes[0].legend(frameon=False, fontsize=7)

    jitter = {METHODS[0]: -0.08, METHODS[1]: 0.08}
    markers = {METHODS[0]: "o", METHODS[1]: "s"}
    colors = {METHODS[0]: "#3978a8", METHODS[1]: "#d07a2d"}
    for method in METHODS:
        selected = [row for row in rows if row["method"] == method and row["valid"]]
        xvals = np.asarray([
            NOISE_LEVELS.index(row["relative_noise"]) + jitter[method]
            for row in selected
        ])
        yvals = np.asarray([row["target_operator0_amplitude_abs"] for row in selected])
        axes[1].scatter(xvals, yvals, marker=markers[method], color=colors[method],
                        s=24, alpha=0.8, label=method)
    axes[1].axhline(0.0, color="black", linewidth=1, label="exact truth")
    axes[1].axhline(np.exp(exact_zero.FIXED_LOG_AMPLITUDE_FLOOR), color="#555555",
                    linestyle="--", linewidth=1, label="fixed chart lower bound")
    axes[1].set_yscale("symlog", linthresh=1e-8)
    axes[1].set_xticks(noise_x, [f"{noise:g}" for noise in NOISE_LEVELS])
    axes[1].set_xlabel("relative matrix noise")
    axes[1].set_ylabel(r"fitted $|Z_0|$ at exact-zero transition")
    axes[1].set_title("Operator-0 overlap estimate")
    axes[1].legend(frameon=False, fontsize=6)

    for method, label, color, marker in (
        (METHODS[0], "fixed operator 0", "#3978a8", "o"),
        (METHODS[1], "largest-component pivot", "#d07a2d", "s"),
    ):
        means = []
        errors = []
        for noise in NOISE_LEVELS:
            seed_means = []
            for seed in PANEL_SEEDS:
                selected = [row for row in rows
                            if row["relative_noise"] == noise and row["seed"] == seed
                            and row["method"] == method and row["valid"]]
                if selected:
                    seed_means.append(float(np.mean([
                        row["absolute_force_error"] for row in selected
                    ])))
            means.append(float(np.mean(seed_means)) if seed_means else np.nan)
            errors.append(float(np.std(seed_means, ddof=1)) if len(seed_means) > 1 else 0.0)
        axes[2].errorbar(noise_x, means, yerr=errors, marker=marker, color=color,
                         capsize=3, label=label)
    axes[2].set_xticks(noise_x, [f"{noise:g}" for noise in NOISE_LEVELS])
    axes[2].set_xlabel("relative matrix noise")
    axes[2].set_ylabel("absolute point-force error")
    axes[2].set_title(f"Force error (toy truth {truth_force:g})")
    axes[2].legend(frameon=False, fontsize=7)
    for axis in axes:
        axis.grid(axis="y", alpha=0.2)
    fig.suptitle("Exact-zero phase-chart stress; synthetic CPU only")
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def _write_readme(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Exact-zero operator-0 chart screen across noise levels",
        "",
        "**Classification:** nine deliberately constructed open synthetic panels; this is a small optimizer feasibility screen, not a coverage study or physical result.",
        "",
        "![Exact-zero chart fit behavior by noise level](multi_noise_comparison.png)",
        "",
        "## Frozen design",
        "",
        "The same positive finite-`N_t` 2-vacuum × 3-static truth has exactly `Z_0(R=2,m=0,n=2)=0`, with nonzero operators 1 and 2. Three seeds are crossed with relative matrix-noise levels `0.0003`, `0.003`, and `0.01`. For each seed, the same standardized Hermitian AR(1) noise realization is scaled to each noise level. Each panel uses 96 blocks, `rho=0.5`, three paired oracle-derived starts, a panel-specific regularized covariance, analytic chart Jacobians, TRF, `max_nfev=2000`, and `1e-10` tolerances. No production initializer is used.",
        "",
        f"- Panels: `{summary['panel_denominator']['planned']}/{summary['panel_denominator']['valid']}/{summary['panel_denominator']['failed']}/{summary['panel_denominator']['abstained']}` (planned/valid/failed/abstained).",
        f"- Captured panel source files: `{summary['source_capture_denominator']['planned']}/{summary['source_capture_denominator']['valid']}/{summary['source_capture_denominator']['failed']}/{summary['source_capture_denominator']['abstained']}`.",
        f"- Fixed chart fits: `{summary['fit_denominators_by_method'][METHODS[0]]}`.",
        f"- Largest-pivot chart fits: `{summary['fit_denominators_by_method'][METHODS[1]]}`.",
        f"- Paired starts valid in both: `{summary['paired_starts_both_valid']}/{summary['paired_starts_planned']}`.",
        "",
        "Per-noise summaries for the fitted zero-component magnitude, force error and solver evaluations are in `summary.json`; every fit and failure reason is retained in `fit_results.csv`, and panel-level counts/covariance condition numbers are in `panel_summary.csv`. The force-error whiskers show the standard deviation across the three seed-level means, not across starts.",
        "",
        "## Interpretation limits",
        "",
        "The pivot chart has an exact coordinate for zero operator-0 amplitude, while the fixed chart has a positive finite lower bound. A fitted nonzero `|Z_0|` in the pivot chart does not invalidate its representation; it can indicate that this noisy one-point dataset does not identify the component as zero. Three seeds per noise level are too few for coverage, risk, or population claims. The force points are toy fit diagnostics, not certified estimates.",
        "",
        "Raw captured matrices and their manifests are retained under `source_package/`. `artifact_hashes.json` covers the report, figure and all panel input files; `source_hashes.json` binds the producer and reader dependencies. Reproduce with `python tasks/wilson_loop/f_lane_pivot_chart_exact_zero_multireplicate_screen.py --output <new-empty-directory>`.",
        "",
        "No production/sealed data, GPU, QUDA, interval coverage, thermal/mixed contamination bound, or physical score is produced.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    print(json.dumps(build(args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
