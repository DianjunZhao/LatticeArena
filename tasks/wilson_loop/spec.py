"""TaskSpec and OperatorContract adapters for wilson_loop (F1 slice 1-2)."""
from pathlib import Path

from core.io import digest
from core.specs import operator_contract, task_spec


def task_spec_for(protocol):
    return task_spec(
        name='wilson_loop', observable='static potential from Wilson loops',
        geometry=list(protocol['geometry']),
        boundary={'spatial': 'periodic', 'temporal': 'periodic'},
        source={'kind': 'static', 'origin': 'spatial origin'},
        splits={'development': list(protocol['development']), 'gap': list(protocol['gap']),
                'validation': list(protocol['validation'])},
        reference={'kind': 'identity kernel', 'windows': protocol['reference_windows']},
        metric={'name': 'precision plus window-spread risk', 'nominal_window_index': protocol['reference_nominal_window']},
        budget={'bootstrap_samples': protocol['bootstrap_samples'], 'block_length': protocol['block_length']},
        dependencies={'kernels': digest(Path(__file__).with_name('kernels.py')),
                      'statistics': digest(Path(__file__).with_name('statistics.py'))},
    )


def operator_contract_for():
    return operator_contract(
        name='wilson-kernel-v1', axes='(mu,t,z,y,x,3,3)', dtype='complex128',
        transformation='gauge_covariant', support='spacetime_local',
        parameters={'alpha': 'float', 'steps': 'int'},
        dependencies={'kernels': digest(Path(__file__).with_name('kernels.py'))},
        constraints={'temporal_links_unsmeared': True, 'left_right_covariant': True},
    )


def bundle_for(run):
    """Measurement bundle for a Wilson-loop run (arrays + manifest + capabilities)."""
    import json

    import numpy as np

    from core.io import fingerprint
    from core.measurement import bundle

    run = Path(run)
    p = json.loads((run / 'validation_provenance.json').read_text())['protocol']
    arrays, splits = {}, {}
    for split in ('development', 'validation'):
        path = run / f'{split}.npz'
        if not path.exists():
            continue
        with np.load(path) as f:
            arrays[split] = f['loops'].copy()
            splits[split] = {'n': int(f['loops'].shape[0])}
    manifest = {'protocol_hash': fingerprint(p), 'splits': splits,
                'r_values': p['r_values'], 'kernels': [k['name'] for k in p['kernels']]}
    return bundle('wilson_loop', arrays, manifest,
                  {'linear_response': False, 'cross_matrix': False, 'new_source': False})
