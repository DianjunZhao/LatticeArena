"""Check a per-transition hybrid phase chart on the NT32 boundary panel.

Only transitions whose matched-Nt=32 initializer falls below the fixed
operator-0 log-amplitude bound switch to a largest-component phase pivot.
This reuses one already captured open synthetic panel and makes no coverage or
physical claim.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
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

from tasks.wilson_loop import f_lane_pivot_chart_nt32_initializer_screen as initializer_screen
from tasks.wilson_loop import f_lane_pivot_chart_fit_comparison as fit_comparison
from tasks.wilson_loop import f_lane_three_static_pivot_chart as pivot
from tasks.wilson_loop import f_lane_three_static_two_vacuum_candidate as current
from tasks.wilson_loop import f_lane_two_sector_fit_candidate as two_state


TASK_DIR = Path(__file__).resolve().parent
INPUT_REPORT = TASK_DIR / "f_lane_pivot_chart_exact_zero_nt32_initializer_20261128_v2"
PANEL_ID = "noise_0.0003_seed_202611281128"
DEFAULT_OUT = TASK_DIR / "f_lane_pivot_chart_exact_zero_nt32_hybrid_20261128_v2"
LOG_AMPLITUDE_LOWER = -12.0
AMPLITUDE_FLOOR = float(np.exp(LOG_AMPLITUDE_LOWER))
STARTS = initializer_screen.STARTS
MAX_NFEV = initializer_screen.MAX_NFEV


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty table: {path}")
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def encode_hybrid_chart(parameters: object) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Re-encode a fixed-chart start, pivoting only out-of-domain transitions.

    The pivot map is chosen once from the initializer and stays fixed during
    the optimizer call. Operator 0 remains the phase anchor where its log
    amplitude satisfies the existing full-fit bound; otherwise the largest
    component is used as the anchor.
    """
    p = np.asarray(parameters, dtype=np.float64)
    epsilon, static, overlaps = current._decode(p)
    expected = (len(two_state.R_VALUES), current.VACUUM_STATES,
                current.STATIC_STATES)
    pivot_map = np.zeros(expected, dtype=np.int64)
    encoded = p.copy()
    rows: list[dict[str, Any]] = []
    for ri, radius in enumerate(two_state.R_VALUES):
        radius_start = 1 + ri * pivot.RADIUS_STRIDE
        amplitude_start = radius_start + current.STATIC_STATES
        for mi in range(current.VACUUM_STATES):
            for ni in range(current.STATIC_STATES):
                z = overlaps[ri, mi, ni]
                z0 = float(abs(z[0]))
                in_fixed_domain = z0 > 0.0 and math.log(z0) >= LOG_AMPLITUDE_LOWER
                chosen = 0 if in_fixed_domain else int(np.argmax(np.abs(z)))
                chosen_abs = float(abs(z[chosen]))
                if not math.isfinite(chosen_abs) or chosen_abs <= 0.0:
                    raise ValueError("hybrid chart cannot encode an all-zero transition vector")
                pivot_map[ri, mi, ni] = chosen
                block = amplitude_start + (mi * current.STATIC_STATES + ni) * 5
                rotated = z * np.exp(-1j * np.angle(z[chosen]))
                encoded[block] = math.log(chosen_abs)
                cursor = block + 1
                for operator in range(current.OPERATOR_COUNT):
                    if operator == chosen:
                        continue
                    encoded[cursor] = float(rotated[operator].real)
                    encoded[cursor + 1] = float(rotated[operator].imag)
                    cursor += 2
                rows.append({
                    "R": radius, "vacuum_state": mi, "static_state": ni,
                    "operator0_abs": z0, "fixed_operator0_log_abs": (
                        math.log(z0) if z0 > 0.0 else None
                    ),
                    "fixed_chart_in_domain": in_fixed_domain,
                    "selected_pivot_operator": chosen,
                    "selection_reason": "fixed_operator0_in_domain" if chosen == 0
                    else "largest_component_after_operator0_bound_failure",
                    "selected_pivot_abs": chosen_abs,
                })
    if (not np.isfinite(encoded).all() or pivot_map.shape != expected
            or not np.isfinite(static).all() or not np.isfinite(epsilon)):
        raise ValueError("hybrid chart re-encoding produced invalid coordinates")
    model_difference = float(np.max(np.abs(
        current._model_vectors(p) - pivot.model_vectors(encoded, pivot_map)
    )))
    details = {
        "transitions": rows,
        "model_max_abs_difference": model_difference,
        "operator0_pivot_count": int(np.count_nonzero(pivot_map == 0)),
        "alternate_pivot_count": int(np.count_nonzero(pivot_map != 0)),
        "amplitude_floor": AMPLITUDE_FLOOR,
        "log_amplitude_lower_bound": LOG_AMPLITUDE_LOWER,
    }
    return encoded, pivot_map, details


def _load_baseline_rows(panel_id: str) -> list[dict[str, Any]]:
    rows = []
    with (INPUT_REPORT / "fit_results.csv").open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["panel_id"] == panel_id:
                rows.append(row)
    expected = len(STARTS) * 2
    if len(rows) != expected:
        raise ValueError(f"expected {expected} baseline chart rows for {panel_id}, got {len(rows)}")
    return rows


def _plot(path: Path, rows: list[dict[str, Any]], transitions: list[dict[str, Any]]) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 5.0))
    methods = ["fixed_operator0", "largest_component_pivot", "adaptive_hybrid"]
    labels = ["fixed op0", "largest pivot", "hybrid"]
    colors = ["#3978a8", "#d07a2d", "#4a9b69"]
    valid_counts = [sum(bool(row["valid"]) for row in rows if row["method"] == method)
                    for method in methods]
    abstain_counts = [sum(str(row["status"]).startswith("ABSTAIN")
                          for row in rows if row["method"] == method) for method in methods]
    failed_counts = [len(STARTS) - valid - abstain
                     for valid, abstain in zip(valid_counts, abstain_counts)]
    x = np.arange(3)
    axes[0].bar(x, valid_counts, color=colors, label="valid")
    axes[0].bar(x, failed_counts, bottom=valid_counts, color="#bbbbbb", label="failed")
    axes[0].bar(x, abstain_counts,
                bottom=np.asarray(valid_counts) + np.asarray(failed_counts),
                color="#bd5a5a", label="abstained")
    axes[0].set_xticks(x, labels)
    axes[0].set_ylim(0, len(STARTS) + 0.4)
    axes[0].set_ylabel("fits / 3 planned starts")
    axes[0].set_title("Boundary-panel completion")
    axes[0].legend(frameon=False, fontsize=8)

    ordered = sorted(transitions, key=lambda r: (r["R"], r["vacuum_state"], r["static_state"]))
    transition_labels = [f"R{r['R']} m{r['vacuum_state']} n{r['static_state']}" for r in ordered]
    pivot_ids = [r["selected_pivot_operator"] for r in ordered]
    pivot_colors = [(["#3978a8", "#d07a2d", "#6c64a8"][i]) for i in pivot_ids]
    axes[1].bar(np.arange(len(ordered)), pivot_ids, color=pivot_colors)
    axes[1].set_xticks(np.arange(len(ordered)), transition_labels, rotation=65, ha="right", fontsize=7)
    axes[1].set_yticks([0, 1, 2], ["op0", "op1", "op2"])
    axes[1].set_ylim(-0.45, 2.45)
    axes[1].set_title("Initializer-selected pivot per transition")

    markers = {"fixed_operator0": "o", "largest_component_pivot": "s", "adaptive_hybrid": "^"}
    for method, label, color in zip(methods, labels, colors):
        selected = [row for row in rows if row["method"] == method and row.get("force_error") is not None]
        if selected:
            axes[2].scatter([row["start_index"] for row in selected],
                            [row["force_error"] for row in selected],
                            color=color, marker=markers[method], s=42, label=label)
    axes[2].set_yscale("log")
    axes[2].set_xticks(range(len(STARTS)))
    axes[2].set_xlabel("paired start index")
    axes[2].set_ylabel("absolute toy-force error (lattice units)")
    axes[2].set_title("Point error on reused panel")
    axes[2].legend(frameon=False, fontsize=8)
    fig.suptitle("Per-transition hybrid chart: one synthetic boundary panel")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _write_readme(path: Path, summary: dict[str, Any]) -> None:
    counts = summary["fit_denominators_by_method"]
    hybrids = summary["hybrid_chart"]
    rows = [
        "# Per-transition hybrid phase chart on the matched-Nt=32 boundary panel",
        "",
        "**Classification:** one reused, open synthetic panel; chart feasibility only, not independent confirmation, interval coverage or physical validation.",
        "",
        "![Hybrid chart results](hybrid_chart_comparison.png)",
        "",
        "## Data flow",
        "",
        "`artifact-hash-bound 96-block matrices -> matched-Nt=32 per-R three-state initializer -> for each (R,m,n), keep op0 when log|Z0| >= -12, otherwise pivot on argmax_i |Zi| -> re-encode same start -> full finite-Nt 2-vacuum x 3-static fit -> compare with saved fixed/pivot fits from the same panel and starts`.",
        "",
        f"The captured source package is **{summary['source_capture_denominator']['valid']}/{summary['source_capture_denominator']['planned']}** files. Across the 12 transition vectors, hybrid uses op0 for **{hybrids['operator0_pivot_count']}** and an alternate operator for **{hybrids['alternate_pivot_count']}**. Re-encoding changes the model by at most `{hybrids['model_max_abs_difference']:.3g}` in absolute component units.",
        "",
        "| Chart | Planned | Valid | Failed | Abstained |",
        "|---|---:|---:|---:|---:|",
    ]
    for method, label in (("fixed_operator0", "fixed op0"),
                          ("largest_component_pivot", "largest pivot"),
                          ("adaptive_hybrid", "hybrid")):
        item = counts[method]
        rows.append(f"| {label} | {item['planned']} | {item['valid']} | {item['failed']} | {item['abstained']} |")
    rows += [
        "",
        f"Hybrid force errors for its three paired starts are `{summary['hybrid_force_errors_lattice_units']}` lattice units; saved fixed/pivot point estimates and all full rows are in `paired_results.csv`. These toy errors compare with generator truth only and are not uncertainty estimates.",
        "",
        "The hybrid map is selected once from each initializer transition and remains fixed during that optimizer call; it is not a dynamically switching chart. It tests whether localizing the chart change can retain the fixed chart's coordinates elsewhere while rescuing an out-of-domain component. The full-fit objective, covariance, bounds, solver and validity rule are unchanged.",
        "",
        "This is one panel already used by both preceding exact-zero reports, with three starts and no new seed. It cannot rank charts generally, establish estimator coverage, certify an overlap floor, validate production Wilson conventions, or bound excited-state/thermal contamination. No GPU, QUDA or sealed input was used. C finite-T Creutz and F ground-state force remain separate; both lanes are `NOT_READY/UNCERTIFIED`, F is `GROUND_STATE_FORCE_UNCERTIFIED`, `physical_score=null`, and sealed data remain closed.",
        "",
        "For a next CPU step, predeclare a small untouched synthetic panel set and compare fixed, global pivot and this hybrid map with identical data splits and starts; retain every failed/abstained fit. If hybrid only reduces abstentions while worsening point error or conditioning, keep it as a numerical fallback rather than promoting it to the primary chart.",
        "",
    ]
    path.write_text("\n".join(rows), encoding="utf-8")


def build(output: str | Path = DEFAULT_OUT) -> dict[str, Any]:
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    fit_comparison.MAX_NFEV = MAX_NFEV
    _write_json(out / "protocol.json", {
        "schema": "wilson-f-nt32-hybrid-chart-protocol-v1",
        "classification": "single reused open synthetic panel; chart feasibility only",
        "input_report": INPUT_REPORT.name, "panel_id": PANEL_ID,
        "selection_rule": "for each (R,m,n), retain fixed op0 if log|Z0| >= -12; otherwise select argmax_i |Zi|; map is fixed during that optimizer call",
        "full_fit": "same finite-Nt 2-vacuum x 3-static model, mean covariance, bounds, TRF solver and rank validity rule as the paired NT32 screen",
        "starts_epsilon_excited_scale": [list(row) for row in STARTS],
        "max_nfev": MAX_NFEV, "tolerance": 1e-10,
        "baseline_rows": "read from the hash-bound prior report; not rerun in this pass",
        "physical_score": None, "certified": False,
    })
    source_hash_manifest = initializer_screen.INPUT_REPORT / "artifact_hashes.json"
    source_artifact_hashes = json.loads(source_hash_manifest.read_text(encoding="utf-8"))
    source_manifest_sha256 = _sha_file(source_hash_manifest)
    baseline_hash_manifest = INPUT_REPORT / "artifact_hashes.json"
    baseline_artifact_hashes = json.loads(baseline_hash_manifest.read_text(encoding="utf-8"))
    baseline_manifest_sha256 = _sha_file(baseline_hash_manifest)
    if _sha_file(INPUT_REPORT / "fit_results.csv") != baseline_artifact_hashes["fit_results.csv"]:
        raise ValueError("saved baseline fit rows do not match their report artifact manifest")
    input_summary = json.loads((INPUT_REPORT / "summary.json").read_text(encoding="utf-8"))
    snapshot, manifest, matrices = initializer_screen._capture_panel(PANEL_ID, source_artifact_hashes)
    if manifest.get("split_id") != "F-synthetic-open-exact-zero-0.0003-202611281128":
        raise ValueError("captured panel manifest does not match the frozen boundary panel")
    source_capture_rows = [{
        "panel_id": PANEL_ID, "source_name": name, "status": entry["status"],
        "expected_sha256": entry["expected_sha256"],
        "observed_sha256": entry["observed_sha256"],
    } for name, entry in snapshot.capture_entries.items()]
    if any(row["status"] != "valid" for row in source_capture_rows):
        raise ValueError("panel raw inputs did not match their bound artifact hashes")

    static_guesses, overlap_guesses, init_receipts = initializer_screen._fit_nt32_initializer(matrices)
    if static_guesses is None or overlap_guesses is None:
        raise ValueError("matched-Nt=32 initializer failed; no chart fits were launched")
    init_rows = [{"panel_id": PANEL_ID, **receipt} for receipt in init_receipts]
    fixed_starts: list[np.ndarray] = []
    hybrid_starts: list[np.ndarray] = []
    pivot_maps: list[np.ndarray] = []
    chart_details: list[dict[str, Any]] = []
    for epsilon, excited_scale in STARTS:
        fixed = current._initial_parameters(static_guesses, overlap_guesses, epsilon, excited_scale)
        hybrid, pivot_map, details = encode_hybrid_chart(fixed)
        lower, upper = fit_comparison._bounds()
        if np.any(hybrid < lower) or np.any(hybrid > upper):
            raise ValueError("hybrid re-encoding is outside the unchanged full-fit bounds")
        fixed_starts.append(fixed)
        hybrid_starts.append(hybrid)
        pivot_maps.append(pivot_map)
        chart_details.append(details)
    if any(not np.array_equal(pivot_maps[0], item) for item in pivot_maps[1:]):
        raise ValueError("per-transition pivot choices changed across paired starts")
    model_differences = [item["model_max_abs_difference"] for item in chart_details]
    if max(model_differences) > 2e-12:
        raise ValueError("hybrid re-encoding failed the exact-model identity tolerance")

    observed = two_state._observed_vectors(matrices)
    mean = observed.mean(axis=0)
    covariance, covariance_diagnostics = two_state._regularized_mean_covariance(observed)
    covariance_cholesky = cholesky(covariance, lower=True, check_finite=True)
    lower, upper = fit_comparison._bounds()
    truth_force = float(input_summary["truth_absolute_force_lattice_units"])
    baseline_rows = _load_baseline_rows(PANEL_ID)
    result_rows: list[dict[str, Any]] = []
    for row in baseline_rows:
        method = row["method"]
        result_rows.append({
            "panel_id": PANEL_ID, "start_index": int(row["start_index"]),
            "method": method, "row_source": "verified_saved_Nt32_screen",
            "rerun_this_pass": False, "status": row["status"],
            "valid": row["valid"] == "True", "force": row["force"] or None,
            "force_error": (float(row["absolute_force_error_lattice_units"])
                            if row["absolute_force_error_lattice_units"] else None),
            "nfev": int(row["nfev"]), "njev": int(row["njev"]),
            "rank": int(row["rank"]),
            "condition_number": (float(row["condition_number"])
                                 if row["condition_number"] else None),
            "error": row["error"],
        })
    transition_rows = chart_details[0]["transitions"]
    progress_path = out / "execution_progress.jsonl"
    progress_path.write_text("", encoding="utf-8")
    status = {
        "schema": "wilson-f-nt32-hybrid-chart-execution-v1", "status": "RUNNING",
        "planned_hybrid_fits": len(STARTS), "completed_hybrid_fits": 0,
        "planned_initializer_fits": len(two_state.R_VALUES),
        "completed_initializer_fits": len(init_receipts), "error": None,
    }
    _write_json(out / "execution_status.json", status)
    for start_index, (initial, pivot_map) in enumerate(zip(hybrid_starts, pivot_maps)):
        fit_result = fit_comparison._run_one(
            "largest_component_pivot", initial, pivot_map, mean,
            covariance_cholesky, lower, upper,
        )
        force = fit_result.get("force")
        row = {
            "panel_id": PANEL_ID, "start_index": start_index,
            "epsilon_start": STARTS[start_index][0],
            "excited_overlap_scale_start": STARTS[start_index][1],
            "method": "adaptive_hybrid", "row_source": "new_hybrid_fit",
            "rerun_this_pass": True, "status": fit_result["status"],
            "valid": bool(fit_result["valid"]), "force": force,
            "force_error": abs(float(force) - truth_force) if force is not None else None,
            "nfev": fit_result.get("nfev"), "njev": fit_result.get("njev"),
            "rank": fit_result.get("rank"),
            "condition_number": fit_result.get("condition_number"),
            "objective": fit_result.get("objective"),
            "elapsed_seconds": fit_result.get("elapsed_seconds"),
            "error": fit_result.get("error"),
        }
        result_rows.append(row)
        with progress_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({
                "completed_hybrid_fits": start_index + 1,
                "planned_hybrid_fits": len(STARTS), "start_index": start_index,
                "status": row["status"], "valid": row["valid"],
            }, sort_keys=True) + "\n")
        status["completed_hybrid_fits"] = start_index + 1
        _write_json(out / "execution_status.json", status)

    counts = {}
    for method in ("fixed_operator0", "largest_component_pivot", "adaptive_hybrid"):
        selected = [row for row in result_rows if row["method"] == method]
        valid_count = sum(bool(row["valid"]) for row in selected)
        abstain_count = sum(str(row["status"]).startswith("ABSTAIN") for row in selected)
        counts[method] = {
            "planned": len(selected), "valid": valid_count,
            "failed": len(selected) - valid_count - abstain_count,
            "abstained": abstain_count,
        }
    transition_count = len(transition_rows)
    summary = {
        "schema": "wilson-f-nt32-hybrid-chart-summary-v1",
        "status": "HYBRID_SCREEN_COMPLETE", "certified": False,
        "classification": "single reused open synthetic boundary panel; chart feasibility only",
        "panel_id": PANEL_ID, "seed": 202611281128, "relative_noise": 0.0003,
        "source_panel_artifact_manifest_sha256": source_manifest_sha256,
        "baseline_report_artifact_manifest_sha256": baseline_manifest_sha256,
        "source_capture_denominator": {
            "planned": len(source_capture_rows),
            "valid": sum(row["status"] == "valid" for row in source_capture_rows),
            "failed": sum(row["status"] == "failed" for row in source_capture_rows),
            "abstained": sum(row["status"] == "abstained" for row in source_capture_rows),
        },
        "nt32_initializer_denominator": {
            "planned": len(init_receipts),
            "valid": sum(bool(row.get("success")) for row in init_receipts),
            "failed": sum(not bool(row.get("success")) for row in init_receipts),
        },
        "fit_denominators_by_method": counts,
        "hybrid_chart": {
            "transition_count": transition_count,
            "operator0_pivot_count": chart_details[0]["operator0_pivot_count"],
            "alternate_pivot_count": chart_details[0]["alternate_pivot_count"],
            "model_max_abs_difference": max(model_differences),
            "amplitude_floor": AMPLITUDE_FLOOR,
            "log_amplitude_lower_bound": LOG_AMPLITUDE_LOWER,
            "pivot_map_identical_across_starts": True,
        },
        "hybrid_force_errors_lattice_units": [row["force_error"] for row in result_rows
                                               if row["method"] == "adaptive_hybrid"],
        "covariance_condition_number": covariance_diagnostics["condition_number"],
        "truth_absolute_force_lattice_units": truth_force,
        "physical_score": None,
        "scope_limits": [
            "one panel reused from two preceding method screens; no new seed",
            "three paired initial starts; no finite-sample or interval coverage claim",
            "pivot map is chosen from the matched-Nt=32 initializer and held fixed during each optimizer call",
            "no production convention validation, independent contamination bound, GPU, QUDA or physical result",
        ],
    }
    _write_json(out / "source_panel_artifact_manifest.json", source_artifact_hashes)
    _write_json(out / "baseline_report_artifact_manifest.json", baseline_artifact_hashes)
    _write_csv(out / "source_capture.csv", source_capture_rows)
    _write_csv(out / "nt32_initializer_fits.csv", init_rows)
    _write_csv(out / "hybrid_transition_map.csv", transition_rows)
    _write_csv(out / "paired_results.csv", result_rows)
    _write_json(out / "summary.json", summary)
    _plot(out / "hybrid_chart_comparison.png", result_rows, transition_rows)
    _write_readme(out / "README.md", summary)
    source_paths = {
        "tasks/wilson_loop/f_lane_pivot_chart_nt32_hybrid_screen.py": Path(__file__),
        "tasks/wilson_loop/f_lane_pivot_chart_nt32_initializer_screen.py": Path(initializer_screen.__file__),
        "tasks/wilson_loop/f_lane_pivot_chart_fit_comparison.py": Path(fit_comparison.__file__),
        "tasks/wilson_loop/f_lane_three_static_pivot_chart.py": Path(pivot.__file__),
        "tasks/wilson_loop/f_lane_three_static_two_vacuum_candidate.py": Path(current.__file__),
        "tasks/wilson_loop/f_lane_two_sector_fit_candidate.py": Path(two_state.__file__),
        "core/source_integrity.py": REPO_ROOT / "core/source_integrity.py",
        "core/npz_safety.py": REPO_ROOT / "core/npz_safety.py",
    }
    _write_json(out / "source_hashes.json", {name: _sha_file(path) for name, path in source_paths.items()})
    artifacts = [
        "README.md", "protocol.json", "summary.json", "source_panel_artifact_manifest.json",
        "baseline_report_artifact_manifest.json",
        "execution_progress.jsonl", "source_capture.csv",
        "nt32_initializer_fits.csv", "hybrid_transition_map.csv", "paired_results.csv",
        "hybrid_chart_comparison.png", "source_hashes.json",
    ]
    _write_json(out / "artifact_hashes.json", {name: _sha_file(out / name) for name in artifacts})
    status.update({"status": "COMPLETE", "error": None})
    _write_json(out / "execution_status.json", status)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    result = build(args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
