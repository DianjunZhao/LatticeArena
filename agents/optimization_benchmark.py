"""Paired, budgeted searches on synthetic pion correlators with known ground energy."""
from pathlib import Path

import numpy as np

from agents.llm import chat
from agents.loop import describe_development, llm_search
from core.candidates import validate_weights
from core.io import digest, fingerprint, write_json
from core.search import Budget, search
from tasks.pion_projection.common import protocol
from tasks.pion_projection.experiment import late_metric
from tasks.pion_projection.statistics import ReferenceFit, bootstrap_indices, risk, shape

ROUNDS = 4
BATCH = 3


def spectrum(rng, p):
    """Vary excited overlaps, gaps, and noise across instances of the same search task."""
    n = len(p['powers'])
    mass = rng.uniform(.65, .95)
    energies = [mass, mass + rng.uniform(.18, .35), mass + rng.uniform(.5, .9)]
    times = np.arange(p['geometry'][3] // 2 + 1)
    modes = shape(energies, times, p['geometry'][3])
    ground = rng.uniform(.7, 1.3, n)
    overlaps = np.column_stack([ground, ground * rng.uniform(-.2, 1.4, n),
                                ground * rng.uniform(-.8, .8, n)])
    return mass, overlaps @ modes, ground[:, None] * modes[0], rng.uniform(.025, .1, n)


def sample_blocks(rng, mean, ground, noise, nblocks):
    n, nt = mean.shape
    covariance = .65 ** np.abs(np.arange(nt)[:, None] - np.arange(nt))
    fluctuations = rng.multivariate_normal(np.zeros(nt), covariance, size=(nblocks, n + 1))
    return mean + ground * noise[:, None] * (fluctuations[:, :1] + fluctuations[:, 1:]) / np.sqrt(2)


def best_basis(dev):
    channels = dev.diagnostics['channels']
    i = min(range(len(channels)), key=lambda j: channels[j]['risk'])
    return {'source': 'basis', 'risk': channels[i]['risk'], 'candidate': np.eye(len(channels))[i].tolist()}


def summarize_rounds(dev, trace):
    best = best_basis(dev)
    progression = []
    for row in trace:
        best = min([best, *row.get('accepted', [])], key=lambda item: item['risk'])
        progression.append(best['risk'])
    return {'candidate': best['candidate'], 'selected_from': best['source'], 'development_risk': best['risk'],
            'best_after_each_round': progression,
            'accepted': sum(len(row.get('accepted', [])) for row in trace)}


def baseline_search(dev, seed, method):
    """Use the same random moves for fixed-center and feedback-directed search."""
    rng = np.random.default_rng(seed)
    base = best_basis(dev)
    center = np.asarray(base['candidate'])
    eye = np.eye(len(center))
    bound = dev.protocol['optimizer_l1_bound']
    trace = []
    if method == 'curve_fit':
        curves = np.array([c['q_early'] for c in dev.diagnostics['channels']]) - 1
        gram = curves @ curves.T
        regularization = np.geomspace(1e-5, 1, ROUNDS * BATCH)
    for r in range(ROUNDS):
        batch = []
        for i in range(BATCH):
            k = r * BATCH + i
            if method == 'curve_fit':
                # Minimize the squared linearized shape departure plus ridge under sum(u)=1.
                u = np.linalg.solve(gram + regularization[k] * eye, np.ones(len(center)))
                u /= u.sum()
                delta = u - center
            else:
                direction = rng.normal(size=len(center))
                direction -= direction.mean()
                delta = rng.uniform(0, 2) * direction / np.abs(direction).sum()
            # Scale the step conservatively so every baseline obeys the same L1 constraint.
            length = np.abs(delta).sum()
            step = min(1, max(0, bound - np.abs(center).sum()) / length) if length else 0
            batch.append((f'{r}.{i}', (center + step * delta).tolist()))
        found = search(batch, dev.evaluate, validate=lambda u: validate_weights(u, len(center), bound),
                       budget=Budget(BATCH))
        trace.append({'round': r, 'accepted': found.accepted, 'rejections': found.rejected})
        if method == 'adaptive_random':
            base = min([base, *found.accepted], key=lambda item: item['risk'])
            center = np.asarray(base['candidate'])
    return trace


def test_selected(dev, candidate, test, indices, truth):
    p = dev.protocol
    w = np.asarray(candidate) / dev.scales
    try:
        metric = late_metric(dev.data, w, p)
        value = risk(test, w, dev.mass, dev.masses, indices, p, late_inverse=metric)
    except (ValueError, np.linalg.LinAlgError) as exc:
        return {'risk': None, 'invalid_reason': str(exc)}
    window = p['score_window']
    train = np.einsum('nbt,b->nt', dev.data, w)[:, None, :]
    result = {key: value[key] for key in ('risk', 'variance', 'departure_squared')}
    try:
        model = ReferenceFit(train, dict(p, reference_basis=[0]), window)
        exact = w @ truth
        energy, _ = model.fit(exact[window] / model.scales[0])
        result['noiseless_energy_bias'] = energy - dev.mass
    except (ValueError, np.linalg.LinAlgError) as exc:
        result.update(noiseless_energy_bias=None, energy_invalid_reason=str(exc))
    return result


def paired_summary(cases, left, right):
    ratios = []
    bias_pairs = []
    for case in cases:
        a, b = (case['test'][name]['risk'] for name in (left, right))
        if a is not None and b is not None and a > 0 and b > 0:
            ratios.append(a / b)
            ea, eb = (case['test'][name].get('noiseless_energy_bias') for name in (left, right))
            if ea is not None and eb is not None:
                bias_pairs.append((abs(ea), abs(eb)))
    return {'numerator': left, 'denominator': right, 'cases': len(cases), 'valid_pairs': len(ratios),
            'valid_bias_pairs': len(bias_pairs), 'denominator_smaller_abs_bias': sum(b < a for a, b in bias_pairs),
            'denominator_wins': sum(x > 1 for x in ratios), 'ties': sum(x == 1 for x in ratios),
            'median_ratio': float(np.median(ratios)) if ratios else None}


def benchmark(destination, seed, episodes, model=None, *, replay=None, responder=None):
    if episodes < 1 or seed < 0:
        raise ValueError('Provide a nonnegative seed and at least one episode')
    if replay is not None:
        replies = Path(replay).read_text().splitlines()
        if len(replies) != ROUNDS:
            raise ValueError(f'Expected {ROUNDS} lines of archived replies')
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=False)
    p = dict(protocol(), bootstrap_samples=128)
    cases = []
    for episode in range(episodes):
        folder = root / f'episode-{episode:03d}'
        folder.mkdir()
        streams = np.random.SeedSequence([seed, episode]).spawn(5)
        mass, truth, ground, noise = spectrum(np.random.default_rng(streams[0]), p)
        nblocks = 32
        data = sample_blocks(np.random.default_rng(streams[1]), truth, ground, noise, nblocks)
        draws = bootstrap_indices(nblocks, p['bootstrap_samples'], streams[2])
        dev = describe_development(p, data, draws, mass, np.full(len(draws), mass))
        write_json(folder / 'development.json', dev.diagnostics)
        selections = {'basis': summarize_rounds(dev, [])}
        for method in ('fixed_random', 'adaptive_random', 'curve_fit'):
            trace = baseline_search(dev, streams[3], method)
            write_json(folder / f'{method}.json', trace)
            selections[method] = summarize_rounds(dev, trace)
        if replay is not None:
            archived = iter(replies)
            dest = folder / 'archived_proposals'
            dest.mkdir()
            _, trace = llm_search(dev, 'archived', ROUNDS, dest, lambda *_: next(archived))
            selections['archived_proposals'] = summarize_rounds(dev, trace)
        if model:
            conditions = [True, False] if episode % 2 == 0 else [False, True]
            for feedback in conditions:
                name = 'llm_feedback' if feedback else 'llm_no_feedback'
                dest = folder / name
                dest.mkdir()
                context = ('This is a synthetic correlator search with known mass. '
                           'You see the same development basis diagnostics in every round.')
                if not feedback:
                    context += ' Previous proposals are listed without their outcomes.'
                _, trace = llm_search(dev, model, ROUNDS, dest, responder or chat,
                                      feedback=feedback, context=context)
                selections[name] = summarize_rounds(dev, trace)
        write_json(folder / 'selection.json', selections)
        # No evaluator output goes back to a proposal method. Each API call has its own prompt.
        test_stream, bootstrap_stream = streams[4].spawn(2)
        test = sample_blocks(np.random.default_rng(test_stream), truth, ground, noise, nblocks)
        test_draws = bootstrap_indices(nblocks, p['bootstrap_samples'], bootstrap_stream)
        scores = {name: test_selected(dev, row['candidate'], test, test_draws, truth)
                  for name, row in selections.items()}
        case = {'episode': episode, 'selection_hash': fingerprint(selections), 'test': scores}
        cases.append(case)
        write_json(folder / 'test.json', case)
    pairs = [('basis', 'curve_fit'), ('fixed_random', 'adaptive_random')]
    if replay is not None:
        pairs += [('basis', 'archived_proposals'), ('archived_proposals', 'curve_fit')]
    if model:
        pairs += [('llm_no_feedback', 'llm_feedback'), ('curve_fit', 'llm_feedback'),
                  ('adaptive_random', 'llm_feedback'), ('basis', 'llm_feedback')]
    result = {'task': 'synthetic-pion-search-v1', 'seed': seed, 'episodes': episodes, 'model': model,
              'replay_sha256': digest(replay) if replay is not None else None,
              'protocol': p, 'shared_basis_evaluations': len(p['powers']), 'proposal_slots': ROUNDS * BATCH,
              'paired_test_risk': [paired_summary(cases, a, b) for a, b in pairs], 'cases': cases}
    write_json(root / 'benchmark.json', result)
    return result
