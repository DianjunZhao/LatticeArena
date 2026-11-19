"""Finite GEVP ground-mode failure grid (todo B)."""
import json
from pathlib import Path

import numpy as np

from .gevp_stats import bootstrap_gevp, summarise, effective_energy
from .statistics import blocks, bootstrap_indices

OUT = Path('results/pion_projection/gevp_ground_failure_grid_v1')
NOISE = (0.01, 0.05)
GAP = (0.1, 0.5)
T0 = (1, 2)
RANK = 2
CUTOFF = (1e-8, 1e-5)
T = 16


def world(rng, ncfg, mass, gap, noise):
    t = np.arange(T)
    e0, e1 = mass, mass + gap
    a0 = np.array([1.0, 0.6])
    a1 = np.array([0.2, 0.5])
    signal = (np.outer(a0, np.exp(-e0 * t) + np.exp(-e0 * (T - t)))
              + np.outer(a1, np.exp(-e1 * t) + np.exp(-e1 * (T - t))))
    data = signal[None] * (1 + noise * rng.normal(size=(ncfg, 2, T)))
    return data


def cell(rng, mass, gap, noise, t0, cutoff, n_dataset=20, n_boot=60):
    failures = 0
    biases = []
    covered = 0
    for _ in range(n_dataset):
        data = blocks(world(rng, 120, mass, gap, noise), 5)
        mix = np.array([[1.0, 0.3], [0.3, 1.0]])
        matrix = np.einsum('ab,nbt,cb->nact', mix, data, mix)
        index = bootstrap_indices(len(data), n_boot, 7)
        energies, failures_list = bootstrap_gevp(matrix, index, t0=t0,
                                                 times=(t0 + 1, t0 + 2, t0 + 3),
                                                 rank=RANK, cutoff=cutoff)
        summary = summarise(energies, (t0 + 1, t0 + 2, t0 + 3))
        if not np.isfinite(summary['energy']):
            failures += 1
            continue
        biases.append(summary['energy'] - mass)
        se = summary['se']
        if se is not None and np.isfinite(se) and abs(summary['energy'] - mass) <= 1.96 * se:
            covered += 1
    valid = len(biases)
    return {'n_dataset': n_dataset, 'failures': failures, 'valid': valid,
            'bias': float(np.mean(biases)) if biases else None,
            'bias_mc_se': float(np.std(biases, ddof=1) / np.sqrt(valid)) if valid > 1 else None,
            'coverage': covered / valid if valid else None}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261119)
    rows = []
    for noise in NOISE:
        for gap in GAP:
            for t0 in T0:
                for cutoff in CUTOFF:
                    result = cell(rng, 1.0, gap, noise, t0, cutoff)
                    result.update({'noise': noise, 'gap': gap, 't0': t0,
                                   'rank': RANK, 'cutoff': cutoff})
                    rows.append(result)
                    print(noise, gap, t0, cutoff, result['failures'], result['valid'],
                          result['bias'], result['coverage'])
    result = {'schema': 'pion-gevp-grid-v1', 'mass': 1.0, 'T': T, 'rows': rows,
              'note': ('rank=2 with a 2x2 matrix; invalid/non-positive metric returns an empty '
                       'spectrum and is counted as a failure')}
    (OUT / 'gevp_ground_failure_grid.json').write_text(json.dumps(result, indent=2) + '\n')
    print('wrote', OUT)


if __name__ == '__main__':
    main()
