"""Synthetic conditional calibration of an independent bounded-block MSE score."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import platform
from pathlib import Path

import numpy as np
from scipy.stats import beta

ROOT = Path(__file__).resolve().parents[2]
SEED = 2026112107
DATASETS = 3000
COUNTS = (12, 24, 100, 400)
FAMILIES = (1, 2, 4)
THRESHOLD = 0.1
WORLDS = (
    'max_variance_null', 'shared_baseline_null', 'threshold_null',
    'practical_improvement', 'strong_improvement', 'anchor_sensitive_null',
)
ANCHORS = ('exact', 'uncertain', 'undercoverage')
DEFAULT_OUT = ROOT / 'results/pion_projection/bounded_score_calibration_20261121_v1'


def bounded_lower(b, b2, c, c2, anchor, *, n, family, lower=0., upper=1.,
                  alpha_s=.05, anchor_bound=0.):
    """Bound from per-dataset block means of mass and squared mass.

    Shape of b/b2 is (datasets,1) or (datasets,F); c/c2 is (datasets,F).
    The function validates observable ranges, not independence or anchor coverage.
    """
    if (not np.isfinite([lower, upper, alpha_s, anchor_bound]).all()
            or upper <= lower or not 0 < alpha_s < 1 or anchor_bound < 0
            or isinstance(n, bool) or int(n) != n or n < 1
            or isinstance(family, bool) or int(family) != family or family < 1):
        raise ValueError('invalid range, budget, block count, family or anchor bound')
    b, b2, c, c2 = [np.asarray(x, float) for x in (b, b2, c, c2)]
    a = np.asarray(anchor, float)
    if c.ndim != 2 or c.shape[1] != family or c2.shape != c.shape:
        raise ValueError('candidate means must have shape (datasets,family)')
    if b.shape not in (c.shape, (c.shape[0], 1)) or b2.shape != b.shape or a.shape != (c.shape[0], 1):
        raise ValueError('baseline/anchor shape mismatch')
    if not all(np.isfinite(x).all() for x in (b,b2,c,c2,a)):
        raise ValueError('nonfinite sufficient statistic')
    if any(np.any((x < lower) | (x > upper)) for x in (b,c,a)):
        raise ValueError('mass mean outside declared range')
    # E[X^2] >= E[X]^2 and E[(X-l)(u-X)] >= 0 are necessary range checks.
    for mean, second in ((b,b2),(c,c2)):
        if np.any(second < mean**2-1e-12) or np.any(second > (lower+upper)*mean-lower*upper+1e-12):
            raise ValueError('second moment inconsistent with bounded observations')
    r = upper-lower
    delta = b2-c2-2*a*(b-c)
    penalty = r*r*math.sqrt(2*math.log(family/alpha_s)/n)
    return delta-penalty-2*anchor_bound*r, delta, penalty


def cp(events, total, level=.05):
    if total == 0:
        return [None, None]
    return [float(beta.ppf(level/2, events, total-events+1)) if events else 0.,
            float(beta.ppf(1-level/2, events+1, total-events)) if events < total else 1.]


def cells():
    result=[]
    for world in WORLDS:
        for anchor in ('exact','uncertain'):
            for n in COUNTS:
                for f in FAMILIES:
                    result.append(dict(world=world, anchor=anchor, n=n, family=f, dependence='iid'))
    for n in COUNTS:
        for f in FAMILIES:
            result.append(dict(world='anchor_sensitive_null',anchor='undercoverage',n=n,family=f,dependence='iid'))
            result.append(dict(world='max_variance_null',anchor='exact',n=n,family=f,dependence='perfect'))
    return result


def generate(spec, count, seed=SEED):
    wi=WORLDS.index(spec['world']); ai=ANCHORS.index(spec['anchor'])
    args=[seed,wi,ai,spec['n'],spec['family'],int(spec['dependence']=='perfect')]
    rng=np.random.default_rng(np.random.SeedSequence(args+[0]))
    arng=np.random.default_rng(np.random.SeedSequence(args+[1]))
    n=spec['n']; f=spec['family']; world=spec['world']
    if world in ('max_variance_null','threshold_null'):
        p=.5 if world=='max_variance_null' else .55
        if spec['dependence']=='perfect':
            b=rng.binomial(1,p,size=(count,1)).astype(float)
        else:
            b=rng.binomial(n,p,size=(count,1))/n
        c=np.repeat(1-b,f,axis=1); b2=b.copy(); c2=c.copy()
        truth=0. if world=='max_variance_null' else .1
    elif world=='anchor_sensitive_null':
        b=rng.binomial(n,.25,size=(count,1))/n; b2=b.copy()
        c=np.full((count,f),.5); c2=np.full((count,f),.25); truth=0.
    else:
        pb,pc={'shared_baseline_null':(.5,.5),'practical_improvement':(.6,.4),
               'strong_improvement':(.7,.3)}[world]
        b=rng.binomial(n,pb,size=(count,1))/n; b2=b.copy()
        c=rng.binomial(n,pc,size=(count,f))/n; c2=c.copy()
        truth={'shared_baseline_null':0.,'practical_improvement':.2,'strong_improvement':.4}[world]
    if spec['anchor']=='exact':
        a=np.zeros((count,1)); bound=0.; alpha_s=.05; alpha_a=0.
    else:
        a=arng.uniform(0,.04,size=(count,1)); bound=.04; alpha_s=.04; alpha_a=.01
        if spec['anchor']=='uncertain':
            a[arng.random((count,1))<.01]=1.
        else:
            a[:]=1.
    return b,b2,c,c2,a,truth,bound,alpha_s,alpha_a


def run(out=DEFAULT_OUT, count=DATASETS):
    if count < 1:
        raise ValueError('count must be positive')
    out=Path(out); out.mkdir(parents=True, exist_ok=False)
    source=Path(__file__)
    design=ROOT/'tasks/pion_projection/bounded_score_design_review_20261121.md'
    specs=cells()
    protocol=dict(schema='bounded-block-mse-calibration-v1',status='FROZEN_BEFORE_GENERATION',
        classification='synthetic conditional calibration; physical_score=null',seed=SEED,
        datasets_per_cell=count,cells=specs,mass_range=[0.,1.],truth_mass=0.,threshold=THRESHOLD,
        seed_recipe='SeedSequence([seed,world_index,anchor_index,n,F,perfect_dependence,stream]); stream0 masses, stream1 anchor',
        true_improvements=dict(max_variance_null=0.,shared_baseline_null=0.,threshold_null=.1,
            practical_improvement=.2,strong_improvement=.4,anchor_sensitive_null=0.),
        generator='All endpoint arms are Bernoulli with b2=b,c2=c. Max-variance/threshold null c=1-b (all F identical). Shared baseline null independent candidate Bernoulli(.5). Alternatives shared baseline p=.6/.7, independent candidates p=.4/.3. Anchor-sensitive b~Bernoulli(.25), c=.5, equal true MSE=.25. Sufficient statistics generated by exact Binomial(n,p), equivalent to iid blocks. Perfect-dependence stress repeats one Bernoulli block n times.',
        anchor='Exact A=0,B=0,alphaS=.05. Uncertain A~Uniform(0,.04) with probability .99, A=1 with probability .01, B=.04,alphaA=.01,alphaS=.04; independent mass/anchor RNG. Undercoverage stress always A=1 but declares B=.04/alphaA=.01.',
        multiplicity='F=J candidates,K=1; Bonferroni within cell; max variance candidates perfectly correlated, shared-baseline candidates conditionally independent. No simultaneous across-cell theorem claim.',
        metrics='Joint coverage iff every L<=trueDelta+1e-12. Hypothetical family certificate iff any L>threshold. False certificate counts only trueDelta<=threshold; alternatives report any-candidate power. Ineligible stress has no issued certificate and all datasets abstain; numeric crossings retained as assumption-violation probes.',
        failures='Every planned dataset retained. Nonfinite/computation failure => failed, abstain, no certificate; conservatively counts as joint coverage failure in all-planned denominator. No invalid-row exclusion/top-up.',
        precision='3000/cell by default; marginal CP95 and simultaneous Bonferroni CP95 across 4 metrics x all cells. No precision gate or adaptive top-up.',
        sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (source,design)},
        environment=dict(python=platform.python_version(),numpy=np.__version__,platform=platform.platform()))
    (out/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    summary=[]
    fields=['cell','dataset','status','eligible','A','anchor_covered','b_mean','b_second','c_means','c_seconds','lower_bounds','true_delta','numeric_crossing','issued_certificate','joint_coverage','failure_reason']
    with gzip.open(out/'raw_datasets.csv.gz','wt',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for ci,spec in enumerate(specs):
            eligible=spec['anchor']!='undercoverage' and spec['dependence']=='iid'
            truth=protocol['true_improvements'][spec['world']]
            bound=0. if spec['anchor']=='exact' else .04
            alpha_s=.05 if spec['anchor']=='exact' else .04
            alpha_a=0. if spec['anchor']=='exact' else .01
            penalty=None
            try:
                b,b2,c,c2,a,truth,bound,alpha_s,alpha_a=generate(spec,count)
                low,delta,penalty=bounded_lower(b,b2,c,c2,a,n=spec['n'],family=spec['family'],alpha_s=alpha_s,anchor_bound=bound)
                crossing=np.any(low>THRESHOLD,axis=1)
                covered=np.all(low<=truth+1e-12,axis=1)
                acov=a[:,0]<=bound+1e-12
                valid=count; failed=0; errors=''
            except Exception as exc:
                valid=0;failed=count;errors=f'{type(exc).__name__}: {exc}'
                crossing=np.zeros(count,dtype=bool);covered=np.zeros(count,dtype=bool);acov=np.zeros(count,dtype=bool)
            false_events=int(crossing.sum()) if truth<=THRESHOLD+1e-12 else None
            metrics={'joint_coverage':int(covered.sum()),'anchor_coverage':int(acov.sum()),
                'numeric_family_crossing':int(crossing.sum()),'false_family_crossing':false_events}
            row=dict(cell=ci,**spec,eligible=eligible,true_delta=truth,planned=count,valid=valid,failed=failed,
                abstained=count if not eligible or failed else 0,alpha_s=alpha_s,alpha_a=alpha_a,
                total_error_budget=alpha_s+alpha_a,statistical_penalty=penalty if valid else None,
                anchor_penalty=2*bound,issued_certificates=int(crossing.sum()) if eligible and valid else 0,
                numerical_error=errors,metrics={})
            for key,ev in metrics.items():
                row['metrics'][key]=None if ev is None else dict(events=ev,denominator=count,rate=ev/count,
                    cp95=cp(ev,count),simultaneous_cp95=cp(ev,count,.05/(4*len(specs))))
            row['power']=None if truth<=THRESHOLD+1e-12 else row['metrics']['numeric_family_crossing']
            summary.append(row)
            for di in range(count):
                writer.writerow(dict(cell=ci,dataset=di,status='failed' if failed else 'valid',eligible=eligible,
                    A=float(a[di,0]) if valid else '',anchor_covered=int(acov[di]),
                    b_mean=float(b[di,0]) if valid else '',b_second=float(b2[di,0]) if valid else '',
                    c_means=json.dumps(c[di].tolist()) if valid else '',c_seconds=json.dumps(c2[di].tolist()) if valid else '',
                    lower_bounds=json.dumps(low[di].tolist()) if valid else '',true_delta=truth,
                    numeric_crossing=int(crossing[di]),issued_certificate=int(crossing[di] and eligible and valid>0),
                    joint_coverage=int(covered[di]),failure_reason=errors))
    (out/'summary.json').write_text(json.dumps(dict(classification=protocol['classification'],cells=summary),indent=2)+'\n')
    write_plot(out,summary)
    write_report(out,summary,protocol)
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}
    (out/'artifact_hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
    return summary


def write_plot(out, rows):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(2,2,figsize=(12,9),layout='constrained')
    for anchor,style in [('exact','-'),('uncertain','--')]:
        for f,color in [(1,'#0072B2'),(2,'#D55E00'),(4,'#009E73')]:
            for ax,world in [(axs[0,0],'practical_improvement'),(axs[0,1],'strong_improvement')]:
                cs=[x for x in rows if x['world']==world and x['anchor']==anchor and x['family']==f and x['eligible']]
                y=np.array([x['power']['rate'] for x in cs]);ci=np.array([x['power']['cp95'] for x in cs])
                ax.errorbar(COUNTS,y,yerr=[y-ci[:,0],ci[:,1]-y],fmt='o'+style,color=color,label=f'F={f}, {anchor}',capsize=2)
    for ax,title in zip(axs[0],['Power: true improvement 0.2 (threshold 0.1)','Power: true improvement 0.4 (threshold 0.1)']):
        ax.set(title=title,xlabel='Independent blocks n',ylabel='Any-candidate certification rate',ylim=(-.03,1.03));ax.set_xscale('log');ax.grid(alpha=.2)
    axs[0,0].legend(fontsize=8)
    for wi,world in enumerate(WORLDS):
        cs=[x for x in rows if x['world']==world and x['eligible']]
        for ai,anchor in enumerate(('exact','uncertain')):
            sub=[x for x in cs if x['anchor']==anchor]
            y=np.array([1-x['metrics']['joint_coverage']['rate'] for x in sub])
            # Plot all n/F cells, jitter only for legibility; no pooling of trials.
            xs=np.full(len(sub),wi)+(ai-.5)*.22+np.linspace(-.07,.07,len(sub))
            axs[1,0].scatter(xs,y,s=18,marker='o' if ai==0 else 'x',color='#0072B2' if ai==0 else '#D55E00')
    axs[1,0].axhline(.05,color='black',ls=':',label='Total error budget .05')
    axs[1,0].set(xticks=range(len(WORLDS)),xticklabels=['Max-var\nnull','Shared\nnull','Threshold\nnull','Improve\n0.2','Improve\n0.4','Anchor\nnull'],ylabel='Family noncoverage rate',title='Eligible cells: every dot is one n/F/anchor cell',ylim=(-.003,max(.06,1.15*max(1-x['metrics']['joint_coverage']['rate'] for x in rows if x['eligible']))));axs[1,0].legend(fontsize=8)
    for kind,label,color in [('undercoverage','Anchor interval wrong','#D55E00'),('perfect','Blocks perfectly dependent','#0072B2')]:
        for f in FAMILIES:
            cs=[x for x in rows if not x['eligible'] and x['family']==f and (x['anchor']==kind or x['dependence']==kind)]
            y=np.array([x['metrics']['numeric_family_crossing']['rate'] for x in cs]);ci=np.array([x['metrics']['numeric_family_crossing']['cp95'] for x in cs])
            axs[1,1].errorbar(COUNTS,y,yerr=[y-ci[:,0],ci[:,1]-y],fmt='o-',color=color,alpha=.45+.13*f,label=f'{label}, F={f}',capsize=2)
    axs[1,1].axhline(.05,color='black',ls=':');axs[1,1].set(xlabel='Nominal blocks n',ylabel='Hypothetical false-certificate crossing',ylim=(-.03,1.03),title='Invalid assumptions: diagnostic only; all abstain');axs[1,1].set_xscale('log');axs[1,1].legend(fontsize=7)
    fig.suptitle('Bounded paired-block MSE: conditional synthetic calibration; no physical score',fontsize=13)
    fig.savefig(out/'calibration.png',dpi=180);plt.close(fig)


def write_report(out,rows,protocol):
    eligible=[x for x in rows if x['eligible']]
    worst=max(eligible,key=lambda x:1-x['metrics']['joint_coverage']['rate'])
    lines=['# Bounded block-MSE score: synthetic conditional calibration','',
        '**COMPLETE / SYNTHETIC_ONLY. `physical_score=null`.** The researcher accepted this distinct block-MSE estimand for exploration; no physical Pion reference, anchor or block-independence claim is established. No GPU/QUDA or E/validation/holdout data used.','',
        '## Formula audit','',
        'With masses in [0,1], d=(b−A)²−(c−A)²∈[−1,1]. Conditional on independent A, Δtrue=E[d|A]+2(A−m*)E[b−c]. Anchor coverage |A−m*|≤B gives Δtrue≥E[d|A]−2B. Hoeffding on width 2 gives P(E[d|A]<mean(d)−sqrt(2log(F/αS)/n))≤αS/F. Union over F, then add anchor failure αA. Result: joint noncoverage≤αS+αA=.05. F counts fixed candidates here (K=1), not datasets; candidates may be correlated.','',
        '## Frozen experiment','',
        f'{len(rows)} cells × {protocol["datasets_per_cell"]} independent outer datasets. n=12/24/100/400; F=1/2/4; δ*=0.1. [protocol.json](protocol.json) was written before generation and binds source/design hashes, seeds and environment. The whole cell stream is deterministic; source hashes must match for replay. New output paths refuse existing directories.','',
        'Endpoint Bernoulli masses produce exact sufficient statistics by binomial draws. In max-variance null, b=X,c=1−X,p=.5,A=0 gives d=±1 and Var(d)=1, saturating the variance bound for [−1,1]; F candidates are identical in this world. Shared-baseline null and alternatives use independent candidate Bernoulli arms with a common baseline. Threshold null has Δ=.1, exactly the practical threshold. Anchor-sensitive null has b~Bernoulli(.25),c=.5: equal true MSE=.25 but different mean masses. This is a new bounded-mass/squared-loss experiment; it does not repeat the older unbounded rare-tail direct-delta grid.','',
        'Exact anchor: A=0,B=0,αS=.05,αA=0. Valid uncertain anchor: independent A~U(0,.04) with probability .99 and A=1 with probability .01, B=.04,αS=.04,αA=.01. Its coverage is exactly .99. Undercoverage stress always A=1 while still declaring B=.04; dependence stress repeats one Bernoulli draw n times while using nominal n. Both stresses intentionally violate the theorem: every dataset is ineligible/abstained; crossings are hypothetical diagnostics only.','',
        '## Results and denominators','',
        f'Planned {sum(x["planned"] for x in rows)}; valid {sum(x["valid"] for x in rows)}; failed {sum(x["failed"] for x in rows)}; abstained {sum(x["abstained"] for x in rows)} (all assumption-violation stress datasets). Eligible cells: {len(eligible)}. Failed rows, if any, count as noncertification and conservative coverage failure in the all-planned denominator. A valid numerical stress row does not become an eligible inference.','',
        f'Largest observed eligible family noncoverage: {1-worst["metrics"]["joint_coverage"]["rate"]:.5f} in {worst["world"]}, {worst["anchor"]}, n={worst["n"]}, F={worst["family"]}. Every cell below retains its own MC interval; rates are not pooled.','',
        'All outcome events are family-level per independent dataset: joint coverage means every lower bound covers its true Δ; false certification means at least one true Δ≤δ* has L>δ*. Power is any-candidate certification when all candidates truly improve beyond δ*. CP95 is marginal exact binomial MC uncertainty, not physical coverage. summary.json additionally supplies simultaneous Bonferroni CP95 across four metrics × all cells. Noncoverage and false certification are distinct metrics.','',
        '![Calibration](calibration.png)','',
        'The low eligible error rates must be read with power and block count. A conservative bound can certify few practical improvements with n=12/24; a small error count alone is not success. The stress plot shows why oracle mass bounds cannot repair an invalid anchor or nonexistent independent blocks.','',
        '| World | Anchor | Dependence | n | F | planned/valid/failed/abstained | Joint coverage [CP95] | False crossing [CP95] | Power [CP95] |','|---|---|---|---:|---:|---|---|---|---|']
    def fmt(m):
        if m is None:return '—'
        return f'{m["events"]}/{m["denominator"]}={m["rate"]:.4f} [{m["cp95"][0]:.4f},{m["cp95"][1]:.4f}]'
    for x in rows:
        lines.append(f'| {x["world"]} | {x["anchor"]} | {x["dependence"]} | {x["n"]} | {x["family"]} | {x["planned"]}/{x["valid"]}/{x["failed"]}/{x["abstained"]} | {fmt(x["metrics"]["joint_coverage"])} | {fmt(x["metrics"]["false_family_crossing"])} | {fmt(x["power"])} |')
    lines.extend(['','## Raw evidence and limits','',
        '[raw_datasets.csv.gz](raw_datasets.csv.gz) contains every planned dataset: cell/dataset IDs, baseline and candidate first/second moments, anchor, per-candidate lower bounds, truth, coverage, crossing, eligibility and issued-certificate/failed status. These are sufficient statistics for exactly recomputing the score; the binomial/anchor seed recipe regenerates the synthetic inputs. [summary.json](summary.json) contains counts and intervals per cell; [artifact_hashes.json](artifact_hashes.json) binds artifacts.','',
        'These results check a conditional bound in finitely many declared DGPs, not exhaustive calibration, proof of sharpness or validation of physical block formation. The theorem relies on the predeclared range and true block independence, plus independent anchor coverage including model/systematic bias. Current Pion D blocks and failed reference do not meet that contract. Existing single-cosh FAIL and M2 NOT_READY remain, E/new validation/shared holdout stay closed. Next physical work must establish bounds/clipping policy, block-estimator interpretation, independent block provenance and a defensible anchor with systematic-error coverage before any physical scoring.','',
        'Reproduce into a fresh directory: `python3 -B -m tasks.pion_projection.bounded_score_calibration --output NEW_DIRECTORY`. This does not run measurement or open data.'])
    (out/'README.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=DEFAULT_OUT)
    parser.add_argument('--datasets',type=int,default=DATASETS);args=parser.parse_args()
    result=run(args.output,args.datasets)
    print(json.dumps(dict(output=str(args.output),cells=len(result),planned=sum(x['planned'] for x in result),failed=sum(x['failed'] for x in result))))
