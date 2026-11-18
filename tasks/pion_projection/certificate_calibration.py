"""End-to-end calibration of the candidate improvement certificate (C2).

Each simulation generates independent development/validation worlds, fits the
reference and its gate on development, runs joint draws, and evaluates the
certificate. Scenarios: no improvement, a known improvement (lower excited-state
contamination), and a misspecified single-cosh reference.
"""
import json
from pathlib import Path

import numpy as np
from scipy.stats import chi2

from .reference import make_reference
from .scoring import improvement_certificate
from .statistics import blocks, bootstrap_indices, risk

OUT = Path('results/pion_projection/certificate_calibration_v1')
PROTOCOL = json.loads(Path('results/pion_projection/s16t16_v1/development_provenance.json').read_text())['protocol']
E0, E1 = 1.0, 1.5
AMPS = np.array([1.0, 0.8, 0.6, 0.4, 0.3, 0.2, 0.15])
CONTAM = np.array([1.0, 0.85, 0.7, 0.5, 0.35, 0.25, 0.15])   # excited-state fraction per channel


def world(rng, ncfg, contam=None, noise=0.02, cfg_sigma=0.01, time_rho=0.5):
    T = PROTOCOL['geometry'][3]
    t = np.arange(T)
    r = (CONTAM if contam is None else contam)[None, :]
    signal = (AMPS[:, None] * (np.exp(-E0 * t) + np.exp(-E0 * (T - t)))[None, :]
              + r.T * AMPS[:, None] * (np.exp(-E1 * t) + np.exp(-E1 * (T - t)))[None, :])
    cfg = rng.normal(size=(ncfg, len(AMPS), 1)) * cfg_sigma
    eps = rng.normal(size=(ncfg, len(AMPS), T))
    for k in range(1, T):
        eps[:, :, k] = time_rho * eps[:, :, k - 1] + np.sqrt(1 - time_rho ** 2) * rng.normal(size=(ncfg, len(AMPS)))
    return signal[None] * (1 + cfg + noise * eps)


def gate(dev_blocks):
    ref = make_reference(dev_blocks, PROTOCOL,
                         PROTOCOL['reference_windows'][PROTOCOL['reference_nominal_window']], 'single')
    mean = ref.samples.mean(axis=0)
    mass, cost = ref.fit(mean)
    dof = ref.samples.shape[1] - len(PROTOCOL['reference_basis']) - 1
    return ref, mass, float(chi2.sf(cost, dof))


def run_simulation(rng, contam_baseline, contam_candidate, outer=60, inner=24, blocks_dev=24):
    ncfg = blocks_dev * PROTOCOL['block_length']
    dev = blocks(world(rng, ncfg, contam_baseline), PROTOCOL['block_length'])
    val = blocks(world(rng, 12 * PROTOCOL['block_length'], contam_baseline), PROTOCOL['block_length'])
    ref, mass, p_value = gate(dev)
    if p_value < 0.05:
        return {'abstain': True, 'p_value': p_value}
    baseline = np.zeros(len(AMPS))
    baseline[1] = 1.0
    candidate = np.zeros(len(AMPS))
    candidate[2] = 1.0
    draw_ids = np.arange(outer)
    risks = {'base': np.zeros(outer), 'cand': np.zeros(outer)}
    for b in range(outer):
        dev_idx = rng.integers(0, len(dev), len(dev))
        ref_b = make_reference(dev[dev_idx], PROTOCOL,
                               PROTOCOL['reference_windows'][PROTOCOL['reference_nominal_window']], 'single')
        fit_b, masses = ref_b.bootstrap(rng.integers(0, len(dev), (inner, len(dev))))
        val_idx = rng.integers(0, len(val), len(val))
        inner_idx = rng.integers(0, len(val), (inner, len(val)))
        for name, weights in (('base', baseline), ('cand', candidate)):
            risks[name][b] = risk(val[val_idx], weights, fit_b['mass'], masses, inner_idx, PROTOCOL)['risk']
    spec = {'schema': 'pion-score-v1', 'version': 'c2', 'estimand': 'conditional',
            'baseline_id': 'base', 'accepted_models': ['single'], 'candidate_ids': ['cand'],
            'analysis_version': 'c2', 'alpha': 0.05,
            'comparison_family': {'candidates': 1, 'models': 1},
            'min_baseline_risk': 1e-9, 'invalid_tolerance': 0.05, 'min_improvement': 1.0,
            'risk_floor': 0.0, 'require_draw_ids': True}
    certificate = improvement_certificate({'single': {'base': risks['base'], 'cand': risks['cand']}},
                                          spec, draw_ids=draw_ids)
    return {'abstain': False, 'p_value': p_value, 'certified': bool(certificate['candidates']['cand']['certified']),
            'lower_bound': certificate['candidates']['cand']['improvement_lower_bound'],
            'point_ratio': float(risks['base'].mean() / risks['cand'].mean()),
            'risks': {name: values.tolist() for name, values in risks.items()}}


def main(n_dataset=8, blocks_list=(6, 12, 24), seed=20261120):
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    flat = np.zeros(7)
    same = flat.copy(); same[1] = same[2] = 0.5
    better = flat.copy(); better[1] = 0.7; better[2] = 0.2
    miss = flat.copy(); miss[[0, 3, 4]] = 0.5; miss[[1, 2]] = 0.5
    scenarios = {
        'no_improvement': (same, same),
        'known_improvement': (better, better),
        'misspecified_reference': (miss, miss),
    }
    rows = {}
    for name, (base_c, cand_c) in scenarios.items():
        for blocks in blocks_list:
            results = []
            for _ in range(n_dataset):
                results.append(run_simulation(rng, base_c, cand_c, blocks_dev=blocks))
            valid = [r for r in results if not r['abstain']]
            certified = sum(r['certified'] for r in valid)
            key = f'{name}/blocks_{blocks}'
            rows[key] = {'n_dataset': n_dataset, 'blocks': blocks, 'abstain': n_dataset - len(valid),
                         'valid': len(valid), 'certified': certified,
                         'unconditional_certified_rate': certified / n_dataset,
                         'conditional_certified_rate': certified / len(valid) if valid else None,
                         'median_lower_bound': float(np.median([r['lower_bound'] for r in valid])) if valid else None,
                         'details': results}
            print(key, {k: rows[key][k] for k in ('n_dataset', 'abstain', 'valid', 'certified',
                                                  'unconditional_certified_rate')})
    (OUT / 'certificate_calibration.json').write_text(json.dumps(rows, indent=2) + '\n')
    print('wrote', OUT)


if __name__ == '__main__':
    main()
