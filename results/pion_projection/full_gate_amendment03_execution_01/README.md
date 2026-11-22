# Amendment03 source-aligned replay

Status: COMPLETE; 2814/2814 synthetic worlds executed with the amendment02 seed set. This is a same-seed provenance/reproducibility audit and not independent Monte Carlo evidence.

Read [analysis](ANALYSIS.md), [run review](RUN_REVIEW.md), and the [candidate-rate and replay-concordance figure](candidate_rates_diagnostic.png). The frozen [amendment03 plan](../full_gate_mc_20261119_v2_amendment_03/README.md) remains separate from these execution outputs. A concurrency-only resume is documented in [execution_amendment_01.json](execution_amendment_01.json); analysis artifact hashes are recorded in [analysis_provenance.json](analysis_provenance.json). The post-run checker is [source_aligned_replay_summary.py](../../../tasks/pion_projection/source_aligned_replay_summary.py). The original amendment02 source-chain classification remains `PARTIAL`; this new replay does not rewrite its receipts. `physical_score=null`.
