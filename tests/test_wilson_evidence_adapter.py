"""CPU-only structural and numerical checks for Wilson lane adapters."""
from __future__ import annotations

import hashlib
import json

from core.evidence import evidence_envelope
from core.receipts import denominator, run_receipt, scenario_spec
from core.state import RunState
from tasks.wilson_loop.evidence_adapter import (
    CONTRACT_PATH,
    _F_UNITS,
    _F_ROUTES,
    apply_wilson_creutz_gate,
    apply_wilson_force_gate,
    creutz_map_sha256,
    force_map_sha256,
)
from tasks.wilson_loop.lane_contract import selected_protocol


H = [f"{i:064x}" for i in range(1, 60)]
PAIRED_DRAWS = 30_000


def _review(digest):
    return {
        "status": "reviewed", "receipt_sha256": digest,
        "scope_sha256": H[40], "reviewer_role_claim": "independent",
        "independence_claim_sha256": H[41],
    }


def _receipt(name, denominators):
    return run_receipt(
        scenario_spec(name, "planned lane adapter unit", "synthetic contract fixture"),
        denominators,
        artifact_hashes={"fixture": H[42]},
        text_flow="lane inputs -> task envelope(s) -> exact denominator check -> draft or abstain",
    )


def _ready_state(*stages):
    state = RunState()
    for stage in stages:
        state.set(stage, "draft", evidence=f"fixture {stage}")
        state.set(stage, "validated", evidence_hash=H[43])
    return state


def _creutz_fixture(*, split="C-calibration-open", halfwidth=0.01):
    hashes = {
        "manifest": H[0], "loop_map": creutz_map_sha256(),
        "loop_measurements": H[1], "dependence_receipt": H[2],
        "coverage_calibration_receipt": H[3], "interval_summary": H[4],
        "review_receipt": H[5], "authorization_receipt": H[6],
    }
    envelope = evidence_envelope(
        "wilson_loop", "finite_t_creutz_interval",
        chain={
            "chain_id": "C-lane-calibration-chain", "split_id": split,
            "state_unit": "paired saved gauge configuration",
            "manifest_sha256": hashes["manifest"],
        },
        observable={
            "map_id": "wilson-finite-t-creutz-R2-T5-stout-v1",
            "map_sha256": hashes["loop_map"],
            "support": {
                "lower": -1.0, "upper": 1.0,
                "unit": "dimensionless finite-T Creutz observable",
            },
        },
        method={
            "name": "paired_circular_block_bootstrap_hull",
            "version": "selected-10000x3-v1",
            "assumptions": ["four loop means are paired within each saved configuration"],
        },
        dependence={
            "mode": "markov", "assumptions": ["production chain is homogeneous"],
            "gamma_ps_lower": 0.3, "tv_bound_after_burn_in": 0.001,
            "burn_in": {"unit": "saved gauge configuration", "count": 8},
        },
        confidence={
            "family_id": "wilson-two-lane-selected-v1", "alpha_total": 0.05,
            "alpha_allocated": 0.025, "family_size": 2,
        },
        source_hashes=hashes, review=_review(hashes["review_receipt"]),
    )
    receipt = _receipt(
        "wilson-finite-t-creutz-calibration",
        {
            "four_required_loop_means": denominator("required paired loop mean", planned=4, valid=4),
            "paired_bootstrap_draws": denominator("paired circular-block draw", planned=PAIRED_DRAWS, valid=PAIRED_DRAWS),
        },
    )
    summary = {
        "hull_lower": 0.09, "hull_upper": 0.11,
        "halfwidth": halfwidth, "invalid_draws": 0,
        "planned_draws": PAIRED_DRAWS,
        "units": "dimensionless",
        "summary_sha256": hashes["interval_summary"],
    }
    return envelope, receipt, summary, hashes


def _force_fixture():
    envelopes = {}
    routes = {}
    summary_hash = H[7]
    review_hash = H[8]
    authorization_hash = H[9]
    gevp_hash = H[10]
    for index, route in enumerate(_F_ROUTES):
        hashes = {
            "manifest": H[11] if route in ("force_interval", "positive_reference") else H[11 + index],
            "observable_map": force_map_sha256(route),
            "data_receipt": H[19 + index],
            "force_summary": summary_hash,
            "review_receipt": review_hash,
            "authorization_receipt": authorization_hash,
        }
        if route in ("force_interval", "positive_reference"):
            hashes.update({"dependence_receipt": H[27], "coverage_calibration_receipt": H[28]})
        else:
            hashes.update({
                "gevp_receipt": gevp_hash,
                "component_receipt": H[29 + index],
                "propagation_receipt": H[30 + index],
            })
            if route == "h_thermal_nt32":
                hashes["matched_nt32_receipt"] = H[36]
        routes[route] = hashes
        if route in ("force_interval", "positive_reference"):
            chain_id = "paired-F-calibration-chain"
            split_id = "F-calibration-open"
            state_unit = "paired saved gauge configuration"
            mode = "markov"
            confidence = {
                "family_id": "wilson-two-lane-selected-v1/F/statistical",
                "alpha_total": 0.0125,
                "alpha_allocated": 0.00625,
                "family_size": 2,
            }
        else:
            chain_id = f"{route}-spectral-chain"
            split_id = f"F-calibration-{route}"
            state_unit = "spectral fit cell"
            mode = "markov" if route == "h_thermal_nt32" else "spectral"
            cells = 4 if route == "spectral_model_truncation" else 8
            confidence = {
                "family_id": "wilson-two-lane-selected-v1/F/systematic",
                "alpha_total": 0.0125,
                "alpha_allocated": 0.0125 * cells / 28,
                "family_size": cells,
            }
        if route == "positive_reference":
            support = {"lower": 0.0, "upper": 2.0, "unit": "dimensionless lattice force a_s*a_t*F"}
        elif route == "force_interval":
            support = {"lower": -1.0, "upper": 1.0, "unit": "dimensionless lattice force a_s*a_t*F"}
        elif route in ("q_excited", "h_thermal_nt32", "x_mixed"):
            unit = {
                "q_excited": "dimensionless q bound",
                "h_thermal_nt32": "dimensionless h bound",
                "x_mixed": "dimensionless x bound",
            }[route]
            support = {"lower": 0.0, "upper": 1.0, "unit": unit}
        else:
            support = {"lower": 0.0, "upper": 1.0,
                       "unit": "dimensionless lattice force a_s*a_t*F"}
        dependence = {
            "mode": mode,
            "assumptions": ["source receipt covers the declared route and saved-state unit"],
        }
        if mode == "markov":
            dependence.update({
                "gamma_ps_lower": 0.3,
                "tv_bound_after_burn_in": 0.001,
                "burn_in": {"unit": state_unit, "count": 8},
            })
        envelopes[route] = evidence_envelope(
            "wilson_loop", {
                "force_interval": "ground_state_force_interval",
                "positive_reference": "positive_reference_force",
                "q_excited": "excited_state_q_envelope",
                "h_thermal_nt32": "matched_nt32_thermal_h_envelope",
                "x_mixed": "mixed_sector_x_envelope",
                "spectral_model_truncation": "spectral_model_truncation_envelope",
            }[route],
            chain={
                "chain_id": chain_id, "split_id": split_id,
                "state_unit": state_unit, "manifest_sha256": hashes["manifest"],
            },
            observable={
                "map_id": f"wilson-ground-state-force-R2.5-v1/{route}",
                "map_sha256": hashes["observable_map"], "support": support,
            },
            method={
                "name": "paired_circular_block_bootstrap_hull"
                if route in ("force_interval", "positive_reference")
                else "joint_3x3_finite_Nt_spectral_envelope",
                "version": "selected-F-v1",
                "assumptions": ["force bounds use the frozen candidate-minus-identity stencil"],
            },
            dependence=dependence,
            confidence=confidence,
            source_hashes=hashes,
            review=_review(review_hash),
        )
    receipt = _receipt(
        "wilson-ground-state-force-calibration",
        {
            "force_interval_draws": denominator("force interval paired draw", planned=PAIRED_DRAWS, valid=PAIRED_DRAWS),
            "positive_reference_draws": denominator("positive force reference draw", planned=PAIRED_DRAWS, valid=PAIRED_DRAWS),
            "gevp_fit_variants": denominator("3x3 GEVP fit variant", planned=36, valid=36),
            "force_systematic_cells": denominator("simultaneous force systematic cell", planned=28, valid=28),
            "matched_nt32_thermal_receipts": denominator("matched Nt=32 thermal receipt", planned=1, valid=1),
        },
    )
    summary = {
        "units": "dimensionless lattice force a_s*a_t*F",
        "positive_reference_force_lower": 1.0,
        "statistical_halfwidth": 0.03,
        "force_component_bounds": {
            "excited_state_force": 0.01,
            "finite_T_thermal": 0.01,
            "mixed": 0.005,
            "spectral_model_truncation": 0.005,
        },
        "systematic_total_bound": 0.03,
        "total_linear_bound": 0.06,
        "invalid_force_interval_draws": 0,
        "invalid_reference_force_draws": 0,
        "summary_sha256": summary_hash,
    }
    return envelopes, receipt, summary, routes


def test_creutz_lane_checks_frozen_point_precision_and_keeps_score_null():
    envelope, receipt, summary, hashes = _creutz_fixture()
    state = _ready_state("operator", "numerical")
    result = apply_wilson_creutz_gate(
        state, envelope, receipt, summary, required_source_hashes=hashes,
        require_source_bytes=False,
    )
    assert result["status"] == "DRAFT_PENDING_TASK_VALIDATION"
    assert state.status["statistical"] == "draft"
    assert result["physical_score"] is None
    assert result["certified"] is False


def test_creutz_lane_requires_explicit_source_bytes_by_default():
    envelope, receipt, summary, hashes = _creutz_fixture()
    state = _ready_state("operator", "numerical")
    result = apply_wilson_creutz_gate(
        state, envelope, receipt, summary, required_source_hashes=hashes,
    )
    assert result["status"] == "ABSTAIN_WILSON_C_LANE"
    assert state.status["statistical"] == "abstained"
    assert any("source-byte verification requires" in reason for reason in result["reasons"])
    assert result["source_verification"]["denominator"] == {
        "unit": "source_file", "planned": 8, "valid": 0,
        "failed": 0, "abstained": 8, "not_run": 0,
    }


def test_creutz_lane_verifies_explicit_source_bytes_before_draft(tmp_path):
    envelope, receipt, summary, hashes = _creutz_fixture()
    common_bytes = b"synthetic shared Wilson C receipt"
    (tmp_path / "common.bin").write_bytes(common_bytes)
    common_hash = hashlib.sha256(common_bytes).hexdigest()
    protocol = selected_protocol()
    map_bytes = json.dumps({
        "protocol_id": protocol["protocol_id"],
        "finite_T_Creutz": protocol["finite_T_Creutz"],
        "lane_contract": json.loads(CONTRACT_PATH.read_text())["lanes"]["finite_T_Creutz"],
    }, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(map_bytes).hexdigest() == creutz_map_sha256()
    (tmp_path / "creutz-map.json").write_bytes(map_bytes)

    hashes = {
        name: (creutz_map_sha256() if name == "loop_map" else common_hash)
        for name in hashes
    }
    envelope["chain"]["manifest_sha256"] = common_hash
    envelope["source_hashes"] = hashes
    envelope["review"]["receipt_sha256"] = common_hash
    summary["summary_sha256"] = common_hash
    source_paths = {
        name: ("creutz-map.json" if name == "loop_map" else "common.bin")
        for name in hashes
    }

    state = _ready_state("operator", "numerical")
    result = apply_wilson_creutz_gate(
        state, envelope, receipt, summary,
        required_source_hashes=hashes,
        source_root=tmp_path,
        source_paths=source_paths,
    )
    assert result["status"] == "DRAFT_PENDING_TASK_VALIDATION"
    assert result["source_byte_identity_verified"] is True
    assert result["source_verification"]["denominator"] == {
        "unit": "source_file", "planned": 8, "valid": 8,
        "failed": 0, "abstained": 0, "not_run": 0,
    }

    (tmp_path / "common.bin").write_bytes(b"tampered Wilson C receipt")
    state = _ready_state("operator", "numerical")
    result = apply_wilson_creutz_gate(
        state, envelope, receipt, summary,
        required_source_hashes=hashes,
        source_root=tmp_path,
        source_paths=source_paths,
    )
    assert result["status"] == "ABSTAIN_SOURCE_BYTES"
    assert result["source_verification"]["denominator"] == {
        "unit": "source_file", "planned": 8, "valid": 1,
        "failed": 7, "abstained": 0, "not_run": 0,
    }


def test_creutz_lane_abstains_on_bad_precision_or_closed_split():
    envelope, receipt, summary, hashes = _creutz_fixture(halfwidth=0.021)
    state = _ready_state("operator", "numerical")
    result = apply_wilson_creutz_gate(
        state, envelope, receipt, summary, required_source_hashes=hashes,
        require_source_bytes=False,
    )
    assert result["status"] == "ABSTAIN_WILSON_C_LANE"
    assert state.status["statistical"] == "abstained"
    assert any("halfwidth" in reason for reason in result["reasons"])

    envelope, receipt, summary, hashes = _creutz_fixture(split="C-sealed-confirmation")
    state = _ready_state("operator", "numerical")
    result = apply_wilson_creutz_gate(
        state, envelope, receipt, summary, required_source_hashes=hashes,
        require_source_bytes=False,
    )
    assert result["status"] == "ABSTAIN_WILSON_C_LANE"
    assert any("closed" in reason for reason in result["reasons"])


def test_force_lane_checks_28_systematic_cells_and_force_unit_budget():
    envelopes, receipt, summary, routes = _force_fixture()
    state = _ready_state("operator", "reference", "numerical")
    result = apply_wilson_force_gate(
        state, envelopes, receipt, summary,
        required_source_hashes_by_envelope=routes,
        require_source_bytes=False,
    )
    assert result["status"] == "DRAFT_PENDING_TASK_VALIDATION"
    assert state.status["statistical"] == "draft"
    assert len(result["envelope_results"]) == 6
    assert result["physical_score"] is None


def test_force_lane_requires_explicit_source_bytes_by_default():
    envelopes, receipt, summary, routes = _force_fixture()
    state = _ready_state("operator", "reference", "numerical")
    result = apply_wilson_force_gate(
        state, envelopes, receipt, summary,
        required_source_hashes_by_envelope=routes,
    )
    assert result["status"] == "ABSTAIN_WILSON_F_LANE"
    assert state.status["statistical"] == "abstained"
    assert any("source-byte verification requires" in reason for reason in result["reasons"])
    assert result["source_verification"]["denominator"]["planned"] == sum(
        len(route_hashes) for route_hashes in routes.values()
    )
    assert result["source_verification"]["denominator"]["abstained"] == sum(
        len(route_hashes) for route_hashes in routes.values()
    )


def test_force_lane_verifies_all_route_source_bytes_atomically(tmp_path):
    envelopes, receipt, summary, routes = _force_fixture()
    common_bytes = b"synthetic shared Wilson F receipt"
    (tmp_path / "common.bin").write_bytes(common_bytes)
    common_hash = hashlib.sha256(common_bytes).hexdigest()
    protocol = selected_protocol()
    force = protocol["ground_state_discrete_static_force"]
    source_paths = {}

    for route, envelope in envelopes.items():
        map_bytes = json.dumps({
            "protocol_id": protocol["protocol_id"],
            "estimand": force["estimand"],
            "formula": force["formula"],
            "units": force["units"],
            "error_propagation": force["error_propagation"],
            "spectral_evidence_plan": force["spectral_evidence_plan"],
            "role": route,
            "support_unit": _F_UNITS[route],
        }, sort_keys=True, separators=(",", ":")).encode()
        assert hashlib.sha256(map_bytes).hexdigest() == force_map_sha256(route)
        map_name = f"{route}-map.json"
        (tmp_path / map_name).write_bytes(map_bytes)
        route_hashes = {
            name: (force_map_sha256(route) if name == "observable_map" else common_hash)
            for name in routes[route]
        }
        routes[route] = route_hashes
        envelope["chain"]["manifest_sha256"] = common_hash
        envelope["source_hashes"] = route_hashes
        envelope["review"]["receipt_sha256"] = common_hash
        source_paths[route] = {
            name: (map_name if name == "observable_map" else "common.bin")
            for name in route_hashes
        }

    summary["summary_sha256"] = common_hash
    state = _ready_state("operator", "reference", "numerical")
    result = apply_wilson_force_gate(
        state, envelopes, receipt, summary,
        required_source_hashes_by_envelope=routes,
        source_root=tmp_path,
        source_paths_by_envelope=source_paths,
    )
    assert result["status"] == "DRAFT_PENDING_TASK_VALIDATION"
    assert result["source_byte_identity_verified"] is True
    assert result["source_verification"]["denominator"] == {
        "unit": "source_file", "planned": 53, "valid": 53,
        "failed": 0, "abstained": 0, "not_run": 0,
    }

    (tmp_path / "common.bin").write_bytes(b"tampered Wilson F receipt")
    state = _ready_state("operator", "reference", "numerical")
    result = apply_wilson_force_gate(
        state, envelopes, receipt, summary,
        required_source_hashes_by_envelope=routes,
        source_root=tmp_path,
        source_paths_by_envelope=source_paths,
    )
    assert result["status"] == "ABSTAIN_SOURCE_BYTES"
    assert result["source_verification"]["denominator"] == {
        "unit": "source_file", "planned": 53, "valid": 6,
        "failed": 47, "abstained": 0, "not_run": 0,
    }


def test_force_lane_abstains_without_positive_reference_or_with_overbudget_bounds():
    envelopes, receipt, summary, routes = _force_fixture()
    summary["positive_reference_force_lower"] = 0.0
    state = _ready_state("operator", "reference", "numerical")
    result = apply_wilson_force_gate(
        state, envelopes, receipt, summary,
        required_source_hashes_by_envelope=routes,
        require_source_bytes=False,
    )
    assert result["status"] == "ABSTAIN_WILSON_F_LANE"
    assert any("positive simultaneous" in reason for reason in result["reasons"])

    envelopes, receipt, summary, routes = _force_fixture()
    summary["force_component_bounds"]["finite_T_thermal"] = 0.02
    summary["systematic_total_bound"] = 0.04
    summary["total_linear_bound"] = 0.07
    state = _ready_state("operator", "reference", "numerical")
    result = apply_wilson_force_gate(
        state, envelopes, receipt, summary,
        required_source_hashes_by_envelope=routes,
        require_source_bytes=False,
    )
    assert result["status"] == "ABSTAIN_WILSON_F_LANE"
    assert any("finite_T_thermal" in reason for reason in result["reasons"])


def test_force_lane_requires_complete_GEVP_thermal_denominators_and_separate_runstate():
    envelopes, receipt, summary, routes = _force_fixture()
    bad = run_receipt(
        receipt["scenario"],
        {
            **receipt["denominators"],
            "gevp_fit_variants": denominator("3x3 GEVP fit variant", planned=36, valid=35, failed=0, abstained=0),
        },
        artifact_hashes=receipt["artifact_hashes"], text_flow=receipt["text_flow"],
        reason_rows=[{
            "unit": "gevp_fit_variants", "state": "not_run", "count": 1,
            "reason": "one planned GEVP variant is missing",
        }],
    )
    state = _ready_state("operator", "reference", "numerical")
    result = apply_wilson_force_gate(
        state, envelopes, bad, summary,
        required_source_hashes_by_envelope=routes,
        require_source_bytes=False,
    )
    assert result["status"] == "ABSTAIN_WILSON_F_LANE"
    assert any("gevp_fit_variants" in reason for reason in result["reasons"])

    envelopes, receipt, summary, routes = _force_fixture()
    state = _ready_state("operator", "reference", "numerical")
    result = apply_wilson_force_gate(
        state, envelopes, receipt, summary,
        required_source_hashes_by_envelope=routes,
        require_source_bytes=False,
    )
    assert result["status"] == "DRAFT_PENDING_TASK_VALIDATION"
