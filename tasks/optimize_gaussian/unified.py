"""Unified statistics entry for the frozen linear candidates (todo P1).

Recomputes the point risks from the frozen v1 data with one code path and then
does a fold-local evaluation (reference refitted on each training fold). The
learned BCB kernel needs the collected response data and is reported as
archived/PARTIAL, not re-evaluated here.
"""
import json
from pathlib import Path

import numpy as np

from tasks.pion_projection.reference import make_reference
from tasks.pion_projection.statistics import blocks, bootstrap_indices, fold, risk

RUN = Path('results/pion_projection/s16t16_v1')
OUT = Path('results/optimize_gaussian/unified_v1')


def load():
    p = json.loads((RUN / 'development_provenance.json').read_text())['protocol']
    sub = json.loads((RUN / 'submission.json').read_text())
    dev = blocks(fold(np.load(RUN / 'development.npz')['correlators']), p['block_length'])
    val = blocks(fold(np.load(RUN / 'validation.npz')['correlators']), p['block_length'])
    return p, sub, dev, val


def evaluate(data, weights, p, mass, masses, seed, late_inverse=None):
    index = bootstrap_indices(len(data), p['bootstrap_samples'], seed)
    return risk(data, np.asarray(weights), mass, masses, index, p,
                late_inverse=np.asarray(late_inverse) if late_inverse is not None else None)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    p, sub, dev, val = load()
    window = p['reference_windows'][p['reference_nominal_window']]
    ref = make_reference(dev, p, window, 'single')
    m0, masses = ref.bootstrap(bootstrap_indices(len(dev), p['bootstrap_samples'], p['seed']))
    rows = {}
    for name, weights in sub['submissions'].items():
        late = sub['late_inverse_covariances'][name]
        rows[name] = evaluate(val, weights, p, m0['mass'], masses, p['seed'] + 1, late)
    archived = json.loads((RUN / 'candidates' / '63c33e619e06704a' / 'compare.json').read_text())['point_risk']
    mapping = {'local': 'local', 'agent_signed_mixture': 'slsqp', 'tuned_gaussian': None}
    checks = {}
    for name in rows:
        key = mapping.get(name)
        checks[name] = {'computed': rows[name]['risk'],
                        'archived': archived.get(key) if key else None,
                        'delta': (abs(rows[name]['risk'] - archived[key]) if key and key in archived else None)}
    folds = np.array_split(np.random.default_rng(5).permutation(len(dev)), 3)
    fold_rows = []
    for i, test_ids in enumerate(folds):
        train = dev[np.setdiff1d(np.arange(len(dev)), test_ids)]
        test = dev[test_ids]
        fold_ref = make_reference(train, p, window, 'single')
        fold_m0, fold_masses = fold_ref.bootstrap(bootstrap_indices(len(train), p['bootstrap_samples'], p['seed'] + i))
        fold = {'fold': i, 'mass': float(fold_m0['mass'])}
        for name, weights in sub['submissions'].items():
            fold[name] = evaluate(test, weights, p, fold_m0['mass'], fold_masses, p['seed'] + 100 + i)['risk']
        fold['local_over_slsqp'] = fold['local'] / fold['agent_signed_mixture']
        fold_rows.append(fold)
    ratios = np.array([f['local_over_slsqp'] for f in fold_rows])
    result = {'point': {name: {k: rows[name][k] for k in ('risk', 'variance', 'departure_squared', 'amplitude', 'amplitude_z')}
                        for name in rows},
              'archived_point_check': checks,
              'fold_local': fold_rows,
              'fold_local_mean_ratio': float(ratios.mean()),
              'fold_local_se_ratio': float(ratios.std(ddof=1) / np.sqrt(len(ratios))),
              'learned_bcb_kernel': 'archived only (needs the collected response data); not re-evaluated',
              'gate': 'reference not certified -> diagnostic_only'}
    (OUT / 'unified.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'point': {n: round(v['risk'], 6) for n, v in rows.items()},
                      'archived_check': {n: (round(c['delta'], 8) if c['delta'] is not None else None)
                                         for n, c in checks.items()},
                      'fold_ratio': (round(ratios.mean(), 2), round(result['fold_local_se_ratio'], 2))}, indent=2))
    print('wrote', OUT)


if __name__ == '__main__':
    main()
