"""Static-potential figures from recorded results."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from .common import protocol


def plot(output):
    output = Path(output)
    p = protocol()
    report = json.loads((output / 'validation_results.json').read_text())
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for name, value in report['results'].items():
        v = value['v']
        err = [1.96 * s for s in value['se']]
        axes[0].errorbar(p['r_values'], v, yerr=err, marker='o', capsize=3, label=name)
    axes[0].set(xlabel='$R/a$', ylabel='$aV(R)$', title='Static potential (validation)')
    axes[0].legend(fontsize=8)
    names = list(report['results'])
    axes[1].bar(range(len(names)), [report['results'][n]['risk'] for n in names])
    axes[1].set_yscale('log')
    axes[1].set_xticks(range(len(names)))
    axes[1].set_xticklabels(names, rotation=30, ha='right', fontsize=8)
    axes[1].set(ylabel='risk', title='Validation risk (lower is better)')
    for ax in axes:
        ax.grid(alpha=0.2)
    fig.suptitle(f"Wilson loop pilot: {report['n_validation']} configurations, "
                 f"reference {'passed' if report['reference_passed'] else 'failed'}")
    fig.tight_layout()
    fig.savefig(output / 'potential.png', dpi=160)
    plt.close(fig)
    print(f'wrote {output / "potential.png"}')
