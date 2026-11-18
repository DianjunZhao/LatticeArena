import numpy as np
import pytest

from tasks.pion_projection.common import protocol
from tasks.pion_projection.kernels import build_kernel
from tasks.pion_projection.statistics import blocks, bootstrap_indices, fold, risk, shape


def random_unitary(rng, shape_):
    a = rng.normal(size=(*shape_, 3, 3)) + 1j*rng.normal(size=(*shape_, 3, 3))
    q, _ = np.linalg.qr(a)
    q[..., :, 0] /= np.linalg.det(q)[..., None]
    return q


def test_kernel_covariance_linearity_hermiticity_and_translation():
    rng = np.random.default_rng(4)
    u = random_unitary(rng, (3, 3, 3, 3))
    g = random_unitary(rng, (3, 3, 3))
    x = rng.normal(size=(3, 3, 3, 3, 2)) + 1j*rng.normal(size=(3, 3, 3, 3, 2))
    y = rng.normal(size=x.shape) + 1j*rng.normal(size=x.shape)
    args = {'powers': [0, 2, 4], 'weights': [1, -2, .5], 'alpha': .2}
    k = build_kernel(u, args)
    np.testing.assert_allclose(k.apply(2*x-3j*y), 2*k.apply(x)-3j*k.apply(y), atol=1e-13)
    np.testing.assert_allclose(np.vdot(x, k.apply(y)), np.vdot(k.apply(x), y), atol=1e-12)
    ug = np.empty_like(u)
    for mu, axis in enumerate((2, 1, 0)):
        ug[mu] = g @ u[mu] @ np.roll(g, -1, axis=axis).swapaxes(-1, -2).conj()
    gx = g @ x
    np.testing.assert_allclose(build_kernel(ug, args).apply(gx), g @ k.apply(x), atol=1e-13)
    np.testing.assert_allclose(np.vdot(gx, build_kernel(ug, args).apply(gx)), np.vdot(x, k.apply(x)), atol=1e-12)
    np.testing.assert_allclose(build_kernel(np.roll(u, 1, axis=2), args).apply(np.roll(x, 1, axis=1)),
                               np.roll(k.apply(x), 1, axis=1), atol=1e-13)
    # Swap x and z and their link directions (cubic symmetry).
    ur = u[[2, 1, 0]].transpose(0, 3, 2, 1, 4, 5)
    np.testing.assert_allclose(build_kernel(ur, args).apply(x.transpose(2, 1, 0, 3, 4)),
                               k.apply(x).transpose(2, 1, 0, 3, 4), atol=1e-13)
    def reflect(a):
        for axis in range(3):
            a = np.take(a, (-np.arange(3)) % 3, axis=axis)
        return a
    up = np.array([reflect(np.roll(u[mu], 1, axis=axis)).swapaxes(-1, -2).conj()
                   for mu, axis in enumerate((2, 1, 0))])
    np.testing.assert_allclose(build_kernel(up, args).apply(reflect(x)), reflect(k.apply(x)), atol=1e-13)


def synthetic(excited=0.0, noise=0.01):
    rng = np.random.default_rng(9)
    f = shape(.8, np.arange(9))
    mean = f + excited*shape(1.5, np.arange(9))
    return (mean[None, :]+noise*f[None, :]*rng.normal(size=(30, 9)))[:, None, :]


def evaluate_synthetic(data, weight=1.0):
    p = protocol()
    b = blocks(data, 5)
    idx = bootstrap_indices(len(b), 500, 9)
    return risk(b, [weight], .8, np.full(500, .8), idx, p)


def test_risk_scaling_noise_and_excited_state():
    data = synthetic()
    a = evaluate_synthetic(data)
    for w in [-10, .001, 15]:
        assert evaluate_synthetic(data, w)['risk'] == pytest.approx(a['risk'], rel=1e-10)
    assert evaluate_synthetic(synthetic(noise=.1))['variance'] > a['variance']*50
    for amplitude in [2., -0.5]:
        assert evaluate_synthetic(synthetic(excited=amplitude))['departure_squared'] > a['departure_squared']*10


def test_invalid_inputs_and_folding():
    with pytest.raises(ValueError):
        evaluate_synthetic(synthetic(), weight=0)
    with pytest.raises(ValueError):
        evaluate_synthetic(synthetic()*np.nan)
    with pytest.raises(ValueError):
        blocks(np.zeros((16, 1, 9)), 5)
    a = np.arange(16)[None, :].astype(float)
    np.testing.assert_array_equal(fold(a), [[0, 8, 8, 8, 8, 8, 8, 8, 8]])
    with pytest.raises(ValueError):
        build_kernel(np.zeros((4, 3, 3, 3, 3, 3)), {'powers': [0], 'weights': [1], 'alpha': .2})


def test_reference_recovers_synthetic_cosh():
    from tasks.pion_projection.statistics import ReferenceFit
    p = protocol()
    rng = np.random.default_rng(18)
    f = shape(.8, np.arange(9))
    amplitudes = np.arange(1., 8.)
    data = amplitudes[None, :, None]*f[None, None, :]*(1+.005*rng.normal(size=(30, 7, 9)))
    b = blocks(data, 5)
    result, boot = ReferenceFit(b, p, [5, 6, 7, 8]).bootstrap(bootstrap_indices(6, 100, 18))
    assert abs(result['mass']-.8) < .003
    assert np.all(np.isfinite(boot)) and result['se'] > 0


def test_block_bootstrap_degenerate_outer_draw_is_not_dropped():
    from tasks.pion_projection.statistics import inverse_covariance
    p = protocol()
    b = blocks(synthetic(), 5)
    inv = inverse_covariance(b[:, 0, p['amplitude_window']])
    repeated = np.repeat(b[:1], 6, axis=0)
    r = risk(repeated, [1], .8, np.full(100, .8), bootstrap_indices(6, 100, 9), p,
             require_valid=False, late_inverse=inv)
    assert np.isfinite(r['risk'])


def test_development_cannot_reopen_after_validation(tmp_path):
    from tasks.pion_projection.experiment import develop
    (tmp_path/'validation.npz').touch()
    with pytest.raises(ValueError, match='Development is closed'):
        develop(tmp_path)


def test_zero_overlap_rejected_and_missing_rows_not_ignored(tmp_path):
    from tasks.pion_projection.common import fingerprint, load_data
    x = synthetic()
    x -= x.mean(axis=0)
    with pytest.raises(ValueError, match='Amplitude|amplitude'):
        evaluate_synthetic(x)
    np.savez(tmp_path/'development.npz', ids=np.arange(29), correlators=np.ones((29, 7, 16)),
             protocol_hash=fingerprint(protocol()))
    with pytest.raises(ValueError, match='missing or reordered'):
        load_data(tmp_path, 'development')


def test_reference_spec_freezes_kind_and_rejects_tampering():
    from tasks.pion_projection.reference import make_reference, reference_spec, verify_reference
    from tasks.pion_projection.statistics import ReferenceFit
    p = protocol()
    spec = reference_spec('single')
    assert verify_reference(spec) == 'single'
    with pytest.raises(ValueError):
        verify_reference({**spec, 'statistics_sha256': '0' * 64})
    with pytest.raises(ValueError):
        verify_reference(dict(spec, kind='twostate'))
    with pytest.raises(ValueError):
        reference_spec('nope')
    data = blocks(np.repeat(synthetic(), 7, axis=1), 5)
    assert isinstance(make_reference(data, p, [5, 6, 7, 8], 'single'), ReferenceFit)
    from tasks.pion_projection.reference_twostate import TwoStateFit
    assert isinstance(make_reference(data, p, [5, 6, 7, 8], 'twostate'), TwoStateFit)


def test_reflection_odd_is_temporal_extent_general():
    from tasks.pion_projection.experiment import reflection_odd
    for temporal in (16, 32):
        raw = np.arange(temporal, dtype=float)[None, None, :]
        odd = reflection_odd(raw)
        t = np.arange(1, temporal // 2)
        np.testing.assert_array_equal(odd[0, 0], raw[0, 0, t] - raw[0, 0, temporal - t])
        assert odd.shape[-1] == temporal // 2 - 1
    with pytest.raises(ValueError):
        reflection_odd(np.zeros((1, 1, 15)))


def test_two_state_fit_reports_parameters_and_condition():
    from tasks.pion_projection.reference_twostate import TwoStateFit
    from tasks.pion_projection.statistics import shape
    p = protocol()
    rng = np.random.default_rng(21)
    t = np.arange(16)
    data = np.zeros((30, 7, 16))
    for k in range(7):
        data[:, k] = (shape(.8, t) + .3*shape(1.4, t))[None, :]*(1 + .005*rng.normal(size=(30, 1)))
    b = blocks(data, 5)
    fit = TwoStateFit(b, p, [5, 6, 7, 8])
    full = fit.fit_full(fit.samples.mean(0))
    assert abs(full['mass'] - .8) < .02
    assert abs(full['gap'] - .6) < .1
    assert full['condition'] > 0 and np.isfinite(full['condition'])
    assert len(full['amplitudes']) == 2*len(p['reference_basis'])
    result, masses = fit.bootstrap(bootstrap_indices(len(b), 50, 0))
    assert result['mass2'] > result['mass'] and result['gap'] > 0
    assert masses.shape == (50,)


def test_verify_reference_rejects_missing_spec():
    from tasks.pion_projection.reference import verify_reference
    for spec in (None, {}, {'schema': 'other'}):
        with pytest.raises(ValueError, match='legacy|schema'):
            verify_reference(spec)


def test_improvement_certificate_accepts_only_real_improvements():
    from tasks.pion_projection.scoring import improvement_certificate
    rng = np.random.default_rng(3)
    base = np.exp(rng.normal(0, 0.05, 4000))
    good = base * np.exp(-0.5)
    bad = base * np.exp(0.2)
    risks = {'m1': {'local': base, 'good': good, 'bad': bad},
             'm2': {'local': base, 'good': good, 'bad': bad}}
    spec = {'schema': 'pion-score-v1', 'version': 'test', 'estimand': 'x',
            'baseline_id': 'local', 'alpha': 0.05,
            'comparison_family': {'candidates': 2, 'models': 2}, 'risk_floor': 0.0}
    out = improvement_certificate(risks, spec)
    assert out['status'] == 'certified'
    assert out['candidates']['good']['certified']
    assert not out['candidates']['bad']['certified']
    assert out['candidates']['good']['improvement_lower_bound'] > 1.4


def test_improvement_certificate_validates_spec_and_abstains_on_nan():
    from tasks.pion_projection.scoring import improvement_certificate, validate_spec
    with pytest.raises(ValueError, match='missing'):
        validate_spec({'schema': 'pion-score-v1'})
    with pytest.raises(ValueError, match='schema'):
        validate_spec({'schema': 'other', 'version': 'v', 'estimand': 'x', 'baseline_id': 'b',
                       'alpha': 0.05, 'comparison_family': {'candidates': 1, 'models': 1}})
    base = np.ones(100)
    bad = np.full(100, np.nan)
    spec = {'schema': 'pion-score-v1', 'version': 't', 'estimand': 'x', 'baseline_id': 'local',
            'alpha': 0.05, 'comparison_family': {'candidates': 1, 'models': 1},
            'invalid_tolerance': 0.01}
    out = improvement_certificate({'m': {'local': base, 'c': bad}}, spec)
    assert out['abstain'] and out['status'] == 'abstain'


def test_candidate_dependency_check(tmp_path, monkeypatch):
    from tasks.pion_projection.candidate import check_dependencies
    from tasks.pion_projection.common import digest
    helper = tmp_path / 'helper.py'
    helper.write_text('x = 1\n')
    monkeypatch.chdir(tmp_path)
    good = {'dependencies': {'helper.py': digest(helper)}}
    assert check_dependencies(good) == good['dependencies']
    helper.write_text('x = 2\n')
    with pytest.raises(ValueError, match='helper.py changed'):
        check_dependencies(good)
    assert check_dependencies({}) == {}


def test_gevp_recovers_a_two_state_matrix():
    from tasks.pion_projection.gevp import gevp_energies, summary, synthetic
    data = synthetic(nblocks=200, n_ops=3, m0=0.8, m1=1.4, seed=3, noise=0.01)
    rows = gevp_energies(data, t0=2, times=[5, 6, 7])
    result = summary(rows, state=0)
    assert abs(result['energy'] - 0.8) < 0.02
    assert result['se_boot'] > 0
    excited = summary(rows, state=1)
    assert abs(excited['energy'] - 1.4) < 0.1


def test_gevp_rejects_bad_matrices():
    from tasks.pion_projection.gevp import gevp_energies, synthetic
    data = synthetic(nblocks=4, n_ops=2, seed=4)
    with pytest.raises(ValueError, match='Hermitian'):
        gevp_energies(data * (1 + 0.1j), t0=2, times=[5])
    singular = data.copy()
    singular[..., 2] = 0.0
    with pytest.raises(ValueError, match='positive definite'):
        gevp_energies(singular, t0=2, times=[5])
    with pytest.raises(ValueError, match='nblocks'):
        gevp_energies(data[0], t0=2, times=[5])
