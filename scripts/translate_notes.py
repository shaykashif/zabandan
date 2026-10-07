"""Translate Urdu-language replies into English so auto_check.py can score them fairly.

The keyword check is English-only. With an Urdu prompt, Qalb and Alif sometimes answer
in Urdu, which the check would miss. This sends every reply that is largely in Urdu
script to a cheap hosted model with instructions to translate literally and add
nothing, then writes copies with the English text to results/<out>/.

Usage: python scripts/translate_notes.py --src baseline_v0_retest --out baseline_v0_retest_en
"""

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_baseline as rb  # noqa: E402

# Thinking off: with it on, Gemma spent its whole budget thinking and returned nothing.
# 26B-A4B dropped whole sections when translating; 31B keeps them.
TRANSLATOR = {"name": "translator", "backend": "openrouter",
              "model": "google/gemma-4-31b-it", "temperature": 0.0,
              "reasoning": {"enabled": False}}

INSTRUCTION = (
    "Translate every Urdu-script passage in the text below into English, literally and "
    "sentence by sentence. Leave text that is already English or Roman Urdu unchanged. "
    "Do not correct, explain, expand or add anything; if the original is wrong or "
    "confused, keep it wrong or confused. Reply with only the translated text.\n\n"
    "TEXT:\n"
)


def urdu_share(text: str) -> float:
    letters = re.findall(r"\w", text)
    urdu = re.findall(r"[؀-ۿ]", text)
    return len(urdu) / max(len(letters), 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--threshold", type=float, default=0.15,
                    help="translate replies whose letters are at least this share Urdu script")
    args = ap.parse_args()

    rb.load_env()
    src, out = rb.ROOT / "results" / args.src, rb.ROOT / "results" / args.out
    out.mkdir(parents=True, exist_ok=True)
    def translate(r: dict) -> dict:
        if urdu_share(r["raw"]) < args.threshold:
            return r
        reply = rb.chat(TRANSLATOR, INSTRUCTION + r["raw"][:12000])
        return {**r, "parsed": None, "raw": reply["content"], "translated_from_urdu": True}

    for path in sorted(src.glob("*.jsonl")):
        rows = rb.load_jsonl(path)
        with ThreadPoolExecutor(max_workers=8) as pool:
            done = list(pool.map(translate, rows))
        with open(out / path.name, "w", encoding="utf-8") as f:
            for r in done:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        n = sum(1 for r in done if r.get("translated_from_urdu"))
        print(f"{path.name}: translated {n}/{len(rows)} replies")


if __name__ == "__main__":
    main()
