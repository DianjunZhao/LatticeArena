"""Fault-injection matrix for the measurement transaction (todo P1a)."""
import json
import shutil
import tempfile
from pathlib import Path

import numpy as np

from .common import digest, fingerprint
from .identity import (DEPENDENCIES, check_resume, generation, loops_sha256,
                       measurement_spec, write_marker)

OUT = Path('results/wilson_loop/audit_20261119_transaction')


def build(root, p, n=3):
    root = Path(root)
    spec = measurement_spec(p, 'development')
    ids = spec['ids'][:n]
    n_kernels, n_r, n_t = len(p['kernels']), len(p['r_values']), len(p['t_values'])
    loops = np.arange(n * n_kernels * n_r * n_t, dtype=float).reshape(n, n_kernels, n_r, n_t) + 1.0
    (root / 'ensemble').mkdir(parents=True)
    records = []
    for row, cfg in enumerate(ids):
        gauge = root / 'ensemble' / f'wilson_b6.{cfg}'
        gauge.write_bytes(f'gauge-{cfg}'.encode())
        records.append({'id': int(cfg), 'gauge_path': str(gauge), 'checksum_status': 'absent',
                        'gauge_sha256': digest(gauge), 'loops_sha256': loops_sha256(loops[row:row + 1])})
    np.savez(root / 'development.npz', ids=np.asarray(ids), loops=loops,
             protocol_hash=fingerprint(p), generation=generation(spec))
    provenance = {'protocol': p, 'kernel_sha256': spec['kernel_sha256'],
                  'dependencies': {name: digest(Path(__file__).parent / name) for name in DEPENDENCIES},
                  'generation': generation(spec), 'records': records}
    (root / 'development_provenance.json').write_text(json.dumps(provenance))
    write_marker(root, 'development', root / 'development.npz', root / 'development_provenance.json',
                 spec, loops)
    return spec


def _rewrite_marker(root, spec):
    with np.load(root / 'development.npz') as f:
        loops = f['loops']
    write_marker(root, 'development', root / 'development.npz',
                 root / 'development_provenance.json', spec, loops)


def check(root, spec):
    try:
        return {'ok': True, 'rows': check_resume(root, 'development', spec, verify_gauge=True)}
    except ValueError as exc:
        return {'ok': False, 'reason': str(exc).replace(str(root), '<tmp>')}


def main():
    protocol = json.loads(Path(__file__).with_name('protocol_v3.json').read_text())
    p = dict(protocol, version='transaction-test', development=[0, 2], validation=[0, 2],
             geometry=[4, 4, 4, 4], r_values=[1, 2], kernels=protocol['kernels'][:2],
             ensemble='ensemble')
    base = Path(tempfile.mkdtemp())
    spec = build(base / 'valid', p, n=3)
    cases = [('valid', 'resume 3 rows', check(base / 'valid', spec))]

    def copy(name):
        dst = base / name
        shutil.copytree(base / 'valid', dst)
        return dst

    root = copy('npz_missing'); (root / 'development.npz').unlink()
    cases.append(('npz_missing', 'partial transaction', check(root, spec)))
    root = copy('provenance_missing'); (root / 'development_provenance.json').unlink()
    cases.append(('provenance_missing', 'partial transaction', check(root, spec)))
    root = copy('marker_missing'); (root / 'development.commit.json').unlink()
    cases.append(('marker_missing', 'partial transaction', check(root, spec)))
    root = copy('marker_generation')
    marker = json.loads((root / 'development.commit.json').read_text())
    marker['generation'] = '0' * 64
    (root / 'development.commit.json').write_text(json.dumps(marker))
    cases.append(('marker_generation', 'generation mismatch', check(root, spec)))
    root = copy('npz_tampered')
    with np.load(root / 'development.npz') as f:
        ids, loops = f['ids'], f['loops'] + 1.0
    np.savez(root / 'development.npz', ids=ids, loops=loops,
             protocol_hash=fingerprint(p), generation=generation(spec))
    cases.append(('npz_tampered', 'file hash differs from marker', check(root, spec)))
    root = copy('provenance_records_reordered')
    prov = json.loads((root / 'development_provenance.json').read_text())
    prov['records'] = [prov['records'][1], prov['records'][0], prov['records'][2]]
    (root / 'development_provenance.json').write_text(json.dumps(prov))
    _rewrite_marker(root, spec)
    cases.append(('records_reordered', 'record ids do not match', check(root, spec)))
    root = copy('gauge_missing')
    first = json.loads((root / 'development_provenance.json').read_text())['records'][0]['gauge_path']
    Path(first).unlink()
    _rewrite_marker(root, spec)
    cases.append(('gauge_missing', 'gauge file/hash mismatch', check(root, spec)))
    root = copy('dependency_changed')
    prov = json.loads((root / 'development_provenance.json').read_text())
    prov['dependencies']['kernels.py'] = '0' * 64
    (root / 'development_provenance.json').write_text(json.dumps(prov))
    _rewrite_marker(root, spec)
    cases.append(('dependency_changed', 'dependency kernels.py changed', check(root, spec)))
    root = copy('marker_loops_hash')
    marker = json.loads((root / 'development.commit.json').read_text())
    marker['loops_sha256'] = '0' * 64
    (root / 'development.commit.json').write_text(json.dumps(marker))
    cases.append(('marker_loops_hash', 'loops content differs', check(root, spec)))

    rows = [{'case': name, 'expected': expected, 'result': result}
            for name, expected, result in cases]
    for row in rows:
        row['status'] = ('PASS' if (row['case'] == 'valid' and row['result']['ok'])
                         or (row['case'] != 'valid' and not row['result']['ok']) else 'FAIL')
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {'schema': 'wilson-transaction-matrix-v1', 'rows': rows,
               'all_status_pass': all(row['status'] == 'PASS' for row in rows)}
    (OUT / 'transaction_matrix.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('all_status_pass', summary['all_status_pass'])
    for row in rows:
        print(row['case'], row['status'], row['result'].get('reason', '')[:70])


if __name__ == '__main__':
    main()
