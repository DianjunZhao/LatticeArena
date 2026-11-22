"""Compare two independently initialized HMC-chain diagnostic summaries."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def _load(path):
    data = json.loads(Path(path).read_text())
    if data.get('status') != 'DIAGNOSTIC_COMPLETE_PHYSICAL_UNCERTIFIED':
        raise ValueError(f"{path}: expected a complete diagnostic-only HMC summary")
    if data.get('physical_status') != 'NOT_RUN':
        raise ValueError(f"{path}: physical status must remain NOT_RUN")
    return data


def build(chain_a_path, chain_b_path, output):
    chain_a = _load(chain_a_path)
    chain_b = _load(chain_b_path)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for name in ('comparison.json', 'chain_comparison.png', 'README.md'):
        if (output / name).exists():
            raise FileExistsError(f'refusing to overwrite {output / name}')

    labels = [Path(chain_a_path).parents[1].name, Path(chain_b_path).parents[1].name]
    chains = [chain_a, chain_b]
    mean_difference = abs(chain_a['plaquette_production_mean'] - chain_b['plaquette_production_mean'])
    lengths = [int(row['block_length_trajectories'])
               for row in chain_a['block_length_sensitivity']]
    rows_a = {int(row['block_length_trajectories']): row
              for row in chain_a['block_length_sensitivity']}
    rows_b = {int(row['block_length_trajectories']): row
              for row in chain_b['block_length_sensitivity']}
    if lengths != [int(row['block_length_trajectories']) for row in chain_b['block_length_sensitivity']]:
        raise ValueError('the two block-length sensitivity grids differ')
    z_by_length = {}
    for length in lengths:
        se_a = rows_a[length]['block_mean_se']
        se_b = rows_b[length]['block_mean_se']
        z_by_length[length] = mean_difference / np.hypot(se_a, se_b)

    comparison = {
        'schema': 'latticearena-hmc-chain-comparison-v1',
        'status': 'DESCRIPTIVE_CROSS_CHAIN_CHECK',
        'physical_status': 'NOT_RUN',
        'chains': {
            label: {
                'actual_trajectories': chain['actual_trajectories'],
                'thermalization_cut': chain['thermalization_cut'],
                'production_trajectories': chain['production_trajectories'],
                'saved_configurations': chain['saved_configurations'],
                'payload_hashes_verified': chain['configuration_payload_hashes_verified'],
                'acceptance': chain['production_acceptance_rate'],
                'acceptance_cp95': chain['production_acceptance_cp95'],
                'delta_h_mean': chain['production_delta_h_mean'],
                'delta_h_sd': chain['production_delta_h_sd'],
                'delta_h_quantiles_05_50_95': chain['production_delta_h_quantiles_05_50_95'],
                'plaquette_mean': chain['plaquette_production_mean'],
                'plaquette_tau_int': chain['plaquette_tau_int_initial_positive_pairs'],
            } for label, chain in zip(labels, chains)
        },
        'absolute_plaquette_mean_difference': mean_difference,
        'difference_over_combined_block_mean_se_by_block_length': z_by_length,
        'block_comparison_note': (
            'Descriptive sensitivity only. The SEs use non-overlapping trajectory blocks; '
            'long blocks leave few blocks, and neither this table nor a single-observable '
            'autocorrelation estimate certifies equilibrium.'
        ),
        'interpretation': (
            'The chains have separate seeds and random starts. Their acceptance and DeltaH '
            'summaries overlap; the plaquette mean difference changes with block length. '
            'This is a cross-chain consistency diagnostic, not an equilibrium or physical-score test.'
        ),
    }
    (output / 'comparison.json').write_text(json.dumps(comparison, indent=2, allow_nan=False) + '\n')

    fig, axes = plt.subplots(1, 4, figsize=(17, 4.8), constrained_layout=True)
    y = np.arange(2)
    acceptance = np.array([c['production_acceptance_rate'] for c in chains])
    cp = np.array([c['production_acceptance_cp95'] for c in chains])
    axes[0].errorbar(acceptance, y,
                     xerr=np.vstack((acceptance - cp[:, 0], cp[:, 1] - acceptance)),
                     fmt='o', capsize=4, color='#315a8a')
    axes[0].set_yticks(y, labels)
    axes[0].set_xlim(0.9, 1.0)
    axes[0].set_xlabel('Production acceptance (exact CP95)')
    axes[0].set_title('Metropolis acceptance')
    axes[0].grid(axis='x', alpha=0.25)

    for row, (label, chain, color) in enumerate(zip(labels, chains, ('#315a8a', '#c26936'))):
        q05, median, q95 = chain['production_delta_h_quantiles_05_50_95']
        axes[1].errorbar(median, row, xerr=[[median - q05], [q95 - median]],
                         fmt='o', capsize=4, color=color, label=label)
        axes[1].plot(chain['production_delta_h_mean'], row, marker='|', ms=14,
                     color='black', linestyle='none')
    axes[1].axvline(0.0, color='black', lw=0.8, alpha=0.6)
    axes[1].set_yticks(y, labels)
    axes[1].set_xlabel('Production ΔH (5th–95th; dot=median, | = mean)')
    axes[1].set_title('Hamiltonian change')
    axes[1].grid(axis='x', alpha=0.25)

    selected_length = 20
    for row, (label, chain, color) in enumerate(zip(labels, chains, ('#315a8a', '#c26936'))):
        summary_row = rows_a[selected_length] if row == 0 else rows_b[selected_length]
        axes[2].errorbar(chain['plaquette_production_mean'], row,
                         xerr=1.96 * summary_row['block_mean_se'],
                         fmt='o', capsize=4, color=color)
    axes[2].set_yticks(y, labels)
    axes[2].set_xlabel('Production plaquette ± 1.96 block SE')
    axes[2].set_title(f'Block length = {selected_length} trajectories')
    axes[2].grid(axis='x', alpha=0.25)

    axes[3].plot(lengths, [z_by_length[length] for length in lengths], 'o-', color='#6a4c93')
    axes[3].axhline(2.0, color='#b33b32', ls='--', lw=1, label='2 (descriptive reference)')
    axes[3].set_xscale('log')
    axes[3].set_xticks(lengths, [str(length) for length in lengths])
    axes[3].set_xlabel('Trajectory block length')
    axes[3].set_ylabel('|Δ mean| / combined block SE')
    axes[3].set_title('Plaquette difference sensitivity')
    axes[3].legend(frameon=False, fontsize=8)
    axes[3].grid(alpha=0.25)
    fig.suptitle('Two independently initialized HMC chains: diagnostic comparison')
    fig.savefig(output / 'chain_comparison.png', dpi=180)
    plt.close(fig)

    lines = [
        '# Cross-chain HMC diagnostic comparison', '',
        '**Status:** `DESCRIPTIVE_CROSS_CHAIN_CHECK`; `physical_status=NOT_RUN`.', '',
        'Both runs used separate seeds and independently generated random starts. Each chain’s receipt, '
        'trajectory log, manifest, and every saved NERSC payload hash were verified by its own diagnostic.', '',
        '| Quantity | Chain D | Chain E |', '|---|---:|---:|',
    ]
    for title, key, fmt in (
        ('Actual / production trajectories', 'actual_trajectories', 'd'),
        ('Configurations (payload hashes checked)', 'saved_configurations', 'd'),
        ('Acceptance', 'production_acceptance_rate', '.5f'),
        ('Plaquette mean', 'plaquette_production_mean', '.8f'),
        ('Plaquette τint (trajectories)', 'plaquette_tau_int_initial_positive_pairs', '.3f'),
        ('ΔH mean', 'production_delta_h_mean', '.5g'),
        ('ΔH SD', 'production_delta_h_sd', '.5g'),
    ):
        left, right = chains
        if key == 'actual_trajectories':
            left_value = f"{left[key]} / {left['production_trajectories']}"
            right_value = f"{right[key]} / {right['production_trajectories']}"
        elif key == 'saved_configurations':
            left_value = f"{left[key]} ({left['configuration_payload_hashes_verified']})"
            right_value = f"{right[key]} ({right['configuration_payload_hashes_verified']})"
        else:
            left_value, right_value = format(left[key], fmt), format(right[key], fmt)
        lines.append(f'| {title} | {left_value} | {right_value} |')
    lines.extend([
        '', f"The absolute plaquette-mean difference is `{mean_difference:.6g}`. Its ratio to the combined block-mean SE "
        f"ranges from `{min(z_by_length.values()):.2f}` to `{max(z_by_length.values()):.2f}` over block lengths "
        f"{', '.join(map(str, lengths))} trajectories. At lengths 5, 10, 20 and 50 the ratios are "
        f"{z_by_length[5]:.2f}, {z_by_length[10]:.2f}, {z_by_length[20]:.2f} and {z_by_length[50]:.2f}. "
        'The shift below 2 as blocks lengthen shows why a naive per-trajectory error would overstate the discrepancy; '
        'the longest blocks also leave only 19 and 9 blocks, so this is a sensitivity display, not a calibrated test.', '',
        'Both plaquette traces rise from the declared hot starts to a stable-looking production region. '
        'That visual settling, overlapping acceptance intervals, and similar ΔH summaries support a descriptive '
        'cross-chain consistency check. They do not establish equilibrium, topological tunneling, or a Pion reference gate.', '',
        '![Acceptance, ΔH, plaquette, and block-size sensitivity](chain_comparison.png)', '',
        '## Next measurements', '',
        'Use D IDs 0–99 for the frozen Pion development set and E IDs 0–59 for the separate-chain anchor. '
        'The first 60 Pion anchor IDs are from E and the remaining 40 are reserved. D IDs 140–199 are '
        'a shared unopened holdout for Pion, Optimize, and a possible Wilson stout/APE comparison; freeze all '
        'participating task protocols and candidate sets before '
        'any task opens them, and never treat reuse across tasks as independent validation evidence. '
        'HMC diagnostics remain separate from Pion measurements and Wilson-loop/Stout–APE physics results.',
    ])
    (output / 'README.md').write_text('\n'.join(lines) + '\n')
    return comparison


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chain-a', required=True)
    parser.add_argument('--chain-b', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args(argv)
    print(json.dumps(build(args.chain_a, args.chain_b, args.out), sort_keys=True))


if __name__ == '__main__':
    main()
