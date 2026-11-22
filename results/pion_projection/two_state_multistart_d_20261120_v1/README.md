# Two-state multistart search diagnostic on D development

**Status: development-only numerical diagnostic; the frozen single-cosh reference gate remains failed.** This result does not authorize an E measurement, validation access, shared-holdout access, or physical score.

The same pinned D0–99 samples and fixed covariance objective are evaluated from a deterministic grid of SLSQP starting points, plus the existing coordinate-search endpoint. At each objective call, amplitudes are profiled with whitened least squares. The scan includes the `gap=0` one-state boundary and records optimizer status, iterations, evaluations, active bounds, finite endpoints, and approximate endpoint clusters for every start.

![D-only multistart trajectories and objective differences](two_state_multistart.png)

| Window | Starts | SLSQP success | Non-success terminal status | Finite endpoints | Approx. endpoint clusters | Boundary endpoints | gap=0 endpoints | Best gap | Legacy gap | Legacy minus best $C^2$ |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| [4, 5, 6, 7, 8] | 29 | 24/29 | 5 × status=4: Inequality constraints incompatible | 29/29 | 6 | 5 | 5 | 0.68376 | 0.663 | 0.074955 |
| [5, 6, 7, 8] | 29 | 24/29 | 5 × status=4: Inequality constraints incompatible | 29/29 | 7 | 6 | 6 | 0.62887 | 0.556 | 0.082121 |
| [6, 7, 8] | 29 | 24/29 | 5 × status=4: Inequality constraints incompatible | 29/29 | 8 | 6 | 6 | 0.92645 | 0.781 | 0.015049 |

## Non-success termination details

- Window [4, 5, 6, 7, 8]: 5 × status=4: Inequality constraints incompatible; 5 non-success endpoints are at `gap=0`, and 5 of them started there. At `gap=0`, the two design columns coincide and the amplitudes lose rank; this association is a numerical degeneracy warning, not proof that it is the only cause of the SLSQP status.
- Window [5, 6, 7, 8]: 5 × status=4: Inequality constraints incompatible; 5 non-success endpoints are at `gap=0`, and 5 of them started there. At `gap=0`, the two design columns coincide and the amplitudes lose rank; this association is a numerical degeneracy warning, not proof that it is the only cause of the SLSQP status.
- Window [6, 7, 8]: 5 × status=4: Inequality constraints incompatible; 5 non-success endpoints are at `gap=0`, and 4 of them started there. At `gap=0`, the two design columns coincide and the amplitudes lose rank; this association is a numerical degeneracy warning, not proof that it is the only cause of the SLSQP status.

## Interpretation boundary

- This compares deterministic local-search starts on the same D sample; it is not an independent validation or uncertainty estimate.
- A lower endpoint objective shows sensitivity to initialization under this optimizer and objective. It does not show that the returned point is the global minimum.
- Endpoint clusters use a descriptive greedy tolerance of 0.02 in both mass0 and gap. The cluster count is not a formal count of mathematical basins.
- `gap=0` makes the two design columns identical. The SVD least-squares objective remains finite there, while the amplitudes are non-identifiable; boundary endpoints must therefore be read together with rank and condition fields.
- Solver `success` is only the SLSQP termination flag. No solver result here reopens the frozen reference gate, changes the candidate score, or licenses reading E, validation, or holdout data.
- The result can inform a new pre-E proposal. Any confirmation model, time window, covariance, adequacy threshold, and failure/abstention rule still need independent review and must be frozen before E is measured.
