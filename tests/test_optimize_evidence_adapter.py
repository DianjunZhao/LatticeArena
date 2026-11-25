"""CPU-only contracts for Optimize task evidence adapters."""
from __future__ import annotations

import hashlib
from io import BytesIO
import json

import numpy as np

from core.evidence import evidence_envelope
from core.receipts import denominator, run_receipt, scenario_spec
from core.source_integrity import capture_source_snapshot
from core.state import RunState
from tasks.optimize_gaussian.evidence_adapter import (
    _D06_ROUTES,
    apply_optimize_bounded_block_risk_gate,
    apply_optimize_d04_reference_gate,
    apply_optimize_d11_operator_gate,
    bounded_risk_map_sha256,
    d04_reference_map_sha256,
    d11_operator_map_sha256,
)
from tasks.optimize_gaussian.source_reader import (
    SCHEMA as D06_SCORE_SCHEMA,
    apply_bounded_block_risk_snapshot_gate,
)


H = [f"{i:064x}" for i in range(1, 40)]


def _review(receipt):
    return {
        "status": "reviewed", "receipt_sha256": receipt,
        "scope_sha256": H[20], "reviewer_role_claim": "independent",
        "independence_claim_sha256": H[21],
    }


def _receipt(name, denominators):
    return run_receipt(
        scenario_spec(name, "planned CPU adapter contract unit", "synthetic schema fixture"),
        denominators,
        artifact_hashes={"fixture": H[22]},
        text_flow="frozen source/map -> task adapter -> shared metadata gate -> draft or abstain",
    )


def _d04_fixture(*, p_value=0.02):
    hashes = {
        "manifest": H[0],
        "correlator_receipt": H[1],
        "fit_map": d04_reference_map_sha256(),
        "fit_diagnostics": H[2],
        "reference_summary": H[3],
        "dependence_receipt": H[4],
        "review_receipt": H[5],
        "authorization_receipt": H[6],
    }
    envelope = evidence_envelope(
        "optimize_gaussian", "d04_e_chain_reference",
        chain={
            "chain_id": "independent-E-reference-chain",
            "split_id": "E-reference",
            "state_unit": "saved gauge configuration",
            "manifest_sha256": hashes["manifest"],
        },
        observable={
            "map_id": "optimize-d04-joint-reference-v1",
            "map_sha256": hashes["fit_map"],
            "support": {"lower": 0.0, "upper": 0.8, "unit": "a_t m_pi"},
        },
        method={
            "name": "candidate_blind_joint_PP_A4P_two_state_fit",
            "version": "selected-d04-v1",
            "assumptions": ["shared PP/A4P states and frozen fit windows"],
        },
        dependence={
            "mode": "markov", "assumptions": ["exact saved E-chain is homogeneous"],
            "gamma_ps_lower": 0.2, "tv_bound_after_burn_in": 0.001,
            "burn_in": {"unit": "saved gauge configuration", "count": 8},
        },
        confidence={
            "family_id": "optimize-gaussian/D04-reference-fit",
            "alpha_total": 0.05, "alpha_allocated": 0.05, "family_size": 1,
        },
        source_hashes=hashes, review=_review(hashes["review_receipt"]),
    )
    receipt = _receipt(
        "optimize-d04-reference",
        {"reference_fit_variants": denominator(
            "joint PP/A4P fit variant", planned=6, valid=6,
        )},
    )
    summary = {
        "reference_mass": 0.31,
        "reference_mass_error": 0.001,
        "relative_mass_error_max": 0.01,
        "gof_p_min": p_value,
        "max_channel_or_window_shift_paired_se": 1.5,
        "fit_variants": 6,
        "boundary_hit_count": 0,
        "summary_sha256": hashes["reference_summary"],
    }
    return envelope, receipt, summary, hashes


def _d11_fixture(*, split="production-links-calibration", su3=True):
    hashes = {
        "link_manifest": H[7],
        "operator_map": d11_operator_map_sha256(),
        "operator_summary": H[8],
        "kernel_source": H[9],
        "su3_receipt": H[10],
        "review_receipt": H[11],
        "authorization_receipt": H[12],
    }
    envelope = evidence_envelope(
        "optimize_gaussian", "d11_production_operator",
        chain={
            "chain_id": "link-set-calibration-01", "split_id": split,
            "state_unit": "production gauge-link field",
            "manifest_sha256": hashes["link_manifest"],
        },
        observable={
            "map_id": "optimize-d11-degree4-operator-v1",
            "map_sha256": hashes["operator_map"],
            "support": {
                "lower": -12.0, "upper": 0.0,
                "unit": "dimensionless operator spectrum",
            },
        },
        method={
            "name": "degree4_bernstein_chebyshev_clenshaw",
            "version": "selected-d11-v1",
            "assumptions": ["three periodic spatial directions and unitary links"],
        },
        dependence={"mode": "deterministic", "assumptions": ["fixed links and operator map"]},
        confidence={
            "family_id": "optimize-gaussian/D11-operator-contract",
            "alpha_total": 0.05, "alpha_allocated": 0.05, "family_size": 1,
        },
        source_hashes=hashes, review=_review(hashes["review_receipt"]),
    )
    receipt = _receipt(
        "optimize-d11-production-operator",
        {"operator_cases": denominator("production link/operator case", planned=2, valid=2)},
    )
    summary = {
        "production_links": True,
        "su3_provenance_valid": su3,
        "shape_and_periodic_boundary_valid": True,
        "unitarity_valid": True,
        "finite_values_valid": True,
        "bernstein_constraints_valid": True,
        "spectral_interval_valid": True,
        "clenshaw_reference_agrees": True,
        "summary_sha256": hashes["operator_summary"],
    }
    return envelope, receipt, summary, hashes


def _d06_fixtures(*, split="D06-calibration-open", gamma=0.2, tv=0.001):
    envelopes = {}
    routes = {}
    alpha = (0.05 - tv) / 3
    common = {
        "manifest": H[13], "score_matrix": H[14],
        "block_chain_receipt": H[15], "gamma_ps_receipt": H[16],
        "initial_law_tv_receipt": H[17], "budget_receipt": H[24],
    }
    for i, route in enumerate(_D06_ROUTES):
        map_hash = bounded_risk_map_sha256(route)
        source_hashes = {
            **common, "score_map": map_hash,
            "cost_ledger": H[25 + i],
            "review_receipt": H[18], "authorization_receipt": H[19],
        }
        routes[route] = source_hashes
        role = "trainable_w_mean" if route == "trainable_w" else f"contrast:{route}"
        lower, upper = ((0.0, 1.0) if route == "trainable_w" else (-10.0 / 9.0, 1.0))
        envelopes[route] = evidence_envelope(
            "optimize_gaussian", "bounded_block_risk",
            chain={
                "chain_id": "paired-D06-calibration-chain",
                "split_id": split,
                "state_unit": "paired length-5 saved-configuration macroblock",
                "manifest_sha256": common["manifest"],
            },
            observable={
                "map_id": f"optimize-bounded-block-risk-v1/{role}",
                "map_sha256": map_hash,
                "support": {"lower": lower, "upper": upper,
                            "unit": "bounded block-risk summand"},
            },
            method={
                "name": "corrected_markov_pseudo_gap_bernstein_support_only",
                "version": "paulin-corrected-v5",
                "assumptions": ["fixed score map on the paired block-state chain"],
            },
            dependence={
                "mode": "markov", "assumptions": ["homogeneous stationary paired block chain"],
                "gamma_ps_lower": gamma,
                "tv_bound_after_burn_in": tv,
                "burn_in": {"unit": "paired macroblock", "count": 8},
            },
            confidence={
                "family_id": "optimize-bounded-block-risk-v1/F3",
                "alpha_total": 0.05, "alpha_allocated": alpha,
                "family_size": 3,
            },
            source_hashes=source_hashes,
            review=_review(source_hashes["review_receipt"]),
        )
    receipt = _receipt(
        "optimize-d06-bounded-block-risk",
        {
            "paired_macroblocks": denominator("paired macroblock", planned=4, valid=4),
            "assigned_arm_runs": denominator("assigned optimizer arm run", planned=12, valid=12),
        },
    )
    return envelopes, receipt, routes


def _d06_score_matrix_payload(split_id="D06-calibration-open", n_blocks=2000,
                              release_signal=True):
    from tasks.optimize_gaussian.bounded_block_risk import ARMS, TIMES

    q = np.full((n_blocks, len(ARMS), len(TIMES)), 0.8, dtype=np.float64)
    if release_signal:
        q[:, 0, :] = 1.0 - np.sqrt(0.60)
        q[:, 1, :] = 1.0 - np.sqrt(0.90)
        q[:, 2, :] = 1.0 - np.sqrt(0.95)
    else:
        q[:, :, :] = 1.0 - np.sqrt(0.60)
    failures = np.zeros((n_blocks, len(ARMS)), dtype=bool)
    failures[0, 1] = True
    q[0, 1, :] = np.nan
    stream = BytesIO()
    np.savez_compressed(
        stream,
        schema=np.asarray(D06_SCORE_SCHEMA),
        split_id=np.asarray(split_id),
        block_ids=np.arange(200, 200 + n_blocks, dtype=np.int64),
        arm_order=np.asarray(ARMS),
        times=np.asarray(TIMES, dtype=np.int64),
        q_by_block_arm_time=q,
        arm_failure_mask=failures,
    )
    return stream.getvalue()


def _d06_score_map_bytes(route):
    role = "trainable_w_mean" if route == "trainable_w" else f"contrast:{route}"
    support = [0.0, 1.0] if route == "trainable_w" else [-10.0 / 9.0, 1.0]
    payload = {
        "schema": "optimize-bounded-block-risk-markov-v1",
        "role": role,
        "times": [2, 3, 4, 5],
        "score": "mean_t min((q-1)^2,1); assigned-arm solver failure scores 1",
        "contrast": None if route == "trainable_w" else "X_comparator - (10/9)*X_trainable_w",
        "r_star": 10.0 / 9.0,
        "support": support,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _d06_snapshot_bundle(tmp_path, *, release_signal=True):
    envelopes, _, _ = _d06_fixtures(gamma=1.0, tv=0.001)
    n_blocks = 2000
    score_matrix_bytes = _d06_score_matrix_payload(n_blocks=n_blocks,
                                                    release_signal=release_signal)
    routes = {}
    snapshots = {}
    shared_payloads = {
        "manifest": b"synthetic shared manifest",
        "score_matrix": score_matrix_bytes,
        "block_chain_receipt": b"synthetic block-chain receipt",
        "gamma_ps_receipt": b"synthetic gamma receipt",
        "initial_law_tv_receipt": b"synthetic initial-law TV receipt",
        "budget_receipt": b"synthetic shared budget receipt",
        "review_receipt": b"synthetic independent-review declaration",
        "authorization_receipt": b"synthetic authorization declaration",
    }
    for route in _D06_ROUTES:
        route_payloads = {
            **shared_payloads,
            "score_map": _d06_score_map_bytes(route),
            "cost_ledger": f"synthetic cost ledger for {route}".encode(),
        }
        hashes = {name: hashlib.sha256(payload).hexdigest()
                  for name, payload in route_payloads.items()}
        assert hashes["score_map"] == bounded_risk_map_sha256(route)
        routes[route] = hashes
        envelope = envelopes[route]
        envelope["chain"]["manifest_sha256"] = hashes["manifest"]
        envelope["source_hashes"] = hashes
        envelope["review"]["receipt_sha256"] = hashes["review_receipt"]

        route_root = tmp_path / route
        route_root.mkdir()
        paths = {}
        for name, payload in route_payloads.items():
            suffix = ".npz" if name == "score_matrix" else ".json" if name == "score_map" else ".bin"
            filename = f"{name}{suffix}"
            (route_root / filename).write_bytes(payload)
            paths[name] = filename
        snapshots[route] = capture_source_snapshot(route_root, hashes, paths)

    receipt = run_receipt(
        scenario_spec(
            "optimize-d06-bounded-block-risk",
            "planned CPU adapter contract unit",
            "synthetic q-matrix snapshot-reader integration fixture",
        ),
        {
            "paired_macroblocks": denominator("paired macroblock", planned=n_blocks,
                                                valid=n_blocks),
            "assigned_arm_runs": denominator(
                "assigned optimizer arm run", planned=n_blocks * 3,
                valid=n_blocks * 3 - 1, failed=1,
            ),
        },
        artifact_hashes={"fixture": H[22]},
        text_flow="captured q matrix -> paired score reader -> D06 source-byte gate -> draft or abstain",
        reason_rows=[{
            "unit": "assigned_arm_runs", "state": "failed", "count": 1,
            "reason": "synthetic declared optimizer arm failure scored as loss 1",
        }],
    )
    return envelopes, receipt, routes, snapshots


def _upstream_ready():
    state = RunState()
    for stage in ("operator", "reference", "numerical"):
        state.set(stage, "draft", evidence=f"fixture {stage}")
        state.set(stage, "validated", evidence_hash=H[30])
    return state


def test_d04_reference_gate_binds_six_joint_fits_and_stops_at_draft():
    envelope, receipt, summary, hashes = _d04_fixture()
    state = RunState()
    result = apply_optimize_d04_reference_gate(
        state, envelope, receipt, summary, required_source_hashes=hashes,
        require_source_bytes=False,
    )
    assert result["status"] == "DRAFT_PENDING_TASK_VALIDATION"
    assert state.status["reference"] == "draft"
    assert result["physical_score"] is None
    assert result["certified"] is False


def test_d04_reference_gate_requires_explicit_source_bytes_by_default():
    envelope, receipt, summary, hashes = _d04_fixture()
    state = RunState()
    result = apply_optimize_d04_reference_gate(
        state, envelope, receipt, summary, required_source_hashes=hashes,
    )
    assert result["status"] == "ABSTAIN_OPTIMIZE_D04_REFERENCE"
    assert state.status["reference"] == "abstained"
    assert any("source-byte verification requires" in reason for reason in result["reasons"])
    assert result["source_verification"]["denominator"] == {
        "unit": "source_file", "planned": 8, "valid": 0,
        "failed": 0, "abstained": 8, "not_run": 0,
    }


def test_d04_reference_gate_accepts_an_incomplete_read_snapshot_and_abstains(tmp_path):
    envelope, receipt, summary, hashes = _d04_fixture()
    snapshot = capture_source_snapshot(tmp_path, hashes, {})
    state = RunState()
    result = apply_optimize_d04_reference_gate(
        state, envelope, receipt, summary,
        required_source_hashes=hashes, source_snapshot=snapshot,
    )
    assert result["status"] == "ABSTAIN_SOURCE_BYTES"
    assert result["source_verification"]["denominator"] == {
        "unit": "source_file", "planned": 8, "valid": 0,
        "failed": 0, "abstained": 8, "not_run": 0,
    }


def test_d04_reference_gate_abstains_on_failed_fit_criterion_or_stale_summary():
    envelope, receipt, summary, hashes = _d04_fixture(p_value=0.009)
    state = RunState()
    result = apply_optimize_d04_reference_gate(
        state, envelope, receipt, summary, required_source_hashes=hashes,
        require_source_bytes=False,
    )
    assert result["status"] == "ABSTAIN_OPTIMIZE_D04_REFERENCE"
    assert state.status["reference"] == "abstained"

    envelope, receipt, summary, hashes = _d04_fixture()
    summary["summary_sha256"] = H[31]
    state = RunState()
    result = apply_optimize_d04_reference_gate(
        state, envelope, receipt, summary, required_source_hashes=hashes,
        require_source_bytes=False,
    )
    assert result["status"] == "ABSTAIN_OPTIMIZE_D04_REFERENCE"
    assert any("summary hash" in reason for reason in result["reasons"])


def test_d11_operator_gate_requires_real_su3_scope_and_stops_at_draft():
    envelope, receipt, summary, hashes = _d11_fixture()
    state = RunState()
    result = apply_optimize_d11_operator_gate(
        state, envelope, receipt, summary, required_source_hashes=hashes,
        require_source_bytes=False,
    )
    assert result["status"] == "DRAFT_PENDING_TASK_VALIDATION"
    assert state.status["operator"] == "draft"
    assert result["physical_score"] is None

    envelope, receipt, summary, hashes = _d11_fixture(su3=False)
    state = RunState()
    result = apply_optimize_d11_operator_gate(
        state, envelope, receipt, summary, required_source_hashes=hashes,
        require_source_bytes=False,
    )
    assert result["status"] == "ABSTAIN_OPTIMIZE_D11_OPERATOR"
    assert state.status["operator"] == "abstained"


def test_d11_operator_gate_requires_explicit_source_bytes_by_default():
    envelope, receipt, summary, hashes = _d11_fixture()
    state = RunState()
    result = apply_optimize_d11_operator_gate(
        state, envelope, receipt, summary, required_source_hashes=hashes,
    )
    assert result["status"] == "ABSTAIN_OPTIMIZE_D11_OPERATOR"
    assert state.status["operator"] == "abstained"
    assert any("source-byte verification requires" in reason for reason in result["reasons"])
    assert result["source_verification"]["denominator"] == {
        "unit": "source_file", "planned": 7, "valid": 0,
        "failed": 0, "abstained": 7, "not_run": 0,
    }


def test_d11_operator_gate_accepts_snapshot_input_and_keeps_missing_files_abstained(tmp_path):
    envelope, receipt, summary, hashes = _d11_fixture()
    snapshot = capture_source_snapshot(tmp_path, hashes, {})
    result = apply_optimize_d11_operator_gate(
        RunState(), envelope, receipt, summary,
        required_source_hashes=hashes, source_snapshot=snapshot,
    )
    assert result["status"] == "ABSTAIN_SOURCE_BYTES"
    assert result["source_verification"]["denominator"] == {
        "unit": "source_file", "planned": 7, "valid": 0,
        "failed": 0, "abstained": 7, "not_run": 0,
    }


def test_bounded_d06_bundle_gates_both_contrasts_and_shared_denominator():
    envelopes, receipt, routes = _d06_fixtures()
    state = _upstream_ready()
    result = apply_optimize_bounded_block_risk_gate(
        state, envelopes, receipt,
        required_source_hashes_by_envelope=routes,
        require_source_bytes=False,
    )
    assert result["status"] == "DRAFT_PENDING_TASK_VALIDATION"
    assert state.status["statistical"] == "draft"
    assert len(result["envelope_results"]) == 3
    assert result["physical_score"] is None
    assert all(not check["independence_proven"]
               for check in result["chain_identity_checks"])


def test_bounded_d06_bundle_requires_explicit_source_bytes_by_default():
    envelopes, receipt, routes = _d06_fixtures()
    state = _upstream_ready()
    result = apply_optimize_bounded_block_risk_gate(
        state, envelopes, receipt,
        required_source_hashes_by_envelope=routes,
    )
    assert result["status"] == "ABSTAIN_OPTIMIZE_D06_BOUNDED_RISK"
    assert state.status["statistical"] == "abstained"
    assert any("source-byte verification requires" in reason for reason in result["reasons"])
    assert result["source_verification"]["denominator"] == {
        "unit": "source_file", "planned": 30, "valid": 0,
        "failed": 0, "abstained": 30, "not_run": 0,
    }


def test_bounded_d06_bundle_verifies_all_mapped_source_bytes(tmp_path):
    envelopes, receipt, routes = _d06_fixtures()
    common_bytes = b"synthetic shared D06 source receipt"
    (tmp_path / "common.bin").write_bytes(common_bytes)
    common_hash = hashlib.sha256(common_bytes).hexdigest()
    source_paths = {}

    for route, envelope in envelopes.items():
        role = "trainable_w_mean" if route == "trainable_w" else f"contrast:{route}"
        support = [0.0, 1.0] if route == "trainable_w" else [-10.0 / 9.0, 1.0]
        map_bytes = json.dumps({
            "schema": "optimize-bounded-block-risk-markov-v1",
            "role": role,
            "times": [2, 3, 4, 5],
            "score": "mean_t min((q-1)^2,1); assigned-arm solver failure scores 1",
            "contrast": None if route == "trainable_w" else "X_comparator - (10/9)*X_trainable_w",
            "r_star": 10.0 / 9.0,
            "support": support,
        }, sort_keys=True, separators=(",", ":")).encode()
        assert hashlib.sha256(map_bytes).hexdigest() == bounded_risk_map_sha256(route)
        map_name = f"{route}-score-map.json"
        (tmp_path / map_name).write_bytes(map_bytes)

        route_hashes = {
            name: (bounded_risk_map_sha256(route) if name == "score_map" else common_hash)
            for name in routes[route]
        }
        routes[route] = route_hashes
        envelope["chain"]["manifest_sha256"] = common_hash
        envelope["source_hashes"] = route_hashes
        envelope["review"]["receipt_sha256"] = common_hash
        source_paths[route] = {
            name: (map_name if name == "score_map" else "common.bin")
            for name in route_hashes
        }

    state = _upstream_ready()
    result = apply_optimize_bounded_block_risk_gate(
        state, envelopes, receipt,
        required_source_hashes_by_envelope=routes,
        source_root=tmp_path,
        source_paths_by_envelope=source_paths,
    )
    assert result["status"] == "DRAFT_PENDING_TASK_VALIDATION"
    assert result["source_byte_identity_verified"] is True
    assert result["source_verification"]["denominator"] == {
        "unit": "source_file", "planned": 30, "valid": 30,
        "failed": 0, "abstained": 0, "not_run": 0,
    }

    (tmp_path / "common.bin").write_bytes(b"tampered D06 source receipt")
    state = _upstream_ready()
    result = apply_optimize_bounded_block_risk_gate(
        state, envelopes, receipt,
        required_source_hashes_by_envelope=routes,
        source_root=tmp_path,
        source_paths_by_envelope=source_paths,
    )
    assert result["status"] == "ABSTAIN_SOURCE_BYTES"
    assert result["source_verification"]["denominator"] == {
        "unit": "source_file", "planned": 30, "valid": 3,
        "failed": 27, "abstained": 0, "not_run": 0,
    }


def test_bounded_d06_bundle_rejects_unapproved_split_bad_gap_and_missing_arm():
    envelopes, receipt, routes = _d06_fixtures(split="sealed-confirmation")
    state = _upstream_ready()
    result = apply_optimize_bounded_block_risk_gate(
        state, envelopes, receipt,
        required_source_hashes_by_envelope=routes,
        require_source_bytes=False,
    )
    assert result["status"] == "ABSTAIN_OPTIMIZE_D06_BOUNDED_RISK"
    assert state.status["statistical"] == "abstained"
    assert any("closed" in reason for reason in result["reasons"])

    envelopes, receipt, routes = _d06_fixtures()
    for envelope in envelopes.values():
        envelope["dependence"]["tv_bound_after_burn_in"] = 0.06
    state = _upstream_ready()
    result = apply_optimize_bounded_block_risk_gate(
        state, envelopes, receipt,
        required_source_hashes_by_envelope=routes,
        require_source_bytes=False,
    )
    assert result["status"] == "ABSTAIN_OPTIMIZE_D06_BOUNDED_RISK"
    assert any("TV" in reason for reason in result["reasons"])

    envelopes, receipt, routes = _d06_fixtures()
    del envelopes["degree4_chebyshev"]
    state = _upstream_ready()
    result = apply_optimize_bounded_block_risk_gate(
        state, envelopes, receipt,
        required_source_hashes_by_envelope=routes,
        require_source_bytes=False,
    )
    assert result["status"] == "ABSTAIN_OPTIMIZE_D06_BOUNDED_RISK"
    assert any("bundle must contain" in reason for reason in result["reasons"])


def test_bounded_d06_bundle_uses_the_captured_source_snapshots_atomically(tmp_path):
    envelopes, receipt, routes = _d06_fixtures()
    common_bytes = b"synthetic shared D06 source receipt"
    (tmp_path / "common.bin").write_bytes(common_bytes)
    common_hash = hashlib.sha256(common_bytes).hexdigest()
    source_paths = {}

    for route in envelopes:
        role = "trainable_w_mean" if route == "trainable_w" else f"contrast:{route}"
        support = [0.0, 1.0] if route == "trainable_w" else [-10.0 / 9.0, 1.0]
        map_bytes = json.dumps({
            "schema": "optimize-bounded-block-risk-markov-v1",
            "role": role,
            "times": [2, 3, 4, 5],
            "score": "mean_t min((q-1)^2,1); assigned-arm solver failure scores 1",
            "contrast": None if route == "trainable_w" else "X_comparator - (10/9)*X_trainable_w",
            "r_star": 10.0 / 9.0,
            "support": support,
        }, sort_keys=True, separators=(",", ":")).encode()
        map_name = f"{route}-score-map.json"
        (tmp_path / map_name).write_bytes(map_bytes)
        route_hashes = {
            name: (bounded_risk_map_sha256(route) if name == "score_map" else common_hash)
            for name in routes[route]
        }
        routes[route] = route_hashes
        envelopes[route]["chain"]["manifest_sha256"] = common_hash
        envelopes[route]["source_hashes"] = route_hashes
        envelopes[route]["review"]["receipt_sha256"] = common_hash
        source_paths[route] = {
            name: (map_name if name == "score_map" else "common.bin")
            for name in route_hashes
        }

    snapshots = {
        route: capture_source_snapshot(tmp_path, routes[route], source_paths[route])
        for route in envelopes
    }
    assert json.loads(snapshots["trainable_w"].read_bytes("score_map"))["role"] == "trainable_w_mean"
    (tmp_path / "common.bin").write_bytes(b"changed after task reader captured bytes")
    result = apply_optimize_bounded_block_risk_gate(
        _upstream_ready(), envelopes, receipt,
        required_source_hashes_by_envelope=routes,
        source_snapshots_by_envelope=snapshots,
    )

    assert result["status"] == "DRAFT_PENDING_TASK_VALIDATION"
    assert result["source_verification"]["denominator"] == {
        "unit": "source_file", "planned": 30, "valid": 30,
        "failed": 0, "abstained": 0, "not_run": 0,
    }


def test_d06_snapshot_reader_reconciles_arrays_receipt_and_atomic_byte_gate(tmp_path):
    envelopes, receipt, routes, snapshots = _d06_snapshot_bundle(tmp_path)
    state = _upstream_ready()
    result = apply_bounded_block_risk_snapshot_gate(
        state, envelopes, receipt,
        required_source_hashes_by_envelope=routes,
        source_snapshots_by_envelope=snapshots,
    )

    assert result["status"] == "DRAFT_PENDING_TASK_VALIDATION"
    assert state.status["statistical"] == "draft"
    assert result["source_verification"]["denominator"] == {
        "unit": "source_file", "planned": 30, "valid": 30,
        "failed": 0, "abstained": 0, "not_run": 0,
    }
    assert set(result["reader_summary"]) == set(_D06_ROUTES)
    assert all(row["source_read_mode"] == "immutable_snapshot"
               for row in result["reader_summary"].values())
    assert all(row["block_denominator"]["planned"] == 2000
               for row in result["reader_summary"].values())
    assert all(row["assigned_arm_run_denominator"]["failed"] == 1
               for row in result["reader_summary"].values())
    assert result["reader_decision"]["dependence_method"] == "corrected_markov_pseudo_gap_bernstein_support_only"
    assert result["reader_decision"]["status"] == "CONDITIONAL_MARKOV_PASS_BOTH_COMPARISONS"
    assert result["reader_summary"]["trainable_w"]["gamma_ps_lower_assumed"] == 1.0
    assert result["reader_summary"]["trainable_w"]["trainable_w_lower_bound"] > 0.0
    assert all(value > 0.0 for value in result["reader_summary"]["trainable_w"]["comparison_lower_bounds"].values())
    assert result["physical_score"] is None and result["certified"] is False


def test_d06_snapshot_reader_abstains_when_receipt_denominator_disagrees(tmp_path):
    envelopes, receipt, routes, snapshots = _d06_snapshot_bundle(tmp_path)
    receipt["denominators"]["paired_macroblocks"]["planned"] = 11
    receipt["denominators"]["paired_macroblocks"]["valid"] = 11
    state = _upstream_ready()
    result = apply_bounded_block_risk_snapshot_gate(
        state, envelopes, receipt,
        required_source_hashes_by_envelope=routes,
        source_snapshots_by_envelope=snapshots,
    )
    assert result["status"] == "ABSTAIN_OPTIMIZE_D06_SNAPSHOT_READER"
    assert state.status["statistical"] == "abstained"
    assert any("receipt denominators" in reason for reason in result["reasons"])
    assert result["physical_score"] is None


def test_d06_snapshot_reader_abstains_when_observed_effect_thresholds_fail(tmp_path):
    envelopes, receipt, routes, snapshots = _d06_snapshot_bundle(
        tmp_path, release_signal=False,
    )
    state = _upstream_ready()
    result = apply_bounded_block_risk_snapshot_gate(
        state, envelopes, receipt,
        required_source_hashes_by_envelope=routes,
        source_snapshots_by_envelope=snapshots,
    )
    assert result["status"] == "ABSTAIN_OPTIMIZE_D06_SNAPSHOT_READER"
    assert state.status["statistical"] == "abstained"
    assert result["reader_decision"]["status"] == "CONDITIONAL_NO_FAMILYWISE_RELEASE"
    assert result["physical_score"] is None and result["certified"] is False


def test_d06_snapshot_reader_rejects_route_specific_markov_inputs(tmp_path):
    envelopes, receipt, routes, snapshots = _d06_snapshot_bundle(tmp_path)
    envelopes["degree4_chebyshev"]["dependence"]["gamma_ps_lower"] = 0.5
    state = _upstream_ready()
    result = apply_bounded_block_risk_snapshot_gate(
        state, envelopes, receipt,
        required_source_hashes_by_envelope=routes,
        source_snapshots_by_envelope=snapshots,
    )
    assert result["status"] == "ABSTAIN_OPTIMIZE_D06_SNAPSHOT_READER"
    assert state.status["statistical"] == "abstained"
    assert any("shared Markov gap" in reason for reason in result["reasons"])
