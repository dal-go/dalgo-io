# dalgo-io

Source for **https://dalgo.io** — the landing page for the
[DALgo](https://github.com/dal-go/dalgo) ecosystem.

## DALgo in DataTug development

In [DataTug](https://datatug.app), DALgo provides a data-access seam in the development ecosystem. Read [how DataTug’s development tools were built](https://datatug.app/en/under-the-hood/tools-we-built/).

## Stack

Plain static HTML + CSS. No build step. Everything served to the browser lives
in `public/`. Deployed as a **CloudFlare Worker with static assets** — see
[`DEPLOY.md`](./DEPLOY.md).

## Local preview

```sh
wrangler dev          # serves public/ exactly as CloudFlare will
# or any static server:
python3 -m http.server 8000 --directory public
```

## Editing

- `public/index.html` — page content and structure.
- `public/styles.css` — design system: fonts, colors, layout, motion.
- `public/tugql/` — the TugQL reference pages and examples.
- `public/dtql/` — a static redirect stub for the former location (index.html to /tugql/, schema.json is a `$ref` to the TugQL schema).

## License

MIT — see `LICENSE`.
