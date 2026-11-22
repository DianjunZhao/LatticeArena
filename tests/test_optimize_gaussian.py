import numpy as np
import pytest

from tasks.optimize_gaussian.features import dagger, directional_features, plaquettes, shift
from tasks.optimize_gaussian.kernels import apply_kernel, correlator
from tasks.optimize_gaussian.submission import build_kernel
from tasks.optimize_gaussian.train import features, gaussian


def su3(rng, shape):
    a = rng.normal(size=(*shape, 3, 3)) + 1j * rng.normal(size=(*shape, 3, 3))
    q, _ = np.linalg.qr(a)
    q[..., :, 0] /= np.linalg.det(q)[..., None]
    return q


def gauge_links(u, g):
    return np.stack([g @ u[d] @ dagger(shift(g, 1, d)) for d in range(3)])


def gauge_field(f, g):
    return np.einsum('...ij,...jn->...in', g, f)


def params(seed=0, steps=1, hidden=4):
    rng = np.random.default_rng(seed)
    return {'W': rng.normal(size=(hidden, 2)).tolist(),
            'theta': rng.normal(size=1 + hidden).tolist(),
            'steps': steps, 'alpha': 0.09090909}


def field(rng, latt=(4, 4, 4)):
    return rng.normal(size=(*latt, 3, 2)) + 1j * rng.normal(size=(*latt, 3, 2))


def test_shift_matches_roll_and_is_periodic():
    rng = np.random.default_rng(1)
    a = rng.normal(size=(4, 4, 4))
    for d, axis in ((0, 2), (1, 1), (2, 0)):
        np.testing.assert_array_equal(shift(a, 1, d), np.roll(a, -1, axis=axis))
        np.testing.assert_array_equal(shift(a, -1, d), np.roll(a, 1, axis=axis))
        np.testing.assert_array_equal(shift(shift(a, 1, d), -1, d), a)


def test_plaquettes_are_closed_and_gauge_invariant():
    rng = np.random.default_rng(2)
    latt = (4, 4, 4)
    u = su3(rng, (3, *latt))
    cold = np.broadcast_to(np.eye(3, dtype=complex), (3, *latt, 3, 3)).copy()
    np.testing.assert_allclose(plaquettes(cold), 1.0, atol=1e-13)
    g = su3(rng, latt)
    np.testing.assert_allclose(plaquettes(gauge_links(u, g)), plaquettes(u), atol=1e-12)
    # the loop must be closed: U_mu(x) U_nu(x+mu) U_mu^dag(x+nu) U_nu^dag(x)
    mu, nu = 0, 1
    loop = u[mu] @ shift(u[nu], 1, mu) @ dagger(shift(u[mu], 1, nu)) @ dagger(u[nu])
    np.testing.assert_allclose(plaquettes(u)[..., 0],
                               np.trace(loop, axis1=-2, axis2=-1).real / 3, atol=1e-12)


def test_kernel_is_hermitian_with_distinct_fields():
    rng = np.random.default_rng(3)
    u = su3(rng, (3, 4, 4, 4))
    f, g = field(rng), field(rng)
    a = rng.normal(size=(3, 4, 4, 4))
    np.testing.assert_allclose(np.vdot(g, apply_kernel(f, u, a)),
                               np.vdot(apply_kernel(g, u, a), f), atol=1e-12)


def test_kernel_is_gauge_covariant():
    rng = np.random.default_rng(4)
    latt = (4, 4, 4)
    u = su3(rng, (3, *latt))
    g = su3(rng, latt)
    f = field(rng)
    a = rng.normal(size=(3, *latt))
    np.testing.assert_allclose(apply_kernel(gauge_field(f, g), gauge_links(u, g), a),
                               gauge_field(apply_kernel(f, u, a), g), atol=1e-12)
    p = params(4, steps=2)
    np.testing.assert_allclose(build_kernel(gauge_links(u, g), p).apply(gauge_field(f, g)),
                               gauge_field(build_kernel(u, p).apply(f), g), atol=1e-12)


def test_kernel_cubic_symmetry():
    rng = np.random.default_rng(5)
    latt = (4, 4, 4)
    u = su3(rng, (3, *latt))
    f = field(rng)
    p = params(5, steps=1)
    swapped_u = u[[2, 1, 0]].transpose(0, 3, 2, 1, 4, 5)
    swapped_f = f.transpose(2, 1, 0, 3, 4)
    np.testing.assert_allclose(build_kernel(swapped_u, p).apply(swapped_f),
                               build_kernel(u, p).apply(f).transpose(2, 1, 0, 3, 4), atol=1e-12)


def test_linear_response_matches_direct_correlator():
    rng = np.random.default_rng(6)
    latt = (4, 4, 4)
    u = su3(rng, (3, *latt))
    f = field(rng)
    p = params(6, steps=2, hidden=4)
    W = np.asarray(p['W'])
    hidden = W.shape[0]
    base = gaussian(f, u, p['steps'], p['alpha'])
    zero = np.zeros((3, *latt))
    C0 = correlator(base, u, zero)
    Dc = correlator(base, u, np.ones((3, *latt))) - C0
    phi = features(u, W)
    Dh = [correlator(base, u, phi[:, ..., h]) - C0 for h in range(hidden)]
    theta = rng.normal(size=1 + hidden)
    a = np.full((3, *latt), theta[0])
    for h in range(hidden):
        a += theta[1 + h] * phi[:, ..., h]
    direct = correlator(base, u, a)
    linear = C0 + theta[0] * Dc + sum(theta[1 + h] * Dh[h] for h in range(hidden))
    np.testing.assert_allclose(linear, direct, atol=1e-11)


def test_features_are_gauge_invariant_and_zero_mean():
    rng = np.random.default_rng(7)
    latt = (4, 4, 4)
    u = su3(rng, (3, *latt))
    g = su3(rng, latt)
    W = np.asarray(params(7, hidden=3)['W'])
    np.testing.assert_allclose(features(gauge_links(u, g), W), features(u, W), atol=1e-11)
    phi = features(u, W)
    np.testing.assert_allclose(phi.mean(axis=(1, 2, 3)), 0.0, atol=1e-11)


def test_a1p_directional_pair_is_exchange_symmetric():
    rng = np.random.default_rng(8)
    latt = (4, 4, 4)
    u = su3(rng, (3, *latt))
    swapped = u[[0, 2, 1]].transpose(0, 2, 1, 3, 4, 5)
    f = directional_features(u).transpose(0, 2, 1, 3, 4)
    s = directional_features(swapped)
    # site axes are (z, y, x), so swapping y and z also transposes sites;
    # direction x sees (xy, xz), and the symmetric (sum, product) pair survives.
    np.testing.assert_allclose(f[0], s[0], atol=1e-12)
    np.testing.assert_allclose(f[1], s[2], atol=1e-12)
    np.testing.assert_allclose(f[2], s[1], atol=1e-12)


def test_invalid_shapes_are_rejected():
    with pytest.raises(Exception):
        apply_kernel(np.zeros((4, 4, 4, 3, 2)), np.zeros((2, 4, 4, 4, 3, 3)), np.zeros((3, 4, 4, 4)))


def test_basis_cache_rejects_identity_change(tmp_path):
    from tasks.optimize_gaussian.train import basis_key, load_basis, save_basis
    p = {'base_steps': 8, 'base_alpha': 0.09, 'hidden': 2}
    W = np.zeros((2, 2))
    key = basis_key(p, 7, W, [0, 1], [2, 3])
    save_basis(tmp_path / 'b.npz', key, np.zeros((2, 3, 4)), np.zeros((2, 3, 4)))
    load_basis(tmp_path / 'b.npz', key)
    for mutated in (basis_key(p, 8, W, [0, 1], [2, 3]),
                    basis_key(p, 7, W + 1, [0, 1], [2, 3]),
                    basis_key(p, 7, W, [0, 1], [2, 4]),
                    basis_key({**p, 'base_steps': 9}, 7, W, [0, 1], [2, 3]),
                    basis_key(p, 7, W, [0, 1], [2, 3], dependencies={'train.py': 'changed'}),
                    basis_key(p, 7, W, [0, 1], [2, 3], inputs={'gauge': {'0': 'changed'}})):
        with pytest.raises(ValueError, match='does not match'):
            load_basis(tmp_path / 'b.npz', mutated)
    np.savez(tmp_path / 'legacy.npz', C_fit=np.zeros(1), C_dev=np.zeros(1))
    with pytest.raises(ValueError, match='no identity record'):
        load_basis(tmp_path / 'legacy.npz', key)


def _cube_rotations():
    import itertools
    out = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            r = np.zeros((3, 3), dtype=int)
            for k, j in enumerate(perm):
                r[k, j] = signs[k]
            if round(np.linalg.det(r)) == 1:
                out.append(r)
    return out


def _transform(field_or_links, r, shift, dagger):
    n = field_or_links.shape[1]
    zz, yy, xx = np.indices((n, n, n))
    v = np.stack([xx, yy, zz], axis=-1)
    w = np.einsum('ij,...j->...i', np.linalg.inv(r), v).round().astype(int) % n
    idx = (w[..., 2], w[..., 1], w[..., 0])
    if field_or_links.ndim == 5:
        return field_or_links[idx]
    out = []
    for k in range(3):
        j = int(np.argmax(np.abs(r[k])))
        sign = int(r[k, j])
        src = field_or_links[j] if sign > 0 else dagger(shift(field_or_links[j], -1, j))
        out.append(src[idx])
    return np.stack(out)


def test_full_proper_cubic_group_covariance():
    from tasks.optimize_gaussian.features import dagger, shift
    rng = np.random.default_rng(11)
    latt = (4, 4, 4)
    u = su3(rng, (3, *latt))
    f = field(rng)
    p = params(11, steps=2)
    base = build_kernel(u, p).apply(f)
    for r in _cube_rotations():
        ug = _transform(u, r, shift, dagger)
        fg = _transform(f, r, shift, dagger)
        np.testing.assert_allclose(build_kernel(ug, p).apply(fg), _transform(base, r, shift, dagger), atol=1e-11)


def test_parity_covariance():
    from tasks.optimize_gaussian.features import dagger, shift
    rng = np.random.default_rng(12)
    latt = (4, 4, 4)
    u = su3(rng, (3, *latt))
    f = field(rng)
    p = params(12, steps=2)
    r = -np.eye(3, dtype=int)
    ug = _transform(u, r, shift, dagger)
    fg = _transform(f, r, shift, dagger)
    np.testing.assert_allclose(build_kernel(ug, p).apply(fg),
                               _transform(build_kernel(u, p).apply(f), r, shift, dagger), atol=1e-11)


def test_run_manifest_records_dependencies_and_ids(tmp_path):
    from tasks.optimize_gaussian.train import run_manifest
    p = {'geometry': [16, 16, 16, 16], 'base_steps': 8, 'base_alpha': 0.09}
    m = run_manifest(p, np.zeros((2, 2)), np.zeros(3), [0, 1], [2], [3], {0: 'a', 1: 'b', 2: 'c', 3: 'd'})
    assert m['schema'] == 'optgauss-run-v1'
    assert m['ids'] == {'fit': [0, 1], 'dev_val': [2], 'test': [3]}
    assert m['propagator_cache'] == {'0': 'a', '1': 'b', '2': 'c', '3': 'd'}
    assert set(m['dependencies']) == {
        'features.py', 'kernels.py', 'submission.py', 'solver_contract.py', 'train.py',
    }
    assert all(len(v) == 64 for v in m['dependencies'].values())
    assert len(m['statistics_sha256']) == 64


def test_submission_matches_linear_response_and_is_hermitian():
    from tasks.optimize_gaussian.kernels import correlator
    from tasks.optimize_gaussian.submission import build_kernel
    from tasks.optimize_gaussian.train import gaussian
    rng = np.random.default_rng(41)
    latt = (3, 4, 5)  # non-cubic on purpose
    u = su3(rng, (3, *latt))
    f, g = field(rng, latt), field(rng, latt)
    p = params(41, steps=1, hidden=3)
    W = np.asarray(p['W'])
    hidden = W.shape[0]
    base = gaussian(f, u, p['steps'], p['alpha'])
    zero = np.zeros((3, *latt))
    C0 = correlator(base, u, zero)
    Dc = correlator(base, u, np.ones((3, *latt))) - C0
    phi = features(u, W)
    Dh = [correlator(base, u, phi[:, ..., h]) - C0 for h in range(hidden)]
    cases = [('zero', np.zeros(1 + hidden)),
             ('c_only', np.array([0.3] + [0.0] * hidden)),
             ('one_v', np.array([0.0, 0.4] + [0.0] * (hidden - 1))),
             ('full', rng.normal(size=1 + hidden))]
    for label, theta in cases:
        a = np.full((3, *latt), theta[0])
        for h in range(hidden):
            a += theta[1 + h] * phi[:, ..., h]
        linear = C0 + theta[0] * Dc + sum(theta[1 + h] * Dh[h] for h in range(hidden))
        direct = correlator(base, u, a)
        np.testing.assert_allclose(linear, direct, rtol=0, atol=1e-10)
        spec = {**p, 'theta': theta.tolist()}
        submitted = complex(np.vdot(f, build_kernel(u, spec).apply(f)))
        np.testing.assert_allclose(submitted.real, direct, rtol=0, atol=1e-10)
        # full BCB Hermiticity with distinct fields
        np.testing.assert_allclose(np.vdot(g, build_kernel(u, spec).apply(f)),
                                   np.vdot(build_kernel(u, spec).apply(g), f), atol=1e-10)


def test_teacher_seven_power_basis_gap():
    from tasks.optimize_gaussian.teacher_check import teacher_result
    result = teacher_result(shape=(2, 2, 2), seed=7)
    assert result['hermiticity_H'] < 1e-12 and result['hermiticity_Q'] < 1e-12
    assert result['augmented_error'] < 1e-10
    assert result['seven_power_error'] > result['spectral_floor']


def test_p3_teacher_spectral_vs_augmented():
    from tasks.optimize_gaussian.p3_teacher import run
    result = run(shape=(2, 2, 2), seed=11, n_probe=16)
    assert result['status'] == 'PASS'
    rows = result['rows']
    assert rows[0]['spectral_test_error'] < 1e-10
    assert rows[-1]['spectral_test_error'] > 1e-3
    assert rows[-1]['augmented_test_error'] < 1e-10


def test_validate_inputs_status(tmp_path, monkeypatch):
    import json
    import numpy as np
    from tasks.optimize_gaussian import train
    gauge = tmp_path / 'wilson_b6.7'
    gauge.write_bytes(b'gauge')
    cache_dir = tmp_path / 'props'
    cache_dir.mkdir()
    prop = cache_dir / 'k.npy'
    np.save(prop, np.zeros(3, dtype=np.complex128))
    import hashlib
    (cache_dir / 'k.json').write_text(json.dumps(
        {'array_sha256': hashlib.sha256(prop.read_bytes()).hexdigest(),
         'keydata': {'gauge': hashlib.sha256(gauge.read_bytes()).hexdigest(), 'residual_max': 1e-12,
                     'geometry': [4, 4, 4, 8], 'boundary': -1, 'tol': 1e-10, 'maxiter': 10000}}))
    monkeypatch.chdir(tmp_path)
    (tmp_path / '.cache/pion_projection/propagators').mkdir(parents=True)
    prop2 = tmp_path / '.cache/pion_projection/propagators/k.npy'
    prop2.write_bytes(prop.read_bytes())
    (prop2.with_suffix('.json')).write_text((cache_dir / 'k.json').read_text())
    p = {'ensemble': str(tmp_path), 'tolerance': 1e-10, 'geometry': [4, 4, 4, 8],
         't_boundary': -1, 'max_iterations': 10000}
    row = train.validate_inputs(p, [7], {7: 'k'})['7']
    assert row['status'] == 'verified' and row['gauge'] and row['propagator']
    assert row['geometry'] and row['boundary'] and row['precision']
    bad = dict(p, geometry=[8, 8, 8, 8])
    with pytest.raises(ValueError, match='protocol mismatch'):
        train.validate_inputs(bad, [7], {7: 'k'})
    # missing protocol fields cannot be verified
    meta = json.loads((tmp_path / '.cache/pion_projection/propagators/k.json').read_text())
    meta['keydata'].pop('geometry')
    (tmp_path / '.cache/pion_projection/propagators/k.json').write_text(json.dumps(meta))
    assert train.validate_inputs(p, [7], {7: 'k'}, trusted=False)['7']['status'] == 'archived_diagnostic'
    # over-residual is refused at the trusted entry, degraded when diagnostic
    meta['keydata']['geometry'] = [4, 4, 4, 8]
    meta['keydata']['residual_max'] = 1.0
    (tmp_path / '.cache/pion_projection/propagators/k.json').write_text(json.dumps(meta))
    with pytest.raises(ValueError, match='residual'):
        train.validate_inputs(p, [7], {7: 'k'})
    assert train.validate_inputs(p, [7], {7: 'k'}, trusted=False)['7']['status'] == 'archived_diagnostic'
    # reference identity binds the actually consumed bootstrap file
    ref = tmp_path / 'reference_bootstrap.npz'
    np.savez(ref, masses=np.zeros(3))
    identity = train.reference_identity(dict(p, reference_bootstrap=str(ref)), [7], {7: 'k'})
    assert identity['reference_bootstrap_digest'] is not None and identity['status'] == 'verified'


def test_validate_inputs_uses_hash_bound_pion_propagator_receipt(tmp_path, monkeypatch):
    import hashlib
    import json
    import numpy as np
    from tasks.optimize_gaussian import train

    ensemble = tmp_path / 'ensemble'
    ensemble.mkdir()
    gauge = ensemble / 'wilson_b6.7'
    gauge.write_bytes(b'gauge bytes')
    gauge_sha = hashlib.sha256(gauge.read_bytes()).hexdigest()
    prop_dir = tmp_path / '.cache/pion_projection/propagators'
    prop_dir.mkdir(parents=True)
    prop = prop_dir / 'cachekey.npy'
    np.save(prop, np.zeros(4, dtype=np.complex128))
    prop_sha = hashlib.sha256(prop.read_bytes()).hexdigest()
    (prop.with_suffix('.json')).write_text(json.dumps({
        'array_sha256': prop_sha,
        'keydata': {'gauge': gauge_sha, 'geometry': [4, 4, 4, 8], 'boundary': -1,
                    'tol': 1e-10, 'maxiter': 10000, 'kappa': 0.14,
                    'source': [0, 0, 0, 0]},
    }))
    measurement = tmp_path / 'development.npz'
    np.savez(measurement, ids=np.array([7]), generation=np.array('generation-1'),
             protocol_hash=np.array('protocol-1'), correlators=np.zeros((1, 1, 8)))
    provenance = tmp_path / 'development_provenance.json'
    provenance.write_text(json.dumps({
        'generation': 'generation-1', 'protocol_hash': 'protocol-1',
        'records': [{'id': 7, 'cache_key': 'cachekey', 'gauge_sha256': gauge_sha,
                     'propagator_sha256': prop_sha, 'residual_max': 1e-12,
                     'trajectory_id': 17}],
    }))
    file_sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    spec = {'measurement_path': str(measurement), 'measurement_sha256': file_sha(measurement),
            'provenance_path': str(provenance), 'provenance_sha256': file_sha(provenance),
            'generation': 'generation-1', 'protocol_hash': 'protocol-1'}
    p = {'ensemble': str(ensemble), 'geometry': [4, 4, 4, 8], 't_boundary': -1,
         'tolerance': 1e-10, 'max_iterations': 10000, 'kappa': 0.14,
         'source': [0, 0, 0, 0], 'propagator_measurement_receipt': spec}
    monkeypatch.chdir(tmp_path)

    row = train.validate_inputs(p, [7], {7: 'cachekey'})['7']
    assert row['status'] == 'verified'
    assert row['residual'] == 1e-12 and row['trajectory_id'] == 17
    assert row['gauge'] and row['propagator'] and row['kappa'] and row['source']

    with pytest.raises(ValueError, match='cfg 8: missing from the bound Pion measurement receipt'):
        train.validate_inputs(p, [7, 8], {7: 'cachekey', 8: 'unreceipted'})

    provenance_doc = json.loads(provenance.read_text())
    provenance_doc['records'][0].pop('residual_max')
    provenance.write_text(json.dumps(provenance_doc))
    spec['provenance_sha256'] = file_sha(provenance)
    with pytest.raises(ValueError, match='cfg 7 is missing .*residual_max'):
        train.validate_inputs(p, [7], {7: 'cachekey'})

    provenance.write_text(provenance.read_text() + ' ')
    with pytest.raises(ValueError, match='provenance hash'):
        train.validate_inputs(p, [7], {7: 'cachekey'})


def test_optimize_output_directory_refuses_existing_and_limits_resume(tmp_path):
    from tasks.optimize_gaussian.artifacts import prepare_output_directory

    output = tmp_path / 'run'
    assert prepare_output_directory(output) == output
    cache = output / 'basis_s20261120.npz'
    cache.write_bytes(b'cache')
    is_basis = lambda child: child.name.startswith('basis_s') and child.suffix == '.npz'
    assert prepare_output_directory(output, resume=True, allowed_existing=is_basis) == output
    with pytest.raises(FileExistsError, match='choose a new run path'):
        prepare_output_directory(output)

    (output / 'results.json').write_text('{"complete": true}')
    with pytest.raises(FileExistsError, match='non-resumable outputs'):
        prepare_output_directory(output, resume=True, allowed_existing=is_basis)


def test_train_main_refuses_historical_output_before_loading_inputs(tmp_path, monkeypatch):
    from tasks.optimize_gaussian import train

    output = tmp_path / 'existing_v9'
    output.mkdir()
    result_path = output / 'results.json'
    result_path.write_text('{"old": true}')
    monkeypatch.setattr(train, 'protocol', lambda: {'output': str(output), 'seeds': [1]})
    with pytest.raises(SystemExit) as exc:
        train.main([])
    assert exc.value.code == 2
    assert result_path.read_text() == '{"old": true}'


def test_unified_main_refuses_existing_output_before_loading_data(tmp_path):
    from tasks.optimize_gaussian import unified

    output = tmp_path / 'existing_package_b'
    output.mkdir()
    result_path = output / 'unified.json'
    result_path.write_text('{"old": true}')
    with pytest.raises(FileExistsError, match='choose a new run path'):
        unified.main(output)
    assert result_path.read_text() == '{"old": true}'


def test_crosslink_target_and_oracle():
    import numpy as np
    from tasks.optimize_gaussian.p3_crosslink import B_of, H_of, samples, su3, target
    rng = np.random.default_rng(2)
    links = su3(rng, 0.1) @ su3(rng, 0.5)
    h, b = H_of(links, (1, 1, 1, 1)), B_of(links, (1, 1, 1, 1))
    q = target(h, b, 0.0)
    assert np.linalg.norm(q - q.conj().T) < 1e-12 and abs(np.trace(q)) < 1e-12
    assert np.linalg.norm(q - (h @ h - np.trace(h @ h) / 3 * np.eye(3))) < 1e-12
    X, Y = samples(rng, links, 100, 0.1, augmented=True)
    assert X.shape[1] == 72 + 27 and Y.shape[1] == 9


def test_unified_estimator_amplitude_sources():
    import numpy as np
    from tasks.optimize_gaussian.unified import risk_with_fixed_amplitude
    rng = np.random.default_rng(0)
    t = np.arange(9)
    data = np.ones((6, 3, 9)) * (np.exp(-0.5 * t) + np.exp(-0.5 * (8 - t)))
    data *= 1 + 0.01 * rng.normal(size=data.shape)
    p = {'amplitude_window': [6, 7, 8], 'score_window': [2, 3, 4, 5], 'geometry': [4, 4, 4, 8],
         'covariance_shrinkage': 0.1}
    idx = np.array([[0, 1, 2], [3, 4, 5]])
    train = risk_with_fixed_amplitude(data, np.ones(3), 0.5, np.full(2, 0.5), idx, p, 1.0, 0.01,
                                      amplitude_source='train')
    test = risk_with_fixed_amplitude(data, np.ones(3), 0.5, np.full(2, 0.5), idx, p, 1.0, 0.01,
                                     amplitude_source='test')
    assert train['late_covariance_source'] == 'train' and train['amplitude'] == 1.0
    assert test['late_covariance_source'] == 'test'
    assert np.isfinite(train['risk']) and np.isfinite(test['risk'])


def test_estimator_regression_runs(tmp_path):
    from tasks.optimize_gaussian.estimator_regression import run
    result = run(n_dataset=5, n_boot=20, out=tmp_path, make_plot=False)
    assert set(result['summary']) == {'train_frozen', 'validation_refit'}
    assert abs(result['summary']['train_frozen']['bias_mean']) < 1e-2


def test_fit_state_stress_separates_reference_shape_from_interval_coverage():
    from tasks.optimize_gaussian.estimator_regression_stress import _q_target
    correct = _q_target(0.8, 0.5)
    wrong = _q_target(0.8, 0.55)
    np.testing.assert_allclose(correct, np.full(4, 1.25), rtol=1e-12, atol=1e-12)
    assert np.ptp(wrong) > 0.1
    assert np.sqrt(np.mean((wrong - 1) ** 2)) > 0.4


def test_crosslink_fairness_matches_sites_and_real_oracle():
    from tasks.optimize_gaussian.p3_crosslink_fair import attributes, run
    result = run(seed=2, epsilon=0.05, n_train=8, n_test=5,
                 n_train_configurations=2, n_test_configurations=2)
    assert len(result['train_probe_indices']) == 2
    assert all(len(x) == 8 for x in result['train_probe_indices'])
    assert all(len(x) == 5 for x in result['test_probe_indices'])
    assert len(result['probe_hashes']['train'][0]) == 64
    for klass in ('A_spectral', 'B_nested'):
        oracle = result['classes'][klass]['oracle']
        assert oracle['feasible']
        assert oracle['coefficient_domain'] == [-5.0, 5.0]
        assert all(np.isreal(oracle['coefficients']))
    assert result['classes']['B_nested']['oracle']['test_error'] < 1e-10
    checks = attributes()
    assert max(checks[key] for key in ('gauge_covariance_h', 'gauge_covariance_b',
                                       'gauge_covariance_q')) < 1e-10


def test_adapt_instance_contract_and_search():
    from tasks.optimize_gaussian.adapt import contract_checks, search_theta
    import numpy as np
    rng = np.random.default_rng(0)
    checks = contract_checks(rng)
    assert all(checks['contract'][k] for k in ('linear_in_field', 'hermitian', 'identity_at_theta0'))
    info = search_theta(rng)
    assert info['accepted'] == 3 and info['rejected'] == 1


@pytest.mark.parametrize('value', [None, float('nan'), float('inf'), -float('inf')])
def test_optimize_search_rejects_nonfinite_results(value):
    from core.search import Budget, search

    budget = Budget(1)
    result = search([('invalid', 0)], lambda _: value, budget=budget)
    assert result.best() is None and result.evaluations == 0
    assert budget.used == 1
    assert result.rejected[0]['reason'] == 'non-finite evaluation result'


def test_optimize_search_budget_counts_rejections_and_stops_evaluator():
    from core.search import Budget, search

    calls = []

    def evaluate(candidate):
        calls.append(candidate)
        raise ValueError('solver failed before returning a risk')

    budget = Budget(2)
    result = search([('invalid', -1), ('failure', 0), ('unvisited', 1)], evaluate,
                    validate=lambda x: (x >= 0, 'invalid candidate'), budget=budget)
    assert calls == [0] and budget.used == 2
    assert result.budget_exhausted and result.evaluations == 0
    assert [row['source'] for row in result.rejected] == ['invalid', 'failure']
    assert 'solver failed' in result.rejected[1]['reason']
    empty = search([('unvisited', 2)], evaluate, budget=Budget(0))
    assert empty.budget_exhausted and not empty.accepted and not empty.rejected
    assert calls == [0]


@pytest.mark.parametrize('mode', ['budget', 'nonconverged', 'large_residual_success'])
def test_optimize_solver_diagnostic_keeps_stop_reason_without_search_gate(monkeypatch, mode):
    """Characterize the current gap: a scalar finite risk is not a solver gate."""
    from types import SimpleNamespace
    from core.search import search
    from tasks.optimize_gaussian import cpu_convergence_diagnostic as diagnostic

    def fake_minimize(objective, start, **kwargs):
        objective(start)
        if mode == 'budget':
            objective(start)  # hard cap=1 must stop this second objective call
        return SimpleNamespace(success=mode == 'large_residual_success',
                               message='controlled solver status')

    monkeypatch.setattr(diagnostic, 'minimize', fake_minimize)
    X, Y = np.eye(2), np.ones(2)
    row = diagnostic._solver_trial(X, Y, 'SLSQP', np.zeros(2), 1,
                                   np.ones(2), X, Y, 2.0)
    assert row['objective_calls'] == 1 and row['feasible']
    assert row['budget_exhausted'] == (mode == 'budget')
    assert row['solver_success'] == (mode == 'large_residual_success')
    assert row['projected_gradient_norm_scaled_variables'] > 1e-5
    if mode == 'budget':
        assert row['solver_message'] == 'objective_evaluation_budget_exhausted'
    # The generic API consumes only the evaluator's scalar, not solver metadata.
    result = search([('diagnostic_only', row)], lambda r: r['test_error'])
    assert result.evaluations == 1 and not result.rejected
    assert result.accepted[0]['candidate'] is row


def test_optimize_paired_draw_identity_and_ordered_basis_ids(tmp_path):
    from core.comparator import check_draws
    from tasks.optimize_gaussian.train import basis_key, load_basis, save_basis

    risks = {'baseline': np.array([1., 2., 3.]), 'candidate': np.array([.9, 1.8, 2.7])}
    _, identity = check_draws(risks, draw_ids=[10, 11, 12])
    _, reordered = check_draws(risks, draw_ids=[12, 11, 10])
    assert identity != reordered
    with pytest.raises(ValueError, match='duplicates'):
        check_draws(risks, draw_ids=[10, 10, 12])
    with pytest.raises(ValueError, match='same length'):
        check_draws(risks, draw_ids=[10, 11])
    with pytest.raises(ValueError, match='different lengths'):
        check_draws({**risks, 'candidate': np.ones(2)}, draw_ids=[10, 11, 12])

    p = {'base_steps': 8, 'base_alpha': .09, 'hidden': 2}
    W = np.zeros((2, 2))
    key = basis_key(p, 7, W, [0, 1], [2, 3], inputs={}, dependencies={})
    cache = tmp_path / 'ordered_basis.npz'
    save_basis(cache, key, np.zeros((2, 3, 4)), np.zeros((2, 3, 4)))
    for fit_ids, dev_ids in (([1, 0], [2, 3]), ([0, 1], [3, 2])):
        changed = basis_key(p, 7, W, fit_ids, dev_ids, inputs={}, dependencies={})
        with pytest.raises(ValueError, match='does not match'):
            load_basis(cache, changed)


@pytest.mark.parametrize('success', [True, False])
def test_optimize_powell_receipt_records_status_without_gating(monkeypatch, success):
    from types import SimpleNamespace
    from tasks.optimize_gaussian import train

    p = {'hidden': 2, 'v_max': 2.0, 'optimizer': {'maxiter': 9}}
    monkeypatch.setattr(train, 'correlators', lambda C, theta, H: theta)
    monkeypatch.setattr(train, 'risk_of', lambda p, theta, masses: float(theta @ theta))
    final = np.array([-2., 2., np.nextafter(2., 0.)])

    def fake_minimize(objective, start, method, bounds, options):
        np.testing.assert_array_equal(start, np.zeros(3))
        assert method == 'Powell' and bounds == [(-2., 2.)] * 3
        assert options == {'maxiter': 9}
        assert objective(np.array([1., 2., 0.])) == 5.5  # original risk + L2
        value = objective(final)
        # Deliberately distinct: the receipt must retain both observed calls and nfev.
        return SimpleNamespace(x=final, fun=value, nfev=7, nit=4, success=success,
                               status=0 if success else 2, message='controlled termination')

    monkeypatch.setattr(train, 'minimize', fake_minimize)
    fit = train.optimize(None, p, None, .25)
    assert fit['theta'] == final.tolist() and fit['nfit'] == 7
    assert fit['risk'] == float(final @ final) + .25 * np.mean(final[1:] ** 2)
    receipt = fit['optimizer_receipt']
    assert receipt['classification'] == 'diagnostic_only'
    assert receipt['success'] is success and receipt['status'] == (0 if success else 2)
    assert receipt['message'] == 'controlled termination'
    assert receipt['nfev'] == 7 and receipt['nit'] == 4 and receipt['objective_calls'] == 2
    assert receipt['elapsed_seconds'] >= 0 and receipt['maxiter'] == 9
    assert receipt['lower_bound_hit_indices'] == [0]
    assert receipt['upper_bound_hit_indices'] == [1]  # near-bound theta[2] is not a hit
    assert receipt['out_of_bounds_indices'] == []
    assert receipt['nonfinite_objective_calls'] == receipt['nonfinite_parameter_calls'] == 0
    assert receipt['final_objective_finite'] and receipt['final_theta_finite']
    assert receipt['box_kkt_diagnostic']['classification'] == 'diagnostic_only'
    assert receipt['box_kkt_diagnostic']['status'] == 'computed'
    assert receipt['box_kkt_diagnostic']['threshold'] is None
    assert receipt['box_kkt_diagnostic']['objective_evaluations_completed'] == 4
    assert len(receipt['objective_trace']) == 2
    assert [row['index'] for row in receipt['objective_trace']] == [1, 2]


def test_box_kkt_diagnostic_measures_interior_stationarity_separately():
    from tasks.optimize_gaussian.train import box_kkt_diagnostic

    target = np.array([.25, -.75])
    calls = []

    def objective(x):
        calls.append(x.copy())
        return float(np.sum((x - target) ** 2))

    receipt = box_kkt_diagnostic(objective, target, [(-2., 2.), (-2., 2.)])
    assert receipt['status'] == 'computed'
    np.testing.assert_allclose(receipt['gradient'], [0., 0.], atol=1e-9)
    assert receipt['kkt_violation_inf'] < 1e-9
    assert receipt['finite_difference_methods'] == ['central', 'central']
    assert receipt['objective_evaluations_attempted'] == len(calls) == 5


@pytest.mark.parametrize(
    'point,target,expected_sign,active_key,method,expected_violation',
    [
        ([0.], [-1.], 1, 'lower_active_indices', 'forward', 0.),
        ([0.], [1.], -1, 'lower_active_indices', 'forward', 2.),
        ([2.], [3.], -1, 'upper_active_indices', 'backward', 0.),
        ([2.], [1.], 1, 'upper_active_indices', 'backward', 2.),
    ],
)
def test_box_kkt_diagnostic_uses_correct_box_boundary_signs(
        point, target, expected_sign, active_key, method, expected_violation):
    from tasks.optimize_gaussian.train import box_kkt_diagnostic

    target = np.asarray(target, dtype=float)
    receipt = box_kkt_diagnostic(
        lambda x: float(np.sum((x - target) ** 2)), point, [(0., 2.)],
    )
    assert receipt['status'] == 'computed'
    assert receipt[active_key] == [0]
    assert receipt['finite_difference_methods'] == [method]
    assert int(np.sign(receipt['gradient'][0])) == expected_sign
    assert receipt['kkt_violation_inf'] == pytest.approx(expected_violation, abs=5e-5)


def test_box_kkt_diagnostic_reports_probe_failure_without_a_gate():
    from tasks.optimize_gaussian.train import box_kkt_diagnostic

    nonfinite = box_kkt_diagnostic(lambda x: float('nan'), [0.], [(-1., 1.)])
    assert nonfinite['status'] == 'nonfinite_probe'
    assert 'kkt_violation_inf' not in nonfinite
    failure = box_kkt_diagnostic(
        lambda x: (_ for _ in ()).throw(RuntimeError('controlled probe failure')),
        [0.], [(-1., 1.)],
    )
    assert failure['status'] == 'probe_exception'
    assert failure['exception']['message'] == 'controlled probe failure'
    assert 'kkt_violation_inf' not in failure


def test_optimize_powell_receipt_keeps_nonfinite_observations(monkeypatch):
    import json
    from types import SimpleNamespace
    from tasks.optimize_gaussian import train

    monkeypatch.setattr(train, 'correlators', lambda C, theta, H: theta)
    monkeypatch.setattr(train, 'risk_of', lambda *args: float('nan'))

    def fake_minimize(objective, start, **kwargs):
        assert np.isnan(objective(np.zeros(2)))
        assert np.isnan(objective(np.array([float('nan'), 0.])))
        return SimpleNamespace(x=np.array([float('nan'), 3.]), fun=float('inf'),
                               success=False, message='non-finite result', nfev=2)

    monkeypatch.setattr(train, 'minimize', fake_minimize)
    fit = train.optimize(None, {'hidden': 1, 'v_max': 2., 'optimizer': {'maxiter': 3}}, None, 0.)
    receipt = fit['optimizer_receipt']
    assert np.isinf(fit['risk']) and np.isnan(fit['theta'][0])  # reporting leaves legacy values alone
    assert receipt['nonfinite_objective_calls'] == 2 and receipt['nonfinite_parameter_calls'] == 1
    assert not receipt['final_objective_finite'] and not receipt['final_theta_finite']
    assert receipt['out_of_bounds_indices'] == [1]
    assert receipt['status'] is None and receipt['nit'] is None
    assert [row['value'] for row in receipt['objective_trace']] == ['nan', 'nan']
    assert all(row['best_so_far'] is None and not row['finite'] for row in receipt['objective_trace'])
    json.dumps(receipt, allow_nan=False)


def test_optimize_powell_trace_preserves_values_and_finite_best_so_far(monkeypatch):
    import json
    from types import SimpleNamespace
    from tasks.optimize_gaussian import train

    values = [float('nan'), float('inf'), 5., 8., -float('inf'), 3., 3., float('nan')]
    remaining = iter(values)
    monkeypatch.setattr(train, 'correlators', lambda C, theta, H: theta)
    monkeypatch.setattr(train, 'risk_of', lambda *args: next(remaining))

    def fake_minimize(objective, start, **kwargs):
        observed = [objective(np.zeros(2)) for _ in values]
        np.testing.assert_array_equal(observed, values)  # optimizer sees original NaN/Inf unchanged
        # Return the last observed nonfinite fun; best-so-far is only a diagnostic.
        return SimpleNamespace(x=np.zeros(2), fun=observed[-1], nfev=len(values),
                               nit=1, success=False, message='controlled mixed trace')

    monkeypatch.setattr(train, 'minimize', fake_minimize)
    fit = train.optimize(None, {'hidden': 1, 'v_max': 2., 'optimizer': {'maxiter': 3}}, None, 0.)
    assert np.isnan(fit['risk']) and fit['theta'] == [0., 0.] and fit['nfit'] == 8
    receipt = fit['optimizer_receipt']
    trace = receipt['objective_trace']
    assert len(trace) == receipt['objective_calls'] == len(values)
    assert [row['index'] for row in trace] == list(range(1, 9))
    assert [row['value'] for row in trace] == ['nan', 'inf', 5., 8., '-inf', 3., 3., 'nan']
    assert [row['finite'] for row in trace] == [False, False, True, True, False, True, True, False]
    assert [row['best_so_far'] for row in trace] == [None, None, 5., 5., 5., 3., 3., 3.]
    best = [row['best_so_far'] for row in trace if row['best_so_far'] is not None]
    assert np.all(np.diff(best) <= 0)
    elapsed = [row['elapsed_seconds'] for row in trace]
    assert 0 <= elapsed[0] <= elapsed[-1] <= receipt['elapsed_seconds']
    assert np.all(np.diff(elapsed) >= 0)
    assert receipt['nonfinite_objective_calls'] == 4
    json.dumps(receipt, allow_nan=False)


@pytest.mark.parametrize('source', ['minimize', 'loss'])
def test_optimize_powell_without_run_context_reraises_solver_or_loss_exception(monkeypatch, source):
    from tasks.optimize_gaussian import train

    failure = RuntimeError('controlled exception; no result receipt')
    monkeypatch.setattr(train, 'correlators', lambda C, theta, H: theta)

    def failed_risk(*args):
        raise failure

    def fake_minimize(objective, start, **kwargs):
        if source == 'loss':
            objective(start)
        raise failure

    monkeypatch.setattr(train, 'risk_of', failed_risk)
    monkeypatch.setattr(train, 'minimize', fake_minimize)
    with pytest.raises(RuntimeError) as caught:
        train.optimize(None, {'hidden': 1, 'v_max': 2., 'optimizer': {'maxiter': 3}}, None, 0.)
    assert caught.value is failure


def _standin_train_main(tmp_path, monkeypatch):
    import json
    from tasks.optimize_gaussian import train

    # Only temporary stand-ins: do not load archived measurements or initialize GPU.
    dev, val, masses = tmp_path / 'dev.json', tmp_path / 'val.json', tmp_path / 'masses.npz'
    dev.write_text(json.dumps({'records': [{'id': 0, 'cache_key': 'fit'},
                                         {'id': 1, 'cache_key': 'dev'}]}))
    val.write_text(json.dumps({'records': [{'id': 2, 'cache_key': 'test'}]}))
    np.savez(masses, masses=np.array([.5]))
    out = tmp_path / 'new-run'
    p = {'output': str(out), 'seeds': [4], 'cache_manifest': str(dev),
         'validation_manifest': str(val), 'reference_bootstrap': str(masses),
         'fit': [0, 0], 'dev_val': [1, 1], 'test': [2, 2], 'hidden': 1,
         'base_steps': 8, 'l2_grid': [0., .1], 'v_max': 2., 'optimizer': {'maxiter': 3}}
    monkeypatch.setattr(train, 'protocol', lambda: p)
    monkeypatch.setattr(train, 'basis_key', lambda *args, **kwargs: {'temporary': True})
    monkeypatch.setattr(train, 'collect', lambda *args: np.zeros((1, 3, 16)))
    monkeypatch.setattr(train, 'correlators', lambda *args: np.zeros((1, 16)))
    monkeypatch.setattr(train, 'risk_of', lambda *args: 1.)
    monkeypatch.setattr(train, 'evaluate', lambda *args: np.zeros((1, 16)))
    monkeypatch.setattr(train, 'q_curve', lambda *args: np.zeros(16))
    monkeypatch.setattr(train, 'coefficient_map', lambda *args: np.zeros(1))
    monkeypatch.setattr(train, 'run_manifest', lambda *args: {'temporary': True})
    return train, p, out


def test_train_main_preserves_each_optimizer_receipt_in_new_output(tmp_path, monkeypatch):
    import json

    train, p, out = _standin_train_main(tmp_path, monkeypatch)
    receipts = []

    def fit_stub(C, p, masses, lam2, *, failure_context=None):
        assert failure_context['seed'] == 4 and failure_context['lam2'] == lam2
        receipt = {'classification': 'diagnostic_only', 'success': bool(lam2), 'message': str(lam2),
                   'objective_trace': [{'index': 1, 'elapsed_seconds': .01, 'value': 1.,
                                        'finite': True, 'best_so_far': 1.}]}
        receipts.append(receipt)
        return {'risk': 1., 'theta': [0., 0.], 'nfit': 2, 'optimizer_receipt': receipt}

    monkeypatch.setattr(train, 'optimize', fit_stub)
    train.main([])
    saved = json.loads((out / 'results.json').read_text())
    assert [row['optimizer_receipt'] for row in saved['grid']] == receipts
    assert saved['best']['optimizer_receipt'] == receipts[0]  # status does not alter selection
    assert saved['best']['lam2'] == 0. and saved['grid'][0]['nfit'] == 2
    assert not (out / 'optimizer_failure.json').exists()


def test_optimize_accepts_only_after_counted_kkt_probe(monkeypatch):
    from types import SimpleNamespace
    from tasks.optimize_gaussian import train
    from tasks.optimize_gaussian.solver_contract import SolverPolicy

    p = {'hidden': 1, 'v_max': 2., 'optimizer': {'maxiter': 3}}
    monkeypatch.setattr(train, 'correlators', lambda _C, theta, _H: theta)
    monkeypatch.setattr(train, 'risk_of', lambda _p, _theta, _masses: 0.)

    def fake_minimize(objective, start, **_kwargs):
        np.testing.assert_array_equal(start, np.zeros(2))
        value = objective(np.zeros(2))
        return SimpleNamespace(x=np.zeros(2), fun=value, nfev=1, nit=1,
                               success=True, status=0, message='fixture converged')

    monkeypatch.setattr(train, 'minimize', fake_minimize)
    fit = train.optimize(
        None, p, None, 0.,
        solver_policy=SolverPolicy(20, 5., 'kkt_residual', 1e-8),
        config_id={'seed': 17, 'lam2': 0.},
    )

    contract = fit['optimizer_receipt']['solver_contract']
    assert contract['gate_status'] == 'contract_accepted'
    assert contract['objective_calls'] == 7  # solver + final reevaluation + five KKT probes
    assert [row['phase'] for row in contract['objective_trace']].count('residual_diagnostic') == 5
    assert fit['optimizer_receipt']['box_kkt_diagnostic']['status'] == 'computed'


def test_train_main_rejected_solver_contract_stops_before_candidate_scoring(tmp_path, monkeypatch):
    import hashlib
    import json
    from types import SimpleNamespace
    from tasks.optimize_gaussian import train

    out = tmp_path / 'rejected-run'
    dev = tmp_path / 'dev.json'
    val = tmp_path / 'val.json'
    masses = tmp_path / 'masses.npz'
    dev.write_text(json.dumps({'records': [{'id': 0, 'cache_key': 'fit'}]}))
    val.write_text(json.dumps({'records': [
        {'id': 1, 'cache_key': 'dev'}, {'id': 2, 'cache_key': 'test'},
    ]}))
    np.savez(masses, masses=np.array([.5]))
    protocol = {
        'output': str(out), 'seeds': [17], 'cache_manifest': str(dev),
        'validation_manifest': str(val), 'reference_bootstrap': str(masses),
        'fit': [0, 0], 'dev_val': [1, 1], 'test': [2, 2], 'hidden': 1,
        'base_steps': 1, 'l2_grid': [0.], 'v_max': 2.,
        'optimizer': {
            'maxiter': 3,
            'solver_contract': {
                'objective_call_cap': 2, 'walltime_cap_seconds': 5.,
                'residual_field': 'kkt_residual', 'residual_tolerance': 1e-8,
                    'require_solver_success': True,
            },
        },
    }
    protocol_path = tmp_path / 'protocol.json'
    protocol_path.write_text(json.dumps(protocol, sort_keys=True))
    protocol_hash = hashlib.sha256(protocol_path.read_bytes()).hexdigest()

    monkeypatch.setattr(train, 'model_space', lambda _p, _seed: np.zeros((1, 2)))
    monkeypatch.setattr(train, 'basis_key', lambda *_args, **_kwargs: {'fixture': True})
    monkeypatch.setattr(train, 'collect', lambda _p, ids, *_args: np.zeros((len(ids), 3, 16)))
    monkeypatch.setattr(train, 'save_basis', lambda *_args, **_kwargs: None)
    monkeypatch.setattr(train, 'correlators', lambda _C, theta, _H: theta)
    risk_calls = []

    def fixture_risk(_p, _C, _masses):
        risk_calls.append(1)
        return 0.

    monkeypatch.setattr(train, 'risk_of', fixture_risk)

    def fake_minimize(objective, start, **_kwargs):
        value = objective(np.zeros_like(start))
        return SimpleNamespace(x=np.zeros_like(start), fun=value, nfev=1, nit=1,
                               success=True, status=0, message='fixture converged')

    monkeypatch.setattr(train, 'minimize', fake_minimize)
    with pytest.raises(train.SolverContractRejected) as caught:
        train.main([
            str(out), '--protocol', str(protocol_path), '--protocol-sha256', protocol_hash,
        ])

    assert caught.value.receipt['stop_reason'] == 'objective_call_budget_exhausted'
    # One baseline calculation plus two permitted objective calls. No learned
    # dev-val candidate score or test evaluation follows the rejection.
    assert len(risk_calls) == 3
    saved = json.loads((out / 'optimizer_contract_rejection.json').read_text())
    assert saved['status'] == 'solver_contract_rejected'
    assert saved['classification'] == 'diagnostic_only' and saved['physical_score'] is None
    assert not (out / 'results.json').exists() and not (out / 'manifest.json').exists()


@pytest.mark.parametrize('source', ['minimize', 'loss'])
def test_train_optimizer_exception_publishes_bound_failure_and_reraises(tmp_path, monkeypatch, source):
    import hashlib
    import json
    from pathlib import Path
    from types import SimpleNamespace

    train, p, out = _standin_train_main(tmp_path, monkeypatch)
    failure = RuntimeError(f'controlled {source} exception')
    optimizer_runs = []
    publications = []
    original_link = train.os.link

    def checked_link(temporary, target):
        # Nothing is published until a complete, parseable payload exists.
        assert json.loads(Path(temporary).read_text())['status'] == 'optimizer_exception'
        publications.append(Path(target).exists())
        return original_link(temporary, target)

    monkeypatch.setattr(train.os, 'link', checked_link)

    def failed_risk(*args):
        raise failure

    def fake_minimize(objective, start, **kwargs):
        optimizer_runs.append(1)
        value = objective(start)
        if len(optimizer_runs) == 1:
            return SimpleNamespace(x=start, fun=value, nfev=1, nit=1, success=True, message='first fit')
        if source == 'loss':
            monkeypatch.setattr(train, 'risk_of', failed_risk)
            objective(start)
        raise failure

    monkeypatch.setattr(train, 'minimize', fake_minimize)
    with pytest.raises(RuntimeError) as caught:
        train.main([])
    assert caught.value is failure
    target = out / 'optimizer_failure.json'
    original = target.read_bytes()
    saved = json.loads(original)
    assert saved['classification'] == 'diagnostic_only' and saved['physical_score'] is None
    assert saved['status'] == 'optimizer_exception'
    assert saved['exception'] == {'type': 'builtins.RuntimeError', 'message': str(failure)}
    assert saved['run_protocol'] == p and saved['protocol_fingerprint'] == train.fingerprint(p)
    assert saved['source_hashes']['train.py'] == hashlib.sha256(Path(train.__file__).read_bytes()).hexdigest()
    assert all(len(value) == 64 for value in saved['source_hashes'].values())
    assert len(saved['statistics_sha256']) == 64
    assert saved['seed'] == 4 and saved['lam2'] == .1
    assert len(saved['completed_grid']) == 1 and saved['completed_grid'][0]['lam2'] == 0.
    diagnostics = saved['optimizer_diagnostics']
    assert diagnostics['objective_calls'] == (2 if source == 'loss' else 1)
    assert diagnostics['completed_objective_calls'] == len(diagnostics['objective_trace']) == 1
    assert diagnostics['objective_trace'][0]['index'] == 1
    assert diagnostics['objective_trace'][0]['finite']
    assert diagnostics['elapsed_seconds'] >= diagnostics['objective_trace'][0]['elapsed_seconds']
    assert not (out / 'results.json').exists() and not (out / 'manifest.json').exists()
    assert not list(out.glob('.optimizer_failure.*.tmp'))
    with pytest.raises(FileExistsError):
        train._write_optimizer_failure(saved, failure, diagnostics)
    assert target.read_bytes() == original
    assert publications == [False, True]
    assert not list(out.glob('.optimizer_failure.*.tmp'))
    with pytest.raises(SystemExit):
        train.main([])  # existing failure output is not reused or replaced
    assert target.read_bytes() == original


def test_optimizer_failure_write_refusal_preserves_original_exception(tmp_path, monkeypatch):
    from tasks.optimize_gaussian import train

    failure = ValueError('original numerical error')

    def fake_minimize(*args, **kwargs):
        raise failure

    monkeypatch.setattr(train, 'minimize', fake_minimize)
    # A completed result directory must never receive a failure receipt.
    (tmp_path / 'results.json').write_text('{"historical": true}')
    with pytest.raises(ValueError) as caught:
        train.optimize(None, {'hidden': 1, 'v_max': 2., 'optimizer': {'maxiter': 3}}, None, 0.,
                       failure_context={'output_directory': str(tmp_path)})
    assert caught.value is failure
    assert not (tmp_path / 'optimizer_failure.json').exists()
    assert any('failure receipt was not written: FileExistsError' in note for note in failure.__notes__)


def test_optimizer_failure_receipt_rejects_unbound_identity_and_cleans_io_failure(tmp_path, monkeypatch):
    import json
    from tasks.optimize_gaussian import train

    context = {'output_directory': str(tmp_path)}
    with pytest.raises(ValueError, match='run identity'):
        train._write_optimizer_failure(context, ValueError('test'), {})
    p = {'hidden': 1, 'v_max': 2., 'optimizer': {'maxiter': 3}}
    context.update(run_protocol=p, protocol_fingerprint=train.fingerprint(p),
                   source_hashes={'train.py': 'a' * 64}, statistics_sha256='b' * 64,
                   seed=7, lam2=.1, completed_grid=[{'dev_val': float('nan')}])
    original = ValueError('original failure survives IO error')

    def broken_link(temporary, target):
        with open(temporary) as handle:
            saved = json.load(handle)
        assert saved['completed_grid'] == [{'dev_val': 'nan'}]
        raise OSError('controlled publish failure')

    def failed_minimize(*args, **kwargs):
        raise original

    monkeypatch.setattr(train.os, 'link', broken_link)
    monkeypatch.setattr(train, 'minimize', failed_minimize)
    with pytest.raises(ValueError) as caught:
        train.optimize(None, p, None, .1, failure_context=context)
    assert caught.value is original
    assert any('controlled publish failure' in note for note in original.__notes__)
    assert not (tmp_path / 'optimizer_failure.json').exists()
    assert not list(tmp_path.glob('.optimizer_failure.*.tmp'))
