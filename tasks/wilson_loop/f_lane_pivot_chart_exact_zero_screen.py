"""Fit a finite-Nt synthetic panel with one exact zero operator-0 overlap.

This is a targeted phase-chart feasibility diagnostic, not Wilson production
analysis, interval calibration, or physical-force certification.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
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
from scipy.linalg import cholesky, solve_triangular
from scipy.optimize import least_squares

from core.source_integrity import capture_source_snapshot
from tasks.wilson_loop import f_lane_absolute_force_bootstrap_diagnostic as snapshot_writer
from tasks.wilson_loop import f_lane_finite_nt_trace_diagnostic as toy
from tasks.wilson_loop import f_lane_three_static_pivot_chart as pivot
from tasks.wilson_loop import f_lane_three_static_two_vacuum_candidate as current
from tasks.wilson_loop import f_lane_two_sector_fit_candidate as two_state
from tasks.wilson_loop import f_lane_two_sector_omitted_coverage_diagnostic as noise_source


TASK_DIR = Path(__file__).resolve().parent
DEFAULT_OUT = TASK_DIR / "f_lane_pivot_chart_exact_zero_20261128_v1"
N_BLOCKS = 96
SEED = 202611281128
AR1_RHO = 0.5
RELATIVE_NOISE = 0.003
FIXED_LOG_AMPLITUDE_FLOOR = -12.0
STARTS = ((0.15, 0.20), (0.30, 0.35), (0.55, 0.50))
BASE_EXCITED_SCALE = 0.35
MAX_NFEV = 2000
TOLERANCE = 1e-10
ZERO_TRANSITION = (0, 0, 2)  # R-index, vacuum-state, static-state; operator index is 0.
METHODS = ("fixed_operator0", "largest_component_pivot")


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha_file(path: Path) -> str:
    return _sha(path.read_bytes())


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("cannot write a result table without planned rows")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _truth() -> tuple[np.ndarray, np.ndarray, float]:
    static = np.stack([toy.STATIC_ENERGIES[radius] for radius in two_state.R_VALUES])
    overlaps = np.asarray(toy.TRANSITION_OVERLAPS, dtype=np.complex128).copy()
    overlaps[ZERO_TRANSITION[0], ZERO_TRANSITION[1], ZERO_TRANSITION[2], 0] = 0.0 + 0.0j
    epsilon = float(toy.VACUUM_ENERGIES[1])
    if np.count_nonzero(overlaps[ZERO_TRANSITION] == 0) < 1:
        raise AssertionError("the registered zero-anchor transition was not set exactly to zero")
    if abs(overlaps[ZERO_TRANSITION][1]) == 0 or abs(overlaps[ZERO_TRANSITION][2]) == 0:
        raise AssertionError("the zero-anchor transition must retain nonzero operators 1 and 2")
    return static, overlaps, epsilon


def _generate_matrices(seed: int = SEED) -> tuple[np.ndarray, dict[str, Any]]:
    static, overlaps, epsilon = _truth()
    rng = np.random.default_rng(seed)
    matrices = np.empty(
        (N_BLOCKS, len(two_state.NT_VALUES), len(two_state.R_VALUES),
         len(two_state.T_VALUES), 3, 3), dtype=np.complex128,
    )
    vacuum = np.asarray((0.0, epsilon), dtype=np.float64)
    rho_scale = math.sqrt(1.0 - AR1_RHO ** 2)
    for r_index, _radius in enumerate(two_state.R_VALUES):
        for nt_index, nt in enumerate(two_state.NT_VALUES):
            partition = float(np.sum(np.exp(-vacuum * nt)))
            for t_index, time_extent in enumerate(two_state.T_VALUES):
                weights = np.exp(
                    -vacuum[:, None] * (nt - time_extent)
                    -static[r_index][None, :] * time_extent
                ) / partition
                mean = np.einsum(
                    "mn,mni,mnj->ij", weights, overlaps[r_index],
                    overlaps[r_index].conj(), optimize=True,
                )
                sigma = max(float(np.max(np.abs(mean))) * RELATIVE_NOISE, 1e-9)
                innovations = np.stack([
                    noise_source._hermitian_noise(rng) for _ in range(N_BLOCKS)
                ])
                sequence = np.empty_like(innovations)
                sequence[0] = innovations[0]
                for block in range(1, N_BLOCKS):
                    sequence[block] = (
                        AR1_RHO * sequence[block - 1] + rho_scale * innovations[block]
                    )
                matrices[:, nt_index, r_index, t_index] = mean + sigma * sequence
    protocol_data = {
        "seed": seed, "n_blocks": N_BLOCKS, "ar1_rho": AR1_RHO,
        "relative_noise_per_matrix": RELATIVE_NOISE,
        "truth_vacuum_energies_at": [0.0, epsilon],
        "truth_static_energies_by_R": {
            str(radius): static[index].tolist()
            for index, radius in enumerate(two_state.R_VALUES)
        },
        "exact_zero_transition": {
            "R": two_state.R_VALUES[ZERO_TRANSITION[0]],
            "vacuum_state_m": ZERO_TRANSITION[1],
            "static_state_n": ZERO_TRANSITION[2],
            "operator_index": 0,
            "operator_0_overlap": [0.0, 0.0],
            "operator_1_overlap": [
                float(overlaps[ZERO_TRANSITION][1].real),
                float(overlaps[ZERO_TRANSITION][1].imag),
            ],
            "operator_2_overlap": [
                float(overlaps[ZERO_TRANSITION][2].real),
                float(overlaps[ZERO_TRANSITION][2].imag),
            ],
        },
        "truth_absolute_force_lattice_units": float(static[1, 0] - static[0, 0]),
    }
    return matrices, protocol_data


def _bounds() -> tuple[np.ndarray, np.ndarray]:
    lower = np.full(current.PARAMETER_COUNT, -np.inf)
    upper = np.full(current.PARAMETER_COUNT, np.inf)
    lower[0], upper[0] = -8.0, 2.5
    radius_stride = current.STATIC_STATES + current.VACUUM_STATES * current.STATIC_STATES * 5
    for r_index in range(len(two_state.R_VALUES)):
        radius_start = 1 + r_index * radius_stride
        lower[radius_start:radius_start + current.STATIC_STATES] = -8.0
        upper[radius_start:radius_start + current.STATIC_STATES] = 2.5
        cursor = radius_start + current.STATIC_STATES
        for _ in range(current.VACUUM_STATES * current.STATIC_STATES):
            lower[cursor], upper[cursor] = FIXED_LOG_AMPLITUDE_FLOOR, 4.0
            lower[cursor + 1:cursor + 5] = -5.0
            upper[cursor + 1:cursor + 5] = 5.0
            cursor += 5
    return lower, upper


def _fixed_encode(epsilon: float, static: np.ndarray, overlaps: np.ndarray
                  ) -> tuple[np.ndarray, tuple[int, ...]]:
    """Encode the same components in the operator-0 chart, flooring exact zeros."""
    parameters = np.empty(current.PARAMETER_COUNT, dtype=np.float64)
    parameters[0] = current._inverse_softplus(float(epsilon))
    radius_stride = current.STATIC_STATES + current.VACUUM_STATES * current.STATIC_STATES * 5
    floor_indices = []
    for r_index in range(len(two_state.R_VALUES)):
        radius_start = 1 + r_index * radius_stride
        increments = np.diff(np.concatenate(([0.0], static[r_index])))
        parameters[radius_start:radius_start + current.STATIC_STATES] = [
            current._inverse_softplus(float(value)) for value in increments
        ]
        cursor = radius_start + current.STATIC_STATES
        for m in range(current.VACUUM_STATES):
            for n in range(current.STATIC_STATES):
                vector = overlaps[r_index, m, n]
                if abs(vector[0]) > 0.0:
                    rotated = vector * np.exp(-1j * np.angle(vector[0]))
                    log_a0 = math.log(abs(vector[0]))
                else:
                    pivot_operator = int(np.argmax(np.abs(vector)))
                    if abs(vector[pivot_operator]) == 0.0:
                        raise ValueError("all-zero transition cannot be encoded in fixed chart")
                    rotated = vector * np.exp(-1j * np.angle(vector[pivot_operator]))
                    rotated = rotated.copy()
                    rotated[0] = math.exp(FIXED_LOG_AMPLITUDE_FLOOR)
                    log_a0 = FIXED_LOG_AMPLITUDE_FLOOR
                    if (r_index, m, n) == ZERO_TRANSITION:
                        floor_indices.append(cursor)
                parameters[cursor:cursor + 5] = [
                    log_a0, float(rotated[1].real), float(rotated[1].imag),
                    float(rotated[2].real), float(rotated[2].imag),
                ]
                cursor += 5
    return parameters, tuple(floor_indices)


def _fit_one(method: str, initial: np.ndarray, pivots: np.ndarray | None,
             mean: np.ndarray, covariance_cholesky: np.ndarray,
             lower: np.ndarray, upper: np.ndarray,
             target_index: int) -> dict[str, Any]:
    residual_calls = 0
    jacobian_calls = 0
    model_calls = 0
    fixed_pivots = np.zeros((2, 2, 3), dtype=np.int64)

    def residual(parameters: np.ndarray) -> np.ndarray:
        nonlocal residual_calls, model_calls
        residual_calls += 1
        model_calls += 1
        model = (current._model_vectors(parameters) if method == METHODS[0]
                 else pivot.model_vectors(parameters, pivots))
        return solve_triangular(
            covariance_cholesky, model.ravel() - mean, lower=True, check_finite=True,
        )

    def jacobian(parameters: np.ndarray) -> np.ndarray:
        nonlocal jacobian_calls, model_calls
        jacobian_calls += 1
        model_calls += 1
        pivot_map = fixed_pivots if method == METHODS[0] else pivots
        raw = pivot.model_jacobian(parameters, pivot_map)
        return solve_triangular(covariance_cholesky, raw, lower=True, check_finite=True)

    started = time.perf_counter()
    try:
        fit = least_squares(
            residual, initial, jac=jacobian, bounds=(lower, upper), method="trf",
            x_scale="jac", max_nfev=MAX_NFEV,
            ftol=TOLERANCE, xtol=TOLERANCE, gtol=TOLERANCE,
        )
        elapsed = time.perf_counter() - started
        singular = np.linalg.svd(fit.jac, compute_uv=False)
        rank_tol = singular[0] * max(fit.jac.shape) * np.finfo(float).eps if singular.size else 0.0
        rank = int(np.count_nonzero(singular > rank_tol))
        finite = bool(np.isfinite(fit.fun).all() and np.isfinite(fit.x).all())
        valid = bool(fit.success and finite and rank == current.PARAMETER_COUNT)
        if method == METHODS[0]:
            _, fitted_static, fitted_overlaps = current._decode(fit.x)
        else:
            assert pivots is not None
            _, fitted_static, fitted_overlaps = pivot._decode(fit.x, pivots)
        target_overlap = fitted_overlaps[ZERO_TRANSITION]
        force = float(fitted_static[1, 0] - fitted_static[0, 0])
        return {
            "status": "VALID_FULL_RANK_FIT" if valid else "FAILED_OR_ABSTAINED_FIT",
            "valid": valid, "optimizer_success": bool(fit.success),
            "residual_calls": residual_calls, "jacobian_calls": jacobian_calls,
            "model_calls": model_calls, "nfev": int(fit.nfev), "njev": int(fit.njev or 0),
            "solver_evaluations": int(fit.nfev + (fit.njev or 0)),
            "elapsed_seconds": elapsed,
            "objective": float(np.dot(fit.fun, fit.fun)) if finite else None,
            "rank": rank,
            "condition_number": float(singular[0] / singular[-1]) if singular.size else None,
            "force": force if finite else None,
            "target_operator0_amplitude_abs": float(abs(target_overlap[0])) if finite else None,
            "target_operator0_parameter": float(fit.x[target_index]) if method == METHODS[0] else None,
            "target_pivot_index": int(pivots[ZERO_TRANSITION]) if method != METHODS[0] else 0,
            "error": None if valid else str(fit.message),
        }
    except (ValueError, FloatingPointError, np.linalg.LinAlgError, OverflowError) as exc:
        return {
            "status": "FAILED_OPTIMIZATION", "valid": False,
            "optimizer_success": False, "residual_calls": residual_calls,
            "jacobian_calls": jacobian_calls, "model_calls": model_calls,
            "nfev": 0, "njev": 0, "solver_evaluations": residual_calls + jacobian_calls,
            "elapsed_seconds": time.perf_counter() - started,
            "objective": None, "rank": 0, "condition_number": None,
            "force": None, "target_operator0_amplitude_abs": None,
            "target_operator0_parameter": None, "target_pivot_index": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _plot(path: Path, rows: list[dict[str, Any]], truth_force: float) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.4))
    x = np.arange(len(STARTS))
    width = 0.34
    for offset, method, label, color in (
        (-width / 2, METHODS[0], "fixed operator 0", "#3978a8"),
        (width / 2, METHODS[1], "largest-component pivot", "#d07a2d"),
    ):
        selected = [row for row in rows if row["method"] == method]
        axes[0].bar(
            x + offset, [int(row["valid"]) for row in selected], width,
            label=label, color=color,
        )
    axes[0].set_xticks(x, [f"start {i}" for i in range(len(STARTS))])
    axes[0].set_ylim(0, 1.2)
    axes[0].set_ylabel("valid full-rank fit (1=yes)")
    axes[0].set_title("Per-start fit validity")
    axes[0].legend(frameon=False, fontsize=8)

    for method, label, marker, color in (
        (METHODS[0], "fixed operator 0", "o", "#3978a8"),
        (METHODS[1], "largest-component pivot", "s", "#d07a2d"),
    ):
        selected = [row for row in rows if row["method"] == method]
        vals = np.asarray([row["target_operator0_amplitude_abs"] or 0.0 for row in selected])
        axes[1].scatter(np.arange(len(vals)), vals, marker=marker, color=color, label=label)
    axes[1].axhline(0.0, color="black", linewidth=1, label="exact truth")
    axes[1].axhline(math.exp(FIXED_LOG_AMPLITUDE_FLOOR), color="#555555",
                    linestyle="--", linewidth=1, label="fixed chart lower bound")
    axes[1].set_yscale("symlog", linthresh=1e-8)
    axes[1].set_xticks(x, [f"start {i}" for i in range(len(STARTS))])
    axes[1].set_ylabel(r"$|Z_0|$ at the exact-zero transition")
    axes[1].set_title("Fitted operator-0 component")
    axes[1].legend(frameon=False, fontsize=7)

    for method, label, color in (
        (METHODS[0], "fixed operator 0", "#3978a8"),
        (METHODS[1], "largest-component pivot", "#d07a2d"),
    ):
        selected = [row for row in rows if row["method"] == method]
        force = [row["force"] if row["force"] is not None else np.nan for row in selected]
        axes[2].plot(x, force, marker="o", color=color, label=label)
    axes[2].axhline(truth_force, color="black", linestyle="--", label="toy truth")
    axes[2].set_xticks(x, [f"start {i}" for i in range(len(STARTS))])
    axes[2].set_ylabel("absolute force (lattice units)")
    axes[2].set_title("Point estimates (diagnostic only)")
    axes[2].legend(frameon=False, fontsize=7)
    for axis in axes:
        axis.grid(axis="y", alpha=0.2)
    fig.suptitle("One exact-zero overlap transition; synthetic CPU screen")
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def _build_protocol(manifest_hash: str, raw_hash: str, contract_hash: str) -> dict[str, Any]:
    return {
        "schema": "wilson-f-exact-zero-pivot-chart-screen-v1",
        "classification": "single-panel oracle-seeded synthetic numerical feasibility screen",
        "source_split": "F-synthetic-open-exact-zero-pivot-v1",
        "source_hashes": {
            "manifest_sha256": manifest_hash,
            "raw_matrices_sha256": raw_hash,
            "lane_contract_sha256": contract_hash,
        },
        "exact_zero_location": {
            "R": 2, "vacuum_state_m": 0, "static_state_n": 2, "operator_index": 0,
        },
        "data_generation": {
            "blocks": N_BLOCKS, "seed": SEED, "ar1_rho": AR1_RHO,
            "relative_noise_per_matrix": RELATIVE_NOISE,
        },
        "paired_methods": list(METHODS),
        "initialization": (
            "oracle toy energies and transition overlaps; vacuum excited overlaps are scaled "
            "by start scale / 0.35; exact-zero vector is represented exactly in pivot chart "
            "and at log-amplitude lower bound -12 in fixed operator-0 chart"
        ),
        "starts_epsilon_excited_scale": [list(row) for row in STARTS],
        "objective": "same regularized covariance-of-block-mean GLS residual for both charts",
        "solver": "scipy least_squares(method=trf, analytic chart Jacobian, x_scale=jac)",
        "max_nfev_per_fit": MAX_NFEV,
        "ftol_xtol_gtol": TOLERANCE,
        "validity": "solver success, finite coordinates/residuals and numerical Jacobian rank 67/67",
        "primary_outputs": [
            "planned/valid/failed/abstained starts per chart",
            "fitted exact-zero transition |Z_0| and fixed chart boundary proximity",
            "nfev/njev, objective, condition number, force point and runtime",
        ],
        "scope_limits": [
            "single deliberately constructed synthetic panel; no population inference",
            "oracle-seeded fit; does not test production initializer behavior",
            "no profile interval or coverage calibration",
            "no production or sealed data, GPU, QUDA, or physical score",
        ],
        "physical_score": None,
        "certified": False,
    }


def build(output: str | Path = DEFAULT_OUT) -> dict[str, Any]:
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    matrices, dgp = _generate_matrices()
    contract_bytes = (TASK_DIR / "lane_contract_v2.json").read_bytes()
    input_root = out / "source_package"
    snapshot, input_hashes = snapshot_writer._snapshot_from_matrices(
        input_root, matrices, contract_bytes, "F-synthetic-open-exact-zero-pivot-v1",
    )
    manifest, validated = two_state._validate_raw_snapshot(
        snapshot, manifest_name="manifest", matrix_name="raw_matrices",
        contract_name="lane_contract",
    )
    if not np.array_equal(validated, matrices):
        raise ValueError("captured synthetic raw matrices differ from the generated panel")
    protocol = _build_protocol(
        input_hashes["manifest"], input_hashes["raw_matrices"], input_hashes["lane_contract"],
    )
    _write_json(out / "protocol.json", protocol)
    _write_json(out / "dgp.json", dgp)

    block_vectors = two_state._observed_vectors(matrices)
    mean = block_vectors.mean(axis=0)
    covariance, covariance_diagnostics = two_state._regularized_mean_covariance(block_vectors)
    chol = cholesky(covariance, lower=True, check_finite=True)
    static, truth_overlaps, epsilon_truth = _truth()
    lower, upper = _bounds()
    radius_stride = current.STATIC_STATES + current.VACUUM_STATES * current.STATIC_STATES * 5
    target_log_index = 1 + ZERO_TRANSITION[0] * radius_stride + current.STATIC_STATES
    target_log_index += (ZERO_TRANSITION[1] * current.STATIC_STATES + ZERO_TRANSITION[2]) * 5
    rows: list[dict[str, Any]] = []
    for start_index, (epsilon_start, excited_scale) in enumerate(STARTS):
        initial_overlaps = truth_overlaps.copy()
        initial_overlaps[:, 1, :, :] *= excited_scale / BASE_EXCITED_SCALE
        try:
            fixed_initial, fixed_floor_indices = _fixed_encode(
                epsilon_start, static, initial_overlaps,
            )
            fixed_init_error = None
        except (ValueError, FloatingPointError, OverflowError) as exc:
            fixed_initial, fixed_floor_indices = None, ()
            fixed_init_error = f"{type(exc).__name__}: {exc}"
        try:
            pivot_initial, pivot_map = pivot.encode_components(
                epsilon_start, static, initial_overlaps,
            )
            pivot_init_error = None
        except (ValueError, FloatingPointError, OverflowError) as exc:
            pivot_initial, pivot_map = None, None
            pivot_init_error = f"{type(exc).__name__}: {exc}"
        initial_model_difference = None
        if fixed_initial is not None and pivot_initial is not None:
            initial_model_difference = float(np.max(np.abs(
                current._model_vectors(fixed_initial)
                - pivot.model_vectors(pivot_initial, pivot_map)
            )))
        for method, initial, pivot_map_value, init_error in (
            (METHODS[0], fixed_initial, None, fixed_init_error),
            (METHODS[1], pivot_initial, pivot_map, pivot_init_error),
        ):
            if init_error is not None or initial is None:
                result = {
                    "status": "ABSTAIN_INITIALIZATION_FAILED", "valid": False,
                    "optimizer_success": False, "residual_calls": 0,
                    "jacobian_calls": 0, "model_calls": 0, "nfev": 0, "njev": 0,
                    "solver_evaluations": 0, "elapsed_seconds": 0.0,
                    "objective": None, "rank": 0, "condition_number": None,
                    "force": None, "target_operator0_amplitude_abs": None,
                    "target_operator0_parameter": None, "target_pivot_index": None,
                    "error": init_error or "initialization failed",
                }
            else:
                result = _fit_one(
                    method, initial, pivot_map_value, mean, chol, lower, upper,
                    target_log_index,
                )
            rows.append({
                "panel_id": "exact_zero_operator0_R2_m0_n2",
                "start_index": start_index, "epsilon_start": epsilon_start,
                "excited_scale_start": excited_scale, "method": method,
                "paired_initial_model_max_abs_difference": initial_model_difference,
                "fixed_boundary_initial_parameter": (
                    fixed_initial[target_log_index] if fixed_initial is not None else None
                ),
                "fixed_floor_transition_parameter_indices": list(fixed_floor_indices),
                **result,
            })
            progress = {
                "completed_fits": len(rows), "planned_fits": len(STARTS) * len(METHODS),
                "start_index": start_index, "method": method,
                "status": result["status"], "valid": result["valid"],
                "nfev": result["nfev"], "njev": result["njev"],
            }
            with (out / "execution_progress.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(progress, sort_keys=True) + "\n")
                stream.flush()
            print(
                f"completed {len(rows)}/{len(STARTS) * len(METHODS)} fits: "
                f"start={start_index} {method} {result['status']}", flush=True,
            )

    result_rows = []
    for method in METHODS:
        group = [row for row in rows if row["method"] == method]
        result_rows.append({
            "method": method, "planned": len(group),
            "valid": sum(bool(row["valid"]) for row in group),
            "failed": sum(row["status"].startswith("FAILED") for row in group),
            "abstained": sum(row["status"].startswith("ABSTAIN") for row in group),
            "valid_force_errors": [
                abs(float(row["force"]) - dgp["truth_absolute_force_lattice_units"])
                for row in group if row["valid"] and row["force"] is not None
            ],
        })
    capture_rows = [
        {"source_name": name, "status": entry["status"],
         "expected_sha256": entry["expected_sha256"],
         "observed_sha256": entry["observed_sha256"]}
        for name, entry in snapshot.capture_entries.items()
    ]
    fixed_valid = next(row for row in result_rows if row["method"] == METHODS[0])
    pivot_valid = next(row for row in result_rows if row["method"] == METHODS[1])
    pivot_target_indexes = sorted({
        row["target_pivot_index"] for row in rows
        if row["method"] == METHODS[1] and row["target_pivot_index"] is not None
    })
    summary = {
        "schema": "wilson-f-exact-zero-pivot-chart-summary-v1",
        "status": "EXACT_ZERO_POINT_FIT_SCREEN_COMPLETE",
        "classification": "single-panel oracle-seeded synthetic fit; diagnostic only",
        "physical_score": None,
        "certified": False,
        "panel_denominator": {"planned": 1, "valid": 1, "failed": 0, "abstained": 0},
        "source_capture_denominator": {
            "planned": len(capture_rows),
            "valid": sum(row["status"] == "valid" for row in capture_rows),
            "failed": sum(row["status"] == "failed" for row in capture_rows),
            "abstained": sum(row["status"] == "abstained" for row in capture_rows),
        },
        "fit_denominators_by_method": {
            row["method"]: {key: row[key] for key in ("planned", "valid", "failed", "abstained")}
            for row in result_rows
        },
        "paired_starts_both_valid": sum(
            all(next(row for row in rows if row["start_index"] == start and row["method"] == method)["valid"]
                for method in METHODS)
            for start in range(len(STARTS))
        ),
        "largest_component_pivot_indices_at_target": pivot_target_indexes,
        "fixed_chart_lower_bound": FIXED_LOG_AMPLITUDE_FLOOR,
        "fixed_chart_minimum_nonzero_target_amplitude": math.exp(FIXED_LOG_AMPLITUDE_FLOOR),
        "max_initial_chart_model_difference": max(
            float(row["paired_initial_model_max_abs_difference"])
            for row in rows if row["paired_initial_model_max_abs_difference"] is not None
        ),
        "truth_absolute_force_lattice_units": dgp["truth_absolute_force_lattice_units"],
        "covariance_diagnostics": covariance_diagnostics,
        "limitations": [
            "one synthetic data panel and three paired starts; no population inference",
            "oracle energies/overlaps are used to construct paired initial values",
            "does not test the production Nt=32 initializer, profile coverage, or contamination bounds",
            "no production/sealed data, GPU, QUDA, or physical score",
        ],
    }
    _write_csv(out / "fit_results.csv", rows)
    _write_csv(out / "source_capture.csv", capture_rows)
    _write_json(out / "fit_denominators.json", {row["method"]: row for row in result_rows})
    _write_json(out / "summary.json", summary)
    _plot(out / "exact_zero_comparison.png", rows, dgp["truth_absolute_force_lattice_units"])
    _write_readme(out / "README.md", summary, rows, result_rows)

    sources = {
        "tasks/wilson_loop/f_lane_pivot_chart_exact_zero_screen.py": Path(__file__),
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
    _write_json(out / "source_hashes.json", {name: _sha_file(path) for name, path in sources.items()})
    artifact_files = [
        "README.md", "protocol.json", "dgp.json", "summary.json", "fit_denominators.json",
        "fit_results.csv", "source_capture.csv", "execution_progress.jsonl",
        "exact_zero_comparison.png", "source_hashes.json",
        "source_package/manifest.json", "source_package/raw_matrices.npz",
        "source_package/lane_contract.json",
    ]
    _write_json(out / "artifact_hashes.json", {
        name: _sha_file(out / name) for name in artifact_files
    })
    return summary


def _write_readme(path: Path, summary: dict[str, Any], rows: list[dict[str, Any]],
                  denominators: list[dict[str, Any]]) -> None:
    denoms = summary["fit_denominators_by_method"]
    lines = [
        "# Exact-zero operator-0 phase-chart fit screen",
        "",
        "**Classification:** one oracle-seeded, open synthetic panel for numerical feasibility only. This is not profile coverage or a physical force result.",
        "",
        "![Exact-zero phase-chart fit comparison](exact_zero_comparison.png)",
        "",
        "## Frozen synthetic panel and fits",
        "",
        "The DGP uses the existing positive finite-`N_t` 2-vacuum × 3-static toy with one exact zero transition component `Z_0(R=2,m=0,n=2)=0`; the other two operator components remain nonzero. It contains 96 correlated AR(1) blocks (`rho=0.5`), one fixed seed and 0.3% relative matrix noise. Both charts use the same sampled matrix mean, regularized covariance, three paired starts, analytic Jacobian, TRF, `x_scale='jac'`, `max_nfev=2000`, and `1e-10` tolerances. The initial energies/overlaps are oracle-derived from this synthetic DGP, not estimated from data.",
        "",
        f"- Source snapshot files: `{summary['source_capture_denominator']['planned']}/{summary['source_capture_denominator']['valid']}/{summary['source_capture_denominator']['failed']}/{summary['source_capture_denominator']['abstained']}` (planned/valid/failed/abstained).",
        f"- Fixed operator-0 fits: `{denoms[METHODS[0]]['planned']}/{denoms[METHODS[0]]['valid']}/{denoms[METHODS[0]]['failed']}/{denoms[METHODS[0]]['abstained']}`.",
        f"- Largest-component pivot fits: `{denoms[METHODS[1]]['planned']}/{denoms[METHODS[1]]['valid']}/{denoms[METHODS[1]]['failed']}/{denoms[METHODS[1]]['abstained']}`.",
        f"- Both charts valid for `{summary['paired_starts_both_valid']}/{len(STARTS)}` paired starts.",
        f"- At the target transition the pivot chart selects operator indices `{summary['largest_component_pivot_indices_at_target']}`; the fixed chart imposes `|Z_0| >= exp(-12) = {summary['fixed_chart_minimum_nonzero_target_amplitude']:.3g}`.",
        f"- Maximum initial model difference between paired coordinates: `{summary['max_initial_chart_model_difference']:.3g}`.",
        "",
        "## What this establishes",
        "",
        "The pivot chart can place an exact zero in its non-pivot operator coordinate while retaining the positive spectral outer product. The fixed chart is strictly positive in operator 0 at finite coordinates and represents this DGP only by approaching its configured lower bound. The fit outcomes show whether the local solver reached acceptable solutions under these fixed starts; three fits are not a convergence-rate or coverage estimate.",
        "",
        "## Limits and reproduction",
        "",
        "This single DGP does not test the measured-`N_t=32` initializer, production overlap conventions, profile intervals, finite-sample coverage, contamination bounds, GPU/QUDA, or a physical force. Every failure remains in `fit_results.csv`. Raw synthetic matrices, manifest and lane contract are retained in `source_package/`; source and artifact SHA-256 maps bind this local report.",
        "",
        "Run `python tasks/wilson_loop/f_lane_pivot_chart_exact_zero_screen.py --output <new-empty-directory>`. The no-clobber output includes the frozen protocol, per-fit progress, raw input snapshot, denominator table, figure and hashes.",
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
