"""Rough automatic check: did each model's notes mention the key nuance of each couplet?

This is a keyword test, not a quality score. Mentioning a pun is not the same as
explaining it well, so it only helps decide which models deserve careful human
scoring. Each check is a list of keyword groups; a reply passes if every group has
at least one keyword in its gloss, notes or "lost" text.

Usage: python scripts/auto_check.py [--results baseline_v0]
"""

import argparse
import json
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CHECKS = {
    "b01": [["nikl", "nikal"], ["fulfil", "come out", "came out", "emerge", "realiz", "turned out"]],
    "b02": [["unity of being", "wahdat", "merg", "dissolv", "annihil", "fana", "become god", "been god", "one with god"]],
    "b04": [["kaam"], ["useless", "nikamma", "good-for-nothing", "worthless"]],
    "b05": [["iron", "sceptic", "skeptic", "doubt", "wry", "self-deception", "consol"]],
    "b06": [["paper"], ["petition", "complain", "plaint", "justice", "grievance", "custom"]],
    "b07": [["surat"], ["way", "means", "solution", "prospect", "possibilit", "form"]],
    "b08": [["mir"], ["rekhta"], ["urdu"]],
    "b09": [["insan"], ["aadmi", "adami", "admi"]],
    "b10": [["iron", "misread", "mistak", "mislead", "misunderst", "deceiv", "illusion"]],
    "b11": [["child"], ["play"]],
    "b12": [["aur"], ["different", "other", "unique", "distinct", "else", "apart"]],
    "b13": [["wine"], ["mystic", "sufi", "divine", "spiritual", "metaphor", "literal"]],
    "b14": [["saghar", "goblet", "cup", "glass"], ["mina", "flask", "decanter", "carafe", "jug"]],
    "b15": [["sar "], ["conquer", "won", "win", "subdue", "yield", "tame", "head"]],
    "b16": [["repet", "repeat", "jaane", "reduplic"], ["gul", "flower", "rose"]],
    "b17": [["petal"]],
    "b18": [["kaam"], ["tamam", "finish", "kill", "end", "done for"]],
    "b19": [["qashqa", "tilak", "forehead"], ["temple", "dair", "hindu"]],
    "b20": [["khudi"], ["self"]],
    "b21": [["saqi", "saaqi", "cupbearer", "cup-bearer"], ["barren", "field", "soil", "nation", "people", "communit"]],
    "b22": [["chilman", "screen", "purdah", "blind"]],
    "b23": [["dagh"], ["stain", "scar", "mark", "blemish", "wound", "brand"]],
    # Either the historical irony (exiled emperor) or the name's meaning ("victory").
    "b24": [["exile", "rangoon", "mughal", "emperor", "burma", "victory"]],
    "b25": [["ruin", "desolat"], ["impermanen", "transien", "fleeting", "ephemeral", "unstable"]],
    "b26": [["double standard", "iron", "hypocri", "unfair", "injustice", "satir"]],
    "b27": [["moth", "parvana", "parwana"], ["candle", "shama", "flame"]],
    # The double sense of khat: first down on the cheek, and a line of writing.
    "b28": [["down", "beard", "facial hair", "hair"], ["letter", "script", "writing", "line"]],
    "b30": [["zunnar", "sacred thread", "thread"], ["infidel", "kafir", "unbeliever"]],
}


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def reply_text(r: dict) -> str:
    p = r.get("parsed") or {}
    parts = [p.get("gloss"), p.get("notes"), p.get("lost")] if p else [r.get("raw", "")]
    return fold(json.dumps(parts, ensure_ascii=False))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="baseline_v0", help="results folder under results/")
    RESULTS = ROOT / "results" / ap.parse_args().results

    table = {}
    for path in sorted(RESULTS.glob("*.jsonl")):
        rows = {json.loads(l)["test_id"]: json.loads(l) for l in path.open(encoding="utf-8")}
        table[path.stem] = {
            tid: all(any(k in reply_text(rows[tid]) for k in group) for group in groups)
            for tid, groups in CHECKS.items() if tid in rows
        }

    ids = list(CHECKS)
    print(f"{'model':18} {'hits':>5}   " + " ".join(t[1:] for t in ids))
    ranked = sorted(table.items(), key=lambda kv: -sum(kv[1].values()))
    for model, hits in ranked:
        marks = " ".join(" ✓" if hits.get(t) else " ·" for t in ids)
        print(f"{model:18} {sum(hits.values()):2}/{len(ids)}   {marks}")

    out = RESULTS / "auto_check.json"
    out.write_text(json.dumps(table, indent=2), encoding="utf-8")
    print(f"\nsaved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
