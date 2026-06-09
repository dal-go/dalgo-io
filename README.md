# dalgo-io

Source for **https://dalgo.io** — the landing page for the
[DALgo](https://github.com/dal-go/dalgo) ecosystem.

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
- `public/dtql/` — the DTQL reference pages and examples.

## License

MIT — see `LICENSE`.
