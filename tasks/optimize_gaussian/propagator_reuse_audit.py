"""Audit whether a frozen Pion point-propagator cache can feed Optimize D-chain IDs."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def audit(root, pion_run, plan_path, protocol_path, output):
    root, pion_run, plan_path, protocol_path, output = map(Path, (root, pion_run, plan_path, protocol_path, output))
    root = root.resolve()
    pion_run = (root / pion_run).resolve()
    plan_path = (root / plan_path).resolve()
    protocol_path = (root / protocol_path).resolve()
    output = (root / output).resolve()
    plan = json.loads(plan_path.read_text())
    protocol = json.loads(protocol_path.read_text())
    provenance = json.loads((pion_run / 'development_provenance.json').read_text())
    submission_path = pion_run / 'submission.json'
    submission = json.loads(submission_path.read_text()) if submission_path.exists() else None
    manifest_path = (root / plan['ensemble'] / 'manifest.json').resolve()
    manifest = json.loads(manifest_path.read_text())
    manifest_rows = {row['id']: row for row in manifest['configs']}
    with np.load(pion_run / 'development.npz', allow_pickle=False) as data:
        ids = data['ids'].astype(int).tolist()
        generation = str(data['generation'])
        measurement_protocol_hash = str(data['protocol_hash'])
    rows = provenance.get('records', [])
    if ids != list(range(0, 100)) or [row['id'] for row in rows] != ids:
        raise ValueError('Pion development prefix is not exactly IDs 0-99')

    issues = []
    if provenance.get('generation') != generation:
        issues.append({'issue': 'NPZ generation differs from Pion provenance'})
    if provenance.get('protocol_hash') != measurement_protocol_hash:
        issues.append({'issue': 'NPZ protocol hash differs from Pion provenance'})
    if measurement_protocol_hash != plan.get('protocol_sha256'):
        issues.append({'issue': 'measurement protocol hash differs from frozen plan'})
    kappa, residuals, dtype_ok = set(), [], []
    metadata_residuals = 0
    verified_cache = 0
    for row in rows:
        cfg_id = row['id']
        expected_manifest = manifest_rows.get(cfg_id)
        if expected_manifest is None:
            issues.append({'id': cfg_id, 'issue': 'missing HMC manifest row'})
            continue
        if row.get('gauge_sha256') != expected_manifest.get('sha256'):
            issues.append({'id': cfg_id, 'issue': 'Pion gauge SHA differs from frozen HMC manifest'})
        if row.get('trajectory_id') != expected_manifest.get('trajectory'):
            issues.append({'id': cfg_id, 'issue': 'Pion trajectory differs from frozen HMC manifest'})
        key = row.get('cache_key')
        if not key or len(key) != 64:
            issues.append({'id': cfg_id, 'issue': 'missing or invalid propagator cache key'})
            continue
        prop = root / '.cache/pion_projection/propagators' / f'{key}.npy'
        meta_path = prop.with_suffix('.json')
        if not prop.is_file() or not meta_path.is_file():
            issues.append({'id': cfg_id, 'issue': 'propagator array or metadata missing'})
            continue
        meta = json.loads(meta_path.read_text())
        kd = meta.get('keydata', {})
        prop_hash = sha256(prop)
        if prop_hash != row.get('propagator_sha256') or prop_hash != meta.get('array_sha256'):
            issues.append({'id': cfg_id, 'issue': 'propagator byte hash mismatch'})
        if kd.get('gauge') != expected_manifest.get('sha256'):
            issues.append({'id': cfg_id, 'issue': 'cache metadata gauge hash differs from HMC manifest'})
        for name, expected in (('geometry', protocol['geometry']), ('boundary', protocol['t_boundary']),
                               ('tol', protocol['tolerance']), ('maxiter', protocol['max_iterations']),
                               ('source', protocol['source'])):
            if kd.get(name) != expected:
                issues.append({'id': cfg_id, 'issue': f'cache metadata {name} differs from Pion protocol'})
        if kd.get('kappa') is None or float(kd.get('kappa', -1)) != float(protocol['kappa']):
            issues.append({'id': cfg_id, 'issue': 'cache metadata hopping parameter differs from Pion protocol'})
        else:
            kappa.add(float(kd['kappa']))
        residual = row.get('residual_max')
        meta_residual = kd.get('residual_max', meta.get('residual_max'))
        if meta_residual is not None:
            metadata_residuals += 1
            if (not np.isfinite(meta_residual) or abs(float(meta_residual) - float(residual)) > 1e-14):
                issues.append({'id': cfg_id, 'issue': 'cache metadata residual differs from Pion measurement receipt'})
        if residual is None or not np.isfinite(residual) or residual > protocol['tolerance']:
            issues.append({'id': cfg_id, 'issue': 'Pion measurement receipt residual fails frozen tolerance'})
        else:
            residuals.append(float(residual))
        array = np.load(prop, mmap_mode='r', allow_pickle=False)
        dtype_ok.append(str(array.dtype) == 'complex128')
        if prop_hash == row.get('propagator_sha256') == meta.get('array_sha256'):
            verified_cache += 1

    gate_passed = None if submission is None else bool(submission['calibration']['reference_passed'])
    result = {
        'schema': 'optgauss-pion-propagator-reuse-audit-v1',
        'scope': 'read-only crosswalk of D-chain IDs 0-99; no propagator or gauge bytes copied or modified',
        'pion_run': str(pion_run.relative_to(root)),
        'pion_measurement_sha256': sha256(pion_run / 'development.npz'),
        'pion_provenance_sha256': sha256(pion_run / 'development_provenance.json'),
        'measurement_plan_sha256': sha256(plan_path),
        'pion_protocol_sha256': sha256(protocol_path),
        'hmc_manifest_sha256': sha256(manifest_path),
        'ids': {'n': len(ids), 'first': ids[0], 'last': ids[-1], 'cached_propagators_verified': verified_cache},
        'metadata': {'geometry': protocol['geometry'], 'source': protocol['source'], 'boundary': protocol['t_boundary'],
                     'tolerance': protocol['tolerance'], 'max_iterations': protocol['max_iterations'],
                     'kappa_values': sorted(kappa), 'max_residual': max(residuals) if residuals else None,
                     'complex128_count': sum(dtype_ok), 'dtype_checked_count': len(dtype_ok)},
        'identity_issues': issues,
        'reuse_status': 'VERIFIED_FOR_TRAIN_DEV_AFTER_RECEIPT_ADAPTER' if not issues and verified_cache == 100 and len(residuals) == 100 else 'REUSE_BLOCKED',
        'residual_receipt_source': 'per-configuration residual_max in generation-bound Pion development_provenance.json',
        'cache_metadata_residual_count': metadata_residuals,
        'optimizer_validator_adapter_required': True,
        'optimizer_validator_adapter_reason': 'current train.validate_inputs reads residual only from the cache metadata JSON; the Pion cache JSON omits residual_max, while the generation-bound measurement provenance contains it',
        'pion_reference_gate_passed': gate_passed,
        'pion_reference_failures': None if submission is None else submission['calibration']['failure_reasons'],
        'score_scope': 'Propagator reuse only certifies input compatibility. Pion reference gate failure means a risk score using that reference remains diagnostic and cannot be treated as physical.',
        'unread_ranges': ['D IDs 100-139', 'shared D IDs 140-199'],
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / 'reuse_audit.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    status = result['reuse_status']
    text = [
        '# Optimize D-chain propagator reuse audit', '',
        f'**Status: `{status}` for fit/development inputs; Optimize scoring remains diagnostic.**', '',
        f"- Pion point propagators: {verified_cache}/100 byte hashes verified for D IDs 0-99.",
        f"- Metadata: geometry {protocol['geometry']}, point source {protocol['source']}, boundary {protocol['t_boundary']}, kappa {sorted(kappa)}, tolerance {protocol['tolerance']}, max iterations {protocol['max_iterations']}.",
        f"- Maximum recorded inversion residual: `{result['metadata']['max_residual']}`; complex128 arrays: {sum(dtype_ok)}/{len(dtype_ok)}.",
        f"- Frozen D HMC manifest hash: `{result['hmc_manifest_sha256']}`; Pion reference gate: `{gate_passed}`.", '',
        'The cache can avoid repeating point-source inversions for Optimize fit IDs 0-59 and development IDs 60-99 after an Optimize-specific RunSpec binds the same solver settings, cache hashes, objective, and code. Current `train.validate_inputs` needs a small adapter because the cache metadata JSON omits residual_max; the generation-bound Pion measurement provenance supplies the per-configuration residuals. The cache audit does not transfer a Pion score or validate the Optimize observable.',
        '',
        'The Pion D-development reference gate failed. Any optimization risk that uses its single-cosh reference is therefore a method diagnostic only until an independently justified reference passes its gate. This report did not inspect D IDs 100-199; the embargo and shared blind range remain unopened.', '',
        'See `reuse_audit.json` for per-ID mismatches and all source/input hashes.', ''
    ]
    (output / 'README.md').write_text('\n'.join(text))
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
