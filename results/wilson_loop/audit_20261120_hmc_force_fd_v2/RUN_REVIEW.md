# Run review: first analytic-force finite-difference pass

This first frozen run retained 5,120 finite-difference comparisons and completed the force-algebra and leapfrog checks, but ended with `FAIL_TOY_CPU_CHECKS` because its initial action-parity criterion compared two different additive zero points.

The vectorized action in `tasks/wilson_loop/hmc_quality.py` uses the constant term $\\beta(6L^3)$ on the $2^4$ toy lattice; the explicit coordinate-loop implementation uses the conventional $\\beta(6V)$. Their difference is exactly $-288$ for $\\beta=6$, $L=2$, and $V=16$. This is gauge independent, so it cancels from the force and from $\\Delta H$. The failed check did not indicate a derivative mismatch. The measured force finite-difference and leapfrog checks in this run passed, but the run remains preserved as a failed first protocol and is not used as the final diagnostic.

The corrected frozen protocol explicitly compares the action's variable part after accounting for the known offset. Its independent rerun is [audit v3](../audit_20261120_hmc_force_fd_v3/README.md), which passed all declared toy CPU checks. The v3 rerun has its own frozen protocol/source hash, raw rows, summary, figure, and provenance; no v2 data were merged into it.

The v2 protocol/source and raw artifacts remain unchanged. `execution_provenance.json` preserves the v2 source hash and listed artifact hashes.
