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

    def test_ru_path_relies_on_auto_trailing_slash_config(self):
        # The Worker uses html_handling "auto-trailing-slash": /ru redirects to /ru/
        # because public/ru/index.html exists. This asserts the config only; the live
        # 307 was checked once by hand with `wrangler dev`.
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
        for page, rw in ((EN, "Read-write: "), (RU, "Чтение и запись: ")):
            m = re.search(re.escape(rw) + r"(.*?)\. ", page)
            self.assertIn("@dalgo/sqlite-wasm", m.group(1))
            self.assertIn("@dalgo/indexeddb", m.group(1))
            for ro in ("ovdb", "bigquery", "d1", "http"):
                self.assertNotIn(f"@dalgo/{ro}<", m.group(1))
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

    def test_published_film_is_the_right_one_per_locale(self):
        video = rs.load_json(rs.SRC / "video.json")
        self.assertTrue(video["enabled"])
        ids = {"en": "wtkqlcjfzQA", "ru": "ekU0IUfgkGY"}
        durations = {"en": "1:45", "ru": "1:57"}
        for loc, page in (("en", EN), ("ru", RU)):
            other = next(v for k, v in ids.items() if k != loc)
            with self.subTest(locale=loc):
                self.assertEqual(video["locales"][loc]["youtubeId"], ids[loc])
                self.assertIn(f'data-video-id="{ids[loc]}"', page)
                self.assertNotIn(other, page)  # never the other language's film
                self.assertIn(f'<img src="/video/poster-{loc}.webp" width="1280" height="720"', page)
                self.assertIn(f'<span class="film-duration" aria-hidden="true">{durations[loc]}</span>', page)
                self.assertIn(f'lang="{loc}" aria-label="', page)
                self.assertIn(durations[loc], re.search(r'class="film-play"[^>]*aria-label="([^"]+)"', page).group(1))
                self.assertNotIn("<iframe", page)  # created on click only
                self.assertNotRegex(page, r"(?i)(https?:)?//[^\s\"']*(youtube|ytimg|googlevideo)")
                self.assertIn('<script src="/video.js" defer></script>', page)
                poster = ROOT / "public" / "video" / f"poster-{loc}.webp"
                self.assertEqual(poster.read_bytes()[:4], b"RIFF")
        js = (ROOT / "public" / "video.js").read_text(encoding="utf-8")
        self.assertIn("https://www.youtube-nocookie.com/embed/", js)
        self.assertNotIn("youtube.com/", js.replace("youtube-nocookie.com", ""))

    def test_disabled_renders_no_film_and_no_youtube(self):
        video = copy.deepcopy(rs.load_json(rs.SRC / "video.json"))
        video["enabled"] = False
        for page in self.render(video).values():
            self.assertNotIn('id="film"', page)
            self.assertNotIn("video.js", page)
            self.assertNotRegex(page, r"(?i)youtube|ytimg|googlevideo")

    def test_enabled_without_both_ids_is_refused(self):
        video = copy.deepcopy(rs.load_json(rs.SRC / "video.json"))
        video["enabled"] = True
        video["locales"]["ru"]["youtubeId"] = ""
        with self.assertRaises(SystemExit):
            self.render(video)


if __name__ == "__main__":
    unittest.main()
