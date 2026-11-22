# Expanded independent-link convergence diagnostic

See preregistration.json (written before generation), raw.json and both figures. Twenty new independent datasets; original seeds 0–2 untouched. Three common starts; budgets 25/100/400 objective calls per start. Analytical SLSQP gradients are not charged as objective calls, so this is objective-budget matching, not wall-time matching.

Flags across all budgets/starts (repeated trajectories are not independent trials): {'budget_exhausted': 1023, 'solver_non_success': 0, 'success_large_residual': 0}. Full rank: 80/80.

|epsilon|class|budget|paired delta|dataset CI95|
|---|---|---|---|---|
|0.0|A_spectral|25|0.889743|[0.8893466922318558, 0.8901540564830417]|
|0.0|A_spectral|100|0.134635|[0.13310285594110347, 0.13620900784505494]|
|0.0|A_spectral|400|0.0784496|[0.07718644741837503, 0.08016399053239508]|
|0.0|B_nested|25|0.884159|[0.8809955814500493, 0.8867292579337271]|
|0.0|B_nested|100|0.134578|[0.13307404389285468, 0.13611645797653404]|
|0.0|B_nested|400|0.110394|[0.10835161194665263, 0.1122016428692698]|
|0.1|A_spectral|25|0.889688|[0.8892919098272394, 0.8900955545533503]|
|0.1|A_spectral|100|0.134536|[0.13299064441743733, 0.13609948180248196]|
|0.1|A_spectral|400|0.0809628|[0.07721176151673716, 0.084731959562355]|
|0.1|B_nested|25|0.883891|[0.8806362193768124, 0.886482544643488]|
|0.1|B_nested|100|0.134763|[0.13322544936758315, 0.13631007845467902]|
|0.1|B_nested|400|0.11023|[0.10726778312673166, 0.11233161439983128]|

All flagged seed/start/residual cases are explicitly listed in raw.json. Budget exhaustion means truncation, not intrinsic optimizer failure. No learned W, production links, physical risk or learned-smear superiority is tested. B oracle near-zero error is constructive teacher inclusion. N=20 is a finite descriptive expansion, not high-precision failure-rate calibration.

## Maximum-budget residual and truncation table (epsilon=0.1)

|class/method|mean projected-gradient|mean test error|truncated starts/60|
|---|---|---|---|
|A_spectral/SLSQP|3.0369789e-08|0.0004157346|0/60|
|A_spectral/Powell|0.01032963|0.081378495|60/60|
|B_nested/SLSQP|5.1823154e-09|3.5715727e-05|0/60|
|B_nested/Powell|0.019237758|0.1102661|60/60|

Scaled condition range: (542375.4756500154, 731204.3616676116). Full rank does not imply good conditioning. Example truncated trajectories and their residuals are in flagged_trials, preserving seed, epsilon, class, method, budget and start.
