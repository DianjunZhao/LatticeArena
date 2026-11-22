# P4 positive-control bootstrap-resolution sensitivity

This is a post-hoc computation on the same 402 independent datasets in the primary run. It changes only the number of outer ratio resamples from 100 to 1000; the saved block measurements, gate decisions, inner bootstrap count (100), effect size and gate threshold are fixed. The dataset denominator is still 402 and this run must not be counted as an additional Monte Carlo experiment.

| Calculation | Detections | Rate | CP95 |
|---|---:|---:|---:|
| Primary, 100 outer draws | 324/402 | 0.8060 | [0.7638704200438828, 0.8434961535421104] |
| Sensitivity, 1000 outer draws | 323/402 | 0.8035 | [0.7612162869422381, 0.8412132028044647] |

Changing outer-resample resolution newly detected 16 datasets and lost 17 prior detections; median shift in the per-dataset lower bound was -0.05419 (5th–95th percentile [-0.4319, 0.3343]). This isolates only Monte Carlo resolution of the bootstrap quantile. It does not increase the number of independent configurations or repair the 16-block sampling uncertainty.

![Outer-bootstrap resolution sensitivity](outer_resolution.png)

Interpret this only as a stability check of the primary 100-draw calculation. The primary result remains the preregistered endpoint; neither calculation establishes physical performance or calibration for an estimated anchor.
