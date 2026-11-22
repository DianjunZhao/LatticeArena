# Kunshan live archive: raw gauge byte and HMC log audit

This read-only audit connected to the configured `kunshan` SSH alias. It streamed SHA-256 digests for 500 remote NERSC files and the SHA-256 of the link payload after `END_HEADER`. It archived small manifests and logs locally, but copied no gauge bytes, wrote nothing remotely, and submitted no Slurm jobs. The `build` command needs the same SSH alias and rereads the remote files; `verify` checks only this frozen local audit.

## Direct results

- `data/S16T16`: 100/100 actual raw-file hashes match the remote manifest; its remote manifest is byte-identical to the local `results/kunshan_logs/manifest.json`.
- `data/S16T16B`: 200/200 actual raw-file hashes match its remote manifest. Its 200 SAVED log paths and the manifest IDs, trajectories and plaquettes cross-check row by row.
- `data/S16T16C`: 200/200 actual raw-file hashes match the remote manifest; that manifest is byte-identical to the local Wilson `manifest_snapshot.json`.
- Raw full-file SHA differs between campaigns because NERSC headers record different creator hardware and creation/archive timestamps. The exact bytes after the `END_HEADER` line are identical for S16T16 vs B: 100/100 IDs; B vs C: 200/200 IDs; S16T16 vs C: 100/100 IDs. Thus these directories contain duplicate gauge payload bytes over their overlapping IDs; do not count them as independent configurations.
- Pion `s16t16_v1` gauge hashes match the actual S16T16 raw files for 90/90 archived measurement rows. Pion GEVP200 hashes match actual S16T16C raw files for 180/180 rows. GEVP200 IDs 0–99 therefore refer to the same link payloads as S16T16/S16T16B where present; its IDs 100–119 and 140–199 are additional points on the same replayed HMC chain, not a separately seeded chain.
- The local HMC production log, B log `hmc200_128345242.out`, and C log `hmc200c_128360922.out` have matching SAVED path/ID/trajectory/plaquette metadata for 100/100, 200/200, and 200/200 rows respectively. The actual file digests were compared against each manifest; match counts are 100, 200, and 200 respectively.
- The B/C batch scripts and `pilot/hmc_generate.py` are byte-identical to the archived local files:
- `pilot/hmc_generate.py` remote/local source bytes identical: True.
- `pilot/hmc200.sbatch` remote/local source bytes identical: True.
- `pilot/hmc200c.sbatch` remote/local source bytes identical: True.
- B/C sparse checkpoint comparison: 70 shared logged trajectories; all compared physics fields match on all shared checkpoints = True; runtime seconds match on 18/70. The B batch/source settings resolve seed 20261109 (generator default; not explicit in batch command). This is direct evidence about saved payloads and logged checkpoints, not every unlogged trajectory.

## S16T16B HMC limits

The B log records 70 sparse trajectory checkpoints, each with one accept flag, $\Delta H$ and a rounded cumulative acceptance fraction. It records 200 saved configurations through trajectory 1396; batch/source settings predict stop trajectory 1396 when `max_save=200` is reached. The `DONE` fraction is 0.977 using the planned denominator. Under the matching generator's `accepted / args.trajectories` formatting, the possible accepted-count set is `[1368]`; conditional on that source and the early-stop schedule, the aggregate actual-run fraction is 0.979943.

This does not reconstruct unlogged per-trajectory accept/reject decisions or $\Delta H$. The plaquette series and lag-window estimates in `hmc_b_plaquette_tau_sensitivity.csv` are exploratory for only 200 saved configurations; no thermalization/autocorrelation rule was frozen in the HMC manifest. Therefore Wilson F4 is **PARTIAL**, not complete. It still needs a protocol-matched receipt with every trajectory's $\Delta H$ and acceptance decision, a declared thermalization cut, and a justified autocorrelation/block rule. The remote B data exist, but the observed B/C duplicate chain must not be counted twice.

## Reproducible artifacts

- `manifest_byte_crosswalk.csv`: all 500 file hashes, manifest digest checks, and payload digests.
- `campaign_payload_crosswalk.csv`: per-ID full-file and gauge-payload equality across campaigns.
- `pion_raw_identity_crosswalk.csv`: stored Pion source hashes against actual remote gauge bytes.
- `hmc_saved_crosswalk.csv`: SAVED paths and metadata against manifests plus verified file hashes.
- `hmc_b_checkpoints.csv`: raw sparse B log checkpoints; no unobserved trajectory decision is imputed.
- `hmc_b_c_checkpoint_comparison.csv`: per-shared-checkpoint B/C comparison of logged acceptance flag, $\Delta H$, plaquette, cumulative rate and runtime.
- `identity_and_duplicate_payloads.png` and `hmc_b_sparse_diagnostics.png`: visual crosswalk and HMC diagnostics.
- `remote_hmc200_128360803.err` records a separate cancelled attempt; it is retained and excluded from the successful B run.

Audit command: `python3 -B -m tasks.kunshan_live_archive_audit build`; script SHA-256: `e8dc94ae029049a86ba9ff81c71213f4b2ac6d526909b6aa93795e0b7ef6b883`.

Frozen artifact verification: `python3 -B -m tasks.kunshan_live_archive_audit verify`.
