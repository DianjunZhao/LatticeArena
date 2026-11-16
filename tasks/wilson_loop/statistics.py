import numpy as np

from core.stats import blocks, bootstrap_indices  # noqa: F401  (re-export)


def potential(w, window, t_values):
    """V(R) from -d log W / dT over a fixed T window; w: (..., nR, nT)."""
    t = np.asarray(window, dtype=float)
    y = np.log(w[..., [list(t_values).index(x) for x in window]])
    x = t - t.mean()
    return -(y * x).sum(-1) / (x * x).sum()


def risk(w_blocks, index, windows, t_values, v_ref):
    """Precision (bootstrap SE) plus plateau spread across T windows."""
    mean = w_blocks.mean(0)
    v = potential(mean, windows[1], t_values)
    vb = potential(w_blocks[index].mean(1), windows[1], t_values)
    se = vb.std(axis=0, ddof=1)
    v_win = np.stack([potential(mean, w, t_values) for w in windows], axis=-1)
    spread = v_win.std(axis=-1)
    v_ref = np.asarray(v_ref)
    return {'risk': float(np.mean((se / v_ref) ** 2 + (spread / v_ref) ** 2)),
            'v': v.tolist(), 'se': se.tolist(), 'spread': spread.tolist(),
            'v_windows': v_win.tolist()}
