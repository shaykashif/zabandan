# Deploying zabandan.shaykas.com

The site is static and committed, built, in `site/`. The Oracle server serves it with nginx
straight from a git checkout, so publishing is: build here, commit, push, pull on the server.

## Publish an update

On this machine:

```bash
python scripts/build_site.py
git add -A && git commit -m "Update site" && git push
```

On the server (MobaXterm):

```bash
/var/www/zabandan/deploy/update.sh
```

## First-time setup on the server (Oracle Linux)

```bash
sudo git clone https://github.com/shaykashif/zabandan.git /var/www/zabandan
sudo chown -R $USER /var/www/zabandan
sudo cp /var/www/zabandan/deploy/nginx-zabandan.conf /etc/nginx/conf.d/zabandan.conf
sudo restorecon -Rv /var/www/zabandan   # SELinux labels, so nginx may read the files
sudo nginx -t && sudo systemctl reload nginx
```

If shaykas.com's nginx server block listens on 443 (Cloudflare "Full" SSL), copy its `listen`
and `ssl_*` lines into the Zabandan block. Check `curl -H "Host: zabandan.shaykas.com"
http://localhost/` returns the home page before switching DNS.

## Switching DNS from the Cloudflare Worker

The site was first served by a Cloudflare Worker, which owns the `zabandan` DNS record. Once
the server is serving it:

1. Remove the Worker and its custom domain: `npx wrangler delete zabandan` (or Cloudflare
   dashboard → Workers & Pages → zabandan → Settings → Delete).
2. Add a DNS record in Cloudflare: type A, name `zabandan`, content the server's IP (the same
   one shaykas.com points to), proxied.

## Adding or changing poems

```bash
python scripts/annotate_poem.py <poem>
python scripts/curate_notes.py <poem>
python scripts/make_og.py        # link-preview image for the new poem
python scripts/build_site.py
```

Then publish as above.

## What's in `site/`

- `index.html`: the list of poems and the search
- `<poem>/index.html`: one reader page per poem, at `/<poem>/`
- `assets/`: stylesheet, scripts, favicon and fonts. Asset URLs carry a content hash
- `404.html`, `sitemap.xml`, `robots.txt` (`_headers` is for Cloudflare and unused by nginx)

## Poems still in copyright

A nazm's data file (`data/nazms/<poem>.yaml`) can set `publish: false`; `build_site.py` then
leaves it out (use `--include-unpublished --out site_preview` to read it locally, and never
publish that folder). Published poems can carry `citation` and `copyright` lines, shown at the
foot of the page. *Kabhī Kabhī* (Sahir Ludhianvi, d. 1980) is published this way.

## Open items

- The ghazal's Roman lines come from Rekhta (via the `urdu_ghazals_rekhta` scrape). Ghalib's
  Urdu is public domain, but Rekhta's transliteration is their editorial work.
- Known issue: in ghazal couplet 5, DeepSeek misreads who writes the letter.
