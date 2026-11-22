import hashlib
import json
import os
import sys

import pytest

from tasks.optimize_gaussian.hard_timeout import run_command_with_hard_timeout


def _paths(tmp_path, name='run'):
    return {
        'receipt_path': tmp_path / f'{name}.receipt.json',
        'stdout_path': tmp_path / f'{name}.stdout.log',
        'stderr_path': tmp_path / f'{name}.stderr.log',
    }


def _python(code, *args):
    return [sys.executable, '-c', code, *map(str, args)]


def test_worker_success_receipt_binds_logs_and_identity(tmp_path):
    paths = _paths(tmp_path)
    receipt = run_command_with_hard_timeout(
        _python("print('worker-ok', flush=True)"),
        timeout_seconds=5.0,
        identity={'run_spec_sha256': 'frozen-run', 'arm': 'A'},
        **paths,
    )

    assert receipt['status'] == 'completed'
    assert receipt['timed_out'] is False
    assert receipt['physical_score'] is None
    assert receipt['identity'] == {'arm': 'A', 'run_spec_sha256': 'frozen-run'}
    assert receipt['stdout']['sha256'] == hashlib.sha256(b'worker-ok\n').hexdigest()
    saved = json.loads(paths['receipt_path'].read_text())
    assert saved == receipt


def test_timeout_kills_worker_and_binds_partial_checkpoint(tmp_path):
    paths = _paths(tmp_path, 'timeout')
    checkpoint = tmp_path / 'timeout.checkpoint.json'
    code = (
        "import json, os, sys, time; "
        "p=sys.argv[1]; t=p+'.tmp'; "
        "open(t,'w').write(json.dumps({'completed_objective_calls': 2,'best_so_far':0.25})); "
        "os.replace(t,p); print('checkpoint-written',flush=True); time.sleep(20)"
    )
    receipt = run_command_with_hard_timeout(
        _python(code, checkpoint), timeout_seconds=0.2,
        terminate_grace_seconds=0.1,
        identity={'run_spec_sha256': 'frozen-run', 'arm': 'learned-W'},
        checkpoint_path=checkpoint, **paths,
    )

    assert receipt['status'] == 'hard_timeout'
    assert receipt['timed_out'] is True
    assert receipt['return_code'] != 0
    assert receipt['checkpoint']['sha256'] == hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    assert receipt['stdout']['sha256'] == hashlib.sha256(b'checkpoint-written\n').hexdigest()
    assert receipt['physical_score'] is None
    assert receipt['termination']['term_sent']
    assert receipt['termination']['complete']
    assert receipt['elapsed_seconds'] < 3.0


def test_worker_failure_is_distinct_from_timeout(tmp_path):
    paths = _paths(tmp_path, 'failure')
    receipt = run_command_with_hard_timeout(
        _python('raise SystemExit(7)'), timeout_seconds=5.0,
        identity={'run_spec_sha256': 'frozen-run'}, **paths,
    )
    assert receipt['status'] == 'worker_failed'
    assert receipt['timed_out'] is False
    assert receipt['return_code'] == 7


def test_launch_error_is_recorded_without_claiming_worker_failure(tmp_path):
    paths = _paths(tmp_path, 'launch-error')
    receipt = run_command_with_hard_timeout(
        [str(tmp_path / 'missing-worker')], timeout_seconds=1.0,
        identity={'run_spec_sha256': 'frozen-run'}, **paths,
    )
    assert receipt['status'] == 'launch_failed'
    assert receipt['timed_out'] is False
    assert receipt['return_code'] is None
    assert receipt['launch_error']['type'] == 'FileNotFoundError'
    assert receipt['stdout']['sha256'] == hashlib.sha256(b'').hexdigest()


@pytest.mark.skipif(os.name != 'posix', reason='requires POSIX process groups')
def test_timeout_kills_worker_descendants_in_same_process_group(tmp_path):
    paths = _paths(tmp_path, 'process-group')
    marker = tmp_path / 'grandchild-survived'
    grandchild_script = tmp_path / 'grandchild.py'
    worker_script = tmp_path / 'worker.py'
    grandchild_script.write_text(
        "import sys, time\ntime.sleep(0.8)\n"
        "open(sys.argv[1], 'w').write('late')\n"
    )
    worker_script.write_text(
        "import subprocess, sys, time\n"
        "subprocess.Popen([sys.executable, sys.argv[1], sys.argv[2]])\n"
        "print('spawned', flush=True)\ntime.sleep(20)\n"
    )
    receipt = run_command_with_hard_timeout(
        [sys.executable, str(worker_script), str(grandchild_script), str(marker)],
        timeout_seconds=0.15,
        terminate_grace_seconds=0.1,
        identity={'run_spec_sha256': 'frozen-run'}, **paths,
    )
    # Give an escaped child enough time to reveal itself if group termination failed.
    import time
    time.sleep(0.9)
    assert receipt['status'] == 'hard_timeout'
    assert receipt['termination']['scope'] == 'process_group'
    assert not marker.exists()


@pytest.mark.skipif(os.name != 'posix', reason='requires POSIX signals')
def test_sigterm_resistant_worker_is_forcefully_stopped(tmp_path):
    paths = _paths(tmp_path, 'term-resistant')
    code = (
        "import signal, time; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        "print('ignoring-term', flush=True); time.sleep(20)"
    )
    receipt = run_command_with_hard_timeout(
        _python(code), timeout_seconds=0.15, terminate_grace_seconds=0.05,
        identity={'run_spec_sha256': 'frozen-run'}, **paths,
    )

    assert receipt['status'] == 'hard_timeout'
    assert receipt['timed_out'] is True
    assert receipt['termination']['complete']
    assert receipt['termination']['term_sent']
    assert receipt['termination']['kill_attempted']
    assert (receipt['termination']['kill_sent']
            or receipt['termination']['leader_fallback_sent'])
    assert receipt['return_code'] != 0


@pytest.mark.skipif(os.name != 'posix', reason='requires POSIX process groups')
def test_unconfirmed_descendant_cleanup_withholds_unstable_hashes(tmp_path, monkeypatch):
    from tasks.optimize_gaussian import hard_timeout

    paths = _paths(tmp_path, 'cleanup-failure')
    marker = tmp_path / 'late-descendant-marker'
    grandchild_script = tmp_path / 'late_grandchild.py'
    worker_script = tmp_path / 'term_resistant_worker.py'
    grandchild_script.write_text(
        "import signal, sys, time\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "time.sleep(0.45)\n"
        "open(sys.argv[1], 'w').write('late')\n"
    )
    worker_script.write_text(
        "import signal, subprocess, sys, time\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "subprocess.Popen([sys.executable, sys.argv[1], sys.argv[2]])\n"
        "print('spawned-resistant-descendant', flush=True)\n"
        "time.sleep(20)\n"
    )
    send_signal = hard_timeout._signal_worker_group

    def deny_group_kill(process, sig):
        if sig == hard_timeout.signal.SIGKILL:
            return False, {'type': 'PermissionError', 'message': 'injected test denial'}
        return send_signal(process, sig)

    monkeypatch.setattr(hard_timeout, '_signal_worker_group', deny_group_kill)
    receipt = run_command_with_hard_timeout(
        [sys.executable, str(worker_script), str(grandchild_script), str(marker)],
        timeout_seconds=0.15, terminate_grace_seconds=0.05,
        identity={'run_spec_sha256': 'frozen-run'}, **paths,
    )

    assert receipt['status'] == 'termination_failed'
    assert receipt['timed_out'] is True
    assert receipt['termination']['kill_error']['type'] == 'PermissionError'
    assert not receipt['termination']['complete']
    assert receipt['termination']['worker_group_alive_after_cleanup']
    assert receipt['stdout']['sha256'] is None
    assert receipt['stdout']['error']['type'] == 'UnstableOutput'
    assert receipt['stderr']['sha256'] is None
    assert receipt['checkpoint']['sha256'] is None
    assert receipt['physical_score'] is None

    # The synthetic descendant demonstrates why the supervisor must not hash
    # or accept files while the worker group can still mutate them.
    import time
    time.sleep(0.5)
    assert marker.read_text() == 'late'


def test_existing_receipt_is_never_overwritten_or_worker_started(tmp_path):
    paths = _paths(tmp_path, 'existing')
    paths['receipt_path'].write_text('preserve-me')
    marker = tmp_path / 'worker-started'
    with pytest.raises(FileExistsError, match='overwrite'):
        run_command_with_hard_timeout(
            _python("from pathlib import Path; Path(__import__('sys').argv[1]).write_text('bad')", marker),
            timeout_seconds=1.0, identity={}, **paths,
        )
    assert paths['receipt_path'].read_text() == 'preserve-me'
    assert not marker.exists()
    assert not paths['stdout_path'].exists()


def test_invalid_identity_and_colliding_paths_reject_before_launch(tmp_path):
    paths = _paths(tmp_path, 'invalid')
    with pytest.raises(ValueError, match='strict-JSON'):
        run_command_with_hard_timeout(_python('pass'), timeout_seconds=1.0,
                                      identity={'bad': float('nan')}, **paths)
    with pytest.raises(ValueError, match='distinct'):
        run_command_with_hard_timeout(
            _python('pass'), timeout_seconds=1.0, identity={},
            receipt_path=tmp_path / 'same', stdout_path=tmp_path / 'same',
            stderr_path=tmp_path / 'stderr',
        )
    assert not paths['receipt_path'].exists()
