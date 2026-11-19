import json

import numpy as np
import pytest

from core.io import write_json
from tasks.pion_projection.path_kernel import build_kernel, expand_paths


def random_su3(rng, shape):
    size = (*shape, 3, 3)
    u, _ = np.linalg.qr(rng.normal(size=size) + 1j * rng.normal(size=size))
    u[..., :, 0] /= np.linalg.det(u)[..., None]
    return u


def dagger(a):
    return a.conj().swapaxes(-2, -1)


def direct_hops(links, field, path):
    for step in reversed(path):
        mu = abs(step) - 1
        axis = 2 - mu
        if step > 0:
            field = links[mu] @ np.roll(field, -1, axis=axis)
        else:
            field = np.roll(dagger(links[mu]) @ field, 1, axis=axis)
    return field


def test_bent_path_transport_matches_direct_hops_and_gauge_transform():
    rng = np.random.default_rng(29)
    spatial = (3, 4, 5)
    links = random_su3(rng, (3, *spatial))
    g = random_su3(rng, spatial)
    transformed = np.stack([g @ u @ dagger(np.roll(g, -1, axis=2-mu)) for mu, u in enumerate(links)])
    field = rng.normal(size=(*spatial, 3, 2)) + 1j * rng.normal(size=(*spatial, 3, 2))
    terms = {'terms': [{'path': [1, 1, -2], 'weight': [0.9, 0.7]}, {'path': [], 'weight': -0.2}]}
    coeffs = expand_paths(terms)
    assert coeffs[(1, 1, 2)] == pytest.approx(0.9 / 48)
    assert coeffs[(-2, -1, -1)] == pytest.approx(0.9 / 48)
    result = build_kernel(links, terms).apply(field)
    expected = sum(w * direct_hops(links, field, path) for path, w in coeffs.items())
    np.testing.assert_allclose(result, expected, atol=1e-13)
    np.testing.assert_allclose(build_kernel(transformed, terms).apply(g @ field), g @ result, atol=1e-13)
    # For a Hermitian kernel, K[U*]^T = K[U] is equivalent to K[U*] = K[U]*.
    np.testing.assert_allclose(build_kernel(links.conj(), terms).apply(field.conj()), result.conj(), atol=1e-13)
    with pytest.raises(ValueError, match='zero'):
        expand_paths({'terms': [{'path': [1, 1, 2], 'weight': [0, 1]}]})
    other = np.roll(field, 1, axis=0)
    np.testing.assert_allclose(np.vdot(other, result), np.vdot(build_kernel(links, terms).apply(other), field))
    # Different order to the same endpoint yields different transport on interacting links.
    reordered = {'terms': [dict(terms['terms'][0], path=[1, -2, 1]), terms['terms'][1]]}
    assert not np.allclose(build_kernel(links, reordered).apply(field), result)


def test_path_symmetry_free_field_support_and_periodicity():
    links = np.broadcast_to(np.eye(3), (3, 5, 5, 5, 3, 3))
    terms = {'terms': [{'path': [], 'weight': -3}, {'path': [1, 1, 1], 'weight': 12}]}
    field = np.zeros((5, 5, 5, 3, 1), complex)
    field[0, 0, 0, 0, 0] = 1
    expected = -3 * field
    for axis in range(3):
        for sign in (-1, 1):
            expected += 2 * np.roll(field, sign * 3, axis=axis)
    np.testing.assert_allclose(build_kernel(links, terms).apply(field), expected)
    bent = {'terms': [{'path': [1, -2, 1, 3], 'weight': [1., .4]}]}
    rotated = {'terms': [{'path': [-3, -1, -3, 2], 'weight': [1., .4]}]}
    assert expand_paths(bent) == expand_paths(rotated)


@pytest.mark.parametrize('term', [{'path': [], 'weight': [0, 1]}, {'path': [0], 'weight': 1},
                                  {'path': [True], 'weight': 2}, {'path': [], 'weight': float('inf')}])
def test_invalid_path(term):
    with pytest.raises(ValueError):
        expand_paths({'terms': [term]})


@pytest.mark.parametrize('feedback', ['round', 'batch'])
def test_search_feedback_and_frozen_selection(tmp_path, monkeypatch, feedback):
    from agents import operator_search as search

    write_json(tmp_path / 'submission.json', {'calibration': {'reference': {}, 'reference_passed': False}})
    write_json(tmp_path / 'development_provenance.json', {'protocol': {'geometry': [4]*4, 'score_window': [1], 'powers': [0],
                                                                         'wall_seconds_per_configuration': 300, 'gpu_memory_limit_gib': 10}})
    write_json(tmp_path / 'development_results.json', {'basis': [{'q': [2.], 'risk': 1.}], 'agent': {'risk': .5}})
    proposals = iter([None, [], [1], [-2]])
    seen_splits = []

    def propose(prompt, model):
        path = next(proposals)
        if feedback == 'batch':
            assert not seen_splits and '"history":' not in prompt and '"previous_replies":' in prompt
            if path in ([1], [-2]):
                assert 'bad' in prompt and '"mean": [3]' not in prompt
        elif path in ([1], [-2]):
            assert '"mean": [3]' in prompt and '"risk": 0.8' in prompt
        if path is None:
            return 'bad'
        return json.dumps({'terms': [{'path': path, 'weight': 1}]})

    def measure(output, definition, split, *, candidate_root):
        path = json.loads(definition.read_text())['parameters']['terms'][0]['path']
        seen_splits.append((path, split))
        dest = candidate_root / definition.parent.name
        if split == 'validation':
            frozen = json.loads((candidate_root.parent / 'selection.json').read_text())
            assert frozen['best']['round'] == 3 and frozen['validation_status'] == 'not_read'
        else:
            write_json(dest / 'frozen.json', {'development_diagnostic': {'risk': .3 if path else .8, 'q': [1],
                       'mean': [3], 'se': [.1], 'variance': .1, 'departure_squared': .2}})
        return dest

    monkeypatch.setattr(search, 'chat', propose)
    monkeypatch.setattr(search, 'run_candidate', measure)
    result = search.run(tmp_path, 'stub', 4, allow_validation=(feedback == 'round'), feedback=feedback)
    session, = (tmp_path / 'agent').iterdir()
    assert result['attempts'] == 4 and result['development_measurement_attempts'] == 2
    assert result['valid_proposals'] == 2 and result['first_valid_round'] == 2
    assert result['best_development_risk_by_attempt'] == [None, .8, .3, .3]
    if feedback == 'batch':
        assert result['validation_status'] == 'not_read' and len(seen_splits) == 2
    result = search.validate_selection(session)
    assert search.validate_selection(session) == result
    assert result['validation_status'] == 'measured'
    assert seen_splits == [([], 'development'), ([1], 'development'), ([1], 'validation')]
    history, = (tmp_path / 'agent').glob('*/history.json')
    records = json.loads(history.read_text())
    assert records[0]['rejected'] and 'Repeated' in records[3]['rejected']


def test_unidentified_validation_candidate_has_no_score():
    from tasks.pion_projection.candidate import compare_candidate
    from tasks.pion_projection.common import protocol
    from tasks.pion_projection.statistics import shape

    p = dict(protocol(), bootstrap_samples=32)
    rng = np.random.default_rng(82)
    val = shape(.8, np.arange(9), 16) * rng.uniform(.98, 1.02, (8, 1, 9))
    metric = np.eye(len(p['amplitude_window'])).tolist()
    frozen = {'submissions': {'local': [1]}, 'late_inverse_covariances': {'local': metric},
              'calibration': {'reference_passed': True, 'failure_reasons': []}}
    report = compare_candidate(val, val, np.zeros_like(val), frozen, metric, .8, np.full(32, .8), p)
    assert 'risk' in report['results']['local'] and 'invalid_reason' in report['results']['candidate']
    assert report['score'] is None and not report['paired_vs_candidate']


def test_complete_two_hop_stencil_reproduces_diffusion_baseline():
    from tasks.pion_projection.kernels import DiffusionKernel

    rng = np.random.default_rng(48)
    links = random_su3(rng, (3, 4, 4, 4))
    field = rng.normal(size=(4, 4, 4, 3, 5)) + 1j * rng.normal(size=(4, 4, 4, 3, 5))
    alpha = .2
    norm = (1 + 6 * alpha)**2
    terms = [{'path': path, 'weight': weight / norm} for path, weight in
             [([], 1 + 6*alpha**2), ([1], 12*alpha), ([1, 1], 6*alpha**2), ([1, 2], 24*alpha**2)]]
    expected = DiffusionKernel(links, [2], [1.], alpha).apply(field)
    np.testing.assert_allclose(build_kernel(links, {'terms': terms}).apply(field), expected, atol=1e-13)


def test_free_mass_distinguishes_a_clean_excitation_from_target_and_checks_reference():
    from tasks.pion_projection.common import protocol
    from tasks.pion_projection.experiment import pion_mass_check
    from tasks.pion_projection.statistics import bootstrap_indices, shape

    p = dict(protocol(), bootstrap_samples=48)
    rng = np.random.default_rng(409)
    noise = rng.normal(0, .003, (20, 1, 9))
    noise -= noise.mean(axis=0)
    vi = bootstrap_indices(len(noise), 48, 551)
    target = .8
    ref_draws = rng.normal(target, .001, 48)
    reference = {'reference_passed': True, 'failure_reasons': []}

    def check(mass, cal):
        values = shape(mass, np.arange(9), 16) * (1 + noise)
        return pion_mass_check(values, [1], target, ref_draws, vi, p, cal)

    matched = check(target, reference)
    assert matched['status'] == 'consistent_with_reference' and len(matched['fits']) == 2
    excited = check(1.2, reference)
    assert excited['status'] == 'unresolved'
    assert 'disagrees' in ' '.join(excited['reasons'])
    assert all(item['mass'] == pytest.approx(1.2) for item in excited['fits'])
    failed = check(target, {'reference_passed': False, 'failure_reasons': ['unstable reference']})
    assert failed['status'] == 'unresolved' and failed['reasons'] == ['unstable reference']


def test_custom_channel_score_is_withheld_even_with_consistent_mass(monkeypatch):
    from tasks.pion_projection import candidate
    from tasks.pion_projection.common import protocol
    from tasks.pion_projection.statistics import shape

    p = dict(protocol(), bootstrap_samples=32)
    noise = np.random.default_rng(32).normal(0, .005, (16, 1, 9))
    val = shape(.8, np.arange(9), 16) * (1 + noise - noise.mean(axis=0))
    metric = np.eye(3).tolist()
    frozen = {'submissions': {'local': [1]}, 'late_inverse_covariances': {'local': metric},
              'calibration': {'reference_passed': True, 'failure_reasons': []}}
    monkeypatch.setattr(candidate, 'nested_intervals', lambda *_: (np.ones((10, 2)), ['local', 'candidate']))
    args = (val, val, val, frozen, metric, .8, np.full(32, .8), p)
    report = candidate.compare_candidate(*args)
    assert report['pion_mass_check']['status'] == 'consistent_with_reference'
    assert report['pion_channel'] == 'custom_unverified' and report['score'] is None
    native = candidate.compare_candidate(*args, channel_by_construction=True)
    assert native['pion_channel'] == 'by_construction' and native['score'] == pytest.approx(100)
