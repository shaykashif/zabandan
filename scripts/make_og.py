"""Render the link-preview images and PNG icons with headless Chrome.

Writes site_src/static/og/<poem>.png and og/site.png (1200x630, for og:image), and
icons/apple-touch-icon.png (180x180) and icons/favicon-48.png. Chrome is used because it
shapes Nastaliq properly, which image libraries don't. Run it after adding a poem, then build.

Usage: python scripts/make_og.py [--model deepseek-v4-pro]
Set CHROME to the browser's path if it isn't in a standard place.
"""

import argparse
import html
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "site_src/static"
FONTS = (STATIC / "fonts").as_uri()
CANDIDATES = [
    os.environ.get("CHROME", ""),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]
e = html.escape

BASE_CSS = f"""
@font-face{{font-family:"Aktiv Grotesk";src:url({FONTS}/aktiv-grotesk-regular.woff2) format("woff2");font-weight:400}}
@font-face{{font-family:"Aktiv Grotesk";src:url({FONTS}/aktiv-grotesk-semibold.woff2) format("woff2");font-weight:600}}
html,body{{margin:0;background:#f6f2e6;color:#1c1b17;font-family:"Aktiv Grotesk",sans-serif}}
.ur{{font-family:"Noto Nastaliq Urdu",serif;direction:rtl;color:#94733a}}
"""
FONT_LINK = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;600&display=block">'


def card(title: str, ur: str, line: str) -> str:
    size = 76 if len(title) < 24 else 60 if len(title) < 48 else 50
    return f"""<!doctype html><html><head><meta charset="utf-8">{FONT_LINK}<style>{BASE_CSS}
body{{width:1200px;height:630px;box-sizing:border-box;padding:46px}}
.frame{{position:absolute;inset:46px;border:2px solid #94733a;outline:2px solid #94733a;outline-offset:7px}}
.in{{position:absolute;inset:96px 104px;display:flex;flex-direction:column;justify-content:space-between}}
.brand{{display:flex;align-items:baseline;gap:16px;font-size:30px;font-weight:600}}
.brand .ur{{font-size:30px;line-height:1.6}}
h1{{margin:0;font-size:{size}px;line-height:1.08;font-weight:600;letter-spacing:-.03em;max-width:960px;text-wrap:balance}}
.t-ur{{margin:6px 0 0;font-size:52px;line-height:1.9;text-align:left}}
.line{{font-size:30px;color:#6a6860}}
</style></head><body><div class="frame"></div><div class="in">
<div class="brand">Zabandan <span class="ur">زباندان</span></div>
<div><h1>{e(title)}</h1><p class="ur t-ur">{e(ur)}</p></div>
<div class="line">{e(line)}</div></div></body></html>"""


def icon(px: int) -> str:
    # The site's mark: an eight-pointed star, gold on paper.
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{BASE_CSS}
body{{width:{px}px;height:{px}px;display:grid;place-items:center}}</style></head><body>
<svg width="{int(px * .78)}" height="{int(px * .78)}" viewBox="0 0 32 32"><g fill="none" stroke="#94733a" stroke-width="2" stroke-linejoin="round">
<path d="M9 9h14v14H9z"/><path d="M16 6.1L25.9 16L16 25.9L6.1 16z"/></g></svg></body></html>"""


def shoot(chrome: str, page: str, out: Path, w: int, h: int) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "card.html"
        src.write_text(page, encoding="utf-8")
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                        f"--user-data-dir={Path(tmp) / 'profile'}", f"--window-size={w},{h}",
                        "--virtual-time-budget=6000", f"--screenshot={out}", src.as_uri()],
                       check=True, capture_output=True, timeout=120)
    print(f"wrote {out.relative_to(ROOT)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model")
    args = ap.parse_args()
    chrome = next((c for c in CANDIDATES if c and Path(c).exists()), None) or shutil.which("chrome")
    if not chrome:
        raise SystemExit("Chrome or Edge not found; set CHROME to its path")

    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from build_site import english_title, byline  # same titles and bylines as the pages

    config = yaml.safe_load((ROOT / "config/models.yaml").read_text(encoding="utf-8"))["models"]
    model = args.model or next(m["name"] for m in config if m.get("role") == "default")
    for f in sorted((ROOT / "data/annotated").glob(f"*.{model}.json")):
        p = json.loads(f.read_text(encoding="utf-8"))
        src = ROOT / "data/nazms" / f"{p['id']}.yaml"
        if src.exists():
            p.update({k: v for k, v in yaml.safe_load(src.read_text(encoding="utf-8")).items() if k != "stanzas"})
        shoot(chrome, card(english_title(p), p["title_ur"], byline(p)), STATIC / "og" / f"{p['id']}.png", 1200, 630)

    shoot(chrome, card("Classical Urdu poetry, word by word", "زباندان", "Ghazals and nazms · zabandan.shaykas.com"),
          STATIC / "og" / "site.png", 1200, 630)
    shoot(chrome, icon(180), STATIC / "icons" / "apple-touch-icon.png", 180, 180)
    shoot(chrome, icon(48), STATIC / "icons" / "favicon-48.png", 48, 48)


if __name__ == "__main__":
    main()
