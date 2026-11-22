"""CPU synthetic cross-link initializer; learned coefficients are not learned smearing."""
import json,time
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from . import p3_crosslink_fair as f
from . import cpu_convergence_diagnostic as d
OUT=Path('results/optimize_gaussian/cpu_operator_initializer_v1')
SPEC=dict(train_seeds=list(range(300,340)),validation_seeds=list(range(400,410)),test_seeds=list(range(500,540)),shift_seeds=list(range(600,640)),budgets=[25,100,400],summaries='normalized traces H^1..H^4 and Frobenius B/H ratio, computed on fitting links only; gauge invariant under conjugation',distribution='epsilon uniform(.01,.1) IID; shift epsilon uniform(.15,.3); independent gauge links/probes, same fair generator',labels='actual SLSQP optimized coefficients, zero start, cap 400 objective calls; no oracle labels',mc='40 independent held-out datasets/population; paired bootstrap 2000 draws, worst proportion MC SE .079; descriptive CI, no adaptive stopping',scope='CPU synthetic operator only; B explicitly includes teacher component. Not learned smear or physical advantage.')
def instance(seed,shift=False):
 ops,tests,pr,pt=d._dataset(seed);rng=np.random.default_rng(seed+9000);eps=rng.uniform(.15,.3) if shift else rng.uniform(.01,.1)
 X,Y=f.design_ensembles(ops,eps,True,pr);Xt,Yt=f.design_ensembles(tests,eps,True,pt)
 # Matrices transform by unitary conjugation; traces and Frobenius norms are invariant.
 features=[]
 for h,b in ops:
  features.append([np.trace(np.linalg.matrix_power(h,k)).real/h.shape[0] for k in range(1,5)]+[np.linalg.norm(b)/np.linalg.norm(h)])
 return X,Y,Xt,Yt,np.r_[1,np.mean(features,axis=0)],eps
def trial(X,Y,Xt,Yt,start,budget):
 sc=np.sqrt(np.mean(abs(X)**2,axis=0));sc=np.where(sc>1e-12,sc,1);xr,yr=f._real_system(X/sc,Y)
 r=d._solver_trial(X,Y,'SLSQP',start*sc,budget,sc,xr,yr,max(float(yr@yr),np.finfo(float).tiny));c=np.array(r['coefficients']);r['heldout_error']=float(np.linalg.norm(Xt@c-Yt)/np.linalg.norm(Yt));return r
def run():
 if OUT.exists():raise FileExistsError(OUT)
 OUT.mkdir(parents=True);(OUT/'preregistration.json').write_text(json.dumps(SPEC,indent=2))
 t=time.perf_counter();xx=[];yy=[]
 for seed in SPEC['train_seeds']:
  X,Y,Xt,Yt,z,e=instance(seed);r=trial(X,Y,Xt,Yt,np.zeros(X.shape[1]),400);xx.append(z);yy.append(r['coefficients'])
 xx=np.array(xx);yy=np.array(yy);mu=xx.mean(0);sd=xx.std(0);mu[0]=0;sd[0]=1;sd=np.maximum(sd,1e-12);zz=(xx-mu)/sd
 models={lam:np.linalg.solve(zz.T@zz+lam*np.eye(6),zz.T@yy) for lam in (.01,1.,100.)}
 val=[]
 for lam,W in models.items():
  risks=[]
  for seed in SPEC['validation_seeds']:
   X,Y,Xt,Yt,z,e=instance(seed);init=np.clip((z-mu)/sd@W,-5,5);risks.append(trial(X,Y,Xt,Yt,init,25)['relative_train_objective'])
  val.append((float(np.mean(risks)),lam))
 lam=min(val)[1];W=models[lam];training=time.perf_counter()-t;rows=[]
 for pop,seeds in [('iid',SPEC['test_seeds']),('shift',SPEC['shift_seeds'])]:
  for seed in seeds:
   X,Y,Xt,Yt,z,e=instance(seed,pop=='shift');t=time.perf_counter();init=np.clip((z-mu)/sd@W,-5,5);infer=time.perf_counter()-t
   for budget in SPEC['budgets']:
    for method in ('learned','zero_random','spectral'):
     t=time.perf_counter()
     if method=='learned':r=trial(X,Y,Xt,Yt,init,budget)
     elif method=='zero_random':
      rng=np.random.default_rng(seed);rs=[trial(X,Y,Xt,Yt,s,budget//2) for s in (np.zeros(10),rng.uniform(-1,1,10))];r=min(rs,key=lambda r:r['relative_train_objective']);r['objective_calls']=sum(a['objective_calls'] for a in rs)
     else:
      # Strong same-data spectral polynomial fit, no teacher extra features.
      a,b=f._real_system(X[:,:8],Y);c=np.linalg.lstsq(a,b,rcond=None)[0];c=np.clip(c,-5,5);r=dict(heldout_error=float(np.linalg.norm(Xt[:,:8]@c-Yt)/np.linalg.norm(Yt)),objective_calls=1,budget_exhausted=False,solver_success=True,projected_gradient_norm_scaled_variables=None)
     rows.append(dict(population=pop,seed=seed,epsilon=e,budget=budget,method=method,wall_seconds=time.perf_counter()-t,inference_seconds=infer if method=='learned' else 0,**r))
 rng=np.random.default_rng(81);paired=[]
 for pop in ('iid','shift'):
  for budget in SPEC['budgets']:
   for method in ('zero_random','spectral'):
    a=np.array([r['heldout_error'] for r in rows if r['population']==pop and r['budget']==budget and r['method']==method]);b=np.array([r['heldout_error'] for r in rows if r['population']==pop and r['budget']==budget and r['method']=='learned']);v=a-b;bs=v[rng.integers(0,40,(2000,40))].mean(1);paired.append(dict(population=pop,budget=budget,comparator=method,delta=float(v.mean()),ci95=np.quantile(bs,[.025,.975]).tolist()))
 (OUT/'raw.json').write_text(json.dumps(dict(spec=SPEC,selected_ridge=lam,validation=val,training_and_selection_seconds=training,weights=W.tolist(),feature_mean=mu.tolist(),feature_scale=sd.tolist(),rows=rows,paired=paired),indent=2))
 fig,axes=plt.subplots(1,2,figsize=(10,4))
 for method in ('learned','zero_random','spectral'):
  for ax,pop in zip(axes,('iid','shift')):
   rr=[r for r in rows if r['population']==pop and r['method']==method];ax.plot(SPEC['budgets'],[np.mean([r['heldout_error'] for r in rr if r['budget']==b]) for b in SPEC['budgets']],'o-',label=method);ax.set(title=pop,xlabel='objective-call cap',ylabel='held-out operator error',yscale='log');ax.legend()
 fig.tight_layout();fig.savefig(OUT/'budget_cost.png');plt.close(fig)
 fig,ax=plt.subplots(figsize=(10,4))
 for i,p in enumerate(paired):
  lo,hi=p['ci95'];v=p['delta'];ax.errorbar(i,v,yerr=[[v-lo],[hi-v]],fmt='o')
 ax.axhline(0,color='k');ax.set(xlabel='population × budget × comparator (raw JSON order)',ylabel='paired comparator minus learned error');fig.tight_layout();fig.savefig(OUT/'paired_intervals.png');plt.close(fig)
 text='# Cross-link initializer CPU synthetic diagnostic\n\nPreregistered train/validation/test/shift seeds and summaries. Labels come from actual bounded SLSQP, not analytic coefficients. Summary computation and label/search/validation training time are included in training_and_selection_seconds; deployment amortization is that value/N. Test walltime and inference are separate in raw.json.\n\nSpectral baseline is a feasible clipped real least-squares polynomial, no extra teacher directions. It is a strong direct baseline but not an optimally constrained Chebyshev implementation. Initializer compares same operator class to zero/random; spectral has a different class. Calls do not account for analytic-gradient or direct-linear-algebra costs, so walltime must also be read.\n\n![Budget](budget_cost.png)\n\n![Paired](paired_intervals.png)\n\n'
 for p in paired:text+=str(p)+'\n\n'
 text+='## Worst cases and truncations\n\n'
 for method in ('learned','zero_random','spectral'):
  rr=[r for r in rows if r['method']==method];r=max(rr,key=lambda r:r['heldout_error']);text+=f"{method}: worst {r['population']} seed={r['seed']} budget={r['budget']}, error={r['heldout_error']}; truncations={sum(x['budget_exhausted'] for x in rr)}.\n\n"
 text+='B contains the teacher component explicitly, so low error is constructive and not a learned physical kernel result. Summaries never use test links; shift changes epsilon only and does not cover all gauge-distribution shifts. Paired intervals are descriptive independent-dataset bootstrap, unadjusted for multiplicity.\n';(OUT/'README.md').write_text(text)
 print('done',training,lam)
if __name__=='__main__':run()
