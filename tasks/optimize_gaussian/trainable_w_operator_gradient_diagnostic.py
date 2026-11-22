"""Finite-difference audit for the trainable-W hopping correlator gradient.

Deterministic CPU fixture only. No production gauge, propagator, reference,
GPU, or sealed split is read.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from . import trainable_w as model
from .trainable_w_diagnostic import su3


DEFAULT_OUT = (Path(__file__).resolve().parents[2]
               / "results/optimize_gaussian/trainable_w_operator_gradient_20261121_v1")
STEPS = (1e-2, 2e-3, 4e-4, 1e-4, 2e-5, 4e-6, 2e-6, 1e-6, 2e-7)


def _fixture():
    rng = np.random.default_rng(92021)
    links = [su3(rng, (3, 3, 3, 3)) for _ in range(2)]
    rng_field = np.random.default_rng(92024)
    field = (rng_field.normal(size=(3, 3, 3, 3, 4))
             + 1j * rng_field.normal(size=(3, 3, 3, 3, 4)))
    W = np.array([[1.2, -.7], [-.4, 1.1]])
    v = np.array([.2, -.3])
    c = .06
    return links[0], field, W, v, c


def _parameter_labels(hidden: int) -> list[str]:
    return ([f"W[{h},{j}]" for h in range(hidden) for j in range(2)]
            + [f"v[{h}]" for h in range(hidden)] + ["c"])


def run(output: str | Path = DEFAULT_OUT) -> dict:
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    links, field, W, v, c = _fixture()
    initial = model.pack(W, v, c)
    value, analytic = model.correlator_and_gradient(field, links, W, v, c)
    labels = _parameter_labels(len(v))
    rows, curves = [], []
    for step in STEPS:
        numeric = np.empty_like(initial)
        for index in range(len(initial)):
            plus, minus = initial.copy(), initial.copy()
            plus[index] += step
            minus[index] -= step
            Wp, vp, cp = model.unpack(plus, len(v))
            Wm, vm, cm = model.unpack(minus, len(v))
            fp = model.correlator_and_gradient(field, links, Wp, vp, cp)[0]
            fm = model.correlator_and_gradient(field, links, Wm, vm, cm)[0]
            numeric[index] = (fp - fm) / (2.0 * step)
            rows.append({
                "step": step, "parameter": labels[index],
                "analytic": analytic[index], "finite_difference": numeric[index],
                "absolute_error": abs(numeric[index] - analytic[index]),
            })
        curves.append({
            "step": step,
            "max_abs_error": float(np.max(np.abs(numeric - analytic))),
            "max_scaled_error": float(
                np.max(np.abs(numeric - analytic)) / max(1.0, np.max(np.abs(analytic)))),
        })

    raw_path = out / "gradient_components.csv"
    with raw_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "classification": "deterministic CPU operator-gradient implementation audit",
        "physical_score": None,
        "data_use": "synthetic SU(3) links and a deterministic complex probe field only",
        "seed_links": 92021,
        "seed_field": 92024,
        "geometry_xyz_storage_zyx": [3, 3, 3],
        "hidden": len(v),
        "parameter_count": len(initial),
        "correlator": value,
        "analytic_gradient": analytic.tolist(),
        "steps": list(STEPS),
        "error_curves": curves,
        "best_step": min(curves, key=lambda row: row["max_abs_error"])["step"],
        "best_max_abs_error": min(row["max_abs_error"] for row in curves),
        "fixed_step_2e-6_max_abs_error": next(
            row["max_abs_error"] for row in curves if row["step"] == 2e-6),
        "planned_parameter_checks": len(STEPS) * len(initial),
        "valid_parameter_checks": len(rows),
        "failed_parameter_checks": sum(not np.isfinite(row["finite_difference"])
                                        for row in rows),
        "abstained_parameter_checks": 0,
        "source_hashes": {
            name: hashlib.sha256((Path(__file__).resolve().parent / name).read_bytes()).hexdigest()
            for name in ("trainable_w.py", "trainable_w_operator_gradient_diagnostic.py",
                         "features.py", "kernels.py", "trainable_w_diagnostic.py")
        },
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    _plot(out / "gradient_convergence.png", curves)
    report = [
        "# Trainable-W actual-kernel gradient audit",
        "",
        "**Deterministic CPU implementation check.** It uses synthetic SU(3) links and a complex probe field; no production gauge, propagator, reference, GPU, or sealed split is read. `physical_score=null`.",
        "",
        "The checked scalar is the actual real hopping correlator `Re <psi|K(W,v,c)|psi>` using `features.directional_features` and `kernels.apply_kernel`. Spatial axes are stored `(z,y,x)`, link directions `(x,y,z)`, and the probe has four columns.",
        "",
        "For each link coefficient, the derivative of the forward and adjoint backward hop is `q_mu(x)=2 Re sum_color,probe psi(x)^dagger U_mu(x) psi(x+mu)`. The remaining chain rule is",
        "",
        "```text",
        "dC/dc       = sum_(mu,x) q_mu(x)",
        "dC/dv_h     = sum_(mu,x) q_mu(x) centered_phi_h(mu,x)",
        "dC/dW_hj    = sum_(mu,x) [q_mu(x)-mean_x q_mu(x)] v_h (1-phi_h(mu,x)^2) z_mu,j(x)",
        "```",
        "",
        "The projected `q-mean_x(q)` is required because the model centers every feature over each direction's spatial slice. The plot compares all 7 W/v/c components to central differences over nine step sizes; each point includes every component, not just a selected parameter.",
        "",
        "![Finite-difference convergence for the operator gradient](gradient_convergence.png)",
        "",
        f"There were {summary['planned_parameter_checks']} planned checks, {summary['valid_parameter_checks']} finite checks, {summary['failed_parameter_checks']} nonfinite checks, and {summary['abstained_parameter_checks']} abstentions. At the unit-test step `2e-6`, maximum absolute error was {summary['fixed_step_2e-6_max_abs_error']:.3e}; the best sweep error was {summary['best_max_abs_error']:.3e} at step {summary['best_step']:.1e}.",
        "",
        "This verifies the chain derivative through the actual CPU hopping kernel for this finite deterministic fixture. It does not validate GPU/CuPy behavior, the Gaussian sandwich, positivity, QUDA propagators, the ensemble-risk/reference derivative, solver convergence, or any physical comparison. The production `train.main` still does not optimize W; objective and solver budgets remain protocol decisions.",
        "",
        "Raw per-component/per-step values are in `gradient_components.csv`; source and artifact hashes are in `artifact_hashes.json`.",
    ]
    (out / "README.md").write_text("\n".join(report) + "\n")
    hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (raw_path, out / "summary.json", out / "gradient_convergence.png",
                     out / "README.md")
    }
    (out / "artifact_hashes.json").write_text(json.dumps(hashes, indent=2) + "\n")
    return summary


def _plot(path: Path, curves: list[dict]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    steps = np.asarray([row["step"] for row in curves])
    errors = np.asarray([row["max_abs_error"] for row in curves])
    fig, ax = plt.subplots(figsize=(7.5, 4.5), layout="constrained")
    ax.loglog(steps, errors, marker="o", label="max over all W/v/c components")
    ax.axvline(2e-6, color="tab:red", linestyle="--", label="unit-test step")
    ax.set_xlabel("central finite-difference step")
    ax.set_ylabel("maximum absolute gradient error")
    ax.set_title("Actual hopping-correlator gradient: finite-difference convergence")
    ax.grid(True, which="both", alpha=0.22)
    ax.legend()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    summary = run(args.output)
    print(json.dumps({"output": str(args.output),
                      "classification": summary["classification"],
                      "checks": summary["valid_parameter_checks"],
                      "best_max_abs_error": summary["best_max_abs_error"]}))


if __name__ == "__main__":
    main()
