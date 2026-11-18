import json
import os
from pathlib import Path

import numpy as np

from core.io import digest, fingerprint, write_json  # noqa: F401  (re-export)

HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = Path('results/wilson_loop/s16t16_v1')
PROTOCOL_PATH = Path(os.environ.get('WILSON_PROTOCOL', str(HERE / 'protocol.json')))


def protocol():
    return json.loads(PROTOCOL_PATH.read_text())


def indices(split):
    first, last = protocol()[split]
    return np.arange(first, last + 1)


def read_nersc(path):
    """Read a NERSC 4D_SU3_GAUGE_3x3 file into (mu, t, z, y, x, 3, 3).

    Validates the header keys we rely on and the exact payload length; unknown
    optional keys are tolerated, but a wrong data type or truncated payload is
    rejected instead of being reshaped silently.
    """
    with open(path, 'rb') as f:
        f.readline()
        header = {}
        while True:
            line = f.readline()
            if not line:
                raise ValueError(f'{path}: missing END_HEADER')
            if line.strip() == b'END_HEADER':
                break
            key, value = line.decode().split('=', 1)
            header[key.strip()] = value.strip()
        payload = f.read()
    try:
        nx, ny, nz, nt = (int(header[f'DIMENSION_{i}']) for i in (1, 2, 3, 4))
    except (KeyError, ValueError) as exc:
        raise ValueError(f'{path}: incomplete NERSC dimension header') from exc
    datatype = header.get('DATATYPE')
    if datatype is not None and not datatype.startswith('4D_SU3_GAUGE_3x3'):
        raise ValueError(f'{path}: unsupported DATATYPE {datatype!r}')
    floating = header.get('FLOATING_POINT')
    if floating is not None and floating.lower() not in ('1', 'true', 'yes'):
        raise ValueError(f'{path}: unsupported FLOATING_POINT {floating!r}')
    expected = nt * nz * ny * nx * 4 * 3 * 3 * 16
    if len(payload) != expected:
        raise ValueError(f'{path}: payload has {len(payload)} bytes, expected {expected}')
    raw = np.frombuffer(payload, dtype='<c16')
    return raw.reshape(nt, nz, ny, nx, 4, 3, 3).transpose(4, 0, 1, 2, 3, 5, 6)


def load_data(output, split):
    p = protocol()
    with np.load(Path(output) / f'{split}.npz', allow_pickle=False) as f:
        if not np.array_equal(f['ids'], indices(split)):
            raise ValueError(f'{split}: missing or reordered configurations')
        if str(f['protocol_hash']) != fingerprint(p):
            raise ValueError('Protocol changed since measurement')
        loops = f['loops'].copy()
    expected = (len(indices(split)), len(p['kernels']), len(p['r_values']), len(p['t_values']))
    if loops.shape != expected:
        raise ValueError(f'Unexpected loop shape {loops.shape}, expected {expected}')
    if loops.dtype.kind not in 'fiu' or not np.all(np.isfinite(loops)):
        raise ValueError('Loops must be finite real numbers')
    return loops
