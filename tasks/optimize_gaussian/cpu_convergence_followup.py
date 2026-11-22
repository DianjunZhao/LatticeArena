"""Independent N=100 CPU follow-up for the synthetic C optimizer diagnostic."""
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

from . import cpu_convergence_diagnostic as diagnostic
from . import p3_crosslink_fair as fair


DEFAULT_OUT = Path('results/optimize_gaussian/cpu_close_20261119_C_followup_n100_v2')
SEEDS = tuple(range(1100, 1200))
EPSILONS = (0.0, 0.1)
BUDGETS = (25, 100, 400)
N_STARTS = 3
DATASET_BOOTSTRAP_DRAWS = 4000
BOOTSTRAP_SEED = 2026113110


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protocol() -> dict:
    paths = [Path(__file__), Path(diagnostic.__file__), Path(fair.__file__)]
    return {
        'version': 'optgauss-cpu-C-independent-followup-n100-v2',
        'scope': 'synthetic CPU operator/optimizer diagnostic; not learned W or physical smear evidence',
        'independent_dataset_seeds': list(SEEDS),
        'epsilon': list(EPSILONS),
        'objective_budgets_per_start': list(BUDGETS),
        'starts': N_STARTS,
        'bootstrap_dataset_draws': DATASET_BOOTSTRAP_DRAWS,
        'bootstrap_seed': BOOTSTRAP_SEED,
        'mc_precision_target': (
            'N=100 gives worst-case Bernoulli Monte Carlo standard error 0.05; '
            'this is not a CP95 half-width target or publication-grade guarantee.'
        ),
        'selection': 'best training objective over common starts; held-out test error never selects a start',
        'comparison': 'paired Powell minus SLSQP held-out error on the same generated links/probes',
        'failure_accounting': (
            'retain every seed/epsilon cell; separate budget exhaustion, solver failure before budget, '
            'large projected-gradient residual, and data-generation/analysis exception.'
        ),
        'interpretation_limit': (
            'class B includes the constructed teacher direction; near-zero oracle error is representability, '
            'not learned generalization. This experiment does not answer learned-smear versus SLSQP.'
        ),
        'source_sha256': {str(p): sha256(p) for p in paths},
    }


def dataset_rows() -> list[dict]:
    diagnostic.BUDGETS = BUDGETS
    diagnostic.N_STARTS = N_STARTS
    diagnostic.SEEDS = SEEDS
    diagnostic.EPSILONS = EPSILONS
    rows = []
    for seed in SEEDS:
        try:
            data = diagnostic._dataset(seed)
        except Exception as exc:
            for epsilon in EPSILONS:
                rows.append({'seed': seed, 'epsilon': epsilon, 'status': 'FAIL_DATASET',
                             'failure': f'{type(exc).__name__}: {exc}'})
            continue
        for epsilon in EPSILONS:
            try:
                row = diagnostic._diagnose_cell(seed, epsilon, *data)
                row['status'] = 'OK'
                rows.append(row)
            except Exception as exc:
                rows.append({'seed': seed, 'epsilon': epsilon, 'status': 'FAIL_CELL',
                             'failure': f'{type(exc).__name__}: {exc}'})
        if (seed - SEEDS[0] + 1) % 10 == 0:
            print(f'finished {seed - SEEDS[0] + 1}/{len(SEEDS)} datasets', flush=True)
    return rows


def analyze(rows: list[dict]) -> tuple[list[dict], list[dict], dict]:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    paired = []
    conditions = []
    for epsilon in EPSILONS:
        for klass in diagnostic.CLASSES:
            cells = [r['classes'][klass] for r in rows
                     if r.get('status') == 'OK' and r['epsilon'] == epsilon]
            for cell in cells:
                conditions.append({
                    'epsilon': epsilon, 'class': klass,
                    'rank': cell['rank_realified_design'], 'n_features': cell['n_features'],
                    'condition_number': cell['condition_number_scaled'],
                })
            for budget_index, budget in enumerate(BUDGETS):
                slsqp = np.asarray([
                    cell['methods']['SLSQP'][budget_index]['best']['test_error'] for cell in cells
                ])
                powell = np.asarray([
                    cell['methods']['Powell'][budget_index]['best']['test_error'] for cell in cells
                ])
                delta = powell - slsqp
                if len(delta):
                    boot = delta[rng.integers(0, len(delta), size=(DATASET_BOOTSTRAP_DRAWS, len(delta)))].mean(1)
                    ci = np.quantile(boot, [0.025, 0.975]).tolist()
                    mean = float(delta.mean())
                    se = float(delta.std(ddof=1) / np.sqrt(len(delta))) if len(delta) > 1 else None
                else:
                    ci = [None, None]
                    mean = None
                    se = None
                paired.append({
                    'epsilon': epsilon, 'class': klass, 'budget_per_start': budget,
                    'successful_datasets': len(delta), 'planned_datasets': len(SEEDS),
                    'mean_delta_powell_minus_slsqp': mean,
                    'standard_error': se, 'dataset_bootstrap_ci95': ci,
                })

    flags = []
    counts = {'budget_exhausted': 0, 'solver_non_success': 0,
              'success_large_residual': 0, 'cell_failures': sum(r.get('status') != 'OK' for r in rows)}
    for row in rows:
        if row.get('status') != 'OK':
            flags.append({'seed': row['seed'], 'epsilon': row['epsilon'],
                          'flags': [row['status']], 'failure': row.get('failure')})
            continue
        for klass, cell in row['classes'].items():
            for method, traces in cell['methods'].items():
                for trace in traces:
                    for start_index, trial in enumerate(trace['all_starts']):
                        trial_flags = []
                        if trial['budget_exhausted']:
                            trial_flags.append('budget_exhausted')
                        elif not trial['solver_success']:
                            trial_flags.append('solver_non_success')
                        if trial['solver_success'] and trial['projected_gradient_norm_scaled_variables'] > 1e-5:
                            trial_flags.append('success_large_residual')
                        for flag in trial_flags:
                            counts[flag] += 1
                        if trial_flags:
                            flags.append({
                                'seed': row['seed'], 'epsilon': row['epsilon'], 'class': klass,
                                'method': method, 'budget': trace['budget_per_start'],
                                'start': start_index, 'flags': trial_flags,
                                'residual': trial['projected_gradient_norm_scaled_variables'],
                            })
    return paired, conditions, {'counts': counts, 'flagged_trials': flags}


def make_figures(out: Path, rows: list[dict], paired: list[dict], conditions: list[dict]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.7))
    for klass, marker in zip(diagnostic.CLASSES, ('o', 's')):
        group = [c for c in conditions if c['epsilon'] == 0.1 and c['class'] == klass]
        axes[0].scatter(np.arange(len(group)), [c['condition_number'] for c in group],
                        marker=marker, s=18, alpha=.55, label=klass)
    axes[0].set(yscale='log', xlabel='independent dataset (by class series)',
                ylabel='scaled design condition number', title='Conditioning across 100 datasets')
    axes[0].legend()
    axes[0].grid(alpha=.2)

    for klass, color in zip(diagnostic.CLASSES, ('#315a8a', '#b15b32')):
        for method, marker, linestyle in (('SLSQP', 'o', '-'), ('Powell', 's', '--')):
            means, ses = [], []
            for budget in BUDGETS:
                values = [r['classes'][klass]['methods'][method][i]['best']['test_error']
                          for r in rows if r.get('status') == 'OK' and r['epsilon'] == 0.1
                          for i, b in enumerate(BUDGETS) if b == budget]
                values = np.asarray(values, dtype=float)
                means.append(float(values.mean()))
                ses.append(float(values.std(ddof=1) / np.sqrt(len(values))) if len(values) > 1 else 0.)
            axes[1].errorbar(np.asarray(BUDGETS) * N_STARTS, means, yerr=ses,
                             color=color, marker=marker, linestyle=linestyle, capsize=2,
                             label=f'{klass}/{method}')
    axes[1].set(yscale='log', xlabel='maximum objective calls across starts',
                ylabel='held-out relative error (mean ± SE)', title='Budget-limited convergence, ε=0.1')
    axes[1].legend(fontsize=7)
    axes[1].grid(alpha=.2, which='both')
    fig.tight_layout()
    fig.savefig(out / 'condition_budget.png', dpi=160)
    plt.close(fig)

    selected = [p for p in paired if p['epsilon'] == 0.1]
    fig, ax = plt.subplots(figsize=(8, 4.7))
    for i, item in enumerate(selected):
        mean = item['mean_delta_powell_minus_slsqp']
        lo, hi = item['dataset_bootstrap_ci95']
        if mean is None:
            continue
        ax.errorbar(i, mean, yerr=[[mean - lo], [hi - mean]], fmt='o', capsize=3)
    ax.set_xticks(range(len(selected)), [f"{p['class']}\n{p['budget_per_start']}" for p in selected])
    ax.axhline(0, color='black', linestyle='--')
    ax.set(ylabel='paired held-out error: Powell − SLSQP (dataset CI95)',
           title='Independent-link paired optimizer comparison (ε=0.1)')
    ax.grid(alpha=.2, axis='y')
    fig.tight_layout()
    fig.savefig(out / 'paired_optimizer_ci.png', dpi=160)
    plt.close(fig)


def execute(out: Path, frozen: dict) -> dict:
    rows = dataset_rows()
    paired, conditions, failure_info = analyze(rows)
    raw = {
        'schema': 'optgauss-cpu-C-independent-followup-v1',
        'scope': frozen['scope'],
        'protocol_sha256': sha256(out / 'preregistration.json'),
        'rows': rows, 'paired': paired, 'conditions': conditions,
        **failure_info,
    }
    (out / 'raw.json').write_text(json.dumps(raw, indent=2) + '\n')
    make_figures(out, rows, paired, conditions)
    text = f'''# C-package independent-link CPU follow-up (N=100)

Protocol and source hashes were frozen before data generation. This is a synthetic continuation of the class/optimizer convergence diagnostic, using 100 new deterministic dataset seeds ({SEEDS[0]}–{SEEDS[-1]}), 3 shared starts, and budgets 25/100/400 objective calls per start. Each seed creates independent train and held-out links/probes through the existing generator; class A and B are evaluated on the same generated links.

The target worst-case Bernoulli Monte Carlo standard error is 0.05 at N=100. This is not a 95% interval half-width guarantee; all paired continuous-outcome intervals remain specific to this synthetic design. SLSQP gradients are analytic and not counted as objective calls, so equal objective-call budgets are not walltime equality.

| ε | class | budget/start | successful N | mean Powell−SLSQP test error | dataset bootstrap CI95 |
|---|---|---:|---:|---:|---:|
'''
    for p in paired:
        text += (f"|{p['epsilon']}|{p['class']}|{p['budget_per_start']}|"
                 f"{p['successful_datasets']}/{p['planned_datasets']}|"
                 f"{p['mean_delta_powell_minus_slsqp']:.6g}|{p['dataset_bootstrap_ci95']}|\n"
                 if p['mean_delta_powell_minus_slsqp'] is not None else
                 f"|{p['epsilon']}|{p['class']}|{p['budget_per_start']}|0/{p['planned_datasets']}|NA|NA|\n")
    text += f'''
![Conditioning and convergence](condition_budget.png)

![Paired optimizer intervals](paired_optimizer_ci.png)

Across recorded trajectories, failure flags are: `{json.dumps(failure_info['counts'], sort_keys=True)}`. Full flagged seed/start/residual rows are retained in `raw.json`; budget exhaustion is truncation, not solver failure. B's constructed teacher direction means near-zero oracle error is representability, not learned advantage. This result does not test real $W$, production links, learned smear or physical risk.
'''
    (out / 'README.md').write_text(text)
    return {'status': 'COMPLETED' if failure_info['counts']['cell_failures'] == 0 else 'COMPLETED_WITH_FAILURES',
            'successful_cells': sum(r.get('status') == 'OK' for r in rows),
            'planned_cells': len(SEEDS) * len(EPSILONS),
            'failure_counts': failure_info['counts']}


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
        out.mkdir(parents=True, exist_ok=False)
        frozen = protocol()
        (out / 'preregistration.json').write_text(json.dumps(frozen, indent=2) + '\n')
        print(json.dumps({'prepared': str(out), 'protocol_sha256': sha256(out / 'preregistration.json')}, indent=2))
        return
    plan_path = out / 'preregistration.json'
    if not plan_path.is_file():
        parser.error(f'missing preregistration: {plan_path}; prepare first')
    frozen = json.loads(plan_path.read_text())
    if frozen != protocol():
        parser.error('preregistration/source hash changed; create a fresh output directory')
    if any((out / name).exists() for name in ('raw.json', 'README.md', 'condition_budget.png', 'paired_optimizer_ci.png')):
        parser.error('output already contains results; create a fresh output directory')
    started = datetime.now(timezone.utc).isoformat()
    result = execute(out, frozen)
    (out / 'run_metadata.json').write_text(json.dumps({
        'started_utc': started, 'finished_utc': datetime.now(timezone.utc).isoformat(),
        'python': platform.python_version(), 'platform': platform.platform(), **result,
    }, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
