import unittest
from pathlib import Path
from render_articles import page_shell

ROOT = Path(__file__).resolve().parents[1]

class FeedbackTests(unittest.TestCase):
    def test_product_routing_on_static_and_generated_pages(self):
        pages = [(str(p.relative_to(ROOT)), p.read_text()) for p in (ROOT / 'public').rglob('*.html') if 'dtql' not in p.parts]
        pages.append(('generator', page_shell(title='Page', description='Page', canonical='https://dalgo.io/articles/example/', og_type='article', main='<main>Content</main>', context_label='Articles', context_href='/articles/')))
        for path, text in pages:
            with self.subTest(path=path):
                self.assertEqual(text.count('https://improveit.now/widget.js'), 1)
                self.assertIn('data-space="ao58m" data-app="53707531c1e1120447e7673109bb6538"', text)
                self.assertIn('data-launcher="hidden"', text)
                self.assertNotRegex(text, r'data-screen|data-url|data-path')
    def test_legacy_redirect_does_not_load_feedback(self):
        self.assertNotIn('improveit', (ROOT / 'public/dtql/index.html').read_text())

if __name__ == '__main__':
    unittest.main()
