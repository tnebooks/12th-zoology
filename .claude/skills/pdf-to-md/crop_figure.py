#!/usr/bin/env python3
"""
Crop one figure from a rendered page using PDF-point rect coordinates
(from render_and_find_figures.py output). Language-agnostic.

Usage:
    python3 crop_figure.py <pdf_path> <page_num> <x0> <x1> <top> <bot> <out_png> [pad]

    page_num is 1-based (matches page-N.png from render_and_find_figures.py).
    Coordinates are PDF points, as printed by render_and_find_figures.py.
    pad (optional, default 6) adds a few points of margin on every side.

Masking an overlapping decoration (e.g. a QR code sitting inside the
figure's own rect — seen in the TN textbook corpus): after cropping, open
the PNG in an image tool and paint over the region, or re-run with a
narrower x0/x1/top/bot that excludes it, whichever preserves more of the
real figure. See SKILL.md for the exact pattern used on Figure 8.16.
"""

import sys
from pathlib import Path

if len(sys.argv) < 8:
    print("Usage: crop_figure.py <pdf_path> <page_num> <x0> <x1> <top> <bot> <out_png> [pad]")
    sys.exit(1)

PDF = sys.argv[1]
PAGE_NUM = int(sys.argv[2])
X0, X1, TOP, BOT = (float(x) for x in sys.argv[3:7])
OUT_PNG = sys.argv[7]
PAD = float(sys.argv[8]) if len(sys.argv) > 8 else 6.0

import pdfplumber
from pdf2image import convert_from_path

with pdfplumber.open(PDF) as pdf:
    page = pdf.pages[PAGE_NUM - 1]
    pw, ph = float(page.width), float(page.height)

pages = convert_from_path(PDF, dpi=300, first_page=PAGE_NUM, last_page=PAGE_NUM)
img = pages[0]
iw, ih = img.size
sx, sy = iw / pw, ih / ph

left  = max(0, int((X0 - PAD) * sx))
right = min(iw, int((X1 + PAD) * sx))
top   = max(0, int((TOP - PAD) * sy))
bot   = min(ih, int((BOT + PAD) * sy))

if right - left < 10 or bot - top < 10:
    print("ERROR: crop region too small — check coordinates")
    sys.exit(1)

crop = img.crop((left, top, right, bot))
crop.save(OUT_PNG, "PNG")
print(f"Saved {OUT_PNG} ({crop.size[0]}x{crop.size[1]}px)")
