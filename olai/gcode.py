"""Stage 6 — emit GRBL G-code punch cycles for a list of dots."""
from __future__ import annotations

from typing import List

import numpy as np

from .config import Config


def _fmt(v: float) -> str:
    """Compact fixed-point formatting (3 decimals, no trailing zeros)."""
    return f"{v:.3f}".rstrip("0").rstrip(".")


def build_gcode(dots_mm: np.ndarray, cfg: Config, meta: dict | None = None) -> str:
    lines: List[str] = []
    meta = meta or {}

    lines.append("; ==============================================")
    lines.append("; Olai Chuvadi Plotter - dotted Tamil outline")
    lines.append(f"; dots={len(dots_mm)}  spacing={cfg.spacing_mm}mm  "
                 f"letter_h={cfg.target_letter_height_mm}mm")
    lines.append(f"; work_area={cfg.work_w}x{cfg.work_h}mm  pen_mode={cfg.pen_mode}")
    for k, v in meta.items():
        lines.append(f"; {k}={v}")
    lines.append("; ==============================================")

    # --- preamble ---
    lines.append("G21")            # millimetres
    lines.append("G90")            # absolute positioning
    lines.append("G94")            # feed = units/min
    lines.append(_pen_up(cfg))     # make sure the needle starts up
    lines.append("G4 P0.2")        # brief settle

    down = _pen_down(cfg)
    up = _pen_up(cfg)
    dwell = f"G4 P{cfg.dwell_ms / 1000.0:.3f}" if cfg.dwell_ms > 0 else None

    for x, y in dots_mm:
        # 1) reposition in XY while lifted
        if cfg.travel_g0:
            lines.append(f"G0 X{_fmt(x)} Y{_fmt(y)}")
        else:
            lines.append(f"G1 X{_fmt(x)} Y{_fmt(y)} F{_fmt(cfg.travel_xy)}")
        # 2) punch down
        lines.append(down)
        if dwell:
            lines.append(dwell)
        # 3) lift back up
        lines.append(up)

    # --- postamble ---
    lines.append(_pen_up(cfg))
    lines.append("G0 X0 Y0")
    lines.append("M2")             # program end
    return "\n".join(lines) + "\n"


def _pen_down(cfg: Config) -> str:
    if cfg.pen_mode == "servo":
        return cfg.servo_down_cmd
    return f"G1 Z{_fmt(cfg.z_down_mm)} F{_fmt(cfg.plunge_z)}"


def _pen_up(cfg: Config) -> str:
    if cfg.pen_mode == "servo":
        return cfg.servo_up_cmd
    return f"G1 Z{_fmt(cfg.z_up_mm)} F{_fmt(cfg.plunge_z)}"


def estimate_runtime_s(dots_mm: np.ndarray, cfg: Config) -> float:
    """Rough job-time estimate (seconds): XY travel + per-dot punch time."""
    if len(dots_mm) == 0:
        return 0.0
    d = np.diff(dots_mm, axis=0)
    travel_mm = float(np.hypot(d[:, 0], d[:, 1]).sum())
    xy_speed = cfg.travel_xy if not cfg.travel_g0 else max(cfg.travel_xy, 3000.0)
    t_travel = travel_mm / (xy_speed / 60.0)
    # each punch = down + up over (z_up - z_down)*2 distance at plunge feed
    z_dist = 2.0 * (cfg.z_up_mm - cfg.z_down_mm)
    t_punch = len(dots_mm) * (z_dist / (cfg.plunge_z / 60.0) + cfg.dwell_ms / 1000.0)
    return t_travel + t_punch
