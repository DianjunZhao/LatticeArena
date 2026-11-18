"""Pre-registered paired analysis: identity vs candidate risk (todo P2).

Runs on the archived v1 measurement. That measurement used the old,
non-covariant APE kernel, so the output is a pipeline demonstration only and
must not be read as a physical result.
"""
import json
from pathlib import Path

import numpy as np

from .common import protocol
from .statistics import bootstrap_indices, risk

RUN = Path('results/wilson_loop/s16t16_v1')
OUT = Path('results/wilson_loop/paired_legacy_v1')


def paired_ratios(data, windows, t_values, v_ref, outer=500, inner=500, seed=20261118):
    """data: (nblocks, nkernels, nR, nT); ratios are risk(identity)/risk(candidate)."""
    rng = np.random.default_rng(seed)
    vi = bootstrap_indices(len(data), inner, seed + 1)
    ratios = np.zeros((outer, data.shape[1] - 1))
    for o in range(outer):
        rows = rng.integers(0, len(data), len(data))
        base = risk(data[rows, 0], vi, windows, t_values, v_ref)['risk']
        for k in range(1, data.shape[1]):
            cand = risk(data[rows, k], vi, windows, t_values, v_ref)['risk']
            ratios[o, k - 1] = base / cand
    return ratios


def main():
    p = protocol()
    frozen = json.loads((RUN / 'submission.json').read_text())
    data = np.load(RUN / 'validation.npz')['loops']
    from .statistics import blocks
    data = blocks(data, p['block_length'])
    names = [k['name'] for k in p['kernels']][1:]
    ratios = paired_ratios(data, frozen['windows'], p['t_values'], np.array(frozen['identity']['v']))
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {}
    for j, name in enumerate(names):
        col = ratios[:, j]
        summary[name] = {'median': float(np.median(col)),
                         'ci95': np.quantile(col, [0.025, 0.975]).tolist(),
                         'probability_better': float(np.mean(col > 1)),
                         'draws': int(len(col))}
    (OUT / 'paired.json').write_text(json.dumps(
        {'status': 'pipeline_demo_only', 'kernel_status': 'legacy_non_covariant',
         'plan': {'outer': 500, 'inner': 500, 'seed': 20261118,
                  'statistic': 'risk(identity)/risk(candidate) on paired block draws'},
         'candidates': summary}, indent=2) + '\n')
    (OUT / 'README.md').write_text(
        '# paired analysis (legacy v1)\n\n'
        'Pipeline demonstration of `tasks/wilson_loop/paired.py` on the archived v1 measurement.\n'
        'The v1 APE kernel is **not gauge covariant**, so these intervals are not physical results;\n'
        'they only show the pre-registered analysis works. Re-run after the v2 re-measurement.\n')
    for name, row in summary.items():
        print(name, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items()})


if __name__ == '__main__':
    main()
