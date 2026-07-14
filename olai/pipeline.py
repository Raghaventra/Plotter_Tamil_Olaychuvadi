"""Orchestrates the full input -> dotted G-code pipeline.

Stages:
  1 load       any input (PDF/SVG/image) -> grayscale
  2 preprocess scan cleanup -> binary ink mask
  3 geometry   centerline (skeleton polylines) OR outline (contours)
  4 map        pixels -> machine mm (scale to letter height, Y-flip, fit)
  5 resample   dots every spacing_mm along strokes (correct on-paper spacing)
  6 optimize   serpentine ordering
  7 emit       G-code + preview
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np

from . import contours as C
from . import gcode as G
from . import input_loader as IL
from . import mapping as M
from . import optimize as O
from . import preprocess as PP
from . import sampler as S
from . import skeleton as SK
from .config import Config


@dataclass
class Result:
    stroke_mode: str
    n_strokes: int
    n_dots: int
    content_w_mm: float
    content_h_mm: float
    mm_per_px: float
    fitted: bool
    travel_mm: float
    runtime_s: float
    gcode_path: str
    preview_path: str


def run(cfg: Config, verbose: bool = True) -> Result:
    def log(msg: str) -> None:
        if verbose:
            print(msg)

    src = cfg.path(cfg.input_pdf)
    if not os.path.exists(src):
        raise FileNotFoundError(f"input not found: {src}")

    log(f"[1/7] Loading {src}")
    gray, px_per_mm = IL.load_grayscale(
        src, cfg.page_index, cfg.render_dpi, cfg.max_dimension_px
    )
    log(f"      image = {gray.shape[1]}x{gray.shape[0]} px  ({px_per_mm:.2f} px/mm)")

    log("[2/7] Preprocessing scan -> ink mask")
    ink = PP.to_ink(gray, cfg)
    letter_h_px = PP.estimate_letter_height_px(ink)
    ink_frac = float((ink > 0).mean())
    log(f"      ink coverage = {ink_frac * 100:.1f}%  |  "
        f"est. letter height = {letter_h_px:.1f}px")

    log(f"[3/7] Extracting geometry (mode: {cfg.stroke_mode})")
    if cfg.stroke_mode == "centerline":
        polys_px = SK.skeleton_polylines(ink)
        closed = False
    else:
        polys_px = C.contours_from_ink(ink, cfg.include_holes)
        closed = True

    # Drop tiny strokes/contours relative to letter height (kills nubs/noise).
    min_len_px = max(1.0, cfg.min_stroke_rel * letter_h_px)
    polys_px = [p for p in polys_px if SK.polyline_length_px(p) >= min_len_px]
    log(f"      {len(polys_px)} strokes (>= {min_len_px:.0f}px)")
    if not polys_px:
        raise RuntimeError("No strokes found. Check threshold/preprocess settings.")

    log("[4/7] Mapping to machine millimetres")
    polys_mm, info = M.polylines_to_mm(
        polys_px,
        letter_h_px,
        target_letter_height_mm=cfg.target_letter_height_mm,
        work_w=cfg.work_w,
        work_h=cfg.work_h,
        margin_mm=cfg.margin_mm,
        fit_if_too_big=cfg.fit_if_too_big,
    )
    log(f"      content = {info.content_w_mm:.1f} x {info.content_h_mm:.1f} mm"
        + ("  [auto-fitted to bed]" if info.fitted else ""))

    log(f"[5/7] Sampling dots every {cfg.spacing_mm} mm")
    dots_mm = S.sample_polylines(polys_mm, cfg.spacing_mm, closed=closed)
    log(f"      {len(dots_mm)} dots")
    if not M.bounds_ok(dots_mm, cfg.work_w, cfg.work_h):
        log("      WARNING: some dots fall outside the work area!")

    if cfg.reorder and len(dots_mm) > 2:
        before = O.travel_distance(dots_mm)
        reordered = O.serpentine_order(dots_mm, cfg.band_mm)
        after = O.travel_distance(reordered)
        if after < before:            # only adopt if it actually helps
            dots_mm = reordered
            log(f"      ordered: travel {before:.0f} -> {after:.0f} mm")
        else:
            log(f"      kept original order (travel {before:.0f} mm; "
                f"serpentine would be {after:.0f} mm)")

    travel_mm = O.travel_distance(dots_mm)
    runtime_s = G.estimate_runtime_s(dots_mm, cfg)

    log("[6/7] Writing G-code")
    gpath = cfg.path(cfg.output_gcode)
    os.makedirs(os.path.dirname(gpath) or ".", exist_ok=True)
    meta = {
        "source": os.path.basename(src),
        "stroke_mode": cfg.stroke_mode,
        "est_runtime_min": f"{runtime_s / 60.0:.1f}",
    }
    with open(gpath, "w", encoding="utf-8") as fh:
        fh.write(G.build_gcode(dots_mm, cfg, meta))
    log(f"      -> {gpath}")

    log("[7/7] Rendering preview")
    from . import preview as P
    ppath = cfg.path(cfg.output_preview)
    os.makedirs(os.path.dirname(ppath) or ".", exist_ok=True)
    P.render_preview(dots_mm, cfg, ppath)
    log(f"      -> {ppath}")

    log(f"DONE. {len(dots_mm)} dots, ~{runtime_s / 60.0:.1f} min est. run time.")

    return Result(
        stroke_mode=cfg.stroke_mode,
        n_strokes=len(polys_px),
        n_dots=len(dots_mm),
        content_w_mm=info.content_w_mm,
        content_h_mm=info.content_h_mm,
        mm_per_px=info.mm_per_px,
        fitted=info.fitted,
        travel_mm=travel_mm,
        runtime_s=runtime_s,
        gcode_path=gpath,
        preview_path=ppath,
    )
