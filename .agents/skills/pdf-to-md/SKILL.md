# PDF to Markdown Skill

## Purpose
Extract text, figures (as cropped high-res images), and equations from a
two-column textbook-style PDF or HTML source into a markdown file + image
set, matching the `osl/12th-physics` project layout — for both English
(`content.en`) and Tamil (`content.ta`), which are parallel,
independently-sourced files of the same chapter and must both be
produced.

## Note for anyone new picking this up
This skill only gives the same output quality it was built and verified
on if you actually follow it — read the whole file before starting, not
just the Steps section. The two things most likely to go wrong for a
first-time user:
1. **Skipping the manual-transcription requirement.** There is a fully
   scripted extractor (`extract_pdf.py`) sitting right there and it is
   tempting to just run it and call the job done. Don't — it was tried,
   measured against hand-transcription, and rejected as rough-draft-only
   (see "The real workflow" below). The actual deliverable is produced by
   reading page images and writing markdown yourself; the scripts only
   render pages and crop figures.
2. **Not confirming the output path before building.** Step 2 (routing)
   exists because getting the chapter slug or project folder wrong is a
   silent failure you won't notice until the end. Always read the real
   chapter title from the source and state the full output path back to
   the user before producing anything.
3. **Running on a lower-effort model/setting.** This skill was built and
   verified on Claude Sonnet 5 at high reasoning effort. The hand-
   transcription step — merging line-wraps into prose, reading equations
   off a page image into correct LaTeX, matching figure crops to the
   right caption — is exactly the kind of close visual reading and
   judgment that degrades first when effort is turned down. If your
   session is running a different model or a lower effort level, say so
   to the user and expect to re-verify more carefully (diff against a
   reference chapter if one exists) rather than assuming the same
   quality bar holds.
If you want to sanity-check your own output against a known-good result,
`dual-nature-of-radiation-and-matter` in both `12th-physics/content.en`
and `content.ta` was the original verification case — see "Verified
against" at the bottom.

## Target repositories
Each subject project is its own git repo with its own GitHub remote —
confirm which one you're in (`git remote -v`) before writing, since the
local folder name and the remote repo name aren't always identical:

| Local folder | Remote(s) |
|---|---|
| `osl/10th-maths` | `origin` → `github.com/tnebooks/10th-maths` |
| `osl/10th-social` | `origin` → `github.com/tnebooks/10th-social` |
| `osl/12th-physics` | `origin` → a personal fork; `upstream` → `github.com/tnebooks/12th-physics` |

When a project has both `origin` and `upstream` (a fork setup, like
`12th-physics`), don't assume which one the user wants without asking —
pushing to the wrong one is a visible, hard-to-undo mistake.

### Write boundary: stage, never commit or push on your own
Finishing an extraction and copying it into a real project checkout is
two separate acts — producing the files and writing them to git history.
Only do the first unless told otherwise:
1. **Check the project's actual image path convention before writing
   any `![...](...)` reference** — don't assume. Some projects keep
   images alongside `_index.md` (flat: `image-8-1.png`), others nest
   them in an `assets/` subfolder (`assets/image-1-1.png`). Check with
   `ls content.<lang>/docs/<any-existing-chapter>/` on a sibling chapter
   in the same project, or check where the old version of *this* chapter
   (if one exists) put its images, before writing your markdown — not
   after. Getting this wrong produces a file that looks complete and
   passes every other check, but silently renders every image as a
   broken link; this happened once (all 58 image refs in a chapter
   missing an `assets/` prefix) and was only caught by a human looking
   at the rendered page, not by any automated check in this workflow.
   If you only discover the mismatch after already writing the file,
   fix every reference in one pass
   (`sed -E 's/\]\((image-[^)]+)\)/](assets\/\1)/g'` or the reverse) and
   re-verify every reference resolves to a real file before moving on.
2. Copy `_index.md` and the new figure images from your scratch output
   dir into `content.<lang>/docs/<chapter-slug>/` in the real repo
   checkout, using the path convention confirmed in step 1.
3. Check whether this is actually a *rewrite* of something already
   committed (`git show HEAD:<path>` vs your new file) — if so, the old
   version's figure assets may now be orphaned (referenced by nothing).
   Point this out to the user and ask before deleting anything; don't
   silently remove files from a git-tracked project.
4. `git add` the new/modified files only — not unrelated untracked
   clutter (editor folders like `.idea/`, OS files).
5. Stop there. Per this session's standing git rules: never `git commit`
   or `git push` without the user explicitly saying so. Leave the
   changes staged and tell the user what's staged and where, so they can
   review and commit themselves.

## Trigger
"parse this pdf", "convert pdf to markdown", "extract pdf content", "pdf to md".

## Input can be a PDF or an HTML source
Some chapters are supplied as HTML instead of PDF — most often for Tamil,
where HTML text is far more reliable than PDF text extraction (no page
images to render, and the glyph-reordering problem described below for
Tamil PDFs doesn't apply to HTML text at all). **When the user says
"Tamil" without naming a file type, ask whether they're providing a PDF
or an HTML source** — don't assume either way, since the pipeline differs
meaningfully (see "HTML source input" below) and picking wrong wastes a
full pass.

## Multiple PDFs or a long PDF? Use agents, not a serial loop
If the user hands over several chapter PDFs at once, or one PDF long
enough that reading it page-by-page yourself would be slow, **default to
dispatching parallel background agents** rather than working through
pages or files one at a time — see "Parallel / multi-agent execution"
below. This is the default for batches, not an optimization to reach for
only when asked.

## The real workflow (read this first)

This is **not** a fully-scripted pipeline. It was tried as one and the
output quality didn't hold up: merged paragraphs, correct LaTeX, and
clean headings only come out right when Claude reads each page image and
transcribes it. The script's job is narrower and purely mechanical:

1. **Script**: render every page at 300 DPI, and crop each figure from
   its background rectangle (language-independent — geometry only, never
   reads text).
2. **Claude**: read each rendered page image directly (the Read tool) and
   hand-write the markdown — merged paragraphs, real LaTeX for every
   equation, correct heading hierarchy, figure refs pointing at the
   cropped images.

Do not try to get the script to also produce the final prose/LaTeX. It
was attempted (`extract_pdf.py`'s column-ordering + equation-flagging
logic) and even after several correctness passes the output was a
regex-mangled approximation — acceptable for a first look, not for
shipping into the project. Use `extract_pdf.py` only as a quick sanity
check or when the user explicitly wants the fast/rough pass; use the
`render_and_find_figures.py` + `crop_figure.py` + manual-transcription
path as the default.

## Two languages, same chapter, parameterized per job

The project tracks parallel content trees:
- `content.en/docs/<chapter-slug>/_index.md` — English
- `content.ta/docs/<chapter-slug>/_index.md` — Tamil

### Chapter slug naming rule

`<chapter-slug>` is the chapter's title, lowercased, with spaces (and any
punctuation) collapsed to single hyphens — a standard kebab-case slug of
the full chapter title, not an abbreviation or a numbered folder. Verified
against every existing chapter folder across all three subject projects:

```
osl/12th-physics/content.en/docs/
  dual-nature-of-radiation-and-matter
  electromagnetic-induction-and-alternating-current
  magnetism-and-magnetic-effects-of-electric-current
  recent-developments-in-physics

osl/10th-maths/content.en/docs/
  relations-and-functions
  numbers-and-sequences
  statistics-and-probability

osl/10th-social/content.en/docs/
  outbreak-of-world-war-i-and-its-aftermath
  anti-colonial-movements-and-the-birth-of-nationalism
  social-and-religious-reform-movements-in-the-19th-century
  the-world-between-two-world-wars
```

Notes on edge cases, all confirmed from the examples above:
- Numerals stay as digits, not spelled out or roman-numeral-collapsed:
  "World War I" → `world-war-i` (the "I" becomes a lowercase letter "i",
  not dropped), "19th century" → `19th-century`.
- Apostrophes and other punctuation are simply dropped, not replaced with
  a hyphen (e.g. a possessive "X's Y" → `xs-y`, no double-hyphen).
- The slug is used identically for both languages and as both the
  directory name and the `categories:` frontmatter value — see an
  existing chapter's frontmatter for the exact shape:
  ```yaml
  title: '<Full Chapter Title>'
  categories:
      - <chapter-slug>
  weight: <unit number>
  ```
  That's the target shape — proper Title Case in `title:`, the kebab-case
  slug only in `categories:`. In practice the existing repos are
  inconsistent about this: some already-committed chapters use the
  lowercase slug as the `title:` value too (e.g. `10th-maths`'s `algebra`,
  `numbers-and-sequences`), while others use proper Title Case (`Geometry`,
  `Mensuration`, `Trigonometry`). When rewriting an existing chapter, this
  is a real discrepancy, not a free formatting choice — flag it to the
  user and ask which they want rather than silently picking one; don't
  assume matching the file's own prior value is automatically correct
  just because it's less of a diff.
- Derive the slug from the chapter's actual title as printed on the PDF's
  title page — not from the PDF filename, which is often just
  `Chapter N.pdf` or similarly uninformative and tells you nothing about
  the slug.

Each source PDF is **entirely one language, cover to cover** — never
mixed. A given PDF is either the English edition or the Tamil edition of
a chapter; there is no per-page or per-paragraph language switching to
handle. This means language is a property of the input file, decided
once at the start of a job, not something detected page-by-page.

These come from **separate source PDFs** (different filenames, different
page images) of the same textbook chapter — not a translation step. Each
language is its own independent extraction job against its own PDF:
1. Identify the PDF's language (ask the user if the filename/content
   doesn't make it obvious — e.g. `_TM` / "Tamil" in the filename vs
   `_EM` / "English").
2. Run the full workflow (render → find figure rects → crop → read
   pages → hand-transcribe) against that one PDF.
3. Write the result under the matching tree: English → `content.en/docs/<slug>/_index.md`,
   Tamil → `content.ta/docs/<slug>/_index.md`.

The two jobs don't need to happen together. If the user hands you only
an English PDF, do only the English job and stop — don't assume a Tamil
companion PDF exists or try to translate one. If they hand you only a
Tamil PDF, same thing in reverse. When the user wants both for a
chapter, they'll supply (or point you to) two separate source PDFs, one
per language, and you run the workflow twice, independently, once per
PDF — each job is self-contained and can be picked up or re-run on its
own without touching the other language's output.

### Why Tamil can't use the scripted text path

`pdfplumber`'s word/text extraction **garbles Tamil** — combining vowel
signs and conjuncts come out of glyph order (confirmed: "அட்டவணை" extracted
as "அ்டடவனண"). This is a known class of issue with complex/Indic scripts
in PDFs using certain font encodings. Do not attempt to fix this with
regex reordering — it is not reliably recoverable from pdfplumber's word
stream. **For Tamil, skip text extraction entirely.** Only use:
- `render_and_find_figures.py` to get page renders + figure rect geometry
  (rects are pure coordinates, unaffected by the text bug)
- Claude reading the rendered page images directly and transcribing Tamil
  prose and LaTeX by hand

English pdfplumber text extraction is usable (Latin script, no reordering
issue) but still only good enough for a rough first pass — see above.
Default to manual transcription for English too unless the user just
wants a quick draft.

## Steps

### 1. Gather inputs and identify language
Ask for the PDF path and output directory if not given. Determine the
PDF's language (whole-file, not per-page — see above) from the filename
or a quick look at page 1; ask the user if it's ambiguous. This decides
the output tree (`content.en` vs `content.ta`) and, for Tamil, rules out
the scripted text-extraction path entirely (see below). If the user
hands you multiple PDFs across languages, treat each as its own job —
don't block one on the other.

### 2. Route to the output folder and confirm before building anything
This applies whenever the user hands you a pre-split, single-chapter PDF
(their own split of a larger book into per-chapter files) rather than a
page range to extract yourself. Do this before rendering pages or
touching the PDF content:

1. Read enough of the PDF (page 1, maybe page 2) to get the chapter's
   **actual title** as printed — not the filename. Split PDFs are
   typically named uninformatively (`Chapter 1.pdf`, `Unit 3.pdf`), which
   tells you nothing about the slug.
2. Derive `<chapter-slug>` from that title using the naming rule above.
3. State the resulting path out loud and get it confirmed before writing
   anything — e.g. "Chapter title is '<title>' → slug
   `<chapter-slug>` → output at
   `<project>/content.<lang>/docs/<chapter-slug>/_index.md`. Confirm?"
   This catches two failure modes before they cost you a full
   transcription pass: the project root being wrong (user gave a path
   that isn't actually the `content.<lang>` tree root, or is a sibling
   subject's project) and the slug being wrong (title read incorrectly,
   or an edge case in the naming rule you're unsure about — apostrophes,
   numerals, an unusually long or ambiguous title).
4. Only after confirmation, proceed to dependency setup and the render
   step below.

If the user gives you a batch of split PDFs to process in sequence,
confirm the routing for each one individually before building it — don't
batch-confirm all the slugs up front from filenames alone, since the
real title (and therefore the slug) is only known once you've actually
opened that specific PDF.

### 3. Check/install dependencies
```bash
python3 -c "import pdfplumber, pdf2image" 2>/dev/null || \
  pip3 install pdfplumber pdf2image --break-system-packages -q
which pdfimages || brew install poppler
```

### 4. Render pages and find figure rects (language-agnostic)
```bash
python3 ~/.claude/skills/pdf-to-md/render_and_find_figures.py "<PDF_PATH>" "<OUTPUT_DIR>"
```
This prints every page's candidate figure rectangles (x0/x1/top/bot in
PDF points) and saves `page-1.png ... page-N.png` at 300 DPI.

### 5. Read every page image and plan the figure map
Use the Read tool on each `page-N.png`. For each `Figure N.N` / `படம் N.N`
caption you see, note which rect (from step 3's printed list, same page)
it belongs to — match by position (the rect sits just above its caption,
in the same column). Multi-figure pages need this done carefully; rects
are unlabeled geometry, matching them to figure numbers is a visual read.

Watch for a rect that contains an unrelated decoration overlapping the
real figure (seen once: a QR code sitting inside Figure 8.16's own
rectangle in the Tamil PDF — it was genuinely inside the box, not a
script error). Crop a touch narrower to exclude it, or mask it out after
cropping (open the crop, paint over the region with the background
color) — whichever keeps more of the real diagram intact.

### 6. Crop each figure
```bash
python3 ~/.claude/skills/pdf-to-md/crop_figure.py "<PDF_PATH>" <page_num> <x0> <x1> <top> <bot> "<out_dir>/image-N-M.png"
```
One call per figure, using the coordinates you matched in step 5. Name
files `image-<chapter>-<fig>.png` (e.g. `image-8-1.png` for Figure 8.1).

### 7. Transcribe the text by hand
Read each page image again (or reuse what you already read in step 5)
and write the markdown directly:
- Merge PDF line-wraps into full prose paragraphs (never keep the PDF's
  per-line breaks).
- Transcribe every equation as real LaTeX: `$...$` for inline symbols
  (`$A$`, `$\nu$`), `$$...$$` for display equations. If the source page
  shows the equation inside a colored highlight box, wrap it in
  `$$\boxed{...}$$` to match.
- Reproduce heading hierarchy exactly: chapter `#`, numbered section
  `##` (e.g. `## 8.2 PHOTO ELECTRIC EFFECT`), numbered subsection `###`
  (`### 8.2.1 ...`), named sub-subsection `#####` (`##### Hertz observation`).
- `Note` / `Do You Know` boxes become `>**Note**` / `>**Do You Know**`
  blockquotes.
- Insert each cropped figure as `![<full caption text>](image-N-M.png)`
  at the point in the text where its caption appears. If a caption spans
  two PDF lines, join them into one caption string.
- Tables (e.g. work-function tables) become real markdown tables, not an
  image reference — this is cleaner than the source project's own
  image-based table and has been accepted as an improvement.
- Text sitting *inside* a figure's rectangle (axis labels, component
  labels like "Metal", "Electrons") is already visible in the cropped
  image — do not also transcribe it into body prose.

### 8. Tamil-specific transcription notes
Match the existing `content.ta` corpus's conventions exactly (confirmed
against `content.ta/docs/dual-nature-of-radiation-and-matter/_index.md`):
- Technical/physics terms: Tamil term first, English original in
  parentheses on first use — e.g. `எலக்ட்ரான் உமிழ்வு (Electron emission)`,
  `மின்னழுத்த அரண் (potential barrier)`. Subsequent mentions use the Tamil
  term alone.
- Equation subscripts that are words (e.g. "max") are transliterated into
  Tamil inside `\text{}`, not left in English:
  `K_{\text{பெருமம்}}`, `v_{\text{பெருமம்}}` (பெருமம் = "maximum").
- Variable letters themselves ($A$, $C$, $V_0$, $\nu$) stay as-is — only
  the descriptive word-subscripts get transliterated.
- Headings and section numbers stay numeric/Latin (`### 8.2.4 ...`);
  only the heading text is Tamil.

### 9. Verify against existing reference (if one exists)
If a reference `_index.md` already exists for this chapter/language
(there was one for this chapter — do not assume there always will be),
diff your transcription against the overlapping section:
```bash
diff <(sed -E 's/image-[^.]+\.png/image.png/' your_output.md) <(sed -n 'START,ENDp' reference.md)
```
Normalize image filenames before diffing since those legitimately differ
by extraction run. Real prose/LaTeX content should match word-for-word;
remaining diffs should only be whitespace, line-wrap artifacts in the
reference, or image filename/table-vs-image-ref differences.

### 10. Show output and offer to copy into the project
Show the user the markdown and a couple of cropped figures. Ask before
writing into the actual `content.en` / `content.ta` project tree.

## HTML source input

Some sources arrive as one large HTML file (often a whole-book export,
e.g. `10-SOCIALSCIENCE-EM.html`) rather than a per-chapter PDF. The
pipeline differs from the PDF path in one major way — there is no page
image to render or crop from — but routing, transcription conventions,
and verification all still apply the same as above.

### What the source actually looks like
Confirmed structure (TN textbook HTML export, fetched via WebFetch):
- One continuous document, not paginated — can span 200+ pages of
  content and multiple subjects/units in a single file. The user needs
  to tell you which unit/chapter they want, or you need to locate it by
  heading text; don't assume the whole file is one job.
- Headings are bold-marked text (`**Unit 1**`, `**1.1 Scramble for
  Colonies**` etc.), not real HTML heading tags in what WebFetch returns
  — treat this the same as the PDF path's "fix bold-as-heading to real
  markdown heading levels" work.
- Images appear inline as `![<alt text>](imageNNN.png)` with **relative
  filenames** — the actual image files live at sibling URLs on the same
  host/path as the HTML (confirmed: `.../image007.png` next to
  `.../10-SOCIALSCIENCE-EM.html` fetches a real PNG directly).
- Each image is typically followed by a `Picture description starts` /
  `Picture description ends` block containing a plain-text description —
  this is effectively a ready-made caption/alt-text. Use it (cleaned up)
  as the markdown image's alt text rather than inventing your own.
- Callout/note boxes are delimited by `**Box Item starts**` /
  `**Box Item ends**` — treat these the same as the PDF path's `>**Note**`
  blockquote convention.
- QR-code placeholders appear as `![Q R CODE <letters> is given.]
  (imageNNN.png)` followed by plain repeated text — these are decorative,
  same call as QR codes in the PDF path: skip them, don't download or
  reference them.

### Steps (HTML variant)
1. **Fetch and locate.** Use WebFetch to pull the relevant section — ask
   it to return the specific unit/chapter's raw content if the file is
   large, since a 200+ page single fetch may get summarized/truncated
   rather than returned verbatim. Confirm you have the complete chapter
   (check for a clean start/end boundary — a "Unit N" heading at the top
   and the next unit's heading, or an Exercise/Summary section, at the
   bottom) before transcribing from it.
2. **Route** exactly as step 2 above — read the real chapter title from
   the fetched content, derive the slug, confirm the output path with
   the user before building anything.
3. **Download the real figures.** For every non-decorative
   `![...](imageNNN.png)` reference, fetch the sibling image URL
   directly (`curl` or equivalent) into your output directory — there is
   no cropping step, the source image file *is* the figure. Keep the
   original filename (`imageNNN.png`) or rename to match this project's
   `image-<chapter>-<fig>.png` convention if the chapter has numbered
   figures; be consistent with whichever you pick.
4. **Transcribe.** Same conventions as PDF step 7 (merge into prose
   paragraphs — HTML text is usually already close to paragraph form so
   this is lighter work than PDF line-unwrapping; real LaTeX for any
   math; proper heading levels; blockquotes for note/box items). Use the
   "Picture description" text as a starting point for each image's alt
   text, tightened to match this project's caption style.
5. **Tamil-specific notes (step 8 above) still apply** if the HTML is
   the Tamil edition — bilingual terms on first use, transliterated
   subscripts, etc. HTML text does not have the PDF glyph-reordering
   problem, so this is usually the *preferred* source for Tamil when
   both a PDF and an HTML are available — say so if the user is deciding
   between the two.
6. **Verify and show**, same as PDF steps 9–10.

### When both a PDF and an HTML source exist for the same chapter
Ask the user which to use rather than guessing, and for Tamil
specifically, mention that HTML is usually the better source (reliable
text, no reordering risk) if they haven't already decided — per the
top-of-file note to always confirm PDF-vs-HTML for Tamil jobs.

## Parallel / multi-agent execution

Default to parallel agents whenever there is more than one chapter PDF to
process, or a single PDF long enough that reading every page serially
would be slow (roughly 15+ pages). There are two independent axes of
parallelism — use either or both depending on what the user hands you:

### Axis 1: multiple chapter sources at once

When the user gives a folder of several already-split, single-chapter
sources — PDFs, HTML files, or a mix of both — dispatch **one agent per
source file**, run in the background, each doing the full pipeline for
its chapter end-to-end: route (step 2) → render/fetch → crop/download →
transcribe → verify. Do not process the folder one file at a time
yourself — that serializes work an agent can do independently. A mixed
batch (some chapters as PDF, some as HTML) is fine — each agent just
follows whichever of the two workflows above matches its own source
file; the routing/confirmation/transcription-quality bar is the same
either way.

Before dispatching, for each source do the lightweight part yourself
first (it's cheap and keeps routing mistakes from multiplying across
agents): open page 1 (PDF) or fetch the start of the chapter (HTML),
read the real chapter title, derive the slug, and confirm the output
path with the user — per-source, not batched sight-unseen from filenames
(see step 2). Only once a source's routing is confirmed, hand that one
off to its own agent with the confirmed source path, output path, and
language already decided — the agent should not have to re-derive or
re-confirm routing itself.

Each agent's prompt needs, at minimum:
- The exact source PDF path and the exact confirmed output directory
  (both the scratch working dir it writes `page-N.png`/`image-*.png`
  into, and the final `content.<lang>/docs/<slug>/` destination)
- A pointer to this skill file (`~/.claude/skills/pdf-to-md/SKILL.md`)
  and an instruction to read it first — don't re-explain the whole
  workflow inline in the prompt, the skill file is the source of truth
  and gets updated independently of any one job
- The language for that PDF and, if Tamil, an explicit reminder that
  text extraction is unusable and page-image reading is mandatory (new
  agents have no memory of this project's prior findings)
- What to report back on completion: figure count + filenames, line
  count, any content it was unsure how to transcribe, and the final
  file paths it wrote

### Axis 2: splitting one long PDF across page ranges

For a single PDF long enough that serial page-by-page reading is slow,
split its page range into roughly-even chunks (6–10 pages per chunk
worked well) and dispatch one agent per chunk, each writing to its own
`part_<start>-<end>.md` plus whatever figures it crops into the shared
output directory — then assemble the parts yourself afterward. This was
validated on a 35-page chapter: 1 chunk done directly, 4 more chunks via
parallel agents, assembled into one `_index.md` with zero figure-filename
collisions and a clean, gap-free figure sequence across all chunks.

Concretely, for each chunk's agent:
- Tell it exactly which page range it owns and where the pre-rendered
  `page-N.png` files already are (render once yourself first with
  `render_and_find_figures.py` over the *whole* PDF, so agents aren't
  duplicating that work or racing to render the same pages)
- Have it name figures by their actual printed figure number (e.g.
  `image-8-13.png`), not by chunk — this is what keeps parallel agents
  from colliding on filenames even though none of them can see what the
  others are doing
- Tell it to write ONLY the markdown for its own page range to its own
  `part_N-M.md`, with no frontmatter and no chapter title (the assembler
  adds those once, from the first chunk or separately)
- Have it report back any judgment calls — an unnumbered figure it had to
  name descriptively instead, a source typo it preserved verbatim, a
  structural oddity (e.g. one printed caption actually covering two
  sub-figures) — these need reconciling across chunks during assembly

### Assembling parallel output

After every agent reports back:
1. Check every part file's image references resolve to files that exist
   on disk, and that there are no filename collisions between chunks
   (`grep -oE 'image-[a-zA-Z0-9.-]+\.png' part_*.md | sort | uniq -d`
   should be empty).
2. Check each part-to-part seam reads continuously: the last heading/
   sentence of one chunk and the first of the next should flow without a
   gap or duplicated content. Figure numbering across the whole document
   should be an unbroken sequence (e.g. Fig 1.1 through Fig 1.50, no
   gaps) — a gap means a figure was missed, a duplicate means two agents
   covered overlapping pages.
3. Reconcile the judgment calls agents flagged (inconsistent figure
   naming for unnumbered figures, differing conventions between chunks)
   before concatenating — fix these centrally rather than leaving
   per-chunk inconsistencies in the final file.
4. Concatenate in page order into the final `_index.md`, do one more full
   read-through yourself, then proceed to step 9 (verify against
   reference) and step 10 (show + offer to copy) as normal.

Don't skip the assembly read-through even when every agent reported
success — agents work from page images only and cannot see each other's
output, so a mismatch at a chunk boundary (e.g. one agent assuming a
sentence that actually continues into the next chunk was already
complete) is a realistic failure mode that only shows up once the pieces
are side by side.

## Output structure
```
<output_dir>/
  _index.md            ← hand-transcribed markdown: prose + LaTeX + figure refs
  page-1.png ...       ← full page scans at 300 DPI (ground truth, also useful after _index.md is done, for spot-checking)
  image-8-1.png ...    ← cropped figures, named by figure number
```

## Known limitations
- **No OCR / auto-LaTeX.** Every equation and every paragraph join is a
  manual transcription step. This is slow but is the only approach that
  has produced output matching the reference quality bar.
- **Figure detection needs a filled background rectangle.** Plain
  black-and-white line art with no color fill won't be found by the rect
  scan — crop those by hand from the page render using any image tool,
  or eyeball coordinates into `crop_figure.py`.
- **Tamil pdfplumber text extraction is unusable** — see above. Don't
  spend time trying to fix it with reordering heuristics; go straight to
  page-image reading.
- `extract_pdf.py` (the older fully-scripted attempt) still exists and
  runs, but treat its markdown output as a rough draft only — known
  issues: interleaved column text if `COL_MID` is mistuned, equation
  lines flagged rather than transcribed, figure crops occasionally
  include non-figure content without a human eye checking the rect match.

## Verified against
TN state board physics textbook, Unit 8 "Dual Nature of Radiation and
Matter":
- English source PDF (chapter pp. 108–122, three chunks): all figures
  (8.1–8.16) correctly cropped and positioned; prose diffed word-for-word
  against the existing `content.en` reference for overlapping sections —
  exact match.
- Tamil source PDF (chapter pp. 108–116): all figures (8.1–8.12) correctly
  cropped (including one QR-code-overlap fix on Figure 8.16); prose and
  LaTeX diffed word-for-word against the existing `content.ta` reference
  — exact match, including the bilingual-term and transliterated-subscript
  conventions.
