import json
import importlib.util
import re
import subprocess
import unittest
from pathlib import Path


import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".textbook-agent" / "tamil-book-manifest.json"
SCRIPT = ROOT / "scripts" / "build-tamil-textbook.py"
PYTHON = Path(sys.executable)


def load_builder_module():
    spec = importlib.util.spec_from_file_location("tamil_textbook_builder", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

EXPECTED_CHAPTERS = [
    (1, "உயிரிகளின் இனப்பெருக்கம்", "reproduction-in-organisms", 9, 19),
    (2, "மனித இனப்பெருக்கம்", "human-reproduction", 20, 43),
    (3, "இனப்பெருக்க நலன்", "reproductive-health", 44, 60),
    (4, "மரபுக் கடத்தல் கொள்கைகள் மற்றும் மாறுபாடுகள்", "principles-of-inheritance-and-variation", 61, 80),
    (5, "மூலக்கூறு மரபியல்", "molecular-genetics", 81, 116),
    (6, "பரிணாமம்", "evolution", 117, 141),
    (7, "மனித நலம் மற்றும் நோய்கள்", "human-health-and-diseases", 142, 160),
    (8, "நோய்த்தடைக்காப்பியல்", "immunology", 161, 183),
    (9, "மனித நலனில் நுண்ணுயிரிகள்", "microbes-in-human-welfare", 184, 195),
    (10, "உயிரி தொழில் நுட்பவியலின் பயன்பாடுகள்", "applications-of-biotechnology", 196, 218),
    (11, "உயிரினங்கள் மற்றும் இனக்கூட்டம்", "organisms-and-populations", 219, 244),
    (12, "உயிரிய பல்வகைத்தன்மை மற்றும் அதன் பாதுகாப்பு", "biodiversity-and-its-conservation", 245, 272),
    (13, "சுற்றுச்சூழல் இடர்பாடுகள்", "environmental-issues", 273, 300),
]


class TamilBookManifestTests(unittest.TestCase):
    def load_manifest(self):
        self.assertTrue(MANIFEST.is_file(), f"missing manifest: {MANIFEST}")
        return json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_manifest_has_bookmark_derived_chapter_ranges(self):
        manifest = self.load_manifest()
        actual = [
            (
                chapter["number"],
                chapter["title"],
                chapter["slug"],
                chapter["pdf_start"],
                chapter["pdf_end"],
            )
            for chapter in manifest["chapters"]
        ]
        self.assertEqual(EXPECTED_CHAPTERS, actual)

    def test_manifest_ranges_cover_only_lesson_pages(self):
        chapters = self.load_manifest()["chapters"]
        pages = [
            page
            for chapter in chapters
            for page in range(chapter["pdf_start"], chapter["pdf_end"] + 1)
        ]
        self.assertEqual(list(range(9, 301)), pages)

    def test_immunology_is_a_standalone_tamil_chapter(self):
        slugs = {chapter["slug"] for chapter in self.load_manifest()["chapters"]}
        self.assertIn("immunology", slugs)

    def test_local_ocr_contract_accepts_tamil_and_english(self):
        if not shutil.which("tesseract"):
            raise unittest.SkipTest("tesseract not installed")
        result = subprocess.run(
            [str(PYTHON), str(SCRIPT), "--check-ocr"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("tam", result.stdout.split())
        self.assertIn("eng", result.stdout.split())


class TamilLessonBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not MANIFEST.is_file():
            raise unittest.SkipTest("Tamil manifest must exist before bundle checks")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_every_tamil_chapter_has_searchable_lesson(self):
        for chapter in self.manifest["chapters"]:
            with self.subTest(slug=chapter["slug"]):
                bundle = ROOT / "content.ta" / "docs" / chapter["slug"]
                lesson = bundle / "_index.md"
                self.assertTrue(lesson.is_file())
                lesson_text = lesson.read_text(encoding="utf-8")
                self.assertIn(f"# பாடம் {chapter['number']}: {chapter['title']}", lesson_text)
                self.assertGreater(len(re.findall(r"[\u0b80-\u0bff]", lesson_text)), 100)
                self.assertNotIn("\ufffd", lesson_text)

    def test_every_tamil_referenced_figure_exists(self):
        for chapter in self.manifest["chapters"]:
            with self.subTest(slug=chapter["slug"]):
                bundle = ROOT / "content.ta" / "docs" / chapter["slug"]
                lesson = bundle / "_index.md"
                lesson_text = lesson.read_text(encoding="utf-8")
                figure_refs = re.findall(r'!\[.*?\]\((assets/[^)]+)\)', lesson_text)
                self.assertTrue(len(figure_refs) > 0)
                for ref in figure_refs:
                    img_path = bundle / ref
                    self.assertTrue(img_path.is_file(), f"Missing image {img_path}")

    def test_tamil_audits_remain_conservative(self):
        for chapter in self.manifest["chapters"]:
            with self.subTest(slug=chapter["slug"]):
                audit = ROOT / ".textbook-agent" / f"ta-{chapter['slug']}"
                records = {}
                for name in ("boundaries", "inventory", "coverage", "assets", "review"):
                    path = audit / f"{name}.json"
                    self.assertTrue(path.is_file(), f"missing {path}")
                    records[name] = json.loads(path.read_text(encoding="utf-8"))
                self.assertFalse(records["inventory"]["complete"])
                self.assertFalse(records["review"]["valid"])
                self.assertFalse(records["review"]["teacher_approval"])
                self.assertEqual([], records["review"]["covered_ids"])
                inventory_ids = {item["id"] for item in records["inventory"]["items"]}
                self.assertEqual(inventory_ids, set(records["coverage"]["mapped_ids"]))

    def test_tamil_landing_lists_all_source_chapters(self):
        landing = (ROOT / "content.ta" / "docs" / "_index.md").read_text(encoding="utf-8")
        for chapter in self.manifest["chapters"]:
            self.assertIn(f"./{chapter['slug']}/", landing)
            self.assertIn(chapter["title"], landing)
        self.assertEqual(len(self.manifest["chapters"]), 13)


class TamilMarkdownFormattingTests(unittest.TestCase):
    def test_symbol_only_ocr_lines_do_not_create_blank_list_items(self):
        builder = load_builder_module()
        self.assertEqual("", builder.ocr_text_to_markdown("•\n➢\n>\n*"))


if __name__ == "__main__":
    unittest.main()
