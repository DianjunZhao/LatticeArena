"""Independent positive-control calibration for the synthetic Wilson-loop gate.

The candidate has half the multiplicative-noise amplitude of the baseline,
while both estimate the same known single-state potential E0. This is a
synthetic diagnostic, not a stout/APE or production-measurement result.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import beta

from . import p4_controls as base
from .statistics import bootstrap_indices, blocks, risk


DEFAULT_OUT = Path('results/wilson_loop/audit_20261119_p4_known_improvement_v2')
N_DATASETS = 402
SEED = 2026111904
BASELINE_NOISE = 0.005
CANDIDATE_NOISE = 0.0025
OUTER_DRAWS = 100
INNER_DRAWS = 100
DESCRIPTIVE_DATASET_BOOTSTRAP_DRAWS = 5000
NOMINAL_WINDOW_INDEX = 1


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protocol() -> dict:
    source_files = [Path(__file__), Path(base.__file__), Path(base.risk.__code__.co_filename)]
    return {
        'version': 'p4-known-improvement-positive-control-v2',
        'synthetic_only': True,
        'physical_status': 'NOT_RUN',
        'seed': SEED,
        'independent_datasets': N_DATASETS,
        'sample_size_rationale': (
            '402 matches the prior worst-case Bernoulli design for pointwise CP95 '
            'half-width about 0.05; no optional stopping or sample-size tuning.'
        ),
        'configurations_per_dataset': 80,
        'block_length': 5,
        'outer_ratio_draws': OUTER_DRAWS,
        'inner_bootstrap_draws': INNER_DRAWS,
        'descriptive_dataset_bootstrap_draws': DESCRIPTIVE_DATASET_BOOTSTRAP_DRAWS,
        'seed_rules': {
            'data_stream': 'one NumPy Generator seeded by protocol seed, consumed in dataset order',
            'inner_bootstrap': 'seed + 100000 + dataset_id',
            'outer_ratio': 'seed + 200000 + dataset_id',
            'dataset_summary_bootstrap': 'seed + 300000',
        },
        't_values': base.PLAN['t_values'],
        'windows': base.PLAN['windows'],
        'nominal_window_index': NOMINAL_WINDOW_INDEX,
        'truth': {
            'E0': base.PLAN['E0'],
            'signal': 'exp(-E0*t), identical for baseline and candidate',
        },
        'noise': {
            'common_fraction': base.PLAN['common_noise_fraction'],
            'baseline_amplitude': BASELINE_NOISE,
            'candidate_amplitude': CANDIDATE_NOISE,
            'candidate_to_baseline_amplitude': CANDIDATE_NOISE / BASELINE_NOISE,
            'input_noise_variance_improvement_factor': (BASELINE_NOISE / CANDIDATE_NOISE) ** 2,
            'interpretation': (
                'The input-noise variance ratio is exactly four by construction. '
                'The induced risk ratio is only approximately four in the small-noise limit; '
                'the gate outcome, not that approximation, is the primary endpoint.'
            ),
        },
        'gate': {
            'legacy_spread_limit': base.PLAN['spread_limit'],
            'oracle_anchor_z_limit': base.PLAN['anchor_z_limit'],
            'pass_rule': 'both legacy spread ratio <= limit and abs(v-E0)/SE <= z limit',
            'improvement_rule': (
                'both baseline and candidate gates PASS and the paired outer-bootstrap '
                '95% lower bound of risk(baseline)/risk(candidate) is greater than 1'
            ),
            'risk_definition': 'mean[(SE/E0)^2 + (window_spread/E0)^2] over radii',
        },
        'reported_events': [
            'baseline_pass', 'candidate_pass', 'both_pass', 'improvement_detected',
            'missed_known_improvement', 'ratio_interval_reversed', 'any_failure',
        ],
        'intervals': 'pointwise exact two-sided Clopper-Pearson 95% per event; dataset is unit',
        'exception_policy': 'retain a failed dataset row and continue; never drop failures from denominator',
        'source_sha256': {str(p): sha256(p) for p in source_files},
    }


def cp95(k: int, n: int) -> list[float]:
    return [
        float(beta.ppf(0.025, k, n - k + 1)) if k else 0.0,
        float(beta.ppf(0.975, k + 1, n - k)) if k < n else 1.0,
    ]


def summarize_row(row: dict) -> dict[str, bool]:
    if row['status'] != 'OK':
        return {
            'baseline_pass': False,
            'candidate_pass': False,
            'both_pass': False,
            'improvement_detected': False,
            'missed_known_improvement': True,
            'ratio_interval_reversed': False,
            'any_failure': True,
        }
    lower, upper = row['ratio_ci95']
    return {
        'baseline_pass': row['gates']['baseline']['status'] == 'PASS',
        'candidate_pass': row['gates']['candidate']['status'] == 'PASS',
        'both_pass': all(g['status'] == 'PASS' for g in row['gates'].values()),
        'improvement_detected': row['improvement_detected'],
        'missed_known_improvement': not row['improvement_detected'],
        'ratio_interval_reversed': upper < 1.0,
        'any_failure': False,
    }


def run_dataset(dataset_id: int, rng: np.random.Generator) -> dict:
    t_values = np.asarray(base.PLAN['t_values'], dtype=float)
    truth_e0 = float(base.PLAN['E0'])
    signal = np.exp(-truth_e0 * t_values)
    common = rng.normal(size=(base.PLAN['configurations'], 1, len(t_values)))
    fraction = float(base.PLAN['common_noise_fraction'])
    channels = []
    for amplitude in (BASELINE_NOISE, CANDIDATE_NOISE):
        independent = rng.normal(size=common.shape)
        standardized_noise = np.sqrt(fraction) * common + np.sqrt(1.0 - fraction) * independent
        channels.append(signal[None, None, :] * (1.0 + amplitude * standardized_noise))
    block_values = np.stack([blocks(x, base.PLAN['block_length']) for x in channels], axis=1)
    n_blocks = block_values.shape[0]
    inner = bootstrap_indices(n_blocks, INNER_DRAWS, SEED + 100_000 + dataset_id)
    windows = base.PLAN['windows']
    nominal = NOMINAL_WINDOW_INDEX

    point = [risk(block_values[:, k], inner, windows, t_values, [truth_e0], nominal=nominal)
             for k in range(2)]
    gates = {}
    for label, result in zip(('baseline', 'candidate'), point):
        value = float(result['v'][0])
        se = float(result['se'][0])
        spread = float(result['spread'][0])
        z = abs(value - truth_e0) / se if se > 0 else float('inf')
        relative_spread = spread / abs(value) if value else float('inf')
        passes_spread = relative_spread <= float(base.PLAN['spread_limit'])
        passes_anchor = z <= float(base.PLAN['anchor_z_limit'])
        gates[label] = {
            'status': 'PASS' if passes_spread and passes_anchor else 'ABSTAIN',
            'legacy_spread_gate': passes_spread,
            'relative_window_spread': relative_spread,
            'oracle_anchor_z': z,
            'value': value,
            'se': se,
            'window_spread': spread,
            'risk': float(result['risk']),
        }

    outer_rng = np.random.default_rng(SEED + 200_000 + dataset_id)
    ratios = []
    for _ in range(OUTER_DRAWS):
        selected = outer_rng.integers(0, n_blocks, n_blocks)
        baseline_risk = risk(block_values[selected, 0], inner, windows, t_values,
                             [truth_e0], nominal=nominal)['risk']
        candidate_risk = risk(block_values[selected, 1], inner, windows, t_values,
                              [truth_e0], nominal=nominal)['risk']
        if candidate_risk <= 0 or not np.isfinite(candidate_risk):
            raise ValueError(f'invalid candidate risk {candidate_risk!r}')
        ratios.append(float(baseline_risk / candidate_risk))
    ratio_ci = np.quantile(ratios, [0.025, 0.975]).tolist()
    detected = (all(g['status'] == 'PASS' for g in gates.values()) and ratio_ci[0] > 1.0)
    return {
        'dataset': dataset_id,
        'status': 'OK',
        'gates': gates,
        'ratio_point': float(point[0]['risk'] / point[1]['risk']),
        'ratio_ci95': [float(ratio_ci[0]), float(ratio_ci[1])],
        'ratio_outer_draws': ratios,
        'improvement_detected': bool(detected),
        'raw_block_loops': block_values.tolist(),
    }


def execute(out: Path, frozen: dict) -> dict:
    rng = np.random.default_rng(SEED)
    rows = []
    for dataset_id in range(N_DATASETS):
        try:
            rows.append(run_dataset(dataset_id, rng))
        except Exception as exc:  # retain every planned dataset in the denominator
            rows.append({'dataset': dataset_id, 'status': 'FAIL',
                         'failure': f'{type(exc).__name__}: {exc}'})
    events = list(frozen['reported_events'])
    summary = {}
    for event in events:
        k = sum(summarize_row(row)[event] for row in rows)
        summary[event] = {'k': int(k), 'n': len(rows), 'rate': float(k / len(rows)),
                          'cp95': cp95(k, len(rows))}

    ok_rows = [row for row in rows if row['status'] == 'OK']
    ratios = np.asarray([row['ratio_point'] for row in ok_rows], dtype=float)
    dataset_rng = np.random.default_rng(SEED + 300_000)
    boot_medians = np.empty(DESCRIPTIVE_DATASET_BOOTSTRAP_DRAWS, dtype=float)
    for i in range(len(boot_medians)):
        sample = dataset_rng.choice(ratios, size=len(ratios), replace=True)
        boot_medians[i] = np.median(sample)
    aggregate = {
        'successful_datasets': len(ok_rows),
        'mean_point_risk_ratio': float(np.mean(ratios)) if len(ratios) else None,
        'median_point_risk_ratio': float(np.median(ratios)) if len(ratios) else None,
        'median_dataset_bootstrap_ci95': np.quantile(boot_medians, [0.025, 0.975]).tolist()
        if len(ratios) else None,
        'note': 'Descriptive dataset-level ratio summary; gate detection rate is the primary endpoint.',
    }

    run_status = 'COMPLETED' if summary['any_failure']['k'] == 0 else 'COMPLETED_WITH_FAILURES'
    raw = {'scope': 'synthetic_positive_control', 'run_status': run_status,
           'physical_status': 'NOT_RUN',
           'protocol_sha256': sha256(out / 'protocol.json'), 'rows': rows}
    (out / 'raw.json').write_text(json.dumps(raw, indent=2) + '\n')
    (out / 'summary.json').write_text(json.dumps({'status': run_status, 'events': summary,
                                                   'aggregate': aggregate}, indent=2) + '\n')

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    if len(ratios):
        positive = ratios[ratios > 0]
        axes[0].hist(np.log10(positive), bins=30, color='#4477aa', alpha=.85)
        axes[0].axvline(0, color='black', linestyle='--', label='no improvement: ratio=1')
        axes[0].set(xlabel='log10 point risk ratio: baseline / candidate',
                    ylabel='independent datasets', title='Known positive-control effect')
        axes[0].legend()
    names = ['baseline pass', 'candidate pass', 'both pass', 'improvement detected',
             'missed improvement', 'failure']
    keys = ['baseline_pass', 'candidate_pass', 'both_pass', 'improvement_detected',
            'missed_known_improvement', 'any_failure']
    rates = np.array([summary[k]['rate'] for k in keys])
    ci = np.array([summary[k]['cp95'] for k in keys])
    axes[1].errorbar(np.arange(len(keys)), rates,
                     yerr=np.maximum(0, np.stack([rates - ci[:, 0], ci[:, 1] - rates])),
                     fmt='o', capsize=3, color='#228833')
    axes[1].set_xticks(np.arange(len(keys)), names, rotation=45, ha='right')
    axes[1].set(ylabel='dataset-level event rate (CP95)', ylim=(-.03, 1.03),
                title='Gate and detection outcomes')
    axes[1].grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(out / 'known_improvement.png', dpi=160)
    plt.close(fig)

    table = '\n'.join(
        f"| {name} | {summary[key]['k']}/{summary[key]['n']} | "
        f"{summary[key]['rate']:.4f} | [{summary[key]['cp95'][0]:.4f}, {summary[key]['cp95'][1]:.4f}] |"
        for name, key in zip(names, keys)
    )
    if len(ratios):
        median_text = (
            f"{aggregate['median_point_risk_ratio']:.4g} (dataset-bootstrap 95% interval "
            f"[{aggregate['median_dataset_bootstrap_ci95'][0]:.4g}, "
            f"{aggregate['median_dataset_bootstrap_ci95'][1]:.4g}])"
        )
    else:
        median_text = 'unavailable because no dataset completed the risk calculation'
    text = f'''# Wilson P4 known-improvement positive control

Run status: **{run_status}**. Failed datasets remain in the planned denominator and in `raw.json`.

This is a new CPU-only synthetic control, separate from the frozen null/common-bias runs. The protocol was written before any dataset was generated; seed `{SEED}`, {N_DATASETS} independent paired datasets, 80 configurations and 16 blocks per dataset. Both labels share the same ground-state signal $W(T)=e^{{-E_0T}}$ with $E_0=0.5$ and 80% common noise, while the candidate's multiplicative-noise amplitude is half the baseline's. Thus the input noise variance ratio is exactly four; because the reported risk contains log-potential and window-spread terms, its expected risk ratio is only approximately four in the small-noise limit.

The primary success event is frozen in `protocol.json`: both labels pass the legacy spread and exact synthetic-anchor diagnostic, and the paired outer-bootstrap 95% lower bound of risk(baseline)/risk(candidate) is greater than one. One independent dataset, not its bootstrap draws, is the statistical unit. Event intervals are pointwise exact Clopper-Pearson 95% intervals; no family-wise statement is made. Failures remain in the denominator.

| Event | Count | Rate | CP95 |
|---|---:|---:|---:|
{table}

Descriptive median point risk ratio across successful datasets: {median_text}; this is secondary to the detection-rate endpoint.

![Known-improvement control diagnostic](known_improvement.png)

This tests whether the current synthetic gate can detect a clear variance reduction when its exact anchor is available. It does not establish calibration for a noisy or estimated production anchor, does not cover common model bias, and does not measure stout/APE or physical Wilson loops. `physical_status` remains `NOT_RUN`.
'''
    (out / 'README.md').write_text(text)
    return {'status': run_status, 'events': summary, 'aggregate': aggregate}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--prepare', action='store_true', help='write and freeze the protocol only')
    parser.add_argument('--execute', action='store_true', help='run a previously prepared protocol')
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
    current = protocol()
    if frozen != current:
        parser.error('protocol or source hashes changed after preparation; use a new run directory')
    if any((out / name).exists() for name in ('raw.json', 'summary.json', 'README.md', 'known_improvement.png')):
        parser.error('output already contains execution artifacts; use a fresh directory')
    started = datetime.now(timezone.utc).isoformat()
    result = execute(out, frozen)
    (out / 'run_metadata.json').write_text(json.dumps({
        'started_utc': started,
        'finished_utc': datetime.now(timezone.utc).isoformat(),
        'python': platform.python_version(),
        'platform': platform.platform(),
        'status': result['status'],
    }, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
