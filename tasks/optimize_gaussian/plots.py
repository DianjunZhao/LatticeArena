"""Figures for the optimize_gaussian v5 run."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        json.loads((Path(__file__).parent / 'protocol.json').read_text())['output'])
    r = json.loads((out / 'results.json').read_text())
    names = ['base'] + [m for m in ('uniform', 'spatial', 'full') if m in r['models']]
    dev = [r['base']['dev_val']] + [r['models'][m]['dev_val'] for m in names[1:]]
    test = [r['base']['test']] + [r['models'][m]['test'] for m in names[1:]]
    x = np.arange(len(names))

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(x - 0.2, dev, 0.4, label='dev-val', color='#888')
    ax.bar(x + 0.2, test, 0.4, label='test', color='#087F8C')
    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.set(ylabel='risk', title=f"v5: base $G^{{{r['base_steps']}}}$, best = {r['best_mode']}")
    ax.legend()
    ax.grid(alpha=0.2, axis='y')
    fig.tight_layout()
    fig.savefig(out / 'fig_models.png', dpi=160)

    d = np.load(out / 'data.npz')
    fig, ax = plt.subplots(figsize=(6, 4))
    t = np.arange(16)
    ax.plot(t[1:9], d['q_base'][1:9], 'o-', label='base')
    ax.plot(t[1:9], d['q_learned'][1:9], 's-', label='learned')
    ax.axhline(1, color='k', lw=0.8, ls='--')
    ax.axvspan(1.5, 5.5, alpha=0.08, color='tab:red')
    ax.set(xlabel='$t/a$', ylabel='$q(t)=C(t)/(A f_0(t))$', title='Test set (mean over configs)')
    ax.legend(fontsize=8)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(out / 'fig_q.png', dpi=160)

    fig, ax = plt.subplots(figsize=(5, 4))
    im = ax.imshow(d['a_map'][0, :, 8, :].real, origin='lower', cmap='coolwarm')
    fig.colorbar(im, ax=ax, label='$a_x(x,y=8,z)$')
    ax.set(xlabel='$x/a$', ylabel='$z/a$', title='Learned coefficient at $t=0$ (config 70)')
    fig.tight_layout()
    fig.savefig(out / 'fig_coeff.png', dpi=160)
    print(f'wrote {out}/fig_models.png, fig_q.png, fig_coeff.png')


if __name__ == '__main__':
    main()
