# PDF to Markdown — what this does

This is a Claude Code skill for turning a textbook chapter (PDF, or an
HTML export) into a clean markdown file with properly formatted text,
real math equations, and cropped figure images — ready to drop into the
`tnebooks` content projects:

- [github.com/tnebooks/10th-maths](https://github.com/tnebooks/10th-maths)
- [github.com/tnebooks/10th-social](https://github.com/tnebooks/10th-social)
- [github.com/tnebooks/12th-physics](https://github.com/tnebooks/12th-physics)

## The problem it solves

Textbook PDFs don't convert to markdown cleanly on their own. A naive
extraction gives you broken line-wraps, garbled equations
(`fx() =+ 68 x` instead of `f(x) = 6x + 8`), and no usable figures. For
Tamil-language PDFs it's worse — the text comes out of order entirely.

This skill exists because we tried the fully-automated route first, and
it wasn't good enough to actually commit. So the approach it documents
is: automate the mechanical parts (rendering pages, cropping figures),
and have Claude read each page like a person would for the text and
math.

## What you get

For a chapter PDF, you end up with:
- `_index.md` — the chapter's text, properly formatted (headings, note
  boxes, tables) with every equation written as real LaTeX
- A set of cropped image files, one per figure/diagram/photo in the
  chapter, named to match the figure numbers in the book
- (For sanity-checking) full-page screenshots of the source PDF, so you
  can compare the output against the original

## How to use it

Just ask Claude, in a session that has this skill available:

> "Parse this PDF into markdown" (and attach or point to the file)

or hand over a folder of already-split chapter PDFs and say where they
should go. Claude will:
1. Open the file and read the actual chapter title (not just the
   filename) to figure out where the output belongs
2. Tell you the folder it's about to write to and wait for you to
   confirm — so if the project or chapter name is wrong, you catch it
   before anything is built, not after
3. Do the extraction and show you the result before copying it into a
   real project folder

If you don't like the output, say so — it's a draft until you approve
copying it in, and even then Claude won't commit or push to GitHub on
its own.

## Languages

Each book exists in English and Tamil as *separate* source files — this
isn't a translation tool, it processes whichever language file you give
it. If you say "Tamil" without specifying whether you have a PDF or an
HTML file, Claude will ask — Tamil text comes out much better from HTML
than from PDF, so it's worth knowing which you have.

## Multiple chapters at once

If you hand over several chapter files together, Claude will work on
them in parallel (multiple chapters at the same time) rather than one at
a time, to get through a batch faster. For a single very long PDF, it
may also split the work across parallel helpers internally and stitch
the result back together — you don't need to manage that, just review
the final output.

## What it doesn't do

- It doesn't push anything to GitHub. It'll stage files for you to
  review and commit yourself.
- It doesn't guess — if the chapter title or target folder is unclear,
  it'll ask rather than pick something.
- It's not instant. Reading and transcribing a chapter properly, the way
  a careful human would, takes real time — especially for long chapters
  with lots of math or figures.

## Cross-check a sample

The best way to know what "good" looks like before relying on this
yourself: compare against a chapter that's already been through this
skill and checked word-for-word against its source.

- **Physics** (the original verification case) — "Dual Nature of
  Radiation and Matter":
  [English](https://github.com/tnebooks/12th-physics/tree/develop/content.en/docs/dual-nature-of-radiation-and-matter) ·
  [Tamil](https://github.com/tnebooks/12th-physics/tree/develop/content.ta/docs/dual-nature-of-radiation-and-matter)
- **Maths** — "Relations and Functions" (full chapter, including worked
  examples and exercises with real LaTeX):
  [English](https://github.com/tnebooks/10th-maths/tree/develop/content.en/docs/relations-and-functions)
- **Social Science** — "Outbreak of World War I and Its Aftermath":
  [English](https://github.com/tnebooks/10th-social/tree/develop/content.en/docs/outbreak-of-world-war-i-and-its-aftermath)

Open the `_index.md` in any of those and compare it against the
chapter's actual pages in the source textbook — that's the quality bar
this skill is meant to hit every time.

## Technical details

If you're a developer and want the exact rules, conventions, and
implementation notes this skill follows, see
[`SKILL.md`](SKILL.md) in this same folder — that file is written for
Claude to follow precisely, this one is written for people to understand
what's going on.
