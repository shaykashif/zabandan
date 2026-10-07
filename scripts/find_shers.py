"""Search the couplet corpus by Roman or Urdu substring.

Usage: python scripts/find_shers.py "dam nikle" ["another phrase" ...] [--poet mirza-ghalib]
Matching ignores case and diacritics in the Roman text.
"""

import argparse
import json
import unicodedata
from pathlib import Path

CORPUS = Path(__file__).resolve().parent.parent / "data/processed/classical_shers.jsonl"


def fold(s: str) -> str:
    """Lowercase and strip diacritics so 'nahīñ' matches 'nahin'."""
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("queries", nargs="+")
    ap.add_argument("--poet")
    args = ap.parse_args()

    shers = [json.loads(line) for line in CORPUS.open(encoding="utf-8")]
    for q in args.queries:
        fq = fold(q)
        hits = [
            s for s in shers
            if (not args.poet or s["poet"] == args.poet)
            and (fq in fold(" / ".join(s["roman"])) or q in " ".join(s["ur"]))
        ]
        print(f"## {q!r}: {len(hits)} hit(s)")
        for s in hits[:5]:
            print(f"  {s['id']}")
            print(f"    {' / '.join(s['roman'])}")
        print()


if __name__ == "__main__":
    main()
