"""Full production reference-gate MC; diagnostic only, no physical scores.

Gate statements are extracted verbatim from develop, not reimplemented. The
receipt records their source/hash. This intentionally fails if delimiters drift.
"""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import numpy as np
from scipy.stats import beta
from . import experiment
from .common import protocol
from .reference import make_reference
from .statistics import blocks, fold, bootstrap_indices, shape

SCENARIOS = ('null', 'known_improvement', 'window_mismatch', 'reflection',
             'relative_error', 'wrong_state', 'nonfinite')

def production_gate(raw, p, seed):
    data = blocks(fold(raw), p['block_length'])
    index = bootstrap_indices(len(data), p['bootstrap_samples'], seed)
    windows, masses = [], []
    for w in p['reference_windows']:
        result, boot = make_reference(data, p, w, 'single').bootstrap(index)
        windows.append(result); masses.append(boot)
    nominal = p['reference_nominal_window']; reference = windows[nominal]
    source = inspect.getsource(experiment.develop)
    start = source.index('    failures = []')
    end = source.index('    sensitivity = {}', start)
    code = '\n'.join(line[4:] for line in source[start:end].splitlines())
    scope = dict(np=np, blocks=blocks, reflection_odd=experiment.reflection_odd,
                 raw=raw, p=p, masses=masses, windows=windows, nominal=nominal,
                 reference=reference, m=reference['mass'], mb=masses[nominal])
    exec(compile(code, 'production_develop_gate', 'exec'), scope)
    return {'passed': not scope['failures'], 'reasons': scope['failures'],
            'mass': reference['mass'], 'relative_se': reference['se']/reference['mass'],
            'reflection_z': scope['reflection_z']}

def generate(rng, scenario, p):
    T=p['geometry'][3]; t=np.arange(T); n=120
    e=1.5 if scenario=='wrong_state' else .8
    f=shape(e,t,T); amps=np.linspace(1,.2,len(p['powers']))
    signal=amps[:,None]*f
    if scenario=='window_mismatch':
        signal += amps[:,None]*3*shape(1.2,t,T)
    noise=.03 if scenario!='relative_error' else 2.5
    raw=signal[None]*(1+noise*rng.normal(size=(n,len(amps),T)))
    if scenario=='reflection': raw[...,1:8] *= 1.15
    if scenario=='nonfinite': raw[0,0,5]=np.nan
    return raw

def cp(k,n):
    return [float(beta.ppf(.025,k,n-k+1)) if k else 0.,
            float(beta.ppf(.975,k+1,n-k)) if k<n else 1.]

def main(dest,n=100,nboot=128):
    dest=Path(dest); dest.mkdir(parents=True,exist_ok=False)
    p=protocol(); p['bootstrap_samples']=nboot
    source=inspect.getsource(experiment.develop)
    plan={'schema':'full-gate-mc-v1','seed':20261119,'n_dataset_per_cell':n,
          'n_boot':nboot,'n_configuration':120,'block_length':p['block_length'],
          'scenarios':list(SCENARIOS),'mc_target':'two-sided 95% CP half-width <=0.10 per rate',
          'sample_size_rule':'N=100: worst-case binomial CP half-width about 0.102; strict target may be INCONCLUSIVE',
          'selection':'fixed single/reference windows; no candidate search',
          'production_gate_sha256':hashlib.sha256(source.encode()).hexdigest(),
          'module_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'protocol':p,'physical_score':None,
          'known_improvement_definition':'reference identical to null; hypothetical candidate excited overlap reduced; gate-only acceptance is not candidate power',
          'wrong_state_definition':'zero ground overlap, exact excited cosh E=1.5; structural false-pass tests ground identity limitation'}
    (dest/'preregistration.json').write_text(json.dumps(plan,indent=2)+'\n')
    rows=[]; summary={}
    for j,s in enumerate(SCENARIOS):
        for i in range(n):
            seed=20261119+j*100000+i; rng=np.random.default_rng(seed)
            try:
                raw=generate(rng,s,p)
                if not np.all(np.isfinite(raw)): raise ValueError('nonfinite correlator')
                r=production_gate(raw,p,seed); r['failure']=False
            except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
                r={'passed':False,'failure':True,'reasons':[type(exc).__name__+': '+str(exc)]}
            rows.append(dict(scenario=s,dataset=i,seed=seed,**r))
        cell=[r for r in rows if r['scenario']==s]; counts={}
        for name,pred in [('pass',lambda r:r['passed']),('abstain',lambda r:not r['passed']),('failure',lambda r:r['failure'])]:
            k=sum(pred(r) for r in cell); ci=cp(k,n)
            counts[name]={'k':k,'n':n,'rate':k/n,'cp95':ci,'precision_status':'PASS' if (ci[1]-ci[0])/2<=.1 else 'INCONCLUSIVE'}
        reasons={}
        for r in cell:
            for reason in r['reasons']:
                key=reason.split(' shifts by')[0]; reasons[key]=reasons.get(key,0)+1
        summary[s]={'rates':counts,'reason_counts':reasons,'examples':cell[:3]}
        print(s,counts,flush=True)
    result={'plan':plan,'summary':summary,'rows':rows,'status':'DIAGNOSTIC_ONLY','physical_score':None}
    (dest/'full_gate_mc.json').write_text(json.dumps(result,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(11,5))
    for offset,name in [(-.22,'pass'),(0,'abstain'),(.22,'failure')]:
        values=[summary[s]['rates'][name] for s in SCENARIOS]
        y=np.array([v['rate'] for v in values]); intervals=np.array([v['cp95'] for v in values])
        ax.errorbar(np.arange(len(values))+offset,y,yerr=[y-intervals[:,0],intervals[:,1]-y],fmt='o',capsize=3,label=name)
    ax.set_xticks(range(len(SCENARIOS)),SCENARIOS,rotation=25,ha='right'); ax.set_ylim(-.03,1.03)
    ax.set_ylabel('dataset frequency, exact binomial 95% CI'); ax.legend();fig.tight_layout();fig.savefig(dest/'full_gate_rates.png');plt.close(fig)
    text=['# 完整生产reference gate的CPU MC诊断','',f'每cell {n}独立dataset，{nboot}配对bootstrap；先写preregistration再执行。',
          '生产develop的全部gate语句按原文提取执行，包含χ²、paired窗口漂移、相对SE、边界与反射；不是χ²子门。',
          '单态模型/窗口固定；不含候选优化或真实anchor，因此没有physical score。known_improvement仅检查参考接受率，不是candidate检验功效。',
          'wrong_state通过是结构假通过：可拟合的纯激发态无法由这些gate认证为基态。','',
          '|场景|pass|abstain|failure|pass CP95|精度|','|---|---:|---:|---:|---|---|']
    for s in SCENARIOS:
        a=summary[s]['rates'];text.append(f"|{s}|{a['pass']['k']}/{n}|{a['abstain']['k']}/{n}|{a['failure']['k']}/{n}|{a['pass']['cp95']}|{a['pass']['precision_status']}|")
    text+=['','![rates](full_gate_rates.png)','','## 失败/弃权样本']
    for s in SCENARIOS:
        bad=[r for r in rows if r['scenario']==s and not r['passed']][:2]
        text.append(f'- {s}: '+ ('；'.join(f"dataset={r['dataset']} seed={r['seed']} {r['reasons']}" for r in bad) if bad else '无拒绝样本；不得据此认证基态。'))
    text+=['','## 解释与限制','null/known_improvement的pass是接受率；window/reflection/relative-error的abstain是检测功效；wrong-state的pass是结构false-pass。失败是abstain子集，不能相加。',
           '相对误差场景可同时触发其他门，reason_counts给出各原因；不假装各场景只操纵一个统计量。',
           'CP区间按独立dataset计，bootstrap次数不是独立样本量。任何半宽未达0.10的率为INCONCLUSIVE，不因观察结果追加样本。',
           '生产软件路径复用通过源码段提取确保判据一致；源码hash绑定并在结构变化时失败。后续可独立重构为共享纯函数。',
           '真实anchor、新GPU/集群测量仍NOT_RUN；此实验不升级production physical_score。']
    (dest/'README.md').write_text('\n'.join(text)+'\n')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--dest',required=True);parser.add_argument('--datasets',type=int,default=100);parser.add_argument('--bootstrap',type=int,default=128);a=parser.parse_args();main(a.dest,a.datasets,a.bootstrap)
