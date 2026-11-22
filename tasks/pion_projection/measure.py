"""Trusted one-rank PyQUDA measurement and checked point-propagator cache."""
import json
import os
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from time import perf_counter

import numpy as np

from .common import digest, fingerprint, indices, protocol, write_json


def _save_checkpoint(path, ids, correlators, protocol_hash, generation):
    path = Path(path)
    temporary = path.with_name(path.stem + '.tmp.npz')
    with temporary.open('wb') as stream:
        np.savez_compressed(stream, ids=np.asarray(ids, dtype=int),
                            correlators=np.asarray(correlators),
                            protocol_hash=protocol_hash, generation=generation)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def measure(output, split, limit=None, plan=None):
    plan_path = plan or os.environ.get('PION_MEASUREMENT_PLAN')
    legacy = plan_path is None
    if legacy and os.environ.get('PION_LEGACY_MEASUREMENT') != '1':
        raise ValueError('a measurement plan is required before any GPU initialisation; '
                         'pass --plan or PION_MEASUREMENT_PLAN '
                         '(legacy: PION_LEGACY_MEASUREMENT=1)')

    p = protocol()
    output = Path(output)
    generation = fingerprint({'protocol': fingerprint(p), 'split': split,
                              'legacy': True})
    plan_data = None
    trajectory_rows = {}
    if not legacy:
        from .measurement_plan import (
            _trajectory_map, generation_id, preflight,
        )
        plan_data = preflight(plan_path, output, split, limit=limit)
        generation = generation_id(plan_path, split, p)
        trajectory_rows = _trajectory_map(plan_data, split)

    if plan_data is not None:
        first, last = plan_data['splits'][split]
        ids = np.arange(first, last + 1, dtype=int)
        ensemble_path = Path(plan_data['split_ensembles'].get(split, plan_data['ensemble']))
    else:
        ids = indices(split)
        ensemble_path = Path(p['ensemble'])
    if limit is not None:
        ids = ids[:limit]
    records, correlators = [], []
    data_path = output / f'{split}.npz'
    provenance_path = output / f'{split}_provenance.json'
    if data_path.exists():
        with np.load(data_path, allow_pickle=False) as saved:
            records_data = json.loads(provenance_path.read_text())
            saved_ids = np.asarray(saved['ids'], dtype=int)
            records = records_data['records'][:len(saved_ids)]
            correlators = list(np.asarray(saved['correlators']))
        if len(saved_ids) != len(records):
            raise ValueError('checkpoint and provenance lengths disagree')
        if len(saved_ids) == len(ids):
            print(json.dumps({'status': 'already_complete', 'split': split,
                              'generation': generation, 'completed': len(ids)}), flush=True)
            return records

    output.mkdir(parents=True, exist_ok=True)
    cache = Path('.cache/pion_projection/propagators')
    cache.mkdir(parents=True, exist_ok=True)
    Path('.cache/quda').mkdir(parents=True, exist_ok=True)

    # This import boundary is intentionally below all plan, identity, split,
    # checkpoint, and validation-submission checks.
    import cupy as cp
    from mpi4py import MPI
    from pyquda_utils import core, io, source
    from pyquda.enum_quda import QudaVerbosity

    core.init([1, 1, 1, 1], p['geometry'], resource_path='.cache/quda')
    if MPI.COMM_WORLD.Get_size() != 1:
        raise ValueError('Pilot supports one MPI rank')
    cp.get_default_memory_pool().set_limit(size=p['gpu_memory_limit_gib'] * 1024**3)
    software = {}
    for name in ['PyQUDA', 'PyQUDA-Utils', 'cupy-cuda12x', 'cupy', 'numpy', 'mpi4py']:
        try:
            software[name] = version(name)
        except PackageNotFoundError:
            software[name] = 'unavailable'
    quda_lib = Path(os.environ.get('QUDA_PATH', '')) / 'lib' / 'libquda.so'
    software['libquda_sha256'] = digest(quda_lib) if quda_lib.is_file() else 'unavailable'
    software['mpi'] = MPI.Get_library_version().strip('\x00\n')
    software['measurement_sha256'] = digest(__file__)
    software['kernel_sha256'] = digest(Path(__file__).with_name('kernels.py'))
    latt = core.LatticeInfo(p['geometry'], p['t_boundary'], 1.0)
    dirac = core.getWilson(latt, 1/(2*p['kappa'])-4, p['tolerance'], p['max_iterations'])
    dirac.setVerbosity(QudaVerbosity.QUDA_SILENT)

    for cfg_id in ids[len(records):]:
        begin = perf_counter()
        filename = ensemble_path / f'wilson_b6.{cfg_id}'
        cfg_hash = digest(filename)
        manifest_row = trajectory_rows.get(int(cfg_id))
        if manifest_row is not None and cfg_hash != manifest_row['sha256']:
            raise ValueError(f'Gauge hash differs from trajectory manifest for ID {cfg_id}')
        keydata = {'gauge': cfg_hash, 'geometry': p['geometry'], 'kappa': p['kappa'],
                   'boundary': p['t_boundary'], 'source': p['source'], 'tol': p['tolerance'],
                   'maxiter': p['max_iterations'], 'software': software}
        key = fingerprint(keydata)
        cachefile = cache / f'{key}.npy'
        metafile = cache / f'{key}.json'
        gauge = io.readNERSCGauge(str(filename))
        if gauge.latt_info.global_size != p['geometry']:
            raise ValueError('Wrong geometry')
        plaq = float(gauge.plaquette()[0])
        cache_hit = cachefile.exists() and metafile.exists()
        with dirac.useGauge(gauge):
            solve_start = perf_counter()
            if cache_hit:
                metadata = json.loads(metafile.read_text())
                if metadata['keydata'] != keydata or digest(cachefile) != metadata['array_sha256']:
                    raise ValueError('Cache provenance/checksum mismatch')
                prop = core.LatticePropagator(latt, cp.asarray(np.load(cachefile, allow_pickle=False)))
            else:
                prop = core.invert(dirac, 'point', p['source'])
            residuals = []
            for spin in range(4):
                for color in range(3):
                    b = source.source(latt, 'point', p['source'], spin, color)
                    r = dirac.mat(prop.getFermion(spin, color)) - b
                    residuals.append(float((r.norm2()/b.norm2())**0.5))
            if not np.all(np.isfinite(residuals)) or max(residuals) > p['tolerance']:
                raise ValueError(f'Failed residual check for {filename}: {residuals}')
            solve_seconds = perf_counter() - solve_start
        if not cache_hit:
            tmp = cachefile.with_suffix('.tmp.npy')
            np.save(tmp, prop.getHost(), allow_pickle=False)
            tmp.replace(cachefile)
            write_json(metafile, {'keydata': keydata, 'array_sha256': digest(cachefile)})
        propagator_hash = digest(cachefile)
        sink_start = perf_counter()
        c = np.zeros((len(p['powers']), p['geometry'][3]))
        # H is Hermitian: <S,H^(2n)S> = ||H^n S||^2. Incremental QUDA
        # smearing is an exact fast path for these even diffusion powers.
        with gauge.use() as gdirac:
            for spin in range(4):
                for color in range(3):
                    field = prop.getFermion(spin, color)
                    previous = 0
                    for j, power in enumerate(p['powers']):
                        n = power // 2
                        if power % 2:
                            raise ValueError('QUDA fast path requires even powers')
                        if n > previous:
                            field = gdirac.wuppertalSmear(field, n-previous, p['alpha'])
                        density = cp.sum(cp.abs(field.data)**2, axis=(-2, -1))
                        c[j] += density.sum(axis=(0, 2, 3, 4)).get()
                        previous = n
        direct = cp.sum(cp.abs(prop.data)**2, axis=(-4, -3, -2, -1)).sum(axis=(0, 2, 3, 4)).get()
        np.testing.assert_allclose(c[0], direct, rtol=1e-12, atol=0)
        if not np.all(np.isfinite(c)) or np.any(c <= 0):
            raise ValueError('Invalid basis correlator')
        # Independently check the generic submitted-kernel route on each new split.
        if len(records) == 0:
            from .kernels import build_kernel
            links = gauge.lexico(force_numpy=False)[:3, 2]
            lexico = prop.lexico(force_numpy=False)[2]
            field = lexico.transpose(0, 1, 2, 5, 3, 4, 6).reshape(16, 16, 16, 3, 48)
            kernel = build_kernel(links, {'powers': [2], 'weights': [1.0], 'alpha': p['alpha']})
            reference = cp.vdot(field, kernel.apply(field)).get()
            np.testing.assert_allclose(reference, c[1, 2], rtol=1e-10, atol=1e-13)
        cp.cuda.Stream.null.synchronize()
        elapsed = perf_counter() - begin
        if elapsed > p['wall_seconds_per_configuration']:
            raise RuntimeError('Configuration wall-time budget exceeded')
        record = {
            'id': int(cfg_id),
            'ensemble': str(ensemble_path),
            'trajectory_id': manifest_row['trajectory'] if manifest_row is not None else None,
            'gauge_sha256': cfg_hash,
            'propagator_sha256': propagator_hash,
            'plaquette': plaq,
            'residual_max': max(residuals),
            'cache_key': key,
            'cache_hit': cache_hit,
            'solve_and_residual_seconds': solve_seconds,
            'sink_seconds': perf_counter()-sink_start,
            'total_seconds': elapsed,
            'cupy_pool_peak_reserved_bytes': cp.get_default_memory_pool().total_bytes(),
        }
        records.append(record)
        correlators.append(c)
        print(json.dumps(record), flush=True)
        # Write provenance first; if interrupted before the atomic array replace,
        # preflight safely ignores the unmatched final provenance row.
        write_json(provenance_path, {
            'plan_path': str(plan_path) if not legacy else None,
            'generation': generation,
            'protocol_hash': fingerprint(p),
            'protocol': p,
            'software': software,
            'records': records,
        })
        _save_checkpoint(data_path, ids[:len(records)], correlators,
                         fingerprint(p), generation)
        del prop, gauge
    return records
