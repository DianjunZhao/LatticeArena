"""Emit evidence JSON for an existing run (todo F0)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from core.evidence import make_receipt, record, verify_receipt, write_evidence
from core.io import digest, fingerprint

CODE = {'kernels': 'tasks/wilson_loop/kernels.py', 'common': 'tasks/wilson_loop/common.py',
        'statistics': 'tasks/wilson_loop/statistics.py'}
PION_CODE = {'kernels': 'tasks/pion_projection/kernels.py', 'statistics': 'tasks/pion_projection/statistics.py',
             'experiment': 'tasks/pion_projection/experiment.py'}


def wilson(run, protocol_path):
    from tasks.wilson_loop.common import indices, read_nersc  # noqa: F401
    p = json.loads(Path(protocol_path).read_text())
    sub = json.loads((run / 'submission.json').read_text())
    prov = json.loads((run / 'validation_provenance.json').read_text())
    entries = []
    with np.load(run / 'validation.npz') as f:
        ids = f['ids'].tolist()
        loops = f['loops']
        entries.append(record('wilson.ids', 'wilson_loop', 'validation ids are the frozen split prefix',
                              f'python scripts/audit_run.py --task wilson_loop --run {run}',
                              observed={'ids': ids[:5], 'n': len(ids)},
                              threshold={'expected': [int(x) for x in np.arange(p['validation'][0], p['validation'][1] + 1)]},
                              status='PASS' if ids == list(range(p['validation'][0], p['validation'][1] + 1)) else 'FAIL',
                              scope='archived_data', geometry=p['geometry'],
                              code={name: digest(Path(path)) for name, path in CODE.items()},
                              inputs={'ids_hash': hashlib.sha256(np.asarray(ids).tobytes()).hexdigest()}))
        entries.append(record('wilson.shape_finite', 'wilson_loop', 'loops are finite with the declared shape',
                              'shape/finite check', observed=list(loops.shape),
                              threshold={'n': len(ids), 'kernels': len(p['kernels']),
                                         'R': len(p['r_values']), 'T': len(p['t_values'])},
                              status='PASS' if loops.shape == (len(ids), len(p['kernels']), len(p['r_values']), len(p['t_values']))
                              and np.all(np.isfinite(loops)) else 'FAIL', scope='archived_data',
                              geometry=p['geometry'],
                              code={name: digest(Path(path)) for name, path in CODE.items()},
                              inputs={'loops_sha256': hashlib.sha256(np.ascontiguousarray(loops).tobytes()).hexdigest()}))
    observed = {'submission': sub.get('kernel_sha256'), 'provenance': prov.get('kernel_sha256')}
    if observed['submission'] is None or observed['provenance'] is None or prov.get('generation') is None:
        status = 'NOT_RUN'
    else:
        status = 'PASS' if observed['submission'] == observed['provenance'] else 'FAIL'
    entries.append(record('wilson.kernel_identity', 'wilson_loop', 'submission kernel hash equals the archived provenance',
                          'sha256 compare', observed=observed, threshold={'equal': True, 'required': True},
                          status=status, scope='archived_data', geometry=p['geometry'],
                          code={name: digest(Path(path)) for name, path in CODE.items()},
                          inputs={'provenance_generation': prov.get('generation')}))
    return entries


def pion(run):
    p = json.loads((run / 'development_provenance.json').read_text())['protocol']
    entries = []
    for split in ('development', 'validation'):
        path = run / f'{split}.npz'
        if not path.exists():
            entries.append(record(f'pion.{split}.present', 'pion_projection', f'{split} file is present',
                                  'file check', observed=False, threshold=True, status='NOT_RUN',
                                  scope='archived_data', geometry=p['geometry']))
            continue
        with np.load(path) as f:
            data = f['correlators']
            stored = str(f['protocol_hash'])
            stored_ids = f['ids'].tolist() if 'ids' in f else None
        expected_n = int(p[split][1] - p[split][0] + 1)
        entries.append(record(f'pion.{split}.shape', 'pion_projection', f'{split} correlators have the RunSpec size and are finite',
                              'RunSpec size/finite check', observed=list(data.shape),
                              threshold={'n': expected_n, 'channels': len(p['powers']), 'T': p['geometry'][3]},
                              status='PASS' if data.shape == (expected_n, len(p['powers']), p['geometry'][3])
                              and np.all(np.isfinite(data)) else 'FAIL', scope='archived_data', geometry=p['geometry'],
                              code={name: digest(Path(path)) for name, path in PION_CODE.items()},
                              inputs={'correlators_sha256': hashlib.sha256(np.ascontiguousarray(data).tobytes()).hexdigest()}))
        expected_ids = list(range(p[split][0], p[split][1] + 1))
        entries.append(record(f'pion.{split}.ids', 'pion_projection',
                              f'{split} ids equal the full RunSpec range (order included)',
                              'id list compare', observed=stored_ids,
                              threshold=expected_ids,
                              status='PASS' if stored_ids == expected_ids else 'FAIL',
                              scope='archived_data', geometry=p['geometry'],
                              code={name: digest(Path(path)) for name, path in PION_CODE.items()},
                              inputs={'ids_sha256': hashlib.sha256(
                                  np.asarray(stored_ids if stored_ids is not None else []).tobytes()).hexdigest()}))
        entries.append(record(f'pion.{split}.protocol_hash', 'pion_projection', f'{split} protocol hash matches the provenance',
                              'hash compare', observed=stored[:12], threshold=fingerprint(p)[:12],
                              status='PASS' if stored == fingerprint(p) else 'FAIL', scope='archived_data',
                              geometry=p['geometry'],
                              code={name: digest(Path(path)) for name, path in PION_CODE.items()},
                              inputs={'protocol_hash': stored}))
    return entries


def verify_entry_against_run(entry, run, task):
    """Recompute claimed code/input hashes from the files; arbitrary strings cannot pass."""
    known = CODE if task == 'wilson_loop' else PION_CODE
    for name, value in entry['code'].items():
        path = Path(known.get(name, name))
        if not path.exists() or digest(path) != value:
            raise ValueError(f'{entry["test_id"]}: code hash for {path} does not match the file')
    split = 'development' if 'development' in entry['test_id'] else 'validation'
    with np.load(run / f'{split}.npz') as f:
        if 'loops_sha256' in entry['inputs']:
            observed = hashlib.sha256(np.ascontiguousarray(f['loops']).tobytes()).hexdigest()
            if observed != entry['inputs']['loops_sha256']:
                raise ValueError(f'{entry["test_id"]}: loops hash does not match {split}.npz')
        if 'correlators_sha256' in entry['inputs']:
            observed = hashlib.sha256(np.ascontiguousarray(f['correlators']).tobytes()).hexdigest()
            if observed != entry['inputs']['correlators_sha256']:
                raise ValueError(f'{entry["test_id"]}: correlators hash does not match {split}.npz')
        if 'ids_sha256' in entry['inputs']:
            observed = hashlib.sha256(np.asarray(f['ids']).tobytes()).hexdigest()
            if observed != entry['inputs']['ids_sha256']:
                raise ValueError(f'{entry["test_id"]}: ids hash does not match {split}.npz')
    for key in ('protocol_hash', 'provenance_generation'):
        if key in entry['inputs']:
            value = entry['inputs'][key]
            if value is None and entry['status'] != 'PASS':
                continue
            if not isinstance(value, str) or len(value) < 8:
                raise ValueError(f'{entry["test_id"]}: {key} is not a hash string')
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', choices=['wilson_loop', 'pion_projection'], required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--protocol')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    run = Path(args.run)
    if args.task == 'wilson_loop':
        protocol_path = args.protocol or str(run.parent.parent / 'tasks/wilson_loop/protocol_v3.json')
        entries = wilson(run, protocol_path)
    else:
        entries = pion(run)
    run_sha = digest(run / 'validation.npz')
    for entry in entries:
        verify_entry_against_run(entry, run, args.task)
        entry['receipt'] = make_receipt(entry, run_sha)
        verify_receipt(entry, run_sha)
    write_evidence(args.out, entries)
    print(f'wrote {args.out} ({len(entries)} entries)')


if __name__ == '__main__':
    main()
