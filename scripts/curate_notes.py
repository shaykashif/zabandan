"""Reduce each couplet's notes to what a translator should flag, and attach them to words.

The site is a translator, not a commentary: interpretation is left to the reader. This
keeps only (1) double meanings and wordplay the English can't carry and (2) cultural,
religious, historical or literary context a Western reader wouldn't know, rewrites each as
a short factual note, and attaches it to the units (words) it is about. The result is
stored as "context_notes" on each couplet; the original "notes" are kept.

Usage: python scripts/curate_notes.py [--model deepseek-v4-pro] [poem ...]
Default: every poem annotated by the default model.
"""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_baseline as rb  # noqa: E402

ROOT = rb.ROOT
KINDS = ("double meaning", "cultural context")

PROMPT = """You are preparing notes for a word-by-word Urdu poetry translator used by English
readers who don't know Urdu or South Asian culture. The reader does their own interpreting;
notes exist only to supply what translation loses.

Below is one {form} by {poet}, couplet by couplet. For each couplet you get its words (as units
with ids), its English translation, and draft notes written earlier.

{couplets}

From the draft notes (and the words themselves), keep ONLY:
1. double meaning: a pun, a word read two ways, or wordplay the English cannot carry.
2. cultural context: a custom, religious idea, historical fact, legend, person, place or literary
   convention (such as the beloved being called "kafir", the moth and candle, the saqi, the
   poet's pen name in the last couplet) that a Western reader would not know.

Drop everything else: interpretation, theme, mood, irony or paradox explained, what the poet
"suggests", grammar, the radif or rhyme, and comments on translation choices.

Write each kept note as one or two plain, factual sentences, at most 35 words, without
phrases like "the poet suggests". Attach it to the ids of the units it is about. A couplet
may have no notes; don't invent filler.

Reply with only a JSON object:
{{"couplets": [{{"index": 0, "notes": [{{"units": ["u8", "u9"], "kind": "double meaning", "text": "..."}}]}}]}}
Include every couplet index, with "notes": [] where nothing qualifies."""


def couplet_text(b: dict) -> str:
    units = ", ".join(f'{u["id"]}={u["roman"]} ("{u["gloss"]}")' for u in b["units"])
    notes = "\n".join(f"    - {n}" for n in b.get("notes") or []) or "    (none)"
    return (f"Couplet index {b['index']}:\n  Urdu: {' / '.join(b['ur'])}\n  Roman: {' / '.join(b.get('roman') or [])}\n"
            f"  Units: {units}\n  English: {' / '.join(b.get('poetic') or [])}\n  Draft notes:\n{notes}")


def curate(path: Path, model: dict) -> None:
    poem = json.loads(path.read_text(encoding="utf-8"))
    prompt = PROMPT.format(form=poem["form"], poet=poem["poet"],
                           couplets="\n\n".join(couplet_text(b) for b in poem["blocks"]))
    for attempt in range(3):
        try:
            reply = rb.chat(model, prompt)
        except (rb.urllib.error.URLError, TimeoutError) as e:
            print(f"  {path.name}: request failed ({e}), retrying")
            continue
        out = rb.parse(reply["content"])
        if out and isinstance(out.get("couplets"), list):
            break
        print(f"  {path.name}: attempt {attempt + 1} unparsed, retrying")
    else:
        raise SystemExit(f"{path.name}: no usable reply")

    by_index = {c.get("index"): c.get("notes") or [] for c in out["couplets"]}
    kept = 0
    for b in poem["blocks"]:
        ids = {u["id"] for u in b["units"]}
        notes = []
        for n in by_index.get(b["index"], []):
            units = [u for u in n.get("units", []) if u in ids]
            if n.get("kind") in KINDS and n.get("text") and units:
                notes.append({"units": units, "kind": n["kind"], "text": n["text"].strip()})
        b["context_notes"] = notes
        kept += len(notes)
    before = sum(len(b.get("notes") or []) for b in poem["blocks"])
    path.write_text(json.dumps(poem, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"== {path.name}: {before} draft notes -> {kept} context notes "
          f"(${(reply.get('usage') or {}).get('cost') or 0:.3f})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("poems", nargs="*")
    ap.add_argument("--model")
    args = ap.parse_args()
    rb.load_env()
    config = yaml.safe_load((ROOT / "config/models.yaml").read_text(encoding="utf-8"))["models"]
    model = next(m for m in config if (m["name"] == args.model if args.model else m.get("role") == "default"))
    paths = [ROOT / "data/annotated" / f"{p}.{model['name']}.json" for p in args.poems] if args.poems else \
            sorted((ROOT / "data/annotated").glob(f"*.{model['name']}.json"))
    with ThreadPoolExecutor(max_workers=len(paths)) as pool:
        list(pool.map(lambda p: curate(p, model), paths))


if __name__ == "__main__":
    main()
