import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".textbook-agent" / "english-book-manifest.json"


EXPECTED_CHAPTERS = [
    (1, "Reproduction in Organisms", "reproduction-in-organisms", 9, 18),
    (2, "Human Reproduction", "human-reproduction", 19, 39),
    (3, "Reproductive Health", "reproductive-health", 40, 52),
    (4, "Principles of Inheritance and Variation", "principles-of-inheritance-and-variation", 53, 68),
    (5, "Molecular Genetics", "molecular-genetics", 69, 99),
    (6, "Evolution", "evolution", 100, 119),
    (7, "Human Health and Diseases", "human-health-and-diseases", 120, 136),
    (8, "Immunology", "immunology", 137, 155),
    (9, "Microbes in Human Welfare", "microbes-in-human-welfare", 156, 164),
    (10, "Applications of Biotechnology", "applications-of-biotechnology", 165, 183),
    (11, "Organisms and Populations", "organisms-and-populations", 184, 204),
    (12, "Biodiversity and its Conservation", "biodiversity-and-its-conservation", 205, 226),
    (13, "Environmental Issues", "environmental-issues", 227, 249),
]


class EnglishBookManifestTests(unittest.TestCase):
    def load_manifest(self):
        self.assertTrue(MANIFEST.is_file(), f"missing manifest: {MANIFEST}")
        return json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_manifest_has_verified_ordered_chapter_ranges(self):
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

    def test_manifest_ranges_are_contiguous_and_cover_lesson_pages(self):
        chapters = self.load_manifest()["chapters"]
        pages = [
            page
            for chapter in chapters
            for page in range(chapter["pdf_start"], chapter["pdf_end"] + 1)
        ]
        self.assertEqual(list(range(9, 250)), pages)

    def test_immunology_is_a_standalone_source_chapter(self):
        chapters = self.load_manifest()["chapters"]
        self.assertIn("immunology", {chapter["slug"] for chapter in chapters})


class EnglishLessonBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not MANIFEST.is_file():
            raise unittest.SkipTest("manifest must exist before bundle checks")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_every_chapter_has_lesson(self):
        for chapter in self.manifest["chapters"]:
            with self.subTest(slug=chapter["slug"]):
                bundle = ROOT / "content.en" / "docs" / chapter["slug"]
                lesson = bundle / "_index.md"
                self.assertTrue(lesson.is_file())
                lesson_text = lesson.read_text(encoding="utf-8")
                self.assertIn(f"# Chapter {chapter['number']}: {chapter['title']}", lesson_text)
                self.assertNotIn("\ufffd", lesson_text)

    def test_every_referenced_figure_exists(self):
        for chapter in self.manifest["chapters"]:
            with self.subTest(slug=chapter["slug"]):
                bundle = ROOT / "content.en" / "docs" / chapter["slug"]
                lesson = bundle / "_index.md"
                lesson_text = lesson.read_text(encoding="utf-8")
                figure_refs = re.findall(r'!\[.*?\]\((assets/[^)]+)\)', lesson_text)
                self.assertTrue(len(figure_refs) > 0)
                for ref in figure_refs:
                    img_path = bundle / ref
                    self.assertTrue(img_path.is_file(), f"Missing image {img_path}")

    def test_every_chapter_has_consistent_audit_records(self):
        for chapter in self.manifest["chapters"]:
            with self.subTest(slug=chapter["slug"]):
                audit = ROOT / ".textbook-agent" / chapter["slug"]
                records = {}
                for name in ("boundaries", "inventory", "coverage", "assets", "review"):
                    path = audit / f"{name}.json"
                    self.assertTrue(path.is_file(), f"missing {path}")
                    records[name] = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(self.manifest["source"]["sha256"], records["boundaries"]["source_pdf_sha256"])
                self.assertEqual(chapter["pdf_start"], records["boundaries"]["pdf_start"])
                self.assertEqual(chapter["pdf_end"], records["boundaries"]["pdf_end"])
                self.assertFalse(records["review"]["teacher_approval"])
                inventory_ids = {item["id"] for item in records["inventory"]["items"]}
                covered_ids = set(records["coverage"]["mapped_ids"])
                self.assertEqual(inventory_ids, covered_ids)

    def test_english_landing_page_lists_only_verified_source_chapters(self):
        landing = (ROOT / "content.en" / "docs" / "_index.md").read_text(encoding="utf-8")
        for chapter in self.manifest["chapters"]:
            self.assertIn(f"./{chapter['slug']}/", landing)
        self.assertEqual(len(self.manifest["chapters"]), 13)


if __name__ == "__main__":
    unittest.main()
