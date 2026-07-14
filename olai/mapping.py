"""Stage 4 — map dots from image pixels into machine millimetres.

Image coordinates: origin top-left, +y downward.
Machine coordinates: origin bottom-left, +y upward (GRBL convention).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class MapResult:
    dots_mm: np.ndarray          # (M, 2) in machine millimetres
    mm_per_px: float             # final scale applied
    content_w_mm: float
    content_h_mm: float
    fitted: bool                 # True if auto-shrunk to fit the work area


def map_to_machine(
    dots_px: np.ndarray,
    letter_height_px: float,
    *,
    target_letter_height_mm: float,
    work_w: float,
    work_h: float,
    margin_mm: float,
    fit_if_too_big: bool,
) -> MapResult:
    if len(dots_px) == 0:
        return MapResult(dots_px.copy(), 0.0, 0.0, 0.0, False)

    # Base scale so a typical letter becomes target_letter_height_mm tall.
    mm_per_px = target_letter_height_mm / max(letter_height_px, 1e-6)

    min_x, min_y = dots_px.min(axis=0)
    max_x, max_y = dots_px.max(axis=0)
    span_x_px = max(max_x - min_x, 1e-6)
    span_y_px = max(max_y - min_y, 1e-6)

    usable_w = work_w - 2 * margin_mm
    usable_h = work_h - 2 * margin_mm

    fitted = False
    if fit_if_too_big:
        # Shrink uniformly if the content would overflow the usable area.
        fit_scale = min(
            usable_w / (span_x_px * mm_per_px),
            usable_h / (span_y_px * mm_per_px),
            1.0,
        )
        if fit_scale < 1.0:
            mm_per_px *= fit_scale
            fitted = True

    content_w_mm = span_x_px * mm_per_px
    content_h_mm = span_y_px * mm_per_px

    # Anchor the content block at the top-left of the usable area.
    x_mm = margin_mm + (dots_px[:, 0] - min_x) * mm_per_px
    # Flip Y: image top -> machine top (work_h - margin).
    top_mm = work_h - margin_mm
    y_mm = top_mm - (dots_px[:, 1] - min_y) * mm_per_px

    dots_mm = np.column_stack([x_mm, y_mm])
    return MapResult(dots_mm, mm_per_px, content_w_mm, content_h_mm, fitted)


@dataclass
class TransformInfo:
    mm_per_px: float
    content_w_mm: float
    content_h_mm: float
    fitted: bool


def polylines_to_mm(
    polys_px,
    letter_height_px: float,
    *,
    target_letter_height_mm: float,
    work_w: float,
    work_h: float,
    margin_mm: float,
    fit_if_too_big: bool,
):
    """Map a list of pixel polylines to machine mm (scale, Y-flip, margins, fit).

    Scaling/resampling in this order (map first, resample in mm afterwards)
    guarantees the on-paper dot spacing equals the configured value regardless
    of input resolution.
    """
    all_pts = np.vstack(polys_px)
    min_xy = all_pts.min(axis=0)
    max_xy = all_pts.max(axis=0)
    span = np.maximum(max_xy - min_xy, 1e-6)

    mm_per_px = target_letter_height_mm / max(letter_height_px, 1e-6)
    usable_w = work_w - 2 * margin_mm
    usable_h = work_h - 2 * margin_mm

    fitted = False
    if fit_if_too_big:
        fit = min(usable_w / (span[0] * mm_per_px),
                  usable_h / (span[1] * mm_per_px), 1.0)
        if fit < 1.0:
            mm_per_px *= fit
            fitted = True

    top_mm = work_h - margin_mm
    out = []
    for p in polys_px:
        x = margin_mm + (p[:, 0] - min_xy[0]) * mm_per_px
        y = top_mm - (p[:, 1] - min_xy[1]) * mm_per_px
        out.append(np.column_stack([x, y]))

    info = TransformInfo(mm_per_px, span[0] * mm_per_px, span[1] * mm_per_px, fitted)
    return out, info


def bounds_ok(dots_mm: np.ndarray, work_w: float, work_h: float) -> bool:
    if len(dots_mm) == 0:
        return True
    return bool(
        dots_mm[:, 0].min() >= -1e-6
        and dots_mm[:, 1].min() >= -1e-6
        and dots_mm[:, 0].max() <= work_w + 1e-6
        and dots_mm[:, 1].max() <= work_h + 1e-6
    )
