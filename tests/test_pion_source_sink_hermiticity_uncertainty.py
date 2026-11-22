import numpy as np
import pytest

from tasks.pion_projection.source_sink_hermiticity_uncertainty import (
    block_bootstrap_metrics,
    per_configuration_metrics,
    run,
    source_sink_matrices,
)


def test_source_sink_matrices_selects_powers_and_transposes_source_sink_axes():
    correlators = np.zeros((2, 3, 4, 8), dtype=np.complex128)
    powers = [0, 2, 4, 16]
    for cfg in range(2):
        for source in range(3):
            correlators[cfg, source, 0, 5] = 10 * source + 0
            correlators[cfg, source, 2, 5] = 10 * source + 2
            correlators[cfg, source, 3, 5] = 10 * source + 3

    matrices = source_sink_matrices(correlators, powers)

    assert matrices.shape == (2, 3, 3, 8)
    assert matrices[0, 2, 1, 5] == correlators[0, 1, 3, 5]
    assert matrices[1, 0, 2, 5] == correlators[1, 2, 0, 5]


def test_per_configuration_metric_keeps_configuration_axis():
    matrices = np.repeat(np.eye(3, dtype=np.complex128)[None, :, :, None], 4, axis=0)
    metrics = per_configuration_metrics(matrices, times=(0,))
    assert metrics[0].shape == (4,)
    assert np.array_equal(metrics[0], np.zeros(4))


def test_block_bootstrap_returns_finite_draws_for_fixed_hermitian_blocks():
    matrices = np.repeat(np.eye(3, dtype=np.complex128)[None, :, :], 12, axis=0)
    draws, invalid = block_bootstrap_metrics(matrices, block_length=3, n_bootstrap=50, seed=4)
    assert draws.shape == (50,)
    assert np.array_equal(draws, np.zeros(50))
    assert invalid == 0


@pytest.mark.parametrize(
    "matrices,block_length,n_bootstrap",
    [
        (np.ones((10, 2, 2)), 3, 10),
        (np.ones((4, 2, 3)), 2, 10),
        (np.ones((4, 2, 2)), 2, 1),
        (np.ones((2, 2, 2)), 2, 10),
    ],
)
def test_block_bootstrap_rejects_incompatible_shapes_or_too_few_blocks(matrices, block_length, n_bootstrap):
    with pytest.raises(ValueError):
        block_bootstrap_metrics(matrices, block_length, n_bootstrap, seed=1)


def test_source_sink_matrix_rejects_missing_power_and_nonfinite_correlators():
    with pytest.raises(ValueError, match="required sink powers"):
        source_sink_matrices(np.ones((2, 3, 2, 8)), powers=[0, 4])
    nonfinite = np.full((2, 3, 3, 8), np.nan)
    with pytest.raises(ValueError, match="finite"):
        source_sink_matrices(nonfinite, powers=[0, 4, 16])


def test_run_refuses_existing_output_before_loading_archives(tmp_path, monkeypatch):
    output = tmp_path / "existing"
    output.mkdir()
    sentinel = output / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")

    def unexpected_load(*args, **kwargs):
        raise AssertionError("existing output must be rejected before archive reads")

    monkeypatch.setattr("tasks.pion_projection.source_sink_hermiticity_uncertainty.load_split", unexpected_load)
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        run(output)
    assert sentinel.read_text(encoding="utf-8") == "keep"
