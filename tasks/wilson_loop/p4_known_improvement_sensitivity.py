"""Post-hoc outer-bootstrap resolution check on a frozen positive-control run.

Uses the same 402 datasets as the primary control; it is not a new independent
Monte Carlo sample and must never be pooled with the primary event counts.
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

from . import p4_known_improvement as primary
from .statistics import bootstrap_indices, risk


RAW = Path('results/wilson_loop/audit_20261119_p4_known_improvement_v2/raw.json')
MAIN_PROTOCOL = Path('results/wilson_loop/audit_20261119_p4_known_improvement_v2/protocol.json')
DEFAULT_OUT = Path('results/wilson_loop/audit_20261119_p4_known_improvement_sensitivity_v1')
OUTER_DRAWS = 1000
INNER_DRAWS = primary.INNER_DRAWS
SENSITIVITY_SEED = 2026111905


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protocol() -> dict:
    source_paths = [Path(__file__), Path(primary.__file__), Path(primary.base.__file__),
                    Path(primary.base.risk.__code__.co_filename)]
    return {
        'version': 'p4-known-improvement-outer-resolution-posthoc-v1',
        'status_scope': 'post-hoc computational sensitivity; not independent new datasets',
        'primary_raw': str(RAW),
        'primary_raw_sha256': sha256(RAW),
        'primary_protocol_sha256': sha256(MAIN_PROTOCOL),
        'datasets_reused': primary.N_DATASETS,
        'dataset_unit': 'same independent datasets as primary; never add denominators',
        'outer_ratio_draws': OUTER_DRAWS,
        'inner_bootstrap_draws': INNER_DRAWS,
        'inner_seed_rule': 'primary seed + 100000 + dataset_id (held fixed)',
        'outer_seed_rule': 'sensitivity seed + dataset_id',
        'seed': SENSITIVITY_SEED,
        'analysis': (
            'Recompute paired ratio percentile intervals using 1000 outer draws on the exact '
            'same saved block data; gate thresholds, inner draw count and data stay fixed.'
        ),
        'interpretation_rule': (
            'Report detection changes as computational resolution sensitivity. Do not call '
            'the second calculation independent evidence or change the primary result.'
        ),
        'source_sha256': {str(p): sha256(p) for p in source_paths},
    }


def execute(out: Path, frozen: dict) -> dict:
    raw = json.loads(RAW.read_text())
    rows = []
    for item in raw['rows']:
        dataset_id = int(item['dataset'])
        if item['status'] != 'OK':
            rows.append({'dataset': dataset_id, 'status': 'INPUT_FAILURE',
                         'primary_status': item['status'], 'primary_detection': False,
                         'sensitivity_detection': False})
            continue
        b = np.asarray(item['raw_block_loops'], dtype=float)
        n_blocks = b.shape[0]
        inner = bootstrap_indices(n_blocks, INNER_DRAWS,
                                  primary.SEED + 100_000 + dataset_id)
        rng = np.random.default_rng(SENSITIVITY_SEED + dataset_id)
        ratios = np.empty(OUTER_DRAWS, dtype=float)
        for draw in range(OUTER_DRAWS):
            selected = rng.integers(0, n_blocks, n_blocks)
            baseline_risk = risk(b[selected, 0], inner, primary.base.PLAN['windows'],
                                 primary.base.PLAN['t_values'],
                                 [primary.base.PLAN['E0']],
                                 nominal=primary.NOMINAL_WINDOW_INDEX)['risk']
            candidate_risk = risk(b[selected, 1], inner, primary.base.PLAN['windows'],
                                  primary.base.PLAN['t_values'],
                                  [primary.base.PLAN['E0']],
                                  nominal=primary.NOMINAL_WINDOW_INDEX)['risk']
            ratios[draw] = baseline_risk / candidate_risk
        ci = np.quantile(ratios, [0.025, 0.975]).tolist()
        both_pass = all(g['status'] == 'PASS' for g in item['gates'].values())
        detected = both_pass and ci[0] > 1.0
        rows.append({
            'dataset': dataset_id,
            'status': 'OK',
            'primary_detection': bool(item['improvement_detected']),
            'sensitivity_detection': bool(detected),
            'primary_ratio_ci95': item['ratio_ci95'],
            'sensitivity_ratio_ci95': [float(ci[0]), float(ci[1])],
            'both_gates_pass': both_pass,
            'ratio_draws': ratios.tolist(),
        })
        if (dataset_id + 1) % 50 == 0:
            print(f'processed {dataset_id + 1}/{len(raw["rows"])}', flush=True)

    ok = [r for r in rows if r['status'] == 'OK']
    primary_detect = sum(r['primary_detection'] for r in ok)
    sensitivity_detect = sum(r['sensitivity_detection'] for r in ok)
    newly_detected = sum((not r['primary_detection']) and r['sensitivity_detection'] for r in ok)
    lost_detected = sum(r['primary_detection'] and (not r['sensitivity_detection']) for r in ok)
    lower_shift = [r['sensitivity_ratio_ci95'][0] - r['primary_ratio_ci95'][0] for r in ok]
    summary = {
        'status': 'COMPLETED',
        'same_dataset_count': len(ok),
        'input_failures': len(rows) - len(ok),
        'primary_detection': {'k': primary_detect, 'n': len(ok),
                              'rate': primary_detect / len(ok),
                              'cp95': primary.cp95(primary_detect, len(ok))},
        'sensitivity_detection': {'k': sensitivity_detect, 'n': len(ok),
                                  'rate': sensitivity_detect / len(ok),
                                  'cp95': primary.cp95(sensitivity_detect, len(ok))},
        'paired_detection_changes': {
            'newly_detected_with_1000_outer': newly_detected,
            'lost_with_1000_outer': lost_detected,
            'unchanged': len(ok) - newly_detected - lost_detected,
        },
        'lower_bound_shift_median': float(np.median(lower_shift)),
        'lower_bound_shift_q05_q95': np.quantile(lower_shift, [0.05, 0.95]).tolist(),
        'interpretation': 'same-data resampling stability check; no new independent evidence',
    }
    (out / 'sensitivity_raw.json').write_text(json.dumps({
        'protocol_sha256': sha256(out / 'protocol.json'),
        'primary_raw_sha256': frozen['primary_raw_sha256'],
        'rows': rows,
    }, indent=2) + '\n')
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
    both = [r for r in ok if r['both_gates_pass']]
    x = np.array([r['primary_ratio_ci95'][0] for r in both])
    y = np.array([r['sensitivity_ratio_ci95'][0] for r in both])
    axes[0].scatter(x, y, s=13, alpha=.55)
    lim = [min(float(x.min()), float(y.min()), 0.0),
           max(float(x.max()), float(y.max()), 1.0)] if len(x) else [0.0, 1.0]
    axes[0].plot(lim, lim, color='black', linestyle='--', linewidth=1)
    axes[0].axvline(1.0, color='#cc3311', linestyle=':')
    axes[0].axhline(1.0, color='#cc3311', linestyle=':')
    axes[0].set(xlabel='100 outer draws: ratio CI lower bound',
                ylabel='1000 outer draws: ratio CI lower bound',
                title='Same-data lower-bound stability')
    axes[0].grid(alpha=.2)
    values = [summary['primary_detection']['rate'], summary['sensitivity_detection']['rate']]
    intervals = np.array([summary['primary_detection']['cp95'],
                          summary['sensitivity_detection']['cp95']])
    axes[1].errorbar(np.arange(2), values,
                     yerr=np.maximum(0, np.stack([np.asarray(values) - intervals[:, 0],
                                                 intervals[:, 1] - np.asarray(values)])),
                     fmt='o', capsize=4)
    axes[1].set_xticks([0, 1], ['100 outer draws', '1000 outer draws'])
    axes[1].set(ylabel='improvement detections / 402 datasets (CP95)',
                ylim=(0, 1), title='Detection rate, same datasets')
    axes[1].grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(out / 'outer_resolution.png', dpi=160)
    plt.close(fig)

    (out / 'README.md').write_text(f'''# P4 positive-control bootstrap-resolution sensitivity

This is a post-hoc computation on the same {len(ok)} independent datasets in the primary run. It changes only the number of outer ratio resamples from 100 to 1000; the saved block measurements, gate decisions, inner bootstrap count (100), effect size and gate threshold are fixed. The dataset denominator is still {len(ok)} and this run must not be counted as an additional Monte Carlo experiment.

| Calculation | Detections | Rate | CP95 |
|---|---:|---:|---:|
| Primary, 100 outer draws | {primary_detect}/{len(ok)} | {summary['primary_detection']['rate']:.4f} | {summary['primary_detection']['cp95']} |
| Sensitivity, 1000 outer draws | {sensitivity_detect}/{len(ok)} | {summary['sensitivity_detection']['rate']:.4f} | {summary['sensitivity_detection']['cp95']} |

Changing outer-resample resolution newly detected {newly_detected} datasets and lost {lost_detected} prior detections; median shift in the per-dataset lower bound was {summary['lower_bound_shift_median']:.4g} (5th–95th percentile [{summary['lower_bound_shift_q05_q95'][0]:.4g}, {summary['lower_bound_shift_q05_q95'][1]:.4g}]). This isolates only Monte Carlo resolution of the bootstrap quantile. It does not increase the number of independent configurations or repair the 16-block sampling uncertainty.

![Outer-bootstrap resolution sensitivity](outer_resolution.png)

Interpret this only as a stability check of the primary 100-draw calculation. The primary result remains the preregistered endpoint; neither calculation establishes physical performance or calibration for an estimated anchor.
''')
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.prepare == args.execute:
        parser.error('choose exactly one of --prepare or --execute')
    out = args.out
    if args.prepare:
        if not RAW.is_file() or not MAIN_PROTOCOL.is_file():
            parser.error('primary v2 run is not present')
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
        parser.error('input or source hash changed after preparation; use a fresh directory')
    if any((out / n).exists() for n in ('sensitivity_raw.json', 'summary.json', 'README.md', 'outer_resolution.png')):
        parser.error('sensitivity artifacts already exist; use a fresh directory')
    started = datetime.now(timezone.utc).isoformat()
    result = execute(out, frozen)
    (out / 'run_metadata.json').write_text(json.dumps({
        'started_utc': started, 'finished_utc': datetime.now(timezone.utc).isoformat(),
        'python': platform.python_version(), 'platform': platform.platform(), 'status': result['status'],
    }, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
