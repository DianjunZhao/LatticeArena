"""402-dataset joint-endpoint extension; synthetic oracle only."""
import json
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import beta

from core.io import digest
from . import p4_controls as base

ENDPOINTS = {
    'legacy_both_pass': 'both estimator legacy spread gates pass',
    'legacy_any_pass': 'at least one estimator legacy spread gate passes',
    'legacy_false_pass': 'biased control AND both legacy gates pass (null: event false by definition)',
    'oracle_any_abstain': 'at least one oracle gate abstains',
    'oracle_both_abstain': 'both oracle gates abstain',
    'false_improvement': 'both oracle gates pass AND ratio CI lower bound > 1; equal-quality labels in both controls',
    'ratio_excludes_one': 'ratio CI excludes 1 in either direction',
    'any_failure': 'any invalid numeric/gate path; exceptions are retained as failures',
}


def cp(k,n):
    return [float(beta.ppf(.025,k,n-k+1)) if k else 0.,
            float(beta.ppf(.975,k+1,n-k)) if k<n else 1.]


def endpoints(row):
    gates=row['gates'];passes=[g['legacy_spread_gate'] for g in gates]
    abstain=[g['status']=='ABSTAIN' for g in gates]
    return {'legacy_both_pass':all(passes),'legacy_any_pass':any(passes),
            'legacy_false_pass':row['control']=='two_state_common_bias' and all(passes),
            'oracle_any_abstain':any(abstain),'oracle_both_abstain':all(abstain),
            'false_improvement':row['improvement'],
            'ratio_excludes_one':not row['ci95'][0]<=1<=row['ci95'][1],
            'any_failure':any(g['status']=='FAIL' for g in gates)}


def main():
    out=Path('results/wilson_loop/audit_20261119_p4_controls_n402')
    out.mkdir(parents=True,exist_ok=False)
    plan=dict(base.PLAN,version='p4-joint-endpoints-n402-v1',seed=2026111902,
              datasets_per_control=402,budget='2 x 402 independent datasets; 100 outer x 100 inner; no tuning',
              endpoints=ENDPOINTS,interval='pointwise two-sided exact Clopper-Pearson 95%; denominator402',
              exception_policy='abort execution preserving protocol; no silent deletion or replacement')
    plan['source_hashes']={p:digest(p) for p in ['tasks/wilson_loop/p4_controls.py',__file__]}
    (out/'protocol.json').write_text(json.dumps(plan,indent=2)+'\n')
    base.PLAN=plan
    rows=base.run()
    summaries={};patterns={}
    for control in ('null','two_state_common_bias'):
        group=[r for r in rows if r['control']==control]
        summaries[control]={}
        patterns[control]=dict(Counter('/'.join(g['status'] for g in r['gates']) for r in group))
        for event in ENDPOINTS:
            k=sum(endpoints(r)[event] for r in group)
            summaries[control][event]={'k':k,'n':len(group),'rate':k/len(group),'cp95':cp(k,len(group))}
    for row in rows:row['joint_endpoints']=endpoints(row)
    (out/'raw.json').write_text(json.dumps({'scope':'synthetic_oracle','physical_status':'NOT_RUN','rows':rows},indent=2)+'\n')
    (out/'summary.json').write_text(json.dumps({'endpoints':summaries,'joint_gate_patterns':patterns},indent=2)+'\n')
    examples=[]
    for control in summaries:
        group=[r for r in rows if r['control']==control]
        for criterion in ('false_improvement','ratio_excludes_one','oracle_any_abstain','any_failure'):
            chosen=next((r for r in group if r['joint_endpoints'][criterion]),None)
            examples.append({'control':control,'criterion':criterion,'example':chosen,
                             'note':'no such case observed' if chosen is None else 'first occurrence, not hand-selected best'})
    (out/'examples.json').write_text(json.dumps(examples,indent=2)+'\n')
    fig,axes=plt.subplots(1,2,figsize=(13,5),sharey=True)
    names=list(ENDPOINTS)
    for ax,(control,values) in zip(axes,summaries.items()):
        rates=np.array([values[k]['rate'] for k in names]);ci=np.array([values[k]['cp95'] for k in names])
        ax.errorbar(np.arange(len(names)),rates,yerr=np.maximum(0,np.stack([rates-ci[:,0],ci[:,1]-rates])),fmt='o',capsize=3)
        ax.set_xticks(np.arange(len(names)),names,rotation=65,ha='right',fontsize=8)
        ax.set(title=control,ylabel='dataset-level event probability; CP95',ylim=(-.03,1.03));ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(out/'joint_rates.png',dpi=150);plt.close(fig)
    table='\n'.join('| '+control+' | '+event+' | '+str(v['k'])+'/402 | %.5f [%.5f, %.5f] |'%(v['rate'],*v['cp95']) for control,events in summaries.items() for event,v in events.items())
    (out/'README.md').write_text('''# P4 N=402 independent synthetic datasets per control

Frozen protocol.json was written before simulation; seed2026111902; 80 configurations/16 paired blocks per dataset,100 outer×100 inner. Two equal-quality estimator labels share80% noise variance; they are not physical stout/APE measurements. Null c1=0; common-bias c1=.5, E0=.5/E1=1.2. Gate thresholds and all event definitions are in protocol.json; no data-dependent tuning. raw.json retains block loops, both decisions, ratio draws/intervals and joint events. summary.json retains paired decision patterns. No old N=40 artifact overwritten.

Statistical unit is one independent dataset. Two within-dataset estimator decisions are one joint outcome, never804 independent trials. CP95 is exact pointwise binomial uncertainty across402 datasets, not a simultaneous family guarantee. Independent synthetic draws underlie this assumption; bootstrap draws do not enlarge denominator. Legacy false-pass is defined only for biased control (structural zero under null); use legacy_both_pass to inspect null acceptance. False improvement means a directional improvement declaration between exchangeable equal-quality labels after both oracle gates pass.

| control | joint event | count | rate [CP95] |
|---|---|---|---|
'''+table+'''

![Joint dataset rates](joint_rates.png)

Representative first occurrences, including ratio anomalies and false improvements if present, are in examples.json. Missing categories explicitly say no case observed. Any thrown numeric exception aborts this runner rather than silently deleting/replacing a dataset; this completed run had no exception. Zero failure here is not universal robustness. Common-bias abstention uses exact E0 supplied by the synthetic world, not an inferred real-data anchor. Null abstention is an oracle-gate false rejection; biased legacy acceptance exposes a spread-gate blind spot. The CP intervals quantify Monte Carlo event uncertainty only, not physics significance, actual gate certification or transferable production error control.

Physical/HMC/F4/GPU/MPI status remains NOT_RUN. These are synthetic loop controls, not gauge fields or stout/APE ensemble comparisons. Prior small-gauge kernel certification remains separate; real anchor availability, frozen candidate budget, production receipts, independent gauge samples and autocorrelation checks remain prerequisites. No production receipt generated or physical score issued. Reproduce into a fresh directory by changing only output path before rerun; the runner refuses an existing directory.
''')
    print(json.dumps(summaries,indent=2))


if __name__=='__main__':main()
