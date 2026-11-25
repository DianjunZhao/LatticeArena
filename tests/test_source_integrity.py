import hashlib

import pytest

from core.source_integrity import verify_source_bytes


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_verify_source_bytes_hashes_only_named_files_under_root(tmp_path):
    (tmp_path / "manifest.json").write_bytes(b'{"id": 1}')
    (tmp_path / "correlator.bin").write_bytes(b"synthetic-correlator")

    receipt = verify_source_bytes(
        tmp_path,
        {"manifest": _sha(b'{"id": 1}'), "correlator": _sha(b"synthetic-correlator")},
        {"manifest": "manifest.json", "correlator": "correlator.bin"},
    )

    assert receipt["status"] == "verified"
    assert receipt["denominator"] == {
        "unit": "source_file",
        "planned": 2,
        "valid": 2,
        "failed": 0,
        "abstained": 0,
        "not_run": 0,
    }
    assert receipt["entries"]["manifest"]["observed_sha256"] == _sha(b'{"id": 1}')


def test_hash_mismatch_is_failed_and_does_not_claim_verified(tmp_path):
    (tmp_path / "data.bin").write_bytes(b"observed bytes")

    receipt = verify_source_bytes(
        tmp_path,
        {"data": _sha(b"expected bytes")},
        {"data": "data.bin"},
    )

    assert receipt["status"] == "incomplete"
    assert receipt["denominator"]["failed"] == 1
    assert receipt["entries"]["data"]["reason"] == "sha256_mismatch"
    assert receipt["entries"]["data"]["observed_sha256"] == _sha(b"observed bytes")


def test_missing_path_mapping_and_missing_file_are_abstentions(tmp_path):
    receipt = verify_source_bytes(
        tmp_path,
        {"unmapped": _sha(b"a"), "missing": _sha(b"b")},
        {"missing": "not-present.bin"},
    )

    assert receipt["status"] == "incomplete"
    assert receipt["denominator"]["planned"] == 2
    assert receipt["denominator"]["abstained"] == 2
    assert receipt["denominator"]["not_run"] == 0
    assert receipt["entries"]["unmapped"]["reason"] == "source_path_missing_or_invalid"
    assert receipt["entries"]["missing"]["reason"] == "source_file_not_found"


def test_path_traversal_is_failed_without_hashing_outside_file(tmp_path, monkeypatch):
    outside = tmp_path.parent / "outside-source.bin"
    outside.write_bytes(b"must not be opened")
    called = False

    def forbidden_hash(path):
        nonlocal called
        called = True
        raise AssertionError(f"unexpected hash read: {path}")

    monkeypatch.setattr("core.source_integrity._sha256_file", forbidden_hash)
    receipt = verify_source_bytes(
        tmp_path,
        {"data": _sha(b"must not be opened")},
        {"data": "../outside-source.bin"},
    )

    assert not called
    assert receipt["denominator"]["failed"] == 1
    assert receipt["entries"]["data"]["observed_sha256"] is None
    assert receipt["entries"]["data"]["reason"] == "path_must_remain_relative_to_root"


def test_symlink_escape_is_failed_before_reading_target(tmp_path, monkeypatch):
    outside = tmp_path.parent / "outside-link-target.bin"
    outside.write_bytes(b"must not be opened")
    link = tmp_path / "external.bin"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")
    called = False

    def forbidden_hash(path):
        nonlocal called
        called = True
        raise AssertionError(f"unexpected hash read: {path}")

    monkeypatch.setattr("core.source_integrity._sha256_file", forbidden_hash)
    receipt = verify_source_bytes(
        tmp_path,
        {"data": _sha(b"must not be opened")},
        {"data": "external.bin"},
    )

    assert not called
    assert receipt["denominator"]["failed"] == 1
    assert receipt["entries"]["data"]["reason"] == "resolved_source_escapes_root"


def test_unexpected_map_key_and_invalid_digest_fail_before_any_read(tmp_path, monkeypatch):
    called = False

    def forbidden_hash(path):
        nonlocal called
        called = True
        raise AssertionError(f"unexpected hash read: {path}")

    monkeypatch.setattr("core.source_integrity._sha256_file", forbidden_hash)
    with pytest.raises(ValueError, match="unexpected source names"):
        verify_source_bytes(
            tmp_path,
            {"expected": _sha(b"bytes")},
            {"unexpected": "outside.bin"},
        )
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        verify_source_bytes(tmp_path, {"data": "bad"}, {})
    assert not called
