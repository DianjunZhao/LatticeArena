"""Finite-difference audit of an analytic Wilson-action force on a 2^4 toy lattice.

This checks the derivative of the local CPU Wilson plaquette action used by
``hmc_quality.py``. It is not a production PyQUDA/QUDA force or HMC receipt.
Run from the repository root with ``prepare``, ``execute``, then ``verify``.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.linalg import expm

from tasks.wilson_loop import hmc_quality as toy


ROOT = Path.cwd()
OUT = Path("results/wilson_loop/audit_20261120_hmc_force_fd_v3")
SOURCE = Path("tasks/wilson_loop/hmc_force_fd.py")
DEPENDENCY = Path("tasks/wilson_loop/hmc_quality.py")
BETA = 6.0
DELTAS = (1e-3, 3e-4, 1e-4, 3e-5, 1e-5)
FIELD_SPECS = (
    {"name": "haar_links", "seed": 1729, "kind": "haar_su3"},
    {"name": "near_identity", "seed": 1730, "kind": "exp_i_0p15H"},
)
INTEGRATOR_SPEC = {"seed": 5, "eps": [0.04, 0.02, 0.01, 0.005], "trajectory_length": 0.2}
PLAN = {
    "schema": "wilson-toy-force-fd-v1",
    "scope": "CPU derivative and integrator checks for hmc_quality.action on periodic 2^4 SU(3) links",
    "lattice_shape": [2, 2, 2, 2],
    "beta": BETA,
    "boundary": "periodic in all four lattice directions",
    "link_variation": "U_mu(x;delta)=exp(i*delta*T_a) U_mu(x), left tangent",
    "generator_convention": "Hermitian traceless GM basis with Tr(T_a T_b)=delta_ab",
    "force_convention": "F_mu(x)=-dS/dtheta in the declared left-tangent basis",
    "fields": list(FIELD_SPECS),
    "finite_difference_steps": list(DELTAS),
    "coverage": "all 4*2^4 links times all 8 generators for both fields at every step",
    "integrator": INTEGRATOR_SPEC,
    "acceptance_checks": {
        "action_variable_part_after_known_constant_offset_abs_max": 5e-12,
        "action_constant_offset_residual_abs_max": 5e-12,
        "force_hermitian_and_traceless_abs_max": 1e-12,
        "normalized_force_error_at_delta_1e-4_max": 5e-7,
        "normalized_force_error_q95_decreases_1e-3_to_1e-4": True,
        "leapfrog_deltaH_halving_ratio": [3.5, 4.5],
        "leapfrog_link_and_momentum_reversibility_abs_max": 1e-11,
    },
    "interpretation_boundary": "method check only; no claim about production action, GPU force, ensemble quality, or physical score",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(data: dict) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def protocol_record() -> dict:
    payload = dict(PLAN)
    payload["source_sha256"] = sha256_file(SOURCE)
    payload["dependency_sha256"] = sha256_file(DEPENDENCY)
    payload["protocol_sha256"] = sha256_bytes(canonical_json(payload))
    return payload


def dagger(a: np.ndarray) -> np.ndarray:
    return np.swapaxes(a.conj(), -1, -2)


def analytic_force(u: np.ndarray, beta: float = BETA) -> np.ndarray:
    """Return -dS in the Hermitian-traceless basis for the code's Wilson action.

    For each link, ``staple`` sums both orientations for every transverse
    direction. Coefficients are projected using the repository's orthonormal
    generators, whose trace normalization is Tr(T_a T_b)=delta_ab.
    """
    result = np.zeros_like(u, dtype=complex)
    for mu in range(4):
        staple = np.zeros_like(u[mu])
        for nu in range(4):
            if nu == mu:
                continue
            u_mu = u[mu]
            u_nu = u[nu]
            forward = (
                np.roll(u_nu, -1, axis=mu)
                @ dagger(np.roll(u_mu, -1, axis=nu))
                @ dagger(u_nu)
            )
            u_nu_x_minus_nu = np.roll(u_nu, 1, axis=nu)
            backward = (
                dagger(np.roll(np.roll(u_nu, -1, axis=mu), 1, axis=nu))
                @ dagger(np.roll(u_mu, 1, axis=nu))
                @ u_nu_x_minus_nu
            )
            staple += forward + backward

        loop_products = u[mu] @ staple
        traces = np.einsum("aij,...ji->...a", toy.GM, loop_products, optimize=True)
        coefficients = -(beta / 3.0) * np.imag(traces)
        result[mu] = np.einsum("...a,aij->...ij", coefficients, toy.GM, optimize=True)
    return result


def field_from_spec(spec: dict) -> np.ndarray:
    rng = np.random.default_rng(spec["seed"])
    shape = (4, 2, 2, 2, 2, 3, 3)
    if spec["kind"] == "haar_su3":
        return np.array(
            [[[[[toy.random_su3(rng) for _ in range(2)] for _ in range(2)]
               for _ in range(2)] for _ in range(2)] for _ in range(4)],
            dtype=complex,
        ).reshape(shape)
    if spec["kind"] == "exp_i_0p15H":
        links = np.empty(shape, dtype=complex)
        for index in np.ndindex(shape[:5]):
            raw = rng.normal(size=(3, 3)) + 1j * rng.normal(size=(3, 3))
            hermitian = 0.5 * (raw + raw.conj().T)
            hermitian -= (np.trace(hermitian).real / 3.0) * np.eye(3)
            links[index] = expm(1j * 0.15 * hermitian)
        return links
    raise ValueError(f"unknown field kind {spec['kind']}")


def explicit_action(u: np.ndarray, beta: float = BETA) -> float:
    """Slow coordinate-loop action, independent of the vectorized roll code."""
    extents = u.shape[1:5]
    total = 0.0
    for x in np.ndindex(extents):
        for mu in range(4):
            for nu in range(mu + 1, 4):
                x_mu = list(x)
                x_nu = list(x)
                x_mu[mu] = (x_mu[mu] + 1) % extents[mu]
                x_nu[nu] = (x_nu[nu] + 1) % extents[nu]
                loop = (
                    u[(mu,) + x]
                    @ u[(nu,) + tuple(x_mu)]
                    @ dagger(u[(mu,) + tuple(x_nu)])
                    @ dagger(u[(nu,) + x])
                )
                total += np.trace(loop).real / 3.0
    volume = math.prod(extents)
    return float(beta * (6 * volume - total))


def analytic_component(force: np.ndarray, mu: int, coord: tuple[int, ...], a: int) -> float:
    return float(np.trace(toy.GM[a] @ force[(mu,) + coord]).real)


def finite_difference_force(u: np.ndarray, mu: int, coord: tuple[int, ...], a: int, delta: float) -> float:
    plus, minus = u.copy(), u.copy()
    link = u[(mu,) + coord]
    generator = toy.GM[a]
    plus[(mu,) + coord] = expm(1j * delta * generator) @ link
    minus[(mu,) + coord] = expm(-1j * delta * generator) @ link
    return float(-(toy.action(plus, BETA) - toy.action(minus, BETA)) / (2.0 * delta))


def integration_rows() -> list[dict]:
    rng = np.random.default_rng(INTEGRATOR_SPEC["seed"])
    u = field_from_spec({"kind": "haar_su3", "seed": INTEGRATOR_SPEC["seed"]})
    coeff = rng.normal(size=(4, 2, 2, 2, 2, 8))
    p = np.einsum("...a,aij->...ij", coeff, toy.GM, optimize=True)
    initial_h = toy.action(u, BETA) + 0.5 * float(np.vdot(p, p).real)
    rows = []
    for eps in INTEGRATOR_SPEC["eps"]:
        steps = round(INTEGRATOR_SPEC["trajectory_length"] / eps)
        u1, p1 = toy.leapfrog(u.copy(), p.copy(), analytic_force, eps, steps)
        final_h = toy.action(u1, BETA) + 0.5 * float(np.vdot(p1, p1).real)
        u2, p2 = toy.leapfrog(u1.copy(), -p1.copy(), analytic_force, eps, steps)
        rows.append({
            "eps": eps,
            "steps": steps,
            "trajectory_length": INTEGRATOR_SPEC["trajectory_length"],
            "delta_H_signed": float(final_h - initial_h),
            "delta_H_abs": float(abs(final_h - initial_h)),
            "link_reversibility_max_abs": float(np.max(np.abs(u2 - u))),
            "momentum_reversibility_max_abs": float(np.max(np.abs(p2 + p))),
        })
    for i in range(1, len(rows)):
        rows[i]["delta_H_ratio_to_previous"] = rows[i - 1]["delta_H_abs"] / rows[i]["delta_H_abs"]
    rows[0]["delta_H_ratio_to_previous"] = None
    return rows


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def error_summary(rows: list[dict]) -> dict:
    grouped: dict[tuple[str, float], list[dict]] = {}
    for row in rows:
        grouped.setdefault((row["field"], float(row["delta"])), []).append(row)
    output = []
    for (field, delta), items in sorted(grouped.items(), key=lambda pair: (pair[0][0], -pair[0][1])):
        abs_error = np.array([float(item["abs_error"]) for item in items])
        norm_error = np.array([float(item["normalized_error"]) for item in items])
        output.append({
            "field": field,
            "delta": delta,
            "components": len(items),
            "abs_error_median": float(np.quantile(abs_error, 0.5)),
            "abs_error_q95": float(np.quantile(abs_error, 0.95)),
            "abs_error_max": float(abs_error.max()),
            "normalized_error_median": float(np.quantile(norm_error, 0.5)),
            "normalized_error_q95": float(np.quantile(norm_error, 0.95)),
            "normalized_error_max": float(norm_error.max()),
        })
    return {"finite_difference_error_by_field_delta": output}


def collect_metrics() -> tuple[list[dict], dict]:
    rows = []
    checks = {"action_variable_part_abs": {}, "action_constant_offset": {}, "force_algebra_residuals": {}}
    for spec in FIELD_SPECS:
        u = field_from_spec(spec)
        explicit = explicit_action(u, BETA)
        lattice_volume = math.prod(u.shape[1:5])
        expected_offset = float(BETA * (6 * u.shape[1] ** 3 - 6 * lattice_volume))
        measured_offset = float(toy.action(u, BETA) - explicit)
        cold = np.broadcast_to(np.eye(3, dtype=complex), u.shape).copy()
        cold_offset = float(toy.action(cold, BETA) - explicit_action(cold, BETA))
        checks["action_constant_offset"][spec["name"]] = {
            "measured": measured_offset,
            "expected_from_code_zero_point": expected_offset,
            "residual_abs": abs(measured_offset - expected_offset),
        }
        checks["action_variable_part_abs"][spec["name"]] = float(abs(
            (toy.action(u, BETA) - toy.action(cold, BETA))
            - (explicit - explicit_action(cold, BETA))
        ))
        f = analytic_force(u, BETA)
        checks["force_algebra_residuals"][spec["name"]] = {
            "hermitian_max_abs": float(np.max(np.abs(f - dagger(f)))),
            "trace_max_abs": float(np.max(np.abs(np.trace(f, axis1=-2, axis2=-1)))),
            "unitarity_max_abs": float(np.max(np.abs(u @ dagger(u) - np.eye(3)))),
            "determinant_max_abs": float(np.max(np.abs(np.linalg.det(u) - 1.0))),
        }
        for mu in range(4):
            for coord in np.ndindex((2, 2, 2, 2)):
                for a in range(8):
                    analytic = analytic_component(f, mu, coord, a)
                    for delta in DELTAS:
                        numeric = finite_difference_force(u, mu, coord, a, delta)
                        absolute = abs(numeric - analytic)
                        rows.append({
                            "field": spec["name"],
                            "seed": spec["seed"],
                            "mu": mu,
                            "x0": coord[0], "x1": coord[1], "x2": coord[2], "x3": coord[3],
                            "generator": a,
                            "delta": delta,
                            "analytic_force_component": analytic,
                            "central_difference_force_component": numeric,
                            "abs_error": absolute,
                            "normalized_error": absolute / max(1.0, abs(analytic)),
                        })
    return rows, checks


def plot_diagnostics(summary: dict, integration: list[dict], destination: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6))
    styles = {"haar_links": "o-", "near_identity": "s--"}
    for field, label in (("haar_links", "Haar SU(3) links"), ("near_identity", "exp(i 0.15 H) links")):
        selected = [row for row in summary["finite_difference_error_by_field_delta"] if row["field"] == field]
        selected.sort(key=lambda row: row["delta"], reverse=True)
        x = [row["delta"] for row in selected]
        axes[0].loglog(x, [row["normalized_error_q95"] for row in selected], styles[field], label=f"{label}: q95")
        axes[0].loglog(x, [row["normalized_error_max"] for row in selected], styles[field], alpha=0.48,
                       label=f"{label}: max")
    axes[0].invert_xaxis()
    axes[0].set(xlabel="central-difference step δ (smaller →)", ylabel="normalized |F_FD − F_analytic|",
                title="Analytic staple force vs action finite difference")
    axes[0].grid(True, which="both", alpha=0.22)
    axes[0].legend(fontsize=7.4)

    eps = [row["eps"] for row in integration]
    dh = [row["delta_H_abs"] for row in integration]
    rev = [row["link_reversibility_max_abs"] for row in integration]
    axes[1].loglog(eps, dh, "o-", label="|ΔH|")
    axes[1].loglog(eps, rev, "s--", label="link reversibility")
    axes[1].invert_xaxis()
    axes[1].set(xlabel="leapfrog step ε (smaller →)", ylabel="absolute error",
                title="Leapfrog using the analytic toy force")
    axes[1].grid(True, which="both", alpha=0.22)
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(destination, dpi=180)
    plt.close(fig)


def markdown_report(summary: dict, checks: dict, integration: list[dict], status: str) -> str:
    rows = summary["finite_difference_error_by_field_delta"]
    lines = [
        "# CPU analytic-force finite-difference audit",
        "",
        f"**Status: `{status}`.** This is a derivative and integrator check of the local Python Wilson plaquette action on a periodic $2^4$ SU(3) toy lattice. It is not a production PyQUDA/QUDA force, a GPU/MPI HMC run, or a physical ensemble validation.",
        "",
        "## Frozen convention and coverage",
        "",
        "The action is the `tasks/wilson_loop/hmc_quality.py` implementation with $\\beta=6$. Links are indexed `(mu,x0,x1,x2,x3)` and all four directions are periodic. A link is varied on the left as $U_\\mu(x;\\delta)=e^{i\\delta T_a}U_\\mu(x)$. The eight repository generators are Hermitian, traceless, and normalized by $\\mathrm{Tr}(T_aT_b)=\\delta_{ab}$; the reported force is $F=-\\partial S/\\partial\\theta$ projected in that basis.",
        "",
        "Two deterministic fields were used: independent Haar-distributed SU(3) links and near-identity links $e^{i0.15H}$ with random Hermitian traceless $H$. For both fields, every one of the $4\\times2^4$ links and all eight generators was checked at five central-difference steps (5120 scalar derivative comparisons total). The action implementation was also compared with a separate explicit coordinate-loop implementation.",
        "",
        "## Results",
        "",
        "| Field | δ | Components | normalized error q95 | normalized error max |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(f"| {row['field']} | {row['delta']:.0e} | {row['components']} | {row['normalized_error_q95']:.3e} | {row['normalized_error_max']:.3e} |")
    lines.extend([
        "",
        "The normalized error is $|F_{FD}-F|/\\max(1,|F|)$, so components near zero do not acquire unstable relative errors. Its q95 decreases by approximately the expected $\\delta^2$ factor from $10^{-3}$ to $10^{-4}$, then floating-point cancellation starts to limit gains at the smallest steps. Full component-level data are in `force_fd_components.csv`.",
        "",
        f"The existing action uses the additive zero point $\\beta(6L^3)$ on this isotropic code path, whereas the explicit coordinate implementation uses $\\beta(6V)$. For $L=2$, their measured gauge-independent offset is `{checks['action_constant_offset']['haar_links']['measured']:.1f}` (expected `{checks['action_constant_offset']['haar_links']['expected_from_code_zero_point']:.1f}`); after subtracting it, the maximum variable-part residual is `{max(checks['action_variable_part_abs'].values()):.3e}`. This offset cancels in force derivatives and $\\Delta H$. Across both fields, the maximum force Hermiticity residual was `{max(v['hermitian_max_abs'] for v in checks['force_algebra_residuals'].values()):.3e}` and maximum trace residual was `{max(v['trace_max_abs'] for v in checks['force_algebra_residuals'].values()):.3e}`.",
        "",
        "### Leapfrog control",
        "",
        "| ε | Steps | |ΔH| | ΔH ratio to previous | Link reversibility max | Momentum reversibility max |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    for row in integration:
        ratio = "—" if row["delta_H_ratio_to_previous"] is None else f"{row['delta_H_ratio_to_previous']:.3f}"
        lines.append(f"| {row['eps']:.4f} | {row['steps']} | {row['delta_H_abs']:.3e} | {ratio} | {row['link_reversibility_max_abs']:.3e} | {row['momentum_reversibility_max_abs']:.3e} |")
    lines.extend([
        "",
        "The trajectory length is fixed at 0.2 and the momenta are one deterministic canonical Gaussian draw in the declared orthonormal generator basis. Halving ε gives an approximately fourfold reduction in |ΔH|, consistent with the leapfrog second-order trend; reversing momenta returns links and momenta to floating-point precision.",
        "",
        "![Force finite-difference and leapfrog diagnostics](hmc_force_fd.png)",
        "",
        "## Interpretation and limits",
        "",
        "This closes the CPU analytic-force finite-difference item for the local toy action and strengthens the integrator check by using that analytic force. It does not verify that this toy action, staple convention, link layout, normalization, or force matches the target production HMC implementation. The random link fields are numerical stress controls, not equilibrium gauge configurations. Production ΔH/acceptance, thermalization, autocorrelation, provenance identity, MPI/GPU behavior, and protocol_v4 remain open.",
        "",
        "Recheck artifact hashes and derived row counts with `python -B -m tasks.wilson_loop.hmc_force_fd verify`.",
    ])
    return "\n".join(lines) + "\n"


def prepare() -> None:
    OUT.mkdir(parents=True, exist_ok=False)
    record = protocol_record()
    (OUT / "protocol.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"prepared": str(OUT), "protocol_sha256": record["protocol_sha256"]}, indent=2))


def execute() -> None:
    protocol_path = OUT / "protocol.json"
    if not protocol_path.exists():
        raise FileNotFoundError("run prepare before execute")
    protocol = json.loads(protocol_path.read_text())
    current = protocol_record()
    if protocol != current:
        raise RuntimeError("protocol/source/dependency hash mismatch; do not execute under a changed design")
    expected_outputs = ("force_fd_components.csv", "leapfrog.csv", "summary.json", "hmc_force_fd.png", "README.md")
    if any((OUT / name).exists() for name in expected_outputs):
        raise FileExistsError("output already exists; preserve it and prepare a new versioned directory")

    rows, checks = collect_metrics()
    write_csv(OUT / "force_fd_components.csv", rows, [
        "field", "seed", "mu", "x0", "x1", "x2", "x3", "generator", "delta",
        "analytic_force_component", "central_difference_force_component", "abs_error", "normalized_error",
    ])
    integration = integration_rows()
    write_csv(OUT / "leapfrog.csv", integration, [
        "eps", "steps", "trajectory_length", "delta_H_signed", "delta_H_abs",
        "link_reversibility_max_abs", "momentum_reversibility_max_abs", "delta_H_ratio_to_previous",
    ])
    summary = error_summary(rows)
    summary.update(checks)
    summary["integration"] = integration

    check = PLAN["acceptance_checks"]
    action_variable_ok = max(checks["action_variable_part_abs"].values()) <= check["action_variable_part_after_known_constant_offset_abs_max"]
    action_offset_ok = max(value["residual_abs"] for value in checks["action_constant_offset"].values()) <= check["action_constant_offset_residual_abs_max"]
    algebra_ok = max(
        max(value["hermitian_max_abs"], value["trace_max_abs"])
        for value in checks["force_algebra_residuals"].values()
    ) <= check["force_hermitian_and_traceless_abs_max"]
    h100 = [row for row in summary["finite_difference_error_by_field_delta"] if math.isclose(row["delta"], 1e-4)]
    fd_ok = max(row["normalized_error_max"] for row in h100) <= check["normalized_force_error_at_delta_1e-4_max"]
    trend_ok = all(
        next(row for row in summary["finite_difference_error_by_field_delta"] if row["field"] == field and math.isclose(row["delta"], 1e-3))["normalized_error_q95"]
        > next(row for row in summary["finite_difference_error_by_field_delta"] if row["field"] == field and math.isclose(row["delta"], 1e-4))["normalized_error_q95"]
        for field in (spec["name"] for spec in FIELD_SPECS)
    )
    ratios = [row["delta_H_ratio_to_previous"] for row in integration[1:]]
    ratio_ok = all(check["leapfrog_deltaH_halving_ratio"][0] <= ratio <= check["leapfrog_deltaH_halving_ratio"][1] for ratio in ratios)
    reverse_ok = max(
        max(row["link_reversibility_max_abs"], row["momentum_reversibility_max_abs"])
        for row in integration
    ) <= check["leapfrog_link_and_momentum_reversibility_abs_max"]
    summary["acceptance"] = {
        "action_variable_part": bool(action_variable_ok),
        "action_constant_offset": bool(action_offset_ok),
        "force_hermitian_traceless": bool(algebra_ok),
        "force_fd_at_1e-4": bool(fd_ok),
        "force_fd_q95_decreases_1e-3_to_1e-4": bool(trend_ok),
        "leapfrog_second_order_ratio": bool(ratio_ok),
        "leapfrog_reversibility": bool(reverse_ok),
    }
    status = "PASS_TOY_CPU_CHECKS" if all(summary["acceptance"].values()) else "FAIL_TOY_CPU_CHECKS"
    summary["status"] = status
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    plot_diagnostics(summary, integration, OUT / "hmc_force_fd.png")
    (OUT / "README.md").write_text(markdown_report(summary, checks, integration, status))

    artifact_names = (*expected_outputs, "protocol.json")
    provenance = {
        "schema": "wilson-toy-force-fd-provenance-v1",
        "protocol_sha256": protocol["protocol_sha256"],
        "source_sha256": sha256_file(SOURCE),
        "dependency_sha256": sha256_file(DEPENDENCY),
        "artifact_sha256": {name: sha256_file(OUT / name) for name in artifact_names},
        "finite_difference_rows": len(rows),
        "integration_rows": len(integration),
        "status": status,
        "python": __import__("platform").python_version(),
        "numpy": np.__version__,
        "scipy": __import__("scipy").__version__,
        "matplotlib": __import__("matplotlib").__version__,
    }
    (OUT / "execution_provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": status, "rows": len(rows), "output": str(OUT), "acceptance": summary["acceptance"]}, indent=2))
    if status != "PASS_TOY_CPU_CHECKS":
        raise SystemExit(1)


def verify() -> None:
    protocol = json.loads((OUT / "protocol.json").read_text())
    current = protocol_record()
    if protocol != current:
        raise RuntimeError("frozen protocol/source/dependency identity does not match current files")
    provenance = json.loads((OUT / "execution_provenance.json").read_text())
    if provenance["protocol_sha256"] != protocol["protocol_sha256"]:
        raise RuntimeError("protocol hash mismatch")
    for name, expected in provenance["artifact_sha256"].items():
        if sha256_file(OUT / name) != expected:
            raise RuntimeError(f"artifact hash mismatch: {name}")
    with (OUT / "force_fd_components.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != provenance["finite_difference_rows"] or len(rows) != 5120:
        raise RuntimeError("finite-difference row count mismatch")
    if not all(math.isfinite(float(row[key])) for row in rows for key in ("analytic_force_component", "central_difference_force_component", "normalized_error")):
        raise RuntimeError("nonfinite derivative row")
    derived = error_summary(rows)["finite_difference_error_by_field_delta"]
    stored = json.loads((OUT / "summary.json").read_text())
    for actual, expected in zip(derived, stored["finite_difference_error_by_field_delta"]):
        for key in ("normalized_error_q95", "normalized_error_max", "abs_error_q95", "abs_error_max"):
            if not math.isclose(actual[key], expected[key], rel_tol=1e-12, abs_tol=1e-18):
                raise RuntimeError(f"summary derivation mismatch: {actual['field']} δ={actual['delta']} {key}")
    if stored["status"] != "PASS_TOY_CPU_CHECKS" or not all(stored["acceptance"].values()):
        raise RuntimeError("the frozen CPU acceptance criteria were not all met")
    print(json.dumps({"verification": "PASS", "rows": len(rows), "artifact_count": len(provenance["artifact_sha256"]), "status": stored["status"]}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "execute", "verify"))
    args = parser.parse_args()
    {"prepare": prepare, "execute": execute, "verify": verify}[args.mode]()


if __name__ == "__main__":
    main()
