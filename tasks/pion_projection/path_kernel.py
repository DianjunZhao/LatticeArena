"""Finite spatial path sums, projected to cubic A1+, Hermiticity and pion G parity."""
from itertools import permutations, product

import numpy as np


def _reduced(path):
    steps = []
    for step in path:
        if steps and steps[-1] == -step:
            steps.pop()
        else:
            steps.append(step)
    return tuple(steps)


def expand_paths(parameters):
    """Each seed weight multiplies the average over its distinct cubic images."""
    if not isinstance(parameters, dict) or set(parameters) != {'terms'} or not isinstance(parameters['terms'], list):
        raise ValueError('Expected a terms list')
    coefficients = {}
    for term in parameters['terms']:
        if not isinstance(term, dict) or set(term) != {'path', 'weight'}:
            raise ValueError('Each term needs path and weight')
        steps, weight = term['path'], term['weight']
        if not isinstance(steps, list) or any(type(s) is not int or abs(s) not in (1, 2, 3) for s in steps):
            raise ValueError('Path steps must be signed spatial axes 1, 2, 3')
        parts = weight if isinstance(weight, list) else [weight, 0]
        if len(parts) != 2 or any(type(x) not in (int, float) or not np.isfinite(float(x)) for x in parts):
            raise ValueError('Weight must be finite real or [real, imaginary]')
        # C exchanges the path endpoints without conjugating its coefficient.
        # Hermiticity conjugates the coefficient as well. Projecting onto both
        # keeps Re(w) times the symmetric sum of a path and its reversed path.
        w = float(parts[0])
        path = _reduced(steps)
        orbit = {tuple((1 if s > 0 else -1) * signs[abs(s)-1] * axes[abs(s)-1] for s in path)
                 for axes in permutations((1, 2, 3)) for signs in product((-1, 1), repeat=3)}
        for image in sorted(orbit):
            adjoint = tuple(-s for s in reversed(image))
            a = w / (2 * len(orbit))
            coefficients[image] = coefficients.get(image, 0j) + a
            coefficients[adjoint] = coefficients.get(adjoint, 0j) + a
    coefficients = {k: v for k, v in coefficients.items() if v != 0}
    if not coefficients or not all(np.isfinite(v) for v in coefficients.values()):
        raise ValueError('Projected operator is zero or nonfinite')
    return coefficients


class PathKernel:
    def __init__(self, links, parameters):
        xp = np
        if type(links).__module__.split('.')[0] == 'cupy':
            import cupy as xp
        if links.ndim != 6 or links.shape[0] != 3 or links.shape[-2:] != (3, 3):
            raise ValueError('Expected spatial links of shape (3,z,y,x,3,3)')
        self.xp, self.shape = xp, links.shape[1:4]
        self.transport = {}
        self.local = 0j
        for path, weight in expand_paths(parameters).items():
            if not path:
                self.local = weight
                continue
            offset = [0, 0, 0]  # z,y,x displacement from the sink
            matrix = None
            for step in path:
                mu = abs(step) - 1
                axis = 2 - mu
                if step < 0:
                    offset[axis] -= 1
                link = xp.roll(links[mu], tuple(-v for v in offset), axis=(0, 1, 2))
                if step < 0:
                    link = link.swapaxes(-1, -2).conj()
                else:
                    offset[axis] += 1
                matrix = link if matrix is None else matrix @ link
            endpoint = tuple(v % size for v, size in zip(offset, self.shape))
            if endpoint not in self.transport:
                self.transport[endpoint] = weight * matrix
            else:
                self.transport[endpoint] += weight * matrix

    def apply(self, field):
        if field.ndim != 5 or field.shape[:3] != self.shape or field.shape[-2] != 3:
            raise ValueError('Expected field of shape (z,y,x,3,nrhs)')
        out = self.local * field
        for endpoint, matrix in self.transport.items():
            shifted = self.xp.roll(field, tuple(-v for v in endpoint), axis=(0, 1, 2))
            out = out + matrix @ shifted
        return out


def build_kernel(spatial_links, parameters):
    return PathKernel(spatial_links, parameters)
