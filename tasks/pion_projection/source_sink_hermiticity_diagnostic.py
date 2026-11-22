"""Plot the legacy S16T16 source-sink Hermiticity check without changing inputs.

This is an audit of already-observed arrays, not a measurement or physics score.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "results/pion_projection/s16t16_ms"
OUT_DIR = ROOT / "results/pion_projection/source_sink_hermiticity_diagnostic_20261121_v1"
TIMES = (3, 4, 5, 6)
SELECTED_POWERS = (0, 4, 16)
THRESHOLD = 0.05
SPLITS = (
    ("legacy_development", "development", range(0, 60)),
    ("observed_validation", "validation", range(70, 100)),
)


def relative_antihermitian_norm(matrix: np.ndarray) -> float:
    """Return max|C-C†|/max|C| for a finite, nonzero square matrix."""
    matrix = np.asarray(matrix)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("source-sink matrix must be square")
    if not np.isfinite(matrix).all():
        raise ValueError("source-sink matrix must be finite")
    scale = float(np.abs(matrix).max())
    if scale == 0.0:
        raise ValueError("source-sink matrix has zero normalization scale")
    return float(np.abs(matrix - matrix.conj().T).max() / scale)


def _decode_label(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, np.bytes_):
        return bytes(value).decode("utf-8")
    return str(value)


def load_split(split: str, expected_ids: range, display_name: str) -> dict[str, object]:
    """Read one pre-existing NPZ/provenance pair and construct C_ij(t)."""
    npz_path = DATA_DIR / f"{split}.npz"
    provenance_path = DATA_DIR / f"{split}_provenance.json"
    with np.load(npz_path, allow_pickle=False) as archive:
        ids = np.asarray(archive["ids"], dtype=np.int64)
        correlators = np.asarray(archive["correlators"])
        powers = [int(x) for x in archive["powers"]]
        sources = [_decode_label(x) for x in archive["sources"]]
        protocol_hash = str(np.asarray(archive["protocol_hash"]).item())

    if ids.tolist() != list(expected_ids):
        raise ValueError(f"{split}: configuration IDs do not match the frozen expected range")
    if correlators.ndim != 4 or correlators.shape[0] != len(ids):
        raise ValueError(f"{split}: unexpected correlator shape {correlators.shape}")
    if correlators.shape[1] != len(sources):
        raise ValueError(f"{split}: source labels do not match correlator axis")
    if not np.isfinite(correlators).all():
        raise ValueError(f"{split}: correlators contain non-finite values")
    if sources != ["point", "H4", "H16"]:
        raise ValueError(f"{split}: unexpected source ordering {sources}")
    if not set(SELECTED_POWERS).issubset(powers):
        raise ValueError(f"{split}: required sink powers are missing")

    with provenance_path.open(encoding="utf-8") as stream:
        provenance = json.load(stream)
    provenance_ids = [int(row["id"]) for row in provenance["records"]]
    if provenance_ids != ids.tolist():
        raise ValueError(f"{split}: provenance IDs differ from NPZ IDs")
    if [row["name"] for row in provenance["source_smear"]] != sources:
        raise ValueError(f"{split}: source labels differ from provenance")
    if str(provenance["protocol"].get("version")) != "s16t16-multisource-v1":
        raise ValueError(f"{split}: unexpected protocol version")

    selected_indices = [powers.index(power) for power in SELECTED_POWERS]
    # Axis 1 is source smearing; axis 2 is sink power. Match the existing
    # gram_identity_check convention: rows=sink (H0/H4/H16), cols=source.
    source_sink = correlators[:, :, selected_indices, :].mean(axis=0)
    matrices = {t: source_sink[:, :, t].T for t in TIMES}
    metrics = {t: relative_antihermitian_norm(matrix) for t, matrix in matrices.items()}

    return {
        "split": display_name,
        "archive_split": split,
        "ids": ids.tolist(),
        "sources": sources,
        "protocol_hash": protocol_hash,
        "provenance": provenance,
        "npz_path": npz_path,
        "provenance_path": provenance_path,
        "correlators": correlators,
        "powers": powers,
        "matrices": matrices,
        "metrics": metrics,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _save_plot(results: list[dict[str, object]], output_dir: Path) -> None:
    colors = {"legacy_development": "#2166ac", "observed_validation": "#b2182b"}
    labels = {
        "legacy_development": "S16T16 development IDs 0–59",
        "observed_validation": "S16T16 validation IDs 70–99 (already observed)",
    }

    fig, ax = plt.subplots(figsize=(8.2, 5.0), constrained_layout=True)
    for result in results:
        split = str(result["split"])
        metrics = result["metrics"]
        values = [float(metrics[t]) for t in TIMES]
        ax.plot(TIMES, values, marker="o", linewidth=2, color=colors[split], label=labels[split])
        for t, value in zip(TIMES, values):
            offset = (0, 9) if split == "observed_validation" else (0, -15)
            ax.annotate(f"{value:.3f}", (t, value), xytext=offset, textcoords="offset points",
                        ha="center", fontsize=8, color=colors[split])
    ax.axhline(THRESHOLD, color="#444444", linestyle="--", linewidth=1.4,
               label="pre-existing acceptance threshold: 5%")
    ax.set(xticks=TIMES, xlabel=r"Euclidean separation $t$",
           ylabel=r"$\max|C-C^\dagger|/\max|C|$",
           title="Legacy source–sink Hermiticity gate")
    ax.set_ylim(bottom=0.0)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    fig.savefig(output_dir / "antihermitian_fraction_by_time.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.2), constrained_layout=True)
    image = None
    for ax, result in zip(axes, results):
        split = str(result["split"])
        matrix = np.asarray(result["matrices"][5])
        normalized = np.abs(matrix - matrix.conj().T) / float(np.abs(matrix).max())
        image = ax.imshow(normalized, vmin=0.0, vmax=0.35, cmap="magma")
        short_title = "Development (IDs 0–59)" if split == "legacy_development" else "Observed validation (70–99)"
        ax.set(xticks=range(3), yticks=range(3), xticklabels=["point", "H4", "H16"],
               yticklabels=["H0", "H4", "H16"], xlabel="source smearing",
               ylabel="sink power", title=short_title)
        for i in range(3):
            for j in range(3):
                ax.text(j, i, f"{normalized[i, j]:.3f}", ha="center", va="center",
                        color="white" if normalized[i, j] > 0.16 else "black", fontsize=9)
    fig.colorbar(image, ax=axes, label=r"$|C-C^\dagger|/\max|C|$ at $t=5$")
    fig.suptitle("Element-wise anti-Hermitian mismatch (ensemble-mean matrices)")
    fig.savefig(output_dir / "antihermitian_matrix_t5.png", dpi=180)
    plt.close(fig)


def run(output_dir: Path = OUT_DIR) -> dict[str, object]:
    results = [load_split(split, expected_ids, display_name)
               for display_name, split, expected_ids in SPLITS]
    hashes = {}
    for result in results:
        for key in ("npz_path", "provenance_path"):
            path = Path(result[key])
            hashes[str(path.relative_to(ROOT))] = _sha256(path)
    protocol_hashes = {str(result["protocol_hash"]) for result in results}
    if len(protocol_hashes) != 1:
        raise ValueError("development and validation protocol hashes differ")

    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing diagnostic directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)
    try:
        rows = []
        for result in results:
            for t in TIMES:
                value = float(result["metrics"][t])
                rows.append({
                    "split": result["split"],
                    "n_configurations": len(result["ids"]),
                    "id_min": min(result["ids"]),
                    "id_max": max(result["ids"]),
                    "t": t,
                    "relative_antihermitian_max_norm": value,
                    "threshold": THRESHOLD,
                    "passes_strict_less_than_threshold": value < THRESHOLD,
                })
        with (output_dir / "summary.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

        summary = {
            "schema": "pion-source-sink-hermiticity-diagnostic-v1",
            "status": "diagnostic_only",
            "physical_score": None,
            "protocol_hash": next(iter(protocol_hashes)),
            "measurement": "ensemble-mean source-sink matrix; rows=sink power H0/H4/H16; columns=source point/H4/H16",
            "threshold": THRESHOLD,
            "threshold_rule": "relative max norm must be strictly less than 0.05",
            "splits": {
                str(result["split"]): {
                    "n_configurations": len(result["ids"]),
                    "id_min": min(result["ids"]),
                    "id_max": max(result["ids"]),
                    "metrics": {str(t): float(result["metrics"][t]) for t in TIMES},
                    "already_observed": str(result["split"]) == "observed_validation",
                }
                for result in results
            },
            "input_sha256": hashes,
            "limitations": [
                "validation IDs 70-99 were already observed; this is not a blind check",
                "the metric is evaluated on the ensemble-mean matrix and has no uncertainty band",
                "the check diagnoses matrix identity/Hermiticity only; it does not identify the unique historical cause or validate a physical reference",
            ],
        }
        (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        _save_plot(results, output_dir)
        report = [
            "# Legacy source–sink Hermiticity diagnostic",
            "",
            "This read-only CPU diagnostic reuses the saved `s16t16_ms` arrays. It does not change the measurement, symmetrize the matrix, rerun a fit, or assign a physical score.",
            "",
            "## Result",
            "",
            "The pre-existing gate requires `max|C-C†|/max|C| < 0.05`. All evaluated ensemble-mean matrices fail by a wide margin:",
            "",
            "| Split | Configurations | t=3 | t=4 | t=5 | t=6 | Gate |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
        for result in results:
            vals = [float(result["metrics"][t]) for t in TIMES]
            report.append(
                f"| {result['split']} | {len(result['ids'])} (IDs {min(result['ids'])}–{max(result['ids'])}) | "
                + " | ".join(f"{x:.4f}" for x in vals)
                + " | FAIL |"
            )
        report.extend([
            "",
            "![Relative anti-Hermitian norm versus time](antihermitian_fraction_by_time.png)",
            "",
            "![Element-wise matrix mismatch at t=5](antihermitian_matrix_t5.png)",
            "",
            "## Interpretation and limits",
            "",
            "The plotted values reproduce the existing convention in `gram_identity_check.py`: select sink powers H0/H4/H16, average configurations, transpose to rows=sink and columns=source, then compare `C` with `C†`. The validation split is already observed, so it is displayed only as an observed cross-check and must not be called blind.",
            "",
            "These are ratios from the ensemble-mean matrices, not per-configuration estimates; the figures therefore show no statistical error band. Their size establishes that the saved matrices do not satisfy the stated 5% identity gate. It does not establish why the historical mismatch occurred. The source/sink smearing-parameter mismatch documented in the TODO is a testable candidate cause, while the old receipt lacks the software/source hashes needed to prove unique attribution.",
            "",
            "Input NPZ and provenance SHA-256 values are recorded in `summary.json`. No new GPU measurement, E anchor, new D validation, or shared holdout data were accessed.",
        ])
        (output_dir / "README.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    except BaseException:
        # The destination was created by this invocation and contains only its
        # partial outputs, so remove it if generation fails.
        import shutil

        shutil.rmtree(output_dir, ignore_errors=True)
        raise
    return summary


def main() -> None:
    summary = run()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
