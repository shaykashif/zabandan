# Deploying zabandan.shaykas.com

The site is static: `python scripts/build_site.py` writes everything to `site/`. shaykas.com's
DNS is on Cloudflare, so Cloudflare Pages is the simplest host. It serves `site/` and attaches
the subdomain without any manual DNS records.

## First time

1. Build the site:
   ```bash
   python scripts/build_site.py
   ```
2. Log in to Cloudflare from this machine (opens a browser):
   ```bash
   npx wrangler login
   ```
3. Create the Pages project:
   ```bash
   npx wrangler pages project create zabandan --production-branch main
   ```
4. Upload the site:
   ```bash
   npx wrangler pages deploy site --project-name zabandan --branch main
   ```
   It prints a `*.zabandan.pages.dev` address; check the site there first.
5. Attach the subdomain: Cloudflare dashboard → Workers & Pages → **zabandan** → Custom domains →
   Set up a custom domain → `zabandan.shaykas.com`. Because shaykas.com is on the same
   Cloudflare account, it creates the CNAME record itself. HTTPS is ready within a few minutes.

## After adding or changing poems

```bash
python scripts/annotate_poem.py <poem>
python scripts/build_site.py
npx wrangler pages deploy site --project-name zabandan --branch main
```

## What's in `site/`

- `index.html`: the list of poems and the search
- `<poem>/index.html`: one reader page per poem, at `/<poem>/`
- `assets/`: stylesheet, scripts, favicon and the Aktiv Grotesk fonts (copied from shaykas.com,
  since a subdomain can't load the main site's fonts without CORS headers)
- `_headers`: Cloudflare Pages caching rules. Asset URLs carry a content hash, so they're cached
  for a year
- `404.html`, `sitemap.xml`, `robots.txt`

## Poems still in copyright

A nazm's data file (`data/nazms/<poem>.yaml`) can set `publish: false`; `build_site.py` then
leaves it out (use `--include-unpublished --out site_preview` to read it locally, and never
deploy that folder). Poems that are published carry a `citation` and `copyright` line, shown at
the foot of the page. *Kabhī Kabhī* (Sahir Ludhianvi, d. 1980) is published this way.

## Before going public

- **Transliteration rights.** The ghazal's Roman lines come from Rekhta (via the
  `urdu_ghazals_rekhta` scrape). Ghalib's Urdu is public domain, but Rekhta's transliteration
  is their editorial work. Either get Rekhta's permission or have the model write the
  transliteration, as it already does for nazms.
- **Review.** Nothing has been checked by a person yet. Known issue: in ghazal couplet 5,
  DeepSeek misreads who writes the letter.
