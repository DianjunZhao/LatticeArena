"""Figures for the optimize_gaussian v3 run."""
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
    r = json.loads((out / 'v3_results.json').read_text())
    d = np.load(out / 'v3_data.npz')

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    grid = r['grid']
    for steps in sorted({g['base_steps'] for g in grid}):
        rows = [g for g in grid if g['base_steps'] == steps]
        axes[0].plot([g['lam2'] for g in rows], [g['dev_val_risk'] for g in rows], 'o-', label=f'$G^{{{steps}}}$')
    axes[0].set(xlabel=r'$\lambda_2$', ylabel='dev-val risk', title='L2 grid (selection on dev-val)')
    axes[0].set_xscale('symlog', linthresh=1e-4)
    axes[0].legend(fontsize=8)
    axes[1].bar(['base', 'learned'], [r['test_risk_base'], r['test_risk_learned']], color=['#888', '#087F8C'])
    axes[1].set(ylabel='test risk', title=f"test: {r['test_ratio']:.2f}x better")
    for ax in axes:
        ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(out / 'fig_risk.png', dpi=160)

    fig, ax = plt.subplots(figsize=(6, 4))
    t = np.arange(16)
    ax.plot(t[1:9], d['q_base'][1:9], 'o-', label=f"$G^{{{r['best']['base_steps']}}}$ base")
    ax.plot(t[1:9], d['q_learned'][1:9], 's-', label='learned correction')
    ax.axhline(1, color='k', lw=0.8, ls='--')
    ax.axvspan(1.5, 5.5, alpha=0.08, color='tab:red')
    ax.set(xlabel='$t/a$', ylabel='$q(t)=C(t)/(A f_0(t))$', title='Shape on the test set (mean over configs)')
    ax.legend(fontsize=8)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(out / 'fig_q.png', dpi=160)

    fig, ax = plt.subplots(figsize=(5, 4))
    im = ax.imshow(d['a_map'][0, :, 8, :].real, origin='lower', cmap='viridis')
    fig.colorbar(im, ax=ax, label='$a_x(x,y=8,z)$')
    ax.set(xlabel='$x/a$', ylabel='$z/a$', title='Learned coefficient at $t=0$ (config 70)')
    fig.tight_layout()
    fig.savefig(out / 'fig_coeff.png', dpi=160)
    print(f'wrote {out}/fig_risk.png, fig_q.png, fig_coeff.png')


if __name__ == '__main__':
    main()
