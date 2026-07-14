"""Stage 1 — rasterize a PDF page to a grayscale image."""
from __future__ import annotations

import numpy as np

try:
    import fitz  # PyMuPDF
except ImportError as exc:  # pragma: no cover
    raise ImportError("PyMuPDF is required (pip install PyMuPDF)") from exc


def render_pdf_page(pdf_path: str, page_index: int, dpi: int):
    """Render one PDF page to a grayscale numpy array.

    Returns
    -------
    gray : np.ndarray (H, W) uint8      0 = black ink, 255 = white paper
    px_per_mm : float                   pixels per millimetre at this DPI
    """
    doc = fitz.open(pdf_path)
    if not (0 <= page_index < doc.page_count):
        raise IndexError(
            f"page_index {page_index} out of range (PDF has {doc.page_count} pages)"
        )
    page = doc[page_index]
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csGRAY, alpha=False)
    gray = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    doc.close()
    px_per_mm = dpi / 25.4
    return gray.copy(), px_per_mm
