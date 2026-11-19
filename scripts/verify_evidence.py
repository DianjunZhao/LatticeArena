"""Re-verify an archived evidence file against its run (todo F0)."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.evidence import verify_receipt  # noqa: E402
from core.io import digest  # noqa: E402
from scripts.audit_run import verify_entry_against_run  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', choices=['wilson_loop', 'pion_projection'], required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--evidence', required=True)
    args = parser.parse_args()
    run = Path(args.run)
    data = json.loads(Path(args.evidence).read_text())
    run_sha = digest(run / 'validation.npz')
    for entry in data['entries']:
        verify_entry_against_run(entry, run, args.task)
        verify_receipt(entry, run_sha)
    print(f'verified {len(data["entries"])} entries for {args.task}')


if __name__ == '__main__':
    main()
