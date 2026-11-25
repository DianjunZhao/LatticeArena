"""Derive the Wilson F force summary from one immutable source snapshot.

This reader checks the deterministic q/h/x-to-force propagation in the
selected ground-state-force contract. It does not fit the force interval,
prove the positive reference, validate GEVP/thermal receipts, or certify the
physical bounds.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any

from core.source_integrity import SourceByteSnapshot

from .evidence_adapter import _F_ROUTES, apply_wilson_force_gate
from .force_budget import propagate_force_budget
from .lane_contract import LATTICE_FORCE_UNITS


SCHEMA = "wilson-f-force-summary-input-v1"
_REQUIRED = frozenset({
    "schema", "units", "positive_reference_force_lower",
    "statistical_halfwidth", "model_truncation_bound",
    "invalid_force_interval_draws", "invalid_reference_force_draws",
    "qhx_corner_bounds",
})


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f"non-finite JSON constant: {value}")


def _finite_number(value: object, name: str, *, allow_zero: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result) or (result < 0 if allow_zero else result <= 0):
        qualifier = "nonnegative" if allow_zero else "positive"
        raise ValueError(f"{name} must be finite and {qualifier}")
    return result


def _parse_summary_bytes(payload: bytes, source_sha256: str) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        raw = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"force summary is not strict UTF-8 JSON: {type(exc).__name__}") from exc
    if not isinstance(raw, dict) or set(raw) != _REQUIRED:
        actual = sorted(raw) if isinstance(raw, dict) else "non-object root"
        raise ValueError(f"force summary schema keys differ: {actual}")
    if raw.get("schema") != SCHEMA:
        raise ValueError(f"force summary schema must be {SCHEMA!r}")
    if raw.get("units") != LATTICE_FORCE_UNITS:
        raise ValueError(f"force summary units must be {LATTICE_FORCE_UNITS!r}")

    reference = _finite_number(
        raw["positive_reference_force_lower"], "positive_reference_force_lower"
    )
    statistical = _finite_number(
        raw["statistical_halfwidth"], "statistical_halfwidth", allow_zero=True
    )
    model = _finite_number(
        raw["model_truncation_bound"], "model_truncation_bound", allow_zero=True
    )
    invalid_counts = {}
    for name in ("invalid_force_interval_draws", "invalid_reference_force_draws"):
        value = raw[name]
        if type(value) is not int or value < 0:
            raise ValueError(f"{name} must be a nonnegative integer")
        invalid_counts[name] = value

    qhx = raw["qhx_corner_bounds"]
    if not isinstance(qhx, dict) or set(qhx) != {"q", "h", "x"}:
        raise ValueError("qhx_corner_bounds must contain exactly q, h, and x")
    try:
        propagated = propagate_force_budget(
            qhx, reference,
            model_truncation_bound=model,
            statistical_halfwidth=statistical,
        )
    except (TypeError, ValueError, OverflowError, FloatingPointError) as exc:
        raise ValueError(f"q/h/x corner inputs are invalid: {exc}") from exc
    components = {
        "excited_state_force": propagated["component_force_bounds"]["q"],
        "finite_T_thermal": propagated["component_force_bounds"]["h"],
        "mixed": propagated["component_force_bounds"]["x"],
        "spectral_model_truncation": model,
    }
    systematic = math.fsum(components.values())
    derived = {
        "units": LATTICE_FORCE_UNITS,
        "positive_reference_force_lower": reference,
        "statistical_halfwidth": statistical,
        "force_component_bounds": components,
        "systematic_total_bound": systematic,
        "total_linear_bound": systematic + statistical,
        **invalid_counts,
        # This is the digest of the exact captured input bytes. The evidence gate
        # separately checks that every route points to the same digest.
        "summary_sha256": source_sha256,
    }
    diagnostic = {
        "schema": "wilson-f-force-summary-read-v1",
        "status": "DERIVED_FROM_IMMUTABLE_SNAPSHOT",
        "source_read_mode": "immutable_snapshot",
        "source_sha256": source_sha256,
        "positive_reference_force_lower": reference,
        "statistical_halfwidth": statistical,
        "q_h_x_force_unit_bounds": components,
        "model_truncation_bound": model,
        "systematic_total_bound": systematic,
        "total_linear_bound": systematic + statistical,
        "force_budget_recalculation": {
            "component_gates_pass": propagated["component_gates_pass"],
            "model_gate_pass": propagated["model_gate_pass"],
            "statistical_gate_pass": propagated["statistical_gate_pass"],
            "total_gate_pass": propagated["total_gate_pass"],
        },
        "text_flow": [
            "six route snapshots -> parse the identical force-summary bytes",
            "validate units, scalar bounds, invalid-draw counts, and 2x4 q/h/x corners",
            "recompute sum(log1p(q)), sum(log1p(h)), sum(log1p(x)), model, and total bounds",
            "pass the derived summary and the same snapshots to the F evidence gate",
            "complete metadata and bytes can reach draft only; physical score remains null",
        ],
        "limitations": [
            "does not derive force intervals or positive-reference bounds from raw loops",
            "does not validate the GEVP, matched-Nt32 thermal, mixed-sector, or model receipts",
            "does not authenticate input authority, reviewer identity, or independence",
            "does not certify the ground-state force or set a physical score",
        ],
    }
    return derived, diagnostic


def read_force_summary_snapshots(
    snapshots_by_envelope: object,
    required_source_hashes_by_envelope: object,
) -> dict[str, Any]:
    """Read and reconcile the same strict force-summary JSON from all six routes."""
    planned = len(_F_ROUTES)
    if (not isinstance(snapshots_by_envelope, Mapping)
            or set(snapshots_by_envelope) != set(_F_ROUTES)
            or not isinstance(required_source_hashes_by_envelope, Mapping)
            or set(required_source_hashes_by_envelope) != set(_F_ROUTES)):
        return {
            "status": "ABSTAIN_F_SUMMARY_ROUTE_MAP",
            "reason": "F summary reader requires exactly the six selected route snapshots and hash maps",
            "denominator": {"unit": "F force-summary route", "planned": planned,
                            "valid": 0, "failed": 0, "abstained": planned},
            "certified": False, "physical_score": None,
        }

    parsed = []
    valid = failed = abstained = 0
    for route in _F_ROUTES:
        snapshot = snapshots_by_envelope[route]
        route_hashes = required_source_hashes_by_envelope[route]
        if not isinstance(snapshot, SourceByteSnapshot) or not isinstance(route_hashes, Mapping):
            abstained += 1
            continue
        expected = route_hashes.get("force_summary")
        if not isinstance(expected, str) or snapshot.expected_hashes.get("force_summary") != expected:
            failed += 1
            continue
        try:
            payload = snapshot.read_bytes("force_summary")
        except (TypeError, ValueError):
            entry = snapshot.capture_entries.get("force_summary", {})
            if entry.get("status") == "failed":
                failed += 1
            else:
                abstained += 1
            continue
        observed = hashlib.sha256(payload).hexdigest()
        if observed != expected:
            failed += 1
            continue
        valid += 1
        parsed.append((payload, observed))

    denominator = {"unit": "F force-summary route", "planned": planned,
                   "valid": valid, "failed": failed, "abstained": abstained}
    if valid != planned or failed or abstained:
        return {
            "status": "ABSTAIN_F_SUMMARY_SOURCE",
            "reason": "one or more route snapshots did not provide the hash-matched summary bytes",
            "denominator": denominator,
            "certified": False, "physical_score": None,
        }
    payloads = {payload for payload, _ in parsed}
    hashes = {digest for _, digest in parsed}
    if len(payloads) != 1 or len(hashes) != 1:
        return {
            "status": "ABSTAIN_F_SUMMARY_ROUTE_MISMATCH",
            "reason": "the six F routes do not capture one identical force-summary byte sequence",
            "denominator": denominator,
            "bundle_denominator": {"unit": "shared force-summary bundle", "planned": 1,
                                   "valid": 0, "failed": 1, "abstained": 0},
            "certified": False, "physical_score": None,
        }
    digest = parsed[0][1]
    try:
        summary, diagnostic = _parse_summary_bytes(parsed[0][0], digest)
    except ValueError as exc:
        return {
            "status": "ABSTAIN_F_SUMMARY_CONTENT",
            "reason": str(exc), "denominator": denominator,
            "bundle_denominator": {"unit": "shared force-summary bundle", "planned": 1,
                                   "valid": 0, "failed": 1, "abstained": 0},
            "certified": False, "physical_score": None,
        }
    return {
        "status": "F_SUMMARY_READ_NOT_CERTIFIED",
        "summary": summary,
        "diagnostic": diagnostic,
        "denominator": denominator,
        "bundle_denominator": {"unit": "shared force-summary bundle", "planned": 1,
                               "valid": 1, "failed": 0, "abstained": 0},
        "certified": False, "physical_score": None,
    }


def apply_wilson_force_snapshot_gate(
    run_state: object,
    envelopes: object,
    receipt: object,
    *,
    required_source_hashes_by_envelope: object,
    source_snapshots_by_envelope: object,
) -> dict[str, Any]:
    """Derive the F force summary from captured bytes, then run the existing gate."""
    read = read_force_summary_snapshots(
        source_snapshots_by_envelope, required_source_hashes_by_envelope
    )
    if read.get("status") != "F_SUMMARY_READ_NOT_CERTIFIED":
        result = apply_wilson_force_gate(
            run_state, envelopes, receipt, None,
            required_source_hashes_by_envelope=required_source_hashes_by_envelope,
            source_snapshots_by_envelope=source_snapshots_by_envelope,
        )
        result["force_summary_reader"] = read
        return result
    result = apply_wilson_force_gate(
        run_state, envelopes, receipt, read["summary"],
        required_source_hashes_by_envelope=required_source_hashes_by_envelope,
        source_snapshots_by_envelope=source_snapshots_by_envelope,
    )
    result["force_summary_reader"] = {
        "status": read["status"],
        "diagnostic": read["diagnostic"],
        "denominator": read["denominator"],
        "bundle_denominator": read["bundle_denominator"],
        "certified": False,
        "physical_score": None,
    }
    return result
