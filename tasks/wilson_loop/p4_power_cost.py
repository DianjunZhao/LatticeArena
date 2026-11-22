"""Preregistered CPU power-versus-sample-cost scan for the Wilson P4 gate.

This is a synthetic oracle-anchor method study, not a production gauge-field
measurement or a stout/APE comparison.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import beta

from . import p4_controls as base
from .statistics import blocks, bootstrap_indices, risk


DEFAULT_OUT = Path('results/wilson_loop/audit_20261119_p4_power_cost_v1')
N_DATASETS = 402
BASE_SEED = 2026111910
BASELINE_NOISE = 0.005
BLOCK_LENGTH = 5
N_BLOCKS = (16, 32, 64)
CANDIDATE_AMPLITUDE_RATIOS = (0.75, 0.50, 0.35)
INNER_DRAWS = 100
OUTER_DRAWS = 100
NOMINAL_WINDOW_INDEX = 1
TARGET_POWER = 0.90
TARGET_POWER_LOWER_BOUND = 0.85


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_paths() -> list[Path]:
    return [Path(__file__), Path(base.__file__), Path(base.risk.__code__.co_filename)]


def protocol() -> dict:
    cells = [
        {
            'n_blocks': int(n_blocks),
            'block_length': BLOCK_LENGTH,
            'configurations_per_dataset': int(n_blocks * BLOCK_LENGTH),
            'candidate_to_baseline_noise_amplitude': float(amplitude_ratio),
            'input_noise_variance_improvement_factor': float(1 / amplitude_ratio**2),
        }
        for n_blocks in N_BLOCKS
        for amplitude_ratio in CANDIDATE_AMPLITUDE_RATIOS
    ]
    return {
        'version': 'p4-known-improvement-power-cost-v1',
        'scope': 'synthetic_cpu_oracle_anchor_method_diagnostic',
        'physical_status': 'NOT_RUN',
        'seed': BASE_SEED,
        'independent_datasets_per_cell': N_DATASETS,
        'sample_size_rationale': (
            '402 independent datasets per cell follows the prior pointwise CP95 '
            'worst-case half-width target of about 0.05; all failures stay in denominator.'
        ),
        'cells': cells,
        'candidate_noise_amplitude_ratios': list(CANDIDATE_AMPLITUDE_RATIOS),
        'block_length': BLOCK_LENGTH,
        'inner_bootstrap_draws': INNER_DRAWS,
        'outer_ratio_draws': OUTER_DRAWS,
        'bootstrap_choice': (
            'Keep the primary positive-control settings of 100 inner and 100 outer draws '
            'for comparability. The separate 100-vs-1000 sensitivity artifact showed '
            'small net aggregate change but per-dataset flips; this scan therefore reports '
            'pointwise dataset-level power intervals and does not claim quantile exactness.'
        ),
        'target_decision': {
            'primary_effect_amplitude_ratio': 0.50,
            'primary_effect_input_variance_improvement_factor': 4.0,
            'target_detection_rate': TARGET_POWER,
            'minimum_cp95_lower_bound': TARGET_POWER_LOWER_BOUND,
            'selection_rule': (
                'Choose the smallest configuration count among 80, 160, and 320 for '
                'which the primary-effect point detection rate is at least 0.90 and '
                'its pointwise CP95 lower bound is at least 0.85. If none qualifies, '
                'report that no tested budget meets the preregistered target.'
            ),
        },
        'truth': {
            'E0': float(base.PLAN['E0']),
            'signal': 'exp(-E0*t), identical for the paired baseline and candidate',
        },
        'noise': {
            'common_fraction': float(base.PLAN['common_noise_fraction']),
            'baseline_amplitude': BASELINE_NOISE,
            'candidate_amplitude': 'baseline amplitude multiplied by cell ratio',
        },
        'windows': base.PLAN['windows'],
        't_values': base.PLAN['t_values'],
        'nominal_window_index': NOMINAL_WINDOW_INDEX,
        'gate': {
            'spread_limit': float(base.PLAN['spread_limit']),
            'oracle_anchor_z_limit': float(base.PLAN['anchor_z_limit']),
            'improvement_rule': (
                'both baseline and candidate pass the spread and exact synthetic E0 anchor '
                'gates, and paired outer-bootstrap 95% lower risk ratio exceeds one'
            ),
            'risk_definition': 'mean[(SE/E0)^2 + (window_spread/E0)^2] over radii',
        },
        'cost_definition': {
            'primary_proxy': 'paired gauge-configuration count per dataset (80, 160, 320)',
            'scope': 'synthetic generation/analysis work; not production GPU time or walltime extrapolation',
        },
        'intervals': 'pointwise exact two-sided Clopper-Pearson 95%; independent dataset is unit',
        'failure_policy': 'retain failed dataset as non-detection in the planned denominator',
        'seed_rules': {
            'data': 'base seed + 100000 * cell index + dataset index',
            'inner_bootstrap': 'base seed + 10000000 + 100000 * cell index + dataset index',
            'outer_ratio': 'base seed + 20000000 + 100000 * cell index + dataset index',
        },
        'source_sha256': {str(path): sha256(path) for path in source_paths()},
    }


def cp95(k: int, n: int) -> list[float]:
    return [
        float(beta.ppf(0.025, k, n - k + 1)) if k else 0.0,
        float(beta.ppf(0.975, k + 1, n - k)) if k < n else 1.0,
    ]


def run_dataset(
    dataset_id: int,
    data_rng: np.random.Generator,
    *,
    cell_index: int,
    n_blocks: int,
    amplitude_ratio: float,
    seed: int,
) -> dict:
    t_values = np.asarray(base.PLAN['t_values'], dtype=float)
    truth_e0 = float(base.PLAN['E0'])
    n_configurations = n_blocks * BLOCK_LENGTH
    signal = np.exp(-truth_e0 * t_values)
    common = data_rng.normal(size=(n_configurations, 1, len(t_values)))
    common_fraction = float(base.PLAN['common_noise_fraction'])
    channels = []
    for amplitude in (BASELINE_NOISE, BASELINE_NOISE * amplitude_ratio):
        independent = data_rng.normal(size=common.shape)
        standardized_noise = (
            np.sqrt(common_fraction) * common
            + np.sqrt(1.0 - common_fraction) * independent
        )
        channels.append(signal[None, None, :] * (1.0 + amplitude * standardized_noise))
    block_values = np.stack(
        [blocks(values, BLOCK_LENGTH) for values in channels], axis=1
    )
    if block_values.shape[0] != n_blocks:
        raise RuntimeError('configuration count did not produce the preregistered block count')

    inner_seed = BASE_SEED + 10_000_000 + 100_000 * cell_index + dataset_id
    inner = bootstrap_indices(n_blocks, INNER_DRAWS, inner_seed)
    windows = base.PLAN['windows']
    nominal = NOMINAL_WINDOW_INDEX
    estimates = [
        risk(block_values[:, channel], inner, windows, t_values, [truth_e0], nominal=nominal)
        for channel in range(2)
    ]
    gates = {}
    for label, result in zip(('baseline', 'candidate'), estimates):
        value = float(result['v'][0])
        se = float(result['se'][0])
        spread = float(result['spread'][0])
        anchor_z = abs(value - truth_e0) / se if se > 0 else float('inf')
        relative_spread = spread / abs(value) if value else float('inf')
        passes_spread = relative_spread <= float(base.PLAN['spread_limit'])
        passes_anchor = anchor_z <= float(base.PLAN['anchor_z_limit'])
        gates[label] = {
            'status': 'PASS' if passes_spread and passes_anchor else 'ABSTAIN',
            'spread_gate': bool(passes_spread),
            'anchor_gate': bool(passes_anchor),
            'relative_window_spread': relative_spread,
            'oracle_anchor_z': anchor_z,
            'value': value,
            'se': se,
            'window_spread': spread,
            'risk': float(result['risk']),
        }

    outer_seed = BASE_SEED + 20_000_000 + 100_000 * cell_index + dataset_id
    outer_rng = np.random.default_rng(outer_seed)
    ratios = []
    for _ in range(OUTER_DRAWS):
        selected = outer_rng.integers(0, n_blocks, n_blocks)
        baseline_risk = risk(
            block_values[selected, 0], inner, windows, t_values,
            [truth_e0], nominal=nominal,
        )['risk']
        candidate_risk = risk(
            block_values[selected, 1], inner, windows, t_values,
            [truth_e0], nominal=nominal,
        )['risk']
        if candidate_risk <= 0 or not np.isfinite(candidate_risk):
            raise ValueError(f'invalid candidate risk {candidate_risk!r}')
        ratios.append(float(baseline_risk / candidate_risk))
    ratio_ci = np.quantile(ratios, [0.025, 0.975]).tolist()
    detected = all(gate['status'] == 'PASS' for gate in gates.values()) and ratio_ci[0] > 1.0
    return {
        'dataset': dataset_id,
        'seed': int(seed),
        'status': 'OK',
        'n_blocks': int(n_blocks),
        'block_length': BLOCK_LENGTH,
        'configurations_per_dataset': int(n_configurations),
        'candidate_to_baseline_noise_amplitude': float(amplitude_ratio),
        'input_noise_variance_improvement_factor': float(1 / amplitude_ratio**2),
        'gates': gates,
        'ratio_point': float(estimates[0]['risk'] / estimates[1]['risk']),
        'ratio_ci95': [float(ratio_ci[0]), float(ratio_ci[1])],
        'ratio_outer_draws': [float(value) for value in ratios],
        'improvement_detected': bool(detected),
    }


def summarize_cell(rows: list[dict]) -> dict:
    n = len(rows)
    ok_rows = [row for row in rows if row.get('status') == 'OK']
    events = {
        'baseline_pass': sum(row['gates']['baseline']['status'] == 'PASS' for row in ok_rows),
        'candidate_pass': sum(row['gates']['candidate']['status'] == 'PASS' for row in ok_rows),
        'both_pass': sum(all(gate['status'] == 'PASS' for gate in row['gates'].values()) for row in ok_rows),
        'improvement_detected': sum(row['improvement_detected'] for row in ok_rows),
        'any_abstain': sum(any(gate['status'] != 'PASS' for gate in row['gates'].values()) for row in ok_rows),
        'failure': n - len(ok_rows),
    }
    summary = {
        name: {'k': int(k), 'n': n, 'rate': float(k / n), 'cp95': cp95(int(k), n)}
        for name, k in events.items()
    }
    return {'events': summary, 'successful_datasets': len(ok_rows)}


def execute(out: Path, frozen: dict) -> dict:
    cell_summaries = []
    started = time.perf_counter()
    wall_started = datetime.now(timezone.utc).isoformat()
    cells = frozen['cells']
    protocol_hash = sha256(out / 'protocol.json')
    checkpoint_path = out / 'checkpoint.json'

    def checkpoint(status: str, completed_rows: int, last_cell: int | None) -> None:
        payload = {
            'status': status,
            'protocol_sha256': protocol_hash,
            'completed_cells': len(cell_summaries),
            'planned_cells': len(cells),
            'completed_datasets': completed_rows,
            'planned_datasets': len(cells) * N_DATASETS,
            'last_cell_index': last_cell,
            'updated_utc': datetime.now(timezone.utc).isoformat(),
        }
        temporary = checkpoint_path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(payload, indent=2) + '\n')
        os.replace(temporary, checkpoint_path)

    completed_total = sum(
        sum(1 for _ in path.open('r', encoding='utf-8'))
        for path in out.glob('cell_*_rows.jsonl')
    )
    checkpoint('RUNNING', completed_total, None)
    for cell_index, cell in enumerate(cells):
        cell_started = time.perf_counter()
        n_blocks = int(cell['n_blocks'])
        amplitude_ratio = float(cell['candidate_to_baseline_noise_amplitude'])
        rows_path = out / f'cell_{cell_index:02d}_rows.jsonl'
        summary_path = out / f'cell_{cell_index:02d}_summary.json'
        if summary_path.exists():
            saved_summary = json.loads(summary_path.read_text())
            if (
                saved_summary.get('protocol_sha256') != protocol_hash
                or saved_summary.get('cell_index') != cell_index
            ):
                raise RuntimeError(f'{summary_path} does not match the frozen protocol')
            saved_rows = list(rows_path.open('r', encoding='utf-8')) if rows_path.exists() else []
            if len(saved_rows) != N_DATASETS:
                raise RuntimeError(f'{summary_path} exists but its raw dataset rows are incomplete')
            cell_summaries.append(saved_summary['summary'])
            print(json.dumps({
                'resume_cell': cell_index,
                'status': 'already_complete',
                'datasets': len(saved_rows),
            }, sort_keys=True), flush=True)
            checkpoint('RUNNING', completed_total, cell_index)
            continue
        rows_by_id: dict[int, dict] = {}
        if rows_path.exists():
            with rows_path.open('r', encoding='utf-8') as handle:
                for line_number, line in enumerate(handle, start=1):
                    try:
                        saved = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise RuntimeError(
                            f'{rows_path} has invalid JSON at line {line_number}; preserve and inspect before resuming'
                        ) from exc
                    dataset_id = int(saved['dataset'])
                    expected_seed = BASE_SEED + 100_000 * cell_index + dataset_id
                    if (
                        saved.get('cell_index') != cell_index
                        or saved.get('seed') != expected_seed
                        or saved.get('n_blocks') != n_blocks
                        or saved.get('candidate_to_baseline_noise_amplitude') != amplitude_ratio
                    ):
                        raise RuntimeError(f'{rows_path} contains a row inconsistent with the frozen cell')
                    if dataset_id in rows_by_id or not 0 <= dataset_id < N_DATASETS:
                        raise RuntimeError(f'{rows_path} has duplicate or out-of-range dataset ID {dataset_id}')
                    rows_by_id[dataset_id] = saved
        if rows_by_id:
            print(json.dumps({
                'resume_cell': cell_index,
                'saved_datasets': len(rows_by_id),
                'planned_datasets': N_DATASETS,
            }, sort_keys=True), flush=True)
        with rows_path.open('a', encoding='utf-8') as row_file:
            for dataset_id in range(N_DATASETS):
                if dataset_id in rows_by_id:
                    continue
                seed = BASE_SEED + 100_000 * cell_index + dataset_id
                data_rng = np.random.default_rng(seed)
                try:
                    row = run_dataset(
                        dataset_id,
                        data_rng,
                        cell_index=cell_index,
                        n_blocks=n_blocks,
                        amplitude_ratio=amplitude_ratio,
                        seed=seed,
                    )
                except Exception as exc:
                    row = {
                        'dataset': dataset_id,
                        'seed': int(seed),
                        'status': 'FAIL',
                        'failure': f'{type(exc).__name__}: {exc}',
                        'improvement_detected': False,
                        'n_blocks': n_blocks,
                        'block_length': BLOCK_LENGTH,
                        'configurations_per_dataset': n_blocks * BLOCK_LENGTH,
                        'candidate_to_baseline_noise_amplitude': amplitude_ratio,
                        'input_noise_variance_improvement_factor': 1 / amplitude_ratio**2,
                    }
                row['cell_index'] = cell_index
                row_file.write(json.dumps(row, separators=(',', ':')) + '\n')
                row_file.flush()
                rows_by_id[dataset_id] = row
                completed_total += 1
                if completed_total % 25 == 0:
                    checkpoint('RUNNING', completed_total, cell_index)
        rows = [rows_by_id[i] for i in range(N_DATASETS)]
        for dataset_id in range(N_DATASETS):
            if rows[dataset_id]['dataset'] != dataset_id:
                raise RuntimeError('resumed dataset rows are not in the planned order')
        elapsed = time.perf_counter() - cell_started
        summary = summarize_cell(rows)
        summary.update({
            'n_blocks': n_blocks,
            'block_length': BLOCK_LENGTH,
            'configurations_per_dataset': n_blocks * BLOCK_LENGTH,
            'candidate_to_baseline_noise_amplitude': amplitude_ratio,
            'input_noise_variance_improvement_factor': 1 / amplitude_ratio**2,
            'cell_wall_seconds': elapsed,
            'seconds_per_dataset': elapsed / N_DATASETS,
        })
        cell_summaries.append(summary)
        summary_document = {
            'protocol_sha256': protocol_hash,
            'cell_index': cell_index,
            'summary': summary,
        }
        summary_temporary = summary_path.with_suffix('.json.tmp')
        summary_temporary.write_text(json.dumps(summary_document, indent=2) + '\n')
        os.replace(summary_temporary, summary_path)
        checkpoint('RUNNING', completed_total, cell_index)
        print(json.dumps({
            'completed_cells': len(cell_summaries),
            'total_cells': len(cells),
            'n_blocks': n_blocks,
            'amplitude_ratio': amplitude_ratio,
            'detections': summary['events']['improvement_detected']['k'],
            'n': N_DATASETS,
            'cell_seconds': round(elapsed, 2),
        }, sort_keys=True), flush=True)

    run_status = 'COMPLETED' if all(cell['events']['failure']['k'] == 0 for cell in cell_summaries) else 'COMPLETED_WITH_FAILURES'
    selected = None
    primary_cells = sorted(
        (cell for cell in cell_summaries if cell['candidate_to_baseline_noise_amplitude'] == 0.5),
        key=lambda cell: cell['configurations_per_dataset'],
    )
    for cell in primary_cells:
        event = cell['events']['improvement_detected']
        if event['rate'] >= TARGET_POWER and event['cp95'][0] >= TARGET_POWER_LOWER_BOUND:
            selected = cell
            break
    aggregate = {
        'status': run_status,
        'cells': cell_summaries,
        'primary_effect_selected_budget': None if selected is None else {
            key: selected[key] for key in (
                'n_blocks', 'block_length', 'configurations_per_dataset',
                'candidate_to_baseline_noise_amplitude', 'input_noise_variance_improvement_factor',
            )
        },
        'power_target_met': selected is not None,
        'total_wall_seconds': time.perf_counter() - started,
        'wall_started_utc': wall_started,
        'wall_finished_utc': datetime.now(timezone.utc).isoformat(),
        'python': platform.python_version(),
        'platform': platform.platform(),
        'physical_status': 'NOT_RUN',
    }
    all_rows = []
    for cell_index in range(len(cells)):
        rows_path = out / f'cell_{cell_index:02d}_rows.jsonl'
        with rows_path.open('r', encoding='utf-8') as handle:
            all_rows.extend(json.loads(line) for line in handle)
    raw = {
        'scope': 'synthetic_cpu_oracle_anchor_method_diagnostic',
        'status': run_status,
        'protocol_sha256': sha256(out / 'protocol.json'),
        'cells': cell_summaries,
        'rows': all_rows,
        'physical_status': 'NOT_RUN',
    }
    (out / 'raw.json').write_text(json.dumps(raw, indent=2) + '\n')
    (out / 'summary.json').write_text(json.dumps(aggregate, indent=2) + '\n')
    write_figure(out, cell_summaries)
    (out / 'README.md').write_text(render_readme(aggregate))
    checkpoint('COMPLETED' if run_status == 'COMPLETED' else 'COMPLETED_WITH_FAILURES',
               len(all_rows), len(cells) - 1)
    return aggregate


def write_figure(out: Path, cells: list[dict]) -> None:
    colors = {0.75: '#4477aa', 0.5: '#228833', 0.35: '#cc6677'}
    fig, ax = plt.subplots(figsize=(8, 5.2))
    for amplitude_ratio in CANDIDATE_AMPLITUDE_RATIOS:
        group = sorted(
            (cell for cell in cells if cell['candidate_to_baseline_noise_amplitude'] == amplitude_ratio),
            key=lambda cell: cell['configurations_per_dataset'],
        )
        x = np.asarray([cell['configurations_per_dataset'] for cell in group], dtype=float)
        event = [cell['events']['improvement_detected'] for cell in group]
        y = np.asarray([value['rate'] for value in event])
        ci = np.asarray([value['cp95'] for value in event])
        ax.errorbar(
            x, y,
            yerr=np.vstack((y - ci[:, 0], ci[:, 1] - y)),
            marker='o', capsize=3, linewidth=1.8,
            color=colors[amplitude_ratio],
            label=(
                f'amplitude ratio={amplitude_ratio:g} '
                f'(variance reduction={1 / amplitude_ratio**2:.2g}x)'
            ),
        )
    ax.axhline(TARGET_POWER, color='black', linestyle='--', linewidth=1, label='target detection rate 0.90')
    ax.set(
        xlabel='paired configurations per dataset (block length fixed at 5)',
        ylabel='dataset-level improvement detection rate (pointwise CP95)',
        ylim=(-0.03, 1.03),
        title='Synthetic P4 power versus sample-cost proxy',
    )
    ax.grid(alpha=0.22)
    ax.legend(fontsize=8, loc='lower right')
    fig.tight_layout()
    fig.savefig(out / 'power_vs_configurations.png', dpi=170)
    plt.close(fig)


def render_readme(aggregate: dict) -> str:
    rows = []
    for cell in aggregate['cells']:
        event = cell['events']['improvement_detected']
        both = cell['events']['both_pass']
        abstain = cell['events']['any_abstain']
        failure = cell['events']['failure']
        rows.append(
            '| {n_blocks} | {block_length} | {configurations_per_dataset} | {ratio:.2f} | '
            '{factor:.2f}x | {detected}/{n} ({rate:.3f}) | [{lo:.3f}, {hi:.3f}] | '
            '{both}/{n} | {abstain}/{n} | {failure}/{n} | {seconds:.1f} |'.format(
                n_blocks=cell['n_blocks'], block_length=cell['block_length'],
                configurations_per_dataset=cell['configurations_per_dataset'],
                ratio=cell['candidate_to_baseline_noise_amplitude'],
                factor=cell['input_noise_variance_improvement_factor'],
                detected=event['k'], n=event['n'], rate=event['rate'],
                lo=event['cp95'][0], hi=event['cp95'][1],
                both=both['k'], abstain=abstain['k'], failure=failure['k'],
                seconds=cell['cell_wall_seconds'],
            )
        )
    selected = aggregate['primary_effect_selected_budget']
    if selected:
        decision = (
            'For the primary fourfold input-variance-reduction effect, the smallest tested '
            f'budget meeting the preregistered rule is {selected["configurations_per_dataset"]} '
            f'paired configurations per dataset ({selected["n_blocks"]} blocks of length '
            f'{selected["block_length"]}).'
        )
    else:
        decision = (
            'No tested budget met the preregistered primary-effect rule: detection rate at '
            'least 0.90 with pointwise CP95 lower bound at least 0.85. The next budget or '
            'effect change must be separately preregistered.'
        )
    return f'''# Wilson P4 power-versus-cost scan (CPU synthetic control)

Status: **{aggregate['status']}**. The preregistration and source hashes are in `protocol.json`; per-dataset gate outcomes, ratio intervals, seeds and failures are in `raw.json`; exact cell summaries are in `summary.json`.

This is a new synthetic oracle-anchor method study, independent of the primary positive-control datasets. It scans 16, 32 and 64 blocks at fixed block length 5 (80, 160 and 320 paired configurations per dataset) and candidate noise-amplitude ratios 0.75, 0.50 and 0.35. Those correspond to input-noise variance reductions of about 1.78x, 4x and 8.16x. Each of the nine cells has 402 independent datasets. The target rule, generator seeds, bootstrap counts and source hashes were frozen before simulation.

The primary planning question is whether the known 4x input-variance reduction reaches a dataset-level detection rate of at least 90%, with a pointwise Clopper-Pearson 95% lower bound of at least 85%, at the smallest tested configuration budget. **{decision}**

| Blocks | Block length | Configurations / dataset | Candidate amplitude ratio | Input variance reduction | Detected | CP95 | Both gates pass | Any gate abstains | Failures | Cell seconds |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

![Detection rate versus paired configuration budget](power_vs_configurations.png)

Cost is reported both as paired configurations per dataset (the planned sample-cost proxy) and measured local CPU walltime per cell. The plot shows how detection rate and pointwise dataset-level intervals vary with budget and effect size. All CI bands are per-cell; there is no family-wise guarantee across the nine comparisons. Failures remain in their planned denominator.

Limits: the signal is exactly single-state and the $E_0$ anchor is known by construction. This does not model estimated-anchor uncertainty, autocorrelation beyond the fixed block model, common physical bias, real gauge fields, stout/APE kernels, HMC, or GPU runtime. It supports only a synthetic planning statement about this gate and this generator; `physical_status` remains `NOT_RUN`.
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--prepare', action='store_true', help='write and freeze the protocol only')
    parser.add_argument('--execute', action='store_true', help='run or resume a previously prepared protocol')
    args = parser.parse_args()
    out = args.out
    if args.prepare == args.execute:
        parser.error('choose exactly one of --prepare or --execute')
    if args.prepare:
        out.mkdir(parents=True, exist_ok=False)
        frozen = protocol()
        (out / 'protocol.json').write_text(json.dumps(frozen, indent=2) + '\n')
        print(json.dumps({'prepared': str(out), 'protocol_sha256': sha256(out / 'protocol.json')}, indent=2))
        return
    plan_path = out / 'protocol.json'
    if not plan_path.is_file():
        parser.error(f'missing frozen protocol: {plan_path}; prepare first')
    frozen = json.loads(plan_path.read_text())
    if frozen != protocol():
        parser.error('protocol or source hashes changed after preparation; use a new run directory')
    if any((out / name).exists() for name in ('raw.json', 'summary.json', 'README.md', 'power_vs_configurations.png')):
        parser.error('output already contains execution artifacts; use a fresh run directory')
    result = execute(out, frozen)
    print(json.dumps({'status': result['status'], 'power_target_met': result['power_target_met'],
                      'primary_effect_selected_budget': result['primary_effect_selected_budget'],
                      'total_wall_seconds': result['total_wall_seconds']}, indent=2))


if __name__ == '__main__':
    main()
