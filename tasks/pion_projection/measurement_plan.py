"""Frozen measurement-plan validation and resumable checkpoint preflight.

This module imports no accelerator stack.  It is deliberately safe to call
before CuPy, MPI, or PyQUDA is imported.
"""
import hashlib
import json
import re
from pathlib import Path

import numpy as np

from .common import fingerprint, protocol

REQUIRED = ('schema', 'ensemble', 'geometry', 'sources', 'sink_powers', 'splits',
            'identity', 'checks', 'statistics', 'freeze', 'budget', 'stop_rules',
            'status', 'protocol_sha256', 'split_ensembles')
HEX = re.compile(r'^[0-9a-f]{64}$')
STATUSES = ('NOT_RUN', 'READY')


def _canonical_sha(value):
    payload = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def _ranges(splits, split_ensembles=None, default_ensemble=None):
    split_ensembles = split_ensembles or {}
    rows = []
    for name, value in splits.items():
        if not (isinstance(value, list) and len(value) == 2
                and all(isinstance(v, int) for v in value)):
            raise ValueError(f'split {name!r} must be [first, last]')
        first, last = value
        if first < 0 or last < first:
            raise ValueError(f'split {name!r} must be a non-empty nonnegative range')
        rows.append((name, first, last))
    for i, (name_a, a0, a1) in enumerate(rows):
        for name_b, b0, b1 in rows[i + 1:]:
            ensemble_a = split_ensembles.get(name_a, default_ensemble)
            ensemble_b = split_ensembles.get(name_b, default_ensemble)
            if ensemble_a == ensemble_b and not (a1 < b0 or b1 < a0):
                raise ValueError(f'splits {name_a!r} and {name_b!r} overlap')
    return rows


def validate_plan(plan):
    missing = [key for key in REQUIRED if key not in plan]
    if missing:
        raise ValueError(f'measurement plan is missing {missing}')
    if plan['schema'] != 'pion-measurement-plan-v1':
        raise ValueError(f'unsupported plan schema {plan["schema"]!r}')
    if plan['status'] not in STATUSES:
        raise ValueError(f'unsupported status {plan["status"]!r}; use READY for a frozen plan')
    if not plan['sources'] or not plan['sink_powers']:
        raise ValueError('sources and sink_powers must be non-empty')
    for key in ('development', 'validation'):
        if key not in plan['splits']:
            raise ValueError(f'splits must declare {key}')
    if not isinstance(plan['split_ensembles'], dict):
        raise ValueError('split_ensembles must be a mapping')
    unknown_ensembles = set(plan['split_ensembles']) - set(plan['splits'])
    if unknown_ensembles:
        raise ValueError(f'split_ensembles contains undeclared splits {sorted(unknown_ensembles)}')
    _ranges(plan['splits'], plan['split_ensembles'], plan['ensemble'])
    split_available = plan.get('budget', {}).get('split_available_configurations', {})
    available = plan.get('budget', {}).get('available_configurations')
    for name, (first, last) in plan['splits'].items():
        split_limit = split_available.get(name, available)
        if split_limit is not None:
            if last >= split_limit:
                raise ValueError(f'split {name!r} exceeds the available configurations ({split_limit})')
    geometry = plan['geometry']
    if not (isinstance(geometry, list) and len(geometry) == 4
            and all(isinstance(v, int) and v > 0 for v in geometry)):
        raise ValueError('geometry must be four positive integers')
    if geometry[3] % 2:
        raise ValueError('an even time extent is required for the cosh fold')
    identity = plan['identity']
    for key in ('gauge_sha256', 'propagator_sha256', 'quda', 'device',
                'precision', 'trajectory_ids'):
        if not isinstance(identity.get(key), str) or not identity[key].strip():
            raise ValueError(f'identity must describe {key}')
    if not HEX.match(str(plan['protocol_sha256'])):
        if plan['status'] == 'READY':
            raise ValueError('protocol_sha256 must be a real SHA-256 for a READY plan')
    if plan['status'] == 'READY':
        frozen_at = plan['freeze'].get('frozen_at_utc')
        if not isinstance(frozen_at, str) or not frozen_at.strip():
            raise ValueError('READY plan must record freeze.frozen_at_utc')
        if plan['identity'].get('require_trajectory_manifest') is not True:
            raise ValueError('READY plan must require a trajectory manifest')
    if not isinstance(plan['stop_rules'], list) or not plan['stop_rules']:
        raise ValueError('stop_rules must be a non-empty list')
    if not isinstance(plan['freeze'], dict) or not plan['freeze']:
        raise ValueError('freeze must be a non-empty mapping')
    return plan


def load_plan(path):
    return validate_plan(json.loads(Path(path).read_text()))


def generation_id(plan_path, split, p=None):
    """Hash the frozen plan, protocol, split and measurement implementation."""
    plan_path = Path(plan_path)
    plan = load_plan(plan_path)
    p = p or protocol()
    if plan['protocol_sha256'] != fingerprint(p):
        raise ValueError('measurement protocol hash differs from the frozen plan')
    source_names = ('measure.py', 'kernels.py', 'statistics.py', 'experiment.py',
                    'reference.py', 'identity.py', 'anchor_review.py')
    return _canonical_sha({
        'plan_sha256': hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        'protocol_sha256': fingerprint(p),
        'split': split,
        'source_sha256': {
            name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in source_names
        },
    })


def _trajectory_map(plan, split):
    ensemble = plan['split_ensembles'].get(split, plan['ensemble'])
    manifest = Path(ensemble) / 'manifest.json'
    if not manifest.is_file():
        raise ValueError(f'trajectory manifest is missing: {manifest}')
    record = json.loads(manifest.read_text())
    configs = record.get('configs')
    if not isinstance(configs, list):
        raise ValueError('trajectory manifest has no configs list')
    by_id = {}
    for row in configs:
        cfg_id = row.get('id')
        trajectory = row.get('trajectory')
        digest = row.get('sha256')
        if not isinstance(cfg_id, int) or not isinstance(trajectory, int) or not HEX.match(str(digest)):
            raise ValueError('trajectory manifest contains an invalid config row')
        if cfg_id in by_id:
            raise ValueError(f'trajectory manifest repeats configuration id {cfg_id}')
        by_id[cfg_id] = row
    first, last = plan['splits'][split]
    missing = [cfg_id for cfg_id in range(first, last + 1) if cfg_id not in by_id]
    if missing:
        raise ValueError(f'trajectory manifest lacks split configuration ids: {missing[:8]}')
    return by_id


def _check_checkpoint(output, split, plan, generation, p, trajectory_rows, limit=None):
    output = Path(output)
    data_path = output / f'{split}.npz'
    provenance_path = output / f'{split}_provenance.json'
    if not data_path.exists():
        if provenance_path.exists():
            raise ValueError('provenance exists without its measurement checkpoint')
        return 0
    if not provenance_path.is_file():
        raise ValueError('measurement checkpoint has no provenance receipt')
    first, last = plan['splits'][split]
    expected = np.arange(first, last + 1, dtype=int)
    if limit is not None:
        expected = expected[:limit]
    with np.load(data_path, allow_pickle=False) as data:
        required = ('ids', 'correlators', 'protocol_hash', 'generation')
        missing = [key for key in required if key not in data]
        if missing:
            raise ValueError(f'measurement checkpoint is missing {missing}')
        ids = np.asarray(data['ids'], dtype=int)
        corr = np.asarray(data['correlators'])
        if str(data['generation']) != generation:
            raise ValueError('measurement checkpoint generation differs from the frozen plan')
        if str(data['protocol_hash']) != fingerprint(p):
            raise ValueError('measurement checkpoint protocol differs from the frozen plan')
        if ids.ndim != 1 or len(ids) > len(expected) or not np.array_equal(ids, expected[:len(ids)]):
            raise ValueError('measurement checkpoint IDs are not a prefix of the frozen split')
        if corr.shape != (len(ids), len(p['powers']), p['geometry'][3]):
            raise ValueError('measurement checkpoint correlator shape is inconsistent')
        if not np.all(np.isfinite(corr)) or np.any(corr <= 0):
            raise ValueError('measurement checkpoint contains non-finite or nonpositive correlators')
        count = len(ids)
    provenance = json.loads(provenance_path.read_text())
    if provenance.get('generation') != generation:
        raise ValueError('measurement provenance generation differs from the frozen plan')
    if provenance.get('protocol_hash') != fingerprint(p):
        raise ValueError('measurement provenance protocol differs from the frozen plan')
    rows = provenance.get('records')
    if not isinstance(rows, list) or len(rows) < count:
        raise ValueError('measurement provenance is shorter than its correlator checkpoint')
    if [row.get('id') for row in rows[:count]] != expected[:count].tolist():
        raise ValueError('measurement provenance IDs differ from checkpoint IDs')
    for row in rows[:count]:
        cfg_id = row['id']
        expected_input = trajectory_rows[cfg_id]
        expected_ensemble = str(Path(plan['split_ensembles'].get(split, plan['ensemble'])))
        if row.get('ensemble') != expected_ensemble:
            raise ValueError(f'measurement provenance ensemble differs for ID {cfg_id}')
        if (not HEX.match(str(row.get('gauge_sha256')))
                or row['gauge_sha256'] != expected_input['sha256']):
            raise ValueError(f'measurement provenance gauge hash differs for ID {cfg_id}')
        if not HEX.match(str(row.get('propagator_sha256'))):
            raise ValueError(f'measurement provenance lacks propagator hash for ID {cfg_id}')
        if row.get('trajectory_id') != expected_input['trajectory']:
            raise ValueError(f'measurement provenance trajectory differs for ID {cfg_id}')
        residual = row.get('residual_max')
        if not isinstance(residual, (int, float)) or not np.isfinite(residual) or residual > p['tolerance']:
            raise ValueError(f'measurement provenance residual fails for ID {cfg_id}')
    return count


def preflight(plan_path, output, split='development', limit=None):
    """Validate plan and checkpoint before importing any accelerator library."""
    plan = load_plan(plan_path)
    if plan['status'] == 'NOT_RUN':
        raise ValueError('plan status is NOT_RUN (draft); refusing to start a measurement')
    if split not in plan['splits']:
        raise ValueError(f'split {split!r} is not declared by the frozen plan')
    p = protocol()
    if Path(plan['ensemble']).resolve() != Path(p['ensemble']).resolve():
        raise ValueError('plan ensemble path differs from the frozen measurement protocol')
    if plan['geometry'] != p['geometry'] or plan['sink_powers'] != p['powers']:
        raise ValueError('plan geometry or sink powers differ from the frozen measurement protocol')
    if plan['sources'] != ['point'] or p['source'] != [0, 0, 0, 0]:
        raise ValueError('this measurement runner supports only a point source at the origin')
    generation = generation_id(plan_path, split, p)
    trajectory_rows = _trajectory_map(plan, split)
    _check_checkpoint(output, split, plan, generation, p, trajectory_rows, limit=limit)
    output = Path(output)
    if split == 'development' and any((output / f'{name}.npz').exists()
                                      for name in ('anchor', 'validation')):
        raise ValueError('development cannot be reopened after holdout measurements exist')
    if split in ('anchor', 'validation'):
        submission = output / 'submission.json'
        development = output / 'development.npz'
        if not submission.is_file() or not development.is_file():
            raise ValueError(f'{split} requires a frozen submission and development measurement')
        frozen = json.loads(submission.read_text())
        development_hash = hashlib.sha256(development.read_bytes()).hexdigest()
        if frozen.get('protocol_hash') != fingerprint(p):
            raise ValueError('submission protocol mismatch')
        if frozen.get('development_sha256') != development_hash:
            raise ValueError('development measurements changed after submission freeze')
        dev_generation = generation_id(plan_path, 'development', p)
        dev_trajectory_rows = _trajectory_map(plan, 'development')
        dev_count = _check_checkpoint(output, 'development', plan, dev_generation, p,
                                      dev_trajectory_rows)
        first, last = plan['splits']['development']
        if dev_count != last - first + 1:
            raise ValueError('development measurements are incomplete')
    if split == 'validation' and 'anchor' in plan['splits']:
        anchor_report_path = output / 'anchor_results.json'
        anchor_data_path = output / 'anchor.npz'
        if not anchor_report_path.is_file() or not anchor_data_path.is_file():
            raise ValueError('validation requires a completed independent-anchor diagnostic')
        anchor_generation = generation_id(plan_path, 'anchor', p)
        anchor_trajectory_rows = _trajectory_map(plan, 'anchor')
        anchor_count = _check_checkpoint(output, 'anchor', plan, anchor_generation, p,
                                         anchor_trajectory_rows)
        anchor_first, anchor_last = plan['splits']['anchor']
        if anchor_count != anchor_last - anchor_first + 1:
            raise ValueError('independent-anchor measurements are incomplete')
        anchor_report = json.loads(anchor_report_path.read_text())
        if anchor_report.get('schema') != 'pion-independent-anchor-review-v1':
            raise ValueError('validation requires the recognized independent-anchor report schema')
        if anchor_report.get('anchor_sha256') != hashlib.sha256(anchor_data_path.read_bytes()).hexdigest():
            raise ValueError('anchor diagnostic does not match the frozen anchor measurements')
        if anchor_report.get('development_sha256') != hashlib.sha256(development.read_bytes()).hexdigest():
            raise ValueError('anchor diagnostic does not match the frozen development measurements')
        if anchor_report.get('submission_sha256') != hashlib.sha256(submission.read_bytes()).hexdigest():
            raise ValueError('anchor diagnostic does not match the frozen submission')
        if anchor_report.get('plan_sha256') != hashlib.sha256(Path(plan_path).read_bytes()).hexdigest():
            raise ValueError('anchor diagnostic does not match the frozen measurement plan')
        if anchor_report.get('protocol_sha256') != fingerprint(p):
            raise ValueError('anchor diagnostic does not match the frozen protocol')
        if anchor_report.get('measurement_generation') != anchor_generation:
            raise ValueError('anchor diagnostic does not match the anchor measurement generation')
        if anchor_report.get('physical_score') is not None:
            raise ValueError('independent-anchor diagnostic must not issue a physical score')
        if anchor_report.get('anchor_reference_passed') is not True:
            raise ValueError('independent-anchor reference gate failed; refusing to open blind validation')
    return plan
