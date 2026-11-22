"""File-backed, fail-closed runner for unfrozen Wilson reference diagnostics.

This runner only accepts a complete, identity-bound D-development transaction.
It never reads gauge files and never touches validation, gap, or shared holdout.
All output is diagnostic-only and is published into a new directory.
"""
import csv
import hashlib
import io
import json
import platform
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from core.io import digest, fingerprint
from core.stats import blocks

from .identity import check_resume, measurement_spec
from .reference_gate_diagnostic import window_gate_proposals
from .statistics import potential

HERE = Path(__file__).resolve().parent
DEFAULT_PROTOCOL = HERE / 'protocol_d_20261120.json'
TRANSACTION_FILES = ('development.npz', 'development_provenance.json',
                     'development.commit.json')
SOURCE_FILES = ('reference_gate_runner.py', 'reference_gate_diagnostic.py',
                'reference_gate_design.md', 'statistics.py', 'identity.py',
                'common.py', 'kernels.py', 'measure.py', 'stout.py')


def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _snapshot_inputs(root):
    paths = [root / name for name in TRANSACTION_FILES]
    if any(not path.is_file() for path in paths):
        missing = [path.name for path in paths if not path.is_file()]
        raise ValueError(f'incomplete development transaction; missing {missing}')
    before = [path.read_bytes() for path in paths]
    return dict(zip(TRANSACTION_FILES, before))


def _load_complete_development(input_dir, protocol):
    root = Path(input_dir).resolve()
    payloads = _snapshot_inputs(root)
    marker = json.loads(payloads['development.commit.json'])
    expected_ids = list(range(100))
    split_ids = list(range(protocol['development'][0], protocol['development'][1] + 1))
    if split_ids != expected_ids:
        raise ValueError(f'expected frozen D development IDs 0-99, found {split_ids[:2]}..{split_ids[-2:]}')
    if marker.get('split') != 'development':
        raise ValueError('commit marker is not for the development split')

    spec = measurement_spec(protocol, 'development')
    n_rows = check_resume(root, 'development', spec, verify_gauge=False)
    if n_rows != 100:
        raise ValueError(f'incomplete development transaction: {n_rows}/100 committed rows')
    after = _snapshot_inputs(root)
    if payloads != after:
        raise ValueError('development transaction changed while it was being read')

    generation = marker.get('generation')
    with np.load(io.BytesIO(payloads['development.npz']), allow_pickle=False) as data:
        ids = data['ids'].astype(np.int64, copy=True)
        loops = data['loops'].copy()
        stored_protocol_hash = str(data['protocol_hash'])
        stored_generation = str(data['generation'])
    expected_shape = (100, len(protocol['kernels']), len(protocol['r_values']),
                      len(protocol['t_values']))
    if ids.tolist() != expected_ids:
        raise ValueError('development IDs are not exactly the ordered range 0-99')
    if loops.shape != expected_shape or not np.isrealobj(loops) or not np.isfinite(loops).all():
        raise ValueError(f'expected finite real loops with shape {expected_shape}, got {loops.shape}')
    protocol_hash = fingerprint(protocol)
    if stored_protocol_hash != protocol_hash:
        raise ValueError('NPZ protocol fingerprint differs from the supplied frozen protocol')
    if stored_generation != generation or generation != fingerprint(spec):
        raise ValueError('NPZ, commit marker, and current measurement spec generations differ')

    provenance = json.loads(payloads['development_provenance.json'])
    expected_manifest_hash = protocol.get('input_manifest', {}).get('sha256')
    if provenance.get('input_manifest_sha256') != expected_manifest_hash:
        raise ValueError('provenance input-manifest identity differs from the frozen protocol')
    if provenance.get('ensemble') != protocol.get('ensemble'):
        raise ValueError('provenance ensemble differs from the frozen protocol')
    records = provenance.get('records', [])
    trajectory_ids = [record.get('hmc_trajectory') for record in records]
    gauge_hashes = [record.get('gauge_sha256') for record in records]
    if (len(records) != 100 or any(not isinstance(t, int) for t in trajectory_ids)
            or len(set(trajectory_ids)) != 100
            or any(not isinstance(h, str) or len(h) != 64
                   or any(char not in '0123456789abcdef' for char in h.lower())
                   for h in gauge_hashes)):
        raise ValueError('development provenance lacks unique trajectory IDs or gauge SHA-256 values')

    reference_kernel = protocol.get('reference_kernel')
    kernels = protocol['kernels']
    if (not isinstance(reference_kernel, int) or not 0 <= reference_kernel < len(kernels)
            or kernels[reference_kernel].get('name') != 'identity'
            or kernels[reference_kernel].get('kind') != 'ape'
            or kernels[reference_kernel].get('alpha') != 0.0
            or kernels[reference_kernel].get('steps') != 0):
        raise ValueError('frozen reference kernel is not the identity operator')

    # The RunSpec independently lists all production dependencies. Verify those
    # source bytes too; the measurement transaction validates its own dependency set.
    for name, expected_hash in protocol.get('source_hashes', {}).items():
        if Path(name).name != name or not (HERE / name).is_file():
            raise ValueError(f'unsupported or missing frozen source dependency {name!r}')
        if digest(HERE / name) != expected_hash:
            raise ValueError(f'frozen protocol source hash mismatch for {name}')

    identity_loops = loops[:, reference_kernel, :, :]
    return {
        'input_dir': root,
        'payloads': payloads,
        'marker': marker,
        'spec': spec,
        'generation': generation,
        'protocol_hash': protocol_hash,
        'identity_loops': identity_loops,
        'ids': ids,
        'n_rows': n_rows,
        'trajectory_ids': trajectory_ids,
        'gauge_sha256_values': gauge_hashes,
    }


def _window_rows(result, r_values, windows):
    rows = []
    for proposal in ('A', 'B'):
        for contrast in result[proposal]['contrasts']:
            i, j = contrast['window_i'], contrast['window_j']
            rows.append({
                'proposal': proposal,
                'R': r_values[contrast['r_index']],
                'window_i': i,
                'window_i_T': json.dumps(windows[i]),
                'window_j': j,
                'window_j_T': json.dumps(windows[j]),
                'point_difference': contrast['point_difference'],
                'paired_sd': contrast['paired_sd'],
                'denominator_floor': contrast['denominator_floor'],
                'signed_z': contrast['z'],
                'valid_draw_count': contrast['valid_draw_count'],
                'invalid_draw_count': contrast['invalid_draw_count'],
                'invalid_draw_indices': json.dumps(contrast['invalid_draw_indices']),
                'failure_reasons': json.dumps(contrast['failure_reasons']),
            })
    return rows


def _write_csv(path, rows, columns):
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def _plot_reference_windows(path, identity_loops, result, protocol):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    windows = protocol['reference_windows']
    t_values = protocol['t_values']
    blocked = blocks(identity_loops, protocol['block_length'])
    index = np.asarray(result['bootstrap_index'], dtype=np.int64)
    mean = blocked.mean(axis=0)
    boot_mean = blocked[index].mean(axis=1)
    points = np.stack([potential(mean, w, t_values) for w in windows], axis=1)
    boot = np.stack([potential(boot_mean, w, t_values) for w in windows], axis=2)
    marginal_sd = boot.std(axis=0, ddof=1)

    fig, axes = plt.subplots(len(protocol['r_values']), 2, figsize=(12, 13), squeeze=False)
    x = np.arange(len(windows))
    for ridx, r in enumerate(protocol['r_values']):
        axes[ridx, 0].errorbar(x, points[ridx], yerr=marginal_sd[ridx], marker='o', capsize=3)
        axes[ridx, 0].set_xticks(x, [f'{w[0]}–{w[-1]}' for w in windows])
        axes[ridx, 0].set_ylabel('aV(R)')
        axes[ridx, 0].set_title(f'R={r}: window potential ± marginal bootstrap SD')
        axes[ridx, 0].grid(alpha=.25)

        contrasts = [row for row in result['A']['contrasts'] if row['r_index'] == ridx]
        cx = np.arange(len(contrasts))
        vals = [row['point_difference'] for row in contrasts]
        errs = [row['paired_sd'] for row in contrasts]
        axes[ridx, 1].errorbar(cx, vals, yerr=errs, marker='o', capsize=3)
        axes[ridx, 1].axhline(0, color='black', linewidth=.8)
        axes[ridx, 1].set_xticks(cx, [f'{row["window_i"]}−{row["window_j"]}' for row in contrasts])
        axes[ridx, 1].set_ylabel('aΔV')
        axes[ridx, 1].set_title(f'R={r}: paired difference ± paired bootstrap SD')
        axes[ridx, 1].grid(alpha=.25)
    fig.suptitle('Development only; proposal not frozen; paired errors use shared bootstrap draws')
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _plot_z(path, result, protocol):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    nominal = protocol['reference_nominal_window']
    windows = protocol['reference_windows']
    other = [i for i in range(len(windows)) if i != nominal]
    matrix = np.full((len(protocol['r_values']), len(other)), np.nan)
    for row in result['A']['contrasts']:
        col = other.index(row['window_i'])
        matrix[row['r_index'], col] = np.nan if row['z'] is None else row['z']
    fig, ax = plt.subplots(figsize=(7, 4.5))
    cmap = plt.get_cmap('coolwarm').with_extremes(bad='#bdbdbd')
    image = ax.imshow(np.ma.masked_invalid(matrix), cmap=cmap, vmin=-2.5, vmax=2.5,
                      aspect='auto')
    ax.set_xticks(range(len(other)), [f'{windows[i]} vs {windows[nominal]}' for i in other])
    ax.set_yticks(range(len(protocol['r_values'])), [f'R={r}' for r in protocol['r_values']])
    for row in range(matrix.shape[0]):
        for col in range(matrix.shape[1]):
            label = 'ABSTAIN' if not np.isfinite(matrix[row, col]) else f'{matrix[row, col]:.3g}'
            ax.text(col, row, label, ha='center', va='center', fontsize=9)
    title = f"A proposal signed z; max |z|={result['A']['maximum']} (threshold 2.5)"
    ax.set_title(title + '\nDevelopment diagnostic only; no family-wise calibration')
    fig.colorbar(image, ax=ax, label='signed z (color saturates at ±2.5)')
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _plot_joint_max(path, result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 4.5))
    c = result['C']
    if c.get('centered') is None or c.get('uncentered') is None:
        ax.text(.5, .5, 'C proposal ABSTAIN: required contrast diagnostics are invalid',
                ha='center', va='center', transform=ax.transAxes)
    else:
        for key, label, color in (('centered', 'centered', 'tab:blue'),
                                  ('uncentered', 'uncentered', 'tab:orange')):
            values = c[key]['draw_maxima']
            ax.hist(values, bins=40, density=True, alpha=.42, label=label, color=color)
            ax.axvline(c[key]['q95'], color=color, linestyle='--',
                       label=f'{label} linear q95={c[key]["q95"]:.3g}')
        ax.axvline(2.5, color='black', linestyle=':', label='candidate threshold 2.5')
        ax.legend(fontsize=8)
    ax.set_xlabel('joint maximum |standardized contrast|')
    ax.set_ylabel('density')
    ax.set_title('Unfrozen C proposal sensitivity; not family-wise calibrated')
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _candidate_rows(result):
    rows = []
    for name in ('A', 'B'):
        proposal = result[name]
        rows.append({'proposal': name, 'variant': 'point_max', 'status': proposal['status'],
                     'statistic': proposal['maximum'], 'candidate_decision': proposal['status'],
                     'threshold': result['threshold'], 'argmax': json.dumps(proposal['argmax'])})
    c = result['C']
    for variant in ('centered', 'uncentered'):
        item = c.get(variant)
        rows.append({'proposal': 'C', 'variant': variant,
                     'status': 'DIAGNOSTIC_ONLY' if item is not None else 'ABSTAIN',
                     'statistic': None if item is None else item['q95'],
                     'candidate_decision': None if item is None else item['candidate_decision'],
                     'threshold': result['threshold'], 'argmax': ''})
    return rows


def _write_report(path, result, receipt):
    def fmt(value):
        return 'ABSTAIN / undefined' if value is None else f'{value:.8g}'

    a, b, c = result['A'], result['B'], result['C']
    failures = sum(bool(row['failure_reasons']) for name in ('A', 'B')
                   for row in result[name]['contrasts'])
    invalid_draws = sum(row['invalid_draw_count'] for name in ('A', 'B')
                        for row in result[name]['contrasts'])
    lines = [
        '# Wilson reference-window diagnostics', '',
        '**Status:** `PROPOSAL_NOT_FROZEN`; `scope=development_diagnostic_only`; '
        '`production_score=null`.', '',
        '## Input and method', '',
        f"- Split: development IDs 0–99; generation `{receipt['generation']}`.",
        f"- Input files: NPZ `{receipt['inputs']['development.npz']['sha256']}`, "
        f"provenance `{receipt['inputs']['development_provenance.json']['sha256']}`, "
        f"commit marker `{receipt['inputs']['development.commit.json']['sha256']}`.",
        f"- Identity loops: {result['parameters']['nconfig']} configurations, "
        f"{result['parameters']['nblocks']} consecutive blocks of length "
        f"{result['parameters']['block_length']}; {result['parameters']['bootstrap_samples']} shared "
        f"bootstrap draws. Index matrix SHA-256: `{receipt['bootstrap_indices_sha256']}`.",
        f"- Candidate threshold: {result['threshold']}; equality passes by the unfrozen proposal rule.", '',
        '- Potentials and paired differences are reported in lattice units (`aV` and `aΔV`); '
        'R and T are lattice separations.', '',
        '## Candidate comparison', '',
        '| Proposal | Candidate result | Statistic | Failed contrasts | Invalid draws |',
        '| --- | --- | ---: | ---: | ---: |',
        f"| A: nominal point-max | {a['status']} | {fmt(a['maximum'])} | "
        f"{sum(bool(x['failure_reasons']) for x in a['contrasts'])} | "
        f"{sum(x['invalid_draw_count'] for x in a['contrasts'])} |",
        f"| B: all-pair point-max | {b['status']} | {fmt(b['maximum'])} | "
        f"{sum(bool(x['failure_reasons']) for x in b['contrasts'])} | "
        f"{sum(x['invalid_draw_count'] for x in b['contrasts'])} |",
        f"| C: centered joint q95 | {('ABSTAIN' if c['centered'] is None else c['centered']['candidate_decision'])} | "
        f"{fmt(None if c['centered'] is None else c['centered']['q95'])} | {failures} | {invalid_draws} |",
        f"| C: uncentered joint q95 | {('ABSTAIN' if c['uncentered'] is None else c['uncentered']['candidate_decision'])} | "
        f"{fmt(None if c['uncentered'] is None else c['uncentered']['q95'])} | {failures} | {invalid_draws} |", '',
        'These are candidate diagnostic outcomes on the frozen development sample. They do not select '
        'a production rule, establish a physical reference, or authorize access to another split.', '',
        '## Figures and interpretation', '',
        '- `reference_windows.png` shows window potentials with marginal bootstrap SD and paired '
        'window differences with their shared-draw SD.',
        '- `reference_window_z.png` shows the signed A-proposal contrast z values; grey cells are '
        'abstentions.',
        '- `reference_joint_max.png` compares centered and uncentered C joint maxima when defined.',
        '- Common shifts shared by all windows can remain invisible to window-stability diagnostics. '
        'The threshold and C quantile have no family-wise coverage calibration here.', '',
        '## Limits and access record', '',
        '- The runner verifies the frozen protocol/source hashes and transaction-internal NPZ, '
        'provenance, generation, per-row loop hashes, declared manifest hash, unique trajectory '
        'IDs, and per-row gauge SHA-256 fields. It does not reopen the manifest or re-read raw gauge bytes.',
        '- No validation, gap, or shared-holdout files were accessed. No production score was '
        'computed or written.',
        '- Any `PROPOSAL_DIAGNOSTIC_PASS` is not a physical certification; a failed or undefined '
        'contrast remains visible in `reference_failures.csv` and the receipt.', '',
    ]
    path.write_text('\n'.join(lines), encoding='utf-8')


def run_reference_gate_diagnostic(input_dir, output_dir, protocol_path=DEFAULT_PROTOCOL):
    """Validate a complete D-development transaction, then write diagnostic artifacts.

    ``output_dir`` must not exist and must not be the input directory or one of
    its descendants. No output is created unless the complete input passes all
    frozen-identity and numerical checks.
    """
    input_root = Path(input_dir).resolve()
    output_root = Path(output_dir).resolve()
    if output_root == input_root or input_root in output_root.parents:
        raise ValueError('output directory must be outside the immutable input transaction')
    if output_root.exists():
        raise FileExistsError(f'refusing to overwrite existing output directory {output_root}')
    if not output_root.parent.is_dir():
        raise FileNotFoundError(f'output parent directory does not exist: {output_root.parent}')

    protocol_path = Path(protocol_path).resolve()
    protocol_bytes = protocol_path.read_bytes()
    protocol = json.loads(protocol_bytes)
    if protocol.get('status') != 'FROZEN_PREFLIGHT_ONLY_NOT_RUN':
        raise ValueError('protocol is not the frozen preflight-only D measurement RunSpec')
    sample = _load_complete_development(input_root, protocol)
    result = window_gate_proposals(
        sample['identity_loops'], windows=protocol['reference_windows'],
        t_values=protocol['t_values'], nominal=protocol['reference_nominal_window'],
        block_length=protocol['block_length'], bootstrap_samples=protocol['bootstrap_samples'],
        seed=protocol['seed'])
    if result['scope'] != 'development_diagnostic_only' or result['production_score'] is not None:
        raise RuntimeError('diagnostic module returned an unexpected scope or score')

    raw_index = np.asarray(result['bootstrap_index'], dtype='<i8')
    index_bytes = raw_index.tobytes()
    if _sha256_bytes(index_bytes) != result['index_sha256_le_i8']:
        raise RuntimeError('bootstrap index matrix hash does not match the diagnostic receipt')
    rows = _window_rows(result, protocol['r_values'], protocol['reference_windows'])
    failed_rows = [row for row in rows if row['failure_reasons'] != '[]'
                   or row['invalid_draw_count'] > 0]

    source_hashes = {name: digest(HERE / name) for name in SOURCE_FILES}
    repo_root = HERE.parents[1]
    source_hashes['core/stats.py'] = digest(repo_root / 'core' / 'stats.py')
    source_hashes['tests/test_wilson_reference_gate_runner.py'] = digest(
        repo_root / 'tests' / 'test_wilson_reference_gate_runner.py')
    receipt = {
        'schema': 'latticearena-wilson-reference-gate-diagnostic-receipt-v1',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'classification': 'development_diagnostic_only',
        'scope': 'development_diagnostic_only',
        'status': result['status'],
        'comparison_status': result['comparison_status'],
        'production_score': None,
        'validation_accessed': False,
        'gap_accessed': False,
        'shared_holdout_accessed': False,
        'raw_gauge_bytes_read_by_runner': False,
        'protocol_path': str(protocol_path),
        'protocol_sha256': _sha256_bytes(protocol_bytes),
        'protocol_fingerprint': sample['protocol_hash'],
        'measurement_spec_fingerprint': fingerprint(sample['spec']),
        'observable_units': 'aV(R) and aΔV; R and T are lattice separations',
        'generation': sample['generation'],
        'split': 'development',
        'ids': sample['ids'].tolist(),
        'trajectory_ids': sample['trajectory_ids'],
        'gauge_sha256_values': sample['gauge_sha256_values'],
        'inputs': {name: {'sha256': _sha256_bytes(data), 'bytes': len(data)}
                   for name, data in sample['payloads'].items()},
        'source_hashes': source_hashes,
        'frozen_protocol_source_hashes_verified': True,
        'bootstrap_indices_file': 'bootstrap_indices_le_i8.bin',
        'bootstrap_indices_sha256': _sha256_bytes(index_bytes),
        'bootstrap_indices_shape': list(raw_index.shape),
        'analysis_parameters': result['parameters'],
        'limitations': result['limits'],
    }
    result_for_json = dict(result)
    result_for_json.pop('bootstrap_index')
    candidate_rows = _candidate_rows(result)

    output_root.mkdir(exist_ok=False)
    try:
        (output_root / 'bootstrap_indices_le_i8.bin').write_bytes(index_bytes)
        (output_root / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True,
                                                                allow_nan=False) + '\n',
                                                   encoding='utf-8')
        (output_root / 'results.json').write_text(json.dumps(result_for_json, indent=2,
                                                              sort_keys=True, allow_nan=False) + '\n',
                                                   encoding='utf-8')
        _write_csv(output_root / 'reference_window_rows.csv', rows,
                   list(rows[0].keys()) if rows else ['proposal', 'R', 'window_i', 'window_j'])
        _write_csv(output_root / 'reference_failures.csv', failed_rows,
                   list(rows[0].keys()) if rows else ['proposal', 'R', 'window_i', 'window_j'])
        _write_csv(output_root / 'candidate_decisions.csv', candidate_rows,
                   ['proposal', 'variant', 'status', 'statistic', 'candidate_decision',
                    'threshold', 'argmax'])
        _plot_reference_windows(output_root / 'reference_windows.png', sample['identity_loops'],
                                result, protocol)
        _plot_z(output_root / 'reference_window_z.png', result, protocol)
        _plot_joint_max(output_root / 'reference_joint_max.png', result)
        _write_report(output_root / 'REFERENCE_REPORT.md', result, receipt)
    except Exception:
        shutil.rmtree(output_root, ignore_errors=True)
        raise
    return {'output_dir': str(output_root), 'receipt': receipt, 'result': result}


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, help='directory containing the committed development transaction')
    parser.add_argument('--output', required=True, help='new output directory; existing paths are refused')
    parser.add_argument('--protocol', default=str(DEFAULT_PROTOCOL), help='frozen D protocol JSON')
    args = parser.parse_args(argv)
    summary = run_reference_gate_diagnostic(args.input, args.output, args.protocol)
    print(json.dumps({'output_dir': summary['output_dir'],
                      'status': summary['receipt']['status'],
                      'comparison_status': summary['receipt']['comparison_status'],
                      'production_score': None,
                      'report': str(Path(summary['output_dir']) / 'REFERENCE_REPORT.md')},
                     sort_keys=True))


if __name__ == '__main__':
    main()
