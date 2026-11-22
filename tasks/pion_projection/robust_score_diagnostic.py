"""Diagnostic-only paired-score alternatives for pion projection (CPU).

This module does not change the production physical score. It compares paired
risk-draw summaries and applies a minimum across frozen reference/window
branches, while keeping identity and low-baseline failures visible.
"""
import json
from pathlib import Path

import numpy as np
from scipy.stats import beta, t as student_t

from core.comparator import check_draws

OUT = Path('results/pion_projection/robust_score_cpu_20261119_v1')
N_DATASETS = 400
N_DRAWS = 64
ALPHA = 0.05
MIN_IMPROVEMENT = 1.05
MIN_BASELINE_RISK = 1e-6
RISK_FLOOR = 0.0


def summarize_paired_branches(branches, draw_ids, *, alpha=ALPHA,
                              risk_floor=RISK_FLOOR,
                              min_baseline_risk=MIN_BASELINE_RISK,
                              min_improvement=MIN_IMPROVEMENT,
                              invalid_tolerance=0.0,
                              draw_ids_by_branch=None):
    """Compare paired risk draws and use the worst lower bound over branches.

    Each branch maps to ``{'baseline': array, 'candidate': array}``. The lower
    quantile is an empirical bootstrap-draw diagnostic, not a stand-alone
    frequentist guarantee. ``min_improvement`` is a risk ratio threshold.
    """
    if not branches:
        raise ValueError('at least one frozen reference/window branch is required')
    if not 0 < alpha < 1:
        raise ValueError('alpha must be in (0, 1)')
    if risk_floor < 0 or min_baseline_risk < 0 or min_improvement <= 0:
        raise ValueError('risk floor and baseline floor must be non-negative; improvement positive')
    draw_ids = np.asarray(draw_ids)
    if draw_ids_by_branch is not None:
        for branch, ids in draw_ids_by_branch.items():
            if not np.array_equal(np.asarray(ids), draw_ids):
                raise ValueError(f'{branch}: draw ids differ from the shared paired draw axis')

    per_branch = {}
    all_invalid = 0
    all_draws = 0
    for name, pair in branches.items():
        if set(pair) != {'baseline', 'candidate'}:
            raise ValueError(f'{name}: expected baseline and candidate risk arrays')
        base = np.asarray(pair['baseline'], dtype=float)
        cand = np.asarray(pair['candidate'], dtype=float)
        check_draws({'baseline': base, 'candidate': cand}, draw_ids, finite=False)
        valid = np.isfinite(base) & np.isfinite(cand) & (base > 0) & (cand > 0)
        invalid = int((~valid).sum())
        all_invalid += invalid
        all_draws += int(base.size)
        if not np.any(valid):
            per_branch[name] = {'valid_draws': 0, 'invalid_draws': invalid,
                                'median_baseline_risk': None,
                                'median_log_improvement': None,
                                'paired_log_lower_bound': None,
                                'paired_ratio_lower_bound': None,
                                'abstain': True,
                                'reason': 'no valid paired positive-risk draws'}
            continue
        base_valid, cand_valid = base[valid], cand[valid]
        log_delta = np.log(base_valid + risk_floor) - np.log(cand_valid + risk_floor)
        # Use an order-statistic quantile so monotone transformation commutes
        # exactly: log(q_alpha(ratio)) == q_alpha(log(ratio)).
        q = alpha / len(branches)
        log_lower = float(np.quantile(log_delta, q, method='inverted_cdf'))
        ratio_lower = float(np.quantile(np.exp(log_delta), q, method='inverted_cdf'))
        median_base = float(np.median(base_valid))
        reasons = []
        if median_base < min_baseline_risk:
            reasons.append('baseline risk below frozen floor')
        if invalid / base.size > invalid_tolerance:
            reasons.append('invalid paired draw fraction above tolerance')
        per_branch[name] = {
            'valid_draws': int(valid.sum()), 'invalid_draws': invalid,
            'median_baseline_risk': median_base,
            'median_log_improvement': float(np.median(log_delta)),
            'paired_log_lower_bound': log_lower,
            'paired_ratio_lower_bound': ratio_lower,
            'log_ratio_quantile_identity_residual': float(abs(log_lower - np.log(ratio_lower))),
            'abstain': bool(reasons), 'reasons': reasons,
        }

    worst = min((row['paired_log_lower_bound'] for row in per_branch.values()
                 if row['paired_log_lower_bound'] is not None), default=None)
    reasons = []
    if any(row['abstain'] for row in per_branch.values()):
        reasons.append('one or more frozen branches abstain')
    if all_draws and all_invalid / all_draws > invalid_tolerance:
        if 'invalid paired draw fraction above tolerance' not in reasons:
            reasons.append('invalid paired draw fraction above tolerance')
    threshold = float(np.log(min_improvement))
    certified = (worst is not None and not reasons and worst > threshold)
    return {
        'status': 'diagnostic_only',
        'branches': per_branch,
        'worst_case_log_lower_bound': worst,
        'threshold_log_improvement': threshold,
        'median_only_would_pass': bool(all(
            row['median_log_improvement'] is not None
            and row['median_log_improvement'] > threshold
            for row in per_branch.values())),
        'worst_case_lower_bound_would_pass': bool(certified),
        'abstain': bool(reasons),
        'reasons': reasons,
        'branch_count': len(branches),
        'alpha_per_branch': alpha / len(branches),
    }


def _cp_interval(successes, trials, confidence=0.95):
    if trials == 0:
        return [None, None]
    tail = (1 - confidence) / 2
    low = 0.0 if successes == 0 else float(beta.ppf(tail, successes, trials - successes + 1))
    high = 1.0 if successes == trials else float(beta.ppf(1 - tail, successes + 1, trials - successes))
    return [low, high]


def _paired_draws(rng, effect=0.0, *, scale=1.0, heavy_tail=False, outlier=False,
                  n_draws=N_DRAWS):
    common = rng.normal(0, 0.15, n_draws)
    if heavy_tail:
        base_noise = student_t.rvs(df=3, size=n_draws, random_state=rng) * 0.035
        cand_noise = student_t.rvs(df=3, size=n_draws, random_state=rng) * 0.035
    else:
        base_noise = rng.normal(0, 0.055, n_draws)
        cand_noise = rng.normal(0, 0.055, n_draws)
    base = scale * np.exp(common + base_noise)
    cand = scale * np.exp(common - effect + cand_noise)
    if outlier:
        cand[0] *= 1e-8
    return base, cand


def _method_flags(summary):
    row = summary['branches']
    threshold = summary['threshold_log_improvement']
    eligible = not summary['abstain']
    median = eligible and all(x['median_log_improvement'] is not None
                              and x['median_log_improvement'] > threshold for x in row.values())
    paired = eligible and all(x['paired_log_lower_bound'] is not None
                              and x['paired_log_lower_bound'] > threshold for x in row.values())
    worst = eligible and summary['worst_case_lower_bound_would_pass']
    return {'median_only': bool(median), 'paired_lower_bound': bool(paired),
            'worst_case_reference_window': bool(worst), 'abstain': bool(summary['abstain'])}


def _one_candidate_trial(rng, effects, *, scale=1.0, heavy_tail=False, outlier=False):
    ids = np.arange(N_DRAWS)
    branches = {}
    for name, effect in effects.items():
        base, cand = _paired_draws(rng, effect, scale=scale, heavy_tail=heavy_tail,
                                   outlier=outlier and name == next(iter(effects)))
        branches[name] = {'baseline': base, 'candidate': cand}
    summary = summarize_paired_branches(
        branches, ids, alpha=ALPHA, risk_floor=RISK_FLOOR,
        min_baseline_risk=MIN_BASELINE_RISK,
        min_improvement=MIN_IMPROVEMENT, invalid_tolerance=0.0)
    return summary, _method_flags(summary)


def _rate_record(values):
    count, n = int(sum(values)), len(values)
    return {'count': count, 'n': n, 'rate': count / n if n else None,
            'mc95': _cp_interval(count, n)}


def simulate(n_datasets=N_DATASETS, seed=20261119):
    rng = np.random.default_rng(seed)
    scenarios = {
        'null': {'effects': {'nominal': 0.0}},
        'known_improvement': {'effects': {'nominal': float(np.log(1.30))}},
        'heavy_tail_null': {'effects': {'nominal': 0.0}, 'heavy_tail': True},
        'single_extreme_draw_null': {'effects': {'nominal': 0.0}, 'outlier': True},
        'near_zero_baseline': {'effects': {'nominal': float(np.log(2.0))}, 'scale': 1e-10},
        'reference_window_conflict': {'effects': {'wide_window': 0.15, 'short_window': -0.10}},
        'single_two_state_reference_conflict': {
            'effects': {'single_reference': 0.15, 'two_state_reference': -0.10}},
    }
    rates = {}
    for scenario, options in scenarios.items():
        flags = {method: [] for method in ('median_only', 'paired_lower_bound',
                                            'worst_case_reference_window', 'abstain')}
        for _ in range(n_datasets):
            _, result = _one_candidate_trial(rng, **options)
            for method, value in result.items():
                flags[method].append(value)
        rates[scenario] = {method: _rate_record(values) for method, values in flags.items()}

    # The same candidate ranking is intentionally reversed between frozen windows.
    flip = {'window_1': {'candidate_A': 0.20, 'candidate_B': 0.04},
            'window_2': {'candidate_A': -0.04, 'candidate_B': 0.18}}
    win_counts = {window: {'candidate_A': 0, 'candidate_B': 0} for window in flip}
    median_effects = {window: {candidate: [] for candidate in ('candidate_A', 'candidate_B')}
                      for window in flip}
    worst_bounds = {candidate: [] for candidate in ('candidate_A', 'candidate_B')}
    robust_wins = {candidate: 0 for candidate in ('candidate_A', 'candidate_B')}
    for _ in range(n_datasets):
        ids = np.arange(N_DRAWS)
        summaries = {candidate: {} for candidate in ('candidate_A', 'candidate_B')}
        for window, window_effects in flip.items():
            for candidate, effect in window_effects.items():
                base, cand = _paired_draws(rng, effect)
                summary = summarize_paired_branches(
                    {window: {'baseline': base, 'candidate': cand}}, ids,
                    min_baseline_risk=MIN_BASELINE_RISK,
                    min_improvement=MIN_IMPROVEMENT)
                summaries[candidate][window] = summary['branches'][window]
                median_effects[window][candidate].append(
                    summary['branches'][window]['median_log_improvement'])
            med_a = median_effects[window]['candidate_A'][-1]
            med_b = median_effects[window]['candidate_B'][-1]
            win_counts[window]['candidate_A' if med_a > med_b else 'candidate_B'] += 1
        for candidate in ('candidate_A', 'candidate_B'):
            lower = min(summaries[candidate][window]['paired_log_lower_bound'] for window in flip)
            worst_bounds[candidate].append(lower)
            if lower > np.log(MIN_IMPROVEMENT):
                robust_wins[candidate] += 1
    ranking = {
        'per_window_winner_probability': {
            window: {candidate: count / n_datasets for candidate, count in counts.items()}
            for window, counts in win_counts.items()},
        'per_window_median_log_effect_mean_mcse': {
            window: {candidate: {'mean': float(np.mean(values)),
                                 'mcse': float(np.std(values, ddof=1) / np.sqrt(n_datasets))}
                     for candidate, values in candidates.items()}
            for window, candidates in median_effects.items()},
        'worst_case_lower_bound_mean_mcse': {
            candidate: {'mean': float(np.mean(values)),
                        'mcse': float(np.std(values, ddof=1) / np.sqrt(n_datasets)),
                        'certified': _rate_record([x > np.log(MIN_IMPROVEMENT) for x in values])}
            for candidate, values in worst_bounds.items()},
        'interpretation': 'window winners reverse; requiring improvement in both frozen windows yields no robust certificate here',
    }

    # A common multiplicative configuration shift cancels in paired log risks.
    shift_residuals = []
    for _ in range(n_datasets):
        base, cand = _paired_draws(rng, effect=0.08)
        factor = float(np.exp(rng.normal(0, 3)))
        before = summarize_paired_branches({'frozen': {'baseline': base, 'candidate': cand}},
                                           np.arange(N_DRAWS))['branches']['frozen']
        after = summarize_paired_branches({'frozen': {'baseline': factor * base,
                                                      'candidate': factor * cand}},
                                          np.arange(N_DRAWS))['branches']['frozen']
        shift_residuals.append(abs(before['paired_log_lower_bound'] - after['paired_log_lower_bound']))

    return {
        'schema': 'pion-robust-score-diagnostic-v1',
        'classification': 'synthetic CPU calibration; not a production or physical score',
        'design': {'independent_datasets_per_cell': n_datasets, 'paired_draws_per_dataset': N_DRAWS,
                   'seed': seed, 'alpha': ALPHA, 'min_improvement_ratio': MIN_IMPROVEMENT,
                   'min_baseline_risk': MIN_BASELINE_RISK, 'risk_floor': RISK_FLOOR,
                   'risk_draws_are_synthetic_paired_perturbations': True},
        'methods': {
            'median_only': 'paired median log risk improvement; descriptive ranking rule, not a confidence bound',
            'paired_lower_bound': 'alpha lower order-statistic quantile of paired log risk improvement',
            'raw_ratio_lower_bound': 'same order statistic on (base+floor)/(candidate+floor); log transform is monotone',
            'worst_case_reference_window': 'minimum paired lower bound across the frozen branches; Bonferroni alpha/branch_count',
        },
        'scenario_rates': rates,
        'ranking_reversal': ranking,
        'common_shift_invariance': {'max_abs_lower_bound_change': float(max(shift_residuals)),
                                    'mean_abs_lower_bound_change': float(np.mean(shift_residuals)),
                                    'n_datasets': n_datasets},
        'limitations': [
            'risk draws are synthetic paired perturbations, not lattice correlator bootstrap draws',
            'the empirical lower quantile is not by itself a calibrated confidence interval',
            'worst-case references/windows only handles the declared set and cannot remove common model bias',
            '400 datasets give Monte Carlo precision for this diagnostic, not physical validation',
        ],
    }


def _plot_rates(result, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    scenarios = ('null', 'known_improvement', 'heavy_tail_null',
                 'single_extreme_draw_null', 'near_zero_baseline',
                 'reference_window_conflict', 'single_two_state_reference_conflict')
    methods = ('median_only', 'paired_lower_bound', 'worst_case_reference_window')
    labels = {'median_only': 'Median only', 'paired_lower_bound': 'Paired lower bound',
              'worst_case_reference_window': 'Worst frozen branch'}
    colors = ('#bd634e', '#4777a8', '#48846e')
    fig, ax = plt.subplots(figsize=(11, 5.5))
    x = np.arange(len(scenarios))
    width = 0.24
    for j, (method, color) in enumerate(zip(methods, colors)):
        ys, errlo, errhi = [], [], []
        for scenario in scenarios:
            rec = result['scenario_rates'][scenario][method]
            low, high = rec['mc95']
            ys.append(rec['rate'])
            errlo.append(rec['rate'] - low)
            errhi.append(high - rec['rate'])
        ax.bar(x + (j - 1) * width, ys, width, color=color, label=labels[method],
               yerr=np.array([errlo, errhi]), capsize=2)
    ax.set_xticks(x, [s.replace('_', '\n') for s in scenarios])
    ax.set_ylim(0, 1.04)
    ax.set_ylabel('Fraction across independent synthetic datasets')
    ax.set_title('Paired score rules: threshold-pass frequency with exact MC intervals')
    ax.grid(axis='y', alpha=0.25)
    ax.legend(frameon=False, ncol=3)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_ranking(result, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    ranking = result['ranking_reversal']
    windows = ('window_1', 'window_2')
    candidates = ('candidate_A', 'candidate_B')
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 4.2))
    colors = {'candidate_A': '#4777a8', 'candidate_B': '#bd634e'}
    x = np.arange(2)
    width = 0.34
    for j, candidate in enumerate(candidates):
        vals = [ranking['per_window_median_log_effect_mean_mcse'][w][candidate]['mean'] for w in windows]
        errs = [ranking['per_window_median_log_effect_mean_mcse'][w][candidate]['mcse'] for w in windows]
        axes[0].bar(x + (j - .5) * width, vals, width, yerr=errs, capsize=3,
                    color=colors[candidate], label=candidate)
    axes[0].axhline(np.log(MIN_IMPROVEMENT), color='black', linestyle=':', linewidth=1,
                    label='minimum improvement')
    axes[0].set_xticks(x, ['Window 1', 'Window 2'])
    axes[0].set_ylabel('Mean paired median log improvement (MC SE)')
    axes[0].set_title('Winner changes with reference window')
    axes[0].legend(fontsize=8, frameon=False)
    worst = ranking['worst_case_lower_bound_mean_mcse']
    vals = [worst[c]['mean'] for c in candidates]
    errs = [worst[c]['mcse'] for c in candidates]
    axes[1].bar(candidates, vals, yerr=errs, capsize=3,
                color=[colors[c] for c in candidates])
    axes[1].axhline(np.log(MIN_IMPROVEMENT), color='black', linestyle=':', linewidth=1)
    axes[1].set_ylabel('Mean worst-window lower bound (MC SE)')
    axes[1].set_title('Worst-case score blocks both candidates')
    for ax in axes:
        ax.grid(axis='y', alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _write_readme(result, root):
    rows = []
    for scenario, methods in result['scenario_rates'].items():
        for method, value in methods.items():
            rows.append(f"| {scenario} | {method} | {value['count']}/{value['n']} | "
                        f"{value['rate']:.3f} | [{value['mc95'][0]:.3f}, {value['mc95'][1]:.3f}] |")
    text = f"""# Pion robust-score synthetic calibration

生成命令：`python -m tasks.pion_projection.robust_score_diagnostic`。该实验仅校准 paired score 启发式，不改变生产物理分数。

## 设计

每个 cell 有 {result['design']['independent_datasets_per_cell']} 个独立合成 dataset，每个 dataset 含 {result['design']['paired_draws_per_dataset']} 个共同 paired risk draws。图中区间是以独立 dataset 为试验单位的 95% Clopper–Pearson Monte Carlo 区间。风险 draw 是合成扰动，不是实测格点 bootstrap。

风险比较包括 median-only 描述分、当前形式的 paired log lower order statistic，以及对冻结 reference/window 分支取最差 lower bound。用 inverted-CDF order statistic 时，正风险下 log lower bound 与原风险比 lower bound 是单调变换的同一排序量；二者不能被宣传为独立稳健方法。median-only 只作排名诊断。

## 认证/接受频率

| 场景 | 方法 | 次数 | 比率 | MC 95% 区间 |
| --- | --- | ---: | ---: | ---: |
{chr(10).join(rows)}

![不同 paired 规则的接受频率与 MC 区间](robust_score_rates.png)

## 排名翻转与 sensitivity

Window 1 和 Window 2 被有意设置为不同 candidate 排名；逐窗 winner 概率和 worst-case 下界的均值/MC 标准误保存在 `robust_score_diagnostic.json`，图见下。这个例子说明 worst-case 会对所冻结的分支集合敏感；它不能发现所有模型共同的偏差。

![reference/window 排名翻转](robust_score_sensitivity.png)

共同乘法尺度变化的最大 paired log lower-bound 差为 `{result['common_shift_invariance']['max_abs_lower_bound_change']:.3e}`（{result['common_shift_invariance']['n_datasets']} 个合成 dataset）。`near_zero_baseline` 按固定 `min_baseline_risk={MIN_BASELINE_RISK:g}` abstain。单个极端 draw 对 median-only 与 lower-quantile 规则的区别见频率表。

## 解释边界

这些结果是方法学合成试验，不构成校准保证，也不能修复错误 reference 或共同模型偏差。只有独立 anchor、冻结 score spec 与真实 paired data 才能支持物理评分；当前 production score 仍不因本结果升级。
"""
    (root / 'README.md').write_text(text)


def main():
    if OUT.exists() and any(OUT.iterdir()):
        raise FileExistsError(f'{OUT} already contains results; choose a new output directory')
    OUT.mkdir(parents=True, exist_ok=True)
    result = simulate()
    (OUT / 'robust_score_diagnostic.json').write_text(json.dumps(result, indent=2) + '\n')
    _plot_rates(result, OUT / 'robust_score_rates.png')
    _plot_ranking(result, OUT / 'robust_score_sensitivity.png')
    _write_readme(result, OUT)
    print('wrote', OUT)


if __name__ == '__main__':
    main()
