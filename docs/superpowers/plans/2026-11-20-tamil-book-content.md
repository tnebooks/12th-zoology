# Tamil Book Content Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate searchable, source-backed Hugo bundles for all 12 Tamil Zoology chapters.

**Architecture:** A dedicated Python generator owns the verified Tamil chapter manifest, Tesseract OCR, page rendering, Hugo Markdown bundles, and conservative audit records. Exact source-page galleries remain the visual authority when OCR is uncertain.

**Tech Stack:** Python 3, Tesseract `tam+eng`, Pillow, Poppler, Hugo, unittest.

**Spec:** `docs/superpowers/specs/2026-11-20-tamil-book-content-design.md`

## Global Constraints

- Source lesson pages are one-based PDF pages 9–269.
- Generate 12 source chapters; Immunology remains within Chapter 7.
- Preserve the existing English work and do not modify `content.en`.
- Keep `valid: false` and `teacher_approval: false` pending semantic review.
- Do not commit, push, or publish.

## Review Focus

- Tamil OCR must contain Tamil Unicode rather than legacy-font garbage or replacement characters.
- Chapter boundaries must follow the Tamil PDF bookmarks, not the English page ranges.
- Source gallery page counts must equal every inclusive Tamil chapter range.
- OCR failures must be recorded while the corresponding source page remains visible.
- Hugo must render every Tamil lesson and source gallery without broken page assets.

---

### Task 1: Define the Tamil source manifest and OCR contract

**Files:**
- Create: `tests/test_tamil_textbook_content.py`
- Create: `scripts/build-tamil-textbook.py`
- Create: `.textbook-agent/tamil-book-manifest.json`

**Interfaces:**
- Consumes: supplied Tamil PDF and its SHA256.
- Produces: ordered `CHAPTERS`, `manifest()`, and `ocr_image()` contracts for Task 2.

- [ ] Write failing tests for the 12 ordered bookmark ranges, exact pages 9–269, and exclusion of standalone Immunology.
- [ ] Run the Tamil tests and confirm the expected failure.
- [ ] Implement the manifest, source hash guard, and Tesseract dependency/language validation.
- [ ] Run the manifest tests to green.

### Task 2: Generate Tamil OCR lesson bundles and evidence

**Files:**
- Modify: `scripts/build-tamil-textbook.py`
- Modify: `tests/test_tamil_textbook_content.py`
- Modify: `content.ta/docs/_index.md`
- Modify: `content.ta/docs/<12 slugs>/_index.md`
- Create: `content.ta/docs/<12 slugs>/source.md`
- Create: `content.ta/docs/<12 slugs>/assets/source-pNNN.webp`
- Create: `.textbook-agent/ta-<12 slugs>/*.json`

**Interfaces:**
- Consumes: Task 1 manifest, `ocr_image(image_path)`, and the Tamil PDF.
- Produces: searchable page-anchored Markdown, 261 source images, and audit records.

- [ ] Add failing bundle tests for Tamil script, source markers, exact gallery assets, audits, and conservative review fields.
- [ ] Run the tests and confirm failure because bundles are not generated.
- [ ] Implement page rendering, parallel `tam+eng` OCR, Markdown generation, WebP generation, and audits.
- [ ] Run the generator and Tamil tests to green.

### Task 3: Verify rendering and isolation

**Files:**
- Modify: `.textbook-agent/ta-<lesson>/review.json` only when verification evidence changes.

**Interfaces:**
- Consumes: generated Tamil bundles and audits.
- Produces: final structural/build evidence with unresolved semantic findings retained.

- [ ] Run both English and Tamil unittest suites.
- [ ] Run Hugo into a fresh `/private/tmp/12th-zoology-tamil-build` destination.
- [ ] Inspect representative OCR and source-gallery pages from Chapters 1, 7, and 12.
- [ ] Run `git diff --check` and confirm this task introduced no `content.en` changes beyond the pre-existing English working tree.
- [ ] Record passing structural checks while retaining `valid: false` and `teacher_approval: false`.

