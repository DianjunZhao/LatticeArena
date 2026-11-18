"""TaskSpec and OperatorContract adapters for pion_projection (F1 slice 1-2)."""
from pathlib import Path

from core.io import digest
from core.specs import operator_contract, task_spec


def task_spec_for(protocol, reference_kind='single', protocol_path=None):
    return task_spec(
        name='pion_projection', observable='zero-momentum pseudoscalar two-point function',
        geometry=list(protocol['geometry']),
        boundary={'spatial': 'periodic', 'temporal': 'antiperiodic (fermion)'},
        source={'kind': 'point', 'time': protocol['source']},
        splits={'development': list(protocol['development']), 'gap': list(protocol['gap']),
                'validation': list(protocol['validation'])},
        reference={'kind': reference_kind, 'window': protocol['reference_windows'][protocol['reference_nominal_window']]},
        metric={'name': 'conditional perturbation risk', 'score_window': list(protocol['score_window'])},
        budget={'bootstrap_samples': protocol['bootstrap_samples'], 'block_length': protocol['block_length']},
        dependencies={'protocol': digest(protocol_path) if protocol_path else 'runtime',
                      'kernels': digest(Path(__file__).with_name('kernels.py')),
                      'statistics': digest(Path(__file__).with_name('statistics.py'))},
    )


def operator_contract_for():
    return operator_contract(
        name='pion-kernel-v1', axes='(z,y,x,3,nrhs)', dtype='complex128',
        transformation='spin_scalar', support='time_slice',
        parameters={'powers': 'list[int]', 'weights': 'list[float]', 'alpha': 'float'},
        dependencies={'kernels': digest(Path(__file__).with_name('kernels.py'))},
        constraints={'hermitian': True, 'zero_momentum': True, 'gauge_covariant': True},
    )
