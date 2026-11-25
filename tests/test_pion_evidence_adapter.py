import copy

from core.evidence import evidence_envelope
from core.receipts import denominator, run_receipt, scenario_spec
from core.state import RunState
from tasks.pion_projection.evidence_adapter import (
    apply_pion_statistical_evidence_gate,
    score_map_sha256,
)


H = [f"{i:064x}" for i in range(1, 20)]
ANCHOR_MAP_ID = "fixture-anchor-scalar-map-v1"
ANCHOR_MAP_HASH = H[6]


def _source_hashes():
    return {
        "score": {
            "manifest": H[0],
            "score_map": score_map_sha256(),
            "block_chain_receipt": H[1],
            "gamma_ps_receipt": H[2],
            "initial_law_tv_receipt": H[3],
            "review_receipt": H[4],
        },
        "anchor": {
            "manifest": H[5],
            "scalar_map": ANCHOR_MAP_HASH,
            "coverage_receipt": H[7],
            "common_bias_receipt": H[8],
            "independence_receipt": H[15],
            "score_anchor_independence_receipt": H[9],
            "review_receipt": H[10],
        },
    }


def _review(receipt_hash):
    return {
        "status": "reviewed",
        "receipt_sha256": receipt_hash,
        "scope_sha256": H[11],
        "reviewer_role_claim": "independent",
        "independence_claim_sha256": H[12],
    }


def _envelopes(*, score_gamma=0.2, score_tv=0.001, score_burn_in=8,
               score_chain_id="score-chain", anchor_chain_id="anchor-chain"):
    hashes = _source_hashes()
    score = evidence_envelope(
        "pion_projection", "score_dependence",
        chain={
            "chain_id": score_chain_id,
            "split_id": "score-development",
            "state_unit": "length-5 saved-configuration macroblock",
            "manifest_sha256": hashes["score"]["manifest"],
        },
        observable={
            "map_id": "pion-bounded-block-risk-selected-v1/bounded-score-map",
            "map_sha256": hashes["score"]["score_map"],
            "support": {"lower": -1, "upper": 1, "unit": "bounded score"},
        },
        method={
            "name": "markov_pseudo_gap_bernstein",
            "version": "fixture-v1",
            "assumptions": ["fixed score map over saved macroblocks"],
        },
        dependence={
            "mode": "markov",
            "assumptions": ["the receipt covers the exact saved-state chain"],
            "gamma_ps_lower": score_gamma,
            "tv_bound_after_burn_in": score_tv,
            "burn_in": {
                "unit": "length-5 saved-configuration macroblock",
                "count": score_burn_in,
            },
        },
        confidence={
            "family_id": "pion-bounded-block-risk-selected-v1/score-F3",
            "alpha_total": 0.05,
            "alpha_allocated": 0.04,
            "family_size": 3,
        },
        source_hashes=hashes["score"],
        review=_review(hashes["score"]["review_receipt"]),
    )
    anchor = evidence_envelope(
        "pion_projection", "anchor_coverage",
        chain={
            "chain_id": anchor_chain_id,
            "split_id": "anchor-evidence",
            "state_unit": "independent stationary anchor unit",
            "manifest_sha256": hashes["anchor"]["manifest"],
        },
        observable={
            "map_id": ANCHOR_MAP_ID,
            "map_sha256": ANCHOR_MAP_HASH,
            "support": {"lower": 0.1, "upper": 3.0, "unit": "a_t m_pi"},
        },
        method={
            "name": "bounded_iid_hoeffding",
            "version": "fixture-v1",
            "assumptions": ["anchor units are independent and stationary"],
        },
        dependence={
            "mode": "iid",
            "assumptions": ["independent stationary units"],
            "independence_receipt_sha256": hashes["anchor"]["independence_receipt"],
        },
        confidence={
            "family_id": "pion-bounded-block-risk-selected-v1/anchor",
            "alpha_total": 0.05,
            "alpha_allocated": 0.01,
            "family_size": 1,
        },
        source_hashes=hashes["anchor"],
        review=_review(hashes["anchor"]["review_receipt"]),
    )
    return {"score": score, "anchor": anchor}, hashes


def _receipt(*, score_planned=12000, score_valid=12000, anchor_planned=1000,
             anchor_valid=1000):
    scenario = scenario_spec(
        "pion-statistical-evidence-fixture", "planned score or anchor unit",
        "synthetic task adapter interface fixture",
    )
    return run_receipt(
        scenario,
        {
            "score_family_blocks": denominator(
                "paired score value", planned=score_planned, valid=score_valid,
            ),
            "anchor_units": denominator(
                "independent stationary anchor scalar", planned=anchor_planned,
                valid=anchor_valid,
            ),
        },
        artifact_hashes={"fixture": H[13]},
        text_flow="fixture envelopes -> task protocol checks -> bundle gate -> draft or abstain",
    )


def _ready_state():
    state = RunState()
    for stage in ("operator", "reference", "numerical"):
        state.set(stage, "draft", evidence=f"synthetic {stage} prerequisite")
        state.set(stage, "validated", evidence_hash=H[14])
    return state


def _apply(state, envelopes, hashes, receipt=None, *, common_bias=0.01):
    return apply_pion_statistical_evidence_gate(
        state,
        envelopes,
        _receipt() if receipt is None else receipt,
        anchor_scalar_map_id=ANCHOR_MAP_ID,
        anchor_scalar_map_sha256=ANCHOR_MAP_HASH,
        common_bias_bound_over_R=common_bias,
        required_source_hashes_by_envelope=hashes,
    )


def test_pion_statistical_adapter_binds_selected_f3_defaults_and_stops_at_draft():
    envelopes, hashes = _envelopes()
    state = _ready_state()
    result = _apply(state, envelopes, hashes)
    assert result["status"] == "DRAFT_PENDING_TASK_VALIDATION"
    assert result["run_state"]["status"]["statistical"] == "draft"
    assert result["certified"] is False
    assert result["physical_score"] is None
    assert result["chain_identity_checks"][0]["independence_proven"] is False


def test_pion_statistical_adapter_abstains_without_upstream_reference_and_anchor_map():
    envelopes, hashes = _envelopes()
    state = RunState()
    result = _apply(state, envelopes, hashes)
    assert result["status"] == "ABSTAIN_PION_STATISTICAL_ADAPTER"
    assert state.status["statistical"] == "abstained"
    assert any("reference stage must be validated" in item for item in result["reasons"])


def test_pion_statistical_adapter_abstains_below_score_gap_or_above_common_bias_cap():
    envelopes, hashes = _envelopes(score_gamma=0.19)
    result = _apply(_ready_state(), envelopes, hashes)
    assert result["status"] == "ABSTAIN_PION_STATISTICAL_ADAPTER"
    assert any("gamma_ps" in item for item in result["reasons"])

    envelopes, hashes = _envelopes()
    result = _apply(_ready_state(), envelopes, hashes, common_bias=0.0101)
    assert result["status"] == "ABSTAIN_PION_STATISTICAL_ADAPTER"
    assert any("C/R" in item for item in result["reasons"])


def test_pion_statistical_adapter_abstains_when_score_tv_or_burn_in_misses_plan():
    envelopes, hashes = _envelopes(score_tv=0.0011)
    result = _apply(_ready_state(), envelopes, hashes)
    assert result["status"] == "ABSTAIN_PION_STATISTICAL_ADAPTER"
    assert any("TV bound" in item for item in result["reasons"])

    envelopes, hashes = _envelopes(score_burn_in=7)
    result = _apply(_ready_state(), envelopes, hashes)
    assert result["status"] == "ABSTAIN_PION_STATISTICAL_ADAPTER"
    assert any("burn-in" in item for item in result["reasons"])


def test_pion_statistical_adapter_abstains_on_wrong_plan_or_chain_identity():
    envelopes, hashes = _envelopes()
    wrong_plan = _receipt(score_planned=11999, score_valid=11999)
    result = _apply(_ready_state(), envelopes, hashes, wrong_plan)
    assert result["status"] == "ABSTAIN_PION_STATISTICAL_ADAPTER"
    assert any("planned 11999" in item for item in result["reasons"])

    envelopes, hashes = _envelopes(anchor_chain_id="score-chain")
    result = _apply(_ready_state(), envelopes, hashes)
    assert result["status"] == "ABSTAIN_EVIDENCE_BUNDLE"
    assert result["run_state"]["status"]["statistical"] == "abstained"


def test_pion_statistical_adapter_does_not_accept_stale_map_hashes():
    envelopes, hashes = _envelopes()
    envelopes = copy.deepcopy(envelopes)
    envelopes["anchor"]["observable"]["map_sha256"] = H[18]
    result = _apply(_ready_state(), envelopes, hashes)
    assert result["status"] == "ABSTAIN_PION_STATISTICAL_ADAPTER"
    assert any("observable-map hash" in item for item in result["reasons"])


def test_pion_statistical_adapter_abstains_on_incomplete_source_hash_map():
    envelopes, hashes = _envelopes()
    bad_hashes = copy.deepcopy(hashes)
    del bad_hashes["anchor"]["common_bias_receipt"]
    result = _apply(_ready_state(), envelopes, bad_hashes)
    assert result["status"] == "ABSTAIN_PION_STATISTICAL_ADAPTER"
    assert any("common_bias_receipt" in item for item in result["reasons"])
