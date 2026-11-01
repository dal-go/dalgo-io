import json
import re
import unittest
from pathlib import Path
from unittest.mock import patch

import render_site as site
from site_pages import adapter_inventory
from site_shell import TITLES, title


class TopicPages(unittest.TestCase):
    def test_every_topic_has_both_locales_with_unique_metadata(self):
        outputs = site.build()
        for locale in ('en', 'ru'):
            for slug in TITLES:
                path = site.PUBLIC / ('ru' if locale == 'ru' else '') / slug / 'index.html'
                page = outputs[path]
                self.assertIn(f'<html lang="{locale}">', page)
                self.assertEqual(len(re.findall(r'<h1\b', page)), 1, (locale, slug))
                self.assertIn(title(slug, locale), page)
                route = ('/ru/' if locale == 'ru' else '/') + slug + '/'
                self.assertIn(f'<link rel="canonical" href="https://dalgo.io{route}"', page)
                self.assertIn(f'hreflang="ru" href="https://dalgo.io/ru/{slug}/"', page)
                self.assertIn(f'hreflang="en" href="https://dalgo.io/{slug}/"', page)
                nav = re.search(r'<nav class="AppHeader-nav"[^>]*>(.*?)</nav>', page, re.S)[1]
                self.assertEqual(len(re.findall('<a ', nav)), 4)
                self.assertIn('data-theme-switch', page)
                self.assertNotIn('cytoscape', page)

    def test_home_preserves_anchors_and_links_to_each_topic(self):
        outputs = site.build()
        for locale in ('en', 'ru'):
            page = outputs[site.LOCALE_INFO[locale]['out']]
            prefix = '/ru/' if locale == 'ru' else '/'
            for slug in TITLES:
                self.assertIn(f'href="{prefix}{slug}/"', page)
            for anchor in ('adapters', 'typescript', 'quickstart', 'collections', 'interfaces', 'queries'):
                self.assertIn(f'id="{anchor}"', page)
            self.assertIn('dalgo-theme-change', page)
            self.assertIn('diagramStyles()', page)

    def test_sitemap_includes_new_routes_without_previous_generated_files(self):
        planned = {site.PUBLIC / prefix / slug / 'index.html' for prefix in ('', 'ru') for slug in TITLES}
        with patch.object(Path, 'rglob', return_value=iter([])):
            xml = site.sitemap(planned)
        for slug in TITLES:
            self.assertIn(f'<loc>https://dalgo.io/{slug}/</loc>', xml)
            self.assertIn(f'<loc>https://dalgo.io/ru/{slug}/</loc>', xml)

    def test_matrix_keeps_languages_and_runtimes_separate(self):
        inventory = adapter_inventory(site.SRC / 'adapter-status.json')
        self.assertEqual(len(inventory['adapters']), 49)
        self.assertEqual(sum('runtime' in row['typescript'] for row in inventory['adapters']), 36)
        by_id = {row['id']: row for row in inventory['adapters']}
        self.assertEqual(by_id['elasticsearch']['go']['status'], 'bootstrap')
        self.assertEqual(by_id['oracle']['typescript']['status'], 'absent')
        self.assertEqual(by_id['databricks']['typescript']['runtime']['classification'], 'trusted-server-http-default')
        self.assertTrue(by_id['databricks']['typescript']['manifest_private'])
        outputs = site.build()
        page = outputs[site.PUBLIC / 'adapters/index.html']
        self.assertIn('Node.js / edge: qualification unverified', page)
        self.assertIn('Trusted server · HTTP', page)
        self.assertIn('Browser · local', page)
        self.assertEqual(len(re.findall(r'<tr><th scope="row">', page)), 49)
        self.assertEqual(json.loads(outputs[site.PUBLIC / 'adapters/status.json']), inventory)

    def test_quick_start_has_working_setup_for_both_languages(self):
        page = site.build()[site.PUBLIC / 'quickstart/index.html']
        self.assertIn('go get github.com/dal-go/dalgo', page)
        self.assertIn('npm install @dalgo/core@0.8.1 @dalgo/indexeddb@0.4.1', page)
        self.assertIn('await import(', page)
        self.assertIn('runReadwriteTransaction', page)
        self.assertNotIn('{{', page)

    def test_manual_pages_and_generated_articles_share_the_theme(self):
        outputs = site.build()
        for path in ('privacy/index.html', 'tugql/index.html', 'tugql/examples/index.html'):
            self.assertIn('data-theme-switch', outputs[site.PUBLIC / path])
        from render_articles import load_articles, render_article
        articles = load_articles()
        for article in articles:
            self.assertIn('data-theme-switch', render_article(article, articles))


if __name__ == '__main__':
    unittest.main()
