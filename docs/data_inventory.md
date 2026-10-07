# Data inventory (Phase 0)

## Rekhta Ghazals (amir9ume/urdu_ghazals_rekhta)

Cloned to `data/raw/urdu_ghazals_rekhta` (gitignored). 30 poets, 1,314 ghazals, each in
Urdu script (`ur`), Devanagari (`hi`) and Roman transliteration (`en`). There are no English
translations.

- Files line up one-to-one across scripts; two lines make one couplet. Ghazals are capped at 50
  per poet, except Ghalib (234).
- The Roman text marks the Persian `-e-` links that Urdu script leaves unwritten
  (`tāqat-e-bedād-e-intizār` vs `طاقت بیداد انتظار`). That helps the analysis step.
- `dataset.zip` contains `__MACOSX` junk; it is deleted after extraction.
- A few Iqbal ghazals have no Devanagari file.

### Classical corpus

`scripts/build_corpus.py` keeps the 12 poets who died before 1956 and writes
`data/processed/classical_shers.jsonl`: **5,148 couplets**. 12 ghazals are skipped because their
Urdu and Roman line counts differ (listed in `build_report.json`).

| Poet | Died | Ghazals | Couplets |
|---|---|---|---|
| Mirza Ghalib | 1869 | 223 | 1,786 |
| Dagh Dehlvi | 1905 | 50 | 707 |
| Bahadur Shah Zafar | 1862 | 50 | 439 |
| Meer Taqi Meer | 1810 | 50 | 421 |
| Akbar Allahabadi | 1921 | 50 | 388 |
| Allama Iqbal | 1938 | 49 | 368 |
| Nazm Tabatabai | 1933 | 26 | 325 |
| Altaf Hussain Hali | 1914 | 28 | 291 |
| Wali Mohammad Wali | 1707 | 40 | 276 |
| Meer Anees | 1874 | 9 | 84 |
| Naji Shakir | 1744 | 10 | 58 |
| Ameer Khusrau | 1325 | 1 | 5 |

Excluded as likely still in copyright: Faiz, Faraz, Jaun Eliya, Parveen Shakir, Gulzar, Javed
Akhtar, Sahir, Firaq, Jigar (died 1960) and the other modern poets.

### Rights

The repo's MIT licence covers the scrape, not Rekhta's content. The classical poems themselves
are public domain. Rekhta's transliterations are their editorial work, so they are fine for
internal testing, but check before training on them or publishing them.

## Urdu_Rekhta (mahwizzzz/Urdu_Rekhta)

Not downloaded. It is gated behind a Hugging Face login and terms acceptance, which the account
owner has to do. The dataset has no README; its listing says 1K–10K rows, 707 KB.

## Test set

`scripts/make_testset.py` writes `data/testsets/baseline_v0.jsonl`: 30 couplets from 8 poets,
tagged by difficulty (wordplay, double meaning, Sufi, stock symbols, Persian vocabulary, irony,
pen name, idiom, allusion, philosophy, archaic Deccani, plain controls). Each has a
`nuance_note` saying what a good translation must keep. The notes are **drafts** for the
bilingual reviewer to correct before scoring.
