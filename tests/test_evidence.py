import copy

from core.evidence import (
    EVIDENCE_SCHEMA,
    apply_evidence_gate,
    evidence_envelope,
    inspect_distinct_chain_identities,
    inspect_evidence_envelope,
)
from core.receipts import denominator, run_receipt, scenario_spec
from core.state import RunState


HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


def make_envelope(*, task="pion_projection", kind="score_dependence",
                  chain_id="score-chain", split_id="development",
                  manifest_hash=HASH_A, unit="bounded score", review="reviewed"):
    review_record = (
        {"status": "pending"} if review == "pending" else
        {"status": "reviewed", "receipt_sha256": HASH_B, "scope_sha256": HASH_C}
    )
    return evidence_envelope(
        task,
        kind,
        chain={
            "chain_id": chain_id,
            "split_id": split_id,
            "state_unit": "saved paired macroblock",
            "manifest_sha256": manifest_hash,
        },
        observable={
            "map_id": "fixture-score-v1",
            "map_sha256": HASH_B,
            "support": {"lower": 0.0, "upper": 1.0, "unit": unit},
        },
        method={
            "name": "corrected Markov pseudo-gap Bernstein bound",
            "version": "fixture-v1",
            "assumptions": ["the fixture chain is homogeneous"],
        },
        dependence={
            "mode": "markov",
            "assumptions": ["gap applies to the exact saved-state chain"],
            "gamma_ps_lower": 0.25,
            "tv_bound_after_burn_in": 0.01,
            "burn_in": {"unit": "saved macroblock", "count": 8},
        },
        confidence={
            "family_id": "fixture-family",
            "alpha_total": 0.05,
            "alpha_allocated": 0.01,
            "family_size": 5,
        },
        source_hashes={"manifest": manifest_hash, "score_map": HASH_B},
        review=review_record,
    )


def make_run_receipt(*, planned=2, valid=2):
    scenario = scenario_spec("evidence-gate-fixture", "panel", "metadata gate fixture")
    counts = denominator("panels", planned=planned, valid=valid)
    reasons = []
    if counts["not_run"]:
        reasons.append({"unit": "panels", "state": "not_run",
                        "count": counts["not_run"], "reason": "fixture not started"})
    return run_receipt(
        scenario, {"panels": counts}, artifact_hashes={"fixture": HASH_C},
        text_flow="fixture -> count planned/valid/not-run panels",
        reason_rows=reasons,
    )


def test_envelope_is_typed_and_never_certifies_physics():
    envelope = make_envelope()
    assert envelope["schema"] == EVIDENCE_SCHEMA
    result = inspect_evidence_envelope(
        envelope,
        expected={
            "task": "pion_projection",
            "evidence_kind": "score_dependence",
            "observable.support.unit": "bounded score",
            "dependence.gamma_ps_lower": 0.25,
        },
        required_source_hashes={"manifest": HASH_A},
    )
    assert result["status"] == "SCHEMA_COMPLETE_NOT_CERTIFIED"
    assert result["certified"] is False
    assert result["physical_score"] is None


def test_task_fixtures_preserve_distinct_observable_units():
    pion_anchor = make_envelope(
        task="pion_projection", kind="anchor_dependence", chain_id="E-anchor",
        split_id="anchor", manifest_hash=HASH_A, unit="dimensionless anchor scalar",
    )
    optimize_score = make_envelope(
        task="optimize_gaussian", kind="paired_block_risk",
        chain_id="D-paired-blocks", split_id="development", manifest_hash=HASH_B,
        unit="bounded loss in [0,1]",
    )
    wilson_force = make_envelope(
        task="wilson_loop", kind="thermal_force_bound", chain_id="D-Wilson",
        split_id="development", manifest_hash=HASH_C, unit="a_s*a_t*F",
    )
    for envelope, task, unit in (
        (pion_anchor, "pion_projection", "dimensionless anchor scalar"),
        (optimize_score, "optimize_gaussian", "bounded loss in [0,1]"),
        (wilson_force, "wilson_loop", "a_s*a_t*F"),
    ):
        result = inspect_evidence_envelope(
            envelope,
            expected={"task": task, "observable.support.unit": unit},
        )
        assert result["status"] == "SCHEMA_COMPLETE_NOT_CERTIFIED"


def test_missing_markov_receipt_fields_abstain():
    envelope = make_envelope()
    del envelope["dependence"]["gamma_ps_lower"]
    result = inspect_evidence_envelope(envelope)
    assert result["status"] == "ABSTAIN_INVALID_EVIDENCE_ENVELOPE"
    assert "gamma_ps_lower" in result["reasons"][0]


def test_wrong_chain_and_force_unit_abstain():
    envelope = make_envelope(task="wilson_loop", kind="thermal_force_bound")
    wrong_chain = inspect_evidence_envelope(
        envelope, expected={"chain.chain_id": "authorized-F-chain"},
    )
    wrong_unit = inspect_evidence_envelope(
        envelope, expected={"observable.support.unit": "a_s*a_t*F"},
    )
    assert wrong_chain["status"] == "ABSTAIN_EVIDENCE_MISMATCH"
    assert wrong_unit["status"] == "ABSTAIN_EVIDENCE_MISMATCH"


def test_stale_source_hash_and_pending_review_abstain():
    envelope = make_envelope(review="pending")
    result = inspect_evidence_envelope(
        envelope, required_source_hashes={"manifest": HASH_C},
    )
    assert result["status"] == "ABSTAIN_EVIDENCE_MISMATCH"
    assert any("source hash mismatch" in reason for reason in result["reasons"])
    assert any("review receipt is missing" in reason for reason in result["reasons"])


def test_distinct_chain_identity_is_not_treated_as_independence_proof():
    anchor = make_envelope(kind="anchor", chain_id="E-anchor", manifest_hash=HASH_A)
    score = make_envelope(kind="score", chain_id="D-score", manifest_hash=HASH_C)
    result = inspect_distinct_chain_identities(anchor, score)
    assert result["status"] == "IDENTITIES_DISTINCT_NOT_INDEPENDENCE_PROOF"
    assert result["identity_distinct"] is True
    assert result["independence_proven"] is False


def test_reused_chain_identity_abstains():
    anchor = make_envelope(kind="anchor", chain_id="same", manifest_hash=HASH_A)
    score = make_envelope(kind="score", chain_id="same", manifest_hash=HASH_B)
    result = inspect_distinct_chain_identities(anchor, score)
    assert result["status"] == "ABSTAIN_CHAIN_IDENTITY_COLLISION"
    assert "chain_id collision" in result["reasons"]
    assert result["independence_proven"] is False


def test_family_confidence_and_review_hashes_are_validated():
    import pytest

    envelope = make_envelope()
    malformed = copy.deepcopy(envelope)
    malformed["confidence"]["alpha_allocated"] = 0.06
    assert inspect_evidence_envelope(malformed)["status"] == "ABSTAIN_INVALID_EVIDENCE_ENVELOPE"

    malformed = copy.deepcopy(envelope)
    malformed["review"]["receipt_sha256"] = "stale"
    assert inspect_evidence_envelope(malformed)["status"] == "ABSTAIN_INVALID_EVIDENCE_ENVELOPE"

    with pytest.raises(ValueError, match="support.upper must exceed lower"):
        evidence_envelope(
            "fixture", "bad-support",
            chain={"chain_id": "c", "split_id": "s", "state_unit": "state",
                   "manifest_sha256": HASH_A},
            observable={"map_id": "m", "map_sha256": HASH_B,
                        "support": {"lower": 1, "upper": 1, "unit": "u"}},
            method={"name": "m", "version": "v", "assumptions": ["a"]},
            dependence={"mode": "deterministic", "assumptions": ["exact"]},
            confidence={"family_id": "f", "alpha_total": 0.05,
                        "alpha_allocated": 0.01, "family_size": 1},
            source_hashes={"source": HASH_A},
        )


def test_runstate_gate_only_advances_to_draft_when_envelope_and_denominator_are_complete():
    state = RunState()
    result = apply_evidence_gate(state, "statistical", make_envelope(), make_run_receipt())
    assert result["status"] == "DRAFT_PENDING_TASK_VALIDATION"
    assert result["run_state"]["status"]["statistical"] == "draft"
    assert result["run_state"]["score"] is None
    assert result["certified"] is False


def test_runstate_gate_abstains_for_incomplete_denominator_or_missing_envelope_field():
    state = RunState()
    partial = apply_evidence_gate(
        state, "statistical", make_envelope(), make_run_receipt(planned=2, valid=1),
    )
    assert partial["status"] == "ABSTAIN_EVIDENCE_GATE"
    assert partial["run_state"]["status"]["statistical"] == "abstained"
    assert any("not run" in reason for reason in partial["reasons"])

    state = RunState()
    broken = make_envelope()
    del broken["dependence"]["tv_bound_after_burn_in"]
    result = apply_evidence_gate(state, "statistical", broken, make_run_receipt())
    assert result["status"] == "ABSTAIN_EVIDENCE_GATE"
    assert result["run_state"]["score"] is None


def test_runstate_gate_rejects_empty_or_missing_run_receipt():
    state = RunState()
    empty = apply_evidence_gate(
        state, "statistical", make_envelope(), make_run_receipt(planned=0, valid=0),
    )
    assert empty["status"] == "ABSTAIN_EVIDENCE_GATE"
    assert any("no planned units" in reason for reason in empty["reasons"])

    state = RunState()
    missing = apply_evidence_gate(state, "statistical", make_envelope(), None)
    assert missing["status"] == "ABSTAIN_EVIDENCE_GATE"
