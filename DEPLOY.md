# Deploying dalgo.io to CloudFlare

This site is a static landing page served from `public/`. It deploys as a
**CloudFlare Worker with static assets** — the current model, *not* the
deprecated standalone CloudFlare Pages product.

There is no Worker script and no build step: the Worker is assets-only.

## Files

```
dalgo-io/
├── public/            ← everything served to the browser
│   ├── index.html
│   ├── styles.css
│   └── dtql/          ← DTQL reference pages + examples
└── wrangler.jsonc     ← Worker + assets config
```

## One-time setup

1. Install Wrangler (CLI) and authenticate:
   ```sh
   npm install -g wrangler        # or use `npx wrangler ...` per-command
   wrangler login                 # opens browser, authorizes your CF account
   ```

2. (Optional) Confirm the account/config:
   ```sh
   wrangler whoami
   ```

## Preview locally

```sh
wrangler dev
```
Serves the `public/` directory at `http://localhost:8787` exactly as CloudFlare will.

## Deploy

From the `dalgo-io/` directory:

```sh
wrangler deploy
```

This uploads `public/` and publishes the Worker. The first deploy prints a
`*.workers.dev` URL you can use to verify before attaching the domain.

## Attach the custom domain (dalgo.io)

Custom domains require the domain to be on CloudFlare (its nameservers pointed
at CloudFlare). Two ways:

**Dashboard (simplest):**
1. CloudFlare Dashboard → **Workers & Pages** → `dalgo-io` → **Settings** → **Domains & Routes**.
2. **Add** → **Custom Domain** → enter `dalgo.io` (and `www.dalgo.io` if wanted).
3. CloudFlare provisions the DNS record + TLS automatically. SSL is ready within a minute or two.

**Or declare it in `wrangler.jsonc`** and let `wrangler deploy` manage it — add:
```jsonc
"routes": [
  { "pattern": "dalgo.io", "custom_domain": true }
]
```
then run `wrangler deploy` again.

## Notes

- `not_found_handling: "404-page"` serves the page for unknown paths; it avoids
  leaking a default error page.
- No secrets, no environment variables, no KV/D1 bindings are needed.
- To roll back, redeploy a previous commit, or use **Deployments** in the
  dashboard to revert to an earlier version.
