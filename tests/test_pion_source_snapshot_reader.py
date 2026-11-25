from __future__ import annotations

from hashlib import sha256
from io import BytesIO

import numpy as np
import pytest

from core.source_integrity import capture_source_snapshot
from tasks.pion_projection.common import fingerprint, load_data


def test_load_data_parses_the_captured_npz_bytes_after_path_changes(tmp_path):
    protocol = {
        "development": [2, 3],
        "powers": [0, 2],
        "geometry": [4, 4, 4, 4],
    }
    expected = np.arange(16, dtype=np.float64).reshape(2, 2, 4)
    payload_stream = BytesIO()
    np.savez_compressed(
        payload_stream,
        ids=np.asarray([2, 3]),
        protocol_hash=np.asarray(fingerprint(protocol)),
        correlators=expected,
    )
    payload = payload_stream.getvalue()
    (tmp_path / "development.npz").write_bytes(payload)
    snapshot = capture_source_snapshot(
        tmp_path,
        {"development_measurements": sha256(payload).hexdigest()},
        {"development_measurements": "development.npz"},
    )

    (tmp_path / "development.npz").write_bytes(b"changed after snapshot capture")
    observed = load_data(
        tmp_path,
        "development",
        protocol,
        source_snapshot=snapshot,
        source_name="development_measurements",
    )

    np.testing.assert_array_equal(observed, expected)


def test_load_data_requires_a_named_snapshot_source(tmp_path):
    snapshot = capture_source_snapshot(tmp_path, {"dev": sha256(b"x").hexdigest()}, {})
    with pytest.raises(ValueError, match="source_name is required"):
        load_data(tmp_path, "development", {}, source_snapshot=snapshot)

