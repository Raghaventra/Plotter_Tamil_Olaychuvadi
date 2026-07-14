"""Stage 2 — extract glyph outlines (contours) from the rasterized page."""
from __future__ import annotations

from typing import List, Tuple

import cv2
import numpy as np


def extract_contours(
    gray: np.ndarray,
    px_per_mm: float,
    min_contour_mm: float,
    include_holes: bool,
) -> Tuple[List[np.ndarray], np.ndarray, List[Tuple[int, int, int, int]]]:
    """Binarize the page and return glyph outlines.

    Parameters
    ----------
    gray : grayscale page (0 ink .. 255 paper)
    px_per_mm : scale from render stage
    min_contour_mm : drop contours whose perimeter is below this (mm)
    include_holes : also return inner holes of glyphs (loops)

    Returns
    -------
    contours : list of (N,2) int arrays in (x, y) pixel coordinates
    bw : binarized image (255 = ink) for debugging/preview
    ext_boxes : bounding boxes (x, y, w, h) of *outer* contours only,
                used to estimate the letter height
    """
    # Otsu handles varying scan brightness; INV so ink becomes white (255).
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    retr = cv2.RETR_CCOMP if include_holes else cv2.RETR_EXTERNAL
    found = cv2.findContours(bw, retr, cv2.CHAIN_APPROX_NONE)
    contours = found[0] if len(found) == 2 else found[1]
    hierarchy = found[1] if len(found) == 2 else found[2]

    min_peri_px = min_contour_mm * px_per_mm

    kept: List[np.ndarray] = []
    ext_boxes: List[Tuple[int, int, int, int]] = []

    for i, c in enumerate(contours):
        peri = cv2.arcLength(c, True)
        if peri < min_peri_px:
            continue
        pts = c.reshape(-1, 2)
        kept.append(pts)
        # In RETR_CCOMP hierarchy, top-level (outer) contours have parent == -1.
        is_outer = True
        if hierarchy is not None and include_holes:
            is_outer = hierarchy[0][i][3] == -1
        if is_outer:
            ext_boxes.append(cv2.boundingRect(c))

    return kept, bw, ext_boxes


def contours_from_ink(ink: np.ndarray, include_holes: bool) -> List[np.ndarray]:
    """Outline mode: contours (outer + optional holes) from a binary ink mask.

    Returns a list of (N, 2) float arrays in (x, y) pixels. No size filtering
    here — the pipeline handles length/size filtering uniformly afterwards.
    """
    retr = cv2.RETR_CCOMP if include_holes else cv2.RETR_EXTERNAL
    found = cv2.findContours(ink, retr, cv2.CHAIN_APPROX_NONE)
    contours = found[0] if len(found) == 2 else found[1]
    return [c.reshape(-1, 2).astype(float) for c in contours if len(c) >= 2]


def estimate_letter_height_px(ext_boxes, gray_shape) -> float:
    """Median height of outer contour bounding boxes -> a robust letter height.

    Falls back to a fraction of the page height if nothing was found.
    """
    heights = [h for (_x, _y, _w, h) in ext_boxes if h > 1]
    if heights:
        return float(np.median(heights))
    return float(gray_shape[0]) / 20.0
