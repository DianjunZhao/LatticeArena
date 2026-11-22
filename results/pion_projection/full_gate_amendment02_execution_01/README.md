# Candidate full-certificate MC execution

Status: COMPLETE; this executor target is 2814/2814 worlds.

All rows refer to immutable adapter receipts. Dataset roots with incomplete earlier attempts are preserved; retries use a new attempt directory. Raw inputs, seed, rejection phase and source hashes remain with each dataset. `candidate_rates_progress.png` shows marginal CP95 rate intervals; precision status only means the interval half-width target is met, not that a physical threshold passed. Failure is a subset of abstention. Synthetic certificates keep `physical_score=null`; no physical anchor, GPU run or publication-level physical conclusion follows.

`COMPLETE` means the full 2814-world execution finished. The post-run audit found one stale `synthetic_adapter.py` hash in the high-level preregistration; the actual receipts match the separately frozen executor spec. See [detailed analysis and receipt checks](ANALYSIS.md), [source-hash disposition](RUN_REVIEW.md), and the [readable post-run rate plot](candidate_rates_diagnostic.png).
