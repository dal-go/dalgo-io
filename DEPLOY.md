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

## GitHub Actions production deployment

[Build and deploy website](.github/workflows/deploy.yml) runs for pull requests,
main pushes, and manual dispatches. The build job checks the static entrypoint
and archives `public/` with `wrangler.jsonc` as `site.tar.gz`. No compilation is
needed for this site. The `site-<source SHA>` artifact retains all asset files,
including dotfiles, `_headers`, and `_redirects` when present.

Automatic publication is disabled unless `CLOUDFLARE_DEPLOY_ENABLED` is `true`.
When enabled, only a main push or manual dispatch on main publishes. A separate production
job downloads the artifact from that same run, extracts it, and runs
`npx --yes wrangler@4.135.0 deploy --config wrangler.jsonc`. It does not check out
or rebuild source. The publish job verifies the recorded source SHA and archive
SHA-256 before extracting. The workflow retains artifacts for 14 days and serializes
production deployments.

### CI credentials and activation

Set the GitHub `CLOUDFLARE_API_TOKEN` secret (repository or `production`
environment) to a token authorized to deploy this Worker and its declared
routes in the production Cloudflare account. `CLOUDFLARE_ACCOUNT_ID` is an
optional GitHub variable; the workflow defaults to the public account identifier
`01c8a86fc1064f063eb5dd9d101d7001`. Build jobs do not receive the token.

Automatic production publication is **disabled** until scoped credentials are
configured and the GitHub variable `CLOUDFLARE_DEPLOY_ENABLED` is set to `true`.
First-run activation is **not executed**. Build artifacts remain available
while the publish job is skipped. The landing owner can publish a verified
GitHub build artifact using an authenticated local Wrangler session instead
of copying an account credential into GitHub.

After a verified artifact is published, record the run's source SHA, archive
checksum, Wrangler version receipt, and public routes. Disable the old
Cloudflare Git production build trigger. Do not configure a Cloudflare build
command or rebuild in the publish job.

## Preview locally

```sh
wrangler dev
```
Serves the `public/` directory at `http://localhost:8787` exactly as CloudFlare will.

## Publish a GitHub build artifact

This procedure is **not executed** until a successful build run is available.
Choose a successful main run for the intended source SHA. Download its
`site-<source SHA>` artifact with `gh run download <run-id> --name
site-<source SHA> --dir <empty-release-directory>`, then enter that directory:

```sh
# Replace with the exact source SHA of the successful GitHub build run.
EXPECTED_SOURCE_SHA='<source-sha>'
test "$(cat source-sha.txt)" = "$EXPECTED_SOURCE_SHA"
sha256sum --check site.tar.gz.sha256
# macOS alternative: shasum -a 256 --check site.tar.gz.sha256
tar -xzf site.tar.gz
npx --yes wrangler@4.135.0 deploy --config wrangler.jsonc
```

Use the downloaded assets, Worker code, and configuration together. Do not
rebuild source before publishing this artifact.

## Manual deploy

From the `dalgo-io/` directory:

```sh
npx --yes wrangler@4.135.0 deploy --config wrangler.jsonc
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
- The site has no runtime secrets or KV/D1 bindings. CI publishing uses the
  Cloudflare token described above.
- To roll back, redeploy a previous commit, or use **Deployments** in the
  dashboard to revert to an earlier version.
