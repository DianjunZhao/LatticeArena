"""Run a receipt-preserving pure-gauge HMC chain on the Kunshan DCU cluster.

The protocol is passed as JSON and the output directory must be new.  This
runner keeps a JSONL row for every trajectory, including thermalization rows,
so sparse stdout checkpoints cannot be mistaken for a complete HMC receipt.
"""

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import cupy as cp
import numpy as np
from pyquda.action import GaugeAction, abstract
from pyquda.hmc import HMC, Integrator
from pyquda_utils import core, io
from pyquda_utils.core import X, Y, Z, T


class BAB(Integrator):
    """Second-order BAB leapfrog used by the archived S16T16 production runs."""

    def integrate(self, updateGauge, updateMom, t):
        dt = t / self.n_steps
        for _ in range(self.n_steps):
            updateMom(dt / 2)
            updateGauge(dt)
            updateMom(dt / 2)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(8 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    os.replace(str(temporary), str(path))


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def package_version(distribution):
    try:
        return version(distribution)
    except PackageNotFoundError:
        return 'unavailable'


def runtime_metadata(include_device=False):
    metadata = {
        'python': sys.version,
        'python_executable': sys.executable,
        'platform': platform.platform(),
        'hostname': platform.node(),
        'packages': {
            name: package_version(name)
            for name in ('PyQUDA', 'PyQUDA-Utils', 'cupy', 'numpy', 'mpi4py')
        },
        'environment': {
            name: os.environ.get(name)
            for name in (
                'QUDA_PATH', 'SLURM_JOB_ID', 'SLURM_JOB_NODELIST',
                'SLURM_JOB_PARTITION', 'SLURM_JOB_GRES', 'ROCM_PATH',
            )
        },
    }
    if include_device:
        for name, getter in (
            ('accelerator_driver_version', cp.cuda.runtime.driverGetVersion),
            ('accelerator_runtime_version', cp.cuda.runtime.runtimeGetVersion),
        ):
            try:
                metadata[name] = int(getter())
            except Exception as error:  # vendor runtimes expose different metadata
                metadata[name] = 'unavailable: ' + repr(error)
        try:
            properties = cp.cuda.runtime.getDeviceProperties(0)
            device_name = properties.get('name', 'unknown')
            if isinstance(device_name, bytes):
                device_name = device_name.decode('utf-8', errors='replace')
            metadata['device'] = {
                'name': str(device_name),
                'major': int(properties.get('major', -1)),
                'minor': int(properties.get('minor', -1)),
                'total_global_memory_bytes': int(properties.get('totalGlobalMem', -1)),
            }
        except Exception as error:
            metadata['device'] = {'status': 'unavailable: ' + repr(error)}
    return metadata


def write_trajectory(stream, row, index):
    stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + '\n')
    stream.flush()
    if index % 20 == 0:
        os.fsync(stream.fileno())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', required=True)
    args = parser.parse_args(argv)

    protocol_path = Path(args.protocol).resolve()
    protocol = json.loads(protocol_path.read_text())
    root = Path.cwd().resolve()
    output = (root / protocol['output_directory']).resolve()
    receipt_path = (root / protocol['receipt_path']).resolve()
    trajectory_path = (root / protocol['trajectory_log_path']).resolve()
    source_path = Path(__file__).resolve()
    for target in (output, receipt_path, trajectory_path):
        if target.exists():
            raise FileExistsError('Refusing to overwrite production output: ' + str(target))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=False)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    trajectory_path.parent.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    receipt = {
        'schema': 'latticearena-hmc-production-receipt-v1',
        'status': 'RUNNING',
        'started_utc': utc_now(),
        'protocol_path': str(protocol_path.relative_to(root)),
        'protocol_sha256': sha256(protocol_path),
        'source_path': str(source_path.relative_to(root)),
        'source_sha256': sha256(source_path),
        'command_line': list(sys.argv),
        'protocol': protocol,
        'runtime': runtime_metadata(include_device=False),
    }
    launcher = root / protocol.get('launcher_path', '')
    if launcher.is_file():
        receipt['launcher_path'] = str(launcher.relative_to(root))
        receipt['launcher_sha256'] = sha256(launcher)
    atomic_json(receipt_path, receipt)

    try:
        lattice = [int(value) for value in protocol['lattice']]
        if len(lattice) != 4 or any(value <= 0 for value in lattice):
            raise ValueError('lattice must contain four positive extents')
        if protocol['boundary_conditions'] != 'periodic_all_directions':
            raise ValueError('this runner only implements periodic pure-gauge boundaries')
        seed = int(protocol['seed'])
        thermal = int(protocol['thermal_trajectories'])
        planned = int(protocol['planned_trajectories'])
        save_every = int(protocol['save_every'])
        max_save = int(protocol['max_saved_configurations'])
        n_steps = int(protocol['integrator_steps'])
        tau = float(protocol['trajectory_length'])
        if min(thermal, planned, save_every, max_save, n_steps) <= 0:
            raise ValueError('trajectory counts, save interval, and integration steps must be positive')
        if planned <= thermal:
            raise ValueError('planned trajectories must exceed the thermalization count')

        (root / '.cache/quda').mkdir(parents=True, exist_ok=True)
        core.init([1, 1, 1, 1], lattice, resource_path=str(root / '.cache/quda'))
        info = core.LatticeInfo(lattice)
        loop = abstract.LoopParam(
            [[X, Y, -X, -Y], [X, Z, -X, -Z], [Y, Z, -Y, -Z],
             [X, T, -X, -T], [Y, T, -Y, -T], [Z, T, -Z, -T]],
            [1.0] * 6,
        )
        hmc = HMC(info, [GaugeAction(info, loop, float(protocol['beta']))], BAB(n_steps))
        gauge = core.LatticeGauge(info)
        rng = np.random.default_rng(seed)
        gaussian = rng.normal(size=gauge.data.shape) + 1j * rng.normal(size=gauge.data.shape)
        q, _ = np.linalg.qr(gaussian)
        q = q / np.linalg.det(q)[..., None, None] ** (1 / 3)
        gauge.data[:] = cp.asarray(q.astype(np.complex128))
        hmc.initialize(seed, gauge)

        def plaquette():
            return float(hmc.plaquette()[0])

        receipt['runtime'] = runtime_metadata(include_device=True)
        receipt['initial_plaquette'] = plaquette()
        receipt['status'] = 'RUNNING'
        atomic_json(receipt_path, receipt)
        manifest_path = output / 'manifest.json'
        manifest = {
            'schema': 'latticearena-hmc-ensemble-manifest-v1',
            'ensemble': protocol['ensemble'],
            'lattice': lattice,
            'beta': float(protocol['beta']),
            'seed': seed,
            'start': protocol['start'],
            'integrator': {'name': 'BAB', 'order': 2, 'steps': n_steps, 'tau': tau},
            'thermal_trajectories': thermal,
            'planned_trajectories': planned,
            'save_every': save_every,
            'configs': [],
        }
        accepted_production = 0
        production_count = 0
        all_delta_h = []
        saved = 0
        actual = 0
        with trajectory_path.open('x', encoding='utf-8') as stream:
            for zero_index in range(planned):
                trajectory = zero_index + 1
                t0 = time.perf_counter()
                hmc.gaussMom()
                e_old = hmc.momAction() + hmc.gaugeAction()
                hmc.integrate(tau, 2e-14)
                e_new = hmc.momAction() + hmc.gaugeAction()
                delta_h = float(e_new - e_old)
                metropolis_accept = bool(hmc.accept(delta_h))
                is_thermal = trajectory <= thermal
                forced_thermal_update = bool(is_thermal and not metropolis_accept)
                if metropolis_accept or is_thermal:
                    hmc.saveGauge(gauge)
                    state_update = 'accepted' if metropolis_accept else 'thermalization_forced_update'
                else:
                    hmc.loadGauge(gauge)
                    state_update = 'rejected_restored'
                plaq_value = plaquette()
                if not is_thermal:
                    production_count += 1
                    accepted_production += int(metropolis_accept)
                    all_delta_h.append(delta_h)
                config_id = None
                config_path = None
                config_sha = None
                if (trajectory > thermal and
                        (trajectory - thermal - 1) % save_every == 0 and
                        saved < max_save):
                    config_id = int(protocol['start_id']) + saved
                    path = output / ('wilson_b6.' + str(config_id))
                    io.writeNERSCGauge(
                        str(path), gauge, ensemble_id=protocol['ensemble'],
                        ensemble_label='beta' + str(protocol['beta']),
                        sequence_number=config_id,
                    )
                    config_sha = sha256(path)
                    config_path = str(path.relative_to(root))
                    manifest['configs'].append({
                        'id': config_id,
                        'trajectory': trajectory,
                        'plaquette': plaq_value,
                        'sha256': config_sha,
                        'metropolis_accept': metropolis_accept,
                    })
                    atomic_json(manifest_path, manifest)
                    saved += 1
                actual = trajectory
                row = {
                    'trajectory': trajectory,
                    'phase': 'thermalization' if is_thermal else 'production',
                    'delta_h': delta_h,
                    'metropolis_accept': metropolis_accept,
                    'state_update': state_update,
                    'thermalization_forced_update': forced_thermal_update,
                    'plaquette_after_update': plaq_value,
                    'production_accepts': accepted_production,
                    'production_trajectories': production_count,
                    'production_acceptance_rate': (
                        accepted_production / production_count if production_count else None
                    ),
                    'configuration_id': config_id,
                    'configuration_path': config_path,
                    'configuration_sha256': config_sha,
                    'elapsed_seconds': time.perf_counter() - t0,
                }
                write_trajectory(stream, row, trajectory)
                if trajectory == 1 or trajectory % 20 == 0 or trajectory == planned:
                    print(json.dumps(row, sort_keys=True), flush=True)
                if saved >= max_save:
                    break
            os.fsync(stream.fileno())

        production_delta_h = np.asarray(all_delta_h, dtype=float)
        manifest['actual_trajectories'] = actual
        manifest['saved_configurations'] = saved
        manifest['production_accepts'] = accepted_production
        manifest['production_trajectories'] = production_count
        manifest['production_acceptance_rate'] = (
            accepted_production / production_count if production_count else None
        )
        atomic_json(manifest_path, manifest)
        receipt.update({
            'status': 'COMPLETED',
            'ended_utc': utc_now(),
            'actual_trajectories': actual,
            'saved_configurations': saved,
            'production_accepts': accepted_production,
            'production_trajectories': production_count,
            'production_acceptance_rate': (
                accepted_production / production_count if production_count else None
            ),
            'production_delta_h_mean': float(np.mean(production_delta_h)),
            'production_delta_h_std': float(np.std(production_delta_h, ddof=1)),
            'production_delta_h_min': float(np.min(production_delta_h)),
            'production_delta_h_max': float(np.max(production_delta_h)),
            'manifest_sha256': sha256(manifest_path),
            'trajectory_log_sha256': sha256(trajectory_path),
            'wall_seconds': time.perf_counter() - started,
        })
        atomic_json(receipt_path, receipt)
        print(json.dumps({key: receipt[key] for key in (
            'status', 'actual_trajectories', 'saved_configurations',
            'production_accepts', 'production_trajectories',
            'production_acceptance_rate', 'production_delta_h_mean',
            'production_delta_h_std', 'wall_seconds',
        )}, sort_keys=True), flush=True)
        return 0
    except Exception as error:
        receipt.update({
            'status': 'FAILED',
            'ended_utc': utc_now(),
            'error': repr(error),
            'wall_seconds': time.perf_counter() - started,
        })
        atomic_json(receipt_path, receipt)
        raise


if __name__ == '__main__':
    sys.exit(main())
