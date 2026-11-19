"""TaskSpec and OperatorContract adapters for pion_projection."""
import hashlib
import json
from pathlib import Path

import numpy as np

from core.io import digest, fingerprint
from core.measurement import bundle
from core.specs import operator_contract, task_spec

from .common import load_data


def task_spec_for(protocol):
    return task_spec(
        name='pion_projection', observable='zero-momentum pseudoscalar two-point function',
        geometry=list(protocol['geometry']),
        boundary={'spatial': 'periodic', 'temporal': 'antiperiodic (fermion)'},
        source={'kind': 'point', 'position': list(protocol['source'])},
        splits={'development': list(protocol['development']), 'gap': list(protocol['gap']),
                'validation': list(protocol['validation'])},
        reference={'kind': 'single', 'window': protocol['reference_windows'][protocol['reference_nominal_window']]},
        metric={'name': 'conditional perturbation risk', 'score_window': list(protocol['score_window'])},
        budget={'bootstrap_samples': protocol['bootstrap_samples'], 'block_length': protocol['block_length']},
        dependencies={'protocol': fingerprint(protocol),
                      'kernels': digest(Path(__file__).with_name('kernels.py')),
                      'statistics': digest(Path(__file__).with_name('statistics.py'))},
    )


def operator_contract_for():
    return operator_contract(
        name='pion-kernel-v1', axes='(z,y,x,3,nrhs)', dtype='complex128',
        transformation='spin_scalar', support='time_slice',
        parameters={'schema_by_builder': {
            'tasks.pion_projection.path_kernel:build_kernel': {'terms': 'list[{path: signed spatial steps, weight: real or [real, imag]}]'},
            'tasks.pion_projection.kernels:build_kernel': {'powers': 'list[int]', 'weights': 'list[float]', 'alpha': 'float'}},
            'custom_builder': 'builder-defined JSON parameters'},
        dependencies={name: digest(Path(__file__).with_name(name + '.py')) for name in ('kernels', 'path_kernel')},
        constraints={'hermitian': True, 'zero_momentum': True, 'gauge_covariant': True,
                     'spatial_symmetry': 'A1+', 'bilinear_irrep': 'A1-', 'isospin': 1,
                     'G_parity': -1, 'neutral_partner_C': 1, 'translation_covariant': True, 'linear_in_field': True},
    )


def bundle_for(run):
    """Trusted measurement bundle: load_data checks IDs/hash/shape/finite."""
    run = Path(run)
    protocol = json.loads((run / 'development_provenance.json').read_text())['protocol']
    arrays, splits, ids_hash, inputs = {}, {}, {}, {}
    for split in ('development', 'validation'):
        data = load_data(run, split, protocol)
        arrays[split] = data
        splits[split] = {'n': int(data.shape[0])}
        ids_hash[split] = fingerprint(list(range(protocol[split][0], protocol[split][1] + 1)))
        inputs[split] = hashlib.sha256(np.ascontiguousarray(data).tobytes()).hexdigest()
    code = {name: digest(Path(__file__).with_name(name)) for name in
            ('kernels.py', 'statistics.py', 'experiment.py')}
    run_spec = task_spec_for(protocol)
    manifest = {'protocol_hash': fingerprint(protocol), 'splits': splits, 'ids': ids_hash,
                'inputs': inputs, 'code': code, 'powers': protocol['powers'],
                'alpha': protocol['alpha'],
                'run_spec': fingerprint(run_spec)}
    return bundle('pion_projection', arrays, manifest,
                  {'linear_response': True, 'cross_matrix': False, 'new_source': False})
