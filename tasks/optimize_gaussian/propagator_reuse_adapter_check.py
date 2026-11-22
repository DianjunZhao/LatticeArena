"""Exercise Optimize's receipt-aware validator on the existing D-chain cache."""
import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np

from tasks.pion_projection.common import digest
from .train import validate_inputs


def audit(root, pion_run, plan_path, protocol_path, output):
    root = Path(root).resolve()
    os.chdir(root)
    pion_run = Path(pion_run)
    plan = json.loads(Path(plan_path).read_text())
    protocol = json.loads(Path(protocol_path).read_text())
    measurement_path = pion_run / 'development.npz'
    provenance_path = pion_run / 'development_provenance.json'
    provenance = json.loads(provenance_path.read_text())
    ids = [int(row['id']) for row in provenance['records']]
    cache = {int(row['id']): row['cache_key'] for row in provenance['records']}
    p = {
        'ensemble': plan['ensemble'], 'geometry': protocol['geometry'],
        't_boundary': protocol['t_boundary'], 'tolerance': protocol['tolerance'],
        'max_iterations': protocol['max_iterations'], 'kappa': protocol['kappa'],
        'source': protocol['source'],
        'propagator_measurement_receipt': {
            'measurement_path': str(measurement_path.resolve()),
            'measurement_sha256': digest(measurement_path),
            'provenance_path': str(provenance_path.resolve()),
            'provenance_sha256': digest(provenance_path),
            'generation': provenance['generation'],
            'protocol_hash': provenance['protocol_hash'],
        },
    }
    rows = validate_inputs(p, ids, cache)
    verified = {int(key): value for key, value in rows.items() if value['status'] == 'verified'}
    failures = {key: value for key, value in rows.items() if value['status'] != 'verified'}
    result = {
        'schema': 'optgauss-pion-receipt-adapter-integration-v1',
        'status': 'PASS' if len(verified) == 100 and not failures else 'FAIL',
        'n_ids': len(ids), 'ids': [ids[0], ids[-1]],
        'verified_count': len(verified), 'failure_count': len(failures),
        'max_residual': max(row['residual'] for row in verified.values()) if verified else None,
        'mean_residual': float(np.mean([row['residual'] for row in verified.values()])) if verified else None,
        'trajectory_join_count': sum(row.get('trajectory_id') is not None for row in verified.values()),
        'source_hashes': {'train.py': digest(Path(__file__).with_name('train.py')),
                          'adapter_check.py': digest(Path(__file__))},
        'pion_inputs': {'measurement_sha256': p['propagator_measurement_receipt']['measurement_sha256'],
                        'provenance_sha256': p['propagator_measurement_receipt']['provenance_sha256'],
                        'generation': provenance['generation'], 'protocol_hash': provenance['protocol_hash']},
        'failures': failures,
        'scope': 'validator integration only for D IDs 0-99; no optimizer fit, E anchor, D gap/validation, or shared holdout read',
    }
    output = root / output
    output.mkdir(parents=True, exist_ok=True)
    (output / 'adapter_check.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    lines = [
        '# Optimize receipt-adapter integration check', '',
        f"**Status: `{result['status']}`.**", '',
        f"- IDs: D {ids[0]}–{ids[-1]} ({len(ids)} configurations). Verified: {len(verified)}/100; failures: {len(failures)}.",
        f"- Maximum residual: `{result['max_residual']}`; trajectory joins: {result['trajectory_join_count']}/100.",
        f"- Generation: `{provenance['generation']}`; protocol: `{provenance['protocol_hash']}`.", '',
        'The test passes the real Pion NPZ/provenance pair and actual remote cache files through `train.validate_inputs`. This confirms input identity and residual receipt reuse for the fit/development ranges; it does not run Optimize training, validate a physical score, or open any held-out ID.', '',
        'See `adapter_check.json` for the failure list and exact hashes.', ''
    ]
    (output / 'README.md').write_text('\n'.join(lines))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--pion-run', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.root, args.pion_run, args.plan, args.protocol, args.output), indent=2))
