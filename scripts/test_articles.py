import unittest

from render_articles import extract_faq, load_articles, parse_front_matter, render_article


SAMPLE = """---
title: Example title
slug: example-title
date: 2026-11-07
description: An example description with a keyword.
summary: A short summary.
order: 1
schema: techarticle
---

A database abstraction layer is a library.

## Before

### Not a question

This heading is not in the FAQ.

## FAQ

### What is a database abstraction layer?

A [database abstraction layer](https://dalgo.io/) keeps **storage** behind one API.

### Can the same code use two stores?

Yes. `dal.DB` is the handle.

## After

This section is not part of the FAQ.
"""


class ArticleSchema(unittest.TestCase):
    def test_existing_articles_keep_the_article_type(self):
        articles = load_articles()
        self.assertGreaterEqual(len(articles), 2)
        for article in articles:
            if article.schema == "techarticle":
                continue
            page = render_article(article, articles)
            self.assertIn('"@type":"Article"', page)
            self.assertNotIn('"@type":"TechArticle"', page)
            self.assertNotIn("BreadcrumbList", page)
            self.assertNotIn("FAQPage", page)

    def test_techarticle_adds_breadcrumb_and_faq(self):
        article = parse_front_matter(SAMPLE, "example.md")
        page = render_article(article, [article])
        self.assertIn('"@type":"TechArticle"', page)
        self.assertIn('"dependencies":"Go"', page)
        self.assertIn("BreadcrumbList", page)
        self.assertIn("https://dalgo.io/articles/", page)
        self.assertIn('"@type":"FAQPage"', page)
        self.assertIn("What is a database abstraction layer?", page)
        self.assertIn("keeps storage behind one API.", page)
        self.assertNotIn("Not a question", page.split("FAQPage", 1)[-1])
        self.assertNotIn("This section is not part of the FAQ.", page.split("FAQPage", 1)[-1])

    def test_faq_extractor_stops_at_the_next_h2(self):
        items = extract_faq(SAMPLE.split("---", 2)[-1])
        self.assertEqual(
            [question for question, _ in items],
            [
                "What is a database abstraction layer?",
                "Can the same code use two stores?",
            ],
        )
        self.assertEqual(items[0][1], "A database abstraction layer keeps storage behind one API.")
        self.assertIn("dal.DB", items[1][1])

    def test_unknown_schema_is_rejected(self):
        text = SAMPLE.replace("schema: techarticle", "schema: blog")
        with self.assertRaises(SystemExit):
            parse_front_matter(text, "example.md")


if __name__ == "__main__":
    unittest.main()
