"""Parallel, receipt-preserving resume driver for the frozen amendment01 MC."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import shutil
import time

import numpy as np

from . import common
from .full_gate_executor import SCENARIOS
from .full_gate_mc import cp
from .synthetic_adapter import execute
from .synthetic_worlds import generate_world


def atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    tmp.replace(path)


def source_hashes_match(plan_spec: dict) -> None:
    base = Path(__file__).parent
    for rel, expected in plan_spec['code_hashes'].items():
        actual = hashlib.sha256((base / rel).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f'frozen plan source changed: {rel}')


def expected_seed(scenario: str, dataset: int) -> int:
    return 20261122 + SCENARIOS.index(scenario) * 100000 + dataset


def receipt_paths(dataset_root: Path):
    root_receipt = dataset_root / 'adapter_parity.json'
    if root_receipt.exists():
        yield root_receipt
    attempts = sorted(dataset_root.glob('attempt_*/adapter_parity.json'))
    yield from attempts


def load_receipt(dataset_root: Path, scenario: str, dataset: int):
    malformed = []
    for path in receipt_paths(dataset_root):
        try:
            value = json.loads(path.read_text())
        except Exception as exc:
            malformed.append({'path': str(path), 'error': f'{type(exc).__name__}: {exc}'})
            continue
        if value.get('scenario') != scenario or value.get('seed') != expected_seed(scenario, dataset):
            raise RuntimeError(f'receipt identity mismatch: {path}')
        if value.get('status') not in ('PASS', 'EXPECTED_REJECTION'):
            raise RuntimeError(f'nonterminal or failed receipt needs review: {path}: {value.get("status")}')
        return path, value, malformed
    return None, None, malformed


def validate_interrupted_root(dataset_root: Path, scenario: str, dataset: int) -> bool:
    """Check any raw-only attempt against deterministic inputs before replaying it."""
    raw_path = dataset_root / 'raw_inputs.npz'
    if not raw_path.exists():
        return False
    protocol = common.protocol()
    protocol.update(
        development=[0, 119], validation=[130, 189], gap=[120, 129],
        bootstrap_samples=128, outer_samples=200, inner_samples=64,
        optimizer_max_iterations=100, synthetic=True,
        synthetic_fixed_candidates={'baseline_channel': 1, 'candidate_channel': 2},
    )
    rng = np.random.default_rng(expected_seed(scenario, dataset))
    expected_dev = generate_world(rng, scenario, protocol, 120)
    expected_val = generate_world(rng, scenario, protocol, 60)
    with np.load(raw_path) as raw:
        dev = raw['development']
        val = raw['validation']
    return (
        np.array_equal(dev, expected_dev, equal_nan=True)
        and np.array_equal(val, expected_val, equal_nan=True)
    )


def next_attempt(dataset_root: Path) -> Path:
    used = []
    for path in dataset_root.glob('attempt_*'):
        if path.is_dir() and path.name.removeprefix('attempt_').isdigit():
            used.append(int(path.name.removeprefix('attempt_')))
    return dataset_root / f'attempt_{max(used, default=0) + 1:03d}'


def worker(scenario: str, dataset: int, destination: str):
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    result = execute(path, scenario, True, seed=expected_seed(scenario, dataset))
    result['elapsed_seconds'] = time.perf_counter() - started
    atomic_json(path / 'adapter_parity.json', result)
    return {'scenario': scenario, 'dataset': dataset, 'attempt': path.name, 'receipt': result}


def summarize(rows: list[dict]) -> dict:
    by_scenario = {}
    for scenario in SCENARIOS:
        cell = [row for row in rows if row['scenario'] == scenario]
        if not cell:
            continue
        stats = {}
        outcomes = {
            'reference_acceptance': lambda row: bool(row.get('reference_accepted')),
            'candidate_certification': lambda row: bool(row.get('candidate_certified')),
            'failure': lambda row: bool(row.get('failure')),
            'abstain': lambda row: row.get('status') == 'EXPECTED_REJECTION' or not row.get('reference_accepted', False),
        }
        for name, predicate in outcomes.items():
            k = sum(predicate(row) for row in cell)
            lo, hi = cp(k, len(cell))
            stats[name] = {
                'k': k, 'n': len(cell), 'cp95': [float(lo), float(hi)],
                'half_width': float((hi - lo) / 2),
                'precision_status': 'PASS' if (hi - lo) / 2 <= .05 else 'INCONCLUSIVE',
            }
        stats['completed_datasets'] = len(cell)
        by_scenario[scenario] = stats
    return by_scenario


def write_plot(path: Path, rows: list[dict], planned_per_cell: int):
    import matplotlib.pyplot as plt

    metrics = (
        ('reference_acceptance', 'Reference accepted'),
        ('candidate_certification', 'Candidate certified'),
        ('failure', 'Failure'),
        ('abstain', 'Abstain'),
    )
    fig, axes = plt.subplots(4, 2, figsize=(13, 13), sharex=True, sharey=True)
    axes = axes.ravel()
    for ax, (metric, title) in zip(axes, metrics):
        for i, scenario in enumerate(SCENARIOS):
            cell = [row for row in rows if row['scenario'] == scenario]
            if not cell:
                continue
            k = sum(
                bool(row.get('reference_accepted')) if metric == 'reference_acceptance'
                else bool(row.get('candidate_certified')) if metric == 'candidate_certification'
                else bool(row.get('failure')) if metric == 'failure'
                else row.get('status') == 'EXPECTED_REJECTION' or not row.get('reference_accepted', False)
                for row in cell
            )
            lo, hi = cp(k, len(cell))
            ax.errorbar(
                i, k / len(cell),
                yerr=[[k / len(cell) - lo], [hi - k / len(cell)]],
                fmt='o', capsize=2,
            )
        ax.set_title(title)
        ax.set_ylim(-.03, 1.03)
        ax.set_xticks(range(len(SCENARIOS)), SCENARIOS, rotation=55, ha='right', fontsize=7)
        ax.grid(alpha=.25)
    axes[-1].axis('off')
    fig.suptitle(f'Candidate full-certificate Monte Carlo rates (CP95); target N={planned_per_cell}/cell')
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main(plan_dir: Path, dest: Path, workers: int = 6, max_per_cell: int | None = None):
    plan_dir = plan_dir.resolve()
    dest = dest.resolve()
    plan_spec = json.loads((plan_dir / 'executor_spec.json').read_text())
    source_hashes_match(plan_spec)
    planned = int(plan_spec['n_per_cell'])
    n = planned if max_per_cell is None else min(planned, int(max_per_cell))
    if n < 1 or workers < 1:
        raise ValueError('workers and max_per_cell must be positive')
    dest.mkdir(parents=True, exist_ok=True)
    driver_path = Path(__file__).resolve()
    driver_spec = {
        'schema': 'pion-full-gate-parallel-driver-v1',
        'plan_executor_spec_sha256': hashlib.sha256((plan_dir / 'executor_spec.json').read_bytes()).hexdigest(),
        'driver_sha256': hashlib.sha256(driver_path.read_bytes()).hexdigest(),
        'workers': workers,
        'planned_per_cell': planned,
        'run_per_cell': n,
        'source_hashes_match': True,
        'resume_rule': 'reuse valid receipts; preserve incomplete attempt folders; retry only into a new attempt_NNN folder',
    }
    frozen_driver = dest / 'parallel_driver_spec.json'
    if frozen_driver.exists() and json.loads(frozen_driver.read_text()) != driver_spec:
        raise RuntimeError('parallel driver spec changed; use a new output directory')
    if not frozen_driver.exists():
        atomic_json(frozen_driver, driver_spec)

    completed: dict[tuple[str, int], dict] = {}
    pending = []
    replay_verified = []
    malformed_attempts = []
    for scenario in SCENARIOS:
        for dataset in range(n):
            dataset_root = dest / scenario / f'dataset_{dataset:04d}'
            receipt_path, receipt, malformed = load_receipt(dataset_root, scenario, dataset)
            malformed_attempts.extend(malformed)
            if receipt is not None:
                completed[(scenario, dataset)] = {
                    'scenario': scenario, 'dataset': dataset,
                    'receipt': str(receipt_path.relative_to(dest)), **receipt,
                }
                continue
            if (dataset_root / 'raw_inputs.npz').exists():
                same = validate_interrupted_root(dataset_root, scenario, dataset)
                replay_verified.append({
                    'scenario': scenario, 'dataset': dataset,
                    'raw_inputs': str((dataset_root / 'raw_inputs.npz').relative_to(dest)),
                    'deterministic_replay_matches': same,
                })
                if not same:
                    raise RuntimeError(f'interrupted raw input mismatch; preserve and inspect: {dataset_root}')
            target = next_attempt(dataset_root)
            pending.append((scenario, dataset, str(target)))

    atomic_json(dest / 'interrupted_attempts.json', {
        'replay_checked': replay_verified,
        'malformed_receipts_preserved': malformed_attempts,
        'note': 'No incomplete folder was overwritten. Deterministically matching raw-only inputs are replayed into a new attempt folder.',
    })

    def write_progress(status: str, last=None):
        rows = list(completed.values())
        atomic_json(dest / 'checkpoint.json', {
            'status': status,
            'completed': len(rows),
            'planned': len(SCENARIOS) * n,
            'full_plan_planned': len(SCENARIOS) * planned,
            'last_completed': last,
            'rates': summarize(rows),
            'physical_score': None,
            'driver_spec': 'parallel_driver_spec.json',
        })
        if status in ('COMPLETE', 'DRY_RUN_COMPLETE') or len(rows) % 50 == 0:
            write_plot(dest / 'candidate_rates_progress.png', rows, planned)
            atomic_json(dest / 'progress_rows.json', {'rows': rows, 'physical_score': None})

    write_progress('RUNNING')
    started = time.perf_counter()
    if pending:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(worker, scenario, dataset, target): (scenario, dataset, target)
                for scenario, dataset, target in pending
            }
            for future in as_completed(futures):
                scenario, dataset, target = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    atomic_json(dest / 'driver_error.json', {
                        'scenario': scenario, 'dataset': dataset, 'attempt': target,
                        'error': f'{type(exc).__name__}: {exc}',
                    })
                    write_progress('BLOCKED', {'scenario': scenario, 'dataset': dataset})
                    raise
                receipt_path = Path(target) / 'adapter_parity.json'
                completed[(scenario, dataset)] = {
                    'scenario': scenario, 'dataset': dataset,
                    'receipt': str(receipt_path.relative_to(dest)), **result['receipt'],
                }
                write_progress('RUNNING', {'scenario': scenario, 'dataset': dataset})

    rows = [completed[key] for key in sorted(completed, key=lambda key: (SCENARIOS.index(key[0]), key[1]))]
    status = 'COMPLETE' if n == planned else 'DRY_RUN_COMPLETE'
    atomic_json(dest / 'dataset_results.json', {'rows': rows, 'physical_score': None})
    atomic_json(dest / 'aggregate.json', {
        'status': status, 'n_executed': len(rows), 'n_planned': len(SCENARIOS) * planned,
        'n_this_run_target': len(SCENARIOS) * n, 'rates': summarize(rows),
        'physical_score': None, 'wall_seconds': time.perf_counter() - started,
    })
    write_progress(status)
    (dest / 'README.md').write_text(
        '# Candidate full-certificate MC execution\n\n'
        f'Status: {status}; this executor target is {len(SCENARIOS) * n}/{len(SCENARIOS) * planned} worlds.\n\n'
        'All rows refer to immutable adapter receipts. Dataset roots with incomplete earlier attempts are preserved; retries use a new attempt directory. '
        'Raw inputs, seed, rejection phase and source hashes remain with each dataset. `candidate_rates_progress.png` shows marginal CP95 rate intervals; '
        'precision status only means the interval half-width target is met, not that a physical threshold passed. Failure is a subset of abstention. '
        'Synthetic certificates keep `physical_score=null`; no physical anchor, GPU run or publication-level physical conclusion follows.\n'
    )
    return status


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan-dir', required=True)
    parser.add_argument('--dest', required=True)
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--max-per-cell', type=int)
    args = parser.parse_args()
    main(Path(args.plan_dir), Path(args.dest), args.workers, args.max_per_cell)
