"""Predeclared independent-dataset synthetic CPU mass stress; no learned model."""
import json
from pathlib import Path
import numpy as np
from scipy.stats import beta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path('results/optimize_gaussian/cpu_close_20261119_B_timear_v1')
SPEC=dict(schema='timear-v1',hypothesis='At fixed true mass and configuration correlation, time correlation changes q-profile uncertainty and reference-offset detectability.',masses=[0.,0.5,0.8],true_mass=.5,configuration_rho=.5,offsets=[0.,0.03],n_dataset=400,n_boot=400,ncfg=80,block=5,seed=20261129,noise=.03,time_rho=.5,mc_target='Independent dataset coverage MC SE <=0.025 worst-case, <=0.0109 near 0.95 (N=400). CP95 intervals; no precision stopping.',estimand='validation-refitted amplitude; true mass known in simulation; reference mass fixed per cell',failure='nonfinite or nonpositive amplitude; count as uncovered; no dropping',reference_validity='Known truth: offset=0 valid by construction; offset=.03 misspecified. q coverage is not reference validation.')
def cp(k,n):
 return [0. if k==0 else float(beta.ppf(.025,k,n-k+1)),1. if k==n else float(beta.ppf(.975,k+1,n-k))]
def f(m):
 t=np.arange(9);return np.exp(-m*t)+np.exp(-m*(9-t))
def run():
 if OUT.exists(): raise FileExistsError(OUT)
 OUT.mkdir(parents=True)
 (OUT/'preregistration.json').write_text(json.dumps(SPEC,indent=2)+'\n')
 rows=[];rng=np.random.default_rng(SPEC['seed']);early=np.array([2,3,4,5]);late=np.array([6,7,8])
 for m in SPEC['masses']:
  for i in range(SPEC['n_dataset']):
   e=rng.normal(size=(80,9))
   for j in range(1,80):e[j]=.5*e[j-1]+np.sqrt(.75)*e[j]
   for t in range(1,9):e[:,t]=m*e[:,t-1]+np.sqrt(1-m*m)*e[:,t]
   b=(f(.5)*(1+.03*e)).reshape(16,5,9).mean(1)
   ix=rng.integers(0,16,size=(400,16));bm=b[ix].mean(1)
   for off in SPEC['offsets']:
    ref=f(.5+off);a=b.mean(0)[late]@ref[late]/(ref[late]@ref[late]);ab=bm[:,late]@ref[late]/(ref[late]@ref[late])
    bad=bool(a<=0 or np.any(ab<=0) or not np.all(np.isfinite(ab)))
    q=b.mean(0)[early]/(a*ref[early]);qb=bm[:,early]/(ab[:,None]*ref[early]);lo,hi=np.quantile(qb,[.025,.975],axis=0)
    target=f(.5)[early]/(a*ref[early]);cov=(lo<=1)&(1<=hi)
    rows.append(dict(time_rho=m,dataset=i,offset=off,failed=bad,q=q.tolist(),lo=lo.tolist(),hi=hi.tolist(),truth_profile=target.tolist(),covered_q1=cov.tolist(),all_q1=bool(cov.all() and not bad),risk=float(np.mean((q-1)**2+qb.var(0,ddof=1)))))
 summary=[]
 for m in SPEC['masses']:
  for off in SPEC['offsets']:
   rr=[r for r in rows if r['time_rho']==m and r['offset']==off];k=sum(r['all_q1'] for r in rr)
   pointcounts=np.sum([r['covered_q1'] for r in rr],axis=0)
   summary.append(dict(mass=m,offset=off,all_profile_coverage=k/400,cp95=cp(k,400),failures=sum(r['failed'] for r in rr),abstentions=0,pointwise_coverage=(pointcounts/400).tolist(),pointwise_cp95=[cp(int(x),400) for x in pointcounts]))
 paired=[]
 for m in SPEC['masses']:
  x=np.array([r['risk'] for r in rows if r['time_rho']==m and r['offset']==0]);y=np.array([r['risk'] for r in rows if r['time_rho']==m and r['offset']!=0]);delta=y-x
  boot=delta[rng.integers(0,400,size=(2000,400))].mean(1)
  paired.append(dict(mass=m,mean_risk_delta=float(delta.mean()),dataset_bootstrap_ci95=np.quantile(boot,[.025,.975]).tolist()))
 (OUT/'raw.json').write_text(json.dumps(dict(spec=SPEC,rows=rows,summary=summary,paired=paired),indent=2)+'\n')
 fig,ax=plt.subplots(1,2,figsize=(10,4))
 for off in SPEC['offsets']:
  ss=[s for s in summary if s['offset']==off];v=np.array([s['all_profile_coverage'] for s in ss]);ci=np.array([s['cp95'] for s in ss]);ax[0].errorbar(SPEC['masses'],v,yerr=[v-ci[:,0],ci[:,1]-v],fmt='o-',label=f'offset {off}')
 ax[0].set(xlabel='time noise rho',ylabel='all-four q=1 coverage');ax[0].legend()
 for p in paired:
  lo,hi=p['dataset_bootstrap_ci95'];ax[1].errorbar(p['mass'],p['mean_risk_delta'],yerr=[[p['mean_risk_delta']-lo],[hi-p['mean_risk_delta']]],fmt='o')
 ax[1].set(xlabel='time noise rho',ylabel='paired risk delta (wrong - correct)');fig.tight_layout();fig.savefig(OUT/'paired_coverage.png');plt.close(fig)
 fig,axes=plt.subplots(1,3,figsize=(12,3.5))
 for ax,m in zip(axes,SPEC['masses']):
  for off in SPEC['offsets']:
   rr=[r for r in rows if r['time_rho']==m and r['offset']==off];ax.plot(early,np.mean([r['q'] for r in rr],axis=0),'o-',label=f'offset {off}')
  ax.axhline(1,color='k',ls='--');ax.set(title=f'rho_t={m}',xlabel='t',ylabel='mean q');ax.legend()
 fig.tight_layout();fig.savefig(OUT/'q_reference_shape.png');plt.close(fig)
 txt='# Time-correlation synthetic CPU stress\n\nPreregistration was saved before dataset generation. See preregistration.json and raw.json.\n\n'
 txt+='True mass=.5, configuration AR rho=.5; time rho scanned; independent datasets, paired reference offsets on identical data and bootstrap indices. All-profile coverage is not nominal pointwise 95% coverage. Reference validity is known by construction, not inferred from coverage. Conditional target truth_profile differs from q=1 for misspecified reference.\n\n'
 txt+='|time rho|offset|all q=1 coverage|CP95|failures|\n|---|---|---|---|---|\n'
 for s in summary:txt+=f"|{s['mass']}|{s['offset']}|{s['all_profile_coverage']}|{s['cp95']}|{s['failures']}|\n"
 txt+='\nThe JSON summary legacy key mass denotes time rho, not physical mass. Physical mass is fixed at 0.5 in preregistration. No failed amplitudes were silently dropped. No abstention gate is implemented: known-wrong references remain diagnostic_only. No learned kernel, SLSQP superiority, GPU evidence, or blind physical test is claimed. Amplitude uses declared unweighted late-window fitting, not production covariance fitting; fixed mass uncertainty is excluded. Paired intervals resample independent dataset risk differences and describe this synthetic design only.\n'
 (OUT/'README.md').write_text(txt)
 print(json.dumps(summary))
if __name__=='__main__':run()
