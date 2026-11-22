"""Read-only redraw of frozen bounded-score summary with explicit block ticks."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def redraw(result):
    result=Path(result)
    output=result/'plot_review'
    output.mkdir(exist_ok=False)
    summary_path=result/'summary.json'
    rows=json.loads(summary_path.read_text())['cells']
    fig,axs=plt.subplots(2,2,figsize=(12,9),layout='constrained')
    for ax,world,effect in zip(axs[0],['practical_improvement','strong_improvement'],[.2,.4]):
        for anchor,style in [('exact','-'),('uncertain','--')]:
            for f,color in [(1,'#0072B2'),(2,'#D55E00'),(4,'#009E73')]:
                cs=[x for x in rows if x['world']==world and x['anchor']==anchor and x['family']==f and x['eligible']]
                y=np.array([x['power']['rate'] for x in cs]); ci=np.array([x['power']['cp95'] for x in cs])
                ax.errorbar([x['n'] for x in cs],y,yerr=[y-ci[:,0],ci[:,1]-y],fmt='o'+style,color=color,capsize=2,label=f'F={f}, {anchor}')
        ax.set(title=f'Power: true improvement {effect}; threshold 0.1',xlabel='Independent blocks n',ylabel='Any-candidate certification',ylim=(-.03,1.03));ax.grid(alpha=.2)
    axs[0,0].legend(fontsize=8)
    worlds=['max_variance_null','shared_baseline_null','threshold_null','practical_improvement','strong_improvement','anchor_sensitive_null']
    for wi,world in enumerate(worlds):
        for ai,anchor in enumerate(('exact','uncertain')):
            cs=[x for x in rows if x['world']==world and x['eligible'] and x['anchor']==anchor]
            y=np.array([1-x['metrics']['joint_coverage']['rate'] for x in cs])
            axs[1,0].scatter(wi+(ai-.5)*.22+np.linspace(-.07,.07,len(cs)),y,s=18,marker='o' if ai==0 else 'x',color='#0072B2' if ai==0 else '#D55E00',label=anchor if wi==0 else None)
    axs[1,0].axhline(.05,color='black',ls=':',label='Total error budget .05')
    axs[1,0].set(xticks=range(6),xticklabels=['Max-var\nnull','Shared\nnull','Threshold\nnull','Improve\n0.2','Improve\n0.4','Anchor\nnull'],ylabel='Family noncoverage',title='Eligible cells: one dot per n/F/anchor cell',ylim=(-.003,.06));axs[1,0].legend(fontsize=8)
    for kind,label,color in [('undercoverage','Anchor interval wrong','#D55E00'),('perfect','Blocks fully dependent','#0072B2')]:
        for f in (1,2,4):
            cs=[x for x in rows if not x['eligible'] and x['family']==f and (x['anchor']==kind or x['dependence']==kind)]
            y=np.array([x['metrics']['numeric_family_crossing']['rate'] for x in cs]);ci=np.array([x['metrics']['numeric_family_crossing']['cp95'] for x in cs])
            axs[1,1].errorbar([x['n'] for x in cs],y,yerr=[y-ci[:,0],ci[:,1]-y],fmt='o-',color=color,alpha=.45+.13*f,label=f'{label}, F={f}',capsize=2)
    axs[1,1].axhline(.05,color='black',ls=':');axs[1,1].set(xlabel='Nominal blocks n',ylabel='Hypothetical false-certificate crossing',ylim=(-.03,1.03),title='Invalid assumptions: diagnostic only; all abstain');axs[1,1].legend(fontsize=7)
    for ax in [axs[0,0],axs[0,1],axs[1,1]]:
        ax.set_xscale('log');ax.set_xticks([12,24,100,400],['12','24','100','400']);ax.minorticks_off()
    fig.suptitle('Bounded paired-block MSE: synthetic conditional calibration; no physical score',fontsize=13)
    fig.savefig(output/'calibration.png',dpi=180);plt.close(fig)
    receipt=dict(status='READ_ONLY_PLOT_REVIEW',summary_sha256=hashlib.sha256(summary_path.read_bytes()).hexdigest(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        image_sha256=hashlib.sha256((output/'calibration.png').read_bytes()).hexdigest(),
        changes='Explicit log-axis ticks 12/24/100/400; no minor ticks; larger legible legends. Summary and raw outcomes unchanged; no new simulation.')
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (output/'README.md').write_text('# Read-only plot review\n\nThe original figure had crowded minor log-axis tick labels. This redraw uses only the frozen summary, explicit block-count ticks and clearer labels. No datasets, rates, intervals or source-bound calibration outputs were modified.\n\n![Readable calibration](calibration.png)\n\nSource and summary/image hashes are in [receipt.json](receipt.json).\n')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('result',type=Path)
    redraw(parser.parse_args().result)
