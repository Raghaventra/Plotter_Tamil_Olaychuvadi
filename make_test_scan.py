#!/usr/bin/env python3
"""Generate synthetic *scanned handwriting* test inputs.

Produces:
  samples/test_scan.png   - noisy, slightly rotated, paper-toned raster "scan"
  samples/test_scan.pdf   - the same image wrapped in a PDF (typical scan export)
  samples/test_strokes.svg- a small vector SVG to exercise the SVG loader path

Real handwriting will differ, but this mimics scan artefacts (noise, blur,
skew, off-white paper) so the preprocessing + skeleton pipeline is exercised.
"""
from __future__ import annotations

import os

import fitz
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

LINES = ["தமிழ் ஓலைச் சுவடி", "அகர முதல", "கடல் கடந்த தமிழ்"]

CANDIDATE_FONTS = [
    "/usr/share/fonts/truetype/lohit-tamil/Lohit-Tamil.ttf",
    "/usr/share/fonts/truetype/samyak-fonts/Samyak-Tamil.ttf",
]


def _font_path() -> str:
    for f in CANDIDATE_FONTS:
        if os.path.exists(f):
            return f
    raise FileNotFoundError("No Tamil font found; install fonts-lohit-taml.")


def _render_clean(w=1800, h=900) -> Image.Image:
    img = Image.new("L", (w, h), 255)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(_font_path(), size=int(h * 0.16),
                              layout_engine=ImageFont.Layout.RAQM)
    y = int(h * 0.08)
    for line in LINES:
        draw.text((int(w * 0.07), y), line, font=font, fill=0)
        y += int(h * 0.30)
    return img


def _scanify(img: Image.Image, rotate_deg=1.5, noise_sigma=10.0) -> Image.Image:
    # slight skew like a hand-fed scan
    img = img.rotate(rotate_deg, expand=False, fillcolor=255,
                     resample=Image.BICUBIC)
    # soft focus
    img = img.filter(ImageFilter.GaussianBlur(0.8))
    arr = np.asarray(img).astype(np.float32)
    # off-white paper tone + sensor noise
    arr = arr * 0.96 + 8.0
    arr += np.random.normal(0, noise_sigma, arr.shape)
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, mode="L")


def make(out_dir="samples") -> None:
    os.makedirs(out_dir, exist_ok=True)
    scan = _scanify(_render_clean())

    png_path = os.path.join(out_dir, "test_scan.png")
    scan.convert("RGB").save(png_path, dpi=(300, 300))

    # wrap the scan in a PDF (as most scanners export)
    pdf_path = os.path.join(out_dir, "test_scan.pdf")
    doc = fitz.open()
    w_pt = scan.width / 300 * 72.0
    h_pt = scan.height / 300 * 72.0
    page = doc.new_page(width=w_pt, height=h_pt)
    page.insert_image(fitz.Rect(0, 0, w_pt, h_pt), filename=png_path)
    doc.save(pdf_path)
    doc.close()

    # a tiny vector SVG (strokes) to prove the SVG loader path works
    svg_path = os.path.join(out_dir, "test_strokes.svg")
    with open(svg_path, "w", encoding="utf-8") as fh:
        fh.write(
            '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200">\n'
            '  <rect width="400" height="200" fill="white"/>\n'
            '  <path d="M40 150 C 80 40, 140 40, 160 150 S 240 260, 280 150" '
            'stroke="black" stroke-width="6" fill="none"/>\n'
            '  <path d="M300 60 L300 150" stroke="black" stroke-width="6" '
            'fill="none"/>\n'
            "</svg>\n"
        )

    print("wrote:", png_path, pdf_path, svg_path)


if __name__ == "__main__":
    make()
