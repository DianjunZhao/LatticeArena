"""Development selection and held-out scoring for the static-potential pilot."""
import json
from pathlib import Path

import numpy as np

from core.ledger import Ledger
from core.receipts import make as make_receipt
from core.state import RunState

from core.io import digest_text

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
    nominal = p['reference_nominal_window']
    if not 0 <= nominal < len(windows):
        raise ValueError('reference_nominal_window is out of range')
    v_ref = potential(data[:, p['reference_kernel']].mean(0), windows[nominal], p['t_values'])
    results = {spec['name']: risk(data[:, k], index, windows, p['t_values'], v_ref, nominal=nominal)
               for k, spec in enumerate(p['kernels'])}
    identity = results['identity']
    state = RunState()
    code = {'kernels.py': digest(Path(__file__).with_name('kernels.py')),
            'statistics.py': digest(Path(__file__).with_name('statistics.py'))}
    inputs = {'development.npz': digest(output / 'development.npz')}
    receipts = {
        'operator': make_receipt('operator', code, inputs,
                                 {'kernels': [spec['name'] for spec in p['kernels']],
                                  'finite_identity_v': bool(np.all(np.isfinite(identity['v'])))}),
        'numerical': make_receipt('numerical', code, inputs,
                                  {'bootstrap_samples': p['bootstrap_samples'],
                                   'bootstrap_se_finite': bool(np.all(np.isfinite(identity['se'])))}),
    }
    state.set('operator', 'draft', 'kernels.py')
    state.set('operator', 'validated', 'kernel receipt', receipt=receipts['operator'])
    state.set('numerical', 'draft', 'per-matrix Newton-Schulz')
    state.set('numerical', 'validated', 'numerical receipt', receipt=receipts['numerical'])
    failures = []
    if np.any(np.array(identity['v']) <= 0):
        failures.append('non-positive reference potential')
    if np.any(np.array(identity['spread']) / np.array(identity['v']) > p['reference_max_relative_se']):
        failures.append('identity plateau spread across T windows exceeds the fixed threshold')
    receipts['reference'] = make_receipt('reference', code, inputs,
                                         {'passed': not failures, 'failures': failures,
                                          'v': identity['v'], 'spread': identity['spread']})
    receipts['statistical'] = make_receipt('statistical', code, inputs,
                                           {'seed': p['seed'], 'blocks': len(data),
                                            'bootstrap_samples': p['bootstrap_samples'],
                                            'risks': {n: r['risk'] for n, r in results.items()}})
    state.set('reference', 'draft', 'identity V')
    if failures:
        state.set('reference', 'failed', '; '.join(failures))
    else:
        state.set('reference', 'validated', 'identity receipt', receipt=receipts['reference'])
    state.set('statistical', 'draft', 'block bootstrap')
    state.set('statistical', 'validated', 'statistical receipt', receipt=receipts['statistical'])
    state.set('comparison', 'draft', 'risk ratios')
    if failures:
        state.set('comparison', 'failed', 'reference gate failed')
    best_risk, best_name = min((r['risk'], n) for n, r in results.items() if n != 'identity')
    frozen = {'protocol_hash': fingerprint(p),
              'development_sha256': digest(output / 'development.npz'),
              'kernel_sha256': digest(Path(__file__).with_name('kernels.py')),
              'windows': windows, 'nominal_window': windows[nominal],
              'nominal_window_index': nominal,
              'reference_passed': not failures, 'failure_reasons': failures,
              'identity': identity, 'kernels': p['kernels'], 'v_ref': v_ref.tolist(), 'results': results,
              'run_state': state.summary(), 'receipts': receipts,
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
    nominal = p['reference_nominal_window']
    results = {}
    for k, spec in enumerate(p['kernels']):
        try:
            results[spec['name']] = risk(data[:, k], index, windows, p['t_values'], v_ref, nominal=nominal)
        except ValueError as exc:
            results[spec['name']] = {'invalid_reason': str(exc), 'risk': None, 'score': None}
    base = results['identity'].get('risk')
    if base is None:
        raise ValueError('identity risk is invalid; refusing to score')
    eps = p['score_epsilon']
    for value in results.values():
        if value.get('risk') is None:
            value['loss_ratio_vs_identity'] = None
            value['score'] = None
            continue
        value['loss_ratio_vs_identity'] = (base + eps) / (value['risk'] + eps)
        value['score'] = 100 * value['loss_ratio_vs_identity'] if frozen['reference_passed'] else None
    state = RunState()
    frozen_state = frozen.get('run_state', {})
    frozen_receipts = frozen.get('receipts') or {}
    receipt_status = {}
    for name in ('operator', 'reference', 'numerical', 'statistical'):
        status = frozen_state.get('status', {}).get(name, 'draft')
        receipt = frozen_receipts.get(name)
        if status == 'validated' and receipt is not None:
            from core.receipts import verify as verify_receipt
            try:
                verify_receipt(receipt)
            except ValueError as exc:
                receipt_status[name] = f'rejected: {exc}'
                state.set(name, 'draft')
            else:
                receipt_status[name] = 'verified'
                state.set(name, 'draft')
                state.set(name, 'validated', receipt=receipt)
        elif status == 'failed':
            state.set(name, 'failed')
        else:
            receipt_status[name] = 'missing receipt'
            state.set(name, 'draft')
    state.set('comparison', 'draft', 'evaluate')
    state.observe_validation(f'evaluate:{p["version"]}')
    if not frozen['reference_passed']:
        state.set('comparison', 'failed', 'reference gate failed')
    report = {'protocol_version': p['version'], 'windows': windows,
              'run_state': state.summary(), 'physical_score': state.score_or_null(),
              'identity': frozen['identity'],
              'reference_passed': frozen['reference_passed'],
              'failure_reasons': frozen['failure_reasons'],
              'n_validation': len(data) * p['block_length'], 'n_blocks': len(data),
              'r_values': p['r_values'], 'results': results,
              'score_status': ('conditional_diagnostic' if frozen['reference_passed']
                               else 'unscored_reference_failed'),
              'receipt_status': receipt_status}
    report['conditional_scores'] = {n: value.get('score') for n, value in results.items()}
    write_json(output / 'validation_results.json', report)
    print('VALIDATION', json.dumps({k: report[k] for k in ('reference_passed', 'failure_reasons')}),
          {n: {'risk': (round(r['risk'], 6) if r.get('risk') is not None else None),
               'score': r['score']} for n, r in results.items()})
