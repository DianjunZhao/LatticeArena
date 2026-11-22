"""Frozen synthetic controls for a future stout-vs-APE comparison, not kernels."""
import json
from pathlib import Path

import numpy as np

from .statistics import blocks, bootstrap_indices, risk

PLAN = {'version': 'p4-synthetic-controls-v1', 'seed': 20261119,
        'datasets_per_control': 40, 'configurations': 80, 'block_length': 5,
        'outer': 100, 'inner': 100, 'windows': [[4, 5, 6], [4, 5, 6, 7], [5, 6, 7, 8]],
        't_values': [4, 5, 6, 7, 8], 'E0': 0.5, 'E1': 1.2,
        'noise': 0.005, 'common_noise_fraction': 0.8,
        'spread_limit': 0.05, 'anchor_z_limit': 3.0,
        'hypotheses': 'null: exchangeable equal-noise estimators; bias: same two-state contamination',
        'decision': 'invalid=>FAIL; spread failure or independent synthetic anchor |z|>3=>ABSTAIN; else PASS',
        'comparison': 'only both PASS and percentile ratio lower bound>1 claims improvement',
        'unit': 'independent synthetic dataset; paired configuration vectors then blocks, not bootstrap draws',
        'budget': '2 controls x 40 datasets; fixed 100 outer x 100 inner; no tuning or early selection'}


def run():
    rng = np.random.default_rng(PLAN['seed'])
    t = np.asarray(PLAN['t_values'])
    rows = []
    for control, c1 in [('null', 0.0), ('two_state_common_bias', 0.5)]:
        signal = np.exp(-.5*t) + c1*np.exp(-1.2*t)
        for dataset in range(PLAN['datasets_per_control']):
            common = rng.normal(size=(80, 1, 5))
            data = []
            for _ in range(2):
                noise = np.sqrt(.8)*common + np.sqrt(.2)*rng.normal(size=common.shape)
                data.append(signal[None,None,:]*(1+.005*noise))
            b = np.stack([blocks(x,5) for x in data],axis=1)
            idx = bootstrap_indices(16,100,PLAN['seed']+dataset)
            results = [risk(b[:,k],idx,PLAN['windows'],PLAN['t_values'],[.5]) for k in range(2)]
            gates = []
            for result in results:
                z = abs(result['v'][0]-.5)/result['se'][0]
                spread = result['spread'][0]/abs(result['v'][0])
                gates.append({'legacy_spread_gate':spread<=.05, 'anchor_z':z,
                              'status':'PASS' if spread<=.05 and z<=3 else 'ABSTAIN'})
            ratios=[]
            for _ in range(100):
                select=rng.integers(0,16,16)
                rr=[risk(b[select,k],idx,PLAN['windows'],PLAN['t_values'],[.5])['risk'] for k in range(2)]
                ratios.append(rr[0]/rr[1])
            ci=np.quantile(ratios,[.025,.975]).tolist()
            rows.append({'control':control,'dataset':dataset,'results':results,'gates':gates,
                         'raw_block_loops':b.tolist(),'outer_ratio_draws':ratios,'ci95':ci,
                         'improvement':all(g['status']=='PASS' for g in gates) and ci[0]>1})
    return rows


def main():
    out=Path('results/wilson_loop/audit_20261119_p4_controls')
    out.mkdir(parents=True,exist_ok=False)
    (out/'protocol.json').write_text(json.dumps(PLAN,indent=2)+'\n')
    rows=run()
    summary={}
    for control in ('null','two_state_common_bias'):
        group=[r for r in rows if r['control']==control]
        statuses=[g['status'] for r in group for g in r['gates']]
        summary[control]={'datasets':len(group),'gate_decisions':len(statuses),
                          **{s:statuses.count(s) for s in ('PASS','ABSTAIN','FAIL')},
                          'legacy_pass':sum(g['legacy_spread_gate'] for r in group for g in r['gates']),
                          'improvement_datasets':sum(r['improvement'] for r in group),
                          'ratio_interval_contains_one':sum(r['ci95'][0]<=1<=r['ci95'][1] for r in group)}
    (out/'raw.json').write_text(json.dumps({'scope':'synthetic_CPU','physical_status':'NOT_RUN',
                                         'plan':PLAN,'rows':rows,'summary':summary},indent=2)+'\n')
    table='\n'.join('| '+c+' | '+' | '.join(str(s[k]) for k in ('PASS','ABSTAIN','FAIL','legacy_pass','improvement_datasets','ratio_interval_contains_one'))+' |' for c,s in summary.items())
    (out/'README.md').write_text('''# P4 synthetic gate controls (not stout or APE measurements)

Protocol was written before simulation to protocol.json. Budget: 40 independent datasets per control, 80 synthetic configurations/16 blocks each, two paired estimator labels; 100 outer ×100 inner. No hyperparameter search. raw.json retains block loops, potentials/SE/spread and every ratio draw. Seed is fixed; all numbers are synthetic_CPU, physical measurement NOT_RUN.

Hypothesis: exchangeable equal-noise labels should not show systematic improvement; common two-state contamination should cause abstention even when legacy spread passes. The two labels are **not implemented stout/APE operators**. The independent synthetic anchor E0=.5 is known exactly by construction and unavailable in real production. Anchor quality here is therefore an oracle stress control, not a certified production gate.

| control | PASS | ABSTAIN | FAIL | legacy PASS | improvement datasets | intervals containing 1 |
|---|---:|---:|---:|---:|---:|---:|
'''+table+'''

Gate counts have denominator80 (two correlated label decisions per dataset), comparison counts denominator40. Do not treat bootstrap draws or the80 decisions as independent experiments. FAIL means invalid input; these finite Gaussian-noise realizations produced no invalid paths, so zero FAIL is not a general robustness proof. ABSTAIN is an expected successful detection in the bias control. Per-dataset intervals and failure/abstention examples are retained in raw.json. Rates from40 datasets have substantial Monte Carlo uncertainty; no claim of calibrated physical significance or general coverage.

Physical stop: no stout physical kernel or real gauge/HMC observable was generated. Synthetic loops cannot establish gauge covariance, overlap gains or cost of stout. Before GPU/production comparison require a frozen stout definition, CPU small-gauge covariance/unitarity/time-locality checks, actual F4 receipts, independent validation samples and external matched search/time budget. The present artifact closes only null/common-bias statistical preflight. If the real E0 anchor is unavailable, this oracle gate cannot be transferred; retain conditional-only/abstain instead of inventing an anchor. No new physics measurement started.
''')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
