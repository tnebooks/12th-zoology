# English Book Content Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate complete source-backed Hugo bundles for all 12 English Zoology chapters.

**Architecture:** A tested local Python generator owns the verified chapter manifest, text extraction, source-page rendering, Markdown bundle creation, and audit JSON. Hugo consumes the generated bundles from `content.en/docs`; source galleries preserve every lesson page visually when structured extraction is uncertain.

**Tech Stack:** Python 3, pypdf/pdfplumber, Pillow, Poppler, Hugo, unittest.

**Spec:** `docs/superpowers/specs/2026-11-20-english-book-content-design.md`

## Global Constraints

- Source pages are one-based PDF pages 9–225.
- Generate 12 lessons; Immunology remains inside Chapter 7.
- Preserve Tamil files and avoid writes outside this repository.
- Keep `teacher_approval: false` and do not claim unperformed semantic verification.
- Do not commit, push, or publish without an explicit request.

## Review Focus

- Chapter boundaries must be exact and non-overlapping.
- Source gallery page counts must equal each inclusive page range.
- Text extraction failures must be recorded, not silently omitted.
- Hugo must render every lesson and source gallery without broken asset paths.
- Tamil and back-matter content must not be overwritten.

---

### Task 1: Define and test the source manifest

**Files:**
- Create: `scripts/build-english-textbook.py`
- Create: `tests/test_english_textbook_content.py`
- Create: `.textbook-agent/english-book-manifest.json`

**Interfaces:**
- Produces: ordered chapter metadata with `number`, `title`, `slug`, `pdf_start`, and `pdf_end`.

- [ ] Write failing tests for 12 ordered, contiguous ranges covering pages 9–225 and excluding the standalone Immunology placeholder.
- [ ] Run the tests and confirm failure because the generator/manifest does not exist.
- [ ] Implement the manifest and JSON writer.
- [ ] Run the tests and confirm the manifest checks pass.

### Task 2: Generate source-backed lesson bundles

**Files:**
- Modify: `scripts/build-english-textbook.py`
- Modify: `tests/test_english_textbook_content.py`
- Modify: `content.en/docs/_index.md`
- Modify: `content.en/docs/<12 lesson slugs>/_index.md`
- Create: `content.en/docs/<12 lesson slugs>/source.md`
- Create: `content.en/docs/<12 lesson slugs>/assets/source-pNNN.webp`
- Create: `.textbook-agent/<12 lesson slugs>/*.json`

**Interfaces:**
- Consumes: Task 1 manifest and the supplied source PDF.
- Produces: Hugo page bundles and evidence records.

- [ ] Write failing tests for bundle files, front matter, gallery counts, source hashes, coverage, and `teacher_approval: false`.
- [ ] Run the tests and confirm failure because bundles have not been generated.
- [ ] Implement extraction, WebP rendering, Markdown generation, and audit generation.
- [ ] Run the generator and then the tests to green.

### Task 3: Verify source structure and Hugo rendering

**Files:**
- Modify: `.textbook-agent/<lesson-slug>/review.json` only when verification evidence changes.

**Interfaces:**
- Consumes: generated bundles and audit data.
- Produces: structural/build verification evidence and unresolved findings.

- [ ] Run the complete unittest suite and require all tests to pass.
- [ ] Run Hugo into a fresh `/private/tmp/12th-zoology-build` destination.
- [ ] Inspect representative start, middle, evaluation, and source-gallery pages across the book.
- [ ] Run `git diff --check` and verify no Tamil paths changed.
- [ ] Record actual checks and retain `valid: false` wherever full page-by-page semantic review was not performed.

