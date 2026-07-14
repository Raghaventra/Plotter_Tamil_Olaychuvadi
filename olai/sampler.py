"""Stage 3 — resample contours into evenly spaced dots (by arc length)."""
from __future__ import annotations

from typing import List

import numpy as np


def resample_closed(points: np.ndarray, spacing_px: float) -> np.ndarray:
    """Place points every ``spacing_px`` along a closed polygon outline.

    Parameters
    ----------
    points : (N, 2) array, the contour vertices (assumed closed loop)
    spacing_px : desired arc-length distance between output dots

    Returns
    -------
    (M, 2) array of dot coordinates.
    """
    pts = np.asarray(points, dtype=float)
    if len(pts) < 2:
        return pts

    closed = np.vstack([pts, pts[0]])          # close the loop
    seg = np.diff(closed, axis=0)
    seg_len = np.hypot(seg[:, 0], seg[:, 1])
    total = float(seg_len.sum())
    if total <= 0:
        return pts[:1]

    n = max(1, int(round(total / spacing_px)))
    targets = np.linspace(0.0, total, n, endpoint=False)
    cum = np.concatenate([[0.0], np.cumsum(seg_len)])

    out = np.empty((n, 2), dtype=float)
    for k, dist in enumerate(targets):
        i = int(np.searchsorted(cum, dist, side="right") - 1)
        i = min(max(i, 0), len(seg) - 1)
        denom = seg_len[i] if seg_len[i] > 0 else 1.0
        t = (dist - cum[i]) / denom
        out[k] = closed[i] + t * seg[i]
    return out


def resample_open(points: np.ndarray, spacing: float) -> np.ndarray:
    """Place points every ``spacing`` along an OPEN polyline (a stroke).

    Both endpoints are always included so stroke ends get a dot.
    """
    pts = np.asarray(points, dtype=float)
    if len(pts) < 2:
        return pts

    seg = np.diff(pts, axis=0)
    seg_len = np.hypot(seg[:, 0], seg[:, 1])
    total = float(seg_len.sum())
    if total <= 0:
        return pts[:1]

    n = max(1, int(round(total / spacing)))
    targets = np.linspace(0.0, total, n + 1)   # include both endpoints
    cum = np.concatenate([[0.0], np.cumsum(seg_len)])

    out = np.empty((len(targets), 2), dtype=float)
    for k, dist in enumerate(targets):
        i = int(np.searchsorted(cum, dist, side="right") - 1)
        i = min(max(i, 0), len(seg) - 1)
        denom = seg_len[i] if seg_len[i] > 0 else 1.0
        t = (dist - cum[i]) / denom
        out[k] = pts[i] + t * seg[i]
    return out


def sample_polylines(polylines: List[np.ndarray], spacing: float,
                     closed: bool) -> np.ndarray:
    """Resample a list of polylines (in mm) into one (M, 2) dot array."""
    fn = resample_closed if closed else resample_open
    dots = [fn(p, spacing) for p in polylines]
    dots = [d for d in dots if len(d)]
    if not dots:
        return np.empty((0, 2), dtype=float)
    return np.vstack(dots)


def sample_all(contours: List[np.ndarray], spacing_px: float) -> np.ndarray:
    """Sample every contour and stack the resulting dots into one (M,2) array."""
    all_dots = [resample_closed(c, spacing_px) for c in contours]
    all_dots = [d for d in all_dots if len(d)]
    if not all_dots:
        return np.empty((0, 2), dtype=float)
    return np.vstack(all_dots)
