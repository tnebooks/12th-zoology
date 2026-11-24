---
name: chapter-references
description: Add verified learning references (videos, links, books) to a Hugo docs-theme chapter's front matter. Use when the user asks to "add references to chapter X", "find resources/videos/books for a chapter", "add references in _index.md", or similar — for the osl design-system theme (10th-maths, 12th-physics, and sibling textbook projects built on osl/design-system).
---

# Chapter References

Research and attach a `references:` block (videos, links, books) to a chapter's front matter in Hugo docs-theme projects built on `osl/design-system`. Data lives directly in each chapter's `_index.md` — not a separate `references.md` page.

## Why `_index.md`, not a separate `references.md` file

Earlier iterations put `references:` in a standalone `references.md` leaf page (matching the design-system's own example at `exampleSite/content.en/docs/documentation/references.md` and `typography.md`). That works and gives a clickable "References" row in the sidebar (via `layouts/_partials/docs/docs-tree.html`, which lists every child page/section uniformly — no special-casing).

But the project owner decided the data should live in the chapter's own `_index.md` front matter instead. Tradeoff to know going in:
- **Lost:** the sidebar no longer shows a separate "References" row for the chapter (that row is tied 1:1 to a `references.md` page existing — confirmed by reading `docs-tree.html`, no synthetic-entry code exists).
- **Gained:** the header's References/Videos panel icons (bell + play-circle, opening `#referencepanel`/`#videopanel` off-canvas drawers) now populate directly on the chapter's main page, because those panels are rendered by `layouts/_partials/scripts.html`, which reads `.Params.references` from whatever page is current — previously that was empty on `_index.md` and only populated on the separate `references.md` page.

If the user wants the old sidebar-link behavior back, put the data in a `references.md` leaf page instead (same front-matter shape, just a different file). Don't mix both — pick one pattern per project and keep it consistent across all chapters/locales.

## Front matter shape

```yaml
---
title: 'Chapter Title'
categories:
    - chapter-slug
weight: 5
references:
    videos:
        - youtube: VIDEO_ID_1
        - youtube: VIDEO_ID_2

    links:
        - "[Link Title - Source Name](https://full-url) — One-sentence description of what it covers."
        - "[Another Link](https://...) — ..."
        - "[Third Link](https://...) — ..."

    books:
        - b1:
            title: "Book or Teacher Guide Title"
            authors:
                - "Author Name"
            publisher: "Publisher or Project Name"
            url: "https://direct-pdf-or-landing-page-url"

        - b2:
            title: "Second Book Title"
            authors:
                - "Author Name"
            publisher: "Publisher Name"
            url: "https://..."
summary: "One or two sentences, used as the page's own summary/blurb. Also what Hugo falls back to for auto-generated listing-card text if this field is absent."
---
```

**Field name: `summary:`, not `description:`.** The theme's `description:` front-matter key is inert — confirmed by reading `layouts/_partials/head.html` and every template in `layouts/`: nothing reads `.Params.description` or `.Description` anywhere. `summary:` is what both locales (`content.en`, `content.ta`) actually use, and it's what Hugo's own page-summary fallback mechanism keys off for listing cards. If you find `description:` in an `_index.md` from an earlier pass, rename it to `summary:` (value unchanged) — don't leave both.

**Target: 2 videos, 3 links, 2 books per chapter**, matching the project's established pattern. Adjust only if the user asks for a different count.

**`references:` block placement:** insert immediately after `weight:` (and `categories:` if present), before `summary:`. Keep `summary:` as the last front-matter key, right before the closing `---`. This matches every chapter already migrated in `10th-maths`.

## Research and verification workflow

Do not guess YouTube IDs, PDF URLs, or link paths from memory or from search-result snippets alone — bad links and fabricated video IDs are the single biggest risk here, and the user has explicitly called this out before ("these should be proper working links not something random"). For every resource:

1. **Search** for a real, topically-matched resource using `WebSearch`. Prefer:
   - Videos: official **Khan Academy** channel (`@khanacademy` or `@KhanAcademyIndiaEnglish`) — India channel videos are often explicitly tagged "Class 10" which is a strong relevance signal for this grade level.
   - Interactive links: **PhET Interactive Simulations** (`phet.colorado.edu`), **GeoGebra** (`geogebra.org/m/...`), or explainer pages from **Cuemath**, **Math is Fun** (`mathsisfun.com`), **Vedantu**.
   - Books/PDFs: **AMSI TIMES Project** teacher guides (`amsi.org.au/teacher_modules/pdfs/*.pdf` or `amsi.org.au/ESA_Senior_Years/PDF/*.pdf`) are a reliable recurring source — free, open, topically organized by Years 7-12, no login/paywall. Also **mathcentre.ac.uk**, **archive.org** (check it's full-view, not borrow-only — grep the page for "Borrow"/"Lending"/"DAISY" to detect lending-only items and reject them), **ncertbooks.org**.

2. **Verify every URL before writing it to a file:**
   - YouTube videos: call the oEmbed endpoint, don't just trust a search snippet:
     ```bash
     curl -s "https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=VIDEO_ID&format=json"
     ```
     Check the returned `title` and `author_name` actually match what you intended (official channel, right topic, not a random reupload). A snippet claiming a video ID exists is not proof — fetch and read the real title back.
   - Links and PDFs:
     ```bash
     curl -s -o /dev/null -w "%{http_code}\n" --max-time 15 -A "Mozilla/5.0" "https://..."
     ```
     Must return `200` (a `301`/`302` redirect to the same host on a simple path-casing change, e.g. `/simulation/` → `/simulations/`, is fine — but verify the final destination too). `403`/`404` means find a different resource, don't paper over it.
   - For PDFs specifically, also check the content-type header is `application/pdf`, not an HTML error page serving a 200:
     ```bash
     curl -sI --max-time 15 -A "Mozilla/5.0" "https://..." | grep -i "content-type"
     ```

3. **No duplicates.** Don't let the same resource appear as both a `videos:` entry and a `links:` entry (easy mistake when a Khan Academy video also has a standalone article page).

4. **Topical match over generic relevance.** Prefer a resource that maps to a *specific named section* in the chapter body (e.g. "Recall → Mid-point of line segment" → search for a midpoint-formula video specifically) over a broad "intro to the whole topic" video, when the chapter covers several distinct sub-topics.

## Multi-locale projects (en + ta)

When the project has parallel locales (`content.en`, `content.ta`):
- Reuse the **same verified resources** (video IDs, links, book PDFs) for both locales — per established convention here, keep video/link/book titles and descriptions in **English even on the `content.ta` page**, since most of these resources (PhET, Khan Academy, AMSI) are English-sourced and a translated title would be misleading.
- Each locale's own `summary:` stays in that locale's language — don't translate the chapter's own summary, only reuse the references data itself.
- If a locale's chapter `_index.md` has richer or different body content than its sibling (seen with `numbers-and-sequences` and `relations-and-functions` in this project, where `content.ta` had a bio/quote intro that `content.en` lacked entirely), that's a separate content gap — flag it to the user rather than silently inventing content. Translating existing Tamil content into English (clearly marked, e.g. a trailing note "*Translated from the Tamil edition's chapter introduction.*") is acceptable when the user explicitly approves it; never invent facts not present in either locale's source.

## Workflow checklist

1. Read the target chapter's `_index.md` (both locales if applicable) to see current front matter and confirm no `references:` block already exists.
2. Identify the chapter's sub-topics from its body headings to guide resource search.
3. Research 2 videos + 3 links + 2 books per the sourcing guidance above.
4. Verify every single URL/video ID per the verification steps above — no exceptions, no "looks right" shortcuts.
5. Build the `references:` block and insert it into front matter (after `weight`/`categories`, before `summary`).
6. If a `summary:`/`description:` field doesn't exist yet, add one (1-2 sentences) — if `description:` exists, rename to `summary:`.
7. Show the user the before/after diff for the first chapter and get confirmation before batching the rest, unless they've already approved the pattern in this session.
8. If a standalone `references.md` exists for the chapter from an earlier pass, delete it once its data has been merged into `_index.md` — don't leave both.

## Known pitfalls (from prior sessions on this project)

- **Confusing "data in HTML" with "visible in browser."** The videos/links/books panels are off-canvas drawers hidden until the user clicks a header icon (link icon → References panel, play-circle icon → Videos panel). Curling the page and finding `data-youtube-id="..."` in the raw HTML confirms the data is wired correctly even if it "looks empty" in a screenshot — the user needs to click the icon, not scroll the page body.
- **Checking the wrong page.** If `references:` lives only on `references.md` (not `_index.md`), the chapter's main page panel will be empty — that's expected, not a bug. If `references:` lives only on `_index.md`, a now-deleted `references.md` page will 404 (also expected) and any stale dev-server cache for that old URL needs a server restart to clear.
- **Hugo dev server caching stale routes.** After deleting a `references.md` file, the dev server (`hugo server`) may keep serving the old `/chapter/references/` URL until restarted. If the user reports a page "still showing" after a file delete, suspect server cache before suspecting the content change.
