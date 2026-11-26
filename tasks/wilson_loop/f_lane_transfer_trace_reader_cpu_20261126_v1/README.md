# Wilson F-lane finite-`N_t` transfer-trace reader: synthetic CPU diagnostic

**Status:** candidate software path only. This report uses a synthetic fit
summary, does not read raw Wilson correlators, and does not certify the proposed
finite-`N_t` interpretation or the ground-state force.

## Data flow and definition

```mermaid
flowchart LR
  S[One captured byte snapshot] --> V[Manifest, split, hashes, axes]
  V --> C[Captured lane-contract semantics]
  C --> F[Caller-supplied fitted energies and overlaps]
  F --> Q[Compute q, h, x for R/kernel/T/Nt]
  Q --> R[Check full trace against 1+q+h+x]
  R --> D[Diagnostic only; physical_score is null]
  D -. missing .-> U[Raw C_ij parser and covariance-aware joint fit]
  U -. missing .-> B[Coverage, thermal/mixed receipts, force budget]
```

For each selected cell, the reader uses the proposed diagonal trace

```text
C_kk(R,T;Nt) = Z0(Nt)^-1 sum_(m,n)
               exp[-eps_m (Nt-T)] exp[-V_n(R) T] |A_k,mn(R)|^2
Z0(Nt) = sum_m exp[-eps_m Nt]
```

and normalizes by the `(m,n)=(0,0)` term. It partitions the remaining positive
terms into `q: m=0,n>0`, `h: m>0,n=0`, and `x: m>0,n>0`. The direct full-trace
ratio must agree numerically with `1+q+h+x`. This is an algebra check on the
proposed factorized endpoint convention; it does not establish that a
production Wilson-loop exporter obeys that convention.

## Synthetic fixture and denominator

`tests/test_wilson_f_lane_transfer_trace_reader.py` constructs 3 vacuum levels,
3 static levels at each of `R={2,3}`, and complex transition-overlap pairs for
the three ordered bare kernels `(identity, APE, stout)`. It uses `T={5,6}` and
`Nt={16,32}`. The fixture verifies all 24 planned `R × kernel × T × Nt` cells:

| Unit | Planned | Valid | Failed | Abstained |
|---|---:|---:|---:|---:|
| Captured source file | 3 | 3 | 0 | 0 |
| Synthetic q/h/x cell | 24 | 24 | 0 | 0 |
| Authorized production measurement | 0 | 0 | 0 | 0 |
| F-lane certification gate | 1 | 0 | 0 | 1 |

All q/h/x components are nonnegative and the maximum tested trace-decomposition
residual is below `1e-12`. The focused suite has **9 passed**. Tests reject a sealed F split, stale fit
hash, incorrect kernel-to-basis map, unordered spectrum, and malformed overlap
axes, a manifest/protocol hash mismatch, and an extra radius row. The fixture is deterministic and is generated in the test itself; no
Wilson production or sealed bytes are opened.

## What remains open

The reader accepts a supplied spectrum/overlap JSON summary. It does not parse
raw `C_ij(R,t)` data, run the proposed 2/3-state joint finite-`Nt` fit, estimate
covariance or uncertainty, calibrate coverage, bound omitted states, or make a
matched-`Nt=32` thermal / mixed-sector receipt. Independent review must first
check the production insertion-time, source/sink, boundary-trace and
normalization conventions. The force-unit error budget, production access and
authorization are separate gates. The task remains
`NOT_READY/UNCERTIFIED`, F=`GROUND_STATE_FORCE_UNCERTIFIED`, and
`physical_score=null`.
