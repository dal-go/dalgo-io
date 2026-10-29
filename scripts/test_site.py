import copy
import re
import unittest
from pathlib import Path

import render_site as rs

ROOT = Path(__file__).resolve().parents[1]
EN = (ROOT / "public" / "index.html").read_text(encoding="utf-8")
RU = (ROOT / "public" / "ru" / "index.html").read_text(encoding="utf-8")
SITEMAP = (ROOT / "public" / "sitemap.xml").read_text(encoding="utf-8")


def links(page: str, rel: str) -> dict[str, str]:
    out = {}
    for tag in re.findall(r"<link [^>]*>", page):
        if f'rel="{rel}"' in tag:
            href = re.search(r'href="([^"]+)"', tag).group(1)
            lang = re.search(r'hreflang="([^"]+)"', tag)
            out[lang.group(1) if lang else ""] = href
    return out


class LandingPages(unittest.TestCase):
    def test_generated_files_match_sources(self):
        for path, text in rs.build().items():
            self.assertEqual(path.read_text(encoding="utf-8"), text, f"{path} is stale: run scripts/render_site.py")

    def test_locales_share_one_key_set(self):
        rs.load_catalogs()  # exits when keys differ

    def test_russian_page_is_russian(self):
        self.assertIn('<html lang="ru">', RU)
        self.assertIn('<html lang="en">', EN)
        self.assertRegex(RU, r"<title>[^<]*слой абстракции баз данных для Go и TypeScript</title>")
        self.assertIn("Один интерфейс.", RU)
        self.assertIn("Быстрый старт", RU)
        self.assertNotIn("Same interface. Different stores.", RU)
        self.assertNotIn("Зачем", EN)
        self.assertIn("database abstraction layer for Go and TypeScript", EN)
        # code stays as it is
        self.assertIn("dalgo2memory", RU)
        self.assertIn("go get github.com/dal-go/dalgo", RU)
        self.assertIn("npm install @dalgo/core", RU)

    def test_switch_works_both_ways(self):
        self.assertRegex(EN, r'<a class="lang-switch-item" href="/ru/" hreflang="ru" lang="ru" data-lang-link>RU</a>')
        self.assertRegex(RU, r'<a class="lang-switch-item" href="/" hreflang="en" lang="en" data-lang-link>EN</a>')
        self.assertIn('aria-current="true" lang="en">EN</span>', EN)
        self.assertIn('aria-current="true" lang="ru">RU</span>', RU)

    def test_hreflang_is_reciprocal_and_canonical(self):
        for name, page, canonical in (("en", EN, "https://dalgo.io/"), ("ru", RU, "https://dalgo.io/ru/")):
            with self.subTest(page=name):
                alt = links(page, "alternate")
                self.assertEqual(alt, {"en": "https://dalgo.io/", "ru": "https://dalgo.io/ru/", "x-default": "https://dalgo.io/"})
                self.assertEqual(links(page, "canonical"), {"": canonical})
                self.assertIn(f'<meta property="og:url" content="{canonical}" />', page)
        self.assertIn('og:locale" content="ru_RU"', RU)
        self.assertIn('og:locale" content="en_US"', EN)
        self.assertEqual(links(EN, "alternate"), links(RU, "alternate"))

    def test_sitemap_lists_both_landing_pages_with_alternates(self):
        for url in ("https://dalgo.io/", "https://dalgo.io/ru/"):
            self.assertIn(f"<loc>{url}</loc>", SITEMAP)
        self.assertEqual(SITEMAP.count('hreflang="ru" href="https://dalgo.io/ru/"'), 2)
        self.assertEqual(SITEMAP.count('hreflang="x-default" href="https://dalgo.io/"'), 2)
        self.assertNotIn("/dtql/", SITEMAP)

    def test_ru_path_is_served_with_trailing_slash(self):
        # The Worker uses html_handling "auto-trailing-slash": /ru redirects to /ru/
        # because public/ru/index.html exists. (Verified live with wrangler dev.)
        config = (ROOT / "wrangler.jsonc").read_text(encoding="utf-8")
        self.assertIn('"html_handling": "auto-trailing-slash"', config)
        self.assertTrue((ROOT / "public" / "ru" / "index.html").is_file())

    def test_adapter_claims_match_the_audit(self):
        for page in (EN, RU):
            self.assertNotIn("github.com/dal-go/dalgo2git", page)  # repo has no adapter code
            self.assertNotIn("dalgo2buntdb", page)  # archived
            self.assertNotIn("dalgo2badger", page)  # archived
            self.assertNotIn("ingitdb-cli/tree/main/pkg/dalgo2ingitdb", page)
            self.assertIn("https://github.com/ingitdb/dalgo2ingitdb", page)
            self.assertIn("https://github.com/dal-go/dalgo/tree/main/dalgotest", page)
            self.assertIn("https://github.com/dal-go/dalgo-http-adapters", page)
            self.assertIn("@dalgo/core", page)
        files = re.search(r"dalgo2files</strong></a> — ([^<]*)", EN).group(1)
        self.assertIn("read-only", files)
        self.assertIn("JSON", files)
        self.assertEqual(len(rs.load_json(rs.SRC / "adapters.json")["cards"]), 11)  # core + 10 suite adapters


class FilmSlot(unittest.TestCase):
    def render(self, video):
        template = (rs.SRC / "index.template.html").read_text(encoding="utf-8")
        catalogs = rs.load_catalogs()
        adapters = rs.load_json(rs.SRC / "adapters.json")
        return {loc: rs.render_page(loc, template, catalogs, adapters, video) for loc in rs.LOCALES}

    def test_disabled_by_default_and_no_youtube_anywhere(self):
        video = rs.load_json(rs.SRC / "video.json")
        self.assertFalse(video["enabled"])
        for page in (EN, RU):
            self.assertNotIn('id="film"', page)
            self.assertNotIn("video.js", page)
            self.assertNotRegex(page, r"(?i)youtube|ytimg|googlevideo")

    def test_enabled_renders_poster_per_locale_without_third_party_requests(self):
        video = copy.deepcopy(rs.load_json(rs.SRC / "video.json"))
        video["enabled"] = True
        video["locales"]["en"]["youtubeId"] = "AAAAAAAAAAA"
        video["locales"]["ru"]["youtubeId"] = "BBBBBBBBBBB"
        pages = self.render(video)
        for loc, vid in (("en", "AAAAAAAAAAA"), ("ru", "BBBBBBBBBBB")):
            page = pages[loc]
            with self.subTest(locale=loc):
                self.assertIn(f'data-video-id="{vid}"', page)
                self.assertIn(f'<img src="/video/poster-{loc}.svg" width="1280" height="720"', page)
                self.assertNotIn("<iframe", page)  # created on click only
                self.assertNotRegex(page, r"(?i)(https?:)?//[^\s\"']*(youtube|ytimg|googlevideo)")
                self.assertIn('<script src="/video.js" defer></script>', page)
        js = (ROOT / "public" / "video.js").read_text(encoding="utf-8")
        self.assertIn("https://www.youtube-nocookie.com/embed/", js)
        self.assertNotIn("youtube.com/", js.replace("youtube-nocookie.com", ""))
        self.assertTrue((ROOT / "public" / "video" / "poster-en.svg").is_file())
        self.assertTrue((ROOT / "public" / "video" / "poster-ru.svg").is_file())

    def test_enabled_without_both_ids_is_refused(self):
        video = copy.deepcopy(rs.load_json(rs.SRC / "video.json"))
        video["enabled"] = True
        video["locales"]["en"]["youtubeId"] = "AAAAAAAAAAA"
        with self.assertRaises(SystemExit):
            self.render(video)


if __name__ == "__main__":
    unittest.main()
