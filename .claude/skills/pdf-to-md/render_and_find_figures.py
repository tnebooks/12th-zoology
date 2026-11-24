#!/usr/bin/env python3
"""
Language-agnostic PDF prep step: render pages at 300 DPI and list
candidate figure bounding boxes (filled background rectangles).

Works for ANY language — it never reads text content, only page geometry,
so it is safe for Tamil/other complex scripts where pdfplumber's text
extraction is unreliable (see SKILL.md "Tamil / non-Latin scripts").

Usage:
    python3 render_and_find_figures.py <pdf_path> <output_dir>

Output:
    <output_dir>/page-1.png, page-2.png, ...   (300 DPI page renders)
    Prints each page's candidate figure rects (x0, x1, top, bottom in PDF
    points) to stdout — read these alongside the rendered pages to decide
    which rect is which Figure N.N, then crop with crop_figure.py.
"""

import sys
from pathlib import Path

if len(sys.argv) < 3:
    print("Usage: render_and_find_figures.py <pdf_path> <output_dir>")
    sys.exit(1)

PDF = sys.argv[1]
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

import pdfplumber
from pdf2image import convert_from_path

DPI = 300

print(f"Rendering pages at {DPI} DPI...")
pages = convert_from_path(PDF, dpi=DPI)
for i, img in enumerate(pages, 1):
    img.save(str(OUT / f"page-{i}.png"), "PNG")
print(f"  {len(pages)} pages -> {OUT}/page-N.png")

print("\nCandidate figure rects per page (filled boxes > 100x40 pt):")
with pdfplumber.open(PDF) as pdf:
    for pn, page in enumerate(pdf.pages, 1):
        rects = [r for r in page.rects
                 if (r['x1'] - r['x0']) > 100 and (r['bottom'] - r['top']) > 40]
        if not rects:
            continue
        print(f"  page {pn}:")
        for r in sorted(rects, key=lambda r: (r['top'], r['x0'])):
            print(f"    x0={r['x0']:.0f} x1={r['x1']:.0f} "
                  f"top={r['top']:.0f} bot={r['bottom']:.0f}")

print(f"\nPDF page size: {page.width:.1f} x {page.height:.1f} pt "
      f"(same scale for all pages unless noted)")
print("\nNext: read each page-N.png, match rects to Figure N.N captions by "
      "eye, then run crop_figure.py per figure.")
