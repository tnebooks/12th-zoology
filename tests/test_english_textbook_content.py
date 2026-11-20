import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".textbook-agent" / "english-book-manifest.json"


EXPECTED_CHAPTERS = [
    (1, "Reproduction in Organisms", "reproduction-in-organisms", 9, 18),
    (2, "Human Reproduction", "human-reproduction", 19, 39),
    (3, "Reproductive Health", "reproductive-health", 40, 52),
    (4, "Principles of Inheritance and Variation", "principles-of-inheritance-and-variation", 53, 65),
    (5, "Molecular Genetics", "molecular-genetics", 66, 96),
    (6, "Evolution", "evolution", 97, 114),
    (7, "Human Health and Diseases", "human-health-and-diseases", 115, 145),
    (8, "Microbes in Human Welfare", "microbes-in-human-welfare", 146, 154),
    (9, "Applications of Biotechnology", "applications-of-biotechnology", 155, 169),
    (10, "Organisms and Populations", "organisms-and-populations", 170, 188),
    (11, "Biodiversity and its Conservation", "biodiversity-and-its-conservation", 189, 208),
    (12, "Environmental Issues", "environmental-issues", 209, 225),
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
        self.assertEqual(list(range(9, 226)), pages)

    def test_immunology_is_not_a_standalone_source_chapter(self):
        chapters = self.load_manifest()["chapters"]
        self.assertNotIn("immunology", {chapter["slug"] for chapter in chapters})


class EnglishLessonBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not MANIFEST.is_file():
            raise unittest.SkipTest("manifest must exist before bundle checks")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_every_chapter_has_lesson_and_source_gallery(self):
        for chapter in self.manifest["chapters"]:
            with self.subTest(slug=chapter["slug"]):
                bundle = ROOT / "content.en" / "docs" / chapter["slug"]
                lesson = bundle / "_index.md"
                gallery = bundle / "source.md"
                self.assertTrue(lesson.is_file())
                self.assertTrue(gallery.is_file())
                lesson_text = lesson.read_text(encoding="utf-8")
                self.assertIn("textbook-source-view:start", lesson_text)
                self.assertIn(f"# Chapter {chapter['number']}: {chapter['title']}", lesson_text)
                self.assertIn(f"PDF pages {chapter['pdf_start']}–{chapter['pdf_end']}", lesson_text)

    def test_source_gallery_has_one_image_for_every_source_page(self):
        for chapter in self.manifest["chapters"]:
            with self.subTest(slug=chapter["slug"]):
                bundle = ROOT / "content.en" / "docs" / chapter["slug"]
                expected_pages = range(chapter["pdf_start"], chapter["pdf_end"] + 1)
                expected_names = {f"source-p{page:03d}.webp" for page in expected_pages}
                actual_names = {path.name for path in (bundle / "assets").glob("source-p*.webp")}
                self.assertEqual(expected_names, actual_names)
                gallery = (bundle / "source.md").read_text(encoding="utf-8")
                for name in expected_names:
                    self.assertIn(f"assets/{name}", gallery)

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
        self.assertNotIn("./immunology/", landing)


if __name__ == "__main__":
    unittest.main()
