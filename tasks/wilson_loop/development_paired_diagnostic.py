"""Development-only paired risk and cost diagnostic for a complete Wilson bundle.

This does not call experiment.develop/evaluate, select a submission, or create a
physical score. It reuses the complete-transaction guard from the reference
runner and reports risk ratios only as diagnostics under the declared windows.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import shutil
from pathlib import Path

import numpy as np

from core.io import digest

from .reference_gate_runner import DEFAULT_PROTOCOL, _load_complete_development
from .statistics import blocks, bootstrap_indices, potential


def _kernel_risks(data, inner_index, windows, t_values, nominal_indices):
    """Compute the same precision-plus-window-spread risk as statistics.risk.

    The inner block-bootstrap indices are shared across kernels so candidate
    differences stay paired. Returns per-nominal risk vectors and explicit
    kernel-level invalid reasons.
    """
    data = np.asarray(data, dtype=float)
    if data.ndim != 4:
        raise ValueError('expected blocks with shape (block,kernel,R,T)')
    if not np.isfinite(data).all():
        raise ValueError('non-finite loop data')
    mean = data.mean(axis=0)
    boot_mean = data[inner_index].mean(axis=1)
    n_kernel = data.shape[1]
    n_window = len(windows)
    window_potentials = np.stack(
        [potential(mean, window, t_values) for window in windows], axis=-1)
    out = {}
    for nominal in nominal_indices:
        risks = np.full(n_kernel, np.nan, dtype=float)
        reasons = [''] * n_kernel
        reference = window_potentials[0, :, nominal]
        if not np.isfinite(reference).all() or np.any(np.abs(reference) < 1e-12):
            reasons = ['invalid_identity_reference'] * n_kernel
            out[nominal] = (risks, reasons)
            continue
        spread = window_potentials.std(axis=-1, ddof=0)
        for kernel in range(n_kernel):
            if not np.isfinite(mean[kernel]).all() or np.any(mean[kernel] <= 0):
                reasons[kernel] = 'nonpositive_or_nonfinite_mean_loop'
                continue
            draws = boot_mean[:, kernel]
            if not np.isfinite(draws).all() or np.any(draws <= 0):
                reasons[kernel] = 'nonpositive_or_nonfinite_bootstrap_loop'
                continue
            try:
                v_boot = potential(draws, windows[nominal], t_values)
            except (FloatingPointError, ValueError, ZeroDivisionError):
                reasons[kernel] = 'potential_evaluation_failed'
                continue
            se = v_boot.std(axis=0, ddof=1)
            value = float(np.mean((se / reference) ** 2
                                  + (spread[kernel] / reference) ** 2))
            if not np.isfinite(value) or value < 0:
                reasons[kernel] = 'invalid_risk'
                continue
            risks[kernel] = value
        out[nominal] = (risks, reasons)
    return out


def paired_risk_diagnostic(loops, protocol, *, outer_samples=500, inner_samples=500,
                           seed=2026112121):
    """Return paired block-bootstrap ratios for each candidate and nominal window."""
    if isinstance(outer_samples, bool) or outer_samples < 1:
        raise ValueError('outer_samples must be positive')
    if isinstance(inner_samples, bool) or inner_samples < 2:
        raise ValueError('inner_samples must be at least two')
    raw = np.asarray(loops, dtype=float)
    expected_tail = (len(protocol['kernels']), len(protocol['r_values']),
                     len(protocol['t_values']))
    if raw.ndim != 4 or raw.shape[1:] != expected_tail or not np.isfinite(raw).all():
        raise ValueError(f'expected finite loops with trailing shape {expected_tail}, got {raw.shape}')
    block_length = int(protocol['block_length'])
    data = blocks(raw, block_length)
    if len(data) < 2:
        raise ValueError('at least two configuration blocks are required')
    windows = protocol['reference_windows']
    t_values = protocol['t_values']
    nominal_indices = list(range(len(windows)))
    inner_index = bootstrap_indices(len(data), inner_samples, seed + 1)
    point = _kernel_risks(data, inner_index, windows, t_values, nominal_indices)

    rng = np.random.default_rng(seed)
    outer_index = rng.integers(0, len(data), size=(outer_samples, len(data)))
    ratios = np.full((outer_samples, len(nominal_indices), len(protocol['kernels']) - 1),
                     np.nan, dtype=float)
    reasons = np.full(ratios.shape, '', dtype=object)
    for draw, selected in enumerate(outer_index):
        trial = _kernel_risks(data[selected], inner_index, windows, t_values, nominal_indices)
        for nominal in nominal_indices:
            risk_values, invalid = trial[nominal]
            baseline = risk_values[0]
            for candidate in range(1, len(protocol['kernels'])):
                target = (draw, nominal, candidate - 1)
                if invalid[0]:
                    reasons[target] = 'identity:' + invalid[0]
                elif invalid[candidate]:
                    reasons[target] = 'candidate:' + invalid[candidate]
                elif not np.isfinite(baseline) or baseline <= 0:
                    reasons[target] = 'invalid_identity_risk'
                elif not np.isfinite(risk_values[candidate]) or risk_values[candidate] <= 0:
                    reasons[target] = 'nonpositive_candidate_risk'
                else:
                    ratios[target] = baseline / risk_values[candidate]

    point_rows, summary_rows = [], []
    for nominal in nominal_indices:
        risk_values, invalid = point[nominal]
        baseline = risk_values[0]
        for candidate in range(1, len(protocol['kernels'])):
            ratio = (baseline / risk_values[candidate]
                     if (not invalid[0] and not invalid[candidate]
                         and np.isfinite(baseline) and baseline > 0
                         and np.isfinite(risk_values[candidate])
                         and risk_values[candidate] > 0) else None)
            point_reason = (invalid[0] or invalid[candidate])
            if ratio is None and not point_reason:
                point_reason = ('nonpositive_identity_risk' if not np.isfinite(baseline) or baseline <= 0
                                else 'nonpositive_candidate_risk')
            point_rows.append({
                'nominal_window_index': nominal,
                'nominal_window_T': windows[nominal],
                'candidate_index': candidate,
                'candidate': protocol['kernels'][candidate]['name'],
                'identity_risk': float(baseline) if np.isfinite(baseline) else None,
                'candidate_risk': (float(risk_values[candidate])
                                   if np.isfinite(risk_values[candidate]) else None),
                'risk_ratio_identity_over_candidate': float(ratio) if ratio is not None else None,
                'point_status': ('valid_diagnostic' if ratio is not None else
                                 f'invalid:{point_reason}'),
            })
            samples = ratios[:, nominal, candidate - 1]
            valid = samples[np.isfinite(samples)]
            reason_values = [value for value in reasons[:, nominal, candidate - 1] if value]
            summary_rows.append({
                'nominal_window_index': nominal,
                'nominal_window_T': json.dumps(windows[nominal]),
                'candidate': protocol['kernels'][candidate]['name'],
                'point_risk_ratio': ratio,
                'bootstrap_median_ratio': float(np.median(valid)) if len(valid) else None,
                'ci95_low': float(np.quantile(valid, 0.025)) if len(valid) else None,
                'ci95_high': float(np.quantile(valid, 0.975)) if len(valid) else None,
                'valid_outer_draws': int(len(valid)),
                'invalid_outer_draws': int(outer_samples - len(valid)),
                'most_common_invalid_reason': (max(set(reason_values), key=reason_values.count)
                                               if reason_values else ''),
            })
    return {
        'blocks': int(len(data)), 'block_length': block_length,
        'inner_index': inner_index, 'outer_index': outer_index,
        'ratios': ratios, 'reasons': reasons,
        'point_rows': point_rows, 'summary_rows': summary_rows,
        'outer_samples': outer_samples, 'inner_samples': inner_samples, 'seed': seed,
    }


def _write_csv(path, rows):
    if not rows:
        path.write_text('')
        return
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _plot(output, summary_rows, cost_rows):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    candidates = list(dict.fromkeys(row['candidate'] for row in summary_rows))
    nominal_labels = {}
    for row in summary_rows:
        nominal_labels[row['nominal_window_index']] = row['nominal_window_T']
    markers = ['o', 's', '^', 'D', 'v', 'P']
    colors = plt.get_cmap('tab10').colors
    fig, (ax_ci, ax_cost) = plt.subplots(1, 2, figsize=(14, 6))
    y_ticks, y_labels = [], []
    for index, candidate in enumerate(candidates):
        cost = next(row['active_kernel_plus_loop_seconds_mean'] for row in cost_rows
                    if row['candidate'] == candidate)
        for nominal in sorted(nominal_labels):
            row = next(item for item in summary_rows
                       if item['candidate'] == candidate
                       and item['nominal_window_index'] == nominal)
            y = index * len(nominal_labels) + nominal
            if row['point_risk_ratio'] is not None and row['ci95_low'] is not None:
                ax_ci.errorbar(row['point_risk_ratio'], y,
                               xerr=[[row['point_risk_ratio'] - row['ci95_low']],
                                     [row['ci95_high'] - row['point_risk_ratio']]],
                               fmt=markers[nominal % len(markers)],
                               color=colors[nominal % len(colors)], capsize=2,
                               label=f'nominal {nominal}' if index == 0 else None)
                ax_cost.scatter(cost, row['point_risk_ratio'],
                                marker=markers[nominal % len(markers)],
                                color=colors[nominal % len(colors)], s=45)
            y_ticks.append(y)
            y_labels.append(f'{candidate} | nominal={nominal}')
    ax_ci.axvline(1.0, color='black', linewidth=1)
    ax_ci.set_xscale('log')
    ax_ci.set_yticks(y_ticks, y_labels, fontsize=7)
    ax_ci.set_xlabel('risk(identity) / risk(candidate), log scale')
    ax_ci.set_title('Paired block-bootstrap diagnostic; interval is percentile 95%')
    ax_ci.grid(axis='x', alpha=0.25)
    ax_ci.legend(fontsize=8)
    ax_cost.axhline(1.0, color='black', linewidth=1)
    ax_cost.set_xscale('log')
    ax_cost.set_xlabel('mean per-config kernel + loop seconds')
    ax_cost.set_ylabel('point risk(identity) / risk(candidate)')
    ax_cost.set_title('Risk versus measured active compute time')
    ax_cost.grid(alpha=0.25)
    fig.suptitle('D development IDs 0–99 only; reference proposal unfrozen; no physical score')
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def run(input_dir, output_dir, protocol_path=DEFAULT_PROTOCOL, *, outer_samples=500,
        inner_samples=500, seed=2026112121, job_id=None, scheduler_elapsed_seconds=None):
    protocol_path = Path(protocol_path).resolve()
    protocol_bytes = protocol_path.read_bytes()
    protocol = json.loads(protocol_bytes)
    sample = _load_complete_development(input_dir, protocol)
    with np.load(io.BytesIO(sample['payloads']['development.npz']), allow_pickle=False) as saved:
        loops = saved['loops'].copy()
    result = paired_risk_diagnostic(
        loops, protocol, outer_samples=outer_samples, inner_samples=inner_samples, seed=seed)
    provenance = json.loads(sample['payloads']['development_provenance.json'])
    timing = provenance['records']
    names = [row['name'] for row in protocol['kernels']]
    cost_rows = []
    for name in names:
        kernel = np.asarray([row['kernel_seconds_by_candidate'][name] for row in timing], dtype=float)
        loop = np.asarray([row['loop_seconds_by_candidate'][name] for row in timing], dtype=float)
        cost_rows.append({
            'candidate': name,
            'n_configurations': int(len(timing)),
            'kernel_seconds_mean': float(kernel.mean()),
            'kernel_seconds_median': float(np.median(kernel)),
            'loop_seconds_mean': float(loop.mean()),
            'active_kernel_plus_loop_seconds_mean': float((kernel + loop).mean()),
            'active_kernel_plus_loop_seconds_median': float(np.median(kernel + loop)),
            'shared_host_read_seconds_mean': float(np.mean([row['host_read_seconds'] for row in timing])),
            'shared_device_transfer_seconds_mean': float(np.mean([row['device_transfer_seconds'] for row in timing])),
            'shared_setup_seconds_mean': float(np.mean([row['setup_seconds'] for row in timing])),
        })

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    try:
        point_path = output_dir / 'paired_point_risks.csv'
        _write_csv(point_path, result['point_rows'])
        summary_path = output_dir / 'paired_bootstrap_summary.csv'
        _write_csv(summary_path, result['summary_rows'])
        cost_path = output_dir / 'candidate_costs.csv'
        _write_csv(cost_path, cost_rows)
        draw_rows = []
        for draw in range(result['outer_samples']):
            for nominal in range(len(protocol['reference_windows'])):
                for candidate in range(1, len(protocol['kernels'])):
                    value = result['ratios'][draw, nominal, candidate - 1]
                    draw_rows.append({
                        'draw': draw, 'nominal_window_index': nominal,
                        'candidate': protocol['kernels'][candidate]['name'],
                        'risk_ratio_identity_over_candidate': (float(value)
                                                               if np.isfinite(value) else None),
                        'status': ('valid' if np.isfinite(value) else
                                   result['reasons'][draw, nominal, candidate - 1]),
                    })
        _write_csv(output_dir / 'paired_bootstrap_draws.csv', draw_rows)
        inner_path = output_dir / 'inner_bootstrap_indices_le_i8.bin'
        outer_path = output_dir / 'outer_bootstrap_indices_le_i8.bin'
        np.asarray(result['inner_index'], dtype='<i8').tofile(inner_path)
        np.asarray(result['outer_index'], dtype='<i8').tofile(outer_path)
        _plot(output_dir / 'paired_risk_vs_cost.png', result['summary_rows'], cost_rows)
        summary_lookup = {(row['candidate'], row['nominal_window_index']): row
                          for row in result['summary_rows']}
        rows = []
        for candidate in names[1:]:
            entries = [summary_lookup[candidate, nominal] for nominal in range(len(protocol['reference_windows']))]
            rows.append('| ' + ' | '.join([
                candidate,
                ', '.join('–'.join(map(str, protocol['reference_windows'][i])) for i in range(len(entries))),
                '; '.join('NA' if x['point_risk_ratio'] is None else f"{x['point_risk_ratio']:.4g} [{x['ci95_low']:.4g}, {x['ci95_high']:.4g}]"
                          for x in entries),
                '; '.join(f"{x['valid_outer_draws']}/{result['outer_samples']}" for x in entries),
            ]) + ' |')
        report = [
            '# Wilson D development paired risk/cost diagnostic', '',
            '**状态：** `development_diagnostic_only`；参考门提案仍 `PROPOSAL_NOT_FROZEN`；`production_score=null`。',
            '',
            '## 输入与定义', '',
            f"- 仅使用已提交 D development IDs 0–99；generation `{sample['generation']}`；同一组loops同时包含identity、APE与stout候选。",
            f"- 测量文件sha：NPZ `{hashlib.sha256(sample['payloads']['development.npz']).hexdigest()}`；provenance `{hashlib.sha256(sample['payloads']['development_provenance.json']).hexdigest()}`；commit `{hashlib.sha256(sample['payloads']['development.commit.json']).hexdigest()}`。",
            f"- 按冻结 `block_length={result['block_length']}` 聚成 {result['blocks']} 个配置块；{result['outer_samples']} 次外层配对块bootstrap、每次 {result['inner_samples']} 个共享内层bootstrap draws，seed={seed}。两层索引以二进制原样保存。",
            '- 风险沿用 `precision + spread` 定义；每个候选和 identity 使用相同 block/bootstrap draws。表中比值为 `risk(identity)/risk(candidate)`，大于 1 表示该风险泛函在此开发样本上较低。',
            '- nominal reference 分别取三个预声明 T 窗口；这是一项参考窗口敏感性扫描，不以任一窗口选择生产 reference。',
            '', '## 配对结果', '',
            '| 候选 | nominal T 窗口（顺序同下列比值） | point ratio [paired bootstrap 95% interval] | 有效外层draw/总数 |',
            '| --- | --- | --- | --- |', *rows,
            '', '![D development paired risk and cost](paired_risk_vs_cost.png)', '',
            '## 成本和边界', '',
            '- 图右侧使用每配置实测 `kernel_seconds_by_candidate + loop_seconds_by_candidate` 的均值；同一单配置测量记录中的 host read、device transfer 与 setup 是共享开销，图中未把它们重复分摊给每个候选。表 `candidate_costs.csv` 同时给出这些共享时间。',
            '- 所有候选在同一 GPU job 顺序测量，所示单配置时间不等价于独立 arm 的 matched-walltime benchmark；job 全程耗时和 setup 规则见关联 scheduler/provenance receipt。',
            '- 这 100 个 development IDs 已用于算法开发，不能作 blind confirmation。风险的分母来自 identity reference，而 reference-window runner 在同一数据上给出 A/B 诊断通过、C joint-max 诊断拒绝；该提案未冻结、也没有 family-wise calibration。共同偏差仍可能同时移动所有窗口。',
            '- 因此结果不能选定生产窗口、认证 ground-state accuracy、证明 APE/stout 物理优劣或产生 `physical_score`；gap 100–119、validation 120–139 和 shared holdout 140–199 均未读取。无效 outer draw 在 CSV 中保留原因，不当作通过。',
        ]
        (output_dir / 'PAIRED_REPORT.md').write_text('\n'.join(report) + '\n', encoding='utf-8')
        receipt = {
            'schema': 'latticearena-wilson-development-paired-diagnostic-v1',
            'classification': 'development_diagnostic_only',
            'status': 'PROPOSAL_NOT_FROZEN',
            'comparison_status': 'DIAGNOSTIC_ONLY',
            'production_score': None,
            'validation_accessed': False, 'gap_accessed': False,
            'shared_holdout_accessed': False, 'raw_gauge_bytes_read_by_runner': False,
            'protocol_sha256': hashlib.sha256(protocol_bytes).hexdigest(),
            'generation': sample['generation'], 'split': 'development',
            'ids': sample['ids'].tolist(),
            'trajectory_ids': sample['trajectory_ids'],
            'gauge_sha256_values': sample['gauge_sha256_values'],
            'inputs': {name: hashlib.sha256(data).hexdigest()
                       for name, data in sample['payloads'].items()},
            'source_hashes': {name: digest(Path(__file__).with_name(name))
                              for name in ('development_paired_diagnostic.py',
                                           'reference_gate_runner.py',
                                           'reference_gate_diagnostic.py',
                                           'statistics.py', 'identity.py', 'common.py')},
            'analysis': {'block_length': result['block_length'], 'nblocks': result['blocks'],
                         'outer_samples': outer_samples, 'inner_samples': inner_samples,
                         'seed': seed, 'nominal_windows': protocol['reference_windows'],
                         'inner_index_sha256': digest(inner_path),
                         'outer_index_sha256': digest(outer_path)},
            'job': {'slurm_job_id': job_id,
                    'scheduler_elapsed_seconds': scheduler_elapsed_seconds},
            'limitations': ['reference proposals are not frozen',
                            'no family-wise calibration',
                            'development sample has already been observed',
                            'not a matched-walltime comparison'],
        }
        receipt_path = output_dir / 'receipt.json'
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True,
                                           allow_nan=False) + '\n', encoding='utf-8')
    except Exception:
        shutil.rmtree(output_dir, ignore_errors=True)
        raise
    return {'output_dir': str(output_dir), 'receipt': receipt,
            'summary_rows': result['summary_rows']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, help='complete committed development transaction')
    parser.add_argument('--output', required=True, help='new no-clobber diagnostic directory')
    parser.add_argument('--protocol', default=str(DEFAULT_PROTOCOL), help='frozen D measurement protocol')
    parser.add_argument('--outer-samples', type=int, default=500)
    parser.add_argument('--inner-samples', type=int, default=500)
    parser.add_argument('--seed', type=int, default=2026112121)
    parser.add_argument('--job-id', help='completed Slurm job ID for traceability')
    parser.add_argument('--scheduler-elapsed-seconds', type=float,
                        help='elapsed time reported by sacct for the completed measurement job')
    args = parser.parse_args(argv)
    if args.outer_samples < 1 or args.inner_samples < 2:
        parser.error('outer-samples must be positive and inner-samples must be at least 2')
    result = run(args.input, args.output, args.protocol,
                 outer_samples=args.outer_samples, inner_samples=args.inner_samples,
                 seed=args.seed, job_id=args.job_id,
                 scheduler_elapsed_seconds=args.scheduler_elapsed_seconds)
    print(json.dumps({'output_dir': result['output_dir'],
                      'status': result['receipt']['status'],
                      'production_score': None,
                      'report': str(Path(result['output_dir']) / 'PAIRED_REPORT.md')},
                     sort_keys=True))


if __name__ == '__main__':
    main()
