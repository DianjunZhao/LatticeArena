"""Create an auditable plot/text review of a completed HMC production receipt."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import beta


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def cp95(successes, trials):
    if trials <= 0:
        return [float('nan'), float('nan')]
    lo = 0.0 if successes == 0 else float(beta.ppf(0.025, successes, trials-successes+1))
    hi = 1.0 if successes == trials else float(beta.ppf(0.975, successes+1, trials-successes))
    return [lo, hi]


def autocorrelation(values):
    values = np.asarray(values, dtype=float)
    centered = values - np.mean(values)
    if len(values) < 3 or not np.any(centered):
        return np.ones(1), 0.5, 0
    nfft = 1 << int(math.ceil(math.log2(2 * len(values))))
    spectrum = np.fft.rfft(centered, n=nfft)
    covariance = np.fft.irfft(spectrum * spectrum.conjugate(), n=nfft)[:len(values)]
    covariance /= np.arange(len(values), 0, -1)  # unbiased lag normalization
    rho = covariance / covariance[0]
    tau = 0.5
    cutoff = 0
    for lag in range(1, len(rho), 2):
        pair = rho[lag] + (rho[lag + 1] if lag + 1 < len(rho) else 0.0)
        if not np.isfinite(pair) or pair <= 0:
            break
        tau += float(pair)
        cutoff = min(lag + 1, len(rho) - 1)
    return rho, max(0.5, tau), cutoff


def block_sensitivity(values, lengths=(1, 2, 5, 10, 20, 50)):
    output = []
    values = np.asarray(values, dtype=float)
    for length in lengths:
        nblock = len(values) // length
        if nblock < 2:
            continue
        means = values[:nblock * length].reshape(nblock, length).mean(axis=1)
        output.append({
            'block_length_trajectories': length,
            'complete_blocks': nblock,
            'discarded_remainder': int(len(values) - nblock * length),
            'mean_plaquette': float(np.mean(means)),
            'block_mean_se': float(np.std(means, ddof=1) / np.sqrt(nblock)),
        })
    return output


def verify_inputs(receipt_path, trajectory_path, manifest_path):
    receipt_path = Path(receipt_path)
    trajectory_path = Path(trajectory_path)
    manifest_path = Path(manifest_path)
    receipt = json.loads(receipt_path.read_text())
    if receipt.get('status') != 'COMPLETED':
        raise ValueError(f"HMC receipt status is {receipt.get('status')!r}, expected COMPLETED")
    if receipt.get('trajectory_log_sha256') != sha256(trajectory_path):
        raise ValueError('trajectory JSONL hash differs from HMC receipt')
    if receipt.get('manifest_sha256') != sha256(manifest_path):
        raise ValueError('ensemble manifest hash differs from HMC receipt')
    rows = read_jsonl(trajectory_path)
    manifest = json.loads(manifest_path.read_text())
    expected = int(receipt['actual_trajectories'])
    if len(rows) != expected:
        raise ValueError(f'trajectory row count {len(rows)} differs from receipt {expected}')
    ids = [row.get('trajectory') for row in rows]
    if ids != list(range(1, expected + 1)):
        raise ValueError('trajectory IDs are not contiguous from 1')
    thermal = int(receipt['protocol']['thermal_trajectories'])
    production = [row for row in rows if row['trajectory'] > thermal]
    if not production:
        raise ValueError('receipt has no production trajectories after the frozen cut')
    if len(production) != int(receipt['production_trajectories']):
        raise ValueError('production trajectory count differs from receipt')
    accepts = sum(bool(row['metropolis_accept']) for row in production)
    if accepts != int(receipt['production_accepts']):
        raise ValueError('production acceptance count differs from receipt')
    if not np.isclose(receipt['production_acceptance_rate'], accepts / len(production)):
        raise ValueError('production acceptance rate differs from trajectory rows')
    delta_h_values = np.asarray([row['delta_h'] for row in production], dtype=float)
    if not np.isclose(receipt['production_delta_h_mean'], np.mean(delta_h_values)):
        raise ValueError('production mean ΔH differs from trajectory rows')
    if not np.isclose(receipt['production_delta_h_std'], np.std(delta_h_values, ddof=1)):
        raise ValueError('production ΔH standard deviation differs from trajectory rows')
    for row in rows:
        if row.get('phase') != ('thermalization' if row['trajectory'] <= thermal else 'production'):
            raise ValueError(f'phase label differs from frozen thermalization cut at trajectory {row["trajectory"]}')
        for key in ('delta_h', 'plaquette_after_update', 'elapsed_seconds'):
            if not np.isfinite(row[key]):
                raise ValueError(f'non-finite {key} at trajectory {row["trajectory"]}')
        if type(row.get('metropolis_accept')) is not bool:
            raise ValueError(f'acceptance flag is not boolean at trajectory {row["trajectory"]}')
    manifest_by_id = {int(row['id']): row for row in manifest.get('configs', [])}
    saved = [row for row in rows if row.get('configuration_id') is not None]
    if len(saved) != int(receipt['saved_configurations']):
        raise ValueError('trajectory save count differs from completion receipt')
    if len(manifest_by_id) != len(saved):
        raise ValueError('manifest row count differs from saved trajectory rows')
    for row in saved:
        config_id = int(row['configuration_id'])
        item = manifest_by_id.get(config_id)
        if item is None or item['trajectory'] != row['trajectory']:
            raise ValueError(f'manifest trajectory mismatch for configuration {config_id}')
        if item['sha256'] != row['configuration_sha256']:
            raise ValueError(f'manifest hash mismatch for configuration {config_id}')
        config_path = manifest_path.parent / f'wilson_b6.{config_id}'
        if not config_path.is_file() or sha256(config_path) != item['sha256']:
            raise ValueError(f'raw NERSC file hash mismatch for configuration {config_id}')
    return receipt, rows, manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', required=True)
    parser.add_argument('--trajectory-log', required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    receipt, rows, manifest = verify_inputs(args.receipt, args.trajectory_log, args.manifest)
    thermal = int(receipt['protocol']['thermal_trajectories'])
    production = [row for row in rows if row['trajectory'] > thermal]
    if not production:
        raise ValueError('no production trajectories remain after the frozen thermalization cut')
    trajectory = np.asarray([row['trajectory'] for row in rows], dtype=int)
    production_trajectory = np.asarray([row['trajectory'] for row in production], dtype=int)
    delta_h = np.asarray([row['delta_h'] for row in production], dtype=float)
    accepted = np.asarray([row['metropolis_accept'] for row in production], dtype=bool)
    plaquette = np.asarray([row['plaquette_after_update'] for row in rows], dtype=float)
    production_plaq = np.asarray([row['plaquette_after_update'] for row in production], dtype=float)
    rolling_window = min(100, len(production), max(20, len(production) // 10))
    rolling_accept = np.convolve(accepted.astype(float), np.ones(rolling_window)/rolling_window, mode='valid')
    rolling_plaq = np.convolve(plaquette, np.ones(rolling_window)/rolling_window, mode='valid')
    rolling_accept_x = production_trajectory[rolling_window - 1:]
    rolling_plaq_x = trajectory[rolling_window - 1:]
    rho, tau, acf_cutoff = autocorrelation(production_plaq)
    block_rows = block_sensitivity(production_plaq)
    n_accept = int(accepted.sum())
    acceptance = n_accept / len(accepted)
    acceptance_ci = cp95(n_accept, len(accepted))
    saved = sum(row['configuration_id'] is not None for row in rows)

    csv_path = out / 'trajectory_table.csv'
    with csv_path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    fig, ax = plt.subplots(figsize=(8.2, 5.2), constrained_layout=True)
    ax.hist(delta_h, bins='fd', color='#315a8a', alpha=0.85, edgecolor='white')
    ax.axvline(0, color='black', lw=1)
    ax.set(xlabel=r'$Delta H$', ylabel='Production trajectories',
           title=f"Production ΔH; mean={delta_h.mean():.3g}, SD={delta_h.std(ddof=1):.3g}")
    fig.savefig(out / 'delta_h_histogram.png', dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.2, 5.2), constrained_layout=True)
    ax.plot(rolling_accept_x, rolling_accept, color='#315a8a', lw=1.5,
            label=f'{rolling_window}-trajectory moving acceptance')
    ax.axhline(acceptance, color='#b24035', ls='--',
               label=f'overall {acceptance:.3f} [{acceptance_ci[0]:.3f}, {acceptance_ci[1]:.3f}]')
    ax.set(xlabel='Trajectory', ylabel='Acceptance fraction', ylim=(0, 1.03),
           title='Metropolis acceptance after the frozen thermalization cut')
    ax.legend(frameon=False)
    fig.savefig(out / 'acceptance_by_trajectory.png', dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9.0, 5.2), constrained_layout=True)
    ax.plot(trajectory, plaquette, color='#8396a8', alpha=0.4, lw=0.7, label='per-trajectory plaquette')
    ax.plot(rolling_plaq_x, rolling_plaq, color='#184f73', lw=1.5,
            label=f'{rolling_window}-trajectory moving mean')
    ax.axvline(thermal + 0.5, color='#b24035', ls='--', label=f'predeclared cut={thermal}')
    saved_rows = [row for row in rows if row['configuration_id'] is not None]
    ax.scatter([row['trajectory'] for row in saved_rows],
               [row['plaquette_after_update'] for row in saved_rows],
               s=12, color='#d58b37', label=f'saved configurations ({saved})')
    ax.set(xlabel='Trajectory', ylabel='Plaquette', title='Thermalization and production trace')
    ax.legend(frameon=False, ncol=2)
    fig.savefig(out / 'plaquette_trajectory.png', dpi=180)
    plt.close(fig)

    max_lag = min(100, len(rho) - 1)
    fig, ax = plt.subplots(figsize=(8.2, 5.2), constrained_layout=True)
    ax.axhspan(-1.96 / np.sqrt(len(production_plaq)), 1.96 / np.sqrt(len(production_plaq)),
               color='#e7edf2', label='approximate ±1.96/√N band')
    ax.plot(np.arange(max_lag + 1), rho[:max_lag + 1], marker='o', ms=2.5, lw=1, color='#315a8a')
    ax.axvline(acf_cutoff, color='#b24035', ls='--', label=f'initial-positive cutoff={acf_cutoff}')
    ax.set(xlabel='Lag (trajectory units)', ylabel='Plaquette autocorrelation',
           title=f'Production plaquette autocorrelation; τint={tau:.2f}')
    ax.legend(frameon=False)
    fig.savefig(out / 'plaquette_autocorrelation.png', dpi=180)
    plt.close(fig)

    summary = {
        'schema': 'latticearena-hmc-diagnostic-v1',
        'status': 'DIAGNOSTIC_COMPLETE_PHYSICAL_UNCERTIFIED',
        'physical_status': 'NOT_RUN',
        'receipt_sha256': sha256(args.receipt),
        'trajectory_log_sha256': sha256(args.trajectory_log),
        'manifest_sha256': sha256(args.manifest),
        'diagnostic_source_sha256': sha256(__file__),
        'actual_trajectories': len(rows),
        'thermalization_cut': thermal,
        'production_trajectories': len(production),
        'saved_configurations': saved,
        'production_accepts': n_accept,
        'production_acceptance_rate': acceptance,
        'production_acceptance_cp95': acceptance_ci,
        'production_delta_h_mean': float(delta_h.mean()),
        'production_delta_h_sd': float(delta_h.std(ddof=1)),
        'production_delta_h_quantiles_05_50_95': np.quantile(delta_h, [0.05, 0.5, 0.95]).tolist(),
        'plaquette_initial': float(plaquette[0]),
        'plaquette_thermal_last': float(plaquette[min(thermal - 1, len(plaquette)-1)]),
        'plaquette_production_mean': float(production_plaq.mean()),
        'plaquette_production_sd': float(production_plaq.std(ddof=1)),
        'plaquette_tau_int_initial_positive_pairs': float(tau),
        'plaquette_acf_window_cutoff': int(acf_cutoff),
        'suggested_block_length_trajectories': int(max(1, math.ceil(2 * tau))),
        'block_length_sensitivity': block_rows,
        'rolling_acceptance_window': rolling_window,
        'configuration_payload_hashes_verified': saved,
    }
    (out / 'diagnostic_summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    table = [
        '# HMC chain diagnostic', '',
        '**Status:** `DIAGNOSTIC_COMPLETE_PHYSICAL_UNCERTIFIED`; `physical_status=NOT_RUN`.', '',
        'The HMC receipt, every trajectory row, saved-configuration manifest, and raw NERSC files passed identity checks.',
        f"The frozen thermalization cut is {thermal} trajectories. The analyzed production portion has "
        f"{len(production)} rows, acceptance {n_accept}/{len(production)} = {acceptance:.4f} "
        f"(exact binomial CP95 [{acceptance_ci[0]:.4f}, {acceptance_ci[1]:.4f}]).",
        f"Production ΔH mean={delta_h.mean():.5g}, SD={delta_h.std(ddof=1):.5g}; "
        f"plaquette mean={production_plaq.mean():.8g}, SD={production_plaq.std(ddof=1):.4g}.",
        f"The initial-positive-pair estimate gives plaquette τint={tau:.3g} trajectories and a "
        f"suggested block length ceil(2τ)={summary['suggested_block_length_trajectories']}. "
        'This is a single-observable finite-chain diagnostic; it is not proof of equilibrium or a physical-score gate.', '',
        '| Block length (trajectories) | Complete blocks | Remainder dropped | Mean plaquette | SE of block means |',
        '|---:|---:|---:|---:|---:|',
    ]
    for row in block_rows:
        table.append(f"| {row['block_length_trajectories']} | {row['complete_blocks']} | "
                     f"{row['discarded_remainder']} | {row['mean_plaquette']:.8g} | {row['block_mean_se']:.3g} |")
    table.extend([
        '', '## Figures', '',
        '- `delta_h_histogram.png`: production Hamiltonian change distribution.',
        '- `acceptance_by_trajectory.png`: rolling and overall Metropolis acceptance.',
        '- `plaquette_trajectory.png`: thermalization cut, production trace, and saved configurations.',
        '- `plaquette_autocorrelation.png`: production autocorrelation and initial-positive window.',
        '',
        '## Limits', '',
        'The autocorrelation rule is the initial-positive-pair truncation of the plaquette autocorrelation; the reported block-length table is sensitivity analysis, not an independently calibrated uncertainty prescription. A single chain and one observable do not establish ensemble independence, topological tunneling, or equilibrium. The plots and per-trajectory table are diagnostics only; Wilson-loop fit and stout/APE paired physical results remain separate gates.',
    ])
    (out / 'README.md').write_text('\n'.join(table) + '\n')
    print(json.dumps(summary, sort_keys=True))


if __name__ == '__main__':
    main()
