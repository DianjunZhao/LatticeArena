"""Read-only sensitivity of frozen pion kernels to the reference fit window."""
import json
from itertools import combinations
from pathlib import Path

import numpy as np

from core.io import digest, fingerprint, write_json
from .common import load_data
from .experiment import late_metric, nested_intervals
from .statistics import ReferenceFit, blocks, bootstrap_indices, fold, risk

CANDIDATES = ('local', 'tuned_gaussian', 'agent_signed_mixture')


def replay_window(dev, val, frozen, protocol, window_index):
    p = dict(protocol, reference_nominal_window=window_index)
    window = p['reference_windows'][window_index]
    di = bootstrap_indices(len(dev), p['bootstrap_samples'], p['seed'])
    vi = bootstrap_indices(len(val), p['bootstrap_samples'], p['seed'] + 1)
    ref, masses = ReferenceFit(dev, p, window).bootstrap(di)
    rows, metrics = {}, {}
    for name in CANDIDATES:
        w = frozen['submissions'][name]
        try:
            metrics[name] = late_metric(dev, w, p)
            res = risk(val, w, ref['mass'], masses, vi, p, late_inverse=metrics[name])
            rows[name] = {key: res[key] for key in ('risk', 'variance', 'departure_squared')}
        except (ValueError, np.linalg.LinAlgError) as exc:
            rows[name] = {'invalid_reason': str(exc)}
    result = {'reference': ref, 'candidates': rows, 'pairs': {}, 'ranking': None}
    if not all('risk' in row for row in rows.values()):
        return result
    draws, names = nested_intervals(dev, val, dict(frozen, late_inverse_covariances=metrics), p)
    eps = p['score_epsilon']
    for name in CANDIDATES:
        rows[name]['risk_95_interval'] = np.quantile(draws[:, names.index(name)], [.025, .975]).tolist()
    for left, right in combinations(CANDIDATES, 2):
        ratios = (draws[:, names.index(left)] + eps) / (draws[:, names.index(right)] + eps)
        result['pairs'][f'{left}/{right}'] = {
            'risk_ratio': rows[left]['risk'] / rows[right]['risk'],
            'risk_ratio_95_interval': np.quantile(ratios, [.025, .975]).tolist()}
    result['ranking'] = sorted(CANDIDATES, key=lambda name: rows[name]['risk'])
    return result


def verify_nominal(row, archive):
    """Check replay against the published point estimates and conditional intervals."""
    reference = row['reference']
    if reference['window'] != archive['reference']['window']:
        raise ValueError('Nominal reference window differs from archive')
    for key in ('mass', 'se', 'chi2'):
        np.testing.assert_allclose(reference[key], archive['reference'][key], rtol=1e-7, atol=1e-12)
    for name, report in row['candidates'].items():
        original = archive['results'][name]
        if 'invalid_reason' in report or 'invalid_reason' in original:
            if report.get('invalid_reason') != original.get('invalid_reason'):
                raise ValueError(f'Nominal candidate validity changed: {name}')
            continue
        for key in ('risk', 'variance', 'departure_squared', 'risk_95_interval'):
            if key == 'risk_95_interval' and key not in original and row['ranking'] is None:
                continue
            np.testing.assert_allclose(report[key], original[key], rtol=1e-7, atol=1e-12,
                                       err_msg=f'nominal replay differs: {name}/{key}')
    if row['ranking'] is None:
        return
    comparison = row['pairs']['tuned_gaussian/agent_signed_mixture']
    for key in comparison:
        np.testing.assert_allclose(comparison[key], archive['agent_vs_tuned_gaussian'][key],
                                   rtol=1e-7, atol=1e-12, err_msg=f'nominal replay differs: {key}')


def diagnose(run, destination):
    run, destination = Path(run), Path(destination)
    if destination.resolve().is_relative_to(run.resolve()):
        raise ValueError('Choose a destination outside the frozen run')
    if destination.exists():
        raise FileExistsError(destination)
    frozen = json.loads((run / 'submission.json').read_text())
    archive = json.loads((run / 'validation_results.json').read_text())
    p = json.loads((run / 'development_provenance.json').read_text())['protocol']
    bindings = {name: digest(run / name) for name in
                ('development.npz', 'validation.npz', 'submission.json', 'validation_results.json')}
    if (frozen['protocol_hash'] != fingerprint(p) or archive['protocol'] != p
            or bindings['development.npz'] != frozen['development_sha256']
            or bindings['validation.npz'] != archive['validation_sha256']
            or bindings['submission.json'] != archive['submission_sha256']):
        raise ValueError('Frozen data, submission or report identity mismatch')
    for filename, key in [('statistics.py', 'statistics_sha256'), ('kernels.py', 'kernel_sha256')]:
        if digest(Path(__file__).with_name(filename)) != frozen[key]:
            raise ValueError(f'Frozen implementation mismatch: {filename}')
    if set(frozen['submissions']) != set(CANDIDATES) or frozen.get('reference', {}).get('kind', 'single') != 'single':
        raise ValueError('Expected the three frozen single-state v1 candidates')
    dev, val = (blocks(fold(load_data(run, split, p)), p['block_length'])
                for split in ('development', 'validation'))
    nominal = p['reference_nominal_window']
    windows = [None] * len(p['reference_windows'])
    windows[nominal] = replay_window(dev, val, frozen, p, nominal)
    verify_nominal(windows[nominal], archive)
    for i, window in enumerate(p['reference_windows']):
        if i != nominal:
            try:
                windows[i] = replay_window(dev, val, frozen, p, i)
            except (ValueError, np.linalg.LinAlgError) as exc:
                windows[i] = {'window': window, 'ranking': None, 'invalid_reason': str(exc)}
    result = {'inputs': bindings, 'protocol_hash': fingerprint(p), 'nominal_index': nominal,
              'nominal_reproduced': True, 'reference_passed': archive['reference_passed'],
              'reference_failure_reasons': archive['reference_failure_reasons'],
              'blocks': {'development': len(dev), 'validation': len(val)}, 'windows': windows}
    destination.mkdir(parents=True, exist_ok=False)
    write_json(destination / 'ranking.json', result)
    lines = ['# Frozen pion ranking by reference window', '',
             f"Nominal replay verified. Development / validation blocks: {len(dev)} / {len(val)}.",
             f"Archived reference gate: {archive['reference_passed']}. Intervals are conditional paired bootstrap intervals.",
             '', '| Window | Mass | Candidate | Variance | Squared departure | Risk |',
             '| --- | ---: | --- | ---: | ---: | ---: |']
    for window, row in zip(p['reference_windows'], windows):
        for name, values in row.get('candidates', {}).items():
            if 'risk' in values:
                lines.append(f"| {window} | {row['reference']['mass']:.5f} | {name} | "
                             f"{values['variance']:.5g} | {values['departure_squared']:.5g} | {values['risk']:.5g} |")
    for window, row in zip(p['reference_windows'], windows):
        lines.extend(['', f'## Window {window}', ''])
        if row['ranking'] is None:
            lines.append(f"Inconclusive: {row.get('invalid_reason', row.get('candidates'))}")
            continue
        lines.append('Increasing risk: ' + ', '.join(row['ranking']) + '.')
        for pair, values in row['pairs'].items():
            lo, hi = values['risk_ratio_95_interval']
            lines.append(f"- {pair}: {values['risk_ratio']:.4g} [{lo:.4g}, {hi:.4g}]")
    (destination / 'ranking.md').write_text('\n'.join(lines) + '\n')
    return result
