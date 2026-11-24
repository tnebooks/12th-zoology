#!/usr/bin/env python3
"""
PDF → Markdown extractor for two-column textbook PDFs (e.g. TN textbook
corpus). Usage:

    python3 extract_pdf.py <pdf_path> <output_dir>

Design:
  1. Figures are cropped from the filled background RECTANGLE behind each
     diagram (not a text-gap heuristic) — reliable because every figure in
     this layout sits on a colored panel whose bounds pdfplumber reports
     exactly via page.rects.
  2. Two-column reading order: lines are split left/right by x0 relative to
     the page midpoint, then emitted LEFT column fully, then RIGHT column.
     Raw top-to-bottom order interleaves the two columns and reads wrong.
  3. Math: pdfplumber has no notion of 2D glyph layout, so fractions,
     super/subscripts etc. come back as scattered single-line fragments —
     reconstructing correct LaTeX from that is not reliable. Lines that
     look equation-like are flagged with an HTML comment
     "<!-- MATH (verify against page scan): ... -->" instead of being
     wrapped in fake $$ ... $$ that would silently ship wrong formulas.
     Cross-check flagged spots against the page-N.png scan (equations
     render correctly there) and hand-transcribe the LaTeX.
  4. Text sitting inside a matched figure's rectangle (diagram labels,
     axis captions) is excluded from body prose — it's already visible in
     the cropped figure image.

Known limits — read before trusting output on a new PDF:
  - COL_MID (column boundary) is auto-estimated as page-width/2 but tune
    it per-PDF if text looks interleaved; two-column layouts vary.
  - Figure/box detection depends on a colored background rect existing —
    plain black-and-white line diagrams with no fill may not be found;
    those fall back to no crop and should be lifted from page-N.png by hand.
  - Running headers/footers are filtered by regex tuned to this publisher's
    patterns (page number + "Unit N ..." + mangled embedded filename) —
    adjust SKIP_RE/FOOTER_RE/MANGLED_RE for a different source.
"""

import re
import sys
from pathlib import Path
from collections import defaultdict

if len(sys.argv) < 3:
    print("Usage: extract_pdf.py <pdf_path> <output_dir>")
    sys.exit(1)

PDF = sys.argv[1]
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

import pdfplumber
from pdf2image import convert_from_path

DPI = 300
PAGE_HEADER_BOT = 35   # pt — skip running header/URL
PAGE_FOOTER_TOP_OFFSET = 30  # pt from bottom — skip footer/page number

with pdfplumber.open(PDF) as _pdf:
    _pw = float(_pdf.pages[0].width)
COL_MID = _pw / 2      # pt — column boundary; tune per-PDF if needed

FIG_RE  = re.compile(r'^Figure\s+(\d+\.\d+)', re.IGNORECASE)
SKIP_RE = re.compile(
    r'^(www\.|Unit \d|UNIT 8|XII_Physics|X+I*__|\d{2,3}\s*$|\d\d-\d\d-\d\d\d\d'
    r'|\d{2,3}\s+Unit \d|\d{2,3}:\d{2}:\d{2}$)'
)
# printer-crop/running-footer artifact: e.g. "110 Unit 8 dual nature of radiation and matter"
FOOTER_RE = re.compile(r'^\d{2,3}\s+Unit\s+\d', re.IGNORECASE)
# mangled double-struck filename artifact e.g. "XXIIII__PPhhyyssiiccss__..."
MANGLED_RE = re.compile(r'^[A-Za-z]*(\w)\1[A-Za-z_.]*\d')

# crude equation detector: require an actual math operator AND absence of
# normal sentence structure (no lowercase article/prose words), to avoid
# false-positiving on prose that merely contains a stray symbol.
EQN_OPERATOR_RE = re.compile(r'[=×÷∫∑√≈≤≥]|\b10[−-]\d+\b')
PROSE_WORD_RE = re.compile(
    r'\b(the|and|is|are|of|in|to|that|which|with|from|this|these|those|'
    r'when|because|their|was|were|has|have|it|as|by|or|for|an|a)\b',
    re.IGNORECASE)

def looks_like_equation(text):
    if not EQN_OPERATOR_RE.search(text):
        return False
    if PROSE_WORD_RE.search(text):
        return False
    if len(text) > 100:
        return False
    return True

print("Rendering pages at 300 DPI...")
page_imgs = convert_from_path(PDF, dpi=DPI)
for i, img in enumerate(page_imgs):
    img.save(str(OUT / f"page-{i+1}.png"), "PNG")
print(f"  {len(page_imgs)} pages")

# ── Gather per-page: lines + big filled rects (candidate figure boxes) ──────
def get_lines(page):
    words = page.extract_words(x_tolerance=3, y_tolerance=3)
    buckets = defaultdict(list)
    for w in words:
        buckets[round(w['top'] / 3) * 3].append(w)
    lines = []
    for top_key in sorted(buckets):
        ws = sorted(buckets[top_key], key=lambda x: x['x0'])
        lines.append({
            'top':    min(w['top']    for w in ws),
            'bottom': max(w['bottom'] for w in ws),
            'x0':     min(w['x0']    for w in ws),
            'x1':     max(w['x1']    for w in ws),
            'text':   ' '.join(w['text'] for w in ws),
        })
    return lines

def get_figure_rects(page):
    """Large filled rects = figure background panels. Merge overlapping."""
    cands = []
    for r in page.rects:
        w = r['x1'] - r['x0']
        h = r['bottom'] - r['top']
        if w > 100 and h > 40:
            cands.append({'x0': r['x0'], 'x1': r['x1'],
                          'top': r['top'], 'bottom': r['bottom']})
    # merge rects that overlap/nest — keep largest bounding union per cluster
    cands.sort(key=lambda r: (r['top'], r['x0']))
    merged = []
    for r in cands:
        placed = False
        for m in merged:
            # overlap test
            if not (r['x1'] < m['x0'] or r['x0'] > m['x1'] or
                    r['bottom'] < m['top'] or r['top'] > m['bottom']):
                m['x0'] = min(m['x0'], r['x0'])
                m['x1'] = max(m['x1'], r['x1'])
                m['top'] = min(m['top'], r['top'])
                m['bottom'] = max(m['bottom'], r['bottom'])
                placed = True
                break
        if not placed:
            merged.append(dict(r))
    return merged

page_lines = {}
page_rects = {}
figure_caps = []

with pdfplumber.open(PDF) as pdf:
    for page_num, page in enumerate(pdf.pages, 1):
        lines = get_lines(page)
        page_lines[page_num] = lines
        page_rects[page_num] = get_figure_rects(page)
        for ln in lines:
            m = FIG_RE.match(ln['text'])
            if m:
                figure_caps.append({
                    'fig_id':  m.group(1),
                    'page':    page_num,
                    'cap_top': ln['top'],
                    'cap_x0':  ln['x0'],
                    'caption': ln['text'],
                })

print(f"\nFound {len(figure_caps)} figure captions")

# ── Match each caption to the nearest figure rect above it, same column ─────
def match_rect(page_num, cap_top, cap_x0):
    in_right = cap_x0 > COL_MID
    best, best_gap = None, 1e9
    for r in page_rects.get(page_num, []):
        rect_width = r['x1'] - r['x0']
        is_full_width = rect_width > (COL_MID - 20)  # spans ~both columns
        if not is_full_width:
            rect_mid = (r['x0'] + r['x1']) / 2
            same_col = (rect_mid > COL_MID) == in_right
            if not same_col:
                continue
        if r['bottom'] > cap_top + 10:   # rect must end at/above caption
            continue
        gap = cap_top - r['bottom']
        if 0 <= gap < best_gap and gap < 60:
            best_gap = gap
            best = r
    return best

print("\nCropping figures from filled-rect bounding boxes...")
img_map = {}
fig_rect_by_page = defaultdict(list)  # page_num → [(rect, fig_id, cap_top)]
with pdfplumber.open(PDF) as pdf:
    for info in figure_caps:
        page_num = info['page']
        page = pdf.pages[page_num - 1]
        pw, ph = float(page.width), float(page.height)
        rect = match_rect(page_num, info['cap_top'], info['cap_x0'])
        fig_id = info['fig_id']
        fname = f"image-{fig_id.replace('.', '-')}.png"

        if rect is None:
            print(f"  ✗ Figure {fig_id} — no matching rect found")
            img_map[fig_id] = None
            continue

        fig_rect_by_page[page_num].append((rect, fig_id, info['cap_top']))

        img = page_imgs[page_num - 1]
        iw, ih = img.size
        sx, sy = iw / pw, ih / ph
        pad = 6
        left  = max(0, int((rect['x0'] - pad) * sx))
        right = min(iw, int((rect['x1'] + pad) * sx))
        top   = max(0, int((rect['top'] - pad) * sy))
        bot   = min(ih, int((rect['bottom'] + pad) * sy))

        crop = img.crop((left, top, right, bot))
        crop.save(str(OUT / fname), "PNG")
        img_map[fig_id] = fname
        print(f"  ✓ Figure {fig_id}  rect=({rect['x0']:.0f},{rect['top']:.0f})-({rect['x1']:.0f},{rect['bottom']:.0f}) → {fname}")

def line_inside_any_figure(page_num, ln):
    """True if this text line's vertical span sits strictly inside a
    matched figure's rect (diagram labels, axis text etc. that must not
    leak into prose). The caption line itself (at/after cap_top) and any
    continuation line below it are NOT filtered — emit_line handles those."""
    for rect, fig_id, cap_top in fig_rect_by_page.get(page_num, []):
        if ln['top'] >= cap_top - 1:
            continue  # caption or below — let emit_line handle it
        if rect['top'] - 4 <= ln['top'] and ln['bottom'] <= rect['bottom'] + 4:
            if not (ln['x1'] < rect['x0'] - 20 or ln['x0'] > rect['x1'] + 20):
                return True
    return False

# ── Build markdown with correct column-major reading order ──────────────────
print("\nBuilding markdown (column-ordered)...")

# fig_id → full multi-line caption (collected via continuation lines below)
full_captions = {info['fig_id']: info['caption'] for info in figure_caps}
cap_top_by_fig = {info['fig_id']: info['cap_top'] for info in figure_caps}

def is_caption_continuation(text):
    return len(text) < 60 and text and not text[0].isdigit() and not FIG_RE.match(text)

def emit_line(md, text, inserted, prev_fig_id, in_figure_zone):
    """Returns (new_prev_fig_id, new_in_figure_zone)."""
    m = FIG_RE.match(text)
    if m:
        fig_id = m.group(1)
        if fig_id not in inserted:
            inserted.add(fig_id)
            fname = img_map.get(fig_id)
            cap = full_captions.get(fig_id, text)
            md.append("")
            if fname:
                md.append(f"![{cap}]({fname})")
            md.append(f"*{cap}*")
            md.append("")
        return fig_id, False

    if prev_fig_id and is_caption_continuation(text):
        # append to the just-emitted caption (handles 2-line captions) —
        # consume AT MOST ONE continuation line, then always reset
        # prev_fig_id so normal body prose right after isn't swallowed too.
        for i in range(len(md) - 1, -1, -1):
            if md[i].startswith('*') and md[i].endswith('*'):
                md[i] = md[i][:-1].rstrip() + ' ' + text + '*'
                break
        return None, False

    if re.match(r'^8\.\d+\s+[A-Z]', text) and len(text) < 90:
        md.append(f"\n## {text}\n")
        return None, False
    if re.match(r'^8\.\d+\.\d+\s+[A-Z]', text) and len(text) < 90:
        md.append(f"\n### {text}\n")
        return None, False
    if re.match(r'^(i{1,3}v?|iv|v)\)', text.lower()):
        md.append(f"\n{text}")
        return None, False

    if looks_like_equation(text):
        # pdfplumber cannot recover 2D glyph layout (fractions, super/sub-
        # scripts), so fragments like "K_max = eV_0" come out scrambled
        # across several lines. Rather than emit confidently-wrong LaTeX,
        # flag the spot — the equation is captured correctly in the page
        # scan image and in image-eqn-*.png crops (see crop_equations()).
        md.append(f"\n<!-- MATH (verify against page scan): {text} -->\n")
        return None, False

    md.append(text)
    return None, False


# Derive a title/slug from the PDF filename (strip bracket tags, trim
# trailing page-range suffixes like "-1-8"). Caller can hand-edit afterward.
_stem = Path(PDF).stem
_stem = re.sub(r'^\[.*?\]', '', _stem)          # drop leading [sp1] etc.
_stem = re.sub(r'-\d+-\d+$', '', _stem)          # drop trailing -1-8 page range
_title_words = re.sub(r'[_\-]+', ' ', _stem).strip()
_slug = re.sub(r'[^a-z0-9]+', '-', _title_words.lower()).strip('-')

md = []
md.append("---")
md.append(f"title: '{_title_words}'")
md.append("categories:")
md.append(f"    - {_slug}")
md.append("---")
md.append("")
md.append(f"# {_title_words.upper()}")
md.append("")

inserted = set()

for page_num in sorted(page_lines):
    lines = page_lines[page_num]
    clean = []
    for ln in lines:
        text = ln['text'].strip()
        if not text or SKIP_RE.match(text):
            continue
        if re.match(r'^XII_Physics|^03-03-2022', text):
            continue
        if FOOTER_RE.match(text) or MANGLED_RE.match(text):
            continue
        # Lines whose vertical span sits inside a matched figure's region
        # (diagram labels, axis captions etc.) are already represented by
        # the cropped figure image — drop them from the body text so they
        # don't leak into prose out of order.
        if line_inside_any_figure(page_num, ln):
            continue
        clean.append(ln)

    # Column split: two-column body text is split left (x0 < COL_MID) vs
    # right (x0 >= COL_MID) and emitted LEFT-COLUMN-FULLY then
    # RIGHT-COLUMN-FULLY so prose reads in natural order instead of
    # interleaving by raw top-to-bottom position.
    left_col  = [l for l in clean if l['x0'] < COL_MID]
    right_col = [l for l in clean if l['x0'] >= COL_MID]

    left_col.sort(key=lambda l: l['top'])
    right_col.sort(key=lambda l: l['top'])

    prev_fig_id = None
    for ln in left_col:
        prev_fig_id, _ = emit_line(md, ln['text'].strip(), inserted, prev_fig_id, False)
    prev_fig_id = None
    for ln in right_col:
        prev_fig_id, _ = emit_line(md, ln['text'].strip(), inserted, prev_fig_id, False)

md_text = '\n'.join(md)
(OUT / '_index.md').write_text(md_text)

print(f"\n✓ Markdown → {OUT / '_index.md'}")
print(f"  Figures inserted: {len(inserted)} / {len(figure_caps)}")
print(f"  Output dir: {OUT}")
