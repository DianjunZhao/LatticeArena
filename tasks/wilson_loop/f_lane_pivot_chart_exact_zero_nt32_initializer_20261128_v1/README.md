# Aborted matched-Nt=32 initializer screen report

This is a preserved execution record, **not a numerical result report**. The process completed all 18 per-radius `Nt=32` initializer fits and returned status rows for all 54 planned chart fits. It then failed while serializing `fit_results.csv`: rows with `optimizer_success` had a different field set from out-of-bounds abstention rows.

The `execution_progress.jsonl` file therefore records only fit status, method, panel and start index; it does not preserve fitted parameters, objectives, forces or Jacobian diagnostics. The partial chart CSV was renamed `fit_results.csv.partial` and must not be used as the complete result table. Although the source-capture and initializer CSVs were written, this run has no final summary, plot or artifact hash manifest, and none of its fit statuses is counted in the method comparison.

The corrected no-clobber rerun is recorded in [`../f_lane_pivot_chart_exact_zero_nt32_initializer_20261128_v2/`](../f_lane_pivot_chart_exact_zero_nt32_initializer_20261128_v2/). That version accepts heterogeneous outcome rows and checkpoints the full tables after each panel.
