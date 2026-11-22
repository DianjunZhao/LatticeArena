# Provenance note

The `prepared_utc` field in `preregistration.json` is a fixed calendar-date placeholder (`2026-11-20T00:00:00Z`), not a wall-clock preparation timestamp. It was not used in the protocol hash, random seeds, simulation, or output hashes. Treat the source/protocol/output hashes and the recorded results as the reproducibility evidence; do not cite this field as the actual execution time. Future runs should record the runtime timestamp dynamically.
