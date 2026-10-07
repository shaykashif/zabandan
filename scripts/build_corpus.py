"""Build a couplet-level corpus of public-domain poets from the Rekhta ghazals dump.

Input:  data/raw/urdu_ghazals_rekhta/dataset/dataset/<poet>/{ur,en,hi}/<ghazal-slug>
Output: data/processed/classical_shers.jsonl  (one couplet per line)
        data/processed/build_report.json      (counts and alignment problems)
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw/urdu_ghazals_rekhta/dataset/dataset"
OUT = ROOT / "data/processed"

# Poets who died before 1956, so their texts are public domain under life+70.
# Year of death is kept for the record.
PUBLIC_DOMAIN_POETS = {
    "ameer-khusrau": 1325,
    "wali-mohammad-wali": 1707,
    "naji-shakir": 1744,
    "meer-taqi-meer": 1810,
    "bahadur-shah-zafar": 1862,
    "mirza-ghalib": 1869,
    "meer-anees": 1874,
    "dagh-dehlvi": 1905,
    "altaf-hussain-hali": 1914,
    "akbar-allahabadi": 1921,
    "nazm-tabatabai": 1933,
    "allama-iqbal": 1938,
}


def read_lines(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip()]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"poets": {}, "skipped_ghazals": []}
    shers = []

    for poet, died in sorted(PUBLIC_DOMAIN_POETS.items()):
        poet_dir = RAW / poet
        n_ghazals = n_shers = 0
        for ur_path in sorted((poet_dir / "ur").iterdir()):
            slug = ur_path.name
            en_path = poet_dir / "en" / slug
            hi_path = poet_dir / "hi" / slug
            ur = read_lines(ur_path)
            en = read_lines(en_path) if en_path.exists() else []
            hi = read_lines(hi_path) if hi_path.exists() else []

            # Couplets are line pairs; skip ghazals whose scripts don't align.
            if len(ur) != len(en) or len(ur) % 2:
                report["skipped_ghazals"].append(
                    {"poet": poet, "slug": slug, "ur_lines": len(ur), "en_lines": len(en)}
                )
                continue

            n_ghazals += 1
            for i in range(0, len(ur), 2):
                idx = i // 2
                shers.append({
                    "id": f"{poet}/{slug}/{idx}",
                    "poet": poet,
                    "poet_died": died,
                    "ghazal": slug,
                    "index": idx,
                    "is_matla": idx == 0,
                    "is_maqta": i + 2 == len(ur),
                    "ur": ur[i:i + 2],
                    "roman": en[i:i + 2],
                    "hi": hi[i:i + 2] if len(hi) == len(ur) else None,
                })
                n_shers += 1
        report["poets"][poet] = {"died": died, "ghazals": n_ghazals, "shers": n_shers}

    with open(OUT / "classical_shers.jsonl", "w", encoding="utf-8") as f:
        for s in shers:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    report["total_shers"] = len(shers)
    (OUT / "build_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
