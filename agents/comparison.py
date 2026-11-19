"""Development-only comparison under a common four-round proposal budget."""
import json
from pathlib import Path

import numpy as np

from agents.llm import chat
from agents.loop import llm_search, prepare_development
from core.candidates import validate_weights
from core.io import digest, fingerprint, write_json
from core.search import search
from tasks.pion_projection.experiment import optimize_mixture


def terminal_reply(prompt, model):
    print(prompt, flush=True)
    return input(f'{model} JSON reply> ')


def compare(run, destination, model, seed, terminal=False):
    dev = prepare_development(run)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    p = dev.protocol
    channels = dev.diagnostics['channels']
    best_basis = min(range(len(channels)), key=lambda i: channels[i]['risk'])
    center = np.eye(len(channels))[best_basis]
    best, trace = llm_search(dev, model, 4, destination, terminal_reply if terminal else chat)
    rng = np.random.default_rng(seed)
    proposals = []
    for k in range(12):
        direction = rng.normal(size=len(center))
        direction -= direction.mean()
        radius = rng.uniform(0, p['optimizer_l1_bound'] - 1)
        u = center + radius * direction / np.linalg.norm(direction, ord=1)
        proposals.append((str(k + 1), u.tolist()))
    random = search(proposals, dev.evaluate, validate=lambda u: validate_weights(u, len(center), p['optimizer_l1_bound']))

    def optimizer_result(ridge):
        fit, converged, calls = optimize_mixture(dev.data, dev.scales, dev.mass, dev.masses, dev.index,
                                                 dict(p, optimizer_ridge=ridge))
        return {'objective_calls': calls, 'converged_starts': converged, 'ridge': ridge,
                'normalized_weights': fit.x.tolist(), 'objective': float(fit.fun), 'risk': dev.evaluate(fit.x)}

    best_llm = best_random = channels[best_basis]['risk']
    progress = []
    for r, row in enumerate(trace):
        for item in row.get('accepted', []):
            best_llm = min(best_llm, item['risk'])
        for item in random.accepted:
            if int(item['source']) <= (r + 1) * 3:
                best_random = min(best_random, item['risk'])
        progress.append({'slots_offered': (r + 1) * 3, 'llm': best_llm, 'random': best_random})

    result = {'protocol_hash': fingerprint(p), 'development_sha256': digest(Path(run) / 'development.npz'),
              'validation_status': 'not_read', 'common_basis_evaluations': len(channels),
              'best_basis': channels[best_basis], 'proposal_slots_per_method': 12,
              'llm': {'model': model, 'transport': 'terminal' if terminal else 'api', 'best': best,
                      'accepted': sum(len(row.get('accepted', [])) for row in trace), 'rounds': trace},
              'random': {'seed': seed, 'best': random.best(), 'accepted': random.accepted, 'rejected': random.rejected},
              'best_including_basis': progress,
              'slsqp': optimizer_result(p['optimizer_ridge']), 'slsqp_raw_risk': optimizer_result(0.0)}
    write_json(destination / 'comparison.json', result)
    write_json(destination / 'development_diagnostics.json', dev.diagnostics)
    print(destination / 'comparison.json', flush=True)
    return result
