"""Measure C_{source,sink}(t) for several Gaussian source smearings (C2, GPU).

For a Hermitian sink kernel K_i = H^{n_i} the correlator with source j is
    C_{j,i}(t) = <S_j, H^{n_i} S_j> = || H^{n_i/2} S_j ||^2,
so one inversion per source is enough. Writes a new array; does not touch the
frozen single-source measurement.
"""
import hashlib
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from .common import digest, fingerprint, indices, write_json
from .smearing_contract import validate_source_sink_smearing


DEFAULT_MULTISOURCE_PROTOCOL = Path(__file__).with_name("protocol_multisource.json")


def require_fresh_output_path(path):
    """Reject existing output paths so a new generation cannot overwrite data."""
    output = Path(path)
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Refusing to reuse existing multisource output path: {output}")
    return output


def read_protocol_snapshot(protocol_path=None):
    """Read and hash the exact protocol bytes used by this measurement."""
    path = DEFAULT_MULTISOURCE_PROTOCOL if protocol_path is None else Path(protocol_path)
    raw = path.read_bytes()
    protocol_data = json.loads(raw)
    if not isinstance(protocol_data, dict):
        raise ValueError("Multisource protocol must be a JSON object")
    return protocol_data, hashlib.sha256(raw).hexdigest()


def multisource_source_hashes():
    """Hash this entry point and its source/sink parameter contract."""
    return {
        "measure_multisource.py": digest(Path(__file__)),
        "smearing_contract.py": digest(Path(__file__).with_name("smearing_contract.py")),
    }


def multisource_generation_id(protocol_sha256, protocol_hash, split, ids, source_sha256):
    """Bind protocol bytes, code, split and ordered configuration IDs."""
    return fingerprint({
        "schema": "s16t16-multisource-generation-v2",
        "protocol_sha256": protocol_sha256,
        "protocol_hash": protocol_hash,
        "split": split,
        "ids": [int(cfg) for cfg in ids],
        "source_sha256": source_sha256,
    })


def preflight_multisource(output, split, limit=None, protocol_path=None):
    """Validate a frozen plan without importing GPU libraries or creating output."""
    path = DEFAULT_MULTISOURCE_PROTOCOL if protocol_path is None else Path(protocol_path)
    p, protocol_sha256 = read_protocol_snapshot(path)
    smearing_contract = validate_source_sink_smearing(p)
    protocol_hash = fingerprint(p)
    available_ids = indices(split, p)
    if limit is not None:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
            raise ValueError("limit must be a non-negative integer")
        ids = available_ids[:limit]
    else:
        ids = available_ids
    source_sha256 = multisource_source_hashes()
    generation = multisource_generation_id(protocol_sha256, protocol_hash, split, ids, source_sha256)
    fresh_output = require_fresh_output_path(output)
    return {
        "protocol": p,
        "protocol_path": path,
        "protocol_sha256": protocol_sha256,
        "protocol_hash": protocol_hash,
        "smearing_contract": smearing_contract,
        "split": split,
        "ids": [int(cfg) for cfg in ids],
        "source_sha256": source_sha256,
        "generation": generation,
        "output": fresh_output,
    }


def apply_matched_propagator_smear(source12, output12, steps, alpha, wuppertal_smear):
    """Apply the sink's low-level Wuppertal callable to all 12 source columns."""
    if isinstance(steps, bool) or not isinstance(steps, int) or steps <= 0:
        raise ValueError("Matched source smearing steps must be a positive integer")
    for spin in range(4):
        for color in range(3):
            field = source12.getFermion(spin, color)
            smeared = wuppertal_smear(field, steps, alpha)
            output12.setFermion(smeared, spin, color)
    return output12


def measure_multisource(output, split, limit=None, protocol_path=None, preflight_only=False):
    # Fail before importing GPU libraries, creating an output directory, or
    # initializing QUDA when source.gaussian12 and sink use different alpha.
    plan = preflight_multisource(output, split, limit, protocol_path)
    if preflight_only:
        return plan
    p = plan["protocol"]
    path = plan["protocol_path"]
    protocol_sha256 = plan["protocol_sha256"]
    protocol_hash = plan["protocol_hash"]
    smearing_contract = plan["smearing_contract"]
    ids = plan["ids"]
    source_sha256 = plan["source_sha256"]
    generation = plan["generation"]
    output = plan["output"]

    import cupy as cp
    from mpi4py import MPI
    from pyquda_utils import core, io, source

    sources = p['source_smear']
    # exist_ok=False closes the race between the read-only preflight and mkdir.
    output.mkdir(parents=True, exist_ok=False)
    core.init([1, 1, 1, 1], p['geometry'], resource_path='.cache/quda')
    if MPI.COMM_WORLD.Get_size() != 1:
        raise ValueError('Pilot supports one MPI rank')
    latt = core.LatticeInfo(p['geometry'], p['t_boundary'], 1.0)
    dirac = core.getWilson(latt, 1/(2*p['kappa'])-4, p['tolerance'], p['max_iterations'])
    rows, records = [], []
    for cfg in ids:
        start = perf_counter()
        gauge = io.readNERSCGauge(f"{p['ensemble']}/wilson_b6.{cfg}")
        if list(gauge.latt_info.global_size) != list(p['geometry']):
            raise ValueError('Wrong geometry')
        per_source = []
        with dirac.useGauge(gauge):
            for spec in sources:
                src = source.source12(latt, 'point', p['source'])
                if spec['steps']:
                    smeared_src = core.LatticePropagator(latt)
                    with gauge.use() as source_smear_dirac:
                        src = apply_matched_propagator_smear(
                            src, smeared_src, spec['steps'], p['alpha'],
                            source_smear_dirac.wuppertalSmear,
                        )
                prop = core.invertPropagator(dirac, src, 12)
                residual = 0.0
                for spin in range(4):
                    for color in range(3):
                        b = src.getFermion(spin, color)
                        r = dirac.mat(prop.getFermion(spin, color)) - b
                        residual = max(residual, float((r.norm2()/b.norm2())**0.5))
                limit_tol = max(1e-8, 10 * p['tolerance'])
                if residual > limit_tol:
                    raise ValueError(f'Residual {residual} above {limit_tol} for cfg {cfg}')
                c = np.zeros((len(p['powers']), p['geometry'][3]))
                with gauge.use() as gdirac:
                    for spin in range(4):
                        for color in range(3):
                            field = prop.getFermion(spin, color)
                            previous = 0
                            for j, power in enumerate(p['powers']):
                                n = power // 2
                                if n > previous:
                                    field = gdirac.wuppertalSmear(field, n-previous, p['alpha'])
                                density = cp.sum(cp.abs(field.data)**2, axis=(-2, -1))
                                c[j] += density.sum(axis=(0, 2, 3, 4)).get()
                                previous = n
                per_source.append(c)
        rows.append(per_source)
        records.append({'id': int(cfg), 'gauge_sha256': digest(f"{p['ensemble']}/wilson_b6.{cfg}"),
                        'seconds': perf_counter()-start})
        np.savez_compressed(output / f'{split}.npz', ids=np.asarray(ids[:len(rows)]),
                            correlators=np.asarray(rows), powers=np.asarray(p['powers']),
                            sources=np.asarray([s['name'] for s in sources]),
                            protocol_hash=protocol_hash, protocol_sha256=protocol_sha256,
                            generation=generation)
        write_json(output / f'{split}_provenance.json',
                    {'schema': 's16t16-multisource-provenance-v2',
                    'protocol_path': str(path), 'protocol_sha256': protocol_sha256,
                    'protocol_hash': protocol_hash, 'generation': generation,
                    'source_sha256': source_sha256, 'protocol': p,
                    'records': records, 'source_smear': sources,
                    'smearing_contract': smearing_contract})
        print(f'multisource cfg {cfg}: {records[-1]["seconds"]:.2f}s', flush=True)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--split', default='development')
    parser.add_argument('--limit', type=int, default=None)
    parser.add_argument('--protocol', type=Path, default=DEFAULT_MULTISOURCE_PROTOCOL)
    parser.add_argument('--preflight-only', action='store_true',
                        help='validate protocol, split, generation identity, and fresh output path without importing GPU libraries')
    args = parser.parse_args()
    result = measure_multisource(args.output, args.split, args.limit,
                                 protocol_path=args.protocol, preflight_only=args.preflight_only)
    if args.preflight_only:
        print(json.dumps({
            "status": "cpu_preflight_ready_not_authorized",
            "split": result["split"],
            "configuration_ids": result["ids"],
            "protocol_path": str(result["protocol_path"]),
            "protocol_sha256": result["protocol_sha256"],
            "protocol_hash": result["protocol_hash"],
            "generation": result["generation"],
            "source_sha256": result["source_sha256"],
            "smearing_contract": result["smearing_contract"],
            "output_path": str(result["output"]),
        }, indent=2))
