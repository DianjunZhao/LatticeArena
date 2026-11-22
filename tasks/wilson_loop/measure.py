"""Measure Wilson loops W(R,T) from smeared spatial lines and original temporal links."""
import os
import subprocess
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from .common import digest, fingerprint, indices_for, protocol, read_nersc_with_status, write_json
from core.ledger import Ledger

from .identity import check_resume, generation, loops_sha256, measurement_spec, write_marker
from .kernels import _lib, build_kernel, dagger, shift


def measurement_input_manifest(p, split, ids):
    """Validate the frozen input manifest and resolve only the requested IDs.

    Returns a map of saved-configuration ID to manifest row. Legacy protocols
    without an explicit input_manifest keep their historical behavior. This
    check is metadata-only; per-file raw hashes are compared during the normal
    NERSC read, before the input is copied to a GPU.
    """
    allowed_splits = p.get('measurement_splits', ['development', 'gap', 'validation'])
    if split not in allowed_splits:
        raise ValueError(f'{split}: split is not authorized for measurement')
    if split not in p or len(p[split]) != 2:
        raise ValueError(f'{split}: no inclusive ID range in protocol')
    first, last = p[split]
    if any(type(cfg) is not int or not first <= cfg <= last for cfg in ids):
        raise ValueError(f'{split}: requested IDs escape the frozen split')

    spec = p.get('input_manifest')
    if spec is None:
        return None
    source_hashes = p.get('source_hashes', {})
    if not isinstance(source_hashes, dict) or not source_hashes:
        raise ValueError('frozen source hashes are required with an input manifest')
    for name, expected_hash in source_hashes.items():
        if Path(name).name != name:
            raise ValueError(f'invalid task source path {name!r}')
        source_path = Path(__file__).with_name(name)
        if not source_path.is_file() or digest(source_path) != expected_hash:
            raise ValueError(f'task source hash mismatch: {name}')
    manifest_path = Path(spec['path'])
    expected_manifest_sha = spec['sha256']
    if not manifest_path.is_file():
        raise ValueError(f'input manifest missing: {manifest_path}')
    actual_manifest_sha = digest(manifest_path)
    if actual_manifest_sha != expected_manifest_sha:
        raise ValueError('input manifest hash mismatch')
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('schema') != spec.get('schema'):
        raise ValueError('input manifest schema mismatch')
    if manifest.get('ensemble') != spec.get('ensemble'):
        raise ValueError('input manifest ensemble mismatch')
    if manifest.get('lattice') != p.get('geometry'):
        raise ValueError('input manifest geometry mismatch')
    if 'beta' in spec and manifest.get('beta') != spec['beta']:
        raise ValueError('input manifest beta mismatch')
    if 'hmc_seed' in spec and manifest.get('seed') != spec['hmc_seed']:
        raise ValueError('input manifest HMC seed mismatch')
    configs = manifest.get('configs')
    if not isinstance(configs, list):
        raise ValueError('input manifest has no configuration table')
    requested = set(ids)
    seen = set()
    by_id = {}
    for row in configs:
        cfg = row.get('id') if isinstance(row, dict) else None
        if type(cfg) is not int or cfg in seen:
            raise ValueError('input manifest has invalid or duplicate configuration IDs')
        seen.add(cfg)
        if cfg not in requested:
            continue
        raw_sha = row.get('sha256')
        if not isinstance(raw_sha, str) or len(raw_sha) != 64:
            raise ValueError(f'input manifest has invalid raw hash for cfg {cfg}')
        try:
            int(raw_sha, 16)
        except ValueError as exc:
            raise ValueError(f'input manifest has invalid raw hash for cfg {cfg}') from exc
        if type(row.get('trajectory')) is not int:
            raise ValueError(f'input manifest has invalid trajectory for cfg {cfg}')
        by_id[cfg] = {key: row.get(key) for key in ('id', 'trajectory', 'sha256')}
    missing = [cfg for cfg in ids if cfg not in by_id]
    if missing:
        raise ValueError(f'input manifest does not contain requested IDs: {missing[:8]}')
    missing_files = [cfg for cfg in ids
                     if not (Path(p['ensemble']) / f'wilson_b6.{cfg}').is_file()]
    if missing_files:
        raise ValueError(f'raw gauge files missing for requested IDs: {missing_files[:8]}')
    return {cfg: by_id[cfg] for cfg in ids}


def loops(links, temporal, p):
    """links/temporal: (t, z, y, x, 3, 3); returns W with shape (len(R), len(T))."""
    R_list, T_list = p['r_values'], p['t_values']
    xp = _lib(links)
    out = xp.zeros((len(R_list), len(T_list)))
    volume = float(np.prod(temporal.shape[:4]))
    for d in range(3):
        axis = 3 - d
        K, cur = {1: links[d].copy()}, links[d].copy()
        for R in range(2, max(R_list) + 1):
            cur = shift(cur, 1, axis)
            K[R] = K[R - 1] @ cur
        P, cur = {1: temporal.copy()}, temporal.copy()
        for T in range(2, max(T_list) + 1):
            cur = shift(cur, 1, 0)
            P[T] = P[T - 1] @ cur
        for i, R in enumerate(R_list):
            for j, T in enumerate(T_list):
                w = K[R] @ shift(P[T], R, axis) @ dagger(shift(K[R], T, 0)) @ dagger(P[T])
                out[i, j] += xp.trace(w, axis1=-2, axis2=-1).real.sum()
    out = out / (9 * volume)
    return out.get() if hasattr(out, 'get') else out


def git_state():
    try:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True,
                                         stderr=subprocess.DEVNULL).strip()
        dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], text=True,
                                             stderr=subprocess.DEVNULL).strip())
        return {'commit': commit, 'dirty': dirty}
    except (OSError, subprocess.CalledProcessError):
        return {'commit': 'unavailable', 'dirty': None}


def synchronize(xp):
    """Make wall-time measurements include queued CuPy work."""
    if xp is not np:
        xp.cuda.get_current_stream().synchronize()


def measure(output, split, limit=None, stop_after=None):
    p = protocol()
    ids = indices_for(p, split)
    if limit is not None:
        if type(limit) is not int or limit < 1:
            raise ValueError('limit must be a positive integer')
        ids = ids[:limit]
    manifest_rows = measurement_input_manifest(p, split, ids.tolist())
    try:
        import cupy as xp
    except ImportError:
        xp = np
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    spec = measurement_spec(p, split)
    if limit:
        spec = dict(spec, ids=spec['ids'][:limit])
    completed = check_resume(output, split, spec)
    if completed:
        print(f'resuming {split} from row {completed}/{len(ids)}', flush=True)
    pending = ids[completed:]
    rows, records, previous_ledger = [], [], None
    if completed:
        with np.load(output / f'{split}.npz', allow_pickle=False) as f:
            rows = f['loops'].tolist()
        provenance = json.loads((output / f'{split}_provenance.json').read_text())
        records = provenance['records'][:completed]
        previous_ledger = provenance.get('ledger')
    kernel_sha = digest(Path(__file__).with_name('kernels.py'))
    ledger = Ledger(device='cupy' if xp is not np else 'cpu', precision='complex128', parallel=1)
    for cfg in pending:
        gauge_path = Path(p['ensemble']) / f'wilson_b6.{cfg}'
        cfg_start = perf_counter()
        read_start = perf_counter()
        u, checksum_status = read_nersc_with_status(gauge_path, expected_geometry=p['geometry'])
        gauge_sha256 = checksum_status.get('raw_sha256') or digest(gauge_path)
        expected_manifest_row = None if manifest_rows is None else manifest_rows[int(cfg)]
        if expected_manifest_row is not None and gauge_sha256 != expected_manifest_row['sha256']:
            raise ValueError(f'cfg {cfg}: raw gauge SHA-256 differs from frozen HMC manifest')
        host_read_seconds = perf_counter() - read_start
        transfer_start = perf_counter()
        u = xp.asarray(u)
        synchronize(xp)
        device_transfer_seconds = perf_counter() - transfer_start
        kernel_seconds_by_candidate = {}
        loop_seconds_by_candidate = {}
        row = []
        for kernel_spec in p['kernels']:
            try:
                kernel_start = perf_counter()
                smeared = build_kernel(u[:3], kernel_spec)
                synchronize(xp)
                kernel_seconds_by_candidate[kernel_spec['name']] = perf_counter() - kernel_start
                loop_start = perf_counter()
                row.append(loops(smeared, u[3], p))
                synchronize(xp)
                loop_seconds_by_candidate[kernel_spec['name']] = perf_counter() - loop_start
            except ValueError as exc:
                raise ValueError(f'cfg {cfg}, kernel {kernel_spec["name"]}: {exc}') from exc
        rows.append(row)
        setup = host_read_seconds + device_transfer_seconds
        kernel_seconds = sum(kernel_seconds_by_candidate.values())
        loop_seconds = sum(loop_seconds_by_candidate.values())
        measure_seconds = kernel_seconds + loop_seconds
        # The shared ledger's kernel phase is the coarse Wilson measurement total;
        # provenance records retain smearing and loop-contraction subphases.
        ledger.add('setup', setup).add('kernel', measure_seconds)
        records.append({'id': int(cfg), 'gauge_path': str(gauge_path), 'checksum_status': checksum_status,
                        'gauge_sha256': gauge_sha256,
                        'hmc_trajectory': None if expected_manifest_row is None else expected_manifest_row.get('trajectory'),
                        'loops_sha256': loops_sha256(np.asarray(row)),
                        'setup_seconds': setup, 'host_read_seconds': host_read_seconds,
                        'device_transfer_seconds': device_transfer_seconds,
                        'kernel_seconds': kernel_seconds, 'loop_seconds': loop_seconds,
                        'kernel_seconds_by_candidate': kernel_seconds_by_candidate,
                        'loop_seconds_by_candidate': loop_seconds_by_candidate,
                        'measure_seconds': measure_seconds,
                        'total_seconds': perf_counter() - cfg_start})
        saved = len(rows)                      # rows holds the full prefix, not only new rows
        if saved != len(records) or [r['id'] for r in records] != spec['ids'][:saved]:
            raise RuntimeError(f'row accounting mismatch: {saved=} {len(records)=} '
                               f'ids={[r["id"] for r in records]} expected={spec["ids"][:saved]}')
        tmp = output / f'.{split}.tmp.npz'
        np.savez_compressed(tmp, ids=np.asarray(spec['ids'][:saved]),
                            loops=np.asarray(rows), protocol_hash=fingerprint(p),
                            generation=generation(spec))
        os.replace(tmp, output / f'{split}.npz')
        write_json(output / f'{split}_provenance.json',
                   {'protocol': p, 'kernel_sha256': kernel_sha, 'ensemble': p['ensemble'],
                    'input_manifest_sha256': None if p.get('input_manifest') is None
                    else p['input_manifest']['sha256'],
                    'git': git_state(), 'generation': generation(spec),
                    'dependencies': {name: digest(Path(__file__).with_name(name))
                                     for name in ('kernels.py', 'statistics.py', 'measure.py',
                                                  'common.py', 'identity.py')},
                    'records': records,
                    'ledger': {'incremental': bool(completed), 'current': ledger.summary(),
                               'previous': previous_ledger}})
        write_marker(output, split, output / f'{split}.npz', output / f'{split}_provenance.json',
                     spec, np.asarray(rows))
        print(f'cfg {cfg}: {records[-1]["total_seconds"]:.2f}s', flush=True)
        if stop_after is not None and len(records) >= stop_after and len(records) < len(spec['ids']):
            print(f'interrupted after {len(records)}/{len(spec["ids"])} rows (test hook)', flush=True)
            raise KeyboardInterrupt('stop_after reached with a complete transaction')
    return records
