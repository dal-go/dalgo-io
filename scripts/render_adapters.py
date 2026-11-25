#!/usr/bin/env python3
"""Render content/adapters/*.md into static pages under public/adapters/<slug>/.

Each Markdown file is one per-adapter reference page (dalgo2sqlite, later
dalgo2postgres, and so on). The /adapters/ hub remains the capability matrix
from render_site.py; this script never overwrites that index or status.json.

`--check` fails when a committed adapter page drifts from its source.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from render_articles import (
    extract_faq,
    faq_ld,
    ld_json,
    page_shell,
    render_blocks,
)
ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "content" / "adapters"
PUBLIC_ADAPTERS = ROOT / "public" / "adapters"
SITE = "https://dalgo.io"
HUB_FILES = frozenset({"index.html", "status.json"})


@dataclass(frozen=True)
class AdapterPage:
    title: str
    slug: str
    date: dt.date
    description: str
    summary: str
    order: int
    body: str
    source_name: str
    schema: str
    repo: str
    matrix: str

    @property
    def url_path(self) -> str:
        return f"/adapters/{self.slug}/"

    @property
    def canonical(self) -> str:
        return f"{SITE}{self.url_path}"

    @property
    def iso_date(self) -> str:
        return self.date.isoformat()

    @property
    def display_date(self) -> str:
        return f"{self.date.day} {self.date.strftime('%B')} {self.date.year}"


def parse_front_matter(text: str, name: str) -> AdapterPage:
    if not text.startswith("---\n"):
        raise SystemExit(f"{name}: missing front matter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise SystemExit(f"{name}: unterminated front matter")
    raw = text[4:end]
    body = text[end + 5 :]
    if body.startswith("\n"):
        body = body[1:]
    fields: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            raise SystemExit(f"{name}: bad front-matter line {line!r}")
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"')
    required = ("title", "slug", "date", "description", "summary", "repo")
    missing = [key for key in required if not fields.get(key)]
    if missing:
        raise SystemExit(f"{name}: missing {', '.join(missing)}")
    slug = fields["slug"]
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise SystemExit(f"{name}: slug {slug!r} must be lowercase kebab-case")
    repo = fields["repo"]
    if not repo.startswith("https://github.com/"):
        raise SystemExit(f"{name}: repo must be an https://github.com/ URL, got {repo!r}")
    schema = fields.get("schema", "")
    if schema not in ("", "techarticle"):
        raise SystemExit(f"{name}: schema must be techarticle or omitted, got {schema!r}")
    try:
        date = dt.date.fromisoformat(fields["date"])
    except ValueError as exc:
        raise SystemExit(f"{name}: date must be YYYY-MM-DD") from exc
    return AdapterPage(
        title=fields["title"],
        slug=slug,
        date=date,
        description=fields["description"],
        summary=fields["summary"],
        order=int(fields.get("order") or "0"),
        body=body.strip() + "\n",
        source_name=name,
        schema=schema,
        repo=repo,
        matrix=fields.get("matrix", ""),
    )


def load_adapter_pages() -> list[AdapterPage]:
    paths = sorted(CONTENT_DIR.glob("*.md"))
    if not CONTENT_DIR.exists():
        return []
    pages = [parse_front_matter(path.read_text(encoding="utf-8"), path.name) for path in paths]
    slugs = [page.slug for page in pages]
    if len(slugs) != len(set(slugs)):
        raise SystemExit(f"duplicate adapter slugs: {slugs}")
    matrix_ids = [page.matrix for page in pages if page.matrix]
    if len(matrix_ids) != len(set(matrix_ids)):
        raise SystemExit(f"duplicate adapter matrix ids: {matrix_ids}")
    pages.sort(key=lambda page: (page.order, page.slug))
    return pages


def adapter_guides_by_matrix() -> dict[str, AdapterPage]:
    return {page.matrix: page for page in load_adapter_pages() if page.matrix}


def tech_article_ld(page: AdapterPage) -> str:
    return ld_json(
        {
            "@context": "https://schema.org",
            "@type": "TechArticle",
            "headline": page.title,
            "description": page.description,
            "datePublished": page.iso_date,
            "dateModified": page.iso_date,
            "inLanguage": "en",
            "mainEntityOfPage": page.canonical,
            "dependencies": "Go",
            "codeRepository": page.repo,
            "author": {"@type": "Organization", "name": "DALgo contributors", "url": "https://dalgo.io/"},
            "publisher": {"@type": "Organization", "name": "DALgo", "url": "https://dalgo.io/"},
        }
    )


def breadcrumb_ld(page: AdapterPage) -> str:
    return ld_json(
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "DALgo", "item": "https://dalgo.io/"},
                {"@type": "ListItem", "position": 2, "name": "Adapters", "item": "https://dalgo.io/adapters/"},
                {"@type": "ListItem", "position": 3, "name": page.title, "item": page.canonical},
            ],
        }
    )


def article_ld(page: AdapterPage) -> str:
    return ld_json(
        {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": page.title,
            "description": page.description,
            "datePublished": page.iso_date,
            "dateModified": page.iso_date,
            "mainEntityOfPage": page.canonical,
            "author": {"@type": "Organization", "name": "DALgo contributors", "url": "https://dalgo.io/"},
            "publisher": {"@type": "Organization", "name": "DALgo", "url": "https://dalgo.io/"},
        }
    )


def render_adapter(page: AdapterPage, pages: list[AdapterPage]) -> str:
    body_html, toc = render_blocks(page.body)
    toc_html = ""
    if toc:
        items = "\n".join(
            f'<li><a href="#{html_escape(anchor)}">{html_escape(label)}</a></li>' for anchor, label in toc
        )
        toc_html = f'<nav class="Box toc" aria-label="On this page"><strong>On this page</strong><ol>{items}</ol></nav>'
    others = [item for item in pages if item.slug != page.slug]
    related = ""
    if others:
        links = "\n".join(f'<li><a href="{item.url_path}">{html_escape(item.title)}</a></li>' for item in others)
        related = f'<aside class="article-related"><h2>More adapter pages</h2><ul>{links}</ul></aside>'
    blocks = [tech_article_ld(page) if page.schema == "techarticle" else article_ld(page)]
    if page.schema == "techarticle":
        blocks.append(breadcrumb_ld(page))
    faq = extract_faq(page.body)
    if faq:
        blocks.append(faq_ld(faq))
    json_ld = "\n".join(f'<script type="application/ld+json">{block}</script>' for block in blocks)
    main = f"""<main id="top">
<article class="article">
  <header class="article-header">
    <p class="article-kicker"><a href="/adapters/">Adapters</a></p>
    <h1>{html_escape(page.title)}</h1>
    <p class="article-meta"><time datetime="{page.iso_date}">{html_escape(page.display_date)}</time></p>
    <p class="article-standfirst">{html_escape(page.summary)}</p>
  </header>
  {toc_html}
  <div class="article-prose">
{body_html}  </div>
  {related}
  <p class="article-source">Source file: <a href="https://github.com/dal-go/dalgo-io/blob/main/content/adapters/{html_escape(page.source_name)}"><code>content/adapters/{html_escape(page.source_name)}</code></a></p>
</article>
{json_ld}
</main>
"""
    return page_shell(
        title=f"{page.title} — DALgo",
        description=page.description,
        canonical=page.canonical,
        og_type="article",
        main=main,
        context_label="Adapters",
        context_href="/adapters/",
        extra_head=f'<meta property="article:published_time" content="{page.iso_date}" />\n',
    )


def html_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_tree(pages: list[AdapterPage], dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    expected = {page.slug for page in pages}
    for path in dest.iterdir():
        if path.is_dir() and path.name not in expected:
            stale = path / "index.html"
            if stale.is_file():
                stale.unlink()
            try:
                path.rmdir()
            except OSError:
                pass
    for page in pages:
        out = dest / page.slug
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(render_adapter(page, pages), encoding="utf-8")


def check_tree(pages: list[AdapterPage]) -> int:
    import tempfile
    
    failed = False
    with tempfile.TemporaryDirectory() as tmp:
        expected = Path(tmp)
        render_tree(pages, expected)
        expected_files = {f"{page.slug}/index.html" for page in pages}
        actual_files = {
            path.relative_to(PUBLIC_ADAPTERS).as_posix()
            for path in PUBLIC_ADAPTERS.rglob("index.html")
            if path.is_file() and path.relative_to(PUBLIC_ADAPTERS).as_posix() not in HUB_FILES
        }
        if expected_files != actual_files:
            print("adapter page file list drifted:", file=sys.stderr)
            print(" expected:", sorted(expected_files), file=sys.stderr)
            print(" actual:  ", sorted(actual_files), file=sys.stderr)
            failed = True
        for rel in sorted(expected_files):
            if rel not in actual_files:
                continue
            got = (PUBLIC_ADAPTERS / rel).read_text(encoding="utf-8")
            want = (expected / rel).read_text(encoding="utf-8")
            if got != want:
                print(f"drift in public/adapters/{rel}", file=sys.stderr)
                diff = difflib.unified_diff(
                    got.splitlines(),
                    want.splitlines(),
                    fromfile=f"public/adapters/{rel}",
                    tofile=f"rendered/{rel}",
                    lineterm="",
                )
                print("\n".join(list(diff)[:80]), file=sys.stderr)
                failed = True
    if failed:
        print("run: python3 scripts/render_adapters.py", file=sys.stderr)
        return 1
    print(f"adapter pages up to date ({len(pages)} pages)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if public/adapters/<slug> is stale")
    args = parser.parse_args()
    pages = load_adapter_pages()
    if args.check:
        return check_tree(pages)
    render_tree(pages, PUBLIC_ADAPTERS)
    print(f"wrote {len(pages)} adapter pages to {PUBLIC_ADAPTERS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
