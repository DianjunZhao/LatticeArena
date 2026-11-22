"""Analyze a frozen candidate on a separately generated physical anchor set."""
import argparse
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from .common import digest, fingerprint, load_data, protocol
from .experiment import nested_intervals, reflection_odd
from .measurement_plan import generation_id, load_plan
from .reference import make_reference, verify_reference
from .statistics import blocks, bootstrap_indices, fold, risk


def _json_safe(value):
    """Convert NumPy values and non-finite diagnostics to strict JSON values."""
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    return value


def _fmt(value, spec='.6g'):
    return 'n/a' if value is None or not np.isfinite(value) else format(float(value), spec)


def reference_review(raw, p, kind, seed):
    data = blocks(fold(raw), p['block_length'])
    indices = bootstrap_indices(len(data), p['bootstrap_samples'], seed)
    windows, mass_samples = [], []
    failures = []
    for window in p['reference_windows']:
        try:
            model = make_reference(data, p, window, kind)
            result, samples = model.bootstrap(indices)
        except (ValueError, np.linalg.LinAlgError, FloatingPointError) as error:
            failures.append(f'Reference fit failed for window {window}: {error!r}')
            windows.append({'window': window, 'status': 'failed', 'reason': repr(error)})
            mass_samples.append(None)
            continue
        result['status'] = 'fit'
        windows.append(result)
        mass_samples.append(np.asarray(samples, dtype=float))

    nominal = p['reference_nominal_window']
    reference = windows[nominal]
    samples = mass_samples[nominal]
    if samples is None:
        failures.append('Anchor nominal reference fit is unavailable')
    else:
        mass = float(reference['mass'])
        se = float(np.std(samples, ddof=1))
        if se / abs(mass) > p['reference_max_relative_error']:
            failures.append('Anchor reference mass relative uncertainty exceeds the frozen limit')
        if reference.get('p_approx', 0.0) < p['reference_min_fit_p']:
            failures.append('Anchor nominal reference fit fails the frozen approximate goodness-of-fit gate')
        for index, result in enumerate(windows):
            if index == nominal or mass_samples[index] is None:
                continue
            paired_se = float(np.std(mass_samples[index] - samples, ddof=1))
            shift = abs(float(result['mass']) - mass) / paired_se if paired_se > 0 else float('inf')
            result['paired_shift_z'] = shift
            if shift > p['reference_max_window_z']:
                failures.append(f'Anchor reference window {result["window"]} shifts by {shift:.2f} sigma')
        if np.any(samples <= p['mass_bounds'][0] + 1e-4) or np.any(samples >= p['mass_bounds'][1] - 1e-4):
            failures.append('Anchor reference bootstrap reaches mass bounds')
    odd = reflection_odd(raw)
    odd_blocks = blocks(odd, p['block_length'])
    odd_mean = odd_blocks.mean(axis=0)
    odd_se = odd_blocks.std(axis=0, ddof=1) / np.sqrt(len(odd_blocks))
    z = np.divide(np.abs(odd_mean), odd_se, out=np.zeros_like(odd_mean), where=odd_se > 0)
    reflection_z = float(np.max(z))
    if reflection_z > p['reflection_max_z']:
        failures.append('Anchor forward/backward reflection check exceeds the frozen z threshold')
    return data, {
        'passed': not failures,
        'failures': failures,
        'windows': windows,
        'nominal': reference,
        'mass_samples': samples,
        'reflection_max_z': reflection_z,
        'n_blocks': len(data),
    }


def run(output, plan_path):
    output = Path(output)
    plan = load_plan(plan_path)
    p = protocol()
    if 'anchor' not in plan['splits']:
        raise ValueError('frozen plan has no anchor split')
    for name in ('anchor_results.json', 'anchor_reference_windows.png', 'anchor_candidate_risks.png',
                 'anchor_review.md', 'anchor_nested_bootstrap.npz'):
        if (output / name).exists():
            raise FileExistsError(f'refusing to overwrite {output / name}')
    submission_path = output / 'submission.json'
    submission = json.loads(submission_path.read_text())
    development_path = output / 'development.npz'
    anchor_path = output / 'anchor.npz'
    if submission.get('protocol_hash') != fingerprint(p):
        raise ValueError('frozen submission protocol hash mismatch')
    if submission.get('development_sha256') != digest(development_path):
        raise ValueError('frozen development data hash mismatch')
    if not submission.get('calibration', {}).get('reference_passed', False):
        raise ValueError('development reference gate failed; anchor is diagnostic only and cannot open validation')
    kind = verify_reference(submission['reference'])
    development_raw = load_data(output, 'development')
    anchor_raw = load_data(output, 'anchor')
    development = blocks(fold(development_raw), p['block_length'])
    anchor, anchor_ref = reference_review(anchor_raw, p, kind, p['seed'] + 101)
    dev_reference = submission['calibration']['reference']
    dev_mass = float(dev_reference['mass'])
    dev_samples = np.asarray(np.load(output / 'reference_bootstrap.npz')['masses'], dtype=float)
    dev_se = float(np.std(dev_samples, ddof=1))
    anchor_se = (float(np.std(anchor_ref['mass_samples'], ddof=1))
                 if anchor_ref['mass_samples'] is not None else None)
    delta_se = math.sqrt(dev_se * dev_se + anchor_se * anchor_se) if anchor_se is not None else None

    risk_rows = []
    risk_draws = None
    names = list(submission['submissions'])
    reference_samples = dev_samples
    anchor_blocks = anchor
    anchor_indices = bootstrap_indices(len(anchor_blocks), p['bootstrap_samples'], p['seed'] + 103)
    if anchor_ref['mass_samples'] is None:
        draw_names = []
        for name in names:
            risk_rows.append({'candidate': name, 'risk': None,
                              'status': 'not_evaluated_anchor_reference_failed'})
    else:
        for name in names:
            try:
                value = risk(anchor_blocks, submission['submissions'][name], dev_mass,
                             reference_samples, anchor_indices, p,
                             late_inverse=np.asarray(submission['late_inverse_covariances'][name]))
                risk_rows.append({'candidate': name, 'risk': float(value['risk']), 'status': 'evaluated'})
            except (ValueError, np.linalg.LinAlgError, FloatingPointError) as error:
                risk_rows.append({'candidate': name, 'risk': None, 'status': 'abstain',
                                  'reason': repr(error)})
        try:
            risk_draws, draw_names = nested_intervals(development, anchor_blocks, submission, p,
                                                      kind, seed_offset=100)
            np.savez_compressed(output / 'anchor_nested_bootstrap.npz', risks=risk_draws,
                                names=np.asarray(draw_names))
        except (ValueError, np.linalg.LinAlgError, FloatingPointError) as error:
            draw_names = []
            risk_rows.append({'candidate': '*', 'risk': None, 'status': 'bootstrap_abstain',
                              'reason': repr(error)})

    anchor_mass = anchor_ref['nominal'].get('mass')
    delta_z = (abs(float(anchor_mass) - dev_mass) / delta_se
               if anchor_mass is not None and delta_se is not None
               and np.isfinite(delta_se) and delta_se > 0 else None)
    if delta_z is None:
        anchor_ref['failures'].append('Development-anchor mass comparison is unavailable')
    elif delta_z > p['reference_max_window_z']:
        anchor_ref['failures'].append(
            f'Independent anchor mass differs from development by {delta_z:.2f} combined standard errors')
    anchor_passed = bool(anchor_ref['passed'] and delta_z is not None
                         and delta_z <= p['reference_max_window_z'])

    result = {
        'schema': 'pion-independent-anchor-review-v1',
        'status': 'PASS_DIAGNOSTIC_GATE' if anchor_passed else 'INCONCLUSIVE_OR_FAILED_DIAGNOSTIC_GATE',
        'physical_score': None,
        'anchor_reference_passed': anchor_passed,
        'anchor_sha256': digest(anchor_path),
        'development_sha256': digest(development_path),
        'submission_sha256': digest(submission_path),
        'measurement_generation': generation_id(plan_path, 'anchor', p),
        'plan_sha256': digest(plan_path),
        'protocol_sha256': fingerprint(p),
        'reference_kind': kind,
        'development_anchor_mass': {
            'development_mass': dev_mass,
            'development_se': dev_se,
            'anchor_mass': float(anchor_mass) if anchor_mass is not None else None,
            'anchor_se': anchor_se,
            'difference_combined_se': float(delta_z) if delta_z is not None else None,
            'threshold_sigma': p['reference_max_window_z'],
        },
        'anchor_reference': {key: value for key, value in anchor_ref.items() if key != 'mass_samples'},
        'candidate_risks': risk_rows,
        'n_anchor_configurations': len(anchor_raw),
        'n_anchor_blocks': len(anchor_blocks),
        'interpretation': 'Separate-chain diagnostic only. Passing does not establish ensemble equilibrium, independent-block sufficiency, or a physical score.',
    }
    result = _json_safe(result)
    (output / 'anchor_results.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')

    dev_windows = submission['calibration']['windows']
    anchor_windows = anchor_ref['windows']
    fig, ax = plt.subplots(figsize=(8.5, 5.2), constrained_layout=True)
    x = np.arange(len(p['reference_windows']))
    for label, records, offset, color in (
        ('development', dev_windows, -0.08, '#315a8a'),
        ('independent anchor', anchor_windows, 0.08, '#c26936'),
    ):
        masses = [row.get('mass', np.nan) for row in records]
        errors = [row.get('se', np.nan) for row in records]
        ax.errorbar(x + offset, masses, yerr=errors, fmt='o-', capsize=3,
                    label=label, color=color)
    ax.set_xticks(x, [str(w) for w in p['reference_windows']])
    delta_label = 'n/a' if delta_z is None else f'{delta_z:.2f}'
    ax.set(xlabel='Reference time window', ylabel='Fitted mass',
           title=f'Development vs independent-anchor reference; Δm/combined SE={delta_label}')
    ax.legend(frameon=False)
    fig.savefig(output / 'anchor_reference_windows.png', dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.5, 5.2), constrained_layout=True)
    if risk_draws is None or 'local' not in draw_names:
        ax.text(0.5, 0.5, 'Nested risk comparison abstained; see anchor_results.json',
                ha='center', va='center', transform=ax.transAxes)
        ax.set_axis_off()
    else:
        local_index = draw_names.index('local')
        valid_names = [name for name in draw_names if name in names]
        ratios, lower, upper = [], [], []
        for name in valid_names:
            index = draw_names.index(name)
            draws = risk_draws[:, local_index] / np.maximum(risk_draws[:, index], p['score_epsilon'])
            ratios.append(float(np.median(draws)))
            lower.append(float(np.quantile(draws, 0.025)))
            upper.append(float(np.quantile(draws, 0.975)))
        y = np.arange(len(valid_names))
        ax.errorbar(ratios, y, xerr=[np.asarray(ratios)-lower, np.asarray(upper)-ratios],
                    fmt='o', capsize=3, color='#315a8a')
        ax.axvline(1.0, color='black', ls='--', lw=1)
        ax.set_yticks(y, valid_names)
        ax.set(xlabel='Local risk / candidate risk (nested bootstrap median and 95% interval)',
               title='Candidate risk on the independent anchor (diagnostic only)')
    fig.savefig(output / 'anchor_candidate_risks.png', dpi=180)
    plt.close(fig)

    lines = [
        '# Independent physical-anchor diagnostic', '',
        f"**Status:** `{result['status']}`; `physical_score=null`.", '',
        f"The anchor contains {len(anchor_raw)} configurations in {len(anchor_blocks)} length-"
        f"{p['block_length']} blocks from a separately seeded HMC chain. Development and anchor masses differ by "
        f"{_fmt(delta_z, '.3f')} combined standard errors; the frozen limit is {p['reference_max_window_z']:.2f}.",
        f"Anchor reference-gate result: **{'passed' if anchor_passed else 'failed / inconclusive'}**.",
        '', '## Anchor reference windows', '',
        '| Window | Development mass ± SE | Anchor mass ± SE | Anchor fit p (approx.) |',
        '|---|---:|---:|---:|',
    ]
    for i, window in enumerate(p['reference_windows']):
        dev_row = dev_windows[i]
        anc_row = anchor_windows[i]
        dev_mass_value = dev_row.get('mass')
        dev_se_value = dev_row.get('se')
        anc_mass_value = anc_row.get('mass')
        anc_se_value = anc_row.get('se')
        lines.append(f"| {window} | {_fmt(dev_mass_value)} ± {_fmt(dev_se_value, '.2g')} | "
                     f"{_fmt(anc_mass_value)} ± {_fmt(anc_se_value, '.2g')} | "
                     f"{_fmt(anc_row.get('p_approx'), '.4g')} |")
    lines.extend(['', '## Candidate risks', '',
                  '| Candidate | Anchor risk | Status |', '|---|---:|---|'])
    for row in risk_rows:
        value = '—' if row['risk'] is None else f"{row['risk']:.6g}"
        lines.append(f"| {row['candidate']} | {value} | {row['status']} |")
    lines.extend(['', '## Figures', '',
                  '- `anchor_reference_windows.png`: development and independent-chain reference masses by fit window.',
                  '- `anchor_candidate_risks.png`: candidate-to-local risk ratios on the anchor with nested bootstrap intervals.',
                  '', '## Limits', '',
                  'The anchor is a separate HMC chain, but this diagnostic does not prove thermal equilibrium or decorrelation within either chain. The 60 anchor configurations provide 12 length-5 blocks; block-length sensitivity and acceptance/plaquette diagnostics from the HMC receipt remain required. Passing this anchor gate only permits opening the predeclared blind validation; it does not itself certify a score.'])
    (output / 'anchor_review.md').write_text('\n'.join(lines) + '\n')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--plan', required=True)
    args = parser.parse_args(argv)
    result = run(args.output, args.plan)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
