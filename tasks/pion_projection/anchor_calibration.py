"""Anchor sensitivity with real block draws (C3).

Replaces the pseudo-replication in energy_experiment.anchor_sensitivity: the
baseline/candidate energies come from block-bootstrap draws of independent
datasets, the anchor is sampled independently and shared by both candidates, and
the naive bootstrap interval is compared with the independent-dataset interval.
"""
import json
from pathlib import Path

import numpy as np

from .energy_experiment import correlators
from .energy_target import lower_bound
from .statistics import ReferenceFit, blocks, bootstrap_indices

OUT = Path('results/pion_projection/anchor_calibration_v1')
PROTOCOL = json.loads(Path('results/pion_projection/s16t16_v1/development_provenance.json').read_text())['protocol']
WINDOW = PROTOCOL['reference_windows'][PROTOCOL['reference_nominal_window']]
TAU_E = 0.01


def mass_draws(raw, rng, n_boot=100):
    data = blocks(raw, PROTOCOL['block_length'])
    ref = ReferenceFit(data, PROTOCOL, WINDOW)
    index = rng.integers(0, len(data), (n_boot, len(data)))
    _, masses = ref.bootstrap(index)
    return np.asarray(masses)


def run_cell(rng, candidate_noise, sigma_anchor, bias_anchor, n_dataset=30, n_boot=100, e0=0.80):
    naive_hits = 0
    dataset_deltas = []
    for _ in range(n_dataset):
        e_b = mass_draws(correlators(rng, noise=0.02), rng, n_boot)
        e_c = mass_draws(correlators(rng, noise=candidate_noise), rng, n_boot)
        anchor = e0 + bias_anchor + (rng.normal(0, sigma_anchor, len(e_b)) if sigma_anchor else 0.0)
        delta = ((e_b - anchor) ** 2 - (e_c - anchor) ** 2) / TAU_E ** 2
        if len(delta) >= 10:
            naive_hits += lower_bound(delta, 0.05) > 0
        dataset_deltas.append(float(delta.mean()))
    dataset_deltas = np.asarray(dataset_deltas)
    return {'candidate_noise': candidate_noise, 'sigma_anchor': sigma_anchor, 'bias_anchor': bias_anchor,
            'n_dataset': n_dataset, 'n_boot': n_boot,
            'naive_certified_fraction': naive_hits / n_dataset,
            'dataset_mean': float(dataset_deltas.mean()),
            'dataset_se': float(dataset_deltas.std(ddof=1) / np.sqrt(n_dataset)),
            'dataset_certified': (bool(lower_bound(dataset_deltas, 0.05) > 0)
                                  if len(dataset_deltas) >= 10 else None)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261121)
    rows = []
    for scenario, candidate_noise in (('improvement', 0.01), ('null', 0.02)):
        for sigma in (0.0, 0.005, 0.01, 0.02):
            row = run_cell(rng, candidate_noise, sigma, 0.0)
            row['scenario'] = scenario
            rows.append(row)
            print(scenario, 'sigma', sigma, 'naive', row['naive_certified_fraction'],
                  'dataset_certified', row['dataset_certified'])
    for bias in (0.01, 0.02, 0.05):
        row = run_cell(rng, 0.01, 0.0, bias)
        row['scenario'] = 'anchor_bias'
        rows.append(row)
        print('bias', bias, 'naive', row['naive_certified_fraction'])
    scaling = []
    for n_boot in (50, 200, 800):
        widths = []
        for _ in range(10):
            e_b = mass_draws(correlators(rng, noise=0.02), rng, n_boot)
            e_c = mass_draws(correlators(rng, noise=0.01), rng, n_boot)
            anchor = 0.80 + rng.normal(0, 0.01, len(e_b))
            delta = ((e_b - anchor) ** 2 - (e_c - anchor) ** 2) / TAU_E ** 2
            widths.append(float(delta.mean() - lower_bound(delta, 0.05)))
        scaling.append({'n_boot': n_boot, 'mean_naive_interval_width': float(np.mean(widths)),
                        'relative_to_50': float(np.mean(widths) / scaling[0]['mean_naive_interval_width']) if scaling else 1.0})
    paired = paired_estimators(rng)
    paired_shared = paired_estimators(rng, cfg_shared=0.5)
    fixed = nboot_fixed_data(rng)
    result = {'rows': rows, 'nboot_scaling': scaling,
              'paired_estimators': paired, 'paired_estimators_shared_cfg': paired_shared,
              'nboot_fixed_data': fixed,
              'note': ('dataset_se is the independent-dataset standard error; naive uses '
                       'the bootstrap draws as if independent and shrinks with Nboot')}
    (OUT / 'anchor_calibration.json').write_text(json.dumps(result, indent=2) + '\n')
    print('scaling', scaling)
    print('wrote', OUT)




def paired_dataset(rng, noise_b=0.02, noise_c=0.01, ncfg=120, cfg_shared=0.0):
    """One physical dataset: common config noise, baseline/candidate differ in amplitude."""
    t = np.arange(PROTOCOL['geometry'][3])
    signal = np.exp(-0.5 * t) + np.exp(-0.5 * (t.size - t))
    eps = rng.normal(size=(ncfg, 1, t.size))
    shared = rng.normal(size=(ncfg, 1, 1)) * np.sqrt(max(cfg_shared, 0.0)) * 0.01
    base_b = signal[None, None, :] * (1 + noise_b * eps + shared)
    base_c = signal[None, None, :] * (1 + noise_c * eps + shared)
    channels = len(PROTOCOL['powers'])
    return (np.broadcast_to(base_b, (ncfg, channels, t.size)).copy(),
            np.broadcast_to(base_c, (ncfg, channels, t.size)).copy())


def _masses(raw, rng, n_boot):
    data = blocks(raw, PROTOCOL['block_length'])
    ref = ReferenceFit(data, PROTOCOL, WINDOW)
    index = rng.integers(0, len(data), (n_boot, len(data)))
    _, masses = ref.bootstrap(index)
    return np.asarray(masses), index


def paired_estimators(rng, n_boot=200, sigma_anchor=0.005, e0=0.80, n_dataset=30, cfg_shared=0.0):
    """naive (draws as independent), paired single-ensemble, independent-repeat."""
    naive_widths, paired_widths, deltas = [], [], []
    for _ in range(n_dataset):
        raw_b, raw_c = paired_dataset(rng, cfg_shared=cfg_shared)
        e_b, index = _masses(raw_b, rng, n_boot)
        e_c, _ = _masses(raw_c, rng, n_boot)
        anchor = e0 + rng.normal(0, sigma_anchor, n_boot)
        delta = ((e_b - anchor) ** 2 - (e_c - anchor) ** 2) / TAU_E ** 2
        naive_widths.append(float(2 * 1.96 * delta.std(ddof=1) / np.sqrt(n_boot)))
        paired_widths.append(float(np.quantile(delta, 0.975) - np.quantile(delta, 0.025)))
        deltas.append(float(delta.mean()))
    deltas = np.asarray(deltas)
    repeat_se = float(deltas.std(ddof=1) / np.sqrt(len(deltas)))
    return {'n_dataset': n_dataset, 'n_boot': n_boot,
            'naive_width_mean': float(np.mean(naive_widths)),
            'paired_width_mean': float(np.mean(paired_widths)),
            'independent_mean': float(deltas.mean()),
            'independent_se': repeat_se,
            'independent_interval': [float(deltas.mean() - 1.96 * repeat_se),
                                     float(deltas.mean() + 1.96 * repeat_se)]}


def nboot_fixed_data(rng, sigma_anchor=0.005, e0=0.80, budgets=(50, 200, 800)):
    """Same raw data and anchor input; only the bootstrap budget changes."""
    raw_b, raw_c = paired_dataset(rng)
    data_b = blocks(raw_b, PROTOCOL['block_length'])
    data_c = blocks(raw_c, PROTOCOL['block_length'])
    ref_b = ReferenceFit(data_b, PROTOCOL, WINDOW)
    ref_c = ReferenceFit(data_c, PROTOCOL, WINDOW)
    anchor_inputs = rng.normal(0, sigma_anchor, max(budgets))
    rows = []
    for n_boot in budgets:
        index = rng.integers(0, len(data_b), (n_boot, len(data_b)))
        _, e_b = ref_b.bootstrap(index)
        _, e_c = ref_c.bootstrap(index)
        anchor = e0 + anchor_inputs[:n_boot]
        delta = ((np.asarray(e_b) - anchor) ** 2 - (np.asarray(e_c) - anchor) ** 2) / TAU_E ** 2
        rows.append({'n_boot': n_boot,
                     'naive_width': float(2 * 1.96 * delta.std(ddof=1) / np.sqrt(n_boot)),
                     'paired_width': float(np.quantile(delta, 0.975) - np.quantile(delta, 0.025))})
    return rows


if __name__ == '__main__':
    main()
