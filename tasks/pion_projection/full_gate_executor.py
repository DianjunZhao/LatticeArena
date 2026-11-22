"""Resumable fixed-N MC runner; each world uses the production file adapter."""
import argparse
import hashlib
import json
import time
from pathlib import Path
from .synthetic_adapter import execute
from .full_gate_mc import cp
SCENARIOS=('null_equal_candidate','known_lower_excited_overlap','window_mismatch','reflection','relative_error','wrong_state','nonfinite')

def atomic(path,data):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2)+'\n');tmp.replace(path)

def main(dest,dry=False):
    dest=Path(dest);dest.mkdir(parents=True,exist_ok=True)
    files=('synthetic_adapter.py','synthetic_worlds.py','experiment.py','joint.py','identity.py','full_gate_executor.py')
    identity={f:hashlib.sha256((Path(__file__).parent/f).read_bytes()).hexdigest() for f in files}
    frozen=dest/'executor_spec.json'
    spec={'schema':'mc-executor-v1','n_per_cell':1 if dry else 402,'seed':20261122,'budgets':[128,200,64],'scenarios':SCENARIOS,'code_hashes':identity,'physical_score':None,'rate_rule':'CP95 marginal per rate, halfwidth<=.05 else INCONCLUSIVE','rejection_rule':'ValueError amplitude not identified or nonfinite => failure and abstain, retain raw inputs/seed/stage/reason; other exceptions BLOCKED','parent_plan':'full_gate_mc_20261119_v2_amendment_01/preregistration.json'}
    if frozen.exists():
        if json.loads(frozen.read_text())!=json.loads(json.dumps(spec)):raise ValueError('executor frozen identity changed')
    else:atomic(frozen,spec)
    n=spec['n_per_cell'];rows=[]
    for j,scenario in enumerate(SCENARIOS):
        for i in range(n):
            folder=dest/scenario/f'dataset_{i:04d}';receipt=folder/'adapter_parity.json'
            if receipt.exists():r=json.loads(receipt.read_text())
            else:
                if folder.exists():raise ValueError(f'incomplete dataset {folder}: inspect before retry; no overwrite')
                t=time.perf_counter();r=execute(folder,scenario,True,seed=20261122+j*100000+i);r['elapsed_seconds']=time.perf_counter()-t;atomic(receipt,r)
            rows.append({'scenario':scenario,'dataset':i,'receipt':str(receipt),**r})
            counts={}
            for s in SCENARIOS:
                cell=[x for x in rows if x['scenario']==s];N=len(cell)
                if not N:continue
                counts[s]={}
                for name,pred in [('acceptance',lambda x:bool(x.get('reference_accepted'))),('certification',lambda x:bool(x.get('candidate_certified'))),('failure',lambda x:bool(x.get('failure'))),('abstain',lambda x:x['status']=='EXPECTED_REJECTION' or not x.get('reference_accepted',False))]:
                    k=sum(pred(x) for x in cell);ci=cp(k,N);counts[s][name]={'k':k,'n':N,'cp95':ci,'status':'PASS' if (ci[1]-ci[0])/2<=.05 else 'INCONCLUSIVE'}
            atomic(dest/'checkpoint.json',{'completed':len(rows),'planned':len(SCENARIOS)*n,'last_scenario':scenario,'last_dataset':i,'rates':counts,'physical_score':None,'status':'RUNNING'})
            print(scenario,i,r['status'],r.get('elapsed_seconds'),flush=True)
            if r['status']=='BLOCKED':raise RuntimeError(r.get('blocker'))
    atomic(dest/'dataset_results.json',{'rows':rows,'physical_score':None})
    state=json.loads((dest/'checkpoint.json').read_text());state['status']='DRY_RUN_COMPLETE' if dry else 'COMPLETE';atomic(dest/'checkpoint.json',state)
    (dest/'README.md').write_text('# File-entry MC execution\n\nEach dataset receipt/raw_inputs.npz stores seed, production stage, rejection reason, code hashes and draw parity. physical_score=null. checkpoint.json is atomically updated after every dataset; rerun identical command resumes completed receipts and rejects incomplete folders rather than overwriting. Rates and exact CP95 are in checkpoint. Acceptance is not candidate power; certification in null is false-certification, in improvement is candidate power, and wrong-state acceptance is structural false-pass. failure is a subset of abstain. Dry-run counts are never pooled into 402/cell MC.\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dest',required=True);p.add_argument('--dry',action='store_true');a=p.parse_args();main(a.dest,a.dry)
