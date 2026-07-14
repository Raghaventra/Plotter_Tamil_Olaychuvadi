"""Stage 3a (centerline mode) — skeletonize ink and trace it into polylines.

The skeleton (1-px medial axis) is converted into a graph and walked into
open polylines (one per stroke segment between endpoints/junctions), plus any
closed loops. Each polyline is an (N, 2) float array of (x, y) pixels.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import cv2
import numpy as np
from skimage.morphology import skeletonize

Pt = Tuple[int, int]
_OFFSETS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def skeleton_polylines(ink: np.ndarray) -> List[np.ndarray]:
    sk = skeletonize(ink > 0)
    return _trace(sk)


def _trace(sk: np.ndarray) -> List[np.ndarray]:
    ys, xs = np.where(sk)
    if len(ys) == 0:
        return []
    ptset = set(zip(ys.tolist(), xs.tolist()))

    def nbrs(p: Pt) -> List[Pt]:
        y, x = p
        out = []
        for dy, dx in _OFFSETS:
            q = (y + dy, x + dx)
            if q in ptset:
                out.append(q)
        return out

    deg: Dict[Pt, int] = {p: len(nbrs(p)) for p in ptset}
    visited_edges = set()
    polylines: List[List[Pt]] = []

    def walk(start: Pt, second: Pt) -> List[Pt]:
        line = [start, second]
        visited_edges.add(frozenset((start, second)))
        prev, cur = start, second
        while deg.get(cur, 0) == 2:
            nxt = None
            for q in nbrs(cur):
                if q != prev and frozenset((cur, q)) not in visited_edges:
                    nxt = q
                    break
            if nxt is None:
                break
            visited_edges.add(frozenset((cur, nxt)))
            line.append(nxt)
            prev, cur = cur, nxt
        return line

    # 1) start from every node (endpoint or junction, degree != 2)
    nodes = [p for p in ptset if deg[p] != 2]
    for node in nodes:
        for q in nbrs(node):
            if frozenset((node, q)) not in visited_edges:
                polylines.append(walk(node, q))

    # 2) remaining pixels belong to isolated loops (all degree 2)
    for p in ptset:
        for q in nbrs(p):
            if frozenset((p, q)) not in visited_edges:
                polylines.append(walk(p, q))

    # convert (y, x) -> (x, y) float arrays
    result = []
    for line in polylines:
        if len(line) >= 2:
            arr = np.array([(x, y) for (y, x) in line], dtype=float)
            result.append(arr)
    return result


def polyline_length_px(poly: np.ndarray) -> float:
    if len(poly) < 2:
        return 0.0
    d = np.diff(poly, axis=0)
    return float(np.hypot(d[:, 0], d[:, 1]).sum())
