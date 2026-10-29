# dalgo-io

Source for **https://dalgo.io** — the landing page for the
[DALgo](https://github.com/dal-go/dalgo) ecosystem.

## DALgo in DataTug development

In [DataTug](https://datatug.app), DALgo provides a data-access seam in the development ecosystem. Read [how DataTug’s development tools were built](https://datatug.app/en/under-the-hood/tools-we-built/).

## Stack

Static HTML + CSS. No production build: everything served to the browser lives
in `public/`, and the generated pages are committed (see "Landing pages in two
languages" below). Deployed as a **CloudFlare Worker with static assets** — see
[`DEPLOY.md`](./DEPLOY.md).

## Local preview

```sh
wrangler dev          # serves public/ exactly as CloudFlare will
# or any static server:
python3 -m http.server 8000 --directory public
```

## Editing

- `content/site/` — the landing page in English and Russian (see below). **Do not edit `public/index.html` or `public/ru/index.html` by hand.**
- `public/styles.css` — design system: fonts, colors, layout, motion.
- `public/tugql/` — the TugQL reference pages and examples.
- `public/dtql/` — a static redirect stub for the former location (index.html to /tugql/, schema.json is a `$ref` to the TugQL schema).
- `content/articles/*.md` — one Markdown file per article (title, date, description, and summary in front matter).
- `public/articles/` — the generated article index and pages. Regenerate after editing Markdown:

```sh
python3 scripts/render_articles.py
python3 scripts/render_articles.py --check   # fails if public/articles is stale
```

The renderer is dependency-free. It understands the subset the articles use: headings, lists, fenced code, tables, blockquotes, links, bold, italics, and inline code. Deploy still serves `public/` with no build step; commit the generated HTML with the Markdown.

## Landing pages in two languages (EN `/`, RU `/ru/`)

The landing page is hand-written HTML, so one template feeds both locales and a
small dependency-free generator (`scripts/render_site.py`, in the style of the
article renderer) fills it. This keeps one source of truth per string and keeps
the code samples, which are identical in both languages, in one place.

| File | Holds |
| --- | --- |
| `content/site/index.template.html` | The page: markup, code samples, diagram script. Every translatable string is a `{{key}}` placeholder. |
| `content/site/en.json`, `content/site/ru.json` | One catalog per locale. The generator fails if the key sets differ or a key is unused. Strings are plain HTML (inline `<code>`, links). |
| `content/site/adapters.json` | Adapter names, URLs and import paths, shared by both locales (descriptions live in the catalogs). |
| `content/site/video.json` | The film slot (below). |

```sh
python3 scripts/render_site.py           # writes public/index.html, public/ru/index.html, public/sitemap.xml
python3 scripts/render_site.py --check   # CI: fails if the committed pages are stale
python3 -m unittest discover -s scripts -p 'test_*.py'
```

Both pages carry `<html lang>`, a canonical URL, reciprocal `hreflang`
(`en`, `ru`, `x-default` = English), Open Graph per locale and an EN/RU switch in
the header. `/ru` redirects to `/ru/` (Cloudflare `auto-trailing-slash`). The
articles, TugQL and privacy pages are English only for now; the Russian page
marks those links "(англ.)". The adapter list follows the adapter audit
(dal-go/backstage `video/swap-the-adapter/data/adapters.md`): cards are the
adapters that pass the shared conformance suite, the rest are listed with their
limits. Update `adapters.json` and both catalogs together when that audit changes.

### Film slot (disabled until the video IDs exist)

The DALgo film ("Swap the adapter") goes into its own section after the hero. It
is a click-to-load YouTube poster: the page ships a local poster and a button, and
nothing is requested from YouTube until the visitor presses play (then a
`youtube-nocookie.com` iframe replaces the button; see `public/video.js`).

To turn it on, edit `content/site/video.json`:

```json
{
  "enabled": true,
  "locales": {
    "en": { "youtubeId": "<11-char id of the English film>", "poster": "/video/poster-en.svg", "width": 1280, "height": 720 },
    "ru": { "youtubeId": "<11-char id of the Russian film>", "poster": "/video/poster-ru.svg", "width": 1280, "height": 720 }
  }
}
```

Then replace `public/video/poster-en.svg` / `poster-ru.svg` (placeholders) with the
real 16:9 posters (keep `width`/`height` equal to the file's size so the box does
not shift), review the `video.*` strings in `en.json` / `ru.json`, and run
`python3 scripts/render_site.py`. Setting `enabled` to `true` without both ids
makes the generator fail; leaving it `false` emits no film markup and no script.

## License

MIT — see `LICENSE`.
