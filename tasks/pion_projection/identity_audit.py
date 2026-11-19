"""Identity audit matrix for joint (todo A1/A2/A5)."""
import json
import shutil
import tempfile
from pathlib import Path

import numpy as np

from .common import digest
from .identity import verify_run_identity

OUT = Path('results/pion_projection/audit_20261119_identity')
RUN = Path('results/pion_projection/s16t16_gevp200')


def case(root, name, mutate):
    work = Path(root) / name
    shutil.copytree(RUN, work)
    mutate(work)
    kind, reasons = verify_run_identity(work)
    return {'case': name, 'kind': kind, 'reasons': reasons, 'ok': not reasons}


def tamper_report_hash(work):
    path = work / 'validation_results.json'
    report = json.loads(path.read_text())
    report['submission_sha256'] = '0' * 64
    path.write_text(json.dumps(report))


def tamper_validation_ids(work):
    with np.load(work / 'validation.npz') as f:
        ids, corr = f['ids'], f['correlators']
        protocol_hash = f['protocol_hash']
    np.savez(work / 'validation.npz', ids=ids[::-1].copy(), correlators=corr,
             protocol_hash=protocol_hash)


def tamper_statistics_hash(work):
    path = work / 'submission.json'
    sub = json.loads(path.read_text())
    sub['reference']['statistics_sha256'] = '0' * 64
    path.write_text(json.dumps(sub))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp())
    rows = [case(root, 'legal', lambda work: None),
            case(root, 'stale_report', tamper_report_hash),
            case(root, 'validation_reordered', tamper_validation_ids),
            case(root, 'source_changed', tamper_statistics_hash)]
    # missing artifact / score spec are legacy-run states: joint already abstains
    import tasks.pion_projection.joint as joint
    dest = root / 'joint_missing'
    certificate = joint.run(RUN, models=('single',), outer=6, inner=4, dest=dest)
    rows.append({'case': 'missing_artifact_spec', 'kind': 'single',
                 'status': certificate['status'],
                 'reasons': certificate['failure_reasons'],
                 'all_candidates_uncertified': all(not item['certified']
                                                   for item in certificate['candidates'].values()),
                 'ok': certificate['status'] == 'abstain'
                 and any('gate_artifact_missing' in r for r in certificate['failure_reasons'])})
    dest2 = root / 'joint_repeat'
    joint.run(RUN, models=('single',), outer=6, inner=4, seed=20261119, dest=dest2)
    with np.load(dest / 'joint_draws.npz') as a, np.load(dest2 / 'joint_draws.npz') as b:
        same = all(np.array_equal(a[key], b[key]) for key in
                   ('draw_id', 'dev_index', 'val_index', 'dev_inner', 'val_inner'))
        same = same and all(np.array_equal(a[key], b[key]) for key in a.files
                            if key.startswith('risk_') or key.startswith('mass_'))
    rows.append({'case': 'same_seed_reproducible', 'ok': bool(same), 'same_arrays': bool(same)})
    result = {'schema': 'pion-identity-audit-v1', 'rows': rows,
              'all_expected': all(row['ok'] for row in rows)}
    (OUT / 'joint_identity_audit.json').write_text(json.dumps(result, indent=2) + '\n')
    for row in rows:
        print(row['case'], row['ok'], row.get('reasons', ''))


if __name__ == '__main__':
    main()
