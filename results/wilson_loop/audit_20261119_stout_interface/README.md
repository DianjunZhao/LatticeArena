# Stout opt-in interface: synthetic-only Wilson-loop response

`build_kernel` defaults to the unchanged APE branch. Only explicit `kind=stout` dispatches rho/steps to the CPU stout updater. `operator_contract_for('stout')` includes stout source identity and per-staple rho semantics. No protocol default, identity definition, evaluator or scoring formula changed. The runtime import avoids circular module initialization. Production measurement dependency closure has not been extended to authorize stout: this result does not authorize a production run or reuse of old archives.

Seed20261119, one synthetic SU3 field (mu,t,z,y,x)=(4,3,2,3,4), periodic shifts. Same spatial input and unchanged temporal links for all three responses, R=1,2, T=1,2. Each value is the deterministic full lattice/color/direction mean ReTr/(9 volume), not an independent ensemble estimate. **No statistical SE/CI exists for this single field**; this table is a response diagnostic, not a significance or physical ranking. NumPy complex128, contract tolerance1e-11; input mutation exactly zero.

| option | W(1,1) | W(1,2) | W(2,1) | W(2,2) |
|---|---|---|---|---|
| identity | 0.00382705991535 | -0.0124167664226 | -0.0032530444572 | -0.01541993121 |
| ape | -0.0135419525249 | -0.00365484838062 | 0.0143745135978 | -0.00486718294266 |
| stout | -0.00607369489644 | -0.00557907546033 | 0.00713375401453 | -0.0051976379559 |

Parameters: identity alpha=0/steps=0; APE alpha=.4/steps=2; stout rho=.1/steps=2. These are not matched physical smearing radii or matched cost. Raw values, parameters, contract source hashes and rejected examples are in [response.json](response.json). Unknown kind, negative rho, mixed alpha/rho are rejected and reasons retained. Tests cover interface covariance/time locality, unchanged default APE output, exact identity, contract dependency and bad parameters; standalone SU3/time-locality tests remain. 11 tests passed in0.11s.

Reproduce tests: `PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -q -p no:cacheprovider tests/test_wilson_stout.py tests/test_wilson_stout_interface.py`. No physical score, HMC receipt, GPU or MPI run was generated. Physical comparison remains NOT_RUN; production preflight must freeze new dependency closure, hardware/budget and independent samples first.
