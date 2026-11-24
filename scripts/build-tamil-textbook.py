#!/usr/bin/env python3
"""Build source-backed Tamil lesson bundles from the supplied textbook PDF."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = Path(
    "/Users/I740919/Downloads/Class_12_Zoology_Tamil_2024_Edition-www.tntextbooks.in.pdf"
)
SOURCE_SHA256 = "be5594197fb941d5c624f7571180d5a6ba2a771fc706d06ca84b8846d32d1aad"

CHAPTERS = [
    {"number": 1, "title": "உயிரிகளின் இனப்பெருக்கம்", "slug": "reproduction-in-organisms", "pdf_start": 9, "pdf_end": 19},
    {"number": 2, "title": "மனித இனப்பெருக்கம்", "slug": "human-reproduction", "pdf_start": 20, "pdf_end": 43},
    {"number": 3, "title": "இனப்பெருக்க நலன்", "slug": "reproductive-health", "pdf_start": 44, "pdf_end": 60},
    {"number": 4, "title": "மரபுக் கடத்தல் கொள்கைகள் மற்றும் மாறுபாடுகள்", "slug": "principles-of-inheritance-and-variation", "pdf_start": 61, "pdf_end": 80},
    {"number": 5, "title": "மூலக்கூறு மரபியல்", "slug": "molecular-genetics", "pdf_start": 81, "pdf_end": 116},
    {"number": 6, "title": "பரிணாமம்", "slug": "evolution", "pdf_start": 117, "pdf_end": 141},
    {"number": 7, "title": "மனித நலம் மற்றும் நோய்கள்", "slug": "human-health-and-diseases", "pdf_start": 142, "pdf_end": 160},
    {"number": 8, "title": "நோய்த்தடைக்காப்பியல்", "slug": "immunology", "pdf_start": 161, "pdf_end": 183},
    {"number": 9, "title": "மனித நலனில் நுண்ணுயிரிகள்", "slug": "microbes-in-human-welfare", "pdf_start": 184, "pdf_end": 195},
    {"number": 10, "title": "உயிரி தொழில் நுட்பவியலின் பயன்பாடுகள்", "slug": "applications-of-biotechnology", "pdf_start": 196, "pdf_end": 218},
    {"number": 11, "title": "உயிரினங்கள் மற்றும் இனக்கூட்டம்", "slug": "organisms-and-populations", "pdf_start": 219, "pdf_end": 244},
    {"number": 12, "title": "உயிரிய பல்வகைத்தன்மை மற்றும் அதன் பாதுகாப்பு", "slug": "biodiversity-and-its-conservation", "pdf_start": 245, "pdf_end": 272},
    {"number": 13, "title": "சுற்றுச்சூழல் இடர்பாடுகள்", "slug": "environmental-issues", "pdf_start": 273, "pdf_end": 300},
]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest(pdf_path: Path) -> dict:
    return {
        "schema_version": 1,
        "source": {
            "path": str(pdf_path),
            "edition": 2024,
            "language": "Tamil",
            "sha256": SOURCE_SHA256,
        },
        "lesson_pdf_pages": {"start": 9, "end": 300},
        "back_matter_pdf_start": 301,
        "chapters": CHAPTERS,
        "teacher_approval": False,
    }


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def validate_tesseract_languages() -> list[str]:
    executable = shutil.which("tesseract")
    if not executable:
        raise FileNotFoundError("tesseract was not found")
    result = subprocess.run(
        [executable, "--list-langs"],
        check=True,
        text=True,
        capture_output=True,
    )
    languages = [line.strip() for line in result.stdout.splitlines()[1:] if line.strip()]
    missing = {"tam", "eng"} - set(languages)
    if missing:
        raise RuntimeError(f"missing Tesseract languages: {sorted(missing)}")
    return languages


def validate_source(pdf_path: Path) -> None:
    if not pdf_path.is_file():
        raise FileNotFoundError(pdf_path)
    actual_hash = file_sha256(pdf_path)
    if actual_hash != SOURCE_SHA256:
        raise ValueError(f"source PDF hash mismatch: {actual_hash}")


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


def render_ocr_pages(pdf_path: Path) -> tuple[tempfile.TemporaryDirectory, dict[int, Path]]:
    temporary = tempfile.TemporaryDirectory(prefix="tamil-zoology-ocr-")
    temp_root = Path(temporary.name)
    prefix = temp_root / "source"
    environment = os.environ.copy()
    environment.setdefault("XDG_CACHE_HOME", str(temp_root / "font-cache"))
    subprocess.run(
        [
            str(find_pdftoppm()),
            "-f",
            "9",
            "-l",
            "300",
            "-r",
            "240",
            "-jpeg",
            "-jpegopt",
            "quality=92",
            str(pdf_path),
            str(prefix),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=environment,
    )
    rendered = {
        int(path.stem.rsplit("-", 1)[1]): path
        for path in temp_root.glob("source-*.jpg")
    }
    expected = set(range(9, 301))
    if set(rendered) != expected:
        missing = sorted(expected - set(rendered))
        raise RuntimeError(f"rendered source pages are incomplete; missing {missing}")
    return temporary, rendered


def clean_ocr_text(text: str) -> str:
    text = unicodedata.normalize(
        "NFC",
        text.replace("\x0c", "").replace("\u200c", "").replace("\u200d", ""),
    )
    cleaned: list[str] = []
    for raw_line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if not line:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue
        if re.search(r"XII Std Biology-Zoology.*TM\.indd", line, re.I):
            continue
        if line == "www.tntextbooks.in" or re.fullmatch(r"\d{1,3}", line):
            continue
        if re.fullmatch(r"[|\-–— ]+", line):
            continue
        if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}.*", line):
            continue
        cleaned.append(line)
    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    return "\n".join(cleaned)


def ocr_image(image_path: Path) -> dict:
    executable = shutil.which("tesseract")
    if not executable:
        raise FileNotFoundError("tesseract was not found")
    result = subprocess.run(
        [
            executable,
            str(image_path),
            "stdout",
            "-l",
            "tam+eng",
            "--psm",
            "3",
            "--dpi",
            "240",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    text = clean_ocr_text(result.stdout)
    tamil_characters = len(re.findall(r"[\u0b80-\u0bff]", text))
    issues = []
    if tamil_characters < 50:
        issues.append("OCR produced unusually little Tamil text; inspect the source image")
    if "\ufffd" in text:
        issues.append("OCR output contains Unicode replacement characters")
    return {
        "text": text,
        "method": "tesseract-5-tam+eng-psm3-240dpi",
        "issues": issues,
    }


def extract_pages(rendered: dict[int, Path]) -> dict[int, dict]:
    validate_tesseract_languages()
    extracted: dict[int, dict] = {}
    workers = min(4, max(1, os.cpu_count() or 1))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(ocr_image, rendered[pdf_page]): pdf_page
            for pdf_page in range(9, 270)
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            pdf_page = futures[future]
            extracted[pdf_page] = future.result()
            if completed % 20 == 0 or completed == len(futures):
                print(f"OCR {completed}/{len(futures)} pages", flush=True)
    return extracted


def ocr_text_to_markdown(text: str) -> str:
    output: list[str] = []
    numbered_heading = re.compile(r"^(\d+\.\d+(?:\.\d+)*)\s+(.+)$")
    special_headings = {
        "பாட உள்ளடக்கம்",
        "கற்றலின் நோக்கங்கள்",
        "கற்றலின் நோக்கங்கள் :",
        "சுருக்கம்",
        "மதிப்பீடு",
        "கருத்து வரைபடம்",
        "இணையச் செயல்பாடு",
    }
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            output.append("")
            continue
        match = numbered_heading.match(stripped)
        normalized_heading = stripped.rstrip(":").strip()
        if match:
            depth = 2 if match.group(1).count(".") == 1 else 3
            output.extend(["", f"{'#' * depth} {stripped}", ""])
        elif normalized_heading in {heading.rstrip(":").strip() for heading in special_headings}:
            output.extend(["", f"## {stripped}", ""])
        elif stripped[0] in {"•", "➢", ">", "*"}:
            item_text = stripped[1:].strip()
            if item_text:
                output.append(f"- {item_text}")
        else:
            output.append(stripped)
    markdown = "\n".join(output)
    return re.sub(r"\n{3,}", "\n\n", markdown).strip()


def write_source_asset(source_jpeg: Path, destination: Path) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_jpeg) as image:
        image = image.convert("RGB")
        image.thumbnail((1400, 1900), Image.Resampling.LANCZOS)
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
        f'summary: "தமிழ்நாடு பன்னிரண்டாம் வகுப்பு உயிரியல் - விலங்கியல் பாடம் {chapter["number"]}."',
        "---",
        "",
        "<!-- textbook-source-view:start -->",
        '[அசல் தமிழ் பாடநூல் பக்கங்கள் - படங்கள், அட்டவணைகள், செயல்பாடுகள் மற்றும் வினாக்கள்]({{< relref "source.md" >}})',
        "<!-- textbook-source-view:end -->",
        "",
        f'# பாடம் {chapter["number"]}: {chapter["title"]}',
        "",
        f'> மூலம்: தமிழ் வழிப் பாடநூல், PDF பக்கங்கள் {chapter["pdf_start"]}-{chapter["pdf_end"]}.',
        "",
        "> குறிப்பு: கீழுள்ள தேடக்கூடிய உரை தானியங்கி OCR மூலம் உருவாக்கப்பட்டது. துல்லியமான படங்கள், அட்டவணைகள் மற்றும் அமைப்பிற்கு அசல் பக்கங்களைப் பார்க்கவும்.",
        "",
    ]
    for pdf_page in range(chapter["pdf_start"], chapter["pdf_end"] + 1):
        printed_page = pdf_page - 8
        body.extend(
            [
                f'<a id="source-page-{pdf_page:03d}"></a>',
                "",
                f"## பாடநூல் பக்கம் {printed_page}",
                "",
                f'[அசல் பக்கத்தைப் பார்க்கவும்](source/#pdf-page-{pdf_page:03d})',
                "",
                ocr_text_to_markdown(pages[pdf_page]["text"]),
                "",
            ]
        )
    return "\n".join(body).rstrip() + "\n"


def source_gallery_markdown(chapter: dict) -> str:
    body = [
        "---",
        f'title: "அசல் பக்கங்கள் - {chapter["title"]}"',
        "build:",
        "  list: never",
        "  render: always",
        "---",
        "",
        f'# அசல் பாடநூல் பக்கங்கள்: {chapter["title"]}',
        "",
        "இந்தப் படங்கள் பாடநூலின் அசல் அமைப்பு, விளக்கப்படங்கள், குறிச்சொற்கள், அட்டவணைகள், செயல்பாடுகள் மற்றும் வினாக்களைப் பாதுகாக்கின்றன.",
        "",
    ]
    for pdf_page in range(chapter["pdf_start"], chapter["pdf_end"] + 1):
        printed_page = pdf_page - 8
        body.extend(
            [
                f'<a id="pdf-page-{pdf_page:03d}"></a>',
                "",
                f"## PDF பக்கம் {pdf_page} - பாடநூல் பக்கம் {printed_page}",
                "",
                f"![அசல் பாடநூல் பக்கம் {printed_page}](assets/source-p{pdf_page:03d}.webp)",
                "",
            ]
        )
    return "\n".join(body).rstrip() + "\n"


def landing_markdown() -> str:
    body = [
        "---",
        "title: 'விலங்கியல்'",
        "categories:",
        "  - science",
        "  - zoology",
        "weight: 1",
        "---",
        "",
        "# பன்னிரண்டாம் வகுப்பு உயிரியல் - விலங்கியல்",
        "",
        "## பாடங்கள்",
        "",
    ]
    for chapter in CHAPTERS:
        body.append(f'{chapter["number"]}. [{chapter["title"]}](./{chapter["slug"]}/)')
    return "\n".join(body) + "\n"


def write_audit_records(chapter: dict, pages: dict[int, dict], assets: list[dict]) -> None:
    audit_root = ROOT / ".textbook-agent" / f'ta-{chapter["slug"]}'
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
    lesson_id = f'ta-chapter-{chapter["number"]}'
    boundaries = {
        "schema_version": 1,
        "lesson_id": lesson_id,
        "original_title": chapter["title"],
        "slug": chapter["slug"],
        "pdf_start": chapter["pdf_start"],
        "pdf_end": chapter["pdf_end"],
        "boundary_evidence": "PDF bookmarks and inspected chapter-opening pages",
        "boundary_evidence_pages": [
            chapter["pdf_start"],
            chapter["pdf_end"],
            chapter["pdf_end"] + 1 if chapter["number"] < 12 else 270,
        ],
        "source_pdf_sha256": SOURCE_SHA256,
        "valid": True,
        "issues": [],
        "teacher_approval": False,
    }
    inventory = {
        "schema_version": 1,
        "lesson_id": lesson_id,
        "complete": False,
        "items": items,
        "issues": [
            "Provisional OCR page-level inventory; figures, tables, questions, choices, and Tamil OCR require item-level review against source images."
        ],
        "teacher_approval": False,
    }
    coverage = {
        "schema_version": 1,
        "lesson_id": lesson_id,
        "mapped_ids": ids,
        "mappings": [
            {"item_id": item["id"], "section_anchor": f'source-page-{item["pdf_page"]:03d}'}
            for item in items
        ],
        "teacher_approval": False,
    }
    asset_record = {
        "schema_version": 1,
        "lesson_id": lesson_id,
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
        "lesson_id": lesson_id,
        "valid": False,
        "covered_ids": [],
        "verified_aid_ids": [],
        "findings": [
            {
                "section_anchor": "lesson",
                "item_id": None,
                "blocking": True,
                "issue": "Tamil OCR and item-level semantic/visual comparison have not yet been fully reviewed.",
            },
            *extraction_findings,
        ],
        "checks": {
            "bookmark_boundaries_inspected": True,
            "source_page_assets_generated": True,
            "structural_bundle_checks": "pending test run",
            "full_semantic_review": False,
            "resource_runtime_checks": False,
        },
        "teacher_approval": False,
    }
    write_json(audit_root / "boundaries.json", boundaries)
    write_json(audit_root / "inventory.json", inventory)
    write_json(audit_root / "coverage.json", coverage)
    write_json(audit_root / "assets.json", asset_record)
    write_json(audit_root / "review.json", review)


def generate_book(pdf_path: Path) -> None:
    validate_source(pdf_path)
    temporary, rendered = render_ocr_pages(pdf_path)
    try:
        pages = extract_pages(rendered)
        for chapter in CHAPTERS:
            bundle = ROOT / "content.ta" / "docs" / chapter["slug"]
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
            (bundle / "_index.md").write_text(lesson_markdown(chapter, pages), encoding="utf-8")
            (bundle / "source.md").write_text(source_gallery_markdown(chapter), encoding="utf-8")
            write_audit_records(chapter, pages, asset_records)
        (ROOT / "content.ta" / "docs" / "_index.md").write_text(
            landing_markdown(), encoding="utf-8"
        )
    finally:
        temporary.cleanup()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--manifest-only", action="store_true")
    parser.add_argument("--check-ocr", action="store_true")
    args = parser.parse_args()

    if args.check_ocr:
        languages = validate_tesseract_languages()
        print(" ".join(language for language in ("tam", "eng") if language in languages))
        return

    validate_source(args.pdf)
    write_json(ROOT / ".textbook-agent" / "tamil-book-manifest.json", manifest(args.pdf))
    if not args.manifest_only:
        generate_book(args.pdf)


if __name__ == "__main__":
    main()
