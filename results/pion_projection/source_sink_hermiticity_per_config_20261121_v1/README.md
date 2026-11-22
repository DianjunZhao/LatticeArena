# Per-configuration source–sink Hermiticity diagnostic

This CPU-only report reanalyzes already-observed `s16t16_ms` IDs 0–59 and 70–99. It reads no new measurement, sealed split, or raw gauge data; it does not alter the archived arrays or assign a physical score.

## Definitions and evidence

For each configuration and Euclidean time, the descriptive ratio is `max|C-C†| / max|C|` after selecting sink powers H0/H4/H16 and arranging rows=sink, columns=source. The pre-existing 5% criterion applies to the ensemble-mean matrix. Per-configuration ratios are shown to expose spread and are **not** treated as separate pass/fail gate decisions.

The uncertainty figure resamples contiguous, non-overlapping blocks in saved-configuration order at lengths 1, 2, 5, and 10, with 5,000 bootstrap draws per cell. Length 10 leaves only 3 blocks in the already-observed validation split; those intervals are intentionally shown as low-resolution. This is an exploratory uncertainty/sensitivity description, not a calibrated physical coverage statement.

| Split | t | Ensemble mean | Per-config median [16%,84%] | Per-config min–max | L=5 block-bootstrap 95% interval | L=5 valid/invalid draws |
|---|---:|---:|---:|---:|---:|---:|
| legacy_development | 3 | 0.2938 | 0.2947 [0.2720,0.3141] | 0.2394–0.3358 | [0.2888,0.2979] | 5000/0 |
| legacy_development | 4 | 0.3015 | 0.3068 [0.2712,0.3283] | 0.2344–0.3483 | [0.2945,0.3077] | 5000/0 |
| legacy_development | 5 | 0.3030 | 0.3029 [0.2646,0.3321] | 0.2284–0.3720 | [0.2949,0.3107] | 5000/0 |
| legacy_development | 6 | 0.3036 | 0.3068 [0.2572,0.3316] | 0.2277–0.3699 | [0.2938,0.3130] | 5000/0 |
| observed_validation | 3 | 0.2989 | 0.2946 [0.2761,0.3202] | 0.2463–0.3675 | [0.2879,0.3092] | 5000/0 |
| observed_validation | 4 | 0.3088 | 0.3072 [0.2771,0.3373] | 0.2497–0.3839 | [0.2941,0.3217] | 5000/0 |
| observed_validation | 5 | 0.3158 | 0.3128 [0.2787,0.3446] | 0.2396–0.4100 | [0.2972,0.3325] | 5000/0 |
| observed_validation | 6 | 0.3164 | 0.3154 [0.2804,0.3479] | 0.2398–0.4119 | [0.2968,0.3341] | 5000/0 |

![Per-configuration ratios](per_configuration_distribution.png)

![Block-bootstrap interval sensitivity](block_bootstrap_interval_sensitivity.png)

## Interpretation and limits

The per-configuration ratios are tightly clustered around roughly 0.3 across both observed splits and all four times; the displayed 16–84% ranges are far above 0.05. This indicates that the ensemble-mean failure is not produced only by averaging a few large outliers in these saved configurations. The block-bootstrap intervals describe uncertainty in the same ensemble-mean matrix metric under the stated saved-configuration block resampling; they do not validate the physical gate or identify a unique cause.

The validation IDs 70–99 were already read and are not blind. Non-overlapping saved-configuration blocks are a sensitivity convention here; the source receipt does not bind these block boundaries to trajectory spacing. The source/sink alpha mismatch remains a plausible mechanism, but this diagnostic cannot establish historical remote software identity or causal attribution. A new matched-kernel measurement is still required to test that mechanism.

Input NPZ/provenance hashes are recorded in `summary.json`. Raw per-configuration ratios are in `per_configuration.csv`; bootstrap summaries are in `block_bootstrap.csv`.

## Reproduction

Run `PYTHONDONTWRITEBYTECODE=1 python3 -B -m tasks.pion_projection.source_sink_hermiticity_uncertainty` from the repository root. The command creates a new output directory and refuses to overwrite an existing one.
