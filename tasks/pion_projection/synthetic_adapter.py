"""CPU file-entry parity adapter; synthetic, never a physical score."""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
from unittest.mock import patch
import numpy as np
from . import common, experiment, joint
from .full_gate_mc import generate, production_gate
from .statistics import blocks, fold, risk
from .reference import make_reference


def execute(dest, scenario=None, full_budget=False, seed=20261119):
    dest=Path(dest);dest.mkdir(parents=True,exist_ok=False)
    run=dest/'run';run.mkdir()
    p=common.protocol();p.update(development=[0,119],validation=[130,189],gap=[120,129],bootstrap_samples=32,outer_samples=4,inner_samples=8,optimizer_max_iterations=100)
    if scenario is not None:
        p.update(synthetic=True, synthetic_fixed_candidates={'baseline_channel':1,'candidate_channel':2})
    if full_budget:
        p.update(bootstrap_samples=128, outer_samples=200, inner_samples=64)
    outer, inner = (200,64) if full_budget else (4,8)
    common.write_json(run/'protocol.json',p)
    rng=np.random.default_rng(seed)
    if scenario is None:
        dev=generate(rng,'null',p);val=generate(rng,'null',p)[:60]
    else:
        from .synthetic_worlds import generate_world
        dev=generate_world(rng,scenario,p,120);val=generate_world(rng,scenario,p,60)
    np.savez_compressed(dest/'raw_inputs.npz',development=dev,validation=val)
    def save(split,raw):
        ids=common.indices(split,p)
        np.savez_compressed(run/f'{split}.npz',ids=ids,correlators=raw,protocol_hash=common.fingerprint(p))
        common.write_json(run/f'{split}_provenance.json',{'protocol':p,'synthetic':True,'records':[]})
    save('development',dev)
    status={'scenario':scenario, 'full_budget':full_budget, 'schema':'pion-synthetic-adapter-v1','synthetic':True,'physical_score':None,'status':'NOT_RUN','mutations':{}}
    status.update(seed=seed, stage='develop')
    log=io.StringIO()
    try:
        with patch.object(common,'PROTOCOL_PATH',run/'protocol.json'),contextlib.redirect_stdout(log):
            experiment.develop(run)
            save('validation',val)
            status['stage']='evaluate'
            experiment.evaluate(run)
            status['stage']='joint'
            result=joint.run(run,outer=outer,inner=inner,seed=81,dest=dest/'joint')
            status.update(reference_accepted=result['reference_passed'], candidate_certified=bool(result['candidates']['fixed_candidate']['certified']) if scenario is not None else False)
            sub=json.loads((run/'submission.json').read_text())
            z=np.load(dest/'joint/joint_draws.npz')
            db=blocks(fold(dev),p['block_length']);vb=blocks(fold(val),p['block_length'])
            differences=[]
            for r in range(outer):
                ref=make_reference(db[z['dev_index'][r]],p,p['reference_windows'][p['reference_nominal_window']],'single')
                fit,masses=ref.bootstrap(z['dev_inner'][r])
                for name,w in sub['submissions'].items():
                    direct=risk(vb[z['val_index'][r]],w,fit['mass'],masses,z['val_inner'][r],p,require_valid=False,late_inverse=np.array(sub['late_inverse_covariances'][name]))['risk']
                    differences.append(abs(direct-z[f'risk_single_{name}'][r]))
            direct_gate=production_gate(dev,p,p['seed'])
            status.update(status='PASS',max_abs_draw_difference=float(max(differences)),n_draw_candidate_comparisons=len(differences),gate_parity=direct_gate['passed']==sub['calibration']['reference_passed'],certificate_status=result['status'])
            # Mutate only adapter-owned files, restore exact bytes after each case.
            for label,file,mutate in [
                ('submission_protocol','submission.json',lambda d:d.update(protocol_hash='WRONG')),
                ('reference_identity','submission.json',lambda d:d['reference'].update(implementation_sha256='WRONG')),
                ('gate_identity','submission.json',lambda d:d['gate_artifact'].update(protocol_hash='WRONG')),
                ('report_identity','validation_results.json',lambda d:d.update(validation_sha256='WRONG')),
                ('late_metric','submission.json',lambda d:d['late_inverse_covariances']['local'][0].__setitem__(0,999.))]:
                path=run/file;original=path.read_bytes();d=json.loads(original);mutate(d);path.write_text(json.dumps(d))
                try:
                    joint.run(run,outer=1,inner=2,dest=dest/f'rejected_{label}')
                    status['mutations'][label]={'rejected':False}
                except (ValueError,KeyError) as e:
                    status['mutations'][label]={'rejected':True,'reason':str(e)}
                finally:path.write_bytes(original)
            status['status']='PASS' if status['gate_parity'] and status['max_abs_draw_difference']<1e-12 and all(v['rejected'] for v in status['mutations'].values()) else 'FAIL'
    except Exception as e:
        reason=type(e).__name__+': '+str(e)
        expected=isinstance(e,ValueError) and (('Amplitude not identified' in str(e)) or ('Nonfinite measurement' in str(e)))
        status.update(status='EXPECTED_REJECTION' if expected else 'BLOCKED',blocker=reason, failure=expected, abstain=True, reference_accepted=False, candidate_certified=False)
    (dest/'execution.log').write_text(log.getvalue())
    status['code_sha256']={f:hashlib.sha256((Path(__file__).parent/f).read_bytes()).hexdigest() for f in ('synthetic_adapter.py','experiment.py','joint.py','identity.py','statistics.py','reference.py')}
    common.write_json(dest/'adapter_parity.json',status)
    (dest/'README.md').write_text('# Synthetic文件入口adapter parity\n\n'+json.dumps(status,indent=2)+'\n\n输入为120开发/60验证synthetic配置；4 outer×8 inner只验程序一致性，不是MC校准。真实develop→evaluate→joint调用improvement_certificate；直接helper使用保存的全部共同索引逐draw复算，不另写gate。protocol通过common.PROTOCOL_PATH临时绑定至新run，未mock算法/认证。生产输出可能含条件score，该run是synthetic，physical_score始终null，不作物理排名。\n\n每项mutation仅改本目录文件并恢复原始bytes；记录明确拒绝原因。主402/cell MC未执行。若BLOCKED则查看execution.log与blocker，不伪造结果。\n')
    return status
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--dest',required=True);print(json.dumps(execute(a.parse_args().dest),indent=2))
