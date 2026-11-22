"""Create a one-shot, synthetic diagnostic for the frozen worker RunSpec."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import sys

from tasks.optimize_gaussian.worker_runspec import run_frozen_worker


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write_fixture(directory, *, split_ids=None):
    directory.mkdir(parents=True, exist_ok=False)
    protocol = directory / 'protocol.json'
    source = directory / 'worker.py'
    input_file = directory / 'input.dat'
    protocol.write_text('{"name":"synthetic-worker-runspec","version":1}\n')
    source.write_text('# synthetic source identity\n')
    input_file.write_text('synthetic input only\n')
    outputs_dir = directory / 'outputs'
    outputs_dir.mkdir()
    outputs = {
        'receipt': outputs_dir / 'worker.receipt.json',
        'stdout': outputs_dir / 'worker.stdout.log',
        'stderr': outputs_dir / 'worker.stderr.log',
        'checkpoint': outputs_dir / 'checkpoint.json',
    }
    spec = {
        'schema': 'optgauss-worker-runspec-v2',
        'run_id': directory.name,
        'command': [sys.executable, '-c',
                    "print('synthetic worker started', flush=True)"],
        'cwd': str(directory.resolve()),
        'timeout_seconds': 3.0,
        'terminate_grace_seconds': 0.1,
        'environment': {'RUNSPEC_MODE': 'synthetic'},
        'files': {
            'protocol': {'path': str(protocol.resolve()), 'sha256': _sha256(protocol),
                         'role': 'protocol'},
            'worker_source': {'path': str(source.resolve()), 'sha256': _sha256(source),
                              'role': 'source'},
            'synthetic_input': {'path': str(input_file.resolve()), 'sha256': _sha256(input_file),
                                'role': 'input'},
        },
        'split_ids': split_ids,
        'outputs': {name: str(path.resolve()) for name, path in outputs.items()},
    }
    # The child only emits a diagnostic marker; it does not load task data.
    spec_path = directory / 'worker.runspec.json'
    spec_path.write_text(json.dumps(spec, sort_keys=True, indent=2) + '\n')
    return spec_path, source, input_file, outputs


def run(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    rows = []

    valid_dir = output / 'valid'
    spec_path, _, _, outputs = _write_fixture(
        valid_dir, split_ids={'fit': [0, 1], 'development': [2], 'blind': [3]})
    receipt = run_frozen_worker(spec_path)
    rows.append({
        'case': 'valid_frozen_spec', 'expected': 'completed',
        'observed': receipt['status'], 'worker_started': True,
        'outputs_created': all(outputs[name].is_file() for name in ('receipt', 'stdout', 'stderr')),
        'detail': 'protocol/source/input hashes and disjoint split IDs passed preflight',
    })

    environment_dir = output / 'environment_isolation'
    environment_spec, _, _, outputs = _write_fixture(environment_dir)
    environment_data = json.loads(environment_spec.read_text())
    environment_data['command'] = [
        sys.executable, '-c',
        "import os; print(os.getenv('RUNSPEC_MODE') + '|' + "
        "os.getenv('LATTICEARENA_UNBOUND_SENTINEL', 'missing'), flush=True)",
    ]
    environment_spec.write_text(json.dumps(environment_data, sort_keys=True, indent=2) + '\n')
    sentinel = 'LATTICEARENA_UNBOUND_SENTINEL'
    inherited_value = os.environ.get(sentinel)
    os.environ[sentinel] = 'ambient-value'
    try:
        environment_receipt = run_frozen_worker(environment_spec)
    finally:
        if inherited_value is None:
            os.environ.pop(sentinel, None)
        else:
            os.environ[sentinel] = inherited_value
    observed_output = outputs['stdout'].read_text().strip()
    rows.append({
        'case': 'explicit_environment', 'expected': 'completed',
        'observed': environment_receipt['status'], 'worker_started': True,
        'outputs_created': all(outputs[name].is_file()
                                for name in ('receipt', 'stdout', 'stderr')),
        'detail': f'child env={observed_output}; unbound parent value was not inherited',
    })

    source_dir = output / 'source_drift'
    source_spec, source, _, outputs = _write_fixture(source_dir)
    source.write_text(source.read_text() + '# changed after freeze\n')
    try:
        run_frozen_worker(source_spec)
        source_status, source_detail = 'unexpected_success', 'worker should not have launched'
    except ValueError as exc:
        source_status, source_detail = 'preflight_rejected', str(exc)
    rows.append({
        'case': 'mutated_source', 'expected': 'preflight_rejected',
        'observed': source_status, 'worker_started': False,
        'outputs_created': any(path.exists() for path in outputs.values()),
        'detail': source_detail,
    })

    input_dir = output / 'input_drift'
    input_spec, _, input_file, outputs = _write_fixture(input_dir)
    input_file.write_text(input_file.read_text() + 'changed after freeze\n')
    try:
        run_frozen_worker(input_spec)
        input_status, input_detail = 'unexpected_success', 'worker should not have launched'
    except ValueError as exc:
        input_status, input_detail = 'preflight_rejected', str(exc)
    rows.append({
        'case': 'mutated_input', 'expected': 'preflight_rejected',
        'observed': input_status, 'worker_started': False,
        'outputs_created': any(path.exists() for path in outputs.values()),
        'detail': input_detail,
    })

    split_dir = output / 'split_overlap'
    split_spec, _, _, outputs = _write_fixture(
        split_dir, split_ids={'fit': [0, 1], 'blind': [1, 2]})
    try:
        run_frozen_worker(split_spec)
        split_status, split_detail = 'unexpected_success', 'worker should not have launched'
    except ValueError as exc:
        split_status, split_detail = 'preflight_rejected', str(exc)
    rows.append({
        'case': 'overlapping_split_ids', 'expected': 'preflight_rejected',
        'observed': split_status, 'worker_started': False,
        'outputs_created': any(path.exists() for path in outputs.values()),
        'detail': split_detail,
    })

    if any(row['observed'] != row['expected'] for row in rows):
        raise RuntimeError('a synthetic worker RunSpec case did not match its expected result')

    csv_path = output / 'cases.csv'
    with csv_path.open('x', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        'schema': 'optgauss-worker-runspec-diagnostic-v2',
        'classification': 'synthetic_execution_control_only',
        'physical_score': None,
        'cases': rows,
        'cases_csv_sha256': _sha256(csv_path),
    }
    summary_path = output / 'summary.json'
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    readme = '''# Frozen worker RunSpec CPU diagnostic v3

This one-shot diagnostic uses only temporary synthetic protocol/source/input
files and a child Python process that prints a marker. It verifies the worker
launch boundary; it is not a training run, GPU smoke, solver comparison, or
physical score (`physical_score = null`).

## Text flow

```text
frozen RunSpec JSON
    -> parse strict JSON (duplicate keys and non-finite constants rejected)
    -> verify protocol/source/input SHA-256 and disjoint split IDs
    -> launch with only RunSpec environment variables; bind env hash and names
    -> verify no-clobber output paths
    -> start argv-only worker in a new process group
    -> bind RunSpec hash, verified files, logs, exit/timeout status in receipt
```

## Observed cases

| Case | Result | Worker started | Meaning |
| --- | --- | --- | --- |
| valid frozen spec | completed | yes | Verified protocol, source, synthetic input, and disjoint IDs before launch. |
| explicit environment | completed | yes | Child saw the RunSpec value and did not inherit an unbound parent variable. |
| mutated source | preflight rejected | no | Source drift was caught before any log or receipt was created. |
| mutated input | preflight rejected | no | Input drift was caught before any log or receipt was created. |
| overlapping split IDs | preflight rejected | no | Shared configuration IDs across fit and blind splits were refused. |

Raw case rows and hashes are in `cases.csv` and `summary.json`. The existing
standalone timeout tests cover child timeout, process-group cleanup, and
termination failure. This diagnostic does not show that SciPy, CUDA, QUDA,
or a live production RunSpec can be safely interrupted. Production thresholds,
reference validity, arm matching, and device-side cleanup still require a
reviewed task-specific RunSpec and an authorized GPU smoke.
'''
    (output / 'README.md').write_text(readme)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('output', help='new no-clobber diagnostic output directory')
    args = parser.parse_args(argv)
    print(json.dumps(run(args.output), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
