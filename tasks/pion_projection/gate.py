"""Shared reference-gate implementation (todo C1)."""
import numpy as np
from scipy.stats import chi2

from .reference import make_reference


def fit_reference_gate(dev_blocks, p, kind='single', window=None):
    """Fit the frozen reference model and return (ref, mass, cost, dof, p_value)."""
    window = p['reference_windows'][p['reference_nominal_window']] if window is None else window
    ref = make_reference(dev_blocks, p, window, kind)
    mean = ref.samples.mean(axis=0)
    if kind == 'single':
        mass, cost = ref.fit(mean)
        dof = ref.samples.shape[1] - len(p['reference_basis']) - 1
    else:
        full = ref.fit_full(mean)
        mass, cost = full['mass'], full['cost']
        dof = ref.nchan * ref.ntime - 2 - 2 * ref.nchan
    return ref, float(mass), float(cost), int(dof), float(chi2.sf(cost, dof))
