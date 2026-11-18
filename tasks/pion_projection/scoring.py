"""Conservative improvement certificate for a frozen candidate set (todo S1).

The function below works on per-model bootstrap risk draws, not on correlators:
the caller must produce the draws with a frozen analysis plan. A candidate is
certified only if its log-risk improvement over the baseline is positive at a
simultaneous lower bound across the accepted reference models and the compared
candidates (Bonferroni over J*K).
"""
import numpy as np

SCHEMA = 'pion-score-v1'
REQUIRED = ('schema', 'version', 'estimand', 'baseline_id', 'alpha', 'comparison_family')


def validate_spec(spec):
    missing = [key for key in REQUIRED if key not in spec]
    if missing:
        raise ValueError(f'score spec is missing {missing}')
    if spec['schema'] != SCHEMA:
        raise ValueError(f'unsupported score schema {spec["schema"]!r}')
    if not 0 < spec['alpha'] < 1:
        raise ValueError('alpha must be in (0, 1)')
    family = spec['comparison_family']
    if not isinstance(family, dict) or family.get('candidates', 0) < 1 or family.get('models', 0) < 1:
        raise ValueError('comparison_family needs positive candidates and models')
    if spec.get('risk_floor', 0.0) < 0:
        raise ValueError('risk_floor must be non-negative')
    return spec


def improvement_certificate(risks, spec):
    """risks: {model: {candidate: array of risk draws}}; the baseline must be present."""
    spec = validate_spec(spec)
    baseline = spec['baseline_id']
    models = list(risks)
    if len(models) != spec['comparison_family']['models']:
        raise ValueError('model count does not match comparison_family')
    candidates = [c for c in risks[models[0]] if c != baseline]
    if len(candidates) != spec['comparison_family']['candidates']:
        raise ValueError('candidate count does not match comparison_family')
    if any(baseline not in risks[m] for m in models):
        raise ValueError('baseline missing in at least one model')
    floor = float(spec.get('risk_floor', 0.0))
    level = spec['alpha'] / (len(candidates) * len(models))
    tolerance = float(spec.get('invalid_tolerance', 0.0))
    out = {'spec_version': spec['version'], 'level': level, 'candidates': {}, 'abstain': False,
           'failure_reasons': []}
    for cand in candidates:
        row = {'per_model_lower_bound': {}, 'per_model_median_improvement': {}, 'invalid_draws': 0}
        bounds = []
        for m in models:
            base = np.asarray(risks[m][baseline], dtype=float) + floor
            value = np.asarray(risks[m][cand], dtype=float) + floor
            valid = np.isfinite(base) & np.isfinite(value) & (base > 0) & (value > 0)
            row['invalid_draws'] += int((~valid).sum())
            d = np.log(base[valid]) - np.log(value[valid])
            if len(d) == 0:
                row['per_model_lower_bound'][m] = None
                bounds.append(-np.inf)
                continue
            low = float(np.quantile(d, level))
            row['per_model_lower_bound'][m] = low
            row['per_model_median_improvement'][m] = float(np.median(d))
            bounds.append(low)
        row['lower_bound'] = float(min(bounds))
        row['improvement_lower_bound'] = float(np.exp(min(bounds))) if np.isfinite(min(bounds)) else 0.0
        row['certified'] = bool(np.isfinite(min(bounds)) and min(bounds) > 0)
        out['candidates'][cand] = row
    total = sum(risks[m][baseline].__len__() for m in models)
    invalid = sum(row['invalid_draws'] for row in out['candidates'].values())
    if total and invalid / (total * len(candidates)) > tolerance:
        out['abstain'] = True
        out['failure_reasons'].append('invalid draw fraction above tolerance')
    out['status'] = 'abstain' if out['abstain'] else (
        'certified' if any(row['certified'] for row in out['candidates'].values()) else 'not_certified')
    return out
