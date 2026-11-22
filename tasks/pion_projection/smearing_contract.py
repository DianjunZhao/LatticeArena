"""CPU-only validation for matched source/sink Wuppertal smearing plans.

The legacy ``source.gaussian12`` helper maps ``(rho, steps)`` to the alpha
passed to the same low-level Wuppertal routine used by the sink. This module
keeps that mapping explicit so an incompatible plan can be rejected before
GPU initialization or output creation.
"""
from __future__ import annotations

import math
from collections.abc import Mapping


def gaussian12_alpha(rho: float, steps: int) -> float:
    """Return the alpha used by PyQUDA ``source.gaussian12``.

    PyQUDA currently computes ``1 / (4 * steps / rho**2 - 6)``. This helper
    records that wrapper convention; it does not validate the backend kernel.
    """
    if isinstance(steps, bool) or not isinstance(steps, int) or steps <= 0:
        raise ValueError("Gaussian smearing steps must be a positive integer")
    try:
        rho = float(rho)
    except (TypeError, ValueError) as exc:
        raise ValueError("Gaussian smearing rho must be a finite positive number") from exc
    if not math.isfinite(rho) or rho <= 0:
        raise ValueError("Gaussian smearing rho must be a finite positive number")
    denominator = 4.0 * steps / (rho * rho) - 6.0
    if not math.isfinite(denominator) or denominator <= 0:
        raise ValueError("Gaussian smearing rho/steps map to a non-positive alpha denominator")
    alpha = 1.0 / denominator
    if not math.isfinite(alpha) or alpha <= 0:
        raise ValueError("Gaussian smearing alpha must be finite and positive")
    return alpha


def gaussian12_rho(alpha: float, steps: int) -> float:
    """Return rho giving the requested ``gaussian12`` alpha and step count."""
    if isinstance(steps, bool) or not isinstance(steps, int) or steps <= 0:
        raise ValueError("Gaussian smearing steps must be a positive integer")
    try:
        alpha = float(alpha)
    except (TypeError, ValueError) as exc:
        raise ValueError("Wuppertal alpha must be a finite positive number") from exc
    if not math.isfinite(alpha) or alpha <= 0:
        raise ValueError("Wuppertal alpha must be a finite positive number")
    rho_squared = 4.0 * steps / (6.0 + 1.0 / alpha)
    if not math.isfinite(rho_squared) or rho_squared <= 0:
        raise ValueError("Wuppertal alpha/steps do not define a positive rho")
    return math.sqrt(rho_squared)


def validate_source_sink_smearing(
    protocol: Mapping[str, object], *, rtol: float = 1e-12, atol: float = 1e-12
) -> list[dict[str, object]]:
    """Validate that every non-point source uses the sink's Wuppertal alpha.

    Returns a machine-readable parameter table suitable for a provenance
    receipt. Point sources are recorded with ``source_alpha=None`` because no
    smearing operator is applied.
    """
    try:
        sink_alpha = float(protocol["alpha"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Protocol must define a numeric sink alpha") from exc
    if not math.isfinite(sink_alpha) or sink_alpha <= 0:
        raise ValueError("Protocol sink alpha must be finite and positive")
    sources = protocol.get("source_smear")
    if not isinstance(sources, list) or not sources:
        raise ValueError("Protocol must define a non-empty source_smear list")

    seen_names: set[str] = set()
    rows: list[dict[str, object]] = []
    mismatches: list[str] = []
    for spec in sources:
        if not isinstance(spec, Mapping):
            raise ValueError("Each source_smear entry must be an object")
        name = spec.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("Each source_smear entry must have a non-empty name")
        if name in seen_names:
            raise ValueError(f"Duplicate source_smear name: {name}")
        seen_names.add(name)
        steps = spec.get("steps")
        if isinstance(steps, bool) or not isinstance(steps, int) or steps < 0:
            raise ValueError(f"{name}: steps must be a non-negative integer")
        if steps == 0:
            rows.append({"name": name, "steps": 0, "rho": spec.get("rho"),
                         "source_alpha": None, "sink_alpha": sink_alpha,
                         "matched": True, "smearing_applied": False})
            continue
        if "rho" not in spec:
            raise ValueError(f"{name}: rho is required for gaussian12 smearing")
        source_alpha = gaussian12_alpha(spec["rho"], steps)
        matched = math.isclose(source_alpha, sink_alpha, rel_tol=rtol, abs_tol=atol)
        rows.append({"name": name, "steps": steps, "rho": float(spec["rho"]),
                     "source_alpha": source_alpha, "sink_alpha": sink_alpha,
                     "matched": matched, "smearing_applied": True})
        if not matched:
            mismatches.append(
                f"{name}: source alpha {source_alpha:.12g} != sink alpha {sink_alpha:.12g}"
            )

    if mismatches:
        raise ValueError("Source/sink Wuppertal alpha mismatch: " + "; ".join(mismatches))
    return rows
