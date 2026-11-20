import json
import importlib.util
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".textbook-agent" / "tamil-book-manifest.json"
SCRIPT = ROOT / "scripts" / "build-tamil-textbook.py"
PYTHON = Path(
    "/Users/apple/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
)


def load_builder_module():
    spec = importlib.util.spec_from_file_location("tamil_textbook_builder", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

EXPECTED_CHAPTERS = [
    (1, "உயிரிகளின் இனப்பெருக்கம்", "reproduction-in-organisms", 9, 19),
    (2, "மனித இனப்பெருக்கம்", "human-reproduction", 20, 42),
    (3, "இனப்பெருக்க நலன்", "reproductive-health", 43, 59),
    (4, "மரபுக் கடத்தல் கொள்கைகள் மற்றும் மாறுபாடுகள்", "principles-of-inheritance-and-variation", 60, 75),
    (5, "மூலக்கூறு மரபியல்", "molecular-genetics", 76, 111),
    (6, "பரிணாமம்", "evolution", 112, 133),
    (7, "மனித நலம் மற்றும் நோய்கள்", "human-health-and-diseases", 134, 169),
    (8, "மனித நலனில் நுண்ணுயிரிகள்", "microbes-in-human-welfare", 170, 181),
    (9, "உயிரி தொழில் நுட்பவியலின் பயன்பாடுகள்", "applications-of-biotechnology", 182, 199),
    (10, "உயிரினங்கள் மற்றும் இனக்கூட்டம்", "organisms-and-populations", 200, 223),
    (11, "உயிரிய பல்வகைத்தன்மை மற்றும் அதன் பாதுகாப்பு", "biodiversity-and-its-conservation", 224, 249),
    (12, "சுற்றுச்சூழல் இடர்பாடுகள்", "environmental-issues", 250, 269),
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
        self.assertEqual(list(range(9, 270)), pages)

    def test_immunology_is_not_a_standalone_tamil_chapter(self):
        slugs = {chapter["slug"] for chapter in self.load_manifest()["chapters"]}
        self.assertNotIn("immunology", slugs)

    def test_local_ocr_contract_accepts_tamil_and_english(self):
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

    def test_every_tamil_chapter_has_searchable_lesson_and_source_gallery(self):
        for chapter in self.manifest["chapters"]:
            with self.subTest(slug=chapter["slug"]):
                bundle = ROOT / "content.ta" / "docs" / chapter["slug"]
                lesson = bundle / "_index.md"
                gallery = bundle / "source.md"
                self.assertTrue(lesson.is_file())
                self.assertTrue(gallery.is_file())
                lesson_text = lesson.read_text(encoding="utf-8")
                self.assertIn("textbook-source-view:start", lesson_text)
                self.assertIn(f"# பாடம் {chapter['number']}: {chapter['title']}", lesson_text)
                self.assertGreater(len(re.findall(r"[\u0b80-\u0bff]", lesson_text)), 100)
                self.assertNotIn("\ufffd", lesson_text)

    def test_every_tamil_source_page_has_one_gallery_asset(self):
        for chapter in self.manifest["chapters"]:
            with self.subTest(slug=chapter["slug"]):
                bundle = ROOT / "content.ta" / "docs" / chapter["slug"]
                expected_names = {
                    f"source-p{page:03d}.webp"
                    for page in range(chapter["pdf_start"], chapter["pdf_end"] + 1)
                }
                actual_names = {path.name for path in (bundle / "assets").glob("source-p*.webp")}
                self.assertEqual(expected_names, actual_names)
                gallery = (bundle / "source.md").read_text(encoding="utf-8")
                for name in expected_names:
                    self.assertIn(f"assets/{name}", gallery)

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

    def test_tamil_landing_lists_only_the_twelve_source_chapters(self):
        landing = (ROOT / "content.ta" / "docs" / "_index.md").read_text(encoding="utf-8")
        for chapter in self.manifest["chapters"]:
            self.assertIn(f"./{chapter['slug']}/", landing)
            self.assertIn(chapter["title"], landing)
        self.assertNotIn("./immunology/", landing)


class TamilMarkdownFormattingTests(unittest.TestCase):
    def test_symbol_only_ocr_lines_do_not_create_blank_list_items(self):
        builder = load_builder_module()
        self.assertEqual("", builder.ocr_text_to_markdown("•\n➢\n>\n*"))


if __name__ == "__main__":
    unittest.main()
