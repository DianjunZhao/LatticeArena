"""Measure Wilson loops W(R,T) from smeared spatial lines and original temporal links."""
from pathlib import Path
from time import perf_counter

import numpy as np

from .common import fingerprint, indices, protocol, read_nersc, write_json
from .kernels import _lib, build_kernel, dagger, shift


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


def measure(output, split, limit=None):
    p = protocol()
    try:
        import cupy as xp
    except ImportError:
        xp = np
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    ids = indices(split)[:limit] if limit else indices(split)
    rows, records = [], []
    for cfg in ids:
        start = perf_counter()
        u = xp.asarray(read_nersc(Path(p['ensemble']) / f'wilson_b6.{cfg}'))
        rows.append([loops(build_kernel(u[:3], k), u[3], p) for k in p['kernels']])
        records.append({'id': int(cfg), 'seconds': perf_counter() - start})
        np.savez_compressed(output / f'{split}.npz', ids=ids[:len(rows)],
                            loops=np.asarray(rows), protocol_hash=fingerprint(p))
        write_json(output / f'{split}_provenance.json', {'protocol': p, 'records': records})
        print(f'cfg {cfg}: {records[-1]["seconds"]:.2f}s', flush=True)
    return records
