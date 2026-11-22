# Kunshan archived HMC and pion-pilot receipt audit

This read-only audit joins the archived HMC log, two manifests, and archived GPU pipeline logs. It does not regenerate measurements or infer missing HMC trajectory records.

## Directly observed

- `pipe_127946355.log` has 60 per-configuration rows for development IDs 0–59; `pipe_127946906.log` has 30 rows for validation IDs 70–99. IDs 60–69 are the declared unused gap.
- All 90/90 logged `gauge_sha256` values match the same-ID `sha256` entries in `results/kunshan_logs/manifest.json`. The maximum recorded residual is 9.992e-11; 0 rows exceed 1e-10. Median solve-plus-residual time is 0.851 s and median total configuration time is 2.717 s. These are archived run values, not a current-hardware benchmark.
- All 90/90 rows also match the repository's `s16t16_v1` development/validation provenance records field by field. The optimize_gaussian v9 manifest points to the same validation provenance and lists the same 30 test IDs (70–99), so that set is already observed and cannot be treated as a fresh blind test.
- The log headers record QUDA/HIP device information; details and input hashes are in `summary.json`.
- The validation JSON reports `score_status=unscored_reference_failed` and `reference_passed=false`: nominal mass 1.08617 (SE 0.00307), $\chi^2/\mathrm{dof}=52.00/8$, approximate $p=1.7e-08$. The two alternative reference windows shift by 21.62σ and 7.82σ. The reported improvement factor is `R_tuned_gaussian/R_agent=1.630` with 95% interval [1.396310154172884, 2.190467036489882]; this remains an unscored diagnostic because the reference gate failed.
- The 100 saved rows in `hmc_production.log` match both manifests by ID, trajectory, and plaquette within 1e-7. The HMC log has no per-configuration gauge hash, so that crosswalk is metadata-only.

## Identity conflict

The 100-entry `results/kunshan_logs/manifest.json` and the first 100 rows of the 200-entry `hmc_quality_v1/manifest_snapshot.json` match on ID, trajectory, and plaquette, but their hash fields match **0/100** rows. The pipeline logs match the primary Kunshan manifest for all 90 measured IDs, and match **0/90** snapshot hashes. This could reflect different hash inputs or a stale/incorrect snapshot; the archived files do not establish which explanation is correct. No local gauge bytes are available to recompute either hash.

![Residual and timing diagnostics](archive_receipt_diagnostic.png)

## Status boundary

This closes an archive-discovery gap: real historical GPU measurement receipts exist for the pion pilot, and they can be cross-linked to the primary 100-configuration manifest at the hash-field level. It does not authenticate the HMC log's gauge bytes, resolve the conflicting snapshot hashes, make the failed reference score valid, reproduce the optimize-gaussian v9 training result or confirm that its $W$ was trained, or satisfy Wilson protocol_v4 / S16T16B production gates.

The source logs and manifests are unchanged. To verify frozen inputs/outputs run:

```bash
python3 -B -m tasks.kunshan_archive_audit --verify
```
