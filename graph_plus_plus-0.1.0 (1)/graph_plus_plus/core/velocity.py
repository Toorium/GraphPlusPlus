"""Velocity computation — 1st & 2nd derivatives for speed/accel analysis.

Used by:
  - motion_path/draw.py for color gradient
  - analysis/velocity_overlay.py for the graph-editor mini-graph
"""
import math
from mathutils import Vector


def compute_speed_series(path):
    """Given a sampled path (list of dicts from path_sampler), return
    a list of (frame, speed) tuples suitable for plotting.
    """
    return [(p['frame'], p['velocity']) for p in path]


def compute_acceleration_series(path):
    """Compute acceleration (2nd derivative) as dV/dt along the path."""
    if len(path) < 3:
        return []
    accel = []
    for i in range(1, len(path) - 1):
        v_prev = path[i - 1]['velocity']
        v_curr = path[i]['velocity']
        dt = path[i + 1]['frame'] - path[i - 1]['frame']
        if dt > 1e-6:
            a = (v_curr - v_prev) / dt
        else:
            a = 0.0
        accel.append((path[i]['frame'], a))
    return accel


def normalize_speed(path):
    """Return max speed across the path (used to normalize color mapping)."""
    return max((p['velocity'] for p in path), default=1.0)


def smooth_series(series, window=3):
    """Simple moving-average smoothing of a (frame, value) list."""
    if len(series) < window:
        return list(series)
    half = window // 2
    out = []
    for i in range(len(series)):
        lo = max(0, i - half)
        hi = min(len(series), i + half + 1)
        avg = sum(v for _, v in series[lo:hi]) / (hi - lo)
        out.append((series[i][0], avg))
    return out
