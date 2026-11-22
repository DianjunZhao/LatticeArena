"""Render the one-configuration D-chain GPU smoke receipt as a cost diagnostic."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def render(run):
    run = Path(run)
    provenance_path = run / 'development_provenance.json'
    with np.load(run / 'development.npz', allow_pickle=False) as saved:
        ids = saved['ids'].tolist()
        loops = saved['loops']
    provenance = json.loads(provenance_path.read_text())
    if len(ids) != 1 or len(provenance.get('records', [])) != 1:
        raise ValueError('this diagnostic is defined only for a single-configuration smoke run')
    row = provenance['records'][0]
    if row['id'] != ids[0] or not np.all(np.isfinite(loops)):
        raise ValueError('smoke result ID/array check failed')
    kernel = row['kernel_seconds_by_candidate']
    contraction = row['loop_seconds_by_candidate']
    names = list(kernel)
    colors = ['#536879' if name == 'identity' else '#D28B26' if name.startswith('ape') else '#087F8C'
              for name in names]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), constrained_layout=True)
    y = np.arange(len(names))
    axes[0].barh(y, [kernel[name] for name in names], color=colors)
    axes[0].set_yticks(y, names)
    axes[0].set_xscale('log')
    axes[0].set_xlim(.7, 300)
    axes[0].set_xticks([1, 2, 5, 10, 20, 50, 100, 200],
                       labels=['1', '2', '5', '10', '20', '50', '100', '200'])
    axes[0].set_xlabel('seconds per configuration (log scale)')
    axes[0].set_title('Smearing / kernel time')
    axes[1].barh(y, [contraction[name] for name in names], color=colors)
    axes[1].set_yticks(y, names)
    axes[1].set_xscale('log')
    axes[1].set_xlim(.1, 10)
    axes[1].set_xticks([.1, .2, .5, 1, 2, 5, 10],
                       labels=['0.1', '0.2', '0.5', '1', '2', '5', '10'])
    axes[1].set_xlabel('seconds per configuration (log scale)')
    axes[1].set_title('Wilson-loop contraction time')
    for ax in axes:
        ax.grid(axis='x', alpha=.25)
    fig.suptitle(f"D-chain GPU smoke: cfg {row['id']} (trajectory {row['hmc_trajectory']}); one sample only")
    image = run / 'smoke_cost.png'
    fig.savefig(image, dpi=180)
    plt.close(fig)
    report = [
        '# Wilson D-chain GPU smoke',
        '',
        '**Status: one-configuration execution smoke passed; no physics comparison.**',
        '',
        f"- Configuration `{row['id']}`, HMC trajectory `{row['hmc_trajectory']}`.",
        f"- NERSC checksum: `{row['checksum_status']['standard']}`; raw SHA-256 `{row['gauge_sha256']}`.",
        f"- Input manifest SHA-256: `{provenance['input_manifest_sha256']}`.",
        f"- Total `{row['total_seconds']:.2f}s` = setup `{row['setup_seconds']:.2f}s`, smearing/kernel `{row['kernel_seconds']:.2f}s`, loop contraction `{row['loop_seconds']:.2f}s`.",
        '',
        '![Per-candidate smoke timing](smoke_cost.png)',
        '',
        'The two 10-step stout candidates dominate runtime at 173.34 s and 176.38 s for this configuration; APE candidates take 1.08–5.35 s. These are single-configuration timings on one DCU, so they estimate execution cost only and do not establish a stable average or a physics preference. The development job should record full wall time and all configuration-specific timings.',
        '',
        'The full frozen D development measurement covers IDs 0–99. D IDs 100–119 remain a gap, IDs 120–139 stay gated on the development reference check, and shared IDs 140–199 remain sealed.',
        '',
    ]
    (run / 'README.md').write_text('\n'.join(report))
    return image


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    print(render(args.run))
