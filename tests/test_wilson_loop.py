import numpy as np
import pytest

from tasks.wilson_loop.kernels import ape, build_kernel
from tasks.wilson_loop.measure import loops
from tasks.wilson_loop.statistics import blocks, bootstrap_indices, potential, risk


def random_su3(rng, shape):
    a = rng.normal(size=(*shape, 3, 3)) + 1j * rng.normal(size=(*shape, 3, 3))
    q, _ = np.linalg.qr(a)
    return q / np.linalg.det(q)[..., None, None] ** (1 / 3)


def cold(latt):
    links = np.broadcast_to(np.eye(3, dtype=complex), (3, *latt, 3, 3)).copy()
    return links, np.broadcast_to(np.eye(3, dtype=complex), (*latt, 3, 3)).copy()


P = {'r_values': [1, 2], 't_values': [1, 2, 3]}


def test_cold_field_gives_unit_loops():
    links, temporal = cold((4, 4, 4, 4))
    w = loops(links, temporal, P)
    np.testing.assert_allclose(w, 1.0, atol=1e-13)


def test_gauge_covariance():
    rng = np.random.default_rng(3)
    latt = (4, 4, 4, 4)
    links = random_su3(rng, (3, *latt))
    temporal = random_su3(rng, latt)
    g = random_su3(rng, latt)
    gp = [np.roll(g, -1, axis=axis) for axis in (0, 1, 2, 3)]
    gt = g.swapaxes(-1, -2).conj()
    links_g = np.stack([g @ links[d] @ np.roll(gt, -1, axis=3 - d) for d in range(3)])
    temporal_g = g @ temporal @ np.roll(gt, -1, axis=0)
    np.testing.assert_allclose(loops(links_g, temporal_g, P), loops(links, temporal, P), rtol=1e-12)


def brute(links, temporal, R, T, d):
    lt, lz, ly, lx = temporal.shape[:4]
    dims = [lx, ly, lz]
    total = 0.0
    for t0 in range(lt):
        for z in range(lz):
            for y in range(ly):
                for x in range(lx):
                    c = [x, y, z]
                    def prod(c0, tt):
                        out = np.eye(3, dtype=complex)
                        for r in range(R):
                            cc = list(c0)
                            cc[d] = (cc[d] + r) % dims[d]
                            out = out @ links[d][tt, cc[2], cc[1], cc[0]]
                        return out
                    def time_line(c0, tt):
                        out = np.eye(3, dtype=complex)
                        for t in range(T):
                            out = out @ temporal[(tt + t) % lt, c0[2], c0[1], c0[0]]
                        return out
                    cR = list(c)
                    cR[d] = (cR[d] + R) % dims[d]
                    w = prod(c, t0) @ time_line(cR, t0) @ prod(c, (t0 + T) % lt).conj().T @ time_line(c, t0).conj().T
                    total += np.trace(w).real
    return total / (3 * lt * lz * ly * lx)


def test_loops_match_brute_force():
    rng = np.random.default_rng(7)
    latt = (4, 4, 4, 4)
    links = random_su3(rng, (3, *latt))
    temporal = random_su3(rng, latt)
    w = loops(links, temporal, P)
    for i, R in enumerate(P['r_values']):
        for j, T in enumerate(P['t_values']):
            reference = sum(brute(links, temporal, R, T, d) for d in range(3)) / 3
            assert w[i, j] == pytest.approx(reference, rel=1e-12)


def test_ape_keeps_links_unitary():
    rng = np.random.default_rng(5)
    links = random_su3(rng, (3, 4, 4, 4, 4))
    smeared = ape(links, 0.5, 3)
    eye = np.einsum('...ij,...kj->...ik', smeared.conj(), smeared)
    np.testing.assert_allclose(eye, np.broadcast_to(np.eye(3), eye.shape), atol=1e-10)
    det = np.linalg.det(smeared)
    np.testing.assert_allclose(det, 1.0, atol=1e-10)


def test_ape_limits():
    rng = np.random.default_rng(11)
    links = random_su3(rng, (3, 4, 4, 4, 4))
    np.testing.assert_allclose(build_kernel(links, {'alpha': 0.5, 'steps': 0}), links)
    np.testing.assert_allclose(ape(links, 0.0, 3), links)


def test_potential_recovers_known_slopes():
    v = np.array([0.4, 0.55, 0.7])
    t = np.arange(0, 9)
    w = np.exp(-np.outer(v, t))[None]
    np.testing.assert_allclose(potential(w, [4, 5, 6, 7], list(t))[0], v, rtol=1e-12)


def test_risk_penalizes_bias_and_noise():
    v = np.array([0.5, 0.6, 0.7])
    t = np.arange(1, 9)
    exact = np.exp(-np.outer(v, t))
    data = np.repeat(exact[None], 12, axis=0)[:, None]
    idx = bootstrap_indices(6, 50, 1)
    b = blocks(data, 2)
    tv = list(range(1, 9))
    windows = [[4, 5, 6], [4, 5, 6, 7], [5, 6, 7, 8]]
    base = risk(b, idx, windows, tv, v)
    shift_t = np.exp(-0.02 * np.arange(8))
    worse = risk(b * shift_t, idx, windows, tv, v)
    assert base['risk'] < 1e-10
    assert worse['risk'] > base['risk']


def test_project_is_bidirectionally_covariant():
    from tasks.wilson_loop.kernels import project
    rng = np.random.default_rng(21)
    m = (rng.normal(size=(3, 3)) + 1j * rng.normal(size=(3, 3)))
    g = random_su3(rng, ())
    h = random_su3(rng, ())
    q = project(m)
    np.testing.assert_allclose(g @ q @ h, project(g @ m @ h), atol=1e-12)
    np.testing.assert_allclose(q.conj().T @ q, np.eye(3), atol=1e-12)
    np.testing.assert_allclose(np.linalg.det(q), 1.0, atol=1e-12)


def test_project_rejects_singular_and_nonfinite():
    from tasks.wilson_loop.kernels import project
    with pytest.raises(ValueError):
        project(np.zeros((3, 3), dtype=complex))
    with pytest.raises(ValueError):
        project(np.full((3, 3), np.nan, dtype=complex))


def test_ape_gauge_covariant_multiple_parameters():
    rng = np.random.default_rng(22)
    latt = (4, 4, 4, 4)
    u = random_su3(rng, (3, *latt))
    for alpha, steps in ((0.0, 2), (0.3, 1), (0.5, 2), (0.7, 1), (1.0, 1)):
        base = ape(u, alpha, steps)
        g = random_su3(rng, latt)
        gt = g.swapaxes(-1, -2).conj()
        ug = np.stack([g @ u[d] @ np.roll(gt, -1, axis=3 - d) for d in range(3)])
        want = np.stack([g @ base[d] @ np.roll(gt, -1, axis=3 - d) for d in range(3)])
        np.testing.assert_allclose(ape(ug, alpha, steps), want, atol=1e-10)


def _nersc(dims=(2, 2, 2, 2), datatype='4D_SU3_GAUGE_3x3', floating='1'):
    nx, ny, nz, nt = dims
    header = ('4D_SU3_GAUGE_3x3\n'
              f'DIMENSION_1={nx}\nDIMENSION_2={ny}\nDIMENSION_3={nz}\nDIMENSION_4={nt}\n'
              f'DATATYPE={datatype}\nFLOATING_POINT={floating}\nEND_HEADER\n')
    payload = np.zeros(nx * ny * nz * nt * 4 * 9, dtype='<c16').tobytes()
    return header.encode() + payload


def test_read_nersc_validates_header_and_payload(tmp_path):
    from tasks.wilson_loop.common import read_nersc
    path = tmp_path / 'gauge'
    path.write_bytes(_nersc())
    u = read_nersc(path)
    assert u.shape == (4, 2, 2, 2, 2, 3, 3)
    path.write_bytes(_nersc(floating='IEEE64LITTLE'))
    read_nersc(path)
    path.write_bytes(_nersc(datatype='4D_SU2_GAUGE_3x3'))
    with pytest.raises(ValueError, match='DATATYPE'):
        read_nersc(path)
    for bad in ('0', 'IEEE32LITTLE', 'IEEE64BIG'):
        path.write_bytes(_nersc(floating=bad))
        with pytest.raises(ValueError, match='FLOATING_POINT'):
            read_nersc(path)
    path.write_bytes(_nersc()[:-16])
    with pytest.raises(ValueError, match='payload'):
        read_nersc(path)


def test_load_data_validates_shape_dtype_and_finite(tmp_path):
    from tasks.pion_projection.common import fingerprint
    from tasks.wilson_loop.common import indices, load_data, protocol
    p = protocol()
    ids = indices('development')
    shape = (len(ids), len(p['kernels']), len(p['r_values']), len(p['t_values']))
    np.savez(tmp_path / 'development.npz', ids=ids, loops=np.ones(shape),
             protocol_hash=fingerprint(p))
    assert load_data(tmp_path, 'development').shape == shape
    for bad in (np.ones(shape[:-1]), np.full(shape, np.nan)):
        np.savez(tmp_path / 'development.npz', ids=ids, loops=bad,
                 protocol_hash=fingerprint(p))
        with pytest.raises(ValueError):
            load_data(tmp_path, 'development')


def _synthetic_loops(ids, v=(0.4, 0.55, 0.7)):
    from tasks.wilson_loop.common import protocol
    p = protocol()
    t = np.array(p['t_values'], dtype=float)
    base = np.exp(-np.outer(v, t))
    return np.repeat(base[None, None, :, :], len(ids), axis=0).repeat(len(p['kernels']), axis=1)


def test_develop_evaluate_roundtrip_and_tamper_rejection(tmp_path):
    import json
    from tasks.pion_projection.common import fingerprint
    from tasks.wilson_loop.common import indices, protocol
    from tasks.wilson_loop.experiment import develop, evaluate
    p = protocol()
    np.savez(tmp_path / 'development.npz', ids=indices('development'),
             loops=_synthetic_loops(indices('development')), protocol_hash=fingerprint(p))
    develop(tmp_path)
    frozen = json.loads((tmp_path / 'submission.json').read_text())
    assert frozen['reference_passed'] and 'kernel_sha256' in frozen
    np.savez(tmp_path / 'validation.npz', ids=indices('validation'),
             loops=_synthetic_loops(indices('validation')), protocol_hash=fingerprint(p))
    evaluate(tmp_path)
    report = json.loads((tmp_path / 'validation_results.json').read_text())
    assert report['reference_passed']
    assert report['results']['identity']['score'] == pytest.approx(100.0)
    loops = _synthetic_loops(indices('development'))
    loops[0, 0, 0, 0] += 0.5
    np.savez(tmp_path / 'development.npz', ids=indices('development'), loops=loops,
             protocol_hash=fingerprint(p))
    with pytest.raises(ValueError, match='Development data changed'):
        evaluate(tmp_path)


def test_protocol_v2_documents_the_normalization_change():
    import json
    from pathlib import Path
    p = json.loads(Path('tasks/wilson_loop/protocol_v2.json').read_text())
    assert p['version'].endswith('-v2') and 'v1' in p['supersedes']
    assert p['normalization'].startswith('alpha/4')
    for kernel in p['kernels'][1:]:
        old = kernel['equivalent_v1_alpha']
        assert kernel['alpha'] == pytest.approx(2 * old / (3 - old), rel=1e-4)


def test_paired_ratios_are_one_for_identical_kernels_and_below_one_for_noise():
    from tasks.wilson_loop.common import protocol
    from tasks.wilson_loop.paired import paired_ratios
    p = protocol()
    t = np.array(p['t_values'], dtype=float)
    v = np.array([0.4, 0.55, 0.7])
    base = np.exp(-np.outer(v, t))
    blocks = 6
    same = np.repeat(base[None, None], blocks, axis=0).repeat(2, axis=1)
    rng = np.random.default_rng(0)
    noisy = same.copy()
    noisy[:, 1] *= np.exp(0.01 * rng.normal(size=noisy[:, 1].shape))
    r_same = paired_ratios(same, p['reference_windows'], p['t_values'], v, outer=40, inner=40, seed=1)
    r_noisy = paired_ratios(noisy, p['reference_windows'], p['t_values'], v, outer=40, inner=40, seed=1)
    np.testing.assert_allclose(r_same, 1.0, rtol=1e-12)
    assert np.median(r_noisy) < 1.0


def test_protocol_v3_is_consistent():
    import json
    from pathlib import Path
    p = json.loads(Path('tasks/wilson_loop/protocol_v3.json').read_text())
    assert p['version'].endswith('-v3')
    assert p['development'] == [0, 99] and p['validation'] == [120, 199]
    assert p['gap'] == [100, 119]
    assert p['kernels'] == json.loads(Path('tasks/wilson_loop/protocol_v2.json').read_text())['kernels']


def test_projection_batch_matches_single_matrices():
    from tasks.wilson_loop.kernels import project
    rng = np.random.default_rng(31)
    a = rng.normal(size=(3, 3)) + 1j * rng.normal(size=(3, 3))
    eye = np.eye(3, dtype=complex)
    single = [project(eye), project(1e4 * eye), project(a), project(1e-6 * a)]
    batch = project(np.stack([eye, 1e4 * eye, a, 1e-6 * a]))
    for i, expected in enumerate(single):
        np.testing.assert_allclose(batch[i], expected, atol=1e-10)


def test_projection_rejects_nonfinite_and_ill_conditioned():
    from tasks.wilson_loop.kernels import project
    bad = np.stack([np.eye(3, dtype=complex), np.full((3, 3), np.inf)])
    with pytest.raises(ValueError, match='non-positive or non-finite'):
        project(bad)


def test_nersc_header_geometry_and_payload(tmp_path):
    from tasks.wilson_loop.common import read_nersc
    header = (b'BEGIN_HEADER\nDIMENSION_1=1\nDIMENSION_2=1\nDIMENSION_3=1\nDIMENSION_4=1\n'
              b'DATATYPE=4D_SU3_GAUGE_3x3\nFLOATING_POINT=IEEE64LITTLE\nEND_HEADER\n')
    path = tmp_path / 'gauge'
    path.write_bytes(header + b'\x00' * (1 * 1 * 1 * 1 * 4 * 3 * 3 * 16))
    read_nersc(path, [1, 1, 1, 1])
    with pytest.raises(ValueError, match='geometry'):
        read_nersc(path, [2, 2, 2, 16])


def test_measurement_generation_and_resume(tmp_path):
    from tasks.wilson_loop.common import protocol
    from tasks.wilson_loop.identity import check_resume, generation, measurement_spec
    spec = measurement_spec(protocol(), 'validation')
    assert check_resume(tmp_path, 'validation', spec) == 0
    np.savez(tmp_path / 'validation.npz', ids=np.asarray(spec['ids'][:3]),
             loops=np.zeros((3, 2, 2, 1)), generation=np.asarray(generation(spec)))
    assert check_resume(tmp_path, 'validation', spec) == 3
    with pytest.raises(ValueError, match='generation'):
        check_resume(tmp_path, 'validation', dict(spec, kernel_sha256='0' * 64))


def test_trust_status_does_not_use_the_protocol_name(monkeypatch):
    from pathlib import Path
    from tasks.wilson_loop.common import protocol
    from tasks.wilson_loop.identity import trust_status
    run = Path('results/wilson_loop/s16t16_v3')
    if not (run / 'submission.json').exists():
        pytest.skip('v3 run not available')
    import tasks.wilson_loop.common as common
    import json
    v3 = json.loads(Path('tasks/wilson_loop/protocol_v3.json').read_text())
    monkeypatch.setattr(common, 'protocol', lambda: v3)
    status = trust_status(run, v3, json.loads((run / 'submission.json').read_text()),
                          json.loads((run / 'validation_provenance.json').read_text()))
    assert status['status'] == 'archived_diagnostic'
    assert status['reasons']


def test_evidence_schema_and_summary(tmp_path):
    from core.evidence import load_evidence, record, summarise, validate, write_evidence
    with pytest.raises(ValueError, match='missing'):
        validate({'test_id': 'x'})
    with pytest.raises(ValueError, match='status'):
        record('x', 'wilson_loop', 'claim', 'cmd', 1, 1, 'MAYBE', 'synthetic_CPU')
    entry = record('x', 'wilson_loop', 'claim', 'cmd', 1, 1, 'PASS', 'synthetic_CPU')
    path = tmp_path / 'e.json'
    write_evidence(path, [entry])
    assert load_evidence(path)[0]['status'] == 'PASS'
    assert summarise([entry])[0]['task'] == 'wilson_loop'


def test_operator_checks_and_counterexamples():
    from core.operator_checks import (bad_gram_schmidt_projector, bad_nonhermitian_kernel,
                                      covariance_residual, good_hermitian_kernel,
                                      hermiticity_residual, linearity_residual)
    rng = np.random.default_rng(5)
    f = rng.normal(size=(8, 3)) + 1j * rng.normal(size=(8, 3))
    g = rng.normal(size=(8, 3)) + 1j * rng.normal(size=(8, 3))
    assert linearity_residual(lambda x: 2 * x - 0.5 * np.roll(x, 1, 0), f, g) < 1e-12
    assert linearity_residual(lambda x: np.abs(x), f, g) > 1e-3
    good = lambda a, b: np.vdot(a, good_hermitian_kernel(b))
    bad = lambda a, b: np.vdot(a, bad_nonhermitian_kernel(b))
    assert hermiticity_residual(good, f, g) < 1e-12
    assert hermiticity_residual(bad, f, g) > 1e-3
    u = np.linalg.qr(rng.normal(size=(3, 3)) + 1j * rng.normal(size=(3, 3)))[0]
    field = rng.normal(size=(3, 3)) + 1j * rng.normal(size=(3, 3))
    assert covariance_residual(lambda x: u @ x, lambda x: u @ x, field) < 1e-12
    assert covariance_residual(bad_gram_schmidt_projector, lambda x: x @ u, field) > 1e-6
