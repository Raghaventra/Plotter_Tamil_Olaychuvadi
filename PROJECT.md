# Olai Chuvadi Plotter — Project Brief & Migration Notes

> Purpose of this file: a self-contained snapshot of the problem, decisions,
> specs, architecture, and current status — so this project can be picked up
> in a **new chat / by another person** with zero context loss.

> **PLAN UPDATE (2026-07-04):** Input changed from *typed* Tamil PDF to a
> **scanned copy of real Tamil handwriting / art-writing** (given as PDF, SVG,
> or image). This looks more natural / less "robotic" for the Olai-chuvadi
> effect. As a result the default dot style switched to **centerline** and a
> **scan-preprocessing** stage was added. The typed-PDF path (outline mode)
> still exists. See §12 for the full change log.

---

## 1. Problem statement

Preserve Tamil literature in the style of old **ஓலைச் சுவடி (Olai chuvadi /
palm-leaf manuscripts)**.

- **Input:** a **scanned copy of handwritten / art-written Tamil**, supplied as
  **PDF, SVG, or image** (PNG/JPG/TIFF...). (Originally: typed Geethapria PDF.)
- **Goal:** convert that writing into **dotted (perforated) Tamil letters** and
  produce a **GRBL-compatible G-code file**.
- **Physical output:** load the G-code in **GRBL-Plotter** software, drive a
  **2-axis pen plotter fitted with a sharp needle**, and have it **punch dots**
  along each pen stroke onto paper — recreating the engraved palm-leaf look.

Division of labour: **user** supplies the input file, feeds the produced
G-code into GRBL-Plotter, and runs the plotter. **This system** handles all the
image processing and G-code generation.

Pipeline in one line:

```
scan (PDF/SVG/image) → clean ink mask → centerline strokes → dots → GRBL G-code → plotter + needle → perforated paper
```

---

## 2. Key facts & constraints discovered

- **Handwriting needs centerline, not outline.** Outlining a thin pen stroke
  traces *both* edges → hollow, doubled letters. The natural writing look comes
  from **skeletonizing** each stroke and dotting its **centerline** (single
  dotted line down the pen path), like a stylus groove on a palm leaf.
- **Font encoding is a non-issue now** (input is a scan/image), but the
  original finding still holds and keeps the design font-agnostic: we always
  work on **rendered pixels**, never character codes.
  - Context: **Geethapria** is a legacy, non-Unicode TTF (1993, Altsys
    Fontographer, ~101 glyphs, TSCII-style). Character extraction is unreliable.
- Typing in Geethapria needs TSCII-encoded input, so for development we render
  **correctly shaped Unicode Tamil** (via Pillow + libraqm) with an available
  Tamil font (`Lohit-Tamil.ttf`) and embed it into a test PDF.

---

## 3. Hardware (user's machine)

Pen Plotter Writing/Drawing DIY Kit:

| Spec | Value |
|---|---|
| Working table size | **345 × 240 × 22 mm** (Z=22 mm is frame clearance only) |
| Machine type | CNC router / pen plotter |
| Number of axes | **2 (X, Y only)** |
| Pen/needle lift | **Servo**, driven by **GRBL-Plotter via Z up/down moves** |
| Power | 12V 3A |
| Software | **GRBL-Plotter** |

**Implication:** there is no real Z stepper. Perforation *depth* is set
**mechanically** (needle protrusion + servo down position). The G-code emits
`Z` up/down moves; GRBL-Plotter translates Z → servo angle.

---

## 4. Agreed design decisions

| Decision | Choice |
|---|---|
| Input | **Scanned handwriting** as PDF / SVG / image (auto-detected by extension) |
| Dot style | **Centerline** (default, for handwriting) — dots follow the middle of each stroke. `outline` mode kept for typed/solid glyphs |
| Machine action | **Punch** — needle stabs down then lifts, once per dot |
| Pen-lift command style | **Z moves** (`pen.mode: z`); optional `servo` (`M3/M5`) mode also implemented |

---

## 5. Machine / geometry parameters (defaults in `config.yaml`)

| Parameter | Value |
|---|---|
| Work area | 345 × 240 mm |
| Stroke mode | **centerline** (default) / outline |
| Target letter height | **6 mm** (median letter scaled to this) |
| Dot spacing | **0.8 mm** (measured on the OUTPUT paper) |
| Z travel (pen up) | **+2.0 mm** |
| Z punch (pen down) | **−0.5 mm** |
| Feed — XY travel | 1500 mm/min (rapids `G0` used by default) |
| Feed — Z plunge | 400 mm/min |
| Margin from edges | 10 mm |
| Render DPI (PDF/SVG) | 600 |
| Max working dimension | 3000 px (large scans downscaled) |
| Preprocess | denoise + Otsu (or adaptive) threshold, speckle removal, optional deskew |
| Dot ordering | serpentine, 2 mm bands (kept only if it reduces travel) |

---

## 6. Architecture / repo layout

```
Plotter/
├── config.yaml          ← ALL parameters live here (single source of truth)
├── run.py               ← CLI entry point:  python run.py
├── make_test_scan.py    ← generates scanned-handwriting test inputs (current)
├── make_test_pdf.py     ← generates a clean typed Tamil PDF (legacy/outline test)
├── requirements.txt
├── PROJECT.md           ← this file
├── olai/                ← the pipeline package
│   ├── __init__.py
│   ├── config.py            Config dataclass + YAML loader + validation
│   ├── input_loader.py  (1) load PDF/SVG/image → grayscale (+ downscale)
│   ├── preprocess.py    (2) denoise + threshold + speckle removal → ink mask
│   ├── skeleton.py      (3a) centerline: skeletonize + trace polylines
│   ├── contours.py      (3b) outline: findContours from ink mask
│   ├── mapping.py       (4) polylines: pixels → machine mm (scale, Y-flip, fit)
│   ├── sampler.py       (5) resample strokes → a dot every `spacing_mm` (in mm)
│   ├── optimize.py      (6) serpentine ordering to minimise air-travel
│   ├── gcode.py         (7) GRBL punch-cycle emitter + runtime estimate
│   ├── preview.py       (7) PNG showing every dot before cutting paper
│   ├── pipeline.py          orchestrates all stages, prints stats
│   └── render.py            (legacy, superseded by input_loader.py)
├── samples/
│   ├── test_scan.pdf / .png ← generated scanned-handwriting test inputs
│   ├── test_strokes.svg     ← generated SVG test input
│   └── test_tamil.pdf       ← generated typed-text test input
└── output/
    ├── olai.gcode           ← generated G-code
    └── preview.png          ← generated dot preview
```

### Pipeline stages

1. **input_loader** — load PDF/SVG (via PyMuPDF; SVG auto-converted to PDF) or
   a raster image to grayscale; downscale so the long side ≤ `max_dimension_px`.
2. **preprocess** — median+bilateral denoise, Otsu or adaptive threshold,
   auto-orient so **ink = 255**, morphological close, speckle removal
   (blobs < `speckle_rel` × letter height), optional deskew. Letter height =
   median connected-component height.
3. **geometry** —
   - *centerline* (default): `skimage.skeletonize` → graph trace into open
     polylines (one per stroke between endpoints/junctions) + closed loops.
   - *outline*: `findContours` (outer + optional holes) as closed polylines.
   Strokes shorter than `min_stroke_rel` × letter height are dropped.
4. **mapping** — scale so median letter = `target_letter_height_mm`; flip Y;
   apply margins; auto-shrink to fit the bed. **Mapping happens BEFORE
   resampling** so the 0.8 mm dot spacing is exact on the output paper.
5. **sampler** — resample each polyline in mm: `resample_open` for centerline,
   `resample_closed` for outline; flatten to a dot array.
6. **optimize** — serpentine sort by horizontal bands; adopted **only if it
   reduces total travel** (outline dots are already locally ordered).
7. **gcode / preview** — preamble (`G21/G90/G94`, pen up) → per dot `G0 X Y` →
   `G1 Z<down> F<plunge>` → `G1 Z<up> F<plunge>` → postamble (`G0 X0 Y0`, `M2`);
   `servo` mode substitutes `servo_down_cmd`/`servo_up_cmd`. Preview PNG drawn.

---

## 7. Environment & setup

- OS: Linux, **Python 3.8.10**, venv at `.venv/`.
- Dependencies (`requirements.txt`): `PyMuPDF`, `opencv-python-headless`,
  `numpy`, `PyYAML`, `Pillow` (built with **raqm** for Tamil shaping),
  `scikit-image` (skeletonization; pulls in `scipy`).
- System Tamil fonts present: `Lohit-Tamil.ttf`, `Samyak-Tamil.ttf`.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

---

## 8. How to run

```bash
. .venv/bin/activate

# 1) (dev only) make scanned-handwriting test inputs (PDF + PNG + SVG)
python make_test_scan.py

# 2) run the pipeline (uses config.yaml; default input = samples/test_scan.pdf)
python run.py

# point it at YOUR scan (PDF / SVG / image), any mode:
python run.py --input path/to/your_scan.pdf
python run.py --input path/to/your.svg
python run.py --input path/to/scan.png --letter-height 8 --spacing 0.6
```

Outputs: `output/olai.gcode` and `output/preview.png`.
**Always eyeball the preview before running on paper.**

To switch styles, edit `stroke_mode` in `config.yaml`
(`centerline` for handwriting, `outline` for typed/solid glyphs).

---

## 9. Current status (as of this snapshot)

**WORKING end-to-end for scanned input (PDF, SVG, image).** Latest tests:

- `samples/test_scan.pdf` (synthetic noisy/skewed scan), **centerline**:
  117 strokes → **1,052 dots**, content **95 × 53 mm**, serpentine cut travel
  5419 → 1626 mm. Preview shows natural single-stroke dotted Tamil.
- `samples/test_strokes.svg`, centerline: SVG loader path verified.
- `samples/test_scan.png`, **outline** mode: 1,894 dots (doubled-edge look) —
  confirms mode toggle works.
- G-code verified: correct preamble, per-dot punch cycle, Z pen-lift.

---

## 10. Known limitations / open items / next steps

- **Validate on a REAL scan.** All tests use a synthetic scan. Need the user's
  actual scanned Tamil handwriting (PDF/SVG) to tune threshold/denoise. If the
  scan has uneven lighting, set `preprocess.threshold: adaptive`.
- **Runtime estimate is pessimistic.** `gcode.estimate_runtime_s` assumes a Z
  *stepper* feed; the real servo lifts faster. TODO: servo-timing model
  (~0.2–0.3 s per up/down) once measured.
- **Resolution trade-off.** At 6 mm letters + 0.8 mm dots, very fine features
  are near the limit. Increase letter height (~8 mm) or reduce spacing — the
  preview shows the trade-off.
- **Skeleton artefacts.** Skeletonization can create tiny spurs at junctions;
  `min_stroke_rel` prunes short ones. Increase it if you see stray nubs.
- **Servo command mode** (`pen.mode: servo`) implemented but untested on HW.
- Path optimization is a serpentine heuristic (not full TSP); good enough.
- Multi-page PDFs: one page per run via `page_index`.

---

## 11. Quick glossary

- **GRBL / GRBL-Plotter:** firmware / desktop software that streams G-code to
  the plotter and (here) maps Z moves to a pen-lift servo.
- **Olai chuvadi:** traditional Tamil palm-leaf manuscript; text was engraved
  with a stylus — the aesthetic this project recreates by punching dots.
- **Centerline / skeleton:** the 1-px medial line down the middle of a stroke;
  dotting it reproduces the pen path (natural handwriting look). **Default.**
- **Outline / contour dots:** dots along the *edges* of a shape (typed glyphs).

---

## 12. Change log

- **v0.1 (2026-07-02):** Initial system. Input = typed Geethapria PDF; dot
  style = outline; pipeline render → contours → sample → map → gcode.
- **v0.2 (2026-07-04):** Input changed to **scanned handwriting** (PDF/SVG/
  image). Added `input_loader` (multi-format + downscale), `preprocess` (scan
  cleanup), `skeleton` (centerline tracing). Default `stroke_mode: centerline`.
  Reordered pipeline so mapping precedes resampling → **dot spacing is now
  exact on the output paper**. Serpentine ordering only applied when it helps.
