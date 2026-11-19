"""Compare v1 risk with early-window energy fits on known periodic spectra."""
from pathlib import Path

import numpy as np

from core.io import write_json
from .common import protocol
from .experiment import late_metric
from .statistics import ReferenceFit, bootstrap_indices, risk, shape


def synthetic_checks(seed=20261109):
    p = protocol()
    m0 = .8
    energies = [m0, 1.1, 1.5]
    times = np.arange(p['geometry'][3] // 2 + 1)
    modes = shape(energies, times, p['geometry'][3])
    # Choose the third amplitude to cancel the first excited term exactly at t=3.
    cancel = -modes[1, 3] / modes[2, 3]
    cases = {'single': ([1, 0, 0], .04), 'lower_noise': ([1, 0, 0], .01),
             'excited': ([1, 1, 0], .04), 'reduced_excitation': ([1, .12, 0], .04),
             'signed_cancellation': ([1, 1, cancel], .04), 'near_zero_overlap': ([1e-5, 0, 0], .04)}
    n = 48
    rng = np.random.default_rng(seed)
    cov = .65 ** np.abs(times[:, None] - times)
    dev_noise, val_noise = rng.multivariate_normal(np.zeros(len(times)), cov, size=(2, n))
    index = bootstrap_indices(n, 256, seed + 1)
    early = p['score_window']
    results = {}
    for name, (amplitudes, noise) in cases.items():
        components = np.asarray(amplitudes)[:, None] * modes
        truth = components.sum(axis=0)
        dev = (truth + noise * modes[0] * dev_noise)[:, None, :]
        val = (truth + noise * modes[0] * val_noise)[:, None, :]
        row = {'amplitudes': amplitudes, 'noise_scale': noise,
               'unsigned_excited_over_ground_early':
                   (abs(components[1:, early]).sum(axis=0) / abs(components[0, early])).tolist(),
               'signed_excited_over_ground_early':
                   (components[1:, early].sum(axis=0) / components[0, early]).tolist()}
        try:
            score = risk(val, [1], m0, np.full(len(index), m0), index, p,
                         late_inverse=late_metric(dev, [1], p))
        except ValueError as exc:
            row.update(risk=None, invalid_reason=str(exc))
        else:
            row.update({k: score[k] for k in ('risk', 'variance', 'departure_squared', 'amplitude_z')})

        # The development metric is fixed for truth, point and validation replicas.
        model = ReferenceFit(dev, dict(p, reference_basis=[0]), early)
        samples = val[:, 0, early] / model.scales[0]
        noiseless_mass = model.fit(truth[early] / model.scales[0])[0]
        mass = model.fit(samples.mean(axis=0))[0]
        boot = np.array([model.fit(rep)[0] for rep in samples[index].mean(axis=1)])
        row['energy'] = {'noiseless_bias': noiseless_mass - m0, 'estimate': mass,
                         'error_to_truth': mass - m0, 'bootstrap_se': float(boot.std(ddof=1)),
                         'interval': np.quantile(boot, [.025, .975]).tolist(),
                         'replicas_at_bound': int(np.sum((boot < p['mass_bounds'][0] + .0001)
                                                         | (boot > p['mass_bounds'][1] - .0001)))}
        results[name] = row
    return {'seed': seed, 'energies': energies, 'frozen_reference_mass': m0, 'early_window': early,
            'temporal_extent': p['geometry'][3], 'blocks_per_split': n, 'bootstrap_samples': len(index),
            'time_noise_correlation': .65, 'cases': results}


def run(destination, seed):
    path = Path(destination)
    path.mkdir(parents=True, exist_ok=False)
    result = synthetic_checks(seed)
    write_json(path / 'synthetic.json', result)
    return result
