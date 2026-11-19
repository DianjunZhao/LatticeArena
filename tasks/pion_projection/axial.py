"""Paired local PP and A4P effective masses from development point propagators."""
import json
from pathlib import Path

import numpy as np

from .common import digest, fingerprint, indices, load_data, protocol, write_json
from .statistics import blocks, bootstrap_indices, effective_mass, fold


def contract(prop):
    """Cache axes are parity,t,z,y,x/2,sink spin,source spin,sink color,source color."""
    pp, ap = [], []
    for t in range(prop.shape[1]):
        s = prop[:, t]
        pp.append(np.vdot(s, s).real)
        # With positive PP normalization, gamma5 (gamma4 gamma5) = -gamma4.
        # DeGrand-Rossi gamma4 exchanges the upper and lower two sink spins.
        ap.append(-2 * np.vdot(s[..., :2, :, :, :], s[..., 2:, :, :, :]).real)
    return np.array([pp, ap])


def mass_differences(rows, p):
    """Use the same blocks and bootstrap draws at all times and in both channels."""
    nt = p['geometry'][3]
    if rows.shape[1:] != (2, nt) or not np.isfinite(rows).all():
        raise ValueError('Expected two finite correlators per configuration')
    half = nt // 2
    odd = np.zeros((len(rows), half + 1))
    odd[:, 1:half] = (rows[:, 1, 1:half] - rows[:, 1, -1:half:-1]) / 2
    data = blocks(np.stack([fold(rows[:, 0]), odd], axis=1), p['block_length'])
    index = bootstrap_indices(len(data), p['bootstrap_samples'], p['seed'])
    window = p['reference_windows'][p['reference_nominal_window']]
    times = np.array([t for t in window if 0 < t < half])
    # The odd correlator vanishes at the midpoint. Only interior masses exist.
    samples = np.concatenate([data.mean(axis=0)[None], data[index].mean(axis=1)])
    with np.errstate(divide='ignore', invalid='ignore'):
        masses = np.array([[effective_mass(curve)[times-1] for curve in sample] for sample in samples])

    def summarize(values):
        valid = np.isfinite(values[1:])
        return {'estimate': float(values[0]) if np.isfinite(values[0]) else None,
                'valid_draws': int(valid.sum()),
                'interval_95': np.quantile(values[1:], [.025, .975]).tolist() if valid.all() else None}

    table = []
    for j, t in enumerate(times):
        pp, ap = masses[:, :, j].T
        row = {'t': int(t), 'PP': summarize(pp), 'A4P': summarize(ap), 'A4P_minus_PP': summarize(ap - pp)}
        if j:
            for k, name in enumerate(('PP', 'A4P')):
                row[name + '_shift_from_previous'] = summarize(masses[:, k, j] - masses[:, k, j-1])
        table.append(row)
    return table


def check(output, destination):
    output, destination = Path(output), Path(destination)
    p = protocol()
    manifest_path = output / 'development_provenance.json'
    manifest = json.loads(manifest_path.read_text())
    frozen = json.loads((output / 'submission.json').read_text())
    ids = indices('development', p).tolist()
    if (manifest['protocol'] != p or [row['id'] for row in manifest['records']] != ids
            or frozen['protocol_hash'] != fingerprint(p) or frozen['development_sha256'] != digest(output/'development.npz')):
        raise ValueError('Development inputs do not match the frozen protocol')
    local = load_data(output, 'development', p)[:, p['powers'].index(0)]
    cache = Path('.cache/pion_projection/propagators')
    x, y, z, nt = p['geometry']
    rows = []
    for record, expected in zip(manifest['records'], local):
        key = record['cache_key']
        array = cache / (key + '.npy')
        meta = json.loads(array.with_suffix('.json').read_text())
        if (fingerprint(meta['keydata']) != key or meta['keydata']['gauge'] != record['gauge_sha256']
                or not 0 <= record['residual_max'] <= p['tolerance'] or digest(array) != meta['array_sha256']):
            raise ValueError(f"Invalid cached propagator on configuration {record['id']}")
        prop = np.load(array, mmap_mode='r', allow_pickle=False)
        if prop.shape != (2, nt, z, y, x//2, 4, 4, 3, 3):
            raise ValueError('Unexpected cached propagator shape')
        pair = contract(prop)
        np.testing.assert_allclose(pair[0], expected, rtol=1e-10, atol=0)
        rows.append(pair)
    rows = np.asarray(rows)
    table = mass_differences(rows, p)
    destination.mkdir(parents=True, exist_ok=False)
    correlators = destination / 'correlators.npz'
    np.savez_compressed(correlators, ids=ids, PP=rows[:, 0], A4P=rows[:, 1])
    report = {'split': 'development', 'configurations': len(ids), 'blocks': len(ids)//p['block_length'],
              'bootstrap_samples': p['bootstrap_samples'], 'protocol_hash': fingerprint(p),
              'development_manifest_sha256': digest(manifest_path), 'submission_sha256': digest(output/'submission.json'),
              'implementation_sha256': digest(__file__), 'correlators_sha256': digest(correlators),
              'reference_passed': frozen['calibration']['reference_passed'], 'effective_masses': table}
    write_json(destination / 'axial_check.json', report)
    print(destination / 'axial_check.json')
    return report
