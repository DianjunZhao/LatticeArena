# Pion matched-smearing contract: CPU preflight

**Status:** CPU contract and protocol preflight passed; no measurement was run. This report checks the parameter contract that must hold before a new source/sink generation can start, verifies that the entry uses the explicit multisource protocol path, and checks that no existing output can be reused. It does not repair or relabel the archived `s16t16_ms` correlators.

## What was checked

The current local PyQUDA wrapper computes the source parameter as

```text
alpha_source = 1 / (4 * steps / rho^2 - 6)
```

and passes that alpha to `wuppertalSmear`. The measurement entry now applies the same low-level Wuppertal callable to each of the 12 source-propagator spin/color columns, using the same `protocol.alpha` passed to sink smearing and the planned source step count. The rho-to-alpha mapping is retained as a CPU compatibility check; the actual source path now passes the matched alpha explicitly. A fake-callable test verifies all 12 calls use identical `steps` and `alpha`. This closes the code-path parameter mismatch, but does not numerically validate the QUDA kernel.

| Source | Steps | Archived rho | Implied source alpha | Sink alpha | rho for alpha=0.2 |
|---|---:|---:|---:|---:|---:|
| point | 0 | 0 | not applied | 0.2 | not applicable |
| H4 | 4 | 1.4291792020 | 0.5454545455 | 0.2 | 1.2060453783 |
| H16 | 16 | 2.8583584040 | 0.5454545455 | 0.2 | 2.4120907566 |

The legacy H4/H16 source parameters do not match the sink alpha. The old protocol is rejected with a diagnostic naming both mismatches. The rho values in the last column are algebraic conversions under the currently audited wrapper formula; they are candidate parameters for a future reviewed protocol, not a measurement or a claim about the historical remote software version.

## CPU fail-closed path

```text
read protocol
  -> use explicit multisource protocol (default protocol_multisource.json; optional --protocol PATH)
  -> calculate source alpha from each (rho, steps)
  -> compare with sink alpha
  -> mismatch: stop before CuPy/MPI/PyQUDA imports, output creation, or QUDA init
  -> match: reject any existing output path before GPU imports
  -> --preflight-only: print IDs, hashes, generation, and alpha table; stop without GPU imports or output creation
  -> new path: create it with exclusive mkdir
  -> smear all 12 source columns with the sink's low-level callable and protocol.alpha
  -> record the checked table and generation identity in provenance
```

The check allows point sources because they apply no smearing. It rejects malformed/nonfinite values, duplicate source labels, non-positive mapped alpha, and any non-point source whose alpha differs from the sink beyond `1e-12` relative/absolute tolerance. The entry now defaults explicitly to `protocol_multisource.json`; it no longer inherits the unrelated single-source `protocol.json` through `common.PROTOCOL_PATH`. A caller may pass a versioned protocol using `--protocol PATH`. `--preflight-only` validates the split, hashes, source/sink alpha table, generation ID, and fresh output path, then exits before GPU imports and output creation. A real measurement still performs exclusive `mkdir` after imports to close the preflight/create race.

## Verification

Command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest -q -p no:cacheprovider --basetemp=.codex-task-tmp-pion-smearing tests/test_pion_smearing_contract.py
```

The versioned CPU candidate [`protocol_multisource_matched_v2.json`](../../tasks/pion_projection/protocol_multisource_matched_v2.json) maps H4/H16 to `rho=1.2060453783/2.4120907566`, while the actual source path passes `alpha=0.2` directly. CLI preflight on development IDs 0–1 returned `cpu_preflight_ready_not_authorized`, generation `d90414a9…`, and did not create the requested output directory.

The focused smearing suite passes **19 tests**. Tests cover raw protocol-byte hashing, correct multisource default-path selection, explicit versioned protocol hashing/preflight, alpha/rho round trips, all 12 source columns receiving identical steps/alpha through a fake Wuppertal callable, generation binding, rejection before GPU imports/output creation, and preservation of an existing output directory. The fake callable proves argument flow only; it does not test QUDA numerics. The two Hermiticity modules pass **14 tests**; combined command: `PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest -q -p no:cacheprovider tests/test_pion_smearing_contract.py tests/test_pion_source_sink_hermiticity_diagnostic.py tests/test_pion_source_sink_hermiticity_uncertainty.py` → **33 passed**.

| Artifact | SHA-256 |
|---|---|
| `tasks/pion_projection/smearing_contract.py` | `fc165c210279b36f3a178689e0e3665780137f3192aa1ba9bce8e513fc06d739` |
| `tasks/pion_projection/measure_multisource.py` | `3fa4402a498ad4139bbc82ea16f5d5bcd170e37970ce36b6f04826f2cdcaae78` |
| `tests/test_pion_smearing_contract.py` | `9589268fe63c70f9dc5e7b208e3582f6cd21cffe6ce813a47f8eaed69062eadc` |
| `tasks/pion_projection/protocol_multisource.json` (read-only input) | `2e514d0e2334238e93ce879824bb5ccd9d647048f8fa03d3fd7baf06f3385110` |
| `tasks/pion_projection/protocol_multisource_matched_v2.json` (CPU-only candidate) | `f9e77108c0ae589c73f3cf4f1bc38573784d602b7a8ca95e2c2dbe245fd11510` |

## Scope and next gate

This validates the local wrapper formula and script preflight only. It does not show which PyQUDA source bytes produced the archived remote data, prove that alpha mismatch is the unique cause of the observed non-Hermiticity, test the QUDA kernel numerically, establish a physical reference, or authorize a GPU job. The new generation binds the local protocol/measurement/contract bytes; runtime PyQUDA/QUDA/device metadata and their hashes still must be captured and reviewed in an authorized GPU receipt. Historical files and outputs were left unchanged.

Next work: make one bounded read-only check for the exact historical remote PyQUDA version/source hash. If unavailable, record that the historical cause remains unproven and do not repeat local recovery searches. The new v2 candidate and explicit `--protocol`/`--preflight-only` path are ready for researcher review; review its source/sink alpha table, development split, input/code identity, stop rules, and distinct output path. This CPU preflight does not authorize a GPU job. Only after the reference/measurement plan is reviewed and the GPU run is authorized should development IDs be measured. Its report must include per-configuration and contiguous-block anti-Hermitian distributions with intervals, a source/sink alpha table, the 5% pass/fail counts, and a plot or text explanation. Do not read E anchor, new D validation, or the shared holdout. Even a successful smearing-identity gate will not by itself pass the existing reference gate or permit a physical score.
