"""Annotate a ghazal or a nazm word by word for the clickable reader page.

The Urdu is split into numbered words by code; the model only refers to those numbers,
so the page always shows the original text exactly.

1. An overview pass reads the whole poem. For a ghazal: radif, qafiya and a summary.
   For a nazm: a summary, the speaker, how the poem is built, each stanza's role and
   where the poem turns.
2. Each couplet (a pair of lines; a nazm's stanzas are split into pairs) is then
   annotated with the whole poem and the overview as context:
     units    clickable words or fixed compounds, covering every word once, glossed
              for this couplet
     phrases  idioms and expressions made of several units
     literal  literal translation as segments pointing at the units they translate
     poetic   a poetic translation
     notes    wordplay, double meanings, allusions
     role     (nazm only) how the couplet moves the poem along
   Code checks coverage and references and retries with the errors if they're wrong.

Every request includes the glossary of conventional terms in data/glossary.yaml.

Usage:
  python scripts/annotate_poem.py hazaaron-khvaahishen                 # ghazal from the corpus
  python scripts/annotate_poem.py parinde-ki-faryad                    # nazm from data/nazms/
  python scripts/annotate_poem.py parinde-ki-faryad --models deepseek-v4-pro gemma-4-31b
Output: data/annotated/<poem>.<model>.json
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
CORPUS = ROOT / "data/processed/classical_shers.jsonl"
NAZMS = ROOT / "data/nazms"
OUT = ROOT / "data/annotated"
POET_EN = {"mirza-ghalib": "Mirza Ghalib", "meer-taqi-meer": "Mir Taqi Mir", "allama-iqbal": "Allama Iqbal",
           "dagh-dehlvi": "Dagh Dehlvi", "bahadur-shah-zafar": "Bahadur Shah Zafar"}
ROMAN_STYLE = ("in the scholarly style Rekhta uses: ā ī ū for long vowels, ñ for a nasal n, "
               "ḳh and ġh, and -e- for the izafat, e.g. āzādiyāñ, āshiyāna, ġham-e-dil")

OVERVIEW_GHAZAL = """You are an expert in the classical Urdu ghazal. Here is a complete ghazal by {poet}.

{poem}

Reply with only a JSON object:
{{
  "radif": {{"ur": "the refrain word(s) ending every second line", "roman": "...", "en": "its meaning"}},
  "qafiya": ["the rhyme words before the radif, in Roman, one per couplet, in order"],
  "summary": "two or three plain sentences on what the ghazal is about and how its couplets relate"
}}"""

OVERVIEW_NAZM = """You are an expert in classical Urdu poetry. Here is a complete nazm by {poet}, "{title}".
Unlike a ghazal, a nazm develops one subject from start to finish, so read it as a whole.

{poem}

Reply with only a JSON object:
{{
  "summary": "two or three plain sentences on what the poem is about and how it develops",
  "speaker": "who speaks, to whom, and in what situation, in one sentence",
  "form": "one sentence on how the poem is built: stanza lengths and rhyme pattern",
  "stanzas": [{{"stanza": 1, "role": "one sentence on what this stanza does in the poem"}}],
  "turns": ["each place the poem shifts in mood, address or argument, naming the stanza and line"],
  "readings": "one or two sentences on readings beyond the literal (allegory, politics, mysticism), or empty if none"
}}"""

BLOCK_PROMPT = """You are an expert translator of classical Urdu poetry. Here is the complete {form} by {poet}, for context.

{poem}
{overview}
Conventional terms of classical Urdu poetry. Use these senses where they apply; don't force them where they don't:
{glossary}

Annotate {where}. Its Urdu lines are split into numbered words:
{tokens}
{roman}

Reply with only a JSON object in exactly this shape:
{{
  "units": [
    {{"id": "u1", "line": 0, "start": 0, "end": 0, "roman": "...", "kind": "word", "gloss": "...", "base": "..."}}
  ],
  "phrases": [
    {{"id": "p1", "units": ["u7", "u8"], "gloss": "..."}}
  ],
  "literal": [
    [{{"text": "Thousands of", "units": ["u1"]}}, {{"text": "desires", "units": ["u2"]}}]
  ],
  "poetic": ["one string per Urdu line"],
  "notes": ["..."]{role_field}
}}

Rules:
- units: cover every numbered word of every line exactly once, in order, with no gaps or
  overlaps. "line" is the line number shown above; "start" and "end" are word numbers
  (inclusive). A unit is one word, or several adjacent words that form one word or a fixed
  compound (for example a Persian izafat compound written as separate words, or بے آبرو).
- kind: one of word, compound, name, particle.
- roman: {roman_rule}
- gloss: what the unit means here, in this couplet, in at most 12 words. Not a dictionary list.
- base: the ordinary dictionary sense if it differs from the gloss, in at most 8 words; otherwise "".
- phrases: idioms and expressions whose meaning differs from their parts (for example دم نکلنا),
  each listing the ids of its units. Use [] if there are none.
- literal: one list of segments per Urdu line, a faithful literal translation as consecutive
  segments. Each segment lists the ids of the units it translates; use [] for English words
  that translate nothing. Joining a line's segment texts with spaces gives the whole line.
- poetic: an English rendering that works as poetry, one string per Urdu line.
- notes: at most 5 notes on wordplay, double meanings, allusions, symbols and idioms. Plain sentences.{role_rule}
"""


def load_glossary() -> str:
    terms = yaml.safe_load((ROOT / "data/glossary.yaml").read_text(encoding="utf-8"))["terms"]
    return "\n".join(f"- {k}: {v}" for k, v in terms.items())


def load_poem(spec: str) -> dict:
    """Return a poem as stanzas of blocks; each block is one couplet (or a lone line)."""
    nazm = NAZMS / f"{spec}.yaml"
    if nazm.exists():
        p = yaml.safe_load(nazm.read_text(encoding="utf-8"))
        blocks = []
        for si, stanza in enumerate(p["stanzas"]):
            for li in range(0, len(stanza), 2):
                blocks.append({"stanza": si, "first_line": li, "ur": stanza[li:li + 2], "roman": None})
        return {**{k: v for k, v in p.items() if k != "stanzas"}, "stanza_lengths": [len(s) for s in p["stanzas"]],
                "blocks": blocks}

    shers = [json.loads(l) for l in CORPUS.open(encoding="utf-8")]
    shers = sorted((s for s in shers if spec in s["ghazal"]), key=lambda s: s["index"])
    if not shers:
        raise SystemExit(f"no nazm in {NAZMS.relative_to(ROOT)} and no ghazal in the corpus matching {spec!r}")
    return {
        "id": spec, "form": "ghazal", "poet": POET_EN.get(shers[0]["poet"], shers[0]["poet"]),
        "title_ur": shers[0]["ur"][0], "title_roman": shers[0]["roman"][0],
        "source": "Text and transliteration: Rekhta, via github.com/amir9ume/urdu_ghazals_rekhta",
        "stanza_lengths": [2] * len(shers),
        "blocks": [{"stanza": s["index"], "first_line": 0, "ur": s["ur"], "roman": s["roman"],
                    "is_matla": s["is_matla"], "is_maqta": s["is_maqta"]} for s in shers],
    }


def poem_text(poem: dict) -> str:
    if poem["form"] == "ghazal":
        return "\n\n".join(f"Couplet {b['stanza'] + 1}:\n" + "\n".join(b["ur"]) + "\n" + "\n".join(b["roman"])
                           for b in poem["blocks"])
    out, si = [], -1
    for b in poem["blocks"]:
        if b["stanza"] != si:
            si = b["stanza"]
            out.append(f"\nStanza {si + 1}:")
        for k, line in enumerate(b["ur"]):
            out.append(f"  line {b['first_line'] + k + 1}: {line}")
    return "\n".join(out).strip()


def validate(ann: dict, words: list[list[str]]) -> list[str]:
    errors, n = [], len(words)
    units = ann.get("units") or []
    ids = {u.get("id") for u in units}
    for line in range(n):
        spans = sorted((u for u in units if u.get("line") == line), key=lambda u: u.get("start", -1))
        pos, broken = 0, False
        for u in spans:
            s, e = u.get("start"), u.get("end")
            if not isinstance(s, int) or not isinstance(e, int) or s != pos or e < s:
                errors.append(f"line {line}: unit {u.get('id')} spans {s}-{e}, expected to start at word {pos}")
                broken = True
                break
            pos = e + 1
        if not broken and pos != len(words[line]):
            errors.append(f"line {line}: units cover words 0-{pos - 1} but the line has words 0-{len(words[line]) - 1}")
    if any(u.get("line") not in range(n) for u in units):
        errors.append(f"every unit's line must be between 0 and {n - 1}")
    for p in ann.get("phrases") or []:
        missing = [x for x in p.get("units", []) if x not in ids]
        if missing:
            errors.append(f"phrase {p.get('id')} refers to unknown units {missing}")
    lit = ann.get("literal")
    if not isinstance(lit, list) or len(lit) != n:
        errors.append(f"literal must be a list of {n} lines of segments")
    else:
        for line in lit:
            for seg in line if isinstance(line, list) else []:
                missing = [x for x in seg.get("units", []) if x not in ids]
                if missing:
                    errors.append(f"literal segment {seg.get('text')!r} refers to unknown units {missing}")
    if not isinstance(ann.get("poetic"), list) or len(ann["poetic"]) != n:
        errors.append(f"poetic must be a list of {n} strings")
    if not all(isinstance(u.get("roman"), str) and u["roman"].strip() for u in units):
        errors.append("every unit needs a roman spelling")
    return errors


def ask(model: dict, prompt: str) -> tuple[dict | None, dict]:
    """A timeout or network error counts as a failed attempt instead of ending the run."""
    try:
        reply = rb.chat(model, prompt)
    except (rb.urllib.error.URLError, TimeoutError, ConnectionError) as e:
        print(f"  [{model['name']}] request failed: {e}")
        return None, {"usage": None, "error": str(e)}
    return rb.parse(reply["content"]), reply


def cache_path(poem: dict, model: dict, n: int) -> Path:
    """Finished couplets are saved as they complete, so a crash never loses them."""
    return OUT / ".cache" / f"{poem['id']}.{model['name']}" / f"{n}.json"


def overview_block(poem: dict, ov: dict) -> str:
    if not ov:
        return ""
    if poem["form"] == "ghazal":
        return f"\nWhat the ghazal is about: {ov.get('summary', '')}\n"
    stanzas = "\n".join(f"  stanza {s.get('stanza')}: {s.get('role')}" for s in ov.get("stanzas", []))
    turns = "\n".join(f"  - {t}" for t in ov.get("turns", []))
    return (f"\nHow the poem works as a whole (keep this arc in mind; a line's meaning can depend on where it falls):\n"
            f"Summary: {ov.get('summary', '')}\nSpeaker: {ov.get('speaker', '')}\nStanzas:\n{stanzas}\nTurns:\n{turns}\n"
            f"Other readings: {ov.get('readings', '')}\n")


def annotate_block(model: dict, poem: dict, ov: dict, glossary: str, b: dict, n: int) -> dict:
    cached = cache_path(poem, model, n)
    if cached.exists():
        print(f"  [{model['name']}] couplet {n + 1}: cached")
        return json.loads(cached.read_text(encoding="utf-8"))
    words = [line.split() for line in b["ur"]]
    tokens = "\n".join(f"Line {i}: " + " ".join(f"[{k}] {w}" for k, w in enumerate(ws)) for i, ws in enumerate(words))
    if b["roman"]:
        roman = "Roman transliteration:\n" + "\n".join(f"Line {i}: {r}" for i, r in enumerate(b["roman"]))
        roman_rule = "the unit's spelling, copied from the Roman line."
    else:
        roman, roman_rule = "", f"transliterate the unit {ROMAN_STYLE}."
    nazm = poem["form"] == "nazm"
    where = (f"couplet {n + 1} (stanza {b['stanza'] + 1}, lines {b['first_line'] + 1}-{b['first_line'] + len(b['ur'])})"
             if nazm else f"couplet {n + 1}")
    prompt = BLOCK_PROMPT.format(
        form=poem["form"], poet=poem["poet"], poem=poem_text(poem), overview=overview_block(poem, ov),
        glossary=glossary, where=where, tokens=tokens, roman=roman, roman_rule=roman_rule,
        role_field=',\n  "role": "..."' if nazm else "",
        role_rule="\n- role: in at most 20 words, what this couplet does in the poem's arc." if nazm else "",
    )
    cost, errors = 0.0, []
    for attempt in range(3):
        ann, reply = ask(model, prompt)
        cost += (reply.get("usage") or {}).get("cost") or 0
        errors = ["reply was not valid JSON"] if ann is None else validate(ann, words)
        if not errors:
            break
        print(f"  [{model['name']}] couplet {n + 1}: attempt {attempt + 1} invalid: {errors[:3]}")
        prompt += "\n\nYour previous answer had these problems; fix them and reply again:\n- " + "\n- ".join(errors)
    else:
        raise RuntimeError(f"[{model['name']}] couplet {n + 1} still invalid after 3 attempts: {errors}")
    for u in ann["units"]:
        u["ur"] = " ".join(words[u["line"]][u["start"]:u["end"] + 1])
    if not b["roman"]:
        b = {**b, "roman": [" ".join(u["roman"] for u in sorted((u for u in ann["units"] if u["line"] == i),
                                                               key=lambda u: u["start"])) for i in range(len(words))]}
    print(f"  [{model['name']}] couplet {n + 1}: ok ({len(ann['units'])} units, {len(ann.get('phrases') or [])} phrases, "
          f"{attempt + 1} attempt{'s' if attempt else ''}, ${cost:.3f})")
    result = {**b, "index": n, "words": words, **ann, "attempts": attempt + 1, "cost": cost}
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result


def annotate(poem: dict, model: dict, glossary: str) -> dict:
    ov_cache = cache_path(poem, model, -1).with_name("overview.json")
    if ov_cache.exists():
        ov, cost = json.loads(ov_cache.read_text(encoding="utf-8")), 0
    else:
        prompt = (OVERVIEW_GHAZAL if poem["form"] == "ghazal" else OVERVIEW_NAZM).format(
            poet=poem["poet"], title=poem.get("title_roman", ""), poem=poem_text(poem))
        for _ in range(3):
            ov, reply = ask(model, prompt)
            if ov:
                break
        ov = ov or {}
        cost = (reply.get("usage") or {}).get("cost") or 0
        if ov:
            ov_cache.parent.mkdir(parents=True, exist_ok=True)
            ov_cache.write_text(json.dumps(ov, ensure_ascii=False), encoding="utf-8")
    with ThreadPoolExecutor(max_workers=10) as pool:
        blocks = list(pool.map(lambda nb: annotate_block(model, poem, ov, glossary, nb[1], nb[0]),
                               enumerate(poem["blocks"])))
    out = {**{k: v for k, v in poem.items() if k != "blocks"}, "model": model["model"], "model_name": model["name"],
           "overview": ov, "blocks": blocks,
           "cost": round(cost + sum(b["cost"] for b in blocks), 4),
           "attempts": sum(b["attempts"] for b in blocks)}
    path = OUT / f"{poem['id']}.{model['name']}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"== [{model['name']}] wrote {path.relative_to(ROOT)}: ${out['cost']}, "
          f"{out['attempts']} requests for {len(blocks)} couplets")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("poem", help="nazm id in data/nazms/, or part of a ghazal's corpus id")
    ap.add_argument("--models", nargs="*", help="model names from config (default: the one with role: default)")
    args = ap.parse_args()

    rb.load_env()
    config = yaml.safe_load((ROOT / "config/models.yaml").read_text(encoding="utf-8"))["models"]
    models = [m for m in config if m["name"] in args.models] if args.models else \
             [m for m in config if m.get("role") == "default"]
    poem = load_poem(args.poem)
    print(f"== {poem['id']} ({poem['form']}, {len(poem['blocks'])} couplets): {', '.join(m['name'] for m in models)}")
    OUT.mkdir(parents=True, exist_ok=True)
    glossary = load_glossary()
    with ThreadPoolExecutor(max_workers=len(models)) as pool:
        list(pool.map(lambda m: annotate(poem, m, glossary), models))


if __name__ == "__main__":
    main()
