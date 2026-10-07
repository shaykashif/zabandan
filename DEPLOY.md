# Deploying zabandan.shaykas.com

The site is static: `python scripts/build_site.py` writes it to `site/`. It's served by a
Cloudflare Worker with static assets (`wrangler.jsonc`), which also attaches the
`zabandan.shaykas.com` custom domain and its DNS record on the shaykas.com zone.

## Deploy

```bash
python scripts/build_site.py
npx wrangler deploy
```

The first time, run `npx wrangler login` and approve it in the browser. The Aktiv Grotesk
fonts must be in `site_src/static/fonts/` before building (they're licensed and not in git).

## After adding or changing poems

```bash
python scripts/annotate_poem.py <poem>
python scripts/curate_notes.py <poem>
python scripts/build_site.py
npx wrangler deploy
```

## What's in `site/`

- `index.html`: the list of poems and the search
- `<poem>/index.html`: one reader page per poem, at `/<poem>/`
- `assets/`: stylesheet, scripts, favicon and fonts. Asset URLs carry a content hash, and
  `_headers` caches them for a year
- `404.html` (served for unknown paths), `sitemap.xml`, `robots.txt`

## Poems still in copyright

A nazm's data file (`data/nazms/<poem>.yaml`) can set `publish: false`; `build_site.py` then
leaves it out (use `--include-unpublished --out site_preview` to read it locally, and never
deploy that folder). Published poems can carry `citation` and `copyright` lines, shown at the
foot of the page. *Kabhī Kabhī* (Sahir Ludhianvi, d. 1980) is published this way.

## Open items

- The ghazal's Roman lines come from Rekhta (via the `urdu_ghazals_rekhta` scrape). Ghalib's
  Urdu is public domain, but Rekhta's transliteration is their editorial work.
- Known issue: in ghazal couplet 5, DeepSeek misreads who writes the letter.
