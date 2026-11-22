"""Projection support-domain audit (todo P0b).

The controlled grid fixes arg(det(M)) rather than only multiplying a random
U(3) matrix by a scalar phase. The SU(3) projection removes that determinant
phase; its center-phase branch jump is shown explicitly around +/- pi.
"""
import json
import warnings
from pathlib import Path

import numpy as np

from .kernels import project

OUT = Path('results/wilson_loop/audit_20261119_projection_domain_v2')
SPECTRA = ((1.0, 1.0, 1.0), (1.0, 1.0, 1e-2), (1.0, 1.0, 1e-3),
           (1.0, 1.0, 1e-4), (1.0, 1.0, 1e-5), (1.0, 1.0, 0.0))
SCALES = (1e-3, 1.0, 1e3)
PHASE_EPS = 1e-6
PHASES = (-np.pi, -np.pi + PHASE_EPS, -np.pi / 2, 0.0,
          np.pi / 2, np.pi - PHASE_EPS, np.pi)
TOL = 1e-9
MAX_CONDITION = 1e3


def cell(rng, svals, scale, phase):
    u, _ = np.linalg.qr(rng.normal(size=(3, 3)) + 1j * rng.normal(size=(3, 3)))
    v, _ = np.linalg.qr(rng.normal(size=(3, 3)) + 1j * rng.normal(size=(3, 3)))
    u = u * np.exp(-1j * np.angle(np.linalg.det(u)) / 3)
    v = v * np.exp(-1j * np.angle(np.linalg.det(v)) / 3)
    a = scale * u @ np.diag(svals) @ v.conj().T
    return a * np.exp(1j * phase / 3)


def residual(x):
    return float(np.max(np.abs(x.conj().T @ x - np.eye(3))))


def polar_factor(a):
    left, _, right = np.linalg.svd(a, full_matrices=False)
    return left @ right


def circular_difference(a, b):
    return float(abs(np.angle(np.exp(1j * (a - b)))))


def supported(svals):
    smallest, largest = min(svals), max(svals)
    return smallest > 0 and largest / smallest <= MAX_CONDITION


def main():
    if OUT.exists() and any(OUT.iterdir()):
        raise FileExistsError(f'{OUT} already contains results; choose a new output directory')
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261119)
    rows = []
    for svals in SPECTRA:
        for scale in SCALES:
            for phase in PHASES:
                a = cell(rng, svals, scale, phase)
                inside = supported(svals)
                determinant = np.linalg.det(a)
                input_phase = (float(np.angle(determinant))
                               if min(svals) > 0 and abs(determinant) > np.finfo(float).tiny else None)
                is_branch_endpoint = (input_phase is not None
                                      and abs(abs(input_phase) - np.pi) < 1e-10)
                row = {'svals': list(svals), 'scale': scale,
                       'requested_det_phase': float(phase), 'input_det_phase': input_phase,
                       'phase_control_error': (circular_difference(input_phase, phase)
                                               if input_phase is not None else None),
                       'branch_endpoint': bool(is_branch_endpoint),
                       'inside_support': bool(inside)}
                try:
                    with warnings.catch_warnings(record=True) as caught:
                        warnings.simplefilter('always', RuntimeWarning)
                        x = project(a[None])
                    l, _ = np.linalg.qr(rng.normal(size=(3, 3)) + 1j * rng.normal(size=(3, 3)))
                    r, _ = np.linalg.qr(rng.normal(size=(3, 3)) + 1j * rng.normal(size=(3, 3)))
                    l = l / np.linalg.det(l) ** (1 / 3)     # SU(3): no extra global phase
                    r = r / np.linalg.det(r) ** (1 / 3)
                    y = project((l @ a @ r)[None])
                    polar = polar_factor(a)
                    polar_phase = float(np.angle(np.linalg.det(polar)))
                    correction = np.trace(polar.conj().T @ x[0]) / 3
                    expected_phase = -polar_phase / 3
                    alternatives = ([expected_phase + k * 2 * np.pi / 3 for k in (-1, 0, 1)]
                                    if is_branch_endpoint else [expected_phase])
                    phase_error = min(circular_difference(float(np.angle(correction)), value)
                                      for value in alternatives)
                    row['covariance_residual'] = float(np.max(np.abs(y[0] - l @ x[0] @ r))
                                                       / max(np.max(np.abs(x[0])), 1e-300))
                    row['unitarity_residual'] = residual(x[0])
                    row['su3_determinant_residual'] = float(abs(np.linalg.det(x[0]) - 1))
                    row['polar_determinant_phase'] = polar_phase
                    row['su3_correction_phase'] = float(np.angle(correction))
                    row['correction_phase_error'] = phase_error
                    row['su3_correction_residual'] = float(np.linalg.norm(
                        x[0] - polar * correction))
                    row['unitarity_ok'] = bool(row['unitarity_residual'] <= TOL)
                    row['su3_ok'] = bool(row['su3_determinant_residual'] <= TOL
                                         and row['correction_phase_error'] <= TOL
                                         and row['su3_correction_residual'] <= TOL)
                    row['rejected'] = not inside or not row['unitarity_ok'] or not row['su3_ok']
                    row['runtime_warnings'] = [str(item.message) for item in caught]
                    if not inside:
                        row['reason'] = (f'outside the declared support (condition '
                                         f'{max(row["svals"]) / min(row["svals"]):.0e} > '
                                         f'{MAX_CONDITION:.0e})')
                    elif not row['unitarity_ok'] or not row['su3_ok']:
                        row['reason'] = 'unitarity or SU(3) projection residual exceeds tolerance'
                except ValueError as exc:
                    row.update({'unitarity_residual': None, 'su3_determinant_residual': None,
                                'polar_determinant_phase': None, 'su3_correction_phase': None,
                                'correction_phase_error': None, 'su3_correction_residual': None,
                                'covariance_residual': None,
                                'unitarity_ok': False, 'rejected': True, 'reason': str(exc),
                                'runtime_warnings': [str(item.message) for item in caught]})
                rows.append(row)
    inside = [row for row in rows if row['inside_support']]
    outside = [row for row in rows if not row['inside_support']]
    covariances = [row['covariance_residual'] for row in inside
                   if row.get('covariance_residual') is not None]
    off_cut_covariances = [row['covariance_residual'] for row in inside
                           if row.get('covariance_residual') is not None
                           and not row['branch_endpoint']]
    result = {'schema': 'wilson-projection-domain-v2', 'tolerance': TOL,
              'scales_tested': list(SCALES),
              'requested_determinant_phases': list(PHASES),
              'phase_epsilon': PHASE_EPS,
              'max_inside_covariance_residual': max(covariances) if covariances else None,
              'max_off_cut_covariance_residual': (max(off_cut_covariances)
                                                   if off_cut_covariances else None),
              'off_cut_covariance_pass': all(value <= TOL for value in off_cut_covariances),
              'branch_endpoint_covariance_max': max(
                  (row['covariance_residual'] for row in inside if row['branch_endpoint']
                   and row.get('covariance_residual') is not None), default=None),
              'branch_endpoint_covariance_outliers': sum(
                  row['inside_support'] and row['branch_endpoint']
                  and row.get('covariance_residual', 0) > TOL for row in rows),
              'max_condition': MAX_CONDITION, 'rows': rows,
              'inside_all_pass': all(row['unitarity_ok'] for row in inside),
              'inside_all_su3_pass': all(row.get('su3_ok', False) for row in inside),
              'all_phase_controls_pass': all(
                  row['phase_control_error'] is None or row['phase_control_error'] <= TOL
                  for row in rows),
              'outside_all_rejected': all(row['rejected'] for row in outside),
              'outside_with_numerically_small_residual': [
                  {'svals': row['svals'], 'scale': row['scale'],
                   'requested_det_phase': row['requested_det_phase'],
                   'unitarity_residual': row['unitarity_residual']} for row in outside
                  if row['unitarity_residual'] is not None and row['unitarity_residual'] <= TOL],
              'silent_failures': sum(1 for row in rows
                                     if not row['unitarity_ok'] and not row['rejected']),
              'note': ('the polar factor carries the input determinant phase; the final SU(3) '
                       'projection removes it to enforce det=1. The principal-root center-phase '
                       'jump across +/-pi is displayed and is not a continuity failure.')}
    (OUT / 'projection_domain.json').write_text(json.dumps(result, indent=2) + '\n')
    _plot_phase(rows, OUT / 'fig_projection_phase_branch.png')
    write_readme(result, OUT / 'README.md')
    print('inside_all_pass', result['inside_all_pass'],
          'inside_all_su3_pass', result['inside_all_su3_pass'],
          'phase_controls_pass', result['all_phase_controls_pass'],
          'outside_all_rejected', result['outside_all_rejected'],
          'silent_failures', result['silent_failures'])
    bad = [row for row in outside if not (row['rejected'] or not row['unitarity_ok'])]
    for row in bad[:3]:
        print('outside accepted:', row['svals'], row['scale'], row.get('unitarity_residual'))


def _plot_phase(rows, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    selected = [row for row in rows if row['inside_support']
                and row['svals'] == [1.0, 1.0, 1e-2] and row['scale'] == 1.0]
    selected.sort(key=lambda row: row['requested_det_phase'])
    x = np.array([row['requested_det_phase'] for row in selected])
    y = np.array([row['su3_correction_phase'] for row in selected])
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6))
    axes[0].plot(x, y, 'o-', color='#315a8a', label='SU(3) determinant correction')
    axes[0].axvline(np.pi, color='#bd634e', linestyle=':', label='principal-branch cut')
    axes[0].axvline(-np.pi, color='#bd634e', linestyle=':')
    axes[0].set(xlabel='requested arg det(M) (actual phase checked)',
                ylabel='phase of factor multiplying polar(M)',
                title='Full determinant phase sweep')
    axes[0].set_xticks([-np.pi, -np.pi / 2, 0, np.pi / 2, np.pi],
                       ['−π', '−π/2', '0', 'π/2', 'π'])
    categories = (-np.pi, -np.pi + PHASE_EPS, np.pi - PHASE_EPS, np.pi)
    values = [next(row['su3_correction_phase'] for row in selected
                   if row['requested_det_phase'] == phase) for phase in categories]
    axes[1].scatter(np.arange(len(categories)), values, color='#bd634e', zorder=3)
    axes[1].plot(np.arange(len(categories)), values, color='#bd634e', alpha=0.65)
    axes[1].set_xticks(np.arange(len(categories)), ['−π', '−π+ε', 'π−ε', 'π'])
    axes[1].set(xlabel='controlled cut-side point', title='Branch-cut detail')
    for ax in axes:
        ax.grid(alpha=0.25)
    fig.suptitle('Controlled determinant phase and the SU(3) center branch')
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def write_readme(result, path):
    inside = [row for row in result['rows'] if row['inside_support']]
    outside = [row for row in result['rows'] if not row['inside_support']]
    max_unitarity = max(row['unitarity_residual'] for row in inside)
    max_det = max(row['su3_determinant_residual'] for row in inside)
    max_phase = max(row['phase_control_error'] for row in result['rows']
                    if row['phase_control_error'] is not None)
    path.write_text(f"""# P0b determinant-phase controlled projection scan

生成：`python -m tasks.wilson_loop.projection_domain`；数值在 `projection_domain.json`，图在 `fig_projection_phase_branch.png`。这是 CPU 有限网格证据。

## 输入与范围

- 126 cells：6 个奇异值谱 × 3 个尺度（{', '.join(f'{x:g}' for x in result['scales_tested'])}）× 7 个受控 determinant phases。
- 奇异值谱含单位矩阵、条件数 100/1,000/10,000/100,000 和奇异矩阵；支持策略为正奇异值且条件数 ≤ {result['max_condition']:.0f}。
- 左右奇异向量均规范为 SU(3)，所以实际 `arg det(M)` 与请求相位一致；扫描 `±π` 和两侧 `±(π−ε)`，`ε={result['phase_epsilon']:g}`。
- 测试尺度仅覆盖所列三点；不能外推到任意浮点动态范围。

## 结果

| 诊断 | 结果 |
| --- | ---: |
| 支持域 cell 通过 | {sum(row['unitarity_ok'] and row.get('su3_ok', False) for row in inside)}/{len(inside)} |
| 域外策略拒绝 | {sum(row['rejected'] for row in outside)}/{len(outside)} |
| 最大输入相位控制误差 | {max_phase:.3e} |
| 最大 unitary 残差（支持域） | {max_unitarity:.3e} |
| 最大 $|\\det P(M)-1|$（支持域） | {max_det:.3e} |
| 切口外最大双侧 SU(3) 协变残差 | {result['max_off_cut_covariance_residual']:.3e} |
| 精确切口端点协变超容差格数 | {result['branch_endpoint_covariance_outliers']} |

![受控 determinant phase 的 SU(3) 中心分支](fig_projection_phase_branch.png)

## 正确解释

极分解的 unitary factor 保留 `arg det(M)`；最终 SU(3) 投影乘以 `exp(-i arg det(Q)/3)`，把 determinant 调到 1。因此
修正前后 determinant phase 的差是预期变换，不是误差。principal cube root 在 `±π` 两侧会发生中心相位跳变；本图显示该
有限边界行为，不声称切口处连续。精确端点的协变 outlier 单独报告；它们不能与切口外的协变通过混为一谈。域外有些
矩阵数值上仍可能可投影，但按预声明条件数策略拒绝。
""")


if __name__ == '__main__':
    main()
