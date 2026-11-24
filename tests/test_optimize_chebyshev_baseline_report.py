import hashlib
import json

from tasks.optimize_gaussian.chebyshev_baseline import build


def test_constrained_baseline_report_is_hashed_and_labels_illustration_denominators(tmp_path):
    output = tmp_path / "constrained-baseline"
    contract = build(output)

    assert contract["status"] == "REVIEW_DRAFT_NOT_FROZEN"
    assert contract["physical_score"] is None
    assert contract["illustration_denominators"] == {
        "planned": 3,
        "valid": 3,
        "failed": 0,
        "abstained": 0,
        "unit": "deterministic response examples, not fit runs or physical samples",
    }
    readme = (output / "README.md").read_text()
    assert "planned/valid/failed/abstained = `3/3/0/0`" in readme
    assert "no physics objective" in readme

    manifest = json.loads((output / "artifact_hashes.json").read_text())
    assert set(manifest) == {
        "contract.json",
        "spectral_response.png",
        "README.md",
        "snapshot_chebyshev_baseline.py",
        "snapshot_kernels.py",
    }
    for name, expected in manifest.items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == expected
    assert (output / "spectral_response.png").is_file()
