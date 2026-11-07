"""Published pages keep titles, descriptions, canonical URLs, and llms.txt."""

import html
import re
import unittest
from pathlib import Path

import render_site as site
from render_articles import load_articles
from seo import GO_LICENSE, GO_REPO, TS_LICENSE, TS_REPO, plain

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
CLAIM = re.compile(r"open[\s-]*source|\bMIT\b|licen[cs]e", re.I)


def route_of(path: Path) -> str:
    rel = path.relative_to(PUBLIC).parent.as_posix()
    return "/" if rel == "." else f"/{rel}/"


def pages():
    for path in sorted(PUBLIC.rglob("index.html")):
        text = path.read_text(encoding="utf-8")
        if "<html" not in text:
            continue
        yield route_of(path), text


def meta(text: str, name: str) -> str:
    match = re.search(rf'<meta name="{name}" content="([^"]*)"', text)
    if not match:
        raise AssertionError(f"missing meta {name}")
    return html.unescape(match.group(1))


def hreflang(text: str) -> dict[str, str]:
    found = {}
    for tag in re.findall(r"<link [^>]*>", text):
        if 'rel="alternate"' not in tag or "hreflang=" not in tag:
            continue
        lang = re.search(r'hreflang="([^"]+)"', tag).group(1)
        found[lang] = re.search(r'href="([^"]+)"', tag).group(1)
    return found


class PublishedSeo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = site.build()
        cls.rendered = {route_of(path): text for path, text in cls.outputs.items() if path.name == "index.html" and "<html" in text}

    def test_every_html_page_has_title_description_and_canonical(self):
        titles = []
        descriptions = []
        for route, text in pages():
            with self.subTest(route=route):
                if route in self.rendered:
                    self.assertEqual(text, self.rendered[route], "run scripts/render_site.py")
                title = html.unescape(re.search(r"<title>(.*?)</title>", text, re.S).group(1)).strip()
                description = meta(text, "description")
                canonical = re.search(r'<link rel="canonical" href="([^"]+)"', text)
                self.assertTrue(title, route)
                self.assertGreaterEqual(len(description), 70, route)
                self.assertGreaterEqual(len(description), 120, route)
                self.assertLessEqual(len(description), 160, route)
                self.assertIsNotNone(canonical, route)
                self.assertEqual(canonical.group(1), f"https://dalgo.io{route}")
                titles.append(title)
                descriptions.append(description)
        self.assertEqual(len(titles), len(set(titles)))
        self.assertEqual(len(descriptions), len(set(descriptions)))
        self.assertGreaterEqual(len(titles), 20)

    def test_language_pairs_are_reciprocal_and_english_only_pages_are_not(self):
        rendered = dict(pages())
        for route in list(rendered):
            if route.startswith("/ru/"):
                continue
            russian = "/ru/" if route == "/" else f"/ru{route}"
            if russian in rendered:
                for each in (route, russian):
                    alt = hreflang(rendered[each])
                    self.assertEqual(alt.get("en"), f"https://dalgo.io{route}", each)
                    self.assertEqual(alt.get("ru"), f"https://dalgo.io{russian}", each)
                    self.assertEqual(alt.get("x-default"), f"https://dalgo.io{route}", each)
            else:
                self.assertNotIn('hreflang="ru"', rendered[route], route)

    def test_home_and_landing_json_ld(self):
        for route in ("/", "/ru/"):
            text = dict(pages())[route]
            self.assertIn('"@type":"Organization"', text)
            self.assertIn('"@type":"WebSite"', text)
            self.assertIn('"@type":"SoftwareSourceCode"', text)
            self.assertIn(GO_REPO, text)
            self.assertIn(TS_REPO, text)
            self.assertIn(GO_LICENSE, text)
            self.assertIn(TS_LICENSE, text)
        landing = [route for route in dict(pages()) if route not in ("/", "/ru/") and not route.startswith("/articles/")]
        self.assertIn("/privacy/", landing)
        self.assertIn("/tugql/", landing)
        self.assertIn("/tugql/examples/", landing)
        for route in landing:
            self.assertIn("BreadcrumbList", dict(pages())[route], route)
        self.assertIn("BreadcrumbList", dict(pages())["/articles/"])

    def test_llms_files_are_generated_and_link_the_repos(self):
        for name in ("llms.txt", "llms-full.txt"):
            path = PUBLIC / name
            self.assertTrue(path.is_file(), name)
            self.assertEqual(path.read_text(encoding="utf-8"), self.outputs[path])
        text = (PUBLIC / "llms.txt").read_text(encoding="utf-8")
        full = (PUBLIC / "llms-full.txt").read_text(encoding="utf-8")
        for url in (
            "https://dalgo.io/",
            "https://dalgo.io/ru/",
            "https://dalgo.io/go/",
            "https://dalgo.io/ru/go/",
            "https://dalgo.io/typescript/",
            "https://dalgo.io/ru/typescript/",
            "https://dalgo.io/adapters/",
            "https://dalgo.io/ru/adapters/",
            "https://dalgo.io/articles/",
            GO_REPO,
            TS_REPO,
            "https://github.com/dal-go/dalgo-http-adapters",
            GO_LICENSE,
            TS_LICENSE,
        ):
            self.assertIn(url, text, url)
        self.assertIn(f"[open-source]({GO_REPO})", text)
        for article in load_articles():
            self.assertIn(article.canonical, full)
            self.assertIn(article.title, full)
        self.assertIn("https://github.com/dal-go/dalgo2sqlite", text)
        for document in (text, full):
            for match in CLAIM.finditer(document):
                window = document[max(0, match.start() - 120) : match.end() + 160]
                self.assertRegex(window, r"\]\(https://github.com/dal-go/")

    def test_robots_allows_every_crawler_and_lists_the_sitemap(self):
        robots = (PUBLIC / "robots.txt").read_text(encoding="utf-8")
        self.assertRegex(robots, r"User-agent:\s*\*")
        self.assertRegex(robots, r"Allow:\s*/")
        self.assertNotRegex(robots, r"Disallow:\s*/")
        self.assertIn("Sitemap: https://dalgo.io/sitemap.xml", robots)

    def test_redirect_stub_is_not_a_document(self):
        stub = (PUBLIC / "dtql" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("<html", stub)
        self.assertIn('url=/tugql/', stub)

    def test_generator_strips_markup_from_catalog_copy(self):
        self.assertNotIn("<", plain("Use <code>dal.DB</code> &amp; adapters"))


if __name__ == "__main__":
    unittest.main()
