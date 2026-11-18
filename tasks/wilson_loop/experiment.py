"""Development selection and held-out scoring for the static-potential pilot."""
import json
from pathlib import Path

import numpy as np

from .common import digest, fingerprint, load_data, protocol, write_json
from .statistics import blocks, bootstrap_indices, potential, risk


def develop(output):
    p = protocol()
    output = Path(output)
    if (output / 'submission.json').exists() or (output / 'validation.npz').exists():
        raise ValueError('Development is closed for this run; use a new output directory')
    data = blocks(load_data(output, 'development'), p['block_length'])
    index = bootstrap_indices(len(data), p['bootstrap_samples'], p['seed'])
    windows = p['reference_windows']
    v_ref = potential(data[:, p['reference_kernel']].mean(0), windows[1], p['t_values'])
    results = {spec['name']: risk(data[:, k], index, windows, p['t_values'], v_ref)
               for k, spec in enumerate(p['kernels'])}
    identity = results['identity']
    failures = []
    if np.any(np.array(identity['v']) <= 0):
        failures.append('non-positive reference potential')
    if np.any(np.array(identity['spread']) / np.array(identity['v']) > p['reference_max_relative_se']):
        failures.append('identity plateau spread across T windows exceeds the fixed threshold')
    best_risk, best_name = min((r['risk'], n) for n, r in results.items() if n != 'identity')
    frozen = {'protocol_hash': fingerprint(p),
              'development_sha256': digest(output / 'development.npz'),
              'kernel_sha256': digest(Path(__file__).with_name('kernels.py')),
              'windows': windows, 'nominal_window': windows[1],
              'reference_passed': not failures, 'failure_reasons': failures,
              'identity': identity, 'kernels': p['kernels'], 'v_ref': v_ref.tolist(), 'results': results,
              'best_nonidentity': {'name': best_name, 'risk': best_risk}}
    write_json(output / 'submission.json', frozen)
    print('DEVELOP', json.dumps({'reference_passed': frozen['reference_passed'],
                                 'failures': failures,
                                 'identity_v': [round(x, 5) for x in identity['v']],
                                 'identity_spread': [round(x, 6) for x in identity['spread']],
                                 'risks': {n: round(r['risk'], 8) for n, r in results.items()}}))


def evaluate(output):
    p = protocol()
    output = Path(output)
    frozen = json.loads((output / 'submission.json').read_text())
    if frozen['protocol_hash'] != fingerprint(p):
        raise ValueError('Protocol changed since development')
    if frozen.get('kernel_sha256') != digest(Path(__file__).with_name('kernels.py')):
        raise ValueError('Kernel implementation changed since development')
    if frozen['development_sha256'] != digest(output / 'development.npz'):
        raise ValueError('Development data changed since development')
    if frozen['kernels'] != p['kernels']:
        raise ValueError('Kernel parameters changed since development')
    data = blocks(load_data(output, 'validation'), p['block_length'])
    index = bootstrap_indices(len(data), p['bootstrap_samples'], p['seed'] + 1)
    windows = frozen['windows']
    v_ref = np.array(frozen['identity']['v'])
    results = {spec['name']: risk(data[:, k], index, windows, p['t_values'], v_ref)
               for k, spec in enumerate(p['kernels'])}
    base = results['identity']['risk']
    eps = p['score_epsilon']
    for value in results.values():
        value['loss_ratio_vs_identity'] = (base + eps) / (value['risk'] + eps)
        value['score'] = 100 * value['loss_ratio_vs_identity'] if frozen['reference_passed'] else None
    report = {'protocol_version': p['version'], 'windows': windows,
              'identity': frozen['identity'],
              'reference_passed': frozen['reference_passed'],
              'failure_reasons': frozen['failure_reasons'],
              'n_validation': len(data) * p['block_length'], 'n_blocks': len(data),
              'r_values': p['r_values'], 'results': results}
    write_json(output / 'validation_results.json', report)
    print('VALIDATION', json.dumps({k: report[k] for k in ('reference_passed', 'failure_reasons')}),
          {n: {'risk': round(r['risk'], 6), 'score': r['score']} for n, r in results.items()})
