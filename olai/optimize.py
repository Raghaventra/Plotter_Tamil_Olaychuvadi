"""Stage 5 — order the dots to minimise air travel.

Punching order does not matter for the result, only for time. A serpentine
(boustrophedon) sort by horizontal bands is O(n log n), robust for thousands
of dots, and produces near-minimal travel for scattered punch points.
"""
from __future__ import annotations

import numpy as np


def serpentine_order(dots_mm: np.ndarray, band_mm: float) -> np.ndarray:
    """Return dots reordered in a boustrophedon pattern.

    Dots are grouped into horizontal bands of height ``band_mm``. Bands are
    visited bottom-to-top; within each band dots are sorted by x, alternating
    direction band to band so the tool snakes across the sheet.
    """
    if len(dots_mm) <= 2 or band_mm <= 0:
        return dots_mm

    y = dots_mm[:, 1]
    band = np.floor((y - y.min()) / band_mm).astype(int)

    order = []
    for b in np.unique(band):            # unique() returns ascending -> bottom up
        idx = np.where(band == b)[0]
        xs = dots_mm[idx, 0]
        left_to_right = (b % 2 == 0)
        idx_sorted = idx[np.argsort(xs if left_to_right else -xs)]
        order.extend(idx_sorted.tolist())

    return dots_mm[np.asarray(order, dtype=int)]


def travel_distance(dots_mm: np.ndarray) -> float:
    """Total XY path length (mm) if dots are visited in the given order."""
    if len(dots_mm) < 2:
        return 0.0
    d = np.diff(dots_mm, axis=0)
    return float(np.hypot(d[:, 0], d[:, 1]).sum())
