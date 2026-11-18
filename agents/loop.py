"""Ask an LLM to propose a signed mixture of diffusion kernels and score it on development."""
import hashlib
import inspect
import json
import tempfile
from pathlib import Path

import numpy as np

from agents.llm import chat
from core.candidates import validate_weights
from core.io import digest, fingerprint, write_json
from core.search import Budget, search
from tasks.pion_projection.common import load_data
from tasks.pion_projection.experiment import late_metric
from tasks.pion_projection.statistics import ReferenceFit, blocks, bootstrap_indices, fold, risk

PROMPT = """You are optimizing the sink kernel of a quenched pion two-point function.

K = sum_k u_k H^p_k / A_k,  H = (I + {alpha} * spatial_hopping) / (1 + 6*{alpha})
powers p_k = {powers}, A_k are the measured amplitudes of each channel.
u is the normalized coefficient vector: sum(u) = 1, sum(|u|) <= {l1_bound}.
u = e_0 (the first power) is the local sink. Signed u are allowed.

Score (lower is better), with m0 fixed by the evaluator:
  q(t) = C(t) / (A f0(t)),  f0(t) = exp(-m0 t) + exp(-m0 ({T}-t))
  risk = mean over t in {score_window} of [ Var_boot(q(t)) + (q(t)-1)^2 ]
The departure term dominates, so a good kernel makes q(t) flat over that window.

Channels, as (power, amplitude A_k, risk of u=e_k):
{baselines}

Previous attempts, as (u, risk):
{history}

Return JSON only: {{"candidates": [[{n_powers} u values], [{n_powers} u values], [{n_powers} u values]]}}
Propose three structurally different vectors each round.
"""


def render_prompt(p, baselines, history):
    return PROMPT.format(alpha=p['alpha'], powers=list(p['powers']), T=p['geometry'][3],
                         score_window=list(p['score_window']), baselines=baselines,
                         history=json.dumps(history[-6:]), n_powers=len(p['powers']),
                         l1_bound=p['optimizer_l1_bound'])


def run(output, model, rounds, allow_validation=False):
    if rounds < 1:
        raise ValueError('rounds must be positive')
    output = Path(output)
    p = json.loads((output / 'development_provenance.json').read_text())['protocol']
    data = blocks(fold(load_data(output, 'development', p)), p['block_length'])
    frozen_path = output / 'submission.json'
    if frozen_path.exists():
        frozen = json.loads(frozen_path.read_text())
        if (frozen['protocol_hash'] != fingerprint(p)
                or frozen['development_sha256'] != digest(output / 'development.npz')):
            raise ValueError('Frozen protocol or development data changed')
        scorer = inspect.getfile(ReferenceFit)
        if frozen['statistics_sha256'] != digest(scorer):
            raise ValueError('Frozen scoring implementation changed')
        if frozen.get('reference', {}).get('kind', 'single') != 'single':
            raise ValueError('This agent supports the single-state pion pilot')

    index = bootstrap_indices(len(data), p['bootstrap_samples'], p['seed'])
    window = p['reference_windows'][p['reference_nominal_window']]
    ref, masses = ReferenceFit(data, p, window).bootstrap(index)
    basis = np.eye(len(p['powers']))
    scores = [risk(data, w, ref['mass'], masses, index, p) for w in basis]
    scales = np.array([s['amplitude'] for s in scores])
    baselines = [[power, float(scale), s['risk']] for power, scale, s in zip(p['powers'], scales, scores)]

    def evaluate(u):
        weights = np.asarray(u, dtype=float) / scales
        return risk(data, weights, ref['mass'], masses, index, p)['risk']

    root = output / 'agent'
    root.mkdir(exist_ok=True)
    destination = Path(tempfile.mkdtemp(prefix='search-', dir=root))
    history, trace, accepted = [], [], []
    for r in range(rounds):
        prompt = render_prompt(p, baselines, history)
        reply = chat(prompt, model)
        record = {'round': r, 'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
                  'reply_sha256': hashlib.sha256(reply.encode()).hexdigest()}
        trace.append(record)
        try:
            payload = json.loads(reply)
        except json.JSONDecodeError:
            payload = None
        proposals = payload.get('candidates') if isinstance(payload, dict) else None
        if not isinstance(proposals, list) or not proposals:
            record['error'] = 'expected a candidates list'
            history.append(record['error'])
        else:
            found = search(((f'{r}.{i}', u) for i, u in enumerate(proposals)), evaluate,
                           validate=lambda u: validate_weights(u, len(scales), p['optimizer_l1_bound']),
                           budget=Budget(3))
            record['accepted'] = found.accepted
            record['rejections'] = [{'source': row['source'], 'reason': row['reason']}
                                    for row in found.rejected]
            record['over_budget'] = found.budget_exhausted
            history.extend([*found.accepted, *record['rejections']])
            accepted.extend(found.accepted)
        write_json(destination / 'rounds.json', trace)

    best = min(accepted, key=lambda row: row['risk']) if accepted else None
    summary = {'model': model, 'rounds': rounds, 'protocol_hash': fingerprint(p),
               'development_sha256': digest(output / 'development.npz'), 'best': best,
               'validation_status': 'not_read'}
    if best:
        weights = np.asarray(best['candidate'], dtype=float) / scales
        best['weights'] = weights.tolist()
    write_json(destination / 'best.json', summary)
    if allow_validation and best:
        validation = blocks(fold(load_data(output, 'validation', p)), p['block_length'])
        vi = bootstrap_indices(len(validation), p['bootstrap_samples'], p['seed'] + 1)
        summary['validation_status'] = 'post_hoc_diagnostic'
        summary['validation_sha256'] = digest(output / 'validation.npz')
        try:
            summary['validation_risk'] = risk(validation, weights, ref['mass'], masses, vi, p,
                                              late_inverse=late_metric(data, weights, p))['risk']
        except ValueError as exc:
            summary['validation_invalid'] = str(exc)
        write_json(destination / 'best.json', summary)
    print(destination / 'best.json')
    return summary
