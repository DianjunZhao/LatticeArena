"""Readable post-run summary plot for a completed full-gate Monte Carlo run."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


SCENARIOS = (
    'null_equal_candidate',
    'known_lower_excited_overlap',
    'window_mismatch',
    'reflection',
    'relative_error',
    'wrong_state',
    'nonfinite',
)
LABELS = (
    'null equal\ncandidate',
    'known lower\nexcited overlap',
    'window\nmismatch',
    'reflection',
    'relative\nerror',
    'wrong\nstate',
    'nonfinite',
)
METRICS = (
    ('reference_acceptance', 'Reference accepted'),
    ('candidate_certification', 'Candidate certified'),
    ('failure', 'Expected input failure'),
    ('abstain', 'Abstain (includes failures)'),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aggregate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f'output already exists: {args.output}')
    aggregate = json.loads(args.aggregate.read_text())
    if aggregate.get('status') != 'COMPLETE' or aggregate.get('n_executed') != 2814:
        parser.error('expected a complete 2814-world amendment02 aggregation')
    rates = aggregate['rates']
    if set(rates) != set(SCENARIOS):
        parser.error('scenario list differs from the frozen seven-cell plan')
    for scenario in SCENARIOS:
        for key, _ in METRICS:
            if rates[scenario][key]['n'] != 402:
                parser.error(f'{scenario}/{key} does not have planned denominator 402')

    fig, axes = plt.subplots(2, 2, figsize=(15, 9), sharex=True)
    x = np.arange(len(SCENARIOS))
    for ax, (metric, title) in zip(axes.ravel(), METRICS):
        values = [rates[scenario][metric] for scenario in SCENARIOS]
        y = np.asarray([value['k'] / value['n'] for value in values])
        ci = np.asarray([value['cp95'] for value in values])
        ax.errorbar(
            x,
            y,
            yerr=np.vstack((y - ci[:, 0], ci[:, 1] - y)),
            fmt='o',
            color='#3569a8',
            capsize=4,
            markersize=6,
            linewidth=1.3,
        )
        ax.set_title(title, fontsize=12)
        ax.set_ylim(-0.04, 1.04)
        ax.set_ylabel('dataset fraction (pointwise CP95)')
        ax.set_xticks(x, LABELS, rotation=0, ha='center', fontsize=9)
        ax.grid(alpha=0.22)

    fig.suptitle('Pion full-certificate MC — amendment02, 402 datasets per scenario', fontsize=15)
    fig.text(
        0.5,
        0.015,
        'Synthetic full-gate calibration only; physical_score = null. Failure is included in abstention.',
        ha='center',
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=170)
    plt.close(fig)
    provenance = {
        'schema': 'pion-full-gate-summary-plot-v1',
        'source_aggregate': str(args.aggregate),
        'source_aggregate_sha256': sha256(args.aggregate),
        'plot_script_sha256': sha256(Path(__file__)),
        'plot_sha256': sha256(args.output),
        'scenarios': list(SCENARIOS),
        'datasets_per_scenario': 402,
        'note': 'Post-run rendering of the frozen aggregate; no rates or intervals recomputed.',
    }
    provenance_path = args.output.with_name('candidate_rates_diagnostic_provenance.json')
    provenance_path.write_text(json.dumps(provenance, indent=2) + '\n')
    print(json.dumps(provenance, indent=2))


if __name__ == '__main__':
    main()
