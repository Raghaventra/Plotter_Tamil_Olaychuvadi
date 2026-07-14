"""Stage 2 — turn a (possibly noisy) scan into a clean binary ink mask.

Output convention everywhere downstream: ``ink`` is uint8, 255 = ink stroke,
0 = background paper.
"""
from __future__ import annotations

import cv2
import numpy as np

from .config import Config


def to_ink(gray: np.ndarray, cfg: Config) -> np.ndarray:
    g = gray
    if cfg.denoise:
        g = cv2.medianBlur(g, 3)
        g = cv2.bilateralFilter(g, 5, 40, 40)

    if cfg.threshold == "adaptive":
        bw = cv2.adaptiveThreshold(
            g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,
            cfg.adaptive_block, cfg.adaptive_C,
        )
    else:
        _, bw = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Ensure ink is the foreground (255). Paper is assumed to be the majority.
    if int((bw == 255).sum()) > int((bw == 0).sum()):
        ink = cv2.bitwise_not(bw)
    else:
        ink = bw

    # small morphological close to bridge scan gaps in strokes
    ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

    if cfg.deskew:
        ink = _deskew(ink)

    if cfg.remove_speckle:
        ink = _remove_speckle(ink, cfg.speckle_rel)

    return ink


def estimate_letter_height_px(ink: np.ndarray) -> float:
    """Median height of connected components -> robust letter height estimate."""
    n, _labels, stats, _cent = cv2.connectedComponentsWithStats(ink, connectivity=8)
    heights = [stats[i, cv2.CC_STAT_HEIGHT] for i in range(1, n)
               if stats[i, cv2.CC_STAT_HEIGHT] > 2]
    if heights:
        return float(np.median(heights))
    return float(ink.shape[0]) / 20.0


def _remove_speckle(ink: np.ndarray, speckle_rel: float) -> np.ndarray:
    """Drop connected components much smaller than the median letter height."""
    n, labels, stats, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
    if n <= 1:
        return ink
    heights = np.array([stats[i, cv2.CC_STAT_HEIGHT] for i in range(1, n)])
    med_h = float(np.median(heights)) if len(heights) else 0.0
    min_dim = max(2.0, speckle_rel * med_h)

    keep = np.zeros(ink.shape, dtype=np.uint8)
    for i in range(1, n):
        w = stats[i, cv2.CC_STAT_WIDTH]
        h = stats[i, cv2.CC_STAT_HEIGHT]
        if max(w, h) >= min_dim:
            keep[labels == i] = 255
    return keep


def _deskew(ink: np.ndarray) -> np.ndarray:
    coords = np.column_stack(np.where(ink > 0))
    if len(coords) < 50:
        return ink
    angle = cv2.minAreaRect(coords[:, ::-1].astype(np.float32))[-1]
    if angle < -45:
        angle += 90
    if abs(angle) > 15:      # unlikely to be true skew for art-writing; skip
        return ink
    h, w = ink.shape
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(ink, m, (w, h), flags=cv2.INTER_NEAREST,
                          borderValue=0)
