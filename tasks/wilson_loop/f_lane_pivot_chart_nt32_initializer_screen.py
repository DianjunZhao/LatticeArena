"""Stress fixed and pivot phase charts with the matched-Nt=32 initializer.

This CPU-only method screen reuses the exact-zero synthetic snapshots from the
preceding report. The initializer reads only those Nt=32 matrices; exact toy
truth is used only to score the final force point, never to construct starts.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
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

from core.source_integrity import capture_source_snapshot
from tasks.wilson_loop import f_lane_joint_spectral_gls_diagnostic as initializer
from tasks.wilson_loop import f_lane_pivot_chart_exact_zero_multireplicate_screen as prior_screen
from tasks.wilson_loop import f_lane_pivot_chart_exact_zero_screen as exact_zero
from tasks.wilson_loop import f_lane_pivot_chart_fit_comparison as fit_comparison
from tasks.wilson_loop import f_lane_three_static_pivot_chart as pivot
from tasks.wilson_loop import f_lane_three_static_two_vacuum_candidate as current
from tasks.wilson_loop import f_lane_two_sector_fit_candidate as two_state


TASK_DIR = Path(__file__).resolve().parent
INPUT_REPORT = TASK_DIR / "f_lane_pivot_chart_exact_zero_20261128_v2"
DEFAULT_OUT = TASK_DIR / "f_lane_pivot_chart_exact_zero_nt32_initializer_20261128_v2"
STARTS = ((0.15, 0.20), (0.30, 0.35), (0.55, 0.50))
MAX_NFEV = 2000
TOLERANCE = 1e-10


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty table: {path}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        fieldnames = list(dict.fromkeys(key for row in rows for key in row))
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _capture_panel(panel_id: str, artifact_hashes: dict[str, str]):
    root = INPUT_REPORT / "source_package" / panel_id
    filenames = {
        "manifest": "manifest.json",
        "raw_matrices": "raw_matrices.npz",
        "lane_contract": "lane_contract.json",
    }
    expected = {
        name: artifact_hashes[f"source_package/{panel_id}/{filename}"]
        for name, filename in filenames.items()
    }
    snapshot = capture_source_snapshot(
        root, expected, {name: filename for name, filename in filenames.items()},
        max_total_bytes=8 * 1024 * 1024,
    )
    manifest, matrices = two_state._validate_raw_snapshot(
        snapshot, manifest_name="manifest", matrix_name="raw_matrices",
        contract_name="lane_contract",
    )
    return snapshot, manifest, matrices


def _nt32_block_vectors(matrices: np.ndarray, radius_index: int) -> np.ndarray:
    nt_index = two_state.NT_VALUES.index(32)
    return np.stack([
        np.concatenate([
            initializer._matrix_vector(matrices[block, nt_index, radius_index, t_index])
            for t_index in range(len(two_state.T_VALUES))
        ])
        for block in range(matrices.shape[0])
    ])


def _fit_nt32_initializer(matrices: np.ndarray):
    """Mirror the candidate's per-R Nt=32 fit while retaining each failure row."""
    static_guesses: list[np.ndarray] = []
    overlap_guesses: list[np.ndarray] = []
    receipts: list[dict[str, Any]] = []
    for radius_index, radius in enumerate(two_state.R_VALUES):
        blocks = _nt32_block_vectors(matrices, radius_index)
        try:
            fit = initializer.fit_joint_spectrum(
                blocks, time_slices=two_state.T_VALUES, n_states=current.STATIC_STATES,
                operator_indices=(0, 1, 2),
            )
            success = bool(fit.get("success"))
            receipts.append({
                "R": radius, "status": "VALID" if success else "FAILED",
                "success": success, "rank": fit.get("rank"),
                "parameter_count": fit.get("parameter_count"), "nfev": fit.get("nfev"),
                "reduced_chi_square": fit.get("reduced_chi_square"),
                "condition_number": fit.get("jacobian_condition_number"),
                "message": fit.get("message"),
            })
            if not success:
                continue
            energies = np.asarray(fit["energies"], dtype=float)
            overlap_pairs = np.asarray(fit["overlaps"], dtype=float)
            if overlap_pairs.shape != (current.STATIC_STATES, current.OPERATOR_COUNT, 2):
                receipts[-1]["status"] = "FAILED_BAD_OVERLAP_AXES"
                continue
            static_guesses.append(energies)
            overlap_guesses.append(overlap_pairs[..., 0] + 1j * overlap_pairs[..., 1])
        except (ValueError, FloatingPointError, np.linalg.LinAlgError) as exc:
            receipts.append({
                "R": radius, "status": "FAILED_EXCEPTION", "success": False,
                "message": f"{type(exc).__name__}: {exc}",
            })
    if len(static_guesses) != len(two_state.R_VALUES):
        return None, None, receipts
    return static_guesses, overlap_guesses, receipts


def _paired_chart_starts(static_guesses: list[np.ndarray], overlap_guesses: list[np.ndarray],
                         epsilon: float, excited_scale: float
                         ) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    fixed_start = current._initial_parameters(
        static_guesses, overlap_guesses, epsilon, excited_scale,
    )
    pivot_start, pivot_map = pivot.encode_current_parameters(fixed_start)
    model_difference = float(np.max(np.abs(
        current._model_vectors(fixed_start)
        - pivot.model_vectors(pivot_start, pivot_map)
    )))
    return fixed_start, pivot_start, pivot_map, model_difference


def _fit_denominator(rows: list[dict[str, Any]], method: str,
                     noise: float | None = None) -> dict[str, int]:
    selected = [row for row in rows if row["method"] == method
                and (noise is None or row["relative_noise"] == noise)]
    valid = sum(bool(row["valid"]) for row in selected)
    abstained = sum(str(row["status"]).startswith("ABSTAIN") for row in selected)
    return {"planned": len(selected), "valid": valid,
            "failed": len(selected) - valid - abstained, "abstained": abstained}


def build(output: str | Path = DEFAULT_OUT) -> dict[str, Any]:
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    fit_comparison.MAX_NFEV = MAX_NFEV
    source_artifacts_path = INPUT_REPORT / "artifact_hashes.json"
    source_artifacts = json.loads(source_artifacts_path.read_text(encoding="utf-8"))
    input_artifact_map_sha256 = _sha_file(source_artifacts_path)
    input_summary = json.loads((INPUT_REPORT / "summary.json").read_text(encoding="utf-8"))
    means_info = json.loads((INPUT_REPORT / "dgp_design.json").read_text(encoding="utf-8"))

    protocol = {
        "schema": "wilson-f-exact-zero-nt32-initializer-screen-v1",
        "classification": "paired initializer-feasibility screen on reused open synthetic matrices",
        "input_report": INPUT_REPORT.name,
        "input_report_artifact_hash_manifest_sha256": input_artifact_map_sha256,
        "panel_ids": sorted(means_info["panel_matrix_hashes"]),
        "panel_count": len(means_info["panel_matrix_hashes"]),
        "source_capture": "capture manifest/raw_matrices/lane_contract by artifact-manifest SHA-256, then read the same immutable snapshot",
        "initialization": "for each R independently, fit the matched Nt=32 3-state/3-operator joint spectrum to blocks; use fitted energies and overlaps only; no injected truth enters the start",
        "full_fit": "same finite-Nt 2-vacuum x 3-static positive-spectrum model, covariance, charts, objective and bounds as paired point-fit screen",
        "starts_epsilon_excited_overlap_scale": [list(row) for row in STARTS],
        "charts": ["fixed operator-0", "largest-component pivot re-encoding of the same physical start"],
        "solver": f"TRF, analytic chart Jacobian, x_scale=jac, max_nfev={MAX_NFEV}, ftol=xtol=gtol={TOLERANCE}",
        "validity": "solver success, finite result and local Jacobian rank 67/67; shared bounds are enforced before optimizer launch",
        "not_claimed": ["independent samples", "profile or interval coverage", "production data behavior", "physical contamination bound", "global chart ranking"],
        "physical_score": None,
        "certified": False,
    }
    _write_json(out / "protocol.json", protocol)
    _write_json(out / "dgp_design.json", {
        "source_report": INPUT_REPORT.name,
        "input_artifact_hash_manifest_sha256": input_artifact_map_sha256,
        "panel_matrix_sha256": means_info["panel_matrix_hashes"],
        "seed_ids": means_info["panel_seed_ids"],
        "noise_levels": means_info["noise_levels"],
        "truth_used_for_initialization": False,
        "truth_used_for_final_force_error_only": True,
    })
    progress_path = out / "execution_progress.jsonl"
    progress_path.write_text("", encoding="utf-8")
    status_path = out / "execution_status.json"
    status = {
        "schema": "wilson-f-exact-zero-nt32-initializer-execution-status-v1",
        "status": "RUNNING", "planned_panels": protocol["panel_count"],
        "completed_panels": 0, "planned_chart_fits": protocol["panel_count"] * len(STARTS) * 2,
        "completed_chart_fits": 0, "initializer_fits_planned": protocol["panel_count"] * 2,
        "initializer_fits_completed": 0, "error": None,
    }
    _write_json(status_path, status)

    capture_rows: list[dict[str, Any]] = []
    initializer_rows: list[dict[str, Any]] = []
    fit_rows: list[dict[str, Any]] = []
    panel_rows: list[dict[str, Any]] = []
    lower, upper = fit_comparison._bounds()
    truth_force = float(input_summary["truth_absolute_force_lattice_units"])

    try:
        for panel_index, panel_id in enumerate(protocol["panel_ids"]):
            snapshot, manifest, matrices = _capture_panel(panel_id, source_artifacts)
            capture_rows.extend({
                "panel_id": panel_id, "source_name": name,
                "status": entry["status"],
                "expected_sha256": entry["expected_sha256"],
                "observed_sha256": entry["observed_sha256"],
            } for name, entry in snapshot.capture_entries.items())
            noise_part, seed_part = panel_id.removeprefix("noise_").split("_seed_", 1)
            relative_noise = float(noise_part)
            seed = int(seed_part)
            expected_split = f"F-synthetic-open-exact-zero-{relative_noise:g}-{seed}"
            if manifest.get("split_id") != expected_split:
                raise ValueError(f"panel ID and captured manifest split disagree: {panel_id}")
            static_guesses, overlap_guesses, init_receipts = _fit_nt32_initializer(matrices)
            initializer_rows.extend({
                "panel_id": panel_id, "relative_noise": relative_noise, "seed": seed,
                **receipt,
            } for receipt in init_receipts)
            status["initializer_fits_completed"] += len(init_receipts)
            init_ok = static_guesses is not None and overlap_guesses is not None
            init_target = (
                float(abs(overlap_guesses[0][2, 0])) if init_ok else None
            )
            init_target_log = float(np.log(init_target)) if init_target and init_target > 0 else None
            if init_ok:
                blocks = two_state._observed_vectors(matrices)
                mean = blocks.mean(axis=0)
                covariance, covariance_diagnostics = two_state._regularized_mean_covariance(blocks)
                covariance_chol = cholesky(covariance, lower=True, check_finite=True)
            else:
                covariance_diagnostics = {"condition_number": None}
            panel_start = len(fit_rows)
            panel_fit_rows = []
            for start_index, (epsilon, excited_scale) in enumerate(STARTS):
                if init_ok:
                    try:
                        fixed_start, pivot_start, pivot_map, start_model_difference = (
                            _paired_chart_starts(
                                static_guesses, overlap_guesses, epsilon, excited_scale,
                            )
                        )
                        starts = (("fixed_operator0", fixed_start, None),
                                  ("largest_component_pivot", pivot_start, pivot_map))
                    except (ValueError, FloatingPointError, np.linalg.LinAlgError) as exc:
                        start_error = f"{type(exc).__name__}: {exc}"
                        starts = tuple((method, None, None) for method in
                                       ("fixed_operator0", "largest_component_pivot"))
                        start_model_difference = None
                else:
                    start_error = "one or more Nt=32 per-R initializer fits failed"
                    starts = tuple((method, None, None) for method in
                                   ("fixed_operator0", "largest_component_pivot"))
                    start_model_difference = None

                for method, initial, pivot_map in starts:
                    if initial is None:
                        result = fit_comparison._start_abstention(
                            "ABSTAIN_NT32_INITIALIZER_FAILED", start_error,
                        )
                    else:
                        result = fit_comparison._run_one(
                            method, initial, pivot_map, mean, covariance_chol, lower, upper,
                        )
                    row = {
                        "panel_id": panel_id, "panel_index": panel_index,
                        "relative_noise": relative_noise, "seed": seed,
                        "start_index": start_index, "epsilon_start": epsilon,
                        "excited_overlap_scale_start": excited_scale,
                        "method": method, "initializer_target_operator0_abs": init_target,
                        "initializer_target_operator0_log_abs": init_target_log,
                        "initial_chart_model_max_abs_difference": start_model_difference,
                        "truth_absolute_force_lattice_units": truth_force,
                        "absolute_force_error_lattice_units": (
                            abs(float(result["force"]) - truth_force)
                            if result.get("force") is not None else None
                        ),
                        "initializer_all_radii_valid": init_ok,
                        "initializer_radii_valid": sum(bool(item.get("success"))
                                                        for item in init_receipts),
                        **result,
                    }
                    fit_rows.append(row)
                    panel_fit_rows.append(row)
                    progress = {
                        "completed_chart_fits": len(fit_rows),
                        "planned_chart_fits": protocol["panel_count"] * len(STARTS) * 2,
                        "panel_id": panel_id, "start_index": start_index,
                        "method": method, "status": result["status"],
                        "valid": result["valid"],
                    }
                    with progress_path.open("a", encoding="utf-8") as stream:
                        stream.write(json.dumps(progress, sort_keys=True) + "\n")
                        stream.flush()
            panel_row = {
                "panel_id": panel_id, "relative_noise": relative_noise, "seed": seed,
                "manifest_split_id": manifest.get("split_id"),
                "initializer_valid_radii": sum(bool(item.get("success")) for item in init_receipts),
                "initializer_planned_radii": len(two_state.R_VALUES),
                "initializer_target_operator0_abs": init_target,
                "fixed_chart": _fit_denominator(panel_fit_rows, "fixed_operator0"),
                "pivot_chart": _fit_denominator(panel_fit_rows, "largest_component_pivot"),
                "covariance_condition_number": covariance_diagnostics["condition_number"],
            }
            panel_rows.append(panel_row)
            status["completed_panels"] += 1
            status["completed_chart_fits"] = len(fit_rows)
            _write_json(status_path, status)
            # Persist full row details after each panel so a later report error
            # cannot erase the completed fits from the only copy in memory.
            _write_csv(out / "source_capture.csv", capture_rows)
            _write_csv(out / "nt32_initializer_fits.csv", initializer_rows)
            _write_csv(out / "fit_results.csv", fit_rows)
            _write_csv(out / "panel_summary.csv", panel_rows)
    except Exception as exc:
        status.update({
            "status": "ABORTED_DURING_RUN", "error": f"{type(exc).__name__}: {exc}",
            "completed_chart_fits": len(fit_rows),
        })
        _write_json(status_path, status)
        raise

    method_counts = {
        method: _fit_denominator(fit_rows, method)
        for method in ("fixed_operator0", "largest_component_pivot")
    }
    by_noise: dict[str, Any] = {}
    for noise in prior_screen.NOISE_LEVELS:
        key = f"{noise:g}"
        by_noise[key] = {}
        for method in method_counts:
            selected = [row for row in fit_rows if row["relative_noise"] == noise
                        and row["method"] == method]
            valid = [row for row in selected if row["valid"]]
            by_noise[key][method] = {
                **_fit_denominator(fit_rows, method, float(noise)),
                "median_initial_target_operator0_abs": float(np.median([
                    row["initializer_target_operator0_abs"] for row in selected
                    if row["initializer_target_operator0_abs"] is not None
                ])) if any(row["initializer_target_operator0_abs"] is not None
                           for row in selected) else None,
                "median_absolute_force_error_lattice_units": float(np.median([
                    row["absolute_force_error_lattice_units"] for row in valid
                    if row["absolute_force_error_lattice_units"] is not None
                ])) if any(row["absolute_force_error_lattice_units"] is not None
                           for row in valid) else None,
                "median_solver_evaluations": float(np.median([
                    row["solver_evaluations"] for row in valid
                ])) if valid else None,
                "initializer_out_of_bounds_abstentions": sum(
                    row["status"] == "ABSTAIN_INITIALIZER_OUT_OF_BOUNDS" for row in selected
                ),
            }
    paired_both = sum(
        all(next(row for row in fit_rows if row["panel_id"] == panel_id
                 and row["start_index"] == start and row["method"] == method)["valid"]
            for method in method_counts)
        for panel_id in protocol["panel_ids"] for start in range(len(STARTS))
    )
    initializer_summary = {
        "planned": len(initializer_rows),
        "valid": sum(bool(row.get("success")) for row in initializer_rows),
        "failed": sum(not bool(row.get("success")) for row in initializer_rows),
        "abstained": 0,
    }
    summary = {
        "schema": "wilson-f-exact-zero-nt32-initializer-summary-v1",
        "status": "NT32_INITIALIZER_SCREEN_COMPLETE",
        "classification": "method feasibility on reused open synthetic matrices; not independent replication or calibration",
        "certified": False, "physical_score": None,
        "panel_denominator": {"planned": len(protocol["panel_ids"]),
                              "valid": sum(row["initializer_valid_radii"] == len(two_state.R_VALUES)
                                           for row in panel_rows),
                              "failed": 0, "abstained": sum(
                                  row["initializer_valid_radii"] != len(two_state.R_VALUES)
                                  for row in panel_rows)},
        "source_capture_denominator": {
            "planned": len(capture_rows),
            "valid": sum(row["status"] == "valid" for row in capture_rows),
            "failed": sum(row["status"] == "failed" for row in capture_rows),
            "abstained": sum(row["status"] == "abstained" for row in capture_rows),
        },
        "nt32_initializer_denominator": initializer_summary,
        "fit_denominators_by_method": method_counts,
        "fit_denominators_by_noise": by_noise,
        "paired_starts_both_valid": paired_both,
        "paired_starts_planned": len(protocol["panel_ids"]) * len(STARTS),
        "truth_target_operator0_amplitude": 0.0,
        "initializer_operator0_lower_bound": 1e-8,
        "fixed_full_fit_operator0_log_lower_bound": -12.0,
        "fixed_full_fit_minimum_nonzero_operator0_amplitude": float(np.exp(-12.0)),
        "truth_absolute_force_lattice_units": truth_force,
        "scope_limits": [
            "same nine panels as the preceding oracle-start screen; no new seeds",
            "initial guesses are fitted from Nt=32 data, but Nt=32 itself is a noisy truncated single-vacuum initializer",
            "only 3 paired starts per panel and 3 seeds per noise level",
            "no profile coverage, production convention validation, physical contamination bound, GPU, or QUDA",
        ],
    }
    _write_csv(out / "source_capture.csv", capture_rows)
    _write_csv(out / "nt32_initializer_fits.csv", initializer_rows)
    _write_csv(out / "fit_results.csv", fit_rows)
    _write_csv(out / "panel_summary.csv", panel_rows)
    _write_json(out / "summary.json", summary)
    _plot(out / "initializer_chart_comparison.png", fit_rows, initializer_rows, truth_force)
    _write_readme(out / "README.md", summary, input_artifact_map_sha256)
    source_paths = {
        "tasks/wilson_loop/f_lane_pivot_chart_nt32_initializer_screen.py": Path(__file__),
        "tasks/wilson_loop/f_lane_pivot_chart_exact_zero_multireplicate_screen.py": Path(prior_screen.__file__),
        "tasks/wilson_loop/f_lane_pivot_chart_exact_zero_screen.py": Path(exact_zero.__file__),
        "tasks/wilson_loop/f_lane_pivot_chart_fit_comparison.py": Path(fit_comparison.__file__),
        "tasks/wilson_loop/f_lane_three_static_pivot_chart.py": Path(pivot.__file__),
        "tasks/wilson_loop/f_lane_three_static_two_vacuum_candidate.py": Path(current.__file__),
        "tasks/wilson_loop/f_lane_two_sector_fit_candidate.py": Path(two_state.__file__),
        "tasks/wilson_loop/f_lane_joint_spectral_gls_diagnostic.py": Path(initializer.__file__),
        "tasks/wilson_loop/lane_contract_v2.json": TASK_DIR / "lane_contract_v2.json",
        "core/source_integrity.py": REPO_ROOT / "core/source_integrity.py",
        "core/npz_safety.py": REPO_ROOT / "core/npz_safety.py",
    }
    _write_json(out / "source_hashes.json", {
        name: _sha_file(path) for name, path in source_paths.items()
    })
    artifacts = [
        "README.md", "protocol.json", "dgp_design.json", "summary.json",
        "execution_progress.jsonl", "source_capture.csv", "nt32_initializer_fits.csv",
        "fit_results.csv", "panel_summary.csv", "initializer_chart_comparison.png", "source_hashes.json",
    ]
    _write_json(out / "artifact_hashes.json", {
        name: _sha_file(out / name) for name in artifacts
    })
    status.update({"status": "COMPLETE", "completed_chart_fits": len(fit_rows),
                   "error": None})
    _write_json(status_path, status)
    return summary


def _plot(path: Path, fit_rows: list[dict[str, Any]],
          init_rows: list[dict[str, Any]], truth_force: float) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13.8, 4.6))
    methods = ("fixed_operator0", "largest_component_pivot")
    labels = ("fixed operator 0", "largest-component pivot")
    colors = ("#3978a8", "#d07a2d")
    width = 0.34
    xs = np.arange(len(prior_screen.NOISE_LEVELS))
    for offset, method, label, color in zip((-width / 2, width / 2), methods, labels, colors):
        rates = []
        for noise in prior_screen.NOISE_LEVELS:
            selected = [row for row in fit_rows if row["method"] == method
                        and row["relative_noise"] == noise]
            rates.append(sum(bool(row["valid"]) for row in selected) / len(selected))
        axes[0].bar(xs + offset, rates, width, color=color, label=label)
    axes[0].set_xticks(xs, [f"{n:g}" for n in prior_screen.NOISE_LEVELS])
    axes[0].set_ylim(0, 1.05)
    axes[0].set_xlabel("relative matrix noise")
    axes[0].set_ylabel("valid fits / 9 planned")
    axes[0].set_title("Fit completion after Nt=32 start")
    axes[0].legend(frameon=False, fontsize=7)

    for method, label, color in zip(methods, labels, colors):
        for noise_i, noise in enumerate(prior_screen.NOISE_LEVELS):
            selected = [row for row in fit_rows if row["method"] == method
                        and row["relative_noise"] == noise
                        and row["start_index"] == 0]
            points = [row for row in selected
                      if row["initializer_target_operator0_abs"] is not None]
            if points:
                axes[1].scatter(
                    [noise_i + (-0.06 if method == methods[0] else 0.06)] * len(points),
                    [row["initializer_target_operator0_abs"] for row in points],
                    color=color, marker="o" if method == methods[0] else "s", s=25,
                    alpha=0.8, label=label if noise_i == 0 else None,
                )
    axes[1].axhline(1e-8, color="#777777", linestyle=":", label="Nt=32 initializer floor")
    axes[1].axhline(np.exp(-12.0), color="#222222", linestyle="--", label="fixed full-fit lower bound")
    axes[1].set_yscale("log")
    axes[1].set_xticks(xs, [f"{n:g}" for n in prior_screen.NOISE_LEVELS])
    axes[1].set_xlabel("relative matrix noise")
    axes[1].set_ylabel(r"Nt=32 initialized $|Z_0|$ at target transition")
    axes[1].set_title("Initializer vs fixed-chart domain")
    axes[1].legend(frameon=False, fontsize=6)

    for method, label, color in zip(methods, labels, colors):
        medians, spreads = [], []
        for noise in prior_screen.NOISE_LEVELS:
            values_by_seed = []
            for seed in prior_screen.PANEL_SEEDS:
                values = [row["absolute_force_error_lattice_units"] for row in fit_rows
                          if row["method"] == method and row["relative_noise"] == noise
                          and row["seed"] == seed and row["valid"]
                          and row["absolute_force_error_lattice_units"] is not None]
                if values:
                    values_by_seed.append(float(np.mean(values)))
            medians.append(float(np.median(values_by_seed)) if values_by_seed else np.nan)
            spreads.append(float(np.std(values_by_seed, ddof=1))
                           if len(values_by_seed) > 1 else 0.0)
        axes[2].errorbar(xs, medians, yerr=spreads, marker="o", capsize=3,
                         color=color, label=label)
    axes[2].set_xticks(xs, [f"{n:g}" for n in prior_screen.NOISE_LEVELS])
    axes[2].set_xlabel("relative matrix noise")
    axes[2].set_ylabel("absolute force point error (lattice units)")
    axes[2].set_title(f"Force error (toy truth {truth_force:g})")
    axes[2].legend(frameon=False, fontsize=7)
    fig.suptitle("Exact-zero phase charts with matched-Nt=32 starts; synthetic CPU only")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _write_readme(path: Path, summary: dict[str, Any], input_map_hash: str) -> None:
    fixed = summary["fit_denominators_by_method"]["fixed_operator0"]
    pivoted = summary["fit_denominators_by_method"]["largest_component_pivot"]
    init = summary["nt32_initializer_denominator"]
    rows = [
        "# Exact-zero phase-chart screen with matched-Nt=32 initialization",
        "",
        "**Classification:** reused open synthetic panels; initializer/fit feasibility only, not a coverage or physical study.",
        "",
        "![Matched-Nt=32 initializer and phase-chart comparison](initializer_chart_comparison.png)",
        "",
        "## Data flow",
        "",
        "`hash-bound exact-zero 96-block matrices -> capture manifest/NPZ/contract -> fit a 3-state, 3-operator spectrum at Nt=32 separately for each R -> use fitted energies/overlaps (no oracle starts) -> paired fixed/pivot full finite-Nt 2-vacuum x 3-static point fits -> preserve all initializer and chart outcomes`.",
        "",
        f"The source artifact-manifest SHA-256 is `{input_map_hash}`. The immutable source capture is **{summary['source_capture_denominator']['valid']}/{summary['source_capture_denominator']['planned']}** files. Per-R Nt=32 initializer fits: `{init['planned']}/{init['valid']}/{init['failed']}/{init['abstained']}` planned/valid/failed/abstained. Full-fit planned/valid/failed/abstained: fixed `{fixed['planned']}/{fixed['valid']}/{fixed['failed']}/{fixed['abstained']}`; pivot `{pivoted['planned']}/{pivoted['valid']}/{pivoted['failed']}/{pivoted['abstained']}`.",
        "",
        "The Nt=32 initializer's fixed operator-0 amplitude floor is `1e-8`, whereas the full-fit fixed chart requires log amplitude at least `-12` (`|Z_0| >= 6.144e-6`). If an initializer estimate falls below the latter, the fit comparison preserves the fixed-chart start as an out-of-bounds abstention; it does not silently clip the estimate. The pivot chart re-encodes the same physical start and can keep a small operator-0 component as a non-pivot coordinate.",
        "",
        "The figure shows completion fractions, the initialized target overlap against both lower bounds, and per-seed force-error means. Force error bars show the standard deviation across available seed-level means, not an uncertainty interval. Exact toy truth is used only for the final force-error calculation.",
        "",
        "Only three seeds per noise level are used, and these are the same panels as the preceding oracle-start screen. The Nt=32 single-vacuum initializer itself is an approximation to the finite-Nt truth; no independent sample, interval coverage, production convention, contamination bound, GPU, QUDA or physical score is established. See CSVs for all fits, failed initializers and denominators.",
        "",
    ]
    path.write_text("\n".join(rows), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    result = build(args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
