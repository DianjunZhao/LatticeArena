"""Pion gate for the selected bounded block-risk protocol.

The adapter binds the shared evidence schema to the frozen F=3 score/anchor
defaults and planned denominators. By default it verifies bytes for explicit
source-root/path mappings before a complete bundle can reach ``draft``. This
matches supplied digests only; it does not authenticate digest authority,
reviewer identity, independence, or physical validity, and it does not compute
an LCB or certify a physical score. A passing result is still draft-only.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from core.evidence import (
    apply_evidence_bundle_gate,
    apply_evidence_bundle_gate_with_source_bytes,
    inspect_evidence_envelope,
)
from core.receipts import RECEIPT_SCHEMA, run_receipt as normalize_run_receipt
from .bounded_block_risk_contract import selected_protocol


STAGE = "statistical"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SCORE_SOURCE_KEYS = frozenset({
    "manifest", "score_map", "block_chain_receipt", "gamma_ps_receipt",
    "initial_law_tv_receipt", "review_receipt",
})
_ANCHOR_SOURCE_KEYS = frozenset({
    "manifest", "scalar_map", "coverage_receipt", "common_bias_receipt",
    "independence_receipt", "score_anchor_independence_receipt", "review_receipt",
})


def _sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def score_map_sha256() -> str:
    """Hash the selected bounded score definition in canonical JSON form."""
    protocol = selected_protocol()
    score = protocol["score"]
    payload = {
        "protocol_id": protocol["protocol_id"],
        "prediction_domain": score["prediction_domain"],
        "units": score["units"],
        "R": score["R"],
        "formula": score["formula"],
        "clipping_interval": score["clipping_interval"],
        "failure_policy": score["failure_policy"],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _expected_fields(anchor_scalar_map_id: str,
                     anchor_scalar_map_sha256: str) -> dict[str, dict[str, Any]]:
    protocol = selected_protocol()
    score = protocol["score"]
    family = protocol["comparison_family"]
    dependence = protocol["dependence_design"]
    anchor = protocol["anchor_design"]
    score_hash = score_map_sha256()
    score_family_id = f"{protocol['protocol_id']}/score-F{family['F']}"
    anchor_family_id = f"{protocol['protocol_id']}/anchor"
    return {
        "score": {
            "task": "pion_projection",
            "evidence_kind": "score_dependence",
            "chain.state_unit": "length-5 saved-configuration macroblock",
            "observable.map_id": f"{protocol['protocol_id']}/bounded-score-map",
            "observable.map_sha256": score_hash,
            "observable.support.lower": -1.0,
            "observable.support.upper": 1.0,
            "observable.support.unit": "bounded score",
            "method.name": dependence["method"],
            "dependence.mode": "markov",
            "confidence.family_id": score_family_id,
            "confidence.alpha_total": family["alpha_total"],
            "confidence.alpha_allocated": family["alpha_score"],
            "confidence.family_size": family["F"],
        },
        "anchor": {
            "task": "pion_projection",
            "evidence_kind": "anchor_coverage",
            "chain.state_unit": "independent stationary anchor unit",
            "observable.map_id": anchor_scalar_map_id,
            "observable.map_sha256": anchor_scalar_map_sha256,
            "observable.support.lower": anchor["support_interval"][0],
            "observable.support.upper": anchor["support_interval"][1],
            "observable.support.unit": score["units"],
            "method.name": anchor["method"],
            "dependence.mode": "iid",
            "confidence.family_id": anchor_family_id,
            "confidence.alpha_total": family["alpha_total"],
            "confidence.alpha_allocated": family["alpha_anchor"],
            "confidence.family_size": 1,
        },
    }


def _validate_denominators(receipt: object) -> list[str]:
    reasons: list[str] = []
    if not isinstance(receipt, dict) or receipt.get("schema") != RECEIPT_SCHEMA:
        return [f"receipt.schema must be {RECEIPT_SCHEMA!r}"]
    try:
        normalized = normalize_run_receipt(
            receipt.get("scenario"), receipt.get("denominators"),
            artifact_hashes=receipt.get("artifact_hashes"),
            text_flow=receipt.get("text_flow"),
            reason_rows=receipt.get("reason_rows"),
        )
    except (TypeError, ValueError) as exc:
        return [str(exc)]
    if receipt.get("status") != normalized["status"]:
        reasons.append("receipt.status does not match its denominator counts")
    protocol = selected_protocol()
    family_size = protocol["comparison_family"]["F"]
    planned = {
        "score_family_blocks": (
            protocol["dependence_design"]["planned_scored_blocks"] * family_size
        ),
        "anchor_units": protocol["anchor_design"]["independent_stationary_units_required"],
    }
    if set(normalized["denominators"]) != set(planned):
        reasons.append(
            "statistical receipt denominators must be exactly score_family_blocks and anchor_units"
        )
    for name, expected_count in planned.items():
        counts = normalized["denominators"].get(name)
        if counts is None:
            continue
        if counts["planned"] != expected_count:
            reasons.append(
                f"{name}: planned {counts['planned']}, expected {expected_count}"
            )
        if counts["not_run"] != 0:
            reasons.append(f"{name}: {counts['not_run']} planned units remain not_run")
        if counts["valid"] != expected_count or counts["failed"] or counts["abstained"]:
            reasons.append(
                f"{name}: expected all {expected_count} units to yield a bounded task value"
            )
    return reasons


def _validate_source_hash_routes(value: object) -> list[str]:
    if not isinstance(value, dict) or set(value) != {"score", "anchor"}:
        return ["required_source_hashes_by_envelope must contain exactly score and anchor routes"]
    reasons: list[str] = []
    for route, required in (("score", _SCORE_SOURCE_KEYS), ("anchor", _ANCHOR_SOURCE_KEYS)):
        hashes = value.get(route)
        if not isinstance(hashes, dict):
            reasons.append(f"{route}: required source hashes must be a mapping")
            continue
        missing = sorted(required - set(hashes))
        if missing:
            reasons.append(f"{route}: missing required source hashes {missing}")
        for name, digest in hashes.items():
            if not _sha256(digest):
                reasons.append(f"{route}: source hash {name!r} is not lowercase SHA-256")
    return reasons


def _validate_source_hash_links(envelopes: object,
                                required_hashes: object) -> list[str]:
    if not isinstance(envelopes, dict) or not isinstance(required_hashes, dict):
        return []
    reasons: list[str] = []
    for route in ("score", "anchor"):
        if route not in required_hashes:
            continue
        result = inspect_evidence_envelope(envelopes.get(route), require_review=True)
        if result["status"] != "SCHEMA_COMPLETE_NOT_CERTIFIED":
            continue
        normalized = result["normalized_envelope"]
        hashes = required_hashes[route]
        required = _SCORE_SOURCE_KEYS if route == "score" else _ANCHOR_SOURCE_KEYS
        if not isinstance(hashes, dict) or not required.issubset(hashes):
            continue
        if hashes["manifest"] != normalized["chain"]["manifest_sha256"]:
            reasons.append(f"{route}: required manifest hash does not bind the chain manifest")
        if hashes["review_receipt"] != normalized["review"]["receipt_sha256"]:
            reasons.append(f"{route}: required review hash does not bind the review receipt")
        map_key = "score_map" if route == "score" else "scalar_map"
        if hashes[map_key] != normalized["observable"]["map_sha256"]:
            reasons.append(f"{route}: required observable-map hash does not bind the envelope map")
        if (route == "anchor"
                and hashes["independence_receipt"]
                != normalized["dependence"]["independence_receipt_sha256"]):
            reasons.append("anchor: IID source hash does not bind its independence receipt")
    return reasons


def _validate_protocol_claims(envelopes: object) -> list[str]:
    if not isinstance(envelopes, dict) or set(envelopes) != {"score", "anchor"}:
        return ["evidence bundle must contain exactly score and anchor envelopes"]
    reasons: list[str] = []
    results = {
        route: inspect_evidence_envelope(envelope, require_review=True)
        for route, envelope in envelopes.items()
    }
    for route, result in results.items():
        if result["status"] != "SCHEMA_COMPLETE_NOT_CERTIFIED":
            reasons.extend(f"{route}: {reason}" for reason in result["reasons"])
    if reasons:
        return reasons

    protocol = selected_protocol()
    score = results["score"]["normalized_envelope"]
    anchor = results["anchor"]["normalized_envelope"]
    design = protocol["dependence_design"]
    score_dependence = score["dependence"]
    if score_dependence["gamma_ps_lower"] < design["gamma_ps_lower_bound_requirement"]:
        reasons.append("score: gamma_ps lower bound is below the selected minimum")
    if score_dependence["burn_in"]["count"] < design["burn_in_blocks"]:
        reasons.append("score: burn-in is shorter than the selected block count")
    if score_dependence["tv_bound_after_burn_in"] > design[
        "post_burn_in_tv_bound_per_comparison"
    ]:
        reasons.append("score: post-burn-in TV bound exceeds the selected maximum")
    if anchor["dependence"]["mode"] != "iid":
        reasons.append("anchor: the selected primary route requires bounded IID units")
    return reasons


def apply_pion_statistical_evidence_gate(
    run_state: object,
    envelopes: object,
    receipt: object,
    *,
    anchor_scalar_map_id: str,
    anchor_scalar_map_sha256: str,
    common_bias_bound_over_R: float,
    required_source_hashes_by_envelope: object,
    source_root: str | Path | None = None,
    source_paths_by_envelope: object = None,
    require_source_bytes: bool = True,
) -> dict[str, Any]:
    """Apply the Pion statistical metadata gate and optionally verify bytes.

    The anchor map and evidence source hashes must come from externally reviewed
    receipts. Production use requires an explicit root and per-envelope relative
    path map; synthetic metadata fixtures may opt out. Byte verification only
    checks the currently read bytes and does not authenticate their authority or
    scientific claims. The adapter requires the operator,
    reference and numerical stages to be validated first and accepts only the
    selected 12,000 family-block scores plus 1,000 anchor units. A complete
    result advances ``statistical`` to ``draft`` only.
    """
    if (not hasattr(run_state, "status") or not hasattr(run_state, "summary")
            or not hasattr(run_state, "set") or not hasattr(run_state, "abstain")):
        raise ValueError("run_state must provide status, summary, set and abstain")
    if STAGE not in run_state.status:
        raise ValueError(f"unknown RunState stage {STAGE!r}")
    if run_state.status[STAGE] != "not_run":
        return {
            "status": "ABSTAIN_RUNSTATE_STAGE_ALREADY_USED",
            "reasons": [f"{STAGE} is already {run_state.status[STAGE]}"],
            "run_state": run_state.summary(),
            "certified": False,
            "physical_score": None,
        }
    if not isinstance(require_source_bytes, bool):
        reason = "require_source_bytes must be an explicit boolean"
        run_state.abstain(STAGE, reason)
        return {
            "status": "ABSTAIN_PION_STATISTICAL_ADAPTER",
            "reasons": [reason],
            "run_state": run_state.summary(),
            "certified": False,
            "physical_score": None,
        }

    reasons: list[str] = []
    for stage in ("operator", "reference", "numerical"):
        if run_state.status.get(stage) != "validated":
            reasons.append(f"upstream {stage} stage must be validated before statistical evidence")

    if not isinstance(anchor_scalar_map_id, str) or not anchor_scalar_map_id.strip():
        reasons.append("anchor scalar map ID is missing")
    if not _sha256(anchor_scalar_map_sha256):
        reasons.append("anchor scalar map hash is missing or invalid")
    if (not isinstance(common_bias_bound_over_R, (int, float))
            or isinstance(common_bias_bound_over_R, bool)
            or not math.isfinite(float(common_bias_bound_over_R))
            or common_bias_bound_over_R < 0):
        reasons.append("common-bias bound C/R must be a finite nonnegative number")
    elif common_bias_bound_over_R > selected_protocol()["anchor_design"][
        "common_bias_bound_C_max_over_R"
    ]:
        reasons.append("common-bias bound C/R exceeds the selected maximum")

    reasons.extend(_validate_source_hash_routes(required_source_hashes_by_envelope))
    reasons.extend(_validate_source_hash_links(
        envelopes, required_source_hashes_by_envelope
    ))
    reasons.extend(_validate_denominators(receipt))
    reasons.extend(_validate_protocol_claims(envelopes))
    if reasons:
        run_state.abstain(STAGE, "; ".join(reasons))
        return {
            "status": "ABSTAIN_PION_STATISTICAL_ADAPTER",
            "reasons": reasons,
            "run_state": run_state.summary(),
            "certified": False,
            "physical_score": None,
        }

    expected = _expected_fields(anchor_scalar_map_id, anchor_scalar_map_sha256)
    score_hash = score_map_sha256()
    source_hashes = required_source_hashes_by_envelope
    if source_hashes["anchor"].get("scalar_map") != anchor_scalar_map_sha256:
        reasons.append("anchor scalar map hash does not match its required source hash")
    if source_hashes["score"].get("score_map") != score_hash:
        reasons.append("score map hash does not match the selected bounded score definition")
    if reasons:
        run_state.abstain(STAGE, "; ".join(reasons))
        return {
            "status": "ABSTAIN_PION_STATISTICAL_ADAPTER",
            "reasons": reasons,
            "run_state": run_state.summary(),
            "certified": False,
            "physical_score": None,
        }

    paths_supplied = source_root is not None or source_paths_by_envelope is not None
    if require_source_bytes or paths_supplied:
        if source_root is None or source_paths_by_envelope is None:
            reason = "source-byte gate requires both source_root and source_paths_by_envelope"
            run_state.abstain(STAGE, reason)
            return {
                "status": "ABSTAIN_PION_STATISTICAL_ADAPTER",
                "reasons": [reason],
                "run_state": run_state.summary(),
                "certified": False,
                "physical_score": None,
            }
        return apply_evidence_bundle_gate_with_source_bytes(
            run_state,
            STAGE,
            envelopes,
            receipt,
            source_root=source_root,
            source_paths_by_envelope=source_paths_by_envelope,
            expected_by_envelope=expected,
            required_source_hashes_by_envelope=source_hashes,
            distinct_chain_pairs=(("anchor", "score"),),
        )

    return apply_evidence_bundle_gate(
        run_state,
        STAGE,
        envelopes,
        receipt,
        expected_by_envelope=expected,
        required_source_hashes_by_envelope=source_hashes,
        distinct_chain_pairs=(("anchor", "score"),),
    )
