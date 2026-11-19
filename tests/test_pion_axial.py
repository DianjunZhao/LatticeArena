import numpy as np

from tasks.pion_projection.axial import contract, mass_differences
from tasks.pion_projection.common import protocol


def test_axial_uses_sink_spin_and_agrees_with_dense_trace():
    rng = np.random.default_rng(84)
    shape = (2, 4, 1, 2, 2, 4, 4, 3, 3)
    s = rng.normal(size=shape) + 1j*rng.normal(size=shape)
    pp, ap = contract(s)
    g4 = np.block([[np.zeros((2, 2)), np.eye(2)], [np.eye(2), np.zeros((2, 2))]])
    g5 = np.diag([1, 1, -1, -1])
    for t in range(4):
        field = s[:, t]
        axial = np.einsum('ij,...jabc->...iabc', g5 @ g4 @ g5, field)
        np.testing.assert_allclose(ap[t], np.vdot(field, axial).real, atol=1e-12)
        np.testing.assert_allclose(pp[t], np.sum(abs(field)**2))


def test_paired_mass_difference_uses_odd_axial_folding_and_preserves_invalid_draws():
    p = dict(protocol(), bootstrap_samples=40)
    t = np.arange(16)
    def correlator(mass, sign):
        return np.exp(-mass*t) + sign*np.exp(-mass*(16-t))
    signal = np.stack([correlator(.7, 1), -correlator(.9, -1)])
    rows = np.arange(1, 31)[:, None, None]*signal
    table = mass_differences(rows, p)
    assert [r['t'] for r in table] == [5, 6, 7]
    for row in table:
        delta = row['A4P_minus_PP']
        np.testing.assert_allclose([delta['estimate'], *delta['interval_95']], .2)
    rows[:, 1] = 0.
    for row in mass_differences(rows, p):
        assert row['A4P_minus_PP'] == {'estimate': None, 'valid_draws': 0, 'interval_95': None}
