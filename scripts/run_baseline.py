"""Phase 1: run the baseline test set through every enabled model, then build a blind
scoring sheet.

Usage:
  python scripts/run_baseline.py                     # run all enabled models
  python scripts/run_baseline.py --models qalb-8b    # run only some
  python scripts/run_baseline.py --sheet             # build the scoring sheet from results
  python scripts/run_baseline.py --models qalb-8b --prompt translate_v0_ur.txt       --plain --out baseline_v0_retest              # variant prompt, plain-text replies

Results go to results/<out>/<model>.jsonl (default baseline_v0). Runs resume: couplets already answered
by a model are skipped, so re-running after a failure only fills the gaps.
"""

import argparse
import csv
import json
import os
import random
import re
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TESTSET = ROOT / "data/testsets/baseline_v0.jsonl"
PROMPT = ROOT / "prompts/translate_v0.txt"
CONFIG = ROOT / "config/models.yaml"
RESULTS = ROOT / "results/baseline_v0"

ENDPOINTS = {
    "ollama": "http://localhost:11434/v1/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
}
FIELDS = ["gloss", "literal", "poetic", "notes", "lost"]

POET_UR = {
    "mirza-ghalib": "مرزا غالب",
    "meer-taqi-meer": "میر تقی میر",
    "allama-iqbal": "علامہ اقبال",
    "dagh-dehlvi": "داغ دہلوی",
    "bahadur-shah-zafar": "بہادر شاہ ظفر",
    "akbar-allahabadi": "اکبر الہ آبادی",
    "wali-mohammad-wali": "ولی دکنی",
    "altaf-hussain-hali": "الطاف حسین حالی",
}

# Small local models write broken JSON (nested objects, unfinished strings), so for
# Ollama the reply is constrained to this shape. It fixes the format, not the content.
REPLY_SCHEMA = {
    "type": "object",
    "properties": {
        "gloss": {"type": "string"},
        "literal": {"type": "string"},
        "poetic": {"type": "string"},
        "notes": {"type": "array", "items": {"type": "string"}},
        "lost": {"type": "string"},
    },
    "required": FIELDS,
}


def load_env() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]


def chat(model: dict, prompt: str, plain: bool = False) -> dict:
    """Return the reply text plus finish reason, reasoning text and token usage.

    A model's config may set `system` and `temperature`, e.g. its authors' recommended
    settings. With plain=True the reply is free text instead of constrained JSON.
    """
    headers = {"Content-Type": "application/json"}
    if model["backend"] == "openrouter":
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise SystemExit("OPENROUTER_API_KEY is not set; add it to .env")
        headers["Authorization"] = f"Bearer {key}"
    payload = {
        "model": model["model"],
        "messages": ([{"role": "system", "content": model["system"]}] if model.get("system") else [])
                    + [{"role": "user", "content": prompt}],
        "temperature": model.get("temperature", 0.3),
        # Reasoning models spend tokens thinking before they answer; with a low cap
        # the answer comes back empty. Local models don't think, and a lower cap stops
        # a repetition loop from tying up the laptop for minutes.
        "max_tokens": 12000 if model["backend"] == "openrouter" else 3000,
    }
    if model["backend"] == "ollama" and not plain:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "translation", "schema": REPLY_SCHEMA},
        }
    if model["backend"] == "openrouter":
        # Cap thinking so it can't use up the whole budget (DeepSeek ran past
        # 12K tokens on one couplet and never answered).
        payload["reasoning"] = model.get("reasoning", {"max_tokens": 6000})
        # Providers serve the same model at different precisions; fp4 ones are
        # cheaper but can be worse. Only route to full-quality weights.
        payload["provider"] = {"quantizations": model.get("quantizations", ["bf16", "fp8"])}
    body = json.dumps(payload).encode()
    req = urllib.request.Request(ENDPOINTS[model["backend"]], data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=900) as resp:
        data = json.load(resp)
    choice = data["choices"][0]
    return {
        "content": choice["message"].get("content") or "",
        "reasoning": choice["message"].get("reasoning") or "",
        "finish_reason": choice.get("finish_reason"),
        "usage": data.get("usage"),
        "provider": data.get("provider"),
    }


def parse(raw: str) -> dict | None:
    """Pull the JSON object out of a reply, tolerating think blocks and code fences."""
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.S)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


SECTION = re.compile(r"^\s*\**\s*(GLOSS|LITERAL|POETIC|NOTES|LOST)\s*\**\s*:\s*\**", re.M | re.I)


def parse_sections(raw: str) -> dict | None:
    """Parse a plain-text reply with GLOSS:/LITERAL:/POETIC:/NOTES:/LOST: headings."""
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.S)
    marks = list(SECTION.finditer(text))
    if not marks:
        return None
    out = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out.setdefault(m.group(1).lower(), text[m.end():end].strip())
    if "notes" in out:
        lines = [ln.strip().lstrip("-•*").strip() for ln in out["notes"].splitlines()]
        out["notes"] = [ln for ln in lines if ln]
    return out


def run(models: list[dict], items: list[dict], plain: bool = False, workers: int = 1) -> None:
    """Hosted models take up to `workers` requests at once; local Ollama runs one at a time."""
    template = PROMPT.read_text(encoding="utf-8")
    RESULTS.mkdir(parents=True, exist_ok=True)
    for model in models:
        out = RESULTS / f"{model['name']}.jsonl"
        done = {r["test_id"] for r in load_jsonl(out)}
        todo = [it for it in items if it["test_id"] not in done]
        print(f"== {model['name']}: {len(todo)} to run, {len(done)} already done")
        lock = threading.Lock()

        def one(it: dict) -> None:
            prompt = template.format(
                poet=it["poet"].replace("-", " ").title(),
                poet_ur=POET_UR.get(it["poet"], it["poet"]),
                ur="\n".join(it["ur"]),
                roman="\n".join(it["roman"]),
            )
            t0 = time.time()
            try:
                reply = chat(model, prompt, plain)
            except (urllib.error.URLError, TimeoutError) as e:
                print(f"  {it['test_id']} FAILED: {e}")
                return
            if not reply["content"].strip():
                # Not saved, so the next run retries it.
                print(f"  {it['test_id']} EMPTY (finish_reason={reply['finish_reason']}), will retry next run")
                return
            parsed = parse_sections(reply["content"]) if plain else parse(reply["content"])
            record = json.dumps({
                "test_id": it["test_id"],
                "model": model["name"],
                "seconds": round(time.time() - t0, 1),
                "finish_reason": reply["finish_reason"],
                "provider": reply["provider"],
                "usage": reply["usage"],
                "parsed": parsed,
                "raw": reply["content"],
                "reasoning": reply["reasoning"],
            }, ensure_ascii=False)
            with lock:
                with open(out, "a", encoding="utf-8") as f:
                    f.write(record + "\n")
            print(f"  {it['test_id']} {'ok' if parsed else 'UNPARSED'} {time.time() - t0:.0f}s")

        n = workers if model["backend"] == "openrouter" else 1
        with ThreadPoolExecutor(max_workers=n) as pool:
            list(pool.map(one, todo))


def as_text(value) -> str:
    if isinstance(value, list):
        return "\n".join(f"- {v}" for v in value)
    return "" if value is None else str(value)


def build_sheet(items: list[dict]) -> None:
    """One row per (couplet, model), with model names hidden behind shuffled letters."""
    results = {}
    for path in sorted(RESULTS.glob("*.jsonl")):
        for r in load_jsonl(path):
            results.setdefault(r["test_id"], []).append(r)

    rng = random.Random(0)
    key = {}
    sheet = RESULTS / "scoring_sheet.csv"
    with open(sheet, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["test_id", "poet", "urdu", "roman", "nuance_note", "label", *FIELDS,
                    "meaning (1-5)", "imagery (1-5)", "double meanings (1-5)",
                    "reads as poetry (1-5)", "comment"])
        for it in items:
            outputs = results.get(it["test_id"], [])
            rng.shuffle(outputs)
            for label, r in zip("ABCDEFGHIJ", outputs):
                key[f"{it['test_id']}{label}"] = r["model"]
                if r["parsed"]:
                    p = r["parsed"]
                else:
                    # Runaway replies can exceed Excel's 32,767-character cell limit.
                    raw = r["raw"]
                    if len(raw) > 3000:
                        raw = raw[:3000] + f"\n[... cut: {len(raw):,} characters, finish_reason={r.get('finish_reason')}]"
                    p = {"literal": "(unparsed reply)\n" + raw}
                w.writerow([it["test_id"], it["poet"], "\n".join(it["ur"]), "\n".join(it["roman"]),
                            it["nuance_note"], label, *(as_text(p.get(k)) for k in FIELDS),
                            "", "", "", "", ""])
    (RESULTS / "blind_key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    print(f"wrote {sheet.relative_to(ROOT)} ({len(key)} rows); key in blind_key.json, don't peek")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", help="model names to run (default: all enabled)")
    ap.add_argument("--limit", type=int, help="only the first N couplets, for a smoke test")
    ap.add_argument("--sheet", action="store_true", help="build the blind scoring sheet")
    ap.add_argument("--prompt", default="translate_v0.txt", help="prompt file in prompts/")
    ap.add_argument("--out", default="baseline_v0", help="results folder under results/")
    ap.add_argument("--plain", action="store_true", help="plain-text replies with headings, not JSON")
    ap.add_argument("--workers", type=int, default=8, help="parallel requests for hosted models")
    args = ap.parse_args()

    global PROMPT, RESULTS
    PROMPT = ROOT / "prompts" / args.prompt
    RESULTS = ROOT / "results" / args.out

    load_env()
    items = load_jsonl(TESTSET)
    if args.sheet:
        build_sheet(items)
        return

    models = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["models"]
    if args.models:
        models = [m for m in models if m["name"] in args.models]
    else:
        models = [m for m in models if m.get("enabled")]
    run(models, items[:args.limit] if args.limit else items, args.plain, args.workers)


if __name__ == "__main__":
    main()
