"""Build the static site for zabandan.shaykas.com.

Every poem annotated by the default model (data/annotated/<poem>.<model>.json) gets a
reader page at /<poem>/, and the index lists them all with a search over titles, poets
and the full text in Urdu, Roman and English.

Usage: python scripts/build_site.py [--model deepseek-v4-pro] [--out site]
       python scripts/build_site.py --include-unpublished --out site_preview
Deploy the output folder as-is (see DEPLOY.md). Poems marked "publish: false" in their
source (still in copyright) are left out unless --include-unpublished is given; never
deploy a build made with that flag.
"""

import argparse
import hashlib
import html
import json
import shutil
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "site_src/static"
BASE_URL = "https://zabandan.shaykas.com"
GOOGLE_FONTS = "https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;600&display=swap"
DROP = {"cost", "attempts", "first_line"}

ICON_MOON = ('<svg class="moon" viewBox="0 0 24 24" aria-hidden="true"><path d="M4.77 14.35A7.6 7.6 0 1 0 16.46 5.85A7.37 7.37 0 0 1 4.77 14.35Z"/>'
             '<path d="M16.46 5.85A7.6 7.6 0 0 0 4.77 14.35" stroke-width="1.3" stroke-dasharray="0 2.3"/>'
             '<path d="M20.92 10.21L22.29 9.93M20.95 13.64L21.74 13.79M19.7 16.85L20.38 17.27M17.36 19.36L18.18 20.49M14.24 20.82L14.44 21.59M10.81 21.02L10.71 21.82M7.55 19.94L6.87 21.16" stroke-width="1.1"/></svg>')
ICON_SUN = ('<svg class="sun" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4.2"/>'
            '<path d="M13.94 12.8L11.2 13.94L10.06 11.2L12.8 10.06ZM12.8 13.94L10.06 12.8L11.2 10.06L13.94 11.2Z" stroke-width=".8"/>'
            '<path d="M12 6.4L12 1.4M14.14 6.83L15.21 4.24M15.96 8.04L19.5 4.5M17.17 9.86L19.76 8.79M17.6 12L22.6 12M17.17 14.14L19.76 15.21M15.96 15.96L19.5 19.5M14.14 17.17L15.21 19.76M12 17.6L12 22.6M9.86 17.17L8.79 19.76M8.04 15.96L4.5 19.5M6.83 14.14L4.24 15.21M6.4 12L1.4 12M6.83 9.86L4.24 8.79M8.04 8.04L4.5 4.5M9.86 6.83L8.79 4.24" stroke-width="1.2"/></svg>')

e = html.escape


def cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def json_script(element_id: str, data) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'<script type="application/json" id="{element_id}">{payload}</script>'


# The same Person node shaykas.com publishes, so search engines tie the two sites together.
PERSON = {"@type": "Person", "@id": "https://shaykas.com/#person", "name": "Shay Kashif",
          "alternateName": "Shayaan Kashif", "url": "https://shaykas.com/"}
SITE_ID = BASE_URL + "/#website"


def json_ld(data) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'<script type="application/ld+json">{payload}</script>'


def page(*, title: str, description: str, path: str, body: str, assets: dict, scripts: list[str],
         og_type: str = "website", main_class: str = "", body_class: str = "",
         image: str = "og/site.png", image_alt: str = "Zabandan", ld: dict | None = None) -> str:
    url = BASE_URL + path
    img = f"{BASE_URL}/assets/{image}?v={assets[image]}"
    # The ink animation (assets/ink.js) is switched off for now: it froze part-way on some loads.
    # To bring it back, add "ink.js" to this list and restore the .js-ink head script and the
    # .js-ink rules in site.css (see git history).
    js = "".join(f'<script src="/assets/{s}?v={assets[s]}" defer></script>' for s in scripts)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{e(title)}</title>
  <meta name="description" content="{e(description)}" />
  <link rel="canonical" href="{url}" />
  <meta property="og:title" content="{e(title)}" />
  <meta property="og:description" content="{e(description)}" />
  <meta property="og:type" content="{og_type}" />
  <meta property="og:url" content="{url}" />
  <meta property="og:site_name" content="Zabandan" />
  <meta property="og:locale" content="en_US" />
  <meta property="og:image" content="{img}" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta property="og:image:alt" content="{e(image_alt)}" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{e(title)}" />
  <meta name="twitter:description" content="{e(description)}" />
  <meta name="twitter:image" content="{img}" />
  <meta name="author" content="Shay Kashif" />
  <link rel="icon" type="image/svg+xml" href="/assets/favicon.svg?v={assets['favicon.svg']}" />
  <link rel="icon" type="image/png" sizes="48x48" href="/assets/icons/favicon-48.png?v={assets['icons/favicon-48.png']}" />
  <link rel="apple-touch-icon" sizes="180x180" href="/assets/icons/apple-touch-icon.png?v={assets['icons/apple-touch-icon.png']}" />
  <meta name="color-scheme" content="light dark" />
  <meta name="theme-color" content="#f6f2e6" />
  <script>try{{var t=localStorage.getItem("theme")||(matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light");document.documentElement.dataset.theme=t;if(t==="dark")document.querySelector('meta[name="theme-color"]').content="#151412"}}catch(e){{}}</script>
  <link rel="preload" href="/assets/fonts/aktiv-grotesk-regular.woff2" as="font" type="font/woff2" crossorigin />
  <link rel="preload" href="/assets/fonts/aktiv-grotesk-semibold.woff2" as="font" type="font/woff2" crossorigin />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link rel="stylesheet" href="{GOOGLE_FONTS}" />
  <link rel="stylesheet" href="/assets/site.css?v={assets['site.css']}" />
  {js}
  {json_ld(ld) if ld else ""}
</head>
<body{f' class="{body_class}"' if body_class else ''}>
  <main{f' class="{main_class}"' if main_class else ''}>
{body}
  </main>
  <div class="corner">
    <button class="theme" type="button" aria-label="Switch to dark mode" title="Dark mode">{ICON_MOON}{ICON_SUN}</button>
  </div>
</body>
</html>
"""


CREDIT = """    <footer class="credit">
      <p>Zabandan is a project by <a href="https://shaykas.com/">Shay Kashif</a> · <a href="https://github.com/shaykashif/zabandan">Source on GitHub</a></p>
      <p>&copy; {year} Shayaan Kashif</p>
    </footer>"""


def english_title(p: dict) -> str:
    """A nazm has a title; a ghazal is known by its first line, so use that line's translation."""
    if p.get("title_en"):
        return p["title_en"]
    return p["blocks"][0]["poetic"][0].strip().rstrip(";,:—-–").strip()


def byline(p: dict) -> str:
    """Poet, form and, where known, the collection it was published in."""
    return " · ".join(x for x in (p["poet"], p["form"].capitalize(), p.get("collection")) if x)


def poem_page(p: dict, assets: dict) -> str:
    ov = p.get("overview") or {}
    title = english_title(p)

    # The page shows translation, not commentary: no summary, stanza roles or general notes,
    # only the word glosses and the curated context notes (scripts/curate_notes.py).
    keep = ("stanza", "ur", "roman", "words", "units", "phrases", "literal", "poetic", "context_notes")
    data = {"form": p["form"], "blocks": [{k: b[k] for k in keep if k in b} for b in p["blocks"]]}

    provenance = []
    if p.get("citation"):
        provenance.append(f"<p>{e(p['citation'])}.</p>")
    if p.get("copyright"):
        provenance.append(f"<p>{e(p['copyright'])}</p>")
    provenance.append(f"<p>{e(p['source'])}.</p>")
    if p.get("text_notes"):
        provenance.append(f"<p>Text notes: {e(p['text_notes'].strip())}</p>")
    provenance.append(
        "<p>Urdu words are split by code, so the text shown is the original. "
        + ("The Roman transliteration was written by the model. " if p["form"] == "nazm" else "")
        + f"Translations and word meanings were generated by {e(p['model'])} and checked automatically "
          "for completeness. I review all entries. If you spot an inconsistency please feel free to email me at "
          "shay [at] shaykas [dot] com.</p>")

    body = f"""    <header class="top">
      <a href="/">&larr; Zabandan</a>
    </header>

    <div class="poem-meta">
      <h1 class="poem-title">{e(title)}</h1>
      <p class="poem-ur ur" lang="ur">{e(p["title_ur"])}</p>
      <p class="poem-roman" lang="ur-Latn">{e(cap(p["title_roman"]))}</p>
      <p class="poem-by">{e(byline(p))}</p>
    </div>

    <div class="reader-bar">
      <span class="hint">Tap any word to translate it. <span class="mark">Underlined</span> words carry a double meaning or cultural context.</span>
      <button class="tgl" id="t-roman" type="button" aria-pressed="true">Roman</button>
      <button class="tgl" id="t-english" type="button" aria-pressed="true">English</button>
      <button class="tgl" id="t-literal" type="button" aria-pressed="true">Literal</button>
    </div>

    <div class="layout" id="layout">
      <div class="page" id="poem"></div>
      <aside class="aside" id="aside" aria-label="Translation">
        <p class="aside-head">Translation</p>
      </aside>
      <svg id="branch" aria-hidden="true"></svg>
    </div>

    <div class="provenance">
      {"".join(provenance)}
    </div>
{CREDIT.format(year=date.today().year)}
    {json_script("poem-data", data)}"""
    desc = (ov.get("summary") or f"{title}, a {p['form']} by {p['poet']}, translated word by word.")[:300]
    url = f"{BASE_URL}/{p['id']}/"
    work = {"@type": "CreativeWork", "name": title, "alternateName": [p["title_ur"], cap(p["title_roman"])],
            "author": {"@type": "Person", "name": p["poet"]}, "inLanguage": "ur", "genre": p["form"].capitalize()}
    if p.get("collection"):
        work["isPartOf"] = {"@type": "Book", "name": p["collection"]}
    ld = {"@context": "https://schema.org", "@type": "WebPage", "@id": url, "url": url,
          "name": f"{title} · {p['poet']}", "description": desc, "inLanguage": "en",
          "isPartOf": {"@id": SITE_ID}, "author": PERSON, "about": work,
          "primaryImageOfPage": f"{BASE_URL}/assets/og/{p['id']}.png"}
    return page(title=f"{title} · {p['poet']}", description=desc, path=f"/{p['id']}/", body=body,
                assets=assets, scripts=["theme.js", "reader.js"], og_type="article",
                main_class="reader", body_class="page-reader",
                image=f"og/{p['id']}.png", image_alt=f"{title}, {byline(p)}", ld=ld)


def search_entry(p: dict) -> dict:
    lines = []
    for i, b in enumerate(p["blocks"]):
        where = f"Couplet {i + 1}"
        for t in b["ur"] + (b.get("roman") or []) + (b.get("poetic") or []):
            lines.append({"where": where, "text": t})
    meta = " ".join(x for x in (p["title_roman"], p.get("title_en") or "", p["poet"], p["form"],
                                p.get("collection") or "") if x)
    return {"id": p["id"], "meta": meta, "meta_ur": p["title_ur"], "lines": lines}


INTRO_DESC = ('Zabandan is a database of classical Urdu poetry that I have translated to English. My goal is to capture cultural and poetic nuance often lost in translation, conveying the true beauty and depth of Urdu literature to non-native readers and fostering an appreciation among Western audiences.')


def index_page(poems: list[dict], assets: dict) -> str:
    rows = []
    for p in poems:
        source = f" · {e(p['collection'])}" if p.get("collection") else ""
        rows.append(f"""      <li data-id="{e(p['id'])}"><a href="/{e(p['id'])}/">
        <span class="t">{e(english_title(p))}</span><span class="d">{e(p['form'].capitalize())}</span>
        <span class="sub"><span>{e(p['poet'])}{source} · <em>{e(cap(p['title_roman']))}</em></span><span class="ur" lang="ur">{e(p['title_ur'])}</span></span>
        <span class="hit" hidden></span>
      </a></li>""")
    body = f"""    <header class="top">
      <a href="https://shaykas.com/">&larr; Shay Kashif</a>
    </header>

    <div class="masthead">
      <h1>Zabandan</h1>
      <span class="ur" lang="ur">زباندان</span>
    </div>

    <div class="intro">
      <p>Zabandan is a database of classical Urdu poetry that I have translated to English. My goal is to capture cultural and poetic nuance often lost in translation, conveying the true beauty and depth of Urdu literature to non-native readers and fostering an appreciation among Western audiences.</p>
      <p>I periodically add poems (mostly ghazals and nazms) that I translate in my free time to the database, and on occasion will also offer interpretations of the work. Each entry has a Romanized transliteration and a literal and poetic English meaning, as well as contextually appropriate definitions of words. If you'd like to suggest a work to translate, notice an error, or have a suggestion, please reach out to me at shay [at] shaykas [dot] com.</p>
    </div>

    <div class="search" role="search">
      <label for="q">Search</label>
      <input id="q" type="search" autocomplete="off" spellcheck="false"
             placeholder="Title, poet, or any word in Urdu, Roman or English" />
    </div>
    <p class="count" id="count" aria-live="polite">{len(poems)} poems</p>

    <h2 class="label">Poems</h2>
    <ul class="list" id="entries">
{chr(10).join(rows)}
    </ul>
    <p class="empty" id="empty" hidden>No poems match. Try a shorter word, or the Roman spelling without accents.</p>
{CREDIT.format(year=date.today().year)}
    {json_script("search-data", [search_entry(p) for p in poems])}"""
    desc = INTRO_DESC
    ld = {"@context": "https://schema.org", "@type": "WebSite", "@id": SITE_ID, "url": BASE_URL + "/",
          "name": "Zabandan", "alternateName": "زباندان", "description": desc, "inLanguage": "en",
          "author": PERSON, "publisher": PERSON,
          "potentialAction": {"@type": "SearchAction", "target": BASE_URL + "/?q={search_term_string}",
                              "query-input": "required name=search_term_string"}}
    return page(title="Zabandan", description=desc, path="/", body=body, assets=assets,
                scripts=["theme.js", "search.js"], ld=ld)


def not_found_page(assets: dict) -> str:
    body = """    <header class="top">
      <a href="/">&larr; Zabandan</a>
    </header>
    <h1 class="poem-title">Not found</h1>
    <p>There's no poem at this address. <a href="/">See all poems</a>.</p>"""
    out = page(title="Not found · Zabandan", description="Page not found.", path="/404", body=body,
               assets=assets, scripts=["theme.js"])
    return out.replace("<head>", '<head>\n  <meta name="robots" content="noindex" />', 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", help="model name (default: the config's role: default)")
    ap.add_argument("--out", default="site")
    ap.add_argument("--include-unpublished", action="store_true",
                    help="include poems marked publish: false, for a local preview only")
    args = ap.parse_args()

    config = yaml.safe_load((ROOT / "config/models.yaml").read_text(encoding="utf-8"))["models"]
    model = args.model or next(m["name"] for m in config if m.get("role") == "default")
    poems = [json.loads(f.read_text(encoding="utf-8"))
             for f in sorted((ROOT / "data/annotated").glob(f"*.{model}.json"))]
    # A nazm's metadata (title, citation, publish flag...) lives in data/nazms/; read it fresh so
    # editing it doesn't need a re-annotation.
    for p in poems:
        src = ROOT / "data/nazms" / f"{p['id']}.yaml"
        if src.exists():
            p.update({k: v for k, v in yaml.safe_load(src.read_text(encoding="utf-8")).items() if k != "stanzas"})
    held = [p["id"] for p in poems if p.get("publish") is False]
    if held and not args.include_unpublished:
        poems = [p for p in poems if p.get("publish") is not False]
        print(f"left out (publish: false): {', '.join(held)}")
    if not poems:
        raise SystemExit(f"no poems annotated by {model} in data/annotated/")
    poems.sort(key=lambda p: (p["poet"], p["title_roman"]))

    out = ROOT / args.out
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SRC, out / "assets")
    assets = {str(f.relative_to(SRC)).replace("\\", "/"): hashlib.sha1(f.read_bytes()).hexdigest()[:8]
              for f in SRC.rglob("*") if f.is_file()}

    (out / "index.html").write_text(index_page(poems, assets), encoding="utf-8")
    for p in poems:
        (out / p["id"]).mkdir()
        (out / p["id"] / "index.html").write_text(poem_page(p, assets), encoding="utf-8")
    (out / "404.html").write_text(not_found_page(assets), encoding="utf-8")

    today = date.today().isoformat()
    urls = ["/"] + [f"/{p['id']}/" for p in poems]
    (out / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{BASE_URL}{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls)
        + "</urlset>\n", encoding="utf-8")
    (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {BASE_URL}/sitemap.xml\n", encoding="utf-8")
    # Cloudflare Pages: assets are versioned by content hash in their URLs, so cache them for a year.
    (out / "_headers").write_text("/assets/*\n  Cache-Control: public, max-age=31536000, immutable\n", encoding="utf-8")

    print(f"built {out.relative_to(ROOT)}/ with {len(poems)} poems ({model}): " + ", ".join(p["id"] for p in poems))


if __name__ == "__main__":
    main()
