"""Typed, fail-closed metadata contracts for scientific evidence receipts.

These helpers verify that a receipt names the expected chain, observable,
support, method, confidence allocation, sources and review artifact. They do
not authenticate those artifacts or certify the underlying physics claim.
"""
from __future__ import annotations

import math
import re
from numbers import Real
from typing import Any


EVIDENCE_SCHEMA = "latticearena-evidence-envelope-v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DEPENDENCE_MODES = frozenset(("iid", "finite_dependence", "markov", "spectral", "deterministic"))


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value


def _sha(value: object, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{label} must be a lowercase SHA-256 hash")
    return value


def _finite(value: object, label: str) -> float:
    if not isinstance(value, Real) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise ValueError(f"{label} must be a finite real number")
    return float(value)


def _hashes(value: object, label: str) -> dict[str, str]:
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{label} must be a nonempty mapping of names to SHA-256 hashes")
    result = {}
    for name, digest in value.items():
        result[_text(name, f"{label} name")] = _sha(digest, f"{label}[{name!r}]")
    return result


def evidence_envelope(
    task: str,
    evidence_kind: str,
    *,
    chain: dict[str, Any],
    observable: dict[str, Any],
    method: dict[str, Any],
    dependence: dict[str, Any],
    confidence: dict[str, Any],
    source_hashes: dict[str, str],
    review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a versioned envelope while preserving its conditional status.

    ``chain_id`` identifies the sampling chain and ``manifest_sha256`` binds
    its saved-configuration/state manifest. ``observable.support.unit`` is the
    unit of the quantity carried by this envelope; for example, Wilson F-lane
    contamination can be recorded in lattice-force units after propagation.
    """
    task = _text(task, "task")
    evidence_kind = _text(evidence_kind, "evidence_kind")
    if not isinstance(chain, dict):
        raise ValueError("chain must be a mapping")
    normalized_chain = {
        "chain_id": _text(chain.get("chain_id"), "chain.chain_id"),
        "split_id": _text(chain.get("split_id"), "chain.split_id"),
        "state_unit": _text(chain.get("state_unit"), "chain.state_unit"),
        "manifest_sha256": _sha(chain.get("manifest_sha256"), "chain.manifest_sha256"),
    }

    if not isinstance(observable, dict) or not isinstance(observable.get("support"), dict):
        raise ValueError("observable and observable.support must be mappings")
    support = observable["support"]
    lower = _finite(support.get("lower"), "observable.support.lower")
    upper = _finite(support.get("upper"), "observable.support.upper")
    if upper <= lower:
        raise ValueError("observable.support.upper must exceed lower")
    normalized_observable = {
        "map_id": _text(observable.get("map_id"), "observable.map_id"),
        "map_sha256": _sha(observable.get("map_sha256"), "observable.map_sha256"),
        "support": {
            "lower": lower,
            "upper": upper,
            "unit": _text(support.get("unit"), "observable.support.unit"),
        },
    }

    if not isinstance(method, dict):
        raise ValueError("method must be a mapping")
    assumptions = method.get("assumptions")
    if isinstance(assumptions, str) or not isinstance(assumptions, (list, tuple)):
        raise ValueError("method.assumptions must be a sequence of nonempty strings")
    if not assumptions:
        raise ValueError("method.assumptions must be nonempty")
    normalized_method = {
        "name": _text(method.get("name"), "method.name"),
        "version": _text(method.get("version"), "method.version"),
        "assumptions": [_text(item, "method assumption") for item in assumptions],
    }

    if not isinstance(dependence, dict):
        raise ValueError("dependence must be a mapping")
    mode = dependence.get("mode")
    if mode not in _DEPENDENCE_MODES:
        raise ValueError(f"dependence.mode must be one of {sorted(_DEPENDENCE_MODES)}")
    normalized_dependence: dict[str, Any] = {
        "mode": mode,
        "assumptions": list(dependence.get("assumptions", ())),
    }
    if not normalized_dependence["assumptions"]:
        raise ValueError("dependence.assumptions must be nonempty")
    for item in normalized_dependence["assumptions"]:
        _text(item, "dependence assumption")
    if mode == "markov":
        gamma = _finite(dependence.get("gamma_ps_lower"), "dependence.gamma_ps_lower")
        tv = _finite(dependence.get("tv_bound_after_burn_in"),
                     "dependence.tv_bound_after_burn_in")
        burn_in = dependence.get("burn_in")
        if not isinstance(burn_in, dict):
            raise ValueError("Markov dependence requires a burn_in mapping")
        burn_count = burn_in.get("count")
        if (not isinstance(burn_count, int) or isinstance(burn_count, bool)
                or burn_count < 0):
            raise ValueError("dependence.burn_in.count must be a nonnegative integer")
        if not 0.0 < gamma <= 1.0:
            raise ValueError("dependence.gamma_ps_lower must be in (0, 1]")
        if not 0.0 <= tv < 1.0:
            raise ValueError("dependence.tv_bound_after_burn_in must be in [0, 1)")
        normalized_dependence.update({
            "gamma_ps_lower": gamma,
            "tv_bound_after_burn_in": tv,
            "burn_in": {
                "unit": _text(burn_in.get("unit"), "dependence.burn_in.unit"),
                "count": burn_count,
            },
        })
    elif mode == "iid":
        normalized_dependence["independence_receipt_sha256"] = _sha(
            dependence.get("independence_receipt_sha256"),
            "dependence.independence_receipt_sha256",
        )
    elif mode == "finite_dependence":
        radius = dependence.get("dependence_radius")
        if not isinstance(radius, int) or isinstance(radius, bool) or radius < 0:
            raise ValueError("finite_dependence requires nonnegative dependence_radius")
        normalized_dependence["dependence_radius"] = radius
        normalized_dependence["graph_sha256"] = _sha(
            dependence.get("graph_sha256"), "dependence.graph_sha256"
        )

    if not isinstance(confidence, dict):
        raise ValueError("confidence must be a mapping")
    alpha_total = _finite(confidence.get("alpha_total"), "confidence.alpha_total")
    alpha_allocated = _finite(confidence.get("alpha_allocated"),
                              "confidence.alpha_allocated")
    family_size = confidence.get("family_size")
    if not 0.0 < alpha_allocated <= alpha_total < 1.0:
        raise ValueError("confidence must satisfy 0 < alpha_allocated <= alpha_total < 1")
    if not isinstance(family_size, int) or isinstance(family_size, bool) or family_size < 1:
        raise ValueError("confidence.family_size must be a positive integer")
    normalized_confidence = {
        "family_id": _text(confidence.get("family_id"), "confidence.family_id"),
        "alpha_total": alpha_total,
        "alpha_allocated": alpha_allocated,
        "family_size": family_size,
    }

    if review is None:
        review = {"status": "pending"}
    if not isinstance(review, dict) or review.get("status") not in ("pending", "reviewed"):
        raise ValueError("review.status must be 'pending' or 'reviewed'")
    normalized_review = {"status": review["status"]}
    if review["status"] == "reviewed":
        normalized_review.update({
            "receipt_sha256": _sha(review.get("receipt_sha256"), "review.receipt_sha256"),
            "scope_sha256": _sha(review.get("scope_sha256"), "review.scope_sha256"),
        })

    return {
        "schema": EVIDENCE_SCHEMA,
        "task": task,
        "evidence_kind": evidence_kind,
        "chain": normalized_chain,
        "observable": normalized_observable,
        "method": normalized_method,
        "dependence": normalized_dependence,
        "confidence": normalized_confidence,
        "source_hashes": _hashes(source_hashes, "source_hashes"),
        "review": normalized_review,
        "certified": False,
        "physical_score": None,
    }


def inspect_evidence_envelope(
    envelope: object,
    *,
    expected: dict[str, Any] | None = None,
    required_source_hashes: dict[str, str] | None = None,
    require_review: bool = True,
) -> dict[str, Any]:
    """Check schema and caller-frozen identities; mismatches fail closed.

    A successful result is only ``SCHEMA_COMPLETE_NOT_CERTIFIED``. External
    hashes must still be checked against their actual bytes by the receipt
    consumer, and scientific assumptions still require independent review.
    """
    try:
        if not isinstance(envelope, dict) or envelope.get("schema") != EVIDENCE_SCHEMA:
            raise ValueError(f"envelope.schema must be {EVIDENCE_SCHEMA!r}")
        normalized = evidence_envelope(
            envelope.get("task"), envelope.get("evidence_kind"),
            chain=envelope.get("chain"), observable=envelope.get("observable"),
            method=envelope.get("method"), dependence=envelope.get("dependence"),
            confidence=envelope.get("confidence"),
            source_hashes=envelope.get("source_hashes"), review=envelope.get("review"),
        )
    except (TypeError, ValueError) as exc:
        return {
            "status": "ABSTAIN_INVALID_EVIDENCE_ENVELOPE",
            "reasons": [str(exc)],
            "certified": False,
            "physical_score": None,
        }

    if expected is None:
        expected = {}
    if not isinstance(expected, dict):
        raise ValueError("expected must be a mapping of dotted field paths to values")
    reasons = []
    for path, wanted in expected.items():
        actual: Any = normalized
        for component in _text(path, "expected field path").split("."):
            if not isinstance(actual, dict) or component not in actual:
                actual = None
                break
            actual = actual[component]
        if actual != wanted:
            reasons.append(f"field mismatch {path}: expected {wanted!r}, observed {actual!r}")
    if required_source_hashes is not None:
        required = _hashes(required_source_hashes, "required_source_hashes")
        for name, digest in required.items():
            actual = normalized["source_hashes"].get(name)
            if actual != digest:
                reasons.append(f"source hash mismatch {name!r}: expected {digest}, observed {actual!r}")
    if require_review and normalized["review"]["status"] != "reviewed":
        reasons.append("independent review receipt is missing")
    return {
        "status": "ABSTAIN_EVIDENCE_MISMATCH" if reasons else "SCHEMA_COMPLETE_NOT_CERTIFIED",
        "reasons": reasons,
        "normalized_envelope": normalized,
        "certified": False,
        "physical_score": None,
    }


def inspect_distinct_chain_identities(first: object, second: object) -> dict[str, Any]:
    """Reject colliding chain IDs/manifests without claiming independence.

    Identity separation is a necessary bookkeeping check, not proof of
    statistical independence or absence of common-mode bias.
    """
    left = inspect_evidence_envelope(first, require_review=False)
    right = inspect_evidence_envelope(second, require_review=False)
    reasons = []
    if left["status"].startswith("ABSTAIN"):
        reasons.append("first envelope is invalid")
    if right["status"].startswith("ABSTAIN"):
        reasons.append("second envelope is invalid")
    if not reasons:
        a, b = left["normalized_envelope"]["chain"], right["normalized_envelope"]["chain"]
        if a["chain_id"] == b["chain_id"]:
            reasons.append("chain_id collision")
        if a["manifest_sha256"] == b["manifest_sha256"]:
            reasons.append("chain manifest collision")
    return {
        "status": "ABSTAIN_CHAIN_IDENTITY_COLLISION" if reasons else "IDENTITIES_DISTINCT_NOT_INDEPENDENCE_PROOF",
        "reasons": reasons,
        "identity_distinct": not reasons,
        "independence_proven": False,
        "physical_score": None,
    }
