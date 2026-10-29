#!/usr/bin/env python3
"""Render content/articles/*.md into static pages under public/articles/.

The site has no production build. Author one Markdown file per article, run
this script, and commit the generated HTML with the source. `--check` fails
when the committed pages drift from the sources.

Markdown support is the subset the articles use: ATX headings, paragraphs,
thematic breaks, fenced code, GFM tables, blockquotes, flat lists, links,
bold, italics, and inline code. Raw HTML in Markdown is escaped.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import html
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "content" / "articles"
PUBLIC_ARTICLES = ROOT / "public" / "articles"
SITE = "https://dalgo.io"

FAVICON = (
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' "
    "viewBox='0 0 64 64'><rect width='64' height='64' rx='12' fill='%230d1117'/>"
    "<text x='50%25' y='52%25' text-anchor='middle' dominant-baseline='middle' "
    "font-family='ui-monospace,monospace' font-size='28' font-weight='700' "
    "fill='%232f81f7'>d/</text></svg>"
)


@dataclass(frozen=True)
class Article:
    title: str
    slug: str
    date: dt.date
    description: str
    summary: str
    order: int
    body: str
    source_name: str

    @property
    def url_path(self) -> str:
        return f"/articles/{self.slug}/"

    @property
    def canonical(self) -> str:
        return f"{SITE}{self.url_path}"

    @property
    def iso_date(self) -> str:
        return self.date.isoformat()

    @property
    def display_date(self) -> str:
        return f"{self.date.day} {self.date.strftime('%B')} {self.date.year}"


def parse_front_matter(text: str, name: str) -> Article:
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
    required = ("title", "slug", "date", "description", "summary")
    missing = [key for key in required if not fields.get(key)]
    if missing:
        raise SystemExit(f"{name}: missing {', '.join(missing)}")
    slug = fields["slug"]
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise SystemExit(f"{name}: slug {slug!r} must be lowercase kebab-case")
    try:
        date = dt.date.fromisoformat(fields["date"])
    except ValueError as exc:
        raise SystemExit(f"{name}: date must be YYYY-MM-DD") from exc
    return Article(
        title=fields["title"],
        slug=slug,
        date=date,
        description=fields["description"],
        summary=fields["summary"],
        order=int(fields.get("order") or "0"),
        body=body.strip() + "\n",
        source_name=name,
    )


def load_articles() -> list[Article]:
    paths = sorted(CONTENT_DIR.glob("*.md"))
    if not paths:
        raise SystemExit(f"no articles in {CONTENT_DIR}")
    articles = [parse_front_matter(path.read_text(encoding="utf-8"), path.name) for path in paths]
    slugs = [article.slug for article in articles]
    if len(slugs) != len(set(slugs)):
        raise SystemExit(f"duplicate article slugs: {slugs}")
    articles.sort(key=lambda article: (article.date, article.order, article.slug), reverse=False)
    # Same-day articles follow `order`. Newer dates come first on the index,
    # and within a day the smaller order is the editorial sequence.
    articles.sort(key=lambda article: (-article.date.toordinal(), article.order, article.slug))
    return articles


_INLINE = re.compile(
    r"`([^`\n]+)`"
    r"|\[([^\]]+)\]\(([^)\s]+)\)"
    r"|\*\*([^*]+)\*\*"
    r"|(?<!\*)\*([^*\n]+)\*(?!\*)"
)


def _safe_url(url: str) -> str:
    if url.startswith("/") or url.startswith("https://") or url.startswith("http://") or url.startswith("mailto:"):
        return html.escape(url, quote=True)
    raise SystemExit(f"refusing URL {url!r}; use http(s), mailto, or a root-relative path")


def render_inline(text: str) -> str:
    parts: list[str] = []
    pos = 0
    for match in _INLINE.finditer(text):
        parts.append(html.escape(text[pos : match.start()]))
        if match.group(1) is not None:
            parts.append(f"<code>{html.escape(match.group(1))}</code>")
        elif match.group(2) is not None:
            url = match.group(3)
            rel = ' rel="noopener"' if url.startswith("http://") or url.startswith("https://") else ""
            parts.append(f'<a href="{_safe_url(url)}"{rel}>{render_inline(match.group(2))}</a>')
        elif match.group(4) is not None:
            parts.append(f"<strong>{render_inline(match.group(4))}</strong>")
        else:
            parts.append(f"<em>{render_inline(match.group(5))}</em>")
        pos = match.end()
    parts.append(html.escape(text[pos:]))
    return "".join(parts)


def slugify(text: str) -> str:
    plain = re.sub(r"`([^`]*)`", r"\1", text)
    plain = re.sub(r"[*_\[\]]", "", plain)
    slug = re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")
    return slug or "section"


def render_blocks(markdown: str) -> tuple[str, list[tuple[str, str]]]:
    lines = markdown.replace("\r\n", "\n").split("\n")
    html_parts: list[str] = []
    toc: list[tuple[str, str]] = []
    used_ids: dict[str, int] = {}
    i = 0

    def unique_id(base: str) -> str:
        count = used_ids.get(base, 0)
        used_ids[base] = count + 1
        return base if count == 0 else f"{base}-{count + 1}"

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("```"):
            lang = line[3:].strip()
            i += 1
            buf: list[str] = []
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            if i >= len(lines):
                raise SystemExit("unclosed code fence")
            i += 1
            names = {
                "go": ("example.go", "Go"),
                "ts": ("example.ts", "TypeScript"),
                "sql": ("query.sql", "SQL"),
                "text": ("text", "Text"),
            }
            name, badge = names.get(lang, (lang or "text", lang or "text"))
            code = html.escape("\n".join(buf), quote=False)
            html_parts.append(
                '<div class="codeblock"><div class="codeblock-head">'
                f'<span class="codeblock-name">{html.escape(name)}</span>'
                f'<span class="codeblock-lang">{html.escape(badge)}</span></div>'
                f"<pre><code>{code}</code></pre></div>"
            )
            continue
        if line.startswith("|"):
            rows: list[str] = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i])
                i += 1
            html_parts.append(render_table(rows))
            continue
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            if level < 2 or level > 4 or not line[level : level + 1] == " ":
                raise SystemExit(f"bad heading: {line}")
            text = line[level + 1 :].strip()
            anchor = unique_id(slugify(text))
            if level == 2:
                toc.append((anchor, re.sub(r"`([^`]*)`", r"\1", text)))
            html_parts.append(f'<h{level} id="{anchor}">{render_inline(text)}</h{level}>')
            i += 1
            continue
        if line.strip() == "---":
            html_parts.append("<hr />")
            i += 1
            continue
        if line.startswith(">"):
            quoted: list[str] = []
            while i < len(lines) and lines[i].startswith(">"):
                quoted.append(lines[i][1:].lstrip())
                i += 1
            html_parts.append(f"<blockquote><p>{render_inline(' '.join(quoted))}</p></blockquote>")
            continue
        if re.match(r"[-*] ", line) or re.match(r"\d+\. ", line):
            ordered = bool(re.match(r"\d+\. ", line))
            items: list[str] = []
            while i < len(lines) and (
                re.match(r"[-*] ", lines[i]) if not ordered else re.match(r"\d+\. ", lines[i])
            ):
                item = re.sub(r"^([-*]|\d+\.)\s+", "", lines[i])
                items.append(f"<li>{render_inline(item)}</li>")
                i += 1
            tag = "ol" if ordered else "ul"
            html_parts.append(f"<{tag}>\n" + "\n".join(items) + f"\n</{tag}>")
            continue
        para: list[str] = [line.strip()]
        i += 1
        while i < len(lines) and lines[i].strip() and not _block_start(lines[i]):
            para.append(lines[i].strip())
            i += 1
        html_parts.append(f"<p>{render_inline(' '.join(para))}</p>")
    return "\n".join(html_parts) + "\n", toc


def _block_start(line: str) -> bool:
    return (
        line.startswith("#")
        or line.startswith("```")
        or line.startswith("|")
        or line.startswith(">")
        or line.strip() == "---"
        or bool(re.match(r"[-*] ", line))
        or bool(re.match(r"\d+\. ", line))
    )


def render_table(rows: list[str]) -> str:
    parsed = [[cell.strip() for cell in row.strip().strip("|").split("|")] for row in rows]
    if len(parsed) < 2 or not all(re.fullmatch(r":?-{3,}:?", cell) for cell in parsed[1]):
        raise SystemExit(f"table needs a header and a | --- | separator, got {rows[0]!r}")
    header, body = parsed[0], parsed[2:]
    width = len(header)
    if any(len(row) != width for row in body):
        raise SystemExit("table rows have different column counts")
    head = "".join(f"<th>{render_inline(cell)}</th>" for cell in header)
    body_html = []
    for row in body:
        cells = "".join(f"<td>{render_inline(cell)}</td>" for cell in row)
        body_html.append(f"<tr>{cells}</tr>")
    return (
        '<div class="article-table-wrap"><table class="article-table"><thead><tr>'
        + head
        + "</tr></thead><tbody>"
        + "".join(body_html)
        + "</tbody></table></div>"
    )


def page_shell(*, title: str, description: str, canonical: str, og_type: str, main: str, context_label: str, context_href: str, extra_head: str = "") -> str:
    desc = html.escape(description, quote=True)
    title_attr = html.escape(title, quote=True)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>{title_attr}</title>
<meta name="description" content="{desc}" />
<link rel="canonical" href="{html.escape(canonical, quote=True)}" />
<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)" />
<meta name="theme-color" content="#0d1117" media="(prefers-color-scheme: dark)" />
<meta property="og:title" content="{title_attr}" />
<meta property="og:description" content="{desc}" />
<meta property="og:type" content="{og_type}" />
<meta property="og:url" content="{html.escape(canonical, quote=True)}" />
{extra_head}<link rel="icon" type="image/svg+xml" href="{FAVICON}" />
<link rel="stylesheet" href="/styles.css" />
<script src="/analytics.js" defer></script>
</head>
<body>

<header class="AppHeader" role="banner">
  <div class="AppHeader-inner">
    <a class="AppHeader-brand" href="/" aria-label="DALgo home">
      <span class="AppHeader-brand-mark" aria-hidden="true">
        <span class="brand-dal">DAL</span><span class="brand-go">go</span>
      </span>
    </a>

    <nav class="AppHeader-context" aria-label="Context">
      <span class="AppHeader-context-slash" aria-hidden="true">/</span>
      <a class="AppHeader-context-item" href="{html.escape(context_href, quote=True)}">{html.escape(context_label)}</a>
    </nav>

    <nav class="AppHeader-nav" aria-label="Primary">
      <a href="/#why">Why</a>
      <a href="/#adapters">Adapters</a>
      <a href="/articles/">Articles</a>
      <a href="/tugql/">TugQL</a>
    </nav>

    <div class="AppHeader-actions">
      <a class="btn btn-default btn-sm" href="https://github.com/dal-go/dalgo" rel="noopener">
        <svg class="octicon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.75.75 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z"/></svg>
        <span>Star</span>
      </a>
    </div>
  </div>
</header>

{main}

<footer class="AppFooter">
  <div class="container AppFooter-inner">
    <ul role="list">
      <li>&copy; <span id="year">2026</span> DALgo contributors</li>
      <li><a href="/">DALgo</a></li>
      <li><a href="/articles/">Articles</a></li>
      <li><a href="/tugql/">TugQL</a></li>
      <li><a href="https://github.com/dal-go/dalgo" rel="noopener">Core repo</a></li>
      <li><a href="https://github.com/dal-go/dalgo/blob/main/LICENSE" rel="noopener">MIT License</a></li>
      <li><a href="/privacy/">Privacy</a></li>
    </ul>
    <span class="AppFooter-tag">Open-source documentation site. No accounts, no advertising.</span>
  </div>
</footer>

<script>document.getElementById('year').textContent = new Date().getFullYear();</script>
<div class="site-feedback"><button type="button" data-feedback-launcher aria-haspopup="dialog" hidden><svg class="feedback-mark" aria-hidden="true" focusable="false" viewBox="0 0 64 64"><rect width="64" height="64" rx="18" fill="#d4ef83"/><path d="M18 46 46 18M20 18h26v26" fill="none" stroke="#202c2a" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/></svg>Suggest an improvement</button></div>
<script id="site-feedback-widget" src="https://improveit.now/widget.js" data-space="ao58m" data-app="53707531c1e1120447e7673109bb6538" data-lang="en" data-color="#0d63e9" data-launcher="hidden" defer></script>
<script src="/feedback.js" defer></script>
</body>
</html>
"""


def render_index(articles: list[Article]) -> str:
    cards = []
    for article in articles:
        cards.append(
            f"""<a class="Box article-card" href="{article.url_path}">
        <time class="article-date" datetime="{article.iso_date}">{html.escape(article.display_date)}</time>
        <h2>{html.escape(article.title)}</h2>
        <p>{html.escape(article.summary)}</p>
      </a>"""
        )
    main = f"""<main id="top">
<section class="hero page-hero">
  <div class="container">
    <div class="hero-eyebrow">Notes from the project</div>
    <h1 class="hero-title"><span class="hero-line">Articles</span></h1>
    <p class="hero-lede">Writing about what DALgo is for, where it fits, and where a database driver is the better tool. Each article is one Markdown file in the site repository.</p>
  </div>
</section>
<section class="section">
  <div class="container article-index">
    <div class="article-list">
      {chr(10).join(cards)}
    </div>
  </div>
</section>
</main>
"""
    return page_shell(
        title="Articles — DALgo",
        description="Articles on why to use DALgo, and when a direct database driver or another tool is the better choice.",
        canonical=f"{SITE}/articles/",
        og_type="website",
        main=main,
        context_label="Articles",
        context_href="/articles/",
    )


def render_article(article: Article, articles: list[Article]) -> str:
    body_html, toc = render_blocks(article.body)
    toc_html = ""
    if toc:
        items = "\n".join(
            f'<li><a href="#{html.escape(anchor)}">{html.escape(label)}</a></li>' for anchor, label in toc
        )
        toc_html = f'<nav class="Box toc" aria-label="On this page"><strong>On this page</strong><ol>{items}</ol></nav>'
    others = [item for item in articles if item.slug != article.slug]
    related = ""
    if others:
        links = "\n".join(
            f'<li><a href="{item.url_path}">{html.escape(item.title)}</a></li>' for item in others
        )
        related = f'<aside class="article-related"><h2>More articles</h2><ul>{links}</ul></aside>'
    json_ld = (
        '{"@context":"https://schema.org","@type":"Article",'
        f'"headline":{json_string(article.title)},'
        f'"description":{json_string(article.description)},'
        f'"datePublished":"{article.iso_date}",'
        f'"dateModified":"{article.iso_date}",'
        f'"mainEntityOfPage":"{article.canonical}",'
        '"author":{"@type":"Organization","name":"DALgo contributors","url":"https://dalgo.io/"},'
        '"publisher":{"@type":"Organization","name":"DALgo","url":"https://dalgo.io/"}}'
    )
    main = f"""<main id="top">
<article class="article">
  <header class="article-header">
    <p class="article-kicker"><a href="/articles/">Articles</a></p>
    <h1>{html.escape(article.title)}</h1>
    <p class="article-meta"><time datetime="{article.iso_date}">{html.escape(article.display_date)}</time></p>
    <p class="article-standfirst">{html.escape(article.summary)}</p>
  </header>
  {toc_html}
  <div class="article-prose">
{body_html}  </div>
  {related}
  <p class="article-source">Source file: <a href="https://github.com/dal-go/dalgo-io/blob/main/content/articles/{html.escape(article.source_name)}"><code>content/articles/{html.escape(article.source_name)}</code></a></p>
</article>
<script type="application/ld+json">{json_ld}</script>
</main>
"""
    return page_shell(
        title=f"{article.title} — DALgo",
        description=article.description,
        canonical=article.canonical,
        og_type="article",
        main=main,
        context_label="Articles",
        context_href="/articles/",
        extra_head=f'<meta property="article:published_time" content="{article.iso_date}" />\n',
    )


def json_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_tree(articles: list[Article], dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    (dest / "index.html").write_text(render_index(articles), encoding="utf-8")
    for article in articles:
        folder = dest / article.slug
        folder.mkdir()
        (folder / "index.html").write_text(render_article(article, articles), encoding="utf-8")


def check_tree(articles: list[Article]) -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        expected = Path(tmp) / "articles"
        render_tree(articles, expected)
        if not PUBLIC_ARTICLES.exists():
            print("public/articles is missing; run scripts/render_articles.py", file=sys.stderr)
            return 1
        failed = False
        expected_files = sorted(path.relative_to(expected).as_posix() for path in expected.rglob("*") if path.is_file())
        actual_files = sorted(
            path.relative_to(PUBLIC_ARTICLES).as_posix() for path in PUBLIC_ARTICLES.rglob("*") if path.is_file()
        )
        if expected_files != actual_files:
            print("article file list drifted:", file=sys.stderr)
            print(" expected:", expected_files, file=sys.stderr)
            print(" actual:  ", actual_files, file=sys.stderr)
            failed = True
        for rel in expected_files:
            if rel not in actual_files:
                continue
            got = (PUBLIC_ARTICLES / rel).read_text(encoding="utf-8")
            want = (expected / rel).read_text(encoding="utf-8")
            if got != want:
                print(f"drift in public/articles/{rel}", file=sys.stderr)
                diff = difflib.unified_diff(
                    got.splitlines(),
                    want.splitlines(),
                    fromfile=f"public/articles/{rel}",
                    tofile=f"rendered/{rel}",
                    lineterm="",
                )
                print("\n".join(list(diff)[:80]), file=sys.stderr)
                failed = True
        if failed:
            print("run: python3 scripts/render_articles.py", file=sys.stderr)
            return 1
    print(f"articles up to date ({len(articles)} pages)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if public/articles is stale")
    args = parser.parse_args()
    articles = load_articles()
    if args.check:
        return check_tree(articles)
    render_tree(articles, PUBLIC_ARTICLES)
    print(f"wrote {len(articles)} articles to {PUBLIC_ARTICLES.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
