# Run review: output serialization failed

This directory contains only the preregistration. The runner completed the 100 seed loops in memory, then failed before writing raw results because it looked for `protocol.json` while the prepared file was named `preregistration.json`.

- The terminal error was `FileNotFoundError` at the protocol-hash step.
- No `raw.json`, paired estimates, tables or figures were written. The in-memory outcomes are not treated as evidence and are not pooled.
- The execution metadata is marked `FAILED_OUTPUT_SERIALIZATION`.
- Recovery uses a corrected file path, a new protocol version, and new seeds 1100–1199 in the separate v2 directory.
