"""Predeclared dataset-level expansion of the matched CPU convergence diagnostic."""
import json,hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from . import cpu_convergence_diagnostic as d
OUT=Path('results/optimize_gaussian/cpu_close_20261119_C_expanded_v1')
SPEC=dict(seeds=list(range(100,120)),epsilon=[0.,.1],budgets=[25,100,400],starts=3,bootstrap_dataset_draws=4000,mc_target='N=20 independent datasets: paired mean CI via dataset bootstrap; failure proportion worst-case SE <=0.112. No claim of 0.05 precision; no adaptive stopping.',scope='Synthetic operator/optimizer diagnostic. B explicitly includes teacher direction; oracle near zero is constructive, not learned advantage.',selection='Best training objective across common starts; held-out error never selects a start.',failure='Report budget exhaustion, solver non-success excluding exhaustion, and success with projected-gradient >1e-5 separately.')
def run():
 if OUT.exists():raise FileExistsError(OUT)
 OUT.mkdir(parents=True)
 spec={**SPEC,'code_sha256':{str(Path(x).name):hashlib.sha256(Path(x).read_bytes()).hexdigest() for x in (__file__,d.__file__)}}
 (OUT/'preregistration.json').write_text(json.dumps(spec,indent=2)+'\n')
 d.BUDGETS=tuple(SPEC['budgets']);d.N_STARTS=SPEC['starts']
 rows=[]
 for seed in SPEC['seeds']:
  data=d._dataset(seed)
  for eps in SPEC['epsilon']:
   rows.append(d._diagnose_cell(seed,eps,*data))
  print('finished seed',seed,flush=True)
 rng=np.random.default_rng(20261130);paired=[];counts={};conds=[]
 for eps in SPEC['epsilon']:
  for klass in d.CLASSES:
   cells=[r['classes'][klass] for r in rows if r['epsilon']==eps]
   for c in cells:conds.append(dict(epsilon=eps,klass=klass,rank=c['rank_realified_design'],n=c['n_features'],condition=c['condition_number_scaled']))
   for j,budget in enumerate(SPEC['budgets']):
    a=np.array([c['methods']['SLSQP'][j]['best']['test_error'] for c in cells]);b=np.array([c['methods']['Powell'][j]['best']['test_error'] for c in cells]);delta=b-a
    boot=delta[rng.integers(0,len(delta),size=(4000,len(delta)))].mean(1)
    paired.append(dict(epsilon=eps,klass=klass,budget=budget,mean_delta_powell_minus_slsqp=float(delta.mean()),ci95=np.quantile(boot,[.025,.975]).tolist()))
 failures=[]
 for row in rows:
  for klass,c in row['classes'].items():
   for method,traces in c['methods'].items():
    for trace in traces:
     for i,t in enumerate(trace['all_starts']):
      flags=[]
      if t['budget_exhausted']:flags.append('budget_exhausted')
      elif not t['solver_success']:flags.append('solver_non_success')
      if t['solver_success'] and t['projected_gradient_norm_scaled_variables']>1e-5:flags.append('success_large_residual')
      if flags:failures.append(dict(seed=row['seed'],epsilon=row['epsilon'],klass=klass,method=method,budget=trace['budget_per_start'],start=i,flags=flags,residual=t['projected_gradient_norm_scaled_variables']))
 for flag in ('budget_exhausted','solver_non_success','success_large_residual'):counts[flag]=sum(flag in f['flags'] for f in failures)
 result=dict(spec=spec,rows=rows,paired=paired,conditions=conds,counts=counts,flagged_trials=failures)
 (OUT/'raw.json').write_text(json.dumps(result,indent=2)+'\n')
 fig,axes=plt.subplots(1,2,figsize=(10,4))
 for klass in d.CLASSES:
  cc=[c for c in conds if c['klass']==klass and c['epsilon']==.1];axes[0].plot(SPEC['seeds'],[c['condition'] for c in cc],'o-',label=klass)
  for method in d.METHODS:
   yy=[]
   for j in range(3):yy.append(np.mean([r['classes'][klass]['methods'][method][j]['best']['test_error'] for r in rows if r['epsilon']==.1]))
   axes[1].plot(SPEC['budgets'],yy,'o-',label=f'{klass}/{method}')
 axes[0].set(xlabel='independent dataset seed',ylabel='scaled design condition');axes[1].set(xlabel='objective budget/start',ylabel='mean held-out error',yscale='log');axes[0].legend();axes[1].legend(fontsize=7);fig.tight_layout();fig.savefig(OUT/'condition_budget.png');plt.close(fig)
 fig,ax=plt.subplots(figsize=(8,4));ss=[p for p in paired if p['epsilon']==.1]
 for i,p in enumerate(ss):
  lo,hi=p['ci95'];v=p['mean_delta_powell_minus_slsqp'];ax.errorbar(i,v,yerr=[[v-lo],[hi-v]],fmt='o')
 ax.set_xticks(range(len(ss)),[f"{p['klass']}\n{p['budget']}" for p in ss]);ax.axhline(0,color='k',ls='--');ax.set_ylabel('paired test error Powell - SLSQP; dataset bootstrap CI95');fig.tight_layout();fig.savefig(OUT/'paired_intervals.png');plt.close(fig)
 text='# Expanded independent-link convergence diagnostic\n\nSee preregistration.json (written before generation), raw.json and both figures. Twenty new independent datasets; original seeds 0–2 untouched. Three common starts; budgets 25/100/400 objective calls per start. Analytical SLSQP gradients are not charged as objective calls, so this is objective-budget matching, not wall-time matching.\n\n'
 text+=f'Flags across all budgets/starts (repeated trajectories are not independent trials): {counts}. Full rank: {sum(c["rank"]==c["n"] for c in conds)}/{len(conds)}.\n\n'
 text+='|epsilon|class|budget|paired delta|dataset CI95|\n|---|---|---|---|---|\n'
 for p in paired:text+=f"|{p['epsilon']}|{p['klass']}|{p['budget']}|{p['mean_delta_powell_minus_slsqp']:.6g}|{p['ci95']}|\n"
 text+='\nAll flagged seed/start/residual cases are explicitly listed in raw.json. Budget exhaustion means truncation, not intrinsic optimizer failure. No learned W, production links, physical risk or learned-smear superiority is tested. B oracle near-zero error is constructive teacher inclusion. N=20 is a finite descriptive expansion, not high-precision failure-rate calibration.\n'
 (OUT/'README.md').write_text(text)
 print(counts,flush=True)
if __name__=='__main__':run()
