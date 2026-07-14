"""Configuration loading and validation."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict

import yaml


@dataclass
class Config:
    """Typed view over ``config.yaml``.

    The raw dict is kept in ``raw`` so nothing is ever silently lost, while
    the frequently used values are exposed as attributes with defaults.
    """

    raw: Dict[str, Any] = field(default_factory=dict)
    base_dir: str = "."

    # -- input
    input_pdf: str = "samples/test_tamil.pdf"
    page_index: int = 0
    render_dpi: int = 600
    max_dimension_px: int = 3000

    # -- stroke style
    stroke_mode: str = "centerline"   # "centerline" (handwriting) | "outline"

    # -- scan preprocessing
    denoise: bool = True
    threshold: str = "otsu"           # "otsu" | "adaptive"
    adaptive_block: int = 41
    adaptive_C: float = 10.0
    deskew: bool = False
    remove_speckle: bool = True
    speckle_rel: float = 0.12         # drop blobs < this * median letter height
    min_stroke_rel: float = 0.12      # drop strokes shorter than this * letter height

    # -- output
    output_gcode: str = "output/olai.gcode"
    output_preview: str = "output/preview.png"

    # -- work area (mm)
    work_w: float = 345.0
    work_h: float = 240.0

    # -- layout
    target_letter_height_mm: float = 6.0
    margin_mm: float = 10.0
    fit_if_too_big: bool = True

    # -- dots
    spacing_mm: float = 0.8
    min_contour_mm: float = 0.6
    include_holes: bool = True

    # -- pen
    pen_mode: str = "z"
    z_up_mm: float = 2.0
    z_down_mm: float = -0.5
    dwell_ms: int = 0
    servo_down_cmd: str = "M3 S1000"
    servo_up_cmd: str = "M5"

    # -- feeds
    plunge_z: float = 400.0
    travel_xy: float = 1500.0
    travel_g0: bool = True

    # -- optimize
    reorder: bool = True
    band_mm: float = 2.0

    def path(self, p: str) -> str:
        """Resolve a possibly-relative path against the config's base dir."""
        if os.path.isabs(p):
            return p
        return os.path.normpath(os.path.join(self.base_dir, p))


def load_config(config_path: str) -> Config:
    with open(config_path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    base_dir = os.path.dirname(os.path.abspath(config_path))

    wa = raw.get("work_area", {})
    lay = raw.get("layout", {})
    dots = raw.get("dots", {})
    pen = raw.get("pen", {})
    feeds = raw.get("feeds", {})
    opt = raw.get("optimize", {})
    inp = raw.get("input", {})
    pre = raw.get("preprocess", {})

    cfg = Config(
        raw=raw,
        base_dir=base_dir,
        input_pdf=raw.get("input_pdf", Config.input_pdf),
        page_index=int(raw.get("page_index", Config.page_index)),
        render_dpi=int(raw.get("render_dpi", Config.render_dpi)),
        max_dimension_px=int(inp.get("max_dimension_px", Config.max_dimension_px)),
        stroke_mode=str(raw.get("stroke_mode", Config.stroke_mode)).lower(),
        denoise=bool(pre.get("denoise", Config.denoise)),
        threshold=str(pre.get("threshold", Config.threshold)).lower(),
        adaptive_block=int(pre.get("adaptive_block", Config.adaptive_block)),
        adaptive_C=float(pre.get("adaptive_C", Config.adaptive_C)),
        deskew=bool(pre.get("deskew", Config.deskew)),
        remove_speckle=bool(pre.get("remove_speckle", Config.remove_speckle)),
        speckle_rel=float(pre.get("speckle_rel", Config.speckle_rel)),
        min_stroke_rel=float(pre.get("min_stroke_rel", Config.min_stroke_rel)),
        output_gcode=raw.get("output_gcode", Config.output_gcode),
        output_preview=raw.get("output_preview", Config.output_preview),
        work_w=float(wa.get("width_mm", Config.work_w)),
        work_h=float(wa.get("height_mm", Config.work_h)),
        target_letter_height_mm=float(
            lay.get("target_letter_height_mm", Config.target_letter_height_mm)
        ),
        margin_mm=float(lay.get("margin_mm", Config.margin_mm)),
        fit_if_too_big=bool(lay.get("fit_if_too_big", Config.fit_if_too_big)),
        spacing_mm=float(dots.get("spacing_mm", Config.spacing_mm)),
        min_contour_mm=float(dots.get("min_contour_mm", Config.min_contour_mm)),
        include_holes=bool(dots.get("include_holes", Config.include_holes)),
        pen_mode=str(pen.get("mode", Config.pen_mode)).lower(),
        z_up_mm=float(pen.get("z_up_mm", Config.z_up_mm)),
        z_down_mm=float(pen.get("z_down_mm", Config.z_down_mm)),
        dwell_ms=int(pen.get("dwell_ms", Config.dwell_ms)),
        servo_down_cmd=str(pen.get("servo_down_cmd", Config.servo_down_cmd)),
        servo_up_cmd=str(pen.get("servo_up_cmd", Config.servo_up_cmd)),
        plunge_z=float(feeds.get("plunge_z", Config.plunge_z)),
        travel_xy=float(feeds.get("travel_xy", Config.travel_xy)),
        travel_g0=bool(feeds.get("travel_g0", Config.travel_g0)),
        reorder=bool(opt.get("reorder", Config.reorder)),
        band_mm=float(opt.get("band_mm", Config.band_mm)),
    )
    _validate(cfg)
    return cfg


def _validate(cfg: Config) -> None:
    errs = []
    if cfg.render_dpi < 72:
        errs.append("render_dpi should be >= 72")
    if cfg.spacing_mm <= 0:
        errs.append("dots.spacing_mm must be > 0")
    if cfg.target_letter_height_mm <= 0:
        errs.append("layout.target_letter_height_mm must be > 0")
    if cfg.margin_mm < 0 or 2 * cfg.margin_mm >= min(cfg.work_w, cfg.work_h):
        errs.append("layout.margin_mm too large for the work area")
    if cfg.pen_mode not in ("z", "servo"):
        errs.append("pen.mode must be 'z' or 'servo'")
    if cfg.stroke_mode not in ("centerline", "outline"):
        errs.append("stroke_mode must be 'centerline' or 'outline'")
    if cfg.threshold not in ("otsu", "adaptive"):
        errs.append("preprocess.threshold must be 'otsu' or 'adaptive'")
    if cfg.adaptive_block % 2 == 0 or cfg.adaptive_block < 3:
        errs.append("preprocess.adaptive_block must be odd and >= 3")
    if cfg.z_up_mm <= cfg.z_down_mm:
        errs.append("pen.z_up_mm must be above pen.z_down_mm")
    if errs:
        raise ValueError("Invalid config:\n  - " + "\n  - ".join(errs))
