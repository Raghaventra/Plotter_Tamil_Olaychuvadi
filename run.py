#!/usr/bin/env python3
"""CLI entry point for the Olai Chuvadi Plotter.

Usage:
    python run.py                       # use config.yaml in this folder
    python run.py --config other.yaml
    python run.py --input my.pdf --page 0 --letter-height 6 --spacing 0.8
"""
from __future__ import annotations

import argparse
import os
import sys

from olai.config import load_config
from olai.pipeline import run as run_pipeline


def main() -> int:
    ap = argparse.ArgumentParser(description="Tamil PDF -> dotted GRBL G-code")
    ap.add_argument("--config", default="config.yaml", help="path to config.yaml")
    ap.add_argument("--input", help="override input_pdf")
    ap.add_argument("--page", type=int, help="override page_index")
    ap.add_argument("--output", help="override output_gcode")
    ap.add_argument("--letter-height", type=float, help="override target letter height (mm)")
    ap.add_argument("--spacing", type=float, help="override dot spacing (mm)")
    ap.add_argument("--dpi", type=int, help="override render DPI")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args()

    cfg_path = os.path.abspath(args.config)
    if not os.path.exists(cfg_path):
        print(f"config not found: {cfg_path}", file=sys.stderr)
        return 2

    cfg = load_config(cfg_path)
    if args.input:
        cfg.input_pdf = args.input
    if args.page is not None:
        cfg.page_index = args.page
    if args.output:
        cfg.output_gcode = args.output
    if args.letter_height:
        cfg.target_letter_height_mm = args.letter_height
    if args.spacing:
        cfg.spacing_mm = args.spacing
    if args.dpi:
        cfg.render_dpi = args.dpi

    run_pipeline(cfg, verbose=not args.quiet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
