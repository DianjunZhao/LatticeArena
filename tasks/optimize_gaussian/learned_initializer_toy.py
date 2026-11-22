"""Finite-budget heterogeneous quadratic benchmark; no smearing/physics claim."""
import json,time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path('results/optimize_gaussian/cpu_initializer_toy_v1')
SPEC=dict(seed=20261201,n_train=200,n_iid=100,n_shift=100,dim=8,budgets=[8,24,64],distribution='A=diag(linspace(1,2,8)) + s vvT, normalized random v; IID s uniform(0,8), shift s uniform(8,20). b=A tanh(2z + .3sin(3z)); z standard normal IID, shift z mean .7; box [-3,3].',initializer='ridge regression from [1,z] to training optima; training optima analytic tanh; labels free analytic, cost recorded; no test training',mc='100 independent paired instances per population; paired mean bootstrap CI95 2000 draws; worst failure MC SE .05; no adaptive sample stopping',methods=['learned_SLSQP','zero_random_SLSQP','Powell','Chebyshev'],scope='Only algorithmic finite-budget toy. Analytic labels and known SPD bounds are privileged training/design information; not learned smear.')
class Stop(Exception):pass
def instances(rng,n,shift=False):
 out=[]
 for _ in range(n):
  z=rng.normal(size=8)+(.7 if shift else 0);v=rng.normal(size=8);v/=np.linalg.norm(v);s=rng.uniform(8,20) if shift else rng.uniform(0,8);A=np.diag(np.linspace(1,2,8))+s*np.outer(v,v);star=np.tanh(2*z+.3*np.sin(3*z));out.append((z,A,A@star,star))
 return out
def solve(A,b,star,method,start,budget,rng):
 calls=0;trace=[];best=(float('inf'),np.zeros(8));t=time.perf_counter();truncated=False;success=False
 def obj(x):
  nonlocal calls,best
  if calls>=budget:raise Stop
  calls+=1;err=x-star;value=float(.5*err@A@err);trace.append(value)
  if value<best[0]:best=(value,x.copy())
  return value
 try:
  if method=='Chebyshev':
   # Chebyshev semi-iteration implemented as scheduled Richardson roots over certified spectral bounds.
   x=np.zeros(8);lo=1.;hi=float(2+np.linalg.norm(A-np.diag(np.linspace(1,2,8)),2))
   roots=(hi+lo)/2-(hi-lo)/2*np.cos(np.pi*(np.arange(budget)+.5)/budget)
   for root in roots:obj(x);x=np.clip(x-(A@x-b)/root,-3,3)
   success=True
  else:
   starts=[start] if method!='zero_random_SLSQP' else [np.zeros(8),rng.uniform(-1,1,8)]
   quotas=[budget] if len(starts)==1 else [budget//2,budget-budget//2]
   for x,q in zip(starts,quotas):
    cap=calls+q
    def capped(y):
     if calls>=cap:raise Stop
     return obj(y)
    try:
     r=minimize(capped,x,method='Powell' if method=='Powell' else 'SLSQP',jac=None if method=='Powell' else lambda y:A@y-b,bounds=[(-3,3)]*8,options={'maxiter':1000,'ftol':1e-10});success=success or bool(r.success)
    except Stop:truncated=True
 except Stop:truncated=True
 x=best[1];g=A@x-b;pg=np.linalg.norm(x-np.clip(x-g,-3,3))
 return dict(risk=best[0],calls=calls,seconds=time.perf_counter()-t,projected_gradient=float(pg),solver_success=success,budget_truncated=truncated,trace=trace)
def run():
 if OUT.exists():raise FileExistsError(OUT)
 OUT.mkdir(parents=True);(OUT/'preregistration.json').write_text(json.dumps(SPEC,indent=2))
 rng=np.random.default_rng(SPEC['seed']);t=time.perf_counter();train=instances(rng,200);X=np.array([np.r_[1,z] for z,A,b,s in train]);Y=np.array([s for z,A,b,s in train]);W=np.linalg.solve(X.T@X+1e-3*np.eye(9),X.T@Y);train_seconds=time.perf_counter()-t
 rows=[]
 for population,shift in [('iid',False),('shift',True)]:
  for i,(z,A,b,star) in enumerate(instances(rng,100,shift)):
   t=time.perf_counter();init=np.clip(np.r_[1,z]@W,-3,3);inference=time.perf_counter()-t
   for budget in SPEC['budgets']:
    for method in SPEC['methods']:
     row=solve(A,b,star,method,init if method=='learned_SLSQP' else np.zeros(8),budget,np.random.default_rng(10000+i));rows.append(dict(population=population,instance=i,budget=budget,method=method,inference_seconds=inference if method=='learned_SLSQP' else 0.,**row))
 summary=[]
 for pop in ('iid','shift'):
  for budget in SPEC['budgets']:
   learned=np.array([r['risk'] for r in rows if r['population']==pop and r['budget']==budget and r['method']=='learned_SLSQP'])
   for method in SPEC['methods'][1:]:
    other=np.array([r['risk'] for r in rows if r['population']==pop and r['budget']==budget and r['method']==method]);delta=other-learned;bs=delta[rng.integers(0,100,(2000,100))].mean(1);summary.append(dict(population=pop,budget=budget,comparator=method,paired_delta=float(delta.mean()),ci95=np.quantile(bs,[.025,.975]).tolist()))
 (OUT/'raw.json').write_text(json.dumps(dict(spec=SPEC,training_seconds=train_seconds,weights=W.tolist(),rows=rows,paired=summary),indent=2))
 fig,axes=plt.subplots(1,2,figsize=(10,4))
 for method in SPEC['methods']:
  for ax,pop in zip(axes,('iid','shift')):
   ax.plot(SPEC['budgets'],[np.mean([r['risk'] for r in rows if r['population']==pop and r['budget']==b and r['method']==method]) for b in SPEC['budgets']],'o-',label=method);ax.set(title=pop,xlabel='objective-call cap',ylabel='held-out quadratic excess risk',yscale='log');ax.legend(fontsize=6)
 fig.tight_layout();fig.savefig(OUT/'budget_risk.png');plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(10,4))
 for method in SPEC['methods']:
  rr=[r for r in rows if r['population']=='shift' and r['budget']==64 and r['method']==method];axes[0].plot(np.minimum.accumulate(rr[0]['trace']),label=method);axes[1].scatter(np.mean([r['seconds']+r['inference_seconds'] for r in rr])+(train_seconds/100 if method=='learned_SLSQP' else 0),np.mean([r['risk'] for r in rr]),label=method)
 axes[0].set(xlabel='objective call',ylabel='instance 0 best-so-far risk',yscale='log');axes[1].set(xlabel='CPU seconds incl training amortized over 100',ylabel='mean shift risk',yscale='log');axes[0].legend(fontsize=6);axes[1].legend(fontsize=6);fig.tight_layout();fig.savefig(OUT/'trajectory_cost.png');plt.close(fig)
 text='# Learned initializer finite-budget toy\n\nNot learned smear, not physical evidence. Spec saved before training. Analytic target labels make this a favorable algorithmic possibility test. Chebyshev is a realizable scheduled spectral iteration baseline with certified bounds, not a physical smearing kernel.\n\nTraining seconds: '+str(train_seconds)+'; raw rows include inference/solver seconds, calls, residuals, traces and truncations. Training amortization is training_seconds / deployment_count; figure uses 100, not an assumed universal break-even.\n\n|population|budget|comparator minus learned risk|CI95|\n|---|---|---|---|\n'
 for s in summary:text+=f"|{s['population']}|{s['budget']} {s['comparator']}|{s['paired_delta']}|{s['ci95']}|\n"
 text+='\n## Failure diagnostics\n\n|population/method (budget64)|truncated/100|residual >1e-5|mean calls|\n|---|---|---|---|\n'
 for pop in ('iid','shift'):
  for method in SPEC['methods']:
   rr=[r for r in rows if r['population']==pop and r['budget']==64 and r['method']==method];text+=f"|{pop}/{method}|{sum(r['budget_truncated'] for r in rr)}|{sum(r['projected_gradient']>1e-5 for r in rr)}|{np.mean([r['calls'] for r in rr])}|\n"
 text+='\n![Budget curves](budget_risk.png)\n\n![Trajectory and cost](trajectory_cost.png)\n\nEvery residual-large case is retained by instance ID in raw.json. Success is a solver flag, not convergence proof. Analytic SLSQP gradients are not charged as objective calls, and walltime is separately recorded. No GPU or independent physical blind test is substituted.\n';(OUT/'README.md').write_text(text)
 print('training seconds',train_seconds);print(summary[:3])
if __name__=='__main__':run()
