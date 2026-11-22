"""Synthetic regression for the fit-state estimand (optimize package B).

The training amplitude is fitted on a disjoint block split and frozen for the
validation calculation. The validation-estimated branch refits it in each
bootstrap draw. This is a CPU estimator-consistency diagnostic, not a claim
about reference-model validity or unconditional training-amplitude coverage.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import beta

from tasks.pion_projection.statistics import blocks, bootstrap_indices, risk

from .unified import risk_with_fixed_amplitude

OUT = Path('results/optimize_gaussian/cpu_close_20261119_B_regression_fitted')
PROTOCOL = {'amplitude_window': [6, 7, 8], 'score_window': [2, 3, 4, 5],
            'geometry': [4, 4, 4, 9], 'covariance_shrinkage': 0.1,
            'amplitude_z_min': 0.0}
M, A = 0.5, 1.0


def f0(t, m=M, T=9):
    return np.exp(-m * t) + np.exp(-m * (T - t))


def dataset(rng, ncfg=80, noise=0.01):
    t = np.arange(PROTOCOL['geometry'][3])
    signal = A * f0(t)
    return signal[None, None, :] * (1 + noise * rng.normal(size=(ncfg, 1, len(t))))


def _clopper_pearson(successes, total, alpha=0.05):
    lower = 0.0 if successes == 0 else float(beta.ppf(alpha / 2, successes, total - successes + 1))
    upper = 1.0 if successes == total else float(beta.ppf(1 - alpha / 2, successes + 1, total - successes))
    return [lower, upper]


def _plot(result, out):
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 4.0))
    names = ('train_frozen', 'validation_refit')
    labels = ('training amplitude frozen', 'validation amplitude refit')
    colors = ('#315a8a', '#b15b32')
    bias = [result['summary'][n]['bias_mean'] for n in names]
    bias_se = [result['summary'][n]['bias_se'] for n in names]
    axes[0].errorbar(range(2), bias, yerr=bias_se, fmt='o', capsize=4, color='#315a8a')
    axes[0].axhline(0, color='black', linewidth=1, alpha=0.6)
    axes[0].set_xticks(range(2), labels, rotation=15, ha='right')
    axes[0].set_ylabel('mean(point q - bootstrap mean q)')
    axes[0].set_title('Point / replica consistency')
    coverage = [result['summary'][n]['all_windows_coverage'] for n in names]
    lows = [coverage[i] - result['summary'][names[i]]['all_windows_coverage_cp95'][0]
            for i in range(2)]
    highs = [result['summary'][names[i]]['all_windows_coverage_cp95'][1] - coverage[i]
             for i in range(2)]
    axes[1].bar(range(2), coverage, color=colors, alpha=0.85)
    axes[1].errorbar(range(2), coverage, yerr=np.array([lows, highs]), fmt='none', ecolor='black', capsize=4)
    axes[1].set_xticks(range(2), labels, rotation=15, ha='right')
    axes[1].set_ylim(0, 1.05)
    axes[1].set_ylabel('fraction of independent datasets')
    axes[1].set_title('All score-window points covered')
    fig.suptitle(f"Synthetic CPU diagnostic ({result['n_dataset']} datasets; {result['n_boot']} draws)")
    fig.tight_layout()
    fig.savefig(out / 'regression.png', dpi=180)
    plt.close(fig)


def run(n_dataset=60, n_boot=200, seed=20261123, out=None, make_plot=True):
    rng = np.random.default_rng(seed)
    rows = []
    weights = np.ones(1)
    for dataset_id in range(n_dataset):
        data = blocks(dataset(rng), 5)
        split = rng.permutation(len(data))
        train, validation = data[split[:8]], data[split[8:]]
        masses = np.full(n_boot, M) + rng.normal(0, 0.002, n_boot)
        train_index = bootstrap_indices(len(train), n_boot, seed + 1000 + dataset_id)
        validation_index = bootstrap_indices(len(validation), n_boot, seed + 2000 + dataset_id)
        train_fit = risk(train, weights, M, masses, train_index, PROTOCOL)
        validation_fit = risk(validation, weights, M, masses, validation_index, PROTOCOL)
        row = {'train_amplitude': train_fit['amplitude'],
               'validation_amplitude': validation_fit['amplitude'], 'sources': {}}
        for source, amplitude, amplitude_se in (
                ('train_frozen', train_fit['amplitude'], train_fit['amplitude_se']),
                ('validation_refit', validation_fit['amplitude'], validation_fit['amplitude_se'])):
            estimator_source = 'train' if source == 'train_frozen' else 'test'
            metric = risk_with_fixed_amplitude(
                validation, weights, M, masses, validation_index, PROTOCOL,
                amplitude, amplitude_se, amplitude_source=estimator_source,
                return_draws=True)
            q = np.asarray(metric['q'])
            q_boot = np.asarray(metric['q_boot'])
            q_target = A / amplitude
            interval = np.quantile(q_boot, [0.025, 0.975], axis=0)
            covered = (interval[0] <= q_target) & (q_target <= interval[1])
            row['sources'][source] = {
                'q': q.tolist(), 'replica_mean': q_boot.mean(axis=0).tolist(),
                'point_minus_replica': float(np.mean(q - q_boot.mean(axis=0))),
                'conditional_q_target': float(q_target),
                'conditional_coverage': covered.tolist(),
                'risk': metric['risk'],
                'late_covariance_source': metric['late_covariance_source'],
            }
        rows.append(row)

    summary = {}
    for source in ('train_frozen', 'validation_refit'):
        biases = np.asarray([r['sources'][source]['point_minus_replica'] for r in rows])
        # Time points from one dataset are correlated; average within each
        # dataset, then estimate MC error across independent datasets.
        dataset_coverage = np.asarray([
            np.mean(r['sources'][source]['conditional_coverage']) for r in rows])
        all_windows = [bool(np.all(r['sources'][source]['conditional_coverage'])) for r in rows]
        all_successes = int(sum(all_windows))
        coverage_mean = float(dataset_coverage.mean()) if len(dataset_coverage) else None
        coverage_se = (float(dataset_coverage.std(ddof=1) / np.sqrt(len(dataset_coverage)))
                       if len(dataset_coverage) > 1 else 0.0)
        summary[source] = {
            'bias_mean': float(biases.mean()),
            'bias_se': float(biases.std(ddof=1) / np.sqrt(len(biases))) if len(biases) > 1 else 0.0,
            'conditional_coverage': coverage_mean,
            'coverage_se_across_datasets': coverage_se,
            'all_windows_coverage': all_successes / len(all_windows) if all_windows else None,
            'all_windows_coverage_successes': all_successes,
            'all_windows_coverage_trials': len(all_windows),
            'all_windows_coverage_cp95': (_clopper_pearson(all_successes, len(all_windows))
                                          if all_windows else [None, None]),
            'independent_dataset_count': len(dataset_coverage),
        }
    result = {'n_dataset': n_dataset, 'n_boot': n_boot, 'seed': seed,
              'n_blocks': 16, 'train_validation_blocks': [8, 8],
              'mass': M, 'true_amplitude': A, 'rows': rows, 'summary': summary,
              'interpretation': ('coverage is conditional on each frozen point amplitude; '
                                 'training-amplitude uncertainty is not propagated into the '
                                 'validation interval. Coverage MC error is calculated across '
                                 'independent datasets; exact binomial intervals use one '
                                 'all-windows-covered indicator per dataset')}
    out = Path(out) if out is not None else OUT
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f'{out} already contains results; choose a new output directory')
    out.mkdir(parents=True, exist_ok=True)
    (out / 'regression.json').write_text(json.dumps(result, indent=2) + '\n')
    if make_plot:
        _plot(result, out)
    print(json.dumps(summary, indent=2))
    return result


if __name__ == '__main__':
    run()
