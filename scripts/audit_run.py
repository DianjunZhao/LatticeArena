"""Emit evidence JSON for an existing run (todo F0)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import json
from pathlib import Path

import numpy as np

from core.evidence import record, write_evidence
from core.io import digest, fingerprint


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
                              scope='archived_data', geometry=p['geometry']))
        entries.append(record('wilson.shape_finite', 'wilson_loop', 'loops are finite with the declared shape',
                              'shape/finite check', observed=list(loops.shape),
                              threshold={'n': len(ids), 'kernels': len(p['kernels']),
                                         'R': len(p['r_values']), 'T': len(p['t_values'])},
                              status='PASS' if loops.shape == (len(ids), len(p['kernels']), len(p['r_values']), len(p['t_values']))
                              and np.all(np.isfinite(loops)) else 'FAIL', scope='archived_data',
                              geometry=p['geometry']))
    entries.append(record('wilson.kernel_identity', 'wilson_loop', 'submission kernel hash equals the archived provenance',
                          'sha256 compare', observed={'submission': sub.get('kernel_sha256'),
                                                      'provenance': prov.get('kernel_sha256')},
                          threshold={'equal': True},
                          status='PASS' if sub.get('kernel_sha256') == prov.get('kernel_sha256') else 'FAIL',
                          scope='archived_data', geometry=p['geometry']))
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
        entries.append(record(f'pion.{split}.shape', 'pion_projection', f'{split} correlators are finite with the declared shape',
                              'shape/finite check', observed=list(data.shape),
                              threshold={'n': len(data), 'channels': len(p['powers']), 'T': p['geometry'][3]},
                              status='PASS' if data.shape == (len(data), len(p['powers']), p['geometry'][3])
                              and np.all(np.isfinite(data)) else 'FAIL', scope='archived_data', geometry=p['geometry']))
        entries.append(record(f'pion.{split}.protocol_hash', 'pion_projection', f'{split} protocol hash matches the provenance',
                              'hash compare', observed=stored[:12], threshold=fingerprint(p)[:12],
                              status='PASS' if stored == fingerprint(p) else 'FAIL', scope='archived_data',
                              geometry=p['geometry']))
    return entries


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
    write_evidence(args.out, entries)
    print(f'wrote {args.out} ({len(entries)} entries)')


if __name__ == '__main__':
    main()
