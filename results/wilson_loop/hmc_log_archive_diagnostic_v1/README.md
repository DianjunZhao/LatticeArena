# Archived HMC log: partial production evidence and identity limits

This is a CPU-only audit of the archived [Kunshan production log](../../kunshan_logs/hmc_production.log) and the saved [HMC manifest snapshot](../hmc_quality_v1/manifest_snapshot.json). The parser is [`hmc_log_diagnostic.py`](../../../tasks/wilson_loop/hmc_log_diagnostic.py). It reads the files and produces the CSV extracts, JSON summary, and plot without changing the source log or manifest.

## What the files directly show

The log header identifies a $16^4$, $\beta=6.0$ run with 120 integration steps, seed `20261109`, and $\tau=0.5`. Its final line reports the planned 900 trajectories, 100 saved configurations, `accept_rate=0.972`, 401.5 wall seconds, and 0.446 wall seconds per planned trajectory. The last saved configuration is at trajectory 896; the source-assisted reconstruction below shows why the printed denominator is not the number actually executed.

The log records only 45 trajectory checkpoints, at trajectories 1, 21, ..., 881. These have sparse $\Delta H$ values, not one value per trajectory. The 25 checkpoints at or after the first saved configuration (trajectory 401) have mean $\Delta H=-0.00959$ and sample SD 0.06695; this is a descriptive summary of those 25 printed values, not an estimator with an autocorrelation-aware uncertainty. The full checkpoint set is dominated by the trajectory-1 value $\Delta H=-23.043$.

The log contains 100 saved plaquettes with IDs 0–99 at trajectories 401–896, spaced by five. Their descriptive mean and sample SD are 0.593759 and 0.000500. All 100 records match the first 100 snapshot rows by ID, trajectory, and rounded plaquette. This is a metadata crosswalk only: the `SAVED` lines contain no configuration hash. The 200-entry snapshot ends at trajectory 1396; IDs 100–199 have no corresponding saved rows in this 900-trajectory log.

A separate 100-entry [Kunshan manifest](../../kunshan_logs/manifest.json) records per-configuration SHA-256 values. The archived GPU measurement logs cover development IDs 0–59 and validation IDs 70–99; their 90 `gauge_sha256` fields match the same-ID hashes in that manifest (90/90). However, the Kunshan manifest and this 200-entry snapshot disagree on every hash in IDs 0–99 (0/100), despite matching ID, trajectory, and plaquette. The HMC log itself cannot settle that conflict because it has no hash field, and local gauge bytes are absent. See the [cross-file archive receipt audit](../../kunshan_logs/archive_audit_v1/README.md) for per-configuration tables, source hashes, and the diagnostic plot.

![Sparse trajectory and saved-configuration diagnostics](hmc_log_diagnostic.png)

The top panel retains the large first-trajectory $\Delta H$; the second panel zooms to the 25 later checkpoints. The lower panels show plaquette history and the logged cumulative acceptance rate. The vertical line at 400 marks the boundary inferred from the first saved configuration. It is not a declared thermalization cut.

## What this does not establish

- The log does not expose every accept/reject decision or include a run-specific source hash. The [v2 source-assisted reconstruction](../hmc_acceptance_reconstruction_v2/README.md) uses the current generator and run note to infer a stop at trajectory 896. If the historical script used the current `DONE` denominator (`accepted / planned_trajectories`), it implies 875 accepts and 97.656% over executed trajectories; if the historical script used the actual stop as the denominator, the same rounded `0.972` token implies 871 accepts and 97.210%. The current source favors the first interpretation, but the missing run-specific source hash prevents choosing conclusively. Neither interpretation recovers the positions of unlogged rejections or justifies an independence-based interval. The earlier single-denominator calculation is retained as [v1](../hmc_acceptance_reconstruction_v1/README.md) and marked superseded in its run review.
- Sparse $\Delta H$ checkpoints do not establish the full production distribution or permit a complete histogram.
- The first save at trajectory 401 suggests a measurement boundary; it does not prove a preregistered thermalization rule. No declared cut or $\tau_{\rm int}$ analysis is present in these two artifacts.
- The log writes to `data/S16T16/...`; the snapshot labels its ensemble `LatticeArena-pilot`; `protocol_v4.json` names `S16T16B`. The existing HMC quality README also calls its snapshot S16T16C. These labels are not reconciled, so this log cannot be assigned to the task's requested S16T16B production.
- The Kunshan manifest hashes match the 90 GPU measurement records, but the snapshot hashes match 0/100 Kunshan manifest entries. The HMC log does not include hashes, and gauge configuration files are not present in this workspace, so this audit cannot decide which manifest hash set corresponds to the bytes used by HMC.

## Status and next work

This corrects the broad claim that the workspace has no production $\Delta H$ or acceptance evidence: **a partial archived run is present**. The last saved trajectory is directly logged as 896; the accepted count and denominator interpretation are source-assisted, with a 875/896 preferred reconstruction and a 871/896 sensitivity case because there is no run-specific source hash. It does not close F4 for `protocol_v4`; the task-specific receipt and physical score remain `NOT_RUN`.

Next, resolve the 0/100 manifest-hash conflict by recovering the authoritative gauge-byte hashes or documenting the exact hash input/convention; recover raw trajectory records for the manifest entries after trajectory 900. If the required evidence cannot be recovered, run the frozen `S16T16B` protocol with per-trajectory $\Delta H$, acceptance decisions, declared thermalization cut, and provenance. Keep the stout/APE matched physical comparison as a separate unfinished gate.

Verify the frozen extraction and source hashes with:

```bash
python3 -B -m tasks.wilson_loop.hmc_log_diagnostic --verify
```

The input, manifest, and generator SHA-256 values plus output hashes are in [`provenance.json`](provenance.json); the sparse trajectory and saved-configuration tables are in [`trajectory_checkpoints.csv`](trajectory_checkpoints.csv) and [`saved_configurations.csv`](saved_configurations.csv).
To generate another copy, pass a new `--output` directory; the script refuses to overwrite an existing output directory.
