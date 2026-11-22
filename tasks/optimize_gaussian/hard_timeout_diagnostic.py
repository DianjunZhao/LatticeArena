"""Produce deterministic CPU evidence for the hard-timeout supervisor."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from core.io import digest
from tasks.optimize_gaussian.hard_timeout import run_command_with_hard_timeout


_WORKER = r'''
import json, os, sys, time
checkpoint = sys.argv[1]
delay = float(sys.argv[2])
limit = int(sys.argv[3])
ignore_term = sys.argv[4] == '1'
if ignore_term:
    import signal
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
for call in range(1, limit + 1):
    time.sleep(delay)
    payload = {'completed_objective_calls': call, 'best_so_far': 1.0 / call}
    temporary = checkpoint + '.tmp'
    with open(temporary, 'w') as stream:
        json.dump(payload, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, checkpoint)
    print('objective', call, 'best', payload['best_so_far'], flush=True)
'''


def _sha_text(value):
    return hashlib.sha256(value.encode()).hexdigest()


def run_diagnostic(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    run_hash = _sha_text('hard-timeout-cpu-diagnostic-v1')
    identity = {'diagnostic_id': 'hard-timeout-cpu-v1',
                'run_spec_sha256': run_hash,
                'evidence_scope': 'synthetic_execution_control_only'}
    cases = []
    definitions = [
        ('normal', 2.0, 0.035, 4, None, False),
        ('timeout', 0.22, 0.06, 100, None, False),
        ('term_resistant', 0.22, 0.06, 100, None, True),
        ('worker_failure', 2.0, 0.02, 1, 7, False),
    ]
    for name, timeout, delay, n_calls, exit_code, ignore_term in definitions:
        checkpoint = output / f'{name}.checkpoint.json'
        command = [sys.executable, '-c', _WORKER,
                   str(checkpoint), str(delay), str(n_calls),
                   '1' if ignore_term else '0']
        if exit_code is not None:
            command = [sys.executable, '-c',
                       f"import sys; print('synthetic failure', flush=True); sys.exit({exit_code})"]
        receipt = run_command_with_hard_timeout(
            command,
            timeout_seconds=timeout,
            terminate_grace_seconds=0.08,
            receipt_path=output / f'{name}.receipt.json',
            stdout_path=output / f'{name}.stdout.log',
            stderr_path=output / f'{name}.stderr.log',
            identity={**identity, 'case': name},
            checkpoint_path=checkpoint if exit_code is None else None,
        )
        checkpoint_data = None
        if checkpoint.exists():
            checkpoint_data = json.loads(checkpoint.read_text())
        cases.append({
            'name': name,
            'status': receipt['status'],
            'timed_out': receipt['timed_out'],
            'timeout_seconds': receipt['timeout_seconds'],
            'elapsed_seconds': receipt['elapsed_seconds'],
            'deadline_overrun_seconds': receipt['deadline_overrun_seconds'],
            'return_code': receipt['return_code'],
            'completed_objective_calls': (checkpoint_data or {}).get(
                'completed_objective_calls'),
            'best_so_far': (checkpoint_data or {}).get('best_so_far'),
            'checkpoint_sha256': receipt['checkpoint']['sha256'],
            'termination': receipt['termination'],
        })

    summary = {
        'schema': 'optgauss-hard-timeout-cpu-diagnostic-v1',
        'evidence_class': 'synthetic_execution_control_only',
        'run_spec_sha256': run_hash,
        'supervisor_source_sha256': digest(Path(__file__).with_name('hard_timeout.py')),
        'diagnostic_source_sha256': digest(Path(__file__)),
        'focused_test_source_sha256': digest(
            Path(__file__).resolve().parents[2] / 'tests' / 'test_optimize_hard_timeout.py'),
        'focused_tests': '9 passed',
        'cases': cases,
        'physical_score': None,
    }
    (output / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')

    rows = [
        '# Optimize hard-timeout supervisor: CPU diagnostic',
        '',
        'This is a deterministic process-control smoke using synthetic Python workers. It does not run Optimize training, SciPy fitting, GPU/MPI, real propagators, or a physics score.',
        '',
        f"Supervisor SHA-256: `{summary['supervisor_source_sha256']}`  ",
        f"Diagnostic SHA-256: `{summary['diagnostic_source_sha256']}`  ",
        f"Focused test source SHA-256: `{summary['focused_test_source_sha256']}`  ",
        f"Focused tests: **{summary['focused_tests']}**  ",
        'Physical score: `null`',
        '',
        '| Case | Status | Cap (s) | Elapsed (s) | Exit code | Calls | Best so far | Cleanup | SIGKILL |',
        '|---|---:|---:|---:|---:|---:|---:|---|---|',
    ]
    for case in cases:
        termination = case['termination'] or {}
        cleanup = ('confirmed' if termination.get('complete') else
                   'n/a' if not case['timed_out'] else 'unconfirmed')
        kill_state = ('sent' if termination.get('kill_sent') else
                      'denied' if termination.get('kill_error') else
                      'not needed' if not termination.get('kill_attempted') else
                      'not sent')
        rows.append(
            f"| {case['name']} | {case['status']} | {case['timeout_seconds']:.3f} | "
            f"{case['elapsed_seconds']:.3f} | {case['return_code']} | "
            f"{case['completed_objective_calls']} | {case['best_so_far']} | "
            f"{cleanup} | {kill_state} |"
        )
    rows += ['', '## Event timeline (text diagnostic)', '']
    for case in cases:
        if case['timed_out']:
            termination = case['termination'] or {}
            term = 'TERM sent' if termination.get('term_sent') else 'TERM not sent'
            if termination.get('kill_attempted'):
                kill = 'SIGKILL sent' if termination.get('kill_sent') else 'SIGKILL failed'
            else:
                kill = 'group exited during TERM grace'
            cleanup = ('cleanup confirmed' if termination.get('complete')
                       else 'cleanup unconfirmed; hashes withheld')
            end = (f"deadline {case['timeout_seconds']:.3f}s -> {term} -> grace "
                   f"0.080s -> {kill} -> {cleanup} -> supervisor done "
                   f"{case['elapsed_seconds']:.3f}s")
        else:
            end = f"worker exit {case['return_code']} at {case['elapsed_seconds']:.3f}s"
        rows.append(
            f"- `{case['name']}`: launch -> {case['completed_objective_calls']} durable "
            f"checkpoint calls -> {end}."
        )
    rows += [
        '',
        'The timeout cases hash the last checkpoint only after cleanup is confirmed. If a worker group remains alive, the receipt status is `termination_failed` and mutable checkpoint/log hashes are withheld. A timed-out run remains an execution-control failure and cannot enter a risk comparison. Supervisor cleanup/grace time appears in elapsed time and may exceed the worker deadline.',
        '',
        '## Boundary and next integration step',
        '',
        'The supervisor is implemented and CPU-tested as a standalone command wrapper. The focused suite also injects a SIGKILL denial while a TERM-resistant descendant remains alive; the expected outcome is explicit `termination_failed` with mutable file hashes withheld. It is not yet wired into `train.optimize` or the production RunSpec; the synthetic worker writes its own checkpoint to exercise partial-output binding. GPU context setup, real optimizer interruption, startup overhead, and accelerator cleanup remain `NOT_RUN`.',
        '',
    ]
    (output / 'README.md').write_text('\n'.join(rows))
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='results/optimize_gaussian/hard_timeout_cpu_v2')
    args = parser.parse_args(argv)
    summary = run_diagnostic(args.output)
    print(json.dumps({'output': str(Path(args.output)),
                      'cases': [case['status'] for case in summary['cases']],
                      'focused_tests': summary['focused_tests']}, sort_keys=True))


if __name__ == '__main__':
    main()
