"""Stage 7 — render a PNG showing exactly where every dot will be punched."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from .config import Config


def render_preview(dots_mm: np.ndarray, cfg: Config, out_path: str,
                   px_per_mm: float = 12.0) -> str:
    """Draw the work area and every punch point to a PNG for verification."""
    w = int(round(cfg.work_w * px_per_mm))
    h = int(round(cfg.work_h * px_per_mm))
    img = Image.new("RGB", (w, h), (250, 249, 244))   # faint palm-leaf cream
    draw = ImageDraw.Draw(img)

    # margin rectangle (usable area)
    m = cfg.margin_mm * px_per_mm
    draw.rectangle([m, m, w - m, h - m], outline=(210, 205, 190), width=1)

    r = max(1.0, (cfg.spacing_mm * px_per_mm) * 0.28)   # dot radius for display
    for x, y in dots_mm:
        px = x * px_per_mm
        py = h - (y * px_per_mm)          # flip Y for image display
        draw.ellipse([px - r, py - r, px + r, py + r], fill=(30, 30, 30))

    # footer label
    draw.text((6, 6), f"{len(dots_mm)} dots | {cfg.work_w:.0f}x{cfg.work_h:.0f} mm",
              fill=(120, 110, 90))
    img.save(out_path)
    return out_path
