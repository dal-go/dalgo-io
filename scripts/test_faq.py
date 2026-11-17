import html
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def visible(markup: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", markup))


class FaqPageTest(unittest.TestCase):
    def check(self, path: str, locale: str) -> None:
        page = (ROOT / path).read_text(encoding="utf-8")
        blocks = [json.loads(block) for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)]
        faq = next(block for block in blocks if block.get("@type") == "FAQPage")
        self.assertEqual(faq["inLanguage"], locale)
        self.assertTrue(any(block.get("@type") == "BreadcrumbList" for block in blocks))
        shown = re.findall(r'<section class="faq-item"><h2 id="q\d+">(.*?)</h2><p>(.*?)</p></section>', page, re.S)
        self.assertGreaterEqual(len(shown), 10)
        self.assertLessEqual(len(shown), 15)
        self.assertEqual(
            [(visible(q), visible(a)) for q, a in shown],
            [(item["name"], item["acceptedAnswer"]["text"]) for item in faq["mainEntity"]],
        )
        for other in ("en", "ru"):
            self.assertIn(f'hreflang="{other}"', page)
        self.assertIn('hreflang="x-default"', page)

    def test_english_faq_json_ld_matches_visible_answers(self):
        self.check("public/faq/index.html", "en")

    def test_russian_faq_json_ld_matches_visible_answers(self):
        self.check("public/ru/faq/index.html", "ru")

    def test_faq_is_in_sitemap_and_llms(self):
        sitemap = (ROOT / "public/sitemap.xml").read_text(encoding="utf-8")
        self.assertIn("https://dalgo.io/faq/", sitemap)
        self.assertIn("https://dalgo.io/ru/faq/", sitemap)
        llms = (ROOT / "public/llms.txt").read_text(encoding="utf-8")
        self.assertIn("https://dalgo.io/faq/", llms)
        self.assertIn("https://dalgo.io/ru/faq/", llms)


if __name__ == "__main__":
    unittest.main()
