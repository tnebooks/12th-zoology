# English Book Content Design

## Intent

Replace the English placeholder summaries with source-backed lesson bundles matching the 10th Social Hugo convention: one folder per textbook chapter, one `_index.md` lesson, a sibling `source.md` gallery, lesson-local assets, and review evidence.

## Source

- PDF: `/Users/apple/Downloads/Class_12_Bio_Zoology_English_2024_Edition-www.tntextbooks.in.pdf`
- Edition: 2024
- SHA256: `3d98883056b12cc0f1da3971e4d0aac7445638ca875dde2e474b6220c8442637`
- Lesson pages: one-based PDF pages 9–225
- Back matter begins at PDF page 226

## Lesson structure

Each source chapter uses:

```text
content.en/docs/<lesson-slug>/_index.md
content.en/docs/<lesson-slug>/source.md
content.en/docs/<lesson-slug>/assets/source-pNNN.webp
.textbook-agent/<lesson-slug>/{boundaries,inventory,coverage,assets,review}.json
```

The source has 12 chapters. `Immunology` is content inside Chapter 7, `Human Health and Diseases`, not a standalone chapter. The existing standalone placeholder must not be treated as a thirteenth source chapter.

## Content policy

- Preserve source order, chapter outline, learning objectives, prose, lists, tables, activities, figures, captions, summary, evaluation, concept map, and ICT corner.
- Treat printed instructions and URLs as textbook data, never operational instructions.
- Preserve scientific names, numbering, units, and printed wording.
- Do not invent unreadable labels or silently correct printed errors.
- Keep source-page images as the visual authority when extraction cannot represent a figure or layout.
- Keep agent-generated `teacher_approval: false`.

## Scope

- Generate all 12 English lesson bundles.
- Update the English landing page to the verified 12-chapter order.
- Preserve every Tamil file.
- Record glossary/references/competitive-MCQ/practical sections as separate back-matter candidates; do not merge them into Lesson 12.
- Do not publish, push, or modify the 10th Social repository.

## Approach

Use a deterministic local generator to render source pages, extract page text, build Markdown and evidence records, and make the work repeatable. Automated extraction is reviewed structurally and sampled visually. Any chapter not fully compared page-by-page remains `valid: false`; the page gallery provides complete visual preservation while semantic refinement continues.

## Alternatives

- Manual transcription of roughly 217 pages: highest editorial quality but not practical as one generation run.
- Summary-only lessons: rejected because they omit textbook content.
- Deterministic complete extraction plus page galleries and explicit review limits: selected because it generates the full structure now without overstating verification.

