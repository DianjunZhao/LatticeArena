import json
from pathlib import Path

import numpy as np

from core.io import digest, fingerprint, write_json  # noqa: F401  (re-export)

HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = Path('results/wilson_loop/s16t16_v1')


def protocol():
    return json.loads((HERE / 'protocol.json').read_text())


def indices(split):
    first, last = protocol()[split]
    return np.arange(first, last + 1)


def read_nersc(path):
    """Read a NERSC 4D_SU3_GAUGE_3x3 file into (mu, t, z, y, x, 3, 3)."""
    with open(path, 'rb') as f:
        f.readline()
        header = {}
        while True:
            line = f.readline()
            if line.strip() == b'END_HEADER':
                break
            key, value = line.decode().split('=')
            header[key.strip()] = value.strip()
        raw = np.frombuffer(f.read(), dtype='<c16')
    nx, ny, nz, nt = (int(header[f'DIMENSION_{i}']) for i in (1, 2, 3, 4))
    return raw.reshape(nt, nz, ny, nx, 4, 3, 3).transpose(4, 0, 1, 2, 3, 5, 6)


def load_data(output, split):
    p = protocol()
    with np.load(Path(output) / f'{split}.npz', allow_pickle=False) as f:
        if not np.array_equal(f['ids'], indices(split)):
            raise ValueError(f'{split}: missing or reordered configurations')
        if str(f['protocol_hash']) != fingerprint(p):
            raise ValueError('Protocol changed since measurement')
        loops = f['loops'].copy()
    if loops.shape[1] != len(p['kernels']):
        raise ValueError('Unexpected loop shape')
    return loops
