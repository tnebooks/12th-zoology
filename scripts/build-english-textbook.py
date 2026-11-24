#!/usr/bin/env python3
"""Build source-backed English lesson bundles from the supplied textbook PDF."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pdfplumber
from PIL import Image
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = Path(
    "/Users/I740919/Downloads/Class_12_Zoology_English_2024_Edition-www.tntextbooks.in.pdf"
)
SOURCE_SHA256 = "6c4d22cb88038d5db924e863fd0c73d22259f467a49ed9a4eba629db8b724f5d"

CHAPTERS = [
    {"number": 1, "title": "Reproduction in Organisms", "slug": "reproduction-in-organisms", "pdf_start": 9, "pdf_end": 18},
    {"number": 2, "title": "Human Reproduction", "slug": "human-reproduction", "pdf_start": 19, "pdf_end": 39},
    {"number": 3, "title": "Reproductive Health", "slug": "reproductive-health", "pdf_start": 40, "pdf_end": 52},
    {"number": 4, "title": "Principles of Inheritance and Variation", "slug": "principles-of-inheritance-and-variation", "pdf_start": 53, "pdf_end": 68},
    {"number": 5, "title": "Molecular Genetics", "slug": "molecular-genetics", "pdf_start": 69, "pdf_end": 99},
    {"number": 6, "title": "Evolution", "slug": "evolution", "pdf_start": 100, "pdf_end": 119},
    {"number": 7, "title": "Human Health and Diseases", "slug": "human-health-and-diseases", "pdf_start": 120, "pdf_end": 136},
    {"number": 8, "title": "Immunology", "slug": "immunology", "pdf_start": 137, "pdf_end": 155},
    {"number": 9, "title": "Microbes in Human Welfare", "slug": "microbes-in-human-welfare", "pdf_start": 156, "pdf_end": 164},
    {"number": 10, "title": "Applications of Biotechnology", "slug": "applications-of-biotechnology", "pdf_start": 165, "pdf_end": 183},
    {"number": 11, "title": "Organisms and Populations", "slug": "organisms-and-populations", "pdf_start": 184, "pdf_end": 204},
    {"number": 12, "title": "Biodiversity and its Conservation", "slug": "biodiversity-and-its-conservation", "pdf_start": 205, "pdf_end": 226},
    {"number": 13, "title": "Environmental Issues", "slug": "environmental-issues", "pdf_start": 227, "pdf_end": 249},
]


def manifest(pdf_path: Path) -> dict:
    return {
        "schema_version": 1,
        "source": {
            "path": str(pdf_path),
            "edition": 2024,
            "language": "English",
            "sha256": SOURCE_SHA256,
        },
        "lesson_pdf_pages": {"start": 9, "end": 249},
        "back_matter_pdf_start": 250,
        "chapters": CHAPTERS,
        "teacher_approval": False,
    }


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_pdftoppm() -> Path:
    command = shutil.which("pdftoppm")
    if command:
        return Path(command)
    for candidate in [
        Path("/opt/homebrew/bin/pdftoppm"),
        Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/pdftoppm",
    ]:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("pdftoppm was not found")


def clean_page_text(text: str, chapter_title: str, printed_page: int) -> str:
    text = (
        text.replace("\x00", "")
        .replace("\u00ad", "")
        .replace("ﬁ", "fi")
        .replace("ﬂ", "fl")
    )
    cleaned = []
    footer_pattern = re.compile(rf"^{re.escape(chapter_title)}\s+{printed_page}$", re.I)
    printer_pattern = re.compile(r"^XII Std (?:Biology-)?Zoology.*EM\.indd", re.I)
    for raw_line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if not line or line == str(printed_page):
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue
        if footer_pattern.match(line) or printer_pattern.match(line):
            continue
        cleaned.append(line)
    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    return "\n".join(cleaned)


def page_text_to_markdown(text: str) -> str:
    output = []
    numbered_heading = re.compile(r"^(\d+\.\d+(?:\.\d+)*)\s+(.+)$")
    special_headings = {
        "chapter outline",
        "learning objectives",
        "learning objective",
        "summary",
        "evaluation",
        "concept map",
        "ict corner",
    }
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            output.append("")
            continue
        match = numbered_heading.match(stripped)
        if match:
            depth = 2 if match.group(1).count(".") == 1 else 3
            output.extend(["", f"{'#' * depth} {stripped}", ""])
        elif stripped.lower() in special_headings:
            output.extend(["", f"## {stripped}", ""])
        elif stripped.startswith("•"):
            output.append(f"- {stripped[1:].strip()}")
        elif re.match(r"^Fig\.\s*\d", stripped, re.I):
            output.append(f"**{stripped}**")
        else:
            output.append(stripped)
    markdown = "\n".join(output)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown.strip()


def extract_pages(pdf_path: Path) -> dict[int, dict]:
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    reader = PdfReader(str(pdf_path))
    extracted = {}
    with pdfplumber.open(str(pdf_path)) as plumber_pdf:
        for chapter in CHAPTERS:
            for pdf_page in range(chapter["pdf_start"], chapter["pdf_end"] + 1):
                printed_page = pdf_page - 8
                method = "pypdf"
                issues = []
                try:
                    raw_text = reader.pages[pdf_page - 1].extract_text() or ""
                except Exception as error:
                    method = "pdfplumber-fallback"
                    issues.append(f"pypdf extraction failed: {type(error).__name__}")
                    raw_text = plumber_pdf.pages[pdf_page - 1].extract_text() or ""
                text = clean_page_text(raw_text, chapter["title"], printed_page)
                if len(text) < 80:
                    issues.append("extracted text is unusually short; inspect the source image")
                extracted[pdf_page] = {
                    "text": text,
                    "method": method,
                    "issues": issues,
                }
    return extracted


def render_source_pages(pdf_path: Path) -> dict[int, Path]:
    pdftoppm = find_pdftoppm()
    temporary = tempfile.TemporaryDirectory(prefix="zoology-source-pages-")
    temp_root = Path(temporary.name)
    prefix = temp_root / "source"
    subprocess.run(
        [
            str(pdftoppm),
            "-f",
            "9",
            "-l",
            "249",
            "-r",
            "120",
            "-jpeg",
            "-jpegopt",
            "quality=90",
            str(pdf_path),
            str(prefix),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    rendered = {}
    for image_path in temp_root.glob("source-*.jpg"):
        page_number = int(image_path.stem.rsplit("-", 1)[1])
        rendered[page_number] = image_path
    if set(rendered) != set(range(9, 250)):
        missing = sorted(set(range(9, 250)) - set(rendered))
        raise RuntimeError(f"rendered source pages are incomplete; missing {missing}")
    rendered["_temporary_directory"] = temporary
    return rendered


def write_source_asset(source_jpeg: Path, destination: Path) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_jpeg) as image:
        image = image.convert("RGB")
        dimensions = [image.width, image.height]
        image.save(destination, "WEBP", quality=84, method=6)
    return {
        "path": str(destination.relative_to(ROOT)),
        "width": dimensions[0],
        "height": dimensions[1],
        "sha256": file_sha256(destination),
    }


def lesson_markdown(chapter: dict, pages: dict[int, dict]) -> str:
    body = [
        "---",
        f'title: "{chapter["title"]}"',
        f'weight: {chapter["number"]}',
        "categories:",
        "  - biology",
        "  - zoology",
        f'summary: "Source-backed Chapter {chapter["number"]} content from the Tamil Nadu Class 12 Zoology textbook."',
        "---",
        "",
        "<!-- textbook-source-view:start -->",
        '[Original English textbook pages — diagrams, tables, activities and exercises]({{< relref "source.md" >}})',
        "<!-- textbook-source-view:end -->",
        "",
        f'# Chapter {chapter["number"]}: {chapter["title"]}',
        "",
        f'> Source: 2024 English-medium textbook, PDF pages {chapter["pdf_start"]}–{chapter["pdf_end"]}.',
        "",
    ]
    for pdf_page in range(chapter["pdf_start"], chapter["pdf_end"] + 1):
        printed_page = pdf_page - 8
        body.extend(
            [
                f'<a id="source-page-{pdf_page:03d}"></a>',
                "",
                f"## Textbook page {printed_page}",
                "",
                f'[View the original page](source/#pdf-page-{pdf_page:03d})',
                "",
                page_text_to_markdown(pages[pdf_page]["text"]),
                "",
            ]
        )
    return "\n".join(body).rstrip() + "\n"


def source_gallery_markdown(chapter: dict) -> str:
    body = [
        "---",
        f'title: "Original pages — {chapter["title"]}"',
        "build:",
        "  list: never",
        "  render: always",
        "---",
        "",
        f'# Original textbook pages: {chapter["title"]}',
        "",
        "These images preserve the supplied page layout, diagrams, labels, tables, activities and exercises.",
        "",
    ]
    for pdf_page in range(chapter["pdf_start"], chapter["pdf_end"] + 1):
        printed_page = pdf_page - 8
        body.extend(
            [
                f'<a id="pdf-page-{pdf_page:03d}"></a>',
                "",
                f"## PDF page {pdf_page} · textbook page {printed_page}",
                "",
                f"![Original textbook page {printed_page}](assets/source-p{pdf_page:03d}.webp)",
                "",
            ]
        )
    return "\n".join(body).rstrip() + "\n"


def landing_markdown() -> str:
    body = [
        "---",
        "title: 'Zoology'",
        "categories:",
        "  - science",
        "  - zoology",
        "weight: 1",
        "---",
        "",
        "# Class 12 Zoology",
        "",
        "## Lessons",
        "",
    ]
    for chapter in CHAPTERS:
        body.append(f'{chapter["number"]}. [{chapter["title"]}](./{chapter["slug"]}/)')
    return "\n".join(body) + "\n"


def write_audit_records(chapter: dict, pages: dict[int, dict], assets: list[dict]) -> None:
    audit_root = ROOT / ".textbook-agent" / chapter["slug"]
    items = []
    for pdf_page in range(chapter["pdf_start"], chapter["pdf_end"] + 1):
        record = pages[pdf_page]
        items.append(
            {
                "id": f"p{pdf_page}-page-text-1",
                "pdf_page": pdf_page,
                "source_order": pdf_page * 1000 + 1,
                "kind": "page_text",
                "parent_id": None,
                "text": record["text"],
                "bbox": [0.0, 0.0, 1.0, 1.0],
                "extraction_method": record["method"],
                "issues": record["issues"],
            }
        )
    ids = [item["id"] for item in items]
    boundary = {
        "schema_version": 1,
        "lesson_id": f'en-chapter-{chapter["number"]}',
        "original_title": chapter["title"],
        "slug": chapter["slug"],
        "pdf_start": chapter["pdf_start"],
        "pdf_end": chapter["pdf_end"],
        "boundary_evidence_pages": [
            chapter["pdf_start"],
            chapter["pdf_end"],
            chapter["pdf_end"] + 1 if chapter["number"] < 13 else 250,
        ],
        "source_pdf_sha256": SOURCE_SHA256,
        "valid": True,
        "issues": [],
        "teacher_approval": False,
    }
    inventory = {
        "schema_version": 1,
        "lesson_id": boundary["lesson_id"],
        "complete": False,
        "items": items,
        "issues": [
            "Provisional page-level inventory; figures, tables, questions and nested choices require item-level review against source images."
        ],
        "teacher_approval": False,
    }
    coverage = {
        "schema_version": 1,
        "lesson_id": boundary["lesson_id"],
        "mapped_ids": ids,
        "mappings": [
            {
                "item_id": item["id"],
                "section_anchor": f'source-page-{item["pdf_page"]:03d}',
            }
            for item in items
        ],
        "teacher_approval": False,
    }
    asset_record = {
        "schema_version": 1,
        "lesson_id": boundary["lesson_id"],
        "assets": assets,
        "teacher_approval": False,
    }
    extraction_findings = [
        {
            "section_anchor": f'source-page-{item["pdf_page"]:03d}',
            "item_id": item["id"],
            "blocking": True,
            "issue": issue,
        }
        for item in items
        for issue in item["issues"]
    ]
    review = {
        "schema_version": 1,
        "lesson_id": boundary["lesson_id"],
        "valid": False,
        "covered_ids": ids,
        "verified_aid_ids": [],
        "findings": [
            {
                "section_anchor": "lesson",
                "item_id": None,
                "blocking": True,
                "issue": "Full item-level semantic and visual comparison has not yet been completed.",
            },
            *extraction_findings,
        ],
        "checks": {
            "boundary_images_inspected": True,
            "source_page_assets_generated": True,
            "structural_bundle_checks": "pending test run",
            "full_semantic_review": False,
            "resource_runtime_checks": False,
        },
        "teacher_approval": False,
    }
    write_json(audit_root / "boundaries.json", boundary)
    write_json(audit_root / "inventory.json", inventory)
    write_json(audit_root / "coverage.json", coverage)
    write_json(audit_root / "assets.json", asset_record)
    write_json(audit_root / "review.json", review)


def generate_book(pdf_path: Path) -> None:
    if not pdf_path.is_file():
        raise FileNotFoundError(pdf_path)
    actual_hash = file_sha256(pdf_path)
    if actual_hash != SOURCE_SHA256:
        raise ValueError(f"source PDF hash mismatch: {actual_hash}")

    pages = extract_pages(pdf_path)
    rendered = render_source_pages(pdf_path)
    temporary = rendered.pop("_temporary_directory")
    try:
        for chapter in CHAPTERS:
            bundle = ROOT / "content.en" / "docs" / chapter["slug"]
            assets_root = bundle / "assets"
            assets_root.mkdir(parents=True, exist_ok=True)
            for old_page in assets_root.glob("source-p*.webp"):
                old_page.unlink()
            asset_records = []
            for pdf_page in range(chapter["pdf_start"], chapter["pdf_end"] + 1):
                destination = assets_root / f"source-p{pdf_page:03d}.webp"
                metadata = write_source_asset(rendered[pdf_page], destination)
                asset_records.append(
                    {
                        "item_id": f"p{pdf_page}-source-page-2",
                        "pdf_page": pdf_page,
                        "bbox": [0.0, 0.0, 1.0, 1.0],
                        "rotation": 0,
                        "uncertainty_flags": [],
                        **metadata,
                    }
                )
            (bundle / "_index.md").write_text(
                lesson_markdown(chapter, pages), encoding="utf-8"
            )
            (bundle / "source.md").write_text(
                source_gallery_markdown(chapter), encoding="utf-8"
            )
            write_audit_records(chapter, pages, asset_records)
        (ROOT / "content.en" / "docs" / "_index.md").write_text(
            landing_markdown(), encoding="utf-8"
        )
    finally:
        temporary.cleanup()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--manifest-only", action="store_true")
    args = parser.parse_args()

    write_json(ROOT / ".textbook-agent" / "english-book-manifest.json", manifest(args.pdf))
    if not args.manifest_only:
        generate_book(args.pdf)


if __name__ == "__main__":
    main()
