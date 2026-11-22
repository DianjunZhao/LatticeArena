# Trainable-W actual-kernel gradient audit

**Deterministic CPU implementation check.** It uses synthetic SU(3) links and a complex probe field; no production gauge, propagator, reference, GPU, or sealed split is read. `physical_score=null`.

The checked scalar is the actual real hopping correlator `Re <psi|K(W,v,c)|psi>` using `features.directional_features` and `kernels.apply_kernel`. Spatial axes are stored `(z,y,x)`, link directions `(x,y,z)`, and the probe has four columns.

For each link coefficient, the derivative of the forward and adjoint backward hop is `q_mu(x)=2 Re sum_color,probe psi(x)^dagger U_mu(x) psi(x+mu)`. The remaining chain rule is

```text
dC/dc       = sum_(mu,x) q_mu(x)
dC/dv_h     = sum_(mu,x) q_mu(x) centered_phi_h(mu,x)
dC/dW_hj    = sum_(mu,x) [q_mu(x)-mean_x q_mu(x)] v_h (1-phi_h(mu,x)^2) z_mu,j(x)
```

The fixture uses hidden width `H=2` (two W rows, two v values, and c), giving 7 W/v/c components. The projected `q-mean_x(q)` is required because the model centers every feature over each direction's spatial slice. The plot compares all 7 components to central differences over nine step sizes; each point includes every component, not just a selected parameter.

![Finite-difference convergence for the operator gradient](gradient_convergence.png)

There were 63 planned checks, 63 finite checks, 0 nonfinite checks, and 0 abstentions. At the unit-test step `2e-6`, maximum absolute error was 3.516e-08; the best sweep error was 3.243e-09 at step 1.0e-04.

This verifies the chain derivative through the actual CPU hopping kernel for this finite deterministic fixture. It does not validate GPU/CuPy behavior, the Gaussian sandwich, positivity, QUDA propagators, the ensemble-risk/reference derivative, solver convergence, or any physical comparison. The production `train.main` still does not optimize W; objective and solver budgets remain protocol decisions.

Raw per-component/per-step values are in `gradient_components.csv`; source and artifact hashes are in `artifact_hashes.json`.
