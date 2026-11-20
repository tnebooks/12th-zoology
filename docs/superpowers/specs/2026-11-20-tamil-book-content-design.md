# Tamil Book Content Design

## Intent

Create searchable Tamil lesson bundles for the supplied Class 12 Bio-Zoology Tamil-medium textbook while preserving every original lesson page as visual evidence. The generated structure must mirror the English Hugo bundles and must not modify English lesson files.

## Source and scope

- Source PDF: `/Users/apple/Downloads/12th_Bio-Zoology_TM_Text_www.tntextbooks.in.pdf`
- Source SHA256: `cfeb3e7327e532eb45c41b17e29354523cd441e36191812c3b697572771caa06`
- The PDF has 312 pages.
- Bookmarks establish 12 chapter starts at PDF pages 9, 20, 43, 60, 76, 112, 134, 170, 182, 200, 224, and 250.
- Lesson content ends at PDF page 269; glossary and later back matter begin at page 270 and are excluded.
- Immunology is part of Chapter 7, not a standalone source chapter.

## Selected approach

Render each lesson page and run local Tesseract OCR with Tamil and English language data. Store cleaned OCR text in each lesson `_index.md`; store a complete `source.md` gallery and one WebP per source page so students and reviewers retain access to the exact diagrams, tables, questions, captions, and layouts.

The embedded PDF text layer is not used as lesson text because its legacy Tamil font encoding extracts as corrupted Unicode. A page-image-only implementation was rejected because it would not provide searchable or accessible Tamil text. Embedded-text conversion was rejected because it visibly corrupts Tamil characters.

## Outputs

- `content.ta/docs/_index.md`: Tamil lesson landing page.
- `content.ta/docs/<existing-slug>/_index.md`: OCR-derived Tamil lesson text with source-page anchors.
- `content.ta/docs/<existing-slug>/source.md`: exact source-page gallery.
- `content.ta/docs/<existing-slug>/assets/source-pNNN.webp`: source page images.
- `.textbook-agent/tamil-book-manifest.json`: Tamil source manifest.
- `.textbook-agent/ta-<slug>/*.json`: Tamil-specific boundary, inventory, coverage, asset, and review records.
- `scripts/build-tamil-textbook.py`: deterministic generator.
- `tests/test_tamil_textbook_content.py`: source-range and bundle tests.

## Fidelity and acceptance

- Preserve source order and one-based PDF page references.
- Keep OCR output visibly labeled as automated transcription.
- Treat each page as a provisional inventory item; do not claim item-level inventory completeness.
- Keep `valid: false` and `teacher_approval: false` until page-by-page semantic review is performed.
- Record unusually short OCR and replacement characters as blocking findings.
- Preserve the full source page even when OCR is uncertain.
- Verify all 261 source page images, all 12 galleries, Tamil script presence, Hugo rendering, and no English changes caused by this task.

## Constraints

- Preserve the existing uncommitted English work.
- Do not delete the pre-existing standalone Immunology placeholder; exclude it from the generated Tamil landing page.
- Do not commit, push, publish, or claim teacher approval.
- The local build may use the already-installed design-system theme referenced by the sibling 10th Social repository.

