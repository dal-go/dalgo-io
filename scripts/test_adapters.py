import unittest

from render_adapters import load_adapter_pages, parse_front_matter, render_adapter


SAMPLE = """---
title: Example adapter
slug: example-adapter
date: 2026-11-25
description: An example description with a keyword that is long enough for the contract.
summary: A short summary.
order: 1
schema: techarticle
repo: https://github.com/dal-go/dalgo2sqlite
matrix: example
---

An adapter is a driver.

## FAQ

### What is this adapter?

A [database adapter](https://dalgo.io/) talks to one store.
"""


class AdapterPages(unittest.TestCase):
    def test_techarticle_adds_breadcrumb_and_repo(self):
        page = parse_front_matter(SAMPLE, "example.md")
        html = render_adapter(page, [page])
        self.assertIn('"@type":"TechArticle"', html)
        self.assertIn('"dependencies":"Go"', html)
        self.assertIn("BreadcrumbList", html)
        self.assertIn("https://dalgo.io/adapters/", html)
        self.assertIn("https://github.com/dal-go/dalgo2sqlite", html)
        self.assertIn('"@type":"FAQPage"', html)
        self.assertIn("What is this adapter?", html)

    def test_published_pages_are_techarticle(self):
        pages = load_adapter_pages()
        self.assertGreaterEqual(len(pages), 1)
        for page in pages:
            html = render_adapter(page, pages)
            if page.schema == "techarticle":
                self.assertIn('"@type":"TechArticle"', html)
                self.assertIn("BreadcrumbList", html)
            self.assertIn(page.canonical, html)
            self.assertIn(page.repo, html)

    def test_unknown_schema_is_rejected(self):
        text = SAMPLE.replace("schema: techarticle", "schema: blog")
        with self.assertRaises(SystemExit):
            parse_front_matter(text, "example.md")

    def test_repo_must_be_github(self):
        text = SAMPLE.replace("https://github.com/dal-go/dalgo2sqlite", "https://example.com/repo")
        with self.assertRaises(SystemExit):
            parse_front_matter(text, "example.md")


if __name__ == "__main__":
    unittest.main()
