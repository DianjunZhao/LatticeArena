"""Read-only audit of the historical optimize_gaussian runs.

All runs below used the pre-2026-11-18 features (forward-anchored plaquettes,
no link-centring), so their risks are uncertified diagnostics, not physical
evidence for or against the learned kernel.
"""
import json
from pathlib import Path

ROOT = Path('results/optimize_gaussian')
CANDIDATE = Path('results/pion_projection/s16t16_v1/candidates/f686a72d9c868716')


def load(name):
    for filename in ('results.json', 'v3_results.json', 'v2_results.json', 'smoke_results.json'):
        path = ROOT / name / filename
        if path.exists():
            return json.loads(path.read_text())
    return None


def summarize(name, r):
    if r is None:
        return {'version': name, 'status': 'missing'}
    if 'models' in r:  # v5
        best = r['best_mode']
        return {'version': name, 'status': 'historical', 'feature_version': 'legacy',
                'dev_val': r['models'][best]['dev_val'], 'test': r['models'][best]['test'],
                'base_test': r['base']['test'], 'ratio': r['base']['test'] / r['models'][best]['test'],
                'note': f'mode={best}'}
    if 'test_risk_learned' in r:
        return {'version': name, 'status': 'historical', 'feature_version': 'legacy',
                'dev_val': r.get('best', {}).get('dev_val', r.get('best_lam2')),
                'test': r['test_risk_learned'], 'base_test': r['test_risk_base'],
                'ratio': r.get('test_ratio', r['test_risk_base'] / r['test_risk_learned']),
                'base_steps': r.get('best', {}).get('base_steps', r.get('base_steps'))}
    if 'final_loss' in r:  # smoke runs: shape loss, not the full risk
        return {'version': name, 'status': 'historical-smoke', 'feature_version': 'legacy',
                'initial_loss': r['initial_loss'], 'final_loss': r['final_loss'],
                'note': 'shape-loss objective, not the full risk'}
    if 'grid' in r and 'base' in r:  # v4
        return {'version': name, 'status': 'historical', 'feature_version': 'legacy',
                'dev_val': min(g['dev_val_risk'] for g in r['grid']),
                'test': r['test_risk_learned'], 'base_test': r['test_risk_base'],
                'ratio': r['test_ratio']}
    return {'version': name, 'status': 'unknown', 'keys': sorted(r)[:8]}


def main():
    rows = []
    for path in sorted(ROOT.iterdir()):
        if path.is_dir() and path.name.startswith(('v', 'smoke')):
            rows.append(summarize(path.name, load(path.name)))
    compare = {}
    if (CANDIDATE / 'compare.json').exists():
        compare = json.loads((CANDIDATE / 'compare.json').read_text())
        compare = {k: v for k, v in compare.items() if k in ('point_risk', 'ratio_a1p_over_slsqp', 'ratio_95')}
    out = {'runs': rows, 'candidate_v8': compare,
           'note': 'All listed runs used the legacy forward-anchored features; the current operator is '
                   'link-centred and A1+ certified, so these risks are diagnostics only. New GPU runs are NOT_RUN.'}
    (ROOT / 'audit.json').write_text(json.dumps(out, indent=2) + '\n')
    for row in rows:
        print(row.get('version'), row.get('status'), row.get('ratio'), row.get('note', ''))


if __name__ == '__main__':
    main()
