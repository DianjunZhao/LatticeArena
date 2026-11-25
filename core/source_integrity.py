"""Verify explicitly declared source-file bytes against SHA-256 expectations.

This proves only that the bytes read from the supplied paths match the supplied
digests. It does not establish who produced the files, whether the hashes came
from a trusted authority, whether samples are independent, or whether the
scientific claims are valid.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any


SOURCE_VERIFICATION_SCHEMA = "latticearena-source-byte-verification-v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _validate_expected_hashes(expected_hashes: object) -> dict[str, str]:
    if not isinstance(expected_hashes, dict) or not expected_hashes:
        raise ValueError("expected_hashes must be a nonempty mapping")
    normalized: dict[str, str] = {}
    for name, digest in expected_hashes.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("source names must be nonempty strings")
        if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
            raise ValueError(f"expected_hashes[{name!r}] must be a lowercase SHA-256 hash")
        normalized[name] = digest
    return normalized


def _safe_relative_path(value: object) -> tuple[Path | None, str | None]:
    if not isinstance(value, str) or not value.strip():
        return None, "source_path_missing_or_invalid"
    if "\\" in value:
        return None, "backslash_path_not_allowed"
    if "\x00" in value:
        return None, "nul_byte_in_path"
    relative = Path(value)
    if relative.is_absolute() or any(part == ".." for part in relative.parts):
        return None, "path_must_remain_relative_to_root"
    if not relative.parts or value.strip() in (".", "./"):
        return None, "path_must_name_a_file"
    return relative, None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_source_bytes(
    root: str | Path,
    expected_hashes: dict[str, str],
    source_paths: dict[str, str],
) -> dict[str, Any]:
    """Hash only the explicitly mapped files contained under ``root``.

    Each expected hash is one planned source. Missing mappings/files are
    abstentions; malformed paths, read errors and hash mismatches are failures.
    Unexpected mapping keys raise before any source file is opened so an
    unregistered path can never trigger an implicit read.
    """
    expected = _validate_expected_hashes(expected_hashes)
    if not isinstance(source_paths, dict):
        raise ValueError("source_paths must be a mapping of expected names to relative paths")
    unexpected = set(source_paths) - set(expected)
    if unexpected:
        names = ", ".join(sorted(str(item) for item in unexpected))
        raise ValueError(f"source_paths contains unexpected source names: {names}")

    root_path = Path(root)
    try:
        root_path = root_path.resolve(strict=True)
    except (OSError, ValueError) as exc:
        raise ValueError("root must name an existing directory") from exc
    if not root_path.is_dir():
        raise ValueError("root must name an existing directory")

    entries: dict[str, dict[str, Any]] = {}
    valid = failed = abstained = 0
    for name, expected_digest in expected.items():
        raw_path = source_paths.get(name)
        relative, path_error = _safe_relative_path(raw_path)
        if path_error is not None:
            status = "abstained" if raw_path is None else "failed"
            if status == "abstained":
                abstained += 1
            else:
                failed += 1
            entries[name] = {
                "status": status,
                "path": raw_path if isinstance(raw_path, str) else None,
                "expected_sha256": expected_digest,
                "observed_sha256": None,
                "reason": path_error,
            }
            continue

        candidate = root_path / relative
        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError:
            abstained += 1
            entries[name] = {
                "status": "abstained",
                "path": raw_path,
                "expected_sha256": expected_digest,
                "observed_sha256": None,
                "reason": "source_file_not_found",
            }
            continue
        except (OSError, ValueError) as exc:
            failed += 1
            entries[name] = {
                "status": "failed",
                "path": raw_path,
                "expected_sha256": expected_digest,
                "observed_sha256": None,
                "reason": f"source_path_resolution_failed:{type(exc).__name__}",
            }
            continue

        if root_path not in resolved.parents:
            failed += 1
            entries[name] = {
                "status": "failed",
                "path": raw_path,
                "expected_sha256": expected_digest,
                "observed_sha256": None,
                "reason": "resolved_source_escapes_root",
            }
            continue
        if not resolved.is_file():
            failed += 1
            entries[name] = {
                "status": "failed",
                "path": raw_path,
                "expected_sha256": expected_digest,
                "observed_sha256": None,
                "reason": "source_is_not_a_regular_file",
            }
            continue

        try:
            observed_digest = _sha256_file(resolved)
        except OSError as exc:
            failed += 1
            entries[name] = {
                "status": "failed",
                "path": raw_path,
                "expected_sha256": expected_digest,
                "observed_sha256": None,
                "reason": f"source_read_failed:{type(exc).__name__}",
            }
            continue

        if observed_digest == expected_digest:
            valid += 1
            entries[name] = {
                "status": "valid",
                "path": raw_path,
                "expected_sha256": expected_digest,
                "observed_sha256": observed_digest,
                "reason": None,
            }
        else:
            failed += 1
            entries[name] = {
                "status": "failed",
                "path": raw_path,
                "expected_sha256": expected_digest,
                "observed_sha256": observed_digest,
                "reason": "sha256_mismatch",
            }

    planned = len(expected)
    return {
        "schema": SOURCE_VERIFICATION_SCHEMA,
        "status": "verified" if valid == planned else "incomplete",
        "denominator": {
            "unit": "source_file",
            "planned": planned,
            "valid": valid,
            "failed": failed,
            "abstained": abstained,
            "not_run": 0,
        },
        "entries": entries,
    }
