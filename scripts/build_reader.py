"""Build the clickable reader page from annotated poems.

Usage: python scripts/build_reader.py hazaaron-khvaahishen parinde-ki-faryad
Reads data/annotated/<poem>.<model>.json for every model that annotated each poem and
writes web/reader.html from web/reader_template.html, with a tab per poem and a switch
between the models' readings. The output is an HTML body fragment (no <html>/<head>),
the format the Artifact publisher wraps; browsers also open it directly.
"""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = [  # order on the page; the first is the default
    {"name": "deepseek-v4-pro", "label": "DeepSeek V4 Pro", "note": "Default: most accurate in the blind scoring"},
    {"name": "gemma-4-31b", "label": "Gemma 4 31B", "note": "Budget option: about a fifteenth of the cost"},
]
DROP = {"cost", "attempts"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("poems", nargs="+")
    ap.add_argument("--out", default="web/reader.html")
    args = ap.parse_args()

    poems, used = [], set()
    for pid in args.poems:
        variants = {}
        for m in MODELS:
            path = ROOT / "data/annotated" / f"{pid}.{m['name']}.json"
            if path.exists():
                variants[m["name"]] = json.loads(path.read_text(encoding="utf-8"))
        if not variants:
            raise SystemExit(f"no annotations for {pid!r} in data/annotated/")
        used |= set(variants)
        first = next(iter(variants.values()))
        meta = {k: first.get(k) for k in ("id", "form", "poet", "title_ur", "title_roman", "title_en",
                                          "collection", "source", "text_notes", "stanza_lengths")}
        short = first["title_roman"].split()
        meta["title_short"] = " ".join(short[:3]) + ("…" if len(short) > 3 else "")
        meta["variants"] = {
            name: {"model": v["model"], "overview": v.get("overview", {}),
                   "blocks": [{k: b[k] for k in b if k not in DROP} for b in v["blocks"]]}
            for name, v in variants.items()
        }
        poems.append(meta)

    data = {"models": [m for m in MODELS if m["name"] in used], "poems": poems}
    page = (ROOT / "web/reader_template.html").read_text(encoding="utf-8")
    page = page.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    out = ROOT / args.out
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} ({len(page) / 1024:.0f} KB): "
          + "; ".join(f"{p['id']} [{', '.join(p['variants'])}]" for p in poems))


if __name__ == "__main__":
    main()
