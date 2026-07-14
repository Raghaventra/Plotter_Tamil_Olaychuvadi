"""Olai Chuvadi Plotter.

Convert typed Tamil (Geethapria) PDF pages into dotted-outline GRBL G-code
so a 2-axis pen plotter fitted with a needle can perforate paper in the
style of an old ஓலைச் சுவடி (palm-leaf manuscript).

Pipeline stages (see pipeline.run):
    render   -> rasterize a PDF page
    contours -> find glyph outlines (outer + holes)
    sampler  -> drop a dot every N mm along each outline
    mapping  -> pixels -> machine millimetres (scale, Y-flip, margins)
    optimize -> order dots to minimise air travel
    gcode    -> emit GRBL punch cycles
    preview  -> render a PNG of every dot for verification
"""

__version__ = "0.1.0"
