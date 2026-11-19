# Executable S16T16 pion projection pilot

The scientific definition is in [the task specification](../../doc/pion_projection.md).
This directory implements a **local research pilot**, including fixed measurement,
cache verification, baseline search, a frozen agent submission, and held-out
diagnostic evaluation. It is not a secure multi-user competition service.

The first run is recorded in [the results report](../../doc/pion_projection_results.md).
The reference checks failed; the software consequently emits `score: null`.
Raw losses and uncertainty intervals are still useful diagnostics.

## Reproduce the run

From the repository root, after setting up [the environment](../../doc/environment.md):

```bash
.venv/bin/python -m pytest -q tests/test_pion_projection.py
bash scripts/run_pion.sh --output results/pion_projection/reproduction measure --split development
bash scripts/run_pion.sh --output results/pion_projection/reproduction develop
bash scripts/run_pion.sh --output results/pion_projection/reproduction measure --split validation
bash scripts/run_pion.sh --output results/pion_projection/reproduction evaluate
bash scripts/run_pion.sh --output results/pion_projection/reproduction plot
```

`--output` precedes the subcommand. Use a fresh output directory: `develop` refuses
to overwrite a frozen submission or reopen development after validation data
exist. Reproduction does not make these previously inspected configurations a
new hidden test set. `plot` uses recorded results and needs no new inversion.

Small result arrays, provenance, frozen proposals, and figures are stored under
`results/`. The approximately 6.4 GiB of point propagators for 45 configurations
live under ignored `.cache/pion_projection/propagators/`; no gauge files are copied
into the repository. Cache loading checks the gauge/software provenance, array
checksum, and, in the fixed measurement runner, all 12 explicit Dirac residuals.

## Fixed v1 protocol

`protocol.json` is the numerical source of truth and its hash accompanies data
and submissions. The protocol was fixed before the first development measurements.

| Setting | v1 value |
| --- | --- |
| Development / gap / validation IDs | 0–29 / 30–34 / 35–49 |
| Valence action | Wilson, kappa 0.14, periodic space, antiperiodic time |
| Source / residual / iteration limit | Origin, 12 spin-color columns, 1e-10, 10000 |
| Diffusion step | `H = (I + 0.2 * spatial_hopping) / 2.2` |
| Baseline kernels | `H^n`, n = 0, 2, 4, 8, 16, 32, 64 |
| Score / amplitude windows | 2–5 / 6–8, folded per configuration |
| Common reference channels | n = 0, 8, 16; separate amplitudes, common mass |
| Reference windows | 4–8, 5–8 (nominal), 6–8 |
| Covariance | 25% diagonal shrinkage, eigenvalue floor 1e-10 times largest eigenvalue |
| Mass search | Bounded scalar minimization, 0.1 < am < 3.0 |
| Blocks / bootstrap | Contiguous blocks of 5; 1000 bootstrap draws |
| Score uncertainty | 200 paired outer draws, each with 128 inner draws |
| Seeds | 20261109 development; +1 validation; +2 nested intervals |
| Amplitude gate | Absolute amplitude / bootstrap SE at least 3 |
| Reference gates | Relative mass SE <= 5%; approximate fit p >= .01; paired window shifts <= 2.5 SE; no mass-bound hits |
| Reflection gate | Maximum absolute forward/backward block-mean z <= 4 over basis channels and t = 1–7 |
| Per-configuration budget | 300 seconds, checked after completion; CuPy pool limit 10 GiB |

The covariance is computed from block means. Reference fitting fixes its metric
from development; each candidate's late-amplitude metric is also fixed from its
development data before validation. Bootstrap samples vary means, reference mass,
and fitted amplitudes using these fixed metrics. Thus the intervals are conditional
on the declared fitting metrics, not a marginalization over all covariance
estimators. Shrinkage chi-square p-values are diagnostic approximations, not exact
finite-sample probabilities. The paired mass-window check uses the uncertainty of
the *difference* on common bootstrap draws.

The five-configuration block length was conservatively fixed; SEs for lengths
1, 2, 3, and 5 are reported on development. Trajectory spacing is not known and
decorrelation has not been established. Only six development blocks and three
validation blocks remain. Nested intervals include the statistical-variance term
in each outer loss; no replica is discarded. Replicas with repeated identical
blocks remain evaluable because fit metrics are fixed. These intervals are
necessarily coarse with three validation blocks.

The reference failure is a gate on scores, not a reason to search for more
favorable windows after looking at validation. Candidate failures produce an
explicit error or invalid record; incomplete measurement checkpoints cannot be
loaded as complete splits.

### Evidence for pion ground-state dominance

The source and sink carry charged isovector flavor. The spatial kernel has
cubic irrep `A1+`, the pseudoscalar bilinear has irrep `A1−`, and the sink
sum sets spatial momentum to zero. With degenerate valence quarks, neutral-partner
`C=+` fixes `G=−` for the isotriplet. These quantum numbers allow radial and
multiparticle excitations. A signed sink can even have zero overlap with the
lowest state.

In validation the scorer releases the mass parameter for each sink and fits a
single cosh on both fixed late windows (5–8 and 6–8). It checks fit quality,
mass precision, bootstrap bounds, agreement with the development reference
and the paired mass shift between windows using the existing reference
thresholds. These fits use the covariance of the validation block means, held
fixed within their bootstrap. The earlier risk calculation still uses its
frozen development fit metric. The report records the fits and failures under
`pion_mass_check`. A failed reference or free-mass check yields `unresolved`
and a null score. Passing yields `consistent_with_reference`. Finite-window
agreement alone cannot identify a unique eigenstate. A second local sink supplies a development-only check on the same
point propagators. Recompute local `PP` and temporal axial `A4P` with:

```bash
python -m tasks.pion_projection --output results/pion_projection/s16t16_v1 check-axial --dest results/axial-reference
```

Each local PP time series must reproduce its archived measurement. Fold PP
evenly and A4P oddly in time. The single-state cosh and sinh both satisfy the
same three-point effective-mass recurrence. Compare the two masses and their
changes between neighboring times on identical bootstrap blocks. A4P vanishes
at the folded midpoint, so only interior times in the nominal window enter.
Intervals are pointwise and become null if any resample has an undefined mass.
This diagnostic preserves the frozen scoring rule and requires no new inversion.
[Example measurement using both correlators](https://doi.org/10.1103/PhysRevD.100.114514).

## Diffusion baselines

The baseline search evaluates all seven diffusion powers on development and
selects the lowest loss. `H^(2k)` is the sink bilinear obtained by smearing both
quark legs with `H^k`; its contraction equals `||H^k S||^2`. QUDA evaluates these
norms incrementally, avoiding redundant smearing and inversions.

For the frozen SLSQP baseline, let `A_n` be the fitted development amplitude of basis n.
Optimize the actual linear kernel

\[
K=\sum_n \frac{u_n}{A_n}H^n,\qquad \sum_n u_n=1,\quad \sum_n |u_n|\le 8.
\]

The search minimizes development loss plus `0.001 * sum(u_n^2)` using SLSQP,
at most 500 iterations per start. The eight deterministic starts are the seven
basis vectors and their uniform average. The regularizer is a search choice and
is **not** added to the reported task loss. All starts, hyperparameters, and
weights are frozen before validation. An overall normalization has no effect on
the task score.

`submission.json` records raw coefficients, normalized coefficients, development
amplitudes, selected baseline, fitting metrics, protocol/data/source hashes, and
reference diagnostics. Applying the same coefficients to configuration-level
correlators is exact by linearity; it is not a time-dependent alteration of the
estimator. The generic kernel route below independently applies the actual
operator to propagators.

## Submit an arbitrary spatial kernel

The default agent designs **weighted spatial paths**. Each term specifies a sequence
of steps along signed x, y or z axes (±1, ±2, ±3) and an independent weight. An
empty sequence gives the local operator. The agent chooses the number of terms,
the extent, the path ordering, and all the weights. Paths can wind around the
periodic lattice, bend, form closed loops or end at the same displacement via
different routes. The evaluator parallel-transports along the actual gauge links
in the specified order.

For the zero-momentum pion, each seed is averaged over its distinct cubic
rotations and reflections. Charge conjugation of the neutral isospin partner
exchanges the path endpoints and keeps the seed coefficient. Taking the
Hermitian part also complex conjugates the coefficient. The joint projection
keeps the real part of each seed weight times the endpoint-symmetric orbit
average. The JSON accepts a signed number or a pair `[real, imaginary]`.
An overall real rescaling leaves the risk invariant. Components that cancel under
projection contribute zero. The evaluator requires a nonzero projected kernel
and a statistically identified late amplitude.

The [bent-shell example](submissions/bent_shell.json) combines a negative local
term, straight three-link paths, and paths that turn after two links. Measure it
directly on a run prepared with the commands above:

```bash
run=results/pion_projection/reproduction
candidate=tasks/pion_projection/submissions/bent_shell.json
bash scripts/run_pion.sh --output "$run" candidate --definition "$candidate" --split development
bash scripts/run_pion.sh --output "$run" candidate --definition "$candidate" --split validation
```

For other constructions, supply a trusted Python builder as `module:function`
and its JSON parameters. It receives the spatial links on one time slice as a
CuPy array of shape `(3,z,y,x,3,3)` and returns an object with `apply(field)`,
where the input and output fields have shape `(z,y,x,3,nrhs)`. This route also
supports weights computed from the spatial gauge field. Custom builders must
obey gauge covariance, translation and cubic symmetry, Hermiticity, and
linearity in the input field and the neutral-partner C-even identity
`K[U*]^T = K[U]` (transpose in site and color). Custom code is marked
`custom_unverified` and receives diagnostics with a null score. The two
built-in kernel constructors enforce the channel by construction.
The same frozen rule applies at every site, time
and configuration. The evaluator owns the point source, propagators and contraction.

For every configuration the evaluator measures the full time series
`C_K(t) = vdot(S(t), K[U_t] S(t))`. New shapes reuse cached propagators. The
development run freezes the definition, builder hash, measured correlators and
late-fit metric under `candidates/<hash>/`. Validation checks the freeze and
compares the new operator with the local sink, tuned Gaussian and signed SLSQP
mixture on the same configurations. In `results.json`, each entry under
`paired_vs_candidate` reports baseline risk divided by candidate risk and its
paired 95% interval. A ratio above one favors the candidate. Reference failure
suppresses the official score.

For the diffusion family, a quick independent operator check uses the first
configuration of each split and compares the generic contraction against the
previously measured basis combination:

```bash
bash scripts/run_pion.sh candidate --definition results/pion_projection/s16t16_v1/agent_candidate.json --split development --verify-only
bash scripts/run_pion.sh candidate --definition results/pion_projection/s16t16_v1/agent_candidate.json --split validation --verify-only
```

The generic matrix-free Python route is slower than the QUDA diffusion fast path;
these checks do not retrain the proposal. Reusing the now-public validation set
for subsequent proposals must be disclosed and cannot support fresh held-out claims.

## LLM search and report

Prepare the development measurements and frozen reference using `measure` and
`develop`. Set `LLM_API_KEY` and choose a model available at your chat-completions
endpoint (`LLM_BASE` defaults to `https://api.deepseek.com/v1`).

```bash
bash scripts/run_pion.sh --output results/pion_projection/reproduction agent --model MODEL --rounds 3 --with-validation
```

Each round proposes one spatial operator and measures its development 2pt. The
next prompt includes its folded mean, standard error, early normalized curve
and risk components. By default only development is read. With
`--with-validation`, prepare the validation measurements as well. The evaluator
selects the lowest valid development risk, writes `selection.json`, then evaluates
that operator on validation. Individual proposals, measurements and history live
under `agent/operators-*/`. To drive the same loop from a coding agent or by hand,
add `--terminal` and write one JSON object per round, for example
`{"terms":[{"path":[],"weight":-0.08},{"path":[1,1,1],"weight":0.52},{"path":[1,1,2],"weight":0.56}]}`.

### Measuring an agent's use of feedback

Use multiple attempts to measure iterative optimization. A one-attempt run
measures initial proposal quality. Choose the model, proposal budget and number
of independent runs before starting. For example, run two separate sessions on
the same prepared development data:

```bash
run=results/pion_projection/reproduction
bash scripts/run_pion.sh --output "$run" agent --model MODEL --rounds 4 --feedback round
bash scripts/run_pion.sh --output "$run" agent --model MODEL --rounds 4 --feedback batch
```

Both sessions receive the same initial physics diagnostics, use the full path
space and spend one attempt per submitted reply, including malformed and
duplicate proposals. In `round` mode the next proposal can use all earlier
development measurements. In `batch` mode the agent sees its own prior replies,
and the evaluator writes every proposal to disk before measuring the first.
Both modes select the earliest candidate attaining the lowest valid development
risk. If all attempts fail, the session has no selected operator.

Each command prints its session directory. Freeze the selections for **all**
sessions before evaluating the winners. After preparing the validation split,
run the following once per session (substitute the printed path):

```bash
bash scripts/run_pion.sh validate-selection --session "$run/agent/operators-SESSION"
```

A repeated call returns the recorded evaluation. The session directory identifies
its data run. For each comparison, read these artifacts:

| Question | Evidence |
| --- | --- |
| Did both searches have the same budget, starting information, data provenance and evaluator? | Match `conditions_hash` in `search_protocol.json`. Record the model, feedback mode and terminal/API source separately. |
| How good was the first valid idea, and how quickly did the search improve it? | Compare `first_valid_round`, `first_valid_risk` and `best_development_risk_by_attempt` in `selection.json`. The curve starts with nulls if early attempts fail. |
| What did the proposals cost? | Compare valid proposals, attempted development measurements and evaluator wall seconds. Equal proposal counts can involve different measurement costs. |
| Did the gains survive selection? | Read the selected operator's validation risk and its paired intervals against the frozen baselines in the report linked by `evaluation.json`. Report sessions with no valid winner and failed reference checks alongside the successful sessions. |

Improvement within a single development curve can also come from trying more
ideas. Compare feedback conditions over repeated sessions with equal budgets to
estimate the contribution of measurement feedback. Use fresh held-out
configurations and a passing reference for a scored comparison. The public
S16T16 pilot supports diagnostic comparisons.

For the historical seven-coefficient search, use `agent --space basis --model MODEL`.
The existing `evaluate` and `report` commands operate on the frozen diffusion
baselines.

The report command reads `validation_results.json`, sends the ranking and reference
status to the model, and writes `REPORT.md` with the computed table and model commentary.
Machine-specific display examples live in [examples/](../../examples/README.md).

## Ranking diagnostics and search comparison

Run the sensitivity replay against a completed v1 run with both measurement arrays,
the frozen submission, development provenance and the archived validation report.
Use a fresh destination outside the input run. The replay checks the protocol, code,
data and submission identities and reproduces the nominal fit, risks and intervals
before evaluating the other reference windows. Every window uses the same kernels,
development-only amplitude fit metrics and paired nested resampling schedule.

```bash
python -m tasks.pion_projection --output results/pion_projection/s16t16_v1 diagnose-ranking --dest results/replay/local
python -m tasks.pion_projection check-synthetic --dest results/replay/known-spectrum
python -m tasks.pion_projection --output results/pion_projection/s16t16_v1 compare-search --model MODEL --dest results/replay/search
```

The synthetic checks run on CPU with a known mass and independent development and
evaluation blocks. The search comparison uses development only, with 12 proposal
slots for each method plus shared basis diagnostics. Set `--seed` for the random
search. SLSQP reports all objective calls across its starts, both with the pilot's
ridge and with plain risk. For an offline replay of the four recorded RTX 3060
rounds, pass `--terminal --model codex-gpt6-session` and redirect stdin from
`examples/pion_projection/rtx3060/search_replies.jsonl`; each line is one round.

See the [ranking stability report](../../doc/pion_ranking_stability.md) for the
two historical runs, the known-spectrum counterexample, and the search comparison.

## Evaluating optimization ability on fresh synthetic cases

`benchmark-optimization` varies the ground mass, spectral gaps, signed excited-state
overlaps and noise of seven synthetic correlator channels across episodes. Each
episode draws 32 independent development blocks and 32 test blocks from the same
spectrum. Channel and time correlations enter both splits. The evaluator knows the
true mass and supplies it in the development diagnostics. This tests the search
for weights within a fixed basis. The historical real-ensemble runs separately
exercise measurement, kernel implementation and the reference gate.

```bash
python -m tasks.pion_projection benchmark-optimization --episodes 12 --seed 20261118 \
  --replay examples/pion_projection/rtx3060/search_replies.jsonl --dest results/optimization/replay
```

Each method starts with the same single-channel diagnostics and may retain the
best basis vector. It gets four batches of three proposal slots. Invalid or
missing proposals consume the opportunity. Selection uses development risk;
every method's weights are saved before the common test draw. Inspect
`selection.json` for valid counts, fallback to a basis vector and the best
development risk by round. `test.json` includes held-out risk and the error
of an early-time fit on the known noiseless spectrum. `benchmark.json` pairs
methods on the same episodes and records the denominator of each comparison.

The fixed-center and adaptive random controls use the same random steps; only
the adaptive method updates its center between batches. A stronger control fits
the linearized shape departure from the initial basis diagnostics, then queries
the full development risk for twelve ridge settings. The optional archived
replies supply the same twelve proposals on every episode.

Add `--model MODEL` to run each new case twice through the configured LLM API.
One condition returns development risk and rejection feedback each round. The
other shows the model its previous proposals without their outcomes. Both use
the same automatic development selector and fresh chat requests. Condition order
alternates by episode. Twelve episodes use 96 model calls. For a prospective
comparison, freeze the model, prompt and budget before choosing fresh evaluator
seeds; the published seed is intended for reproduction. Compare paired wins,
invalid counts, held-out risk and energy bias across episodes. [Results of the
first transfer check](../../doc/pion_ranking_stability.md#transfer-to-fresh-synthetic-correlators).
