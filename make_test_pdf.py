#!/usr/bin/env python3
"""Generate a Tamil test PDF for developing the pipeline.

Geethapria is a legacy non-Unicode font that needs TSCII-encoded input, so
for development we render *correctly shaped* Unicode Tamil (via Pillow + raqm)
with an available Tamil font and embed it into a PDF. The dot pipeline works
on rendered pixels, so your real Geethapria PDF flows through identically.
"""
from __future__ import annotations

import os

import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont

# A few Tamil words/lines (Unicode) for the sample sheet.
LINES = [
    "தமிழ் ஓலைச் சுவடி",
    "அகர முதல எழுத்தெல்லாம்",
    "ஆதி பகவன் முதற்றே உலகு",
    "கடல் கடந்த தமிழ்",
]

CANDIDATE_FONTS = [
    "/usr/share/fonts/truetype/lohit-tamil/Lohit-Tamil.ttf",
    "/usr/share/fonts/truetype/samyak-fonts/Samyak-Tamil.ttf",
    "/usr/share/fonts/truetype/lohit-tamil-classical/Lohit-Tamil-Classical.ttf",
]


def _find_font() -> str:
    for f in CANDIDATE_FONTS:
        if os.path.exists(f):
            return f
    raise FileNotFoundError("No Tamil font found; install fonts-lohit-taml.")


def make_pdf(out_pdf: str, font_path: str | None = None,
             render_px: int = 2400) -> str:
    font_path = font_path or _find_font()

    # Render text to a high-res RGB image with correct Tamil shaping (raqm).
    W, H = render_px, int(render_px * 0.55)
    img = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, size=int(H * 0.14),
                              layout_engine=ImageFont.Layout.RAQM)

    y = int(H * 0.06)
    for line in LINES:
        draw.text((int(W * 0.06), y), line, font=font, fill=(0, 0, 0))
        y += int(H * 0.22)

    # Embed the image into a PDF page (sized so it looks like ~180 x 100 mm).
    page_w_pt = 180 / 25.4 * 72.0
    page_h_pt = page_w_pt * (H / W)
    doc = fitz.open()
    page = doc.new_page(width=page_w_pt, height=page_h_pt)

    os.makedirs(os.path.dirname(out_pdf) or ".", exist_ok=True)
    tmp_png = out_pdf + ".tmp.png"
    img.save(tmp_png)
    page.insert_image(fitz.Rect(0, 0, page_w_pt, page_h_pt), filename=tmp_png)
    doc.save(out_pdf)
    doc.close()
    os.remove(tmp_png)
    return out_pdf


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "samples/test_tamil.pdf"
    path = make_pdf(out)
    print(f"Wrote test PDF: {path} (font: {_find_font()})")
