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


def nersc_word_checksum(payload, floating_point):
    """32-bit word sum as used by the standard NERSC CHECKSUM header.

    Grid computes this on host-order values: for IEEE64LITTLE the file words are
    already host order; for IEEE64BIG the doubles are byte-swapped first. The
    sum is modulo 2**32.
    """
    value = (floating_point or 'IEEE64LITTLE').strip().upper()
    if value in ('1', 'TRUE', 'YES', 'IEEE64LITTLE'):
        words = np.frombuffer(payload, dtype='<u4')
    elif value == 'IEEE64BIG':
        words = np.frombuffer(payload, dtype='>f8').astype('<f8').view('<u4')
    elif value in ('IEEE32',):
        words = np.frombuffer(payload, dtype='<u4')
    elif value == 'IEEE32BIG':
        words = np.frombuffer(payload, dtype='>f4').astype('<f4').view('<u4')
    else:
        raise ValueError(f'unsupported FLOATING_POINT {floating_point!r}')
    return int(np.asarray(words, dtype=np.uint64).sum() & np.uint64(0xFFFFFFFF))


def _nersc_payload(path, expected_geometry=None):
    """Parse a NERSC gauge file; return (raw bytes, checksum status, dims).

    The standard header CHECKSUM is verified when present; a trailing private
    16-byte MD5 is verified separately. A failed standard header cannot be
    rescued by a valid MD5, and an absent check is reported by name.
    """
    import hashlib
    file_hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        first_line = f.readline()
        file_hasher.update(first_line)
        header = {}
        while True:
            line = f.readline()
            if not line:
                raise ValueError(f'{path}: missing END_HEADER')
            file_hasher.update(line)
            if line.strip() == b'END_HEADER':
                break
            key, value = line.decode().split('=', 1)
            header[key.strip()] = value.strip()
        payload = f.read()
        file_hasher.update(payload)
    try:
        nx, ny, nz, nt = (int(header[f'DIMENSION_{i}']) for i in (1, 2, 3, 4))
    except (KeyError, ValueError) as exc:
        raise ValueError(f'{path}: incomplete NERSC dimension header') from exc
    datatype = header.get('DATATYPE')
    if datatype is not None and not datatype.startswith('4D_SU3_GAUGE_3x3'):
        raise ValueError(f'{path}: unsupported DATATYPE {datatype!r}')
    floating = header.get('FLOATING_POINT')
    if floating is not None:
        value = floating.strip().upper()
        if value in ('IEEE64', 'IEEE64BIG', 'IEEE64LITTLE', 'IEEE32', 'IEEE32BIG', '1', 'TRUE', 'YES'):
            pass
        else:
            raise ValueError(f'{path}: unsupported FLOATING_POINT {floating!r}')
    if expected_geometry is not None and [nx, ny, nz, nt] != list(expected_geometry):
        raise ValueError(f'{path}: header geometry {[nx, ny, nz, nt]} != run geometry {list(expected_geometry)}')
    expected = nt * nz * ny * nx * 4 * 3 * 3 * 16
    status = {'standard': 'absent', 'md5': 'absent', 'verified': False,
              'raw_sha256': file_hasher.hexdigest()}
    if len(payload) == expected:
        raw = payload
    elif len(payload) == expected + 16:
        raw, trailer = payload[:expected], payload[expected:]
        if hashlib.md5(raw).digest() == trailer:
            status['md5'] = 'verified'
        else:
            raise ValueError(f'{path}: NERSC trailing MD5 mismatch')
    else:
        raise ValueError(f'{path}: payload has {len(payload)} bytes, expected {expected}'
                         f' (or {expected + 16} with a checksum trailer)')
    if 'CHECKSUM' in header:
        try:
            declared = int(header['CHECKSUM'], 16)
        except ValueError as exc:
            raise ValueError(f'{path}: unparsable CHECKSUM {header["CHECKSUM"]!r}') from exc
        computed = nersc_word_checksum(raw, floating)
        if computed != declared:
            raise ValueError(f'{path}: NERSC header checksum mismatch '
                             f'(computed {computed:08x}, header {declared:08x})')
        status['standard'] = 'verified'
    status['verified'] = status['standard'] == 'verified'
    return raw, status, (nx, ny, nz, nt)


def read_nersc(path, expected_geometry=None):
    """Read a NERSC 4D_SU3_GAUGE_3x3 file into (mu, t, z, y, x, 3, 3).

    Validates the header keys we rely on, the exact payload length and the
    optional MD5 trailer; unknown optional keys are tolerated, but a wrong data
    type or truncated payload is rejected instead of being reshaped silently.
    """
    raw, _, (nx, ny, nz, nt) = _nersc_payload(path, expected_geometry)
    return np.frombuffer(raw, dtype='<c16').reshape(nt, nz, ny, nx, 4, 3, 3).transpose(4, 0, 1, 2, 3, 5, 6)


def read_nersc_with_status(path, expected_geometry=None):
    """Read the array and return the explicit checksum status in one parse."""
    raw, status, (nx, ny, nz, nt) = _nersc_payload(path, expected_geometry)
    array = np.frombuffer(raw, dtype='<c16').reshape(nt, nz, ny, nx, 4, 3, 3).transpose(4, 0, 1, 2, 3, 5, 6)
    return array, status


def nersc_checksum_status(path, expected_geometry=None):
    """Checksum status dict; a mismatch raises."""
    _, status, _ = _nersc_payload(path, expected_geometry)
    return {key: status[key] for key in ('standard', 'md5', 'verified')}


def indices_for(p, split):
    first, last = p[split]
    return np.arange(first, last + 1)


def load_data(output, split, p=None):
    p = p or protocol()
    with np.load(Path(output) / f'{split}.npz', allow_pickle=False) as f:
        if not np.array_equal(f['ids'], indices_for(p, split)):
            raise ValueError(f'{split}: missing or reordered configurations')
        if str(f['protocol_hash']) != fingerprint(p):
            raise ValueError('Protocol changed since measurement')
        loops = f['loops'].copy()
    expected = (len(indices_for(p, split)), len(p['kernels']), len(p['r_values']), len(p['t_values']))
    if loops.shape != expected:
        raise ValueError(f'Unexpected loop shape {loops.shape}, expected {expected}')
    if loops.dtype.kind not in 'fiu' or not np.all(np.isfinite(loops)):
        raise ValueError('Loops must be finite real numbers')
    return loops
