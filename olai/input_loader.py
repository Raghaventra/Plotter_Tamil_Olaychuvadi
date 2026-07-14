"""Stage 1 — load any supported input into a grayscale image.

Supported: PDF, SVG (both via PyMuPDF), and raster images (PNG/JPG/TIFF/...).
Large scans are downscaled to `max_dimension_px` for speed and noise control.
"""
from __future__ import annotations

import os

import cv2
import numpy as np
from PIL import Image

try:
    import fitz  # PyMuPDF
except ImportError as exc:  # pragma: no cover
    raise ImportError("PyMuPDF is required (pip install PyMuPDF)") from exc

RASTER_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".ppm"}
VECTOR_EXT = {".pdf", ".svg", ".svgz", ".xps", ".epub", ".cbz"}


def load_grayscale(path: str, page_index: int, dpi: int, max_dimension_px: int):
    """Return (gray uint8 HxW, px_per_mm).

    px_per_mm is approximate for raster scans (used only for noise thresholds;
    the pipeline rescales everything to the target letter height later).
    """
    ext = os.path.splitext(path)[1].lower()

    if ext in RASTER_EXT:
        pil = Image.open(path).convert("L")
        info_dpi = pil.info.get("dpi")
        eff_dpi = float(info_dpi[0]) if info_dpi and info_dpi[0] else float(dpi)
        gray = np.array(pil)
        px_per_mm = eff_dpi / 25.4
    else:
        # PDF / SVG / other doc formats via PyMuPDF.
        doc = fitz.open(path)
        if not doc.is_pdf:
            # e.g. SVG -> convert to a 1-page PDF first.
            pdf_bytes = doc.convert_to_pdf()
            doc = fitz.open("pdf", pdf_bytes)
        if not (0 <= page_index < doc.page_count):
            raise IndexError(
                f"page_index {page_index} out of range (doc has {doc.page_count})"
            )
        zoom = dpi / 72.0
        pix = doc[page_index].get_pixmap(
            matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csGRAY, alpha=False
        )
        gray = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
        gray = gray.copy()
        doc.close()
        px_per_mm = dpi / 25.4

    gray, px_per_mm = _downscale(gray, px_per_mm, max_dimension_px)
    return gray, px_per_mm


def _downscale(gray: np.ndarray, px_per_mm: float, max_dim: int):
    h, w = gray.shape[:2]
    long_side = max(h, w)
    if max_dim and long_side > max_dim:
        scale = max_dim / long_side
        new_size = (max(1, int(round(w * scale))), max(1, int(round(h * scale))))
        gray = cv2.resize(gray, new_size, interpolation=cv2.INTER_AREA)
        px_per_mm *= scale
    return gray, px_per_mm
