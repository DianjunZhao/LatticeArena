import builtins
import hashlib
import json
from pathlib import Path

import pytest

from tasks.pion_projection import measure_multisource
from tasks.pion_projection.smearing_contract import (
    gaussian12_alpha,
    gaussian12_rho,
    validate_source_sink_smearing,
)


ROOT = Path(__file__).resolve().parents[1]


def _legacy_multisource_protocol():
    return json.loads((ROOT / "tasks/pion_projection/protocol_multisource.json").read_text())


def _install_protocol(monkeypatch, protocol):
    monkeypatch.setattr(
        measure_multisource,
        "read_protocol_snapshot",
        lambda protocol_path=None: (protocol, hashlib.sha256(b"frozen test protocol").hexdigest()),
    )


def test_protocol_snapshot_hashes_the_exact_file_bytes(monkeypatch):
    path = ROOT / "tasks/pion_projection/protocol_multisource.json"
    protocol, protocol_sha256 = measure_multisource.read_protocol_snapshot(path)

    assert protocol == _legacy_multisource_protocol()
    assert protocol_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()


def test_default_protocol_is_the_multisource_protocol_not_single_source_protocol():
    protocol, protocol_sha256 = measure_multisource.read_protocol_snapshot()
    expected = ROOT / "tasks/pion_projection/protocol_multisource.json"
    assert measure_multisource.DEFAULT_MULTISOURCE_PROTOCOL.resolve() == expected.resolve()
    assert protocol == _legacy_multisource_protocol()
    assert protocol_sha256 == hashlib.sha256(expected.read_bytes()).hexdigest()


def test_legacy_multisource_protocol_fails_closed_with_alpha_diagnostic():
    protocol = _legacy_multisource_protocol()
    with pytest.raises(ValueError, match="H4: source alpha .* != sink alpha 0.2.*H16"):
        validate_source_sink_smearing(protocol)
    assert gaussian12_alpha(protocol["source_smear"][1]["rho"], 4) == pytest.approx(0.5454545454545454)
    assert gaussian12_alpha(protocol["source_smear"][2]["rho"], 16) == pytest.approx(0.5454545454545454)


@pytest.mark.parametrize("steps", [1, 4, 16, 64])
def test_rho_conversion_round_trips_requested_alpha(steps):
    rho = gaussian12_rho(0.2, steps)
    assert rho == pytest.approx((4 * steps / 11) ** 0.5)
    assert gaussian12_alpha(rho, steps) == pytest.approx(0.2)


def test_matched_plan_reports_source_and_sink_parameters():
    protocol = _legacy_multisource_protocol()
    protocol["source_smear"][1]["rho"] = gaussian12_rho(protocol["alpha"], 4)
    protocol["source_smear"][2]["rho"] = gaussian12_rho(protocol["alpha"], 16)

    rows = validate_source_sink_smearing(protocol)

    assert [row["matched"] for row in rows] == [True, True, True]
    assert rows[0]["source_alpha"] is None
    assert rows[1]["source_alpha"] == pytest.approx(protocol["alpha"])
    assert rows[2]["source_alpha"] == pytest.approx(protocol["alpha"])


def test_versioned_matched_protocol_file_is_hash_bound_and_preflight_ready():
    path = ROOT / "tasks/pion_projection/protocol_multisource_matched_v2.json"
    protocol, protocol_sha256 = measure_multisource.read_protocol_snapshot(path)
    rows = validate_source_sink_smearing(protocol)

    assert protocol["version"] == "s16t16-multisource-matched-v2"
    assert [row["matched"] for row in rows] == [True, True, True]
    assert protocol["source_smear"][1]["rho"] == pytest.approx(1.2060453783)
    assert protocol["source_smear"][2]["rho"] == pytest.approx(2.4120907566)
    assert protocol_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()


def test_matched_protocol_cpu_preflight_does_not_import_gpu_or_create_output(tmp_path, monkeypatch):
    protocol_path = ROOT / "tasks/pion_projection/protocol_multisource_matched_v2.json"
    output = tmp_path / "new_generation"
    imported_gpu_modules = []
    original_import = builtins.__import__

    def reject_gpu_imports(name, *args, **kwargs):
        if name == "cupy" or name == "mpi4py" or name.startswith("pyquda_utils"):
            imported_gpu_modules.append(name)
            raise AssertionError(f"GPU module imported during CPU preflight: {name}")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_gpu_imports)
    plan = measure_multisource.measure_multisource(
        output, "development", limit=2, protocol_path=protocol_path, preflight_only=True
    )

    assert plan["ids"] == [0, 1]
    assert plan["protocol"]["version"] == "s16t16-multisource-matched-v2"
    assert plan["smearing_contract"][-1]["matched"] is True
    assert plan["protocol_sha256"] == hashlib.sha256(protocol_path.read_bytes()).hexdigest()
    assert not output.exists()
    assert imported_gpu_modules == []


def test_generation_id_binds_protocol_split_ids_and_source_hashes():
    source_hashes = {"measure_multisource.py": "a" * 64, "smearing_contract.py": "b" * 64}
    common = ("c" * 64, "d" * 64, "development", [0, 1, 2], source_hashes)
    base = measure_multisource.multisource_generation_id(*common)

    assert measure_multisource.multisource_generation_id(*common) == base
    assert measure_multisource.multisource_generation_id(
        *common[:2], "validation", common[3], common[4]
    ) != base
    assert measure_multisource.multisource_generation_id(
        common[0], common[1], common[2], [0, 2, 1], common[4]
    ) != base
    assert measure_multisource.multisource_generation_id(
        common[0], common[1], common[2], common[3], {**source_hashes, "measure_multisource.py": "e" * 64}
    ) != base


def test_source_propagator_smearing_passes_sink_alpha_to_all_columns():
    class Propagator:
        def __init__(self, values=None):
            self.values = values or {
                (spin, color): (spin, color) for spin in range(4) for color in range(3)
            }

        def getFermion(self, spin, color):
            return self.values[(spin, color)]

        def setFermion(self, value, spin, color):
            self.values[(spin, color)] = value

    source = Propagator()
    output = Propagator({(spin, color): None for spin in range(4) for color in range(3)})
    calls = []

    def fake_wuppertal(field, steps, alpha):
        calls.append((field, steps, alpha))
        return ("smeared", field)

    result = measure_multisource.apply_matched_propagator_smear(
        source, output, steps=4, alpha=0.2, wuppertal_smear=fake_wuppertal
    )

    assert result is output
    assert len(calls) == 12
    assert all(steps == 4 and alpha == 0.2 for _, steps, alpha in calls)
    assert all(value[0] == "smeared" for value in output.values.values())


def test_measurement_rejects_mismatch_before_output_or_gpu_imports(tmp_path, monkeypatch):
    protocol = _legacy_multisource_protocol()
    _install_protocol(monkeypatch, protocol)
    output = tmp_path / "must_not_be_created"
    imported_gpu_modules = []
    original_import = builtins.__import__

    def reject_gpu_imports(name, *args, **kwargs):
        if name == "cupy" or name == "mpi4py" or name.startswith("pyquda_utils"):
            imported_gpu_modules.append(name)
            raise AssertionError(f"GPU module imported before preflight: {name}")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_gpu_imports)

    with pytest.raises(ValueError, match="Source/sink Wuppertal alpha mismatch"):
        measure_multisource.measure_multisource(output, "development", limit=1)

    assert not output.exists()
    assert imported_gpu_modules == []


def test_existing_output_is_rejected_before_gpu_import_or_overwrite(tmp_path, monkeypatch):
    protocol = _legacy_multisource_protocol()
    protocol["source_smear"][1]["rho"] = gaussian12_rho(protocol["alpha"], 4)
    protocol["source_smear"][2]["rho"] = gaussian12_rho(protocol["alpha"], 16)
    _install_protocol(monkeypatch, protocol)
    output = tmp_path / "existing_generation"
    output.mkdir()
    sentinel = output / "prior_result.txt"
    sentinel.write_text("preserve this generation")
    imported_gpu_modules = []
    original_import = builtins.__import__

    def reject_gpu_imports(name, *args, **kwargs):
        if name == "cupy" or name == "mpi4py" or name.startswith("pyquda_utils"):
            imported_gpu_modules.append(name)
            raise AssertionError(f"GPU module imported before output preflight: {name}")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_gpu_imports)
    with pytest.raises(FileExistsError, match="Refusing to reuse existing multisource output path"):
        measure_multisource.measure_multisource(output, "development", limit=1)

    assert sentinel.read_text() == "preserve this generation"
    assert imported_gpu_modules == []


@pytest.mark.parametrize(
    "rho,steps",
    [(0.0, 4), (-1.0, 4), (1.0, 0), (float("inf"), 4), (1.0, True)],
)
def test_invalid_gaussian_parameters_are_rejected(rho, steps):
    with pytest.raises(ValueError):
        gaussian12_alpha(rho, steps)
