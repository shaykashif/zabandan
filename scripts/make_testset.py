"""Assemble the baseline test set from the couplet corpus.

Each entry names a couplet by corpus id, tags the difficulty it tests, and notes
what a good translation must preserve. The notes are drafts for the bilingual
reviewer to confirm or correct before scoring.

Output: data/testsets/baseline_v0.jsonl
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data/processed/classical_shers.jsonl"
OUT = ROOT / "data/testsets/baseline_v0.jsonl"

G = "mirza-ghalib/"
M = "meer-taqi-meer/"
I = "allama-iqbal/"
D = "dagh-dehlvi/"
Z = "bahadur-shah-zafar/"

# Tags: wordplay, double-meaning, sufi, stock-symbol, persianate, irony,
# takhallus, idiom, allusion, philosophical, archaic, imagery, control
TESTSET = [
    (G + "hazaaron-khvaahishen-aisii-ki-har-khvaahish-pe-dam-nikle-mirza-ghalib-ghazals/0",
     ["wordplay", "idiom"],
     "'nikle' works three ways: 'dam nikalna' (breath leaving, i.e. dying for each desire), "
     "'armān nikalna' (desires fulfilled) and 'kam nikalna' (turned out too few). "
     "The irony that even many fulfilled desires fall short must survive."),
    (G + "na-thaa-kuchh-to-khudaa-thaa-kuchh-na-hotaa-to-khudaa-hotaa-mirza-ghalib-ghazals/0",
     ["wordplay", "philosophical", "sufi"],
     "Built on 'honā' (to be). Before anything was, God was; had nothing been, God would be; "
     "my being drowned me. Had I not been, what would I have been? Implies merging into God "
     "(waḥdat al-wujūd). Keep the repetition of 'being'."),
    (G + "dil-e-naadaan-tujhe-huaa-kyaa-hai-mirza-ghalib-ghazals/0",
     ["control"],
     "Simple address to the naive heart: what has happened to you, what cure is there for this "
     "pain? Checks that the model doesn't over-embellish plain diction."),
    (G + "gair-len-mahfil-men-bose-jaam-ke-mirza-ghalib-ghazals/6",
     ["takhallus", "idiom", "irony"],
     "Contrast of 'nikammā' (useless) with 'aadmī the kaam ke' (a man of use). Self-mocking "
     "tone, pen name in the final couplet."),
    (G + "husn-e-mah-garche-ba-hangaam-e-kamaal-achchhaa-hai-mirza-ghalib-ghazals/9",
     ["irony", "takhallus"],
     "Sceptical irony: I know the truth about paradise, but it is a nice thought to keep the heart "
     "happy. Must not become pious or flatly atheist."),
    (G + "naqsh-fariyaadii-hai-kis-kii-shokhi-e-tahriir-kaa-mirza-ghalib-ghazals/0",
     ["persianate", "allusion"],
     "Famously opaque opening of the Diwan. Alludes to the Persian custom of petitioners wearing "
     "paper robes before a ruler: every figure in the picture wears paper, complaining against the "
     "playful pen of its maker. Needs annotation; a bare literal version is meaningless."),
    (G + "koii-ummiid-bar-nahiin-aatii-mirza-ghalib-ghazals/0",
     ["double-meaning", "idiom"],
     "'bar aana' = to be fulfilled. 'sūrat' = face and also way out or form: no face appears / no "
     "way appears. Flag the double sense."),
    (G + "huii-taakhiir-to-kuchh-baais-e-taakhiir-bhii-thaa-mirza-ghalib-ghazals/10",
     ["takhallus", "allusion"],
     "'Rekhta' is the old name for Urdu poetry; 'Mīr' is Mir Taqi Mir. Ghalib names himself and "
     "concedes an earlier master. Both names and the literary-history context need explaining."),
    (G + "bas-ki-dushvaar-hai-har-kaam-kaa-aasaan-honaa-mirza-ghalib-ghazals/0",
     ["wordplay", "philosophical"],
     "'aadmī' (a human being) vs 'insāñ' (a humane person): even a man can't easily be human. "
     "English 'man/human' tends to collapse the distinction. 'bas-ki' is archaic for 'so much so'."),
    (G + "husn-e-mah-garche-ba-hangaam-e-kamaal-achchhaa-hai-mirza-ghalib-ghazals/4",
     ["irony"],
     "Seeing the beloved brings colour to the lover's face, so she thinks the sick man is well. "
     "Keep the bittersweet misreading."),
    (G + "baaziicha-e-atfaal-hai-duniyaa-mire-aage-mirza-ghalib-ghazals/0",
     ["persianate", "imagery"],
     "'bāzīcha-e-atfāl' = a children's playground. The world is a spectacle staged before me "
     "night and day. Tone: detached and lofty, not dismissive."),
    (G + "hai-bas-ki-har-ik-un-ke-ishaare-men-nishaan-aur-mirza-ghalib-ghazals/10",
     ["takhallus", "wordplay"],
     "The repeated end word 'aur' means 'other/different': Ghalib's style of expression is "
     "something else. A boast that works through that final word."),
    (G + "ye-na-thii-hamaarii-qismat-ki-visaal-e-yaar-hotaa-mirza-ghalib-ghazals/10",
     ["sufi", "double-meaning", "takhallus", "irony"],
     "Mystical topics, such eloquence: we'd think you a saint (valī) if you weren't a "
     "wine-drinker. Leaves open whether the wine is literal or mystical; should not be resolved."),
    (G + "baaziicha-e-atfaal-hai-duniyaa-mire-aage-mirza-ghalib-ghazals/12",
     ["stock-symbol", "imagery"],
     "Hands can't move but the eyes still have life: leave the goblet and flask before me. "
     "Wine vessels as the poet's last attachment to life."),
    (G + "aah-ko-chaahiye-ik-umr-asar-hote-tak-mirza-ghalib-ghazals/0",
     ["idiom", "wordplay", "stock-symbol"],
     "A sigh needs a lifetime to take effect ('asar'); who lives long enough for your tresses to "
     "be won ('sar hona' = to be conquered, with 'sar' also meaning head/tip). Tresses (zulf) as "
     "the beloved's snare."),
    (M + "pattaa-pattaa-buutaa-buutaa-haal-hamaaraa-jaane-hai-meer-taqi-meer-ghazals/0",
     ["wordplay", "stock-symbol"],
     "Doubled words 'pattā pattā, buuTā buuTā' and the repeated 'jaane'. Every leaf knows my state; "
     "only the flower (the beloved) doesn't, though the whole garden does."),
    (M + "hastii-apnii-habaab-kii-sii-hai-meer-taqi-meer-ghazals/1",
     ["imagery", "control"],
     "Simple, famous simile: the delicacy of her lip is like a rose petal. Tests restraint."),
    (M + "ultii-ho-gaiin-sab-tadbiiren-kuchh-na-davaa-ne-kaam-kiyaa-meer-taqi-meer-ghazals/0",
     ["idiom", "wordplay"],
     "'kaam kiyā' (medicine did not work) answered by 'kaam tamām kiyā' (finished me off). "
     "The pun on 'kaam' carries the couplet."),
    (M + "ultii-ho-gaiin-sab-tadbiiren-kuchh-na-davaa-ne-kaam-kiyaa-meer-taqi-meer-ghazals/14",
     ["allusion", "irony", "takhallus"],
     "'qashqa' = Hindu forehead mark, 'dair' = temple. The conventional 'infidel of love' trope, "
     "not a literal conversion. Keep the irony and avoid flattening it into a religious claim."),
    (I + "khird-mandon-se-kyaa-puuchhuun-ki-merii-ibtidaa-kyaa-hai-allama-iqbal-ghazals/1",
     ["philosophical"],
     "'ḳhudī' is Iqbal's technical term for selfhood, not 'ego' or 'pride'. Raise it so high that "
     "God asks His servant, before each decree, what is your will?"),
    (I + "digar-guun-hai-jahaan-taaron-kii-gardish-tez-hai-saaqii-allama-iqbal-ghazals/5",
     ["stock-symbol", "takhallus", "allusion"],
     "Barren field ('kisht-e-vīrāñ') as the poet's people; a little moisture would make the soil "
     "fertile. The cupbearer (saaqī) is addressed. Political-revivalist allegory."),
    (D + "uzr-aane-men-bhii-hai-aur-bulaate-bhii-nahiin-dagh-dehlvi-ghazals-3/4",
     ["irony", "allusion"],
     "'chilman' = bamboo screen used for purdah. 'ḳhuub parda hai' is ironic: what a veil, "
     "neither quite hidden nor coming forward. Playful coquetry."),
    (D + "kaabe-kii-hai-havas-kabhii-kuu-e-butaan-kii-hai-dagh-dehlvi-ghazals/15",
     ["takhallus", "allusion"],
     "Only we know the language called Urdu; its fame spreads across Hindustan. Pen name 'Dāġh' "
     "(literally 'stain/scar') in the final couplet; pride of authorship."),
    (Z + "lagtaa-nahiin-hai-dil-miraa-ujde-dayaar-men-bahadur-shah-zafar-ghazals/4",
     ["takhallus", "allusion", "irony"],
     "Zafar was the last Mughal emperor and died in exile in Rangoon. 'Zafar' means 'victory'. "
     "Not even two yards of earth in the beloved's lane (homeland). The attribution of this ghazal "
     "is disputed; the reviewer should check."),
    (Z + "lagtaa-nahiin-hai-dil-miraa-ujde-dayaar-men-bahadur-shah-zafar-ghazals/0",
     ["persianate", "allusion"],
     "My heart finds no rest in this ruined land; whose fortune ever held in this impermanent world "
     "('ālam-e-nā-pāedār')? Elegiac tone."),
    ("akbar-allahabadi/gamza-nahiin-hotaa-ki-ishaaraa-nahiin-hotaa-akbar-allahabadi-ghazals/5",
     ["irony"],
     "Double standard: we sigh and are disgraced, they murder and no one talks. Akbar is a "
     "satirist, so a political reading is also open."),
    ("akbar-allahabadi/huun-main-parvaana-magar-shama-to-ho-raat-to-ho-akbar-allahabadi-ghazals/0",
     ["stock-symbol"],
     "Moth and candle (parvāna/sham'a): I am the moth, but let there be a candle, let there be "
     "night; ready to give my life, if only there were a reason."),
    ("wali-mohammad-wali/huaa-zaahir-khat-e-ruu-e-nigaar-aahista-aahista-wali-mohammad-wali-ghazals/0",
     ["archaic", "imagery", "double-meaning"],
     "Early Deccani Urdu ('jyuuñ' = like). 'ḳhat' is the first down on the beloved's cheek, "
     "conventionally a youth's, and also means 'line/script'. Slowly, the way spring comes to a garden."),
    ("altaf-hussain-hali/burii-aur-bhalii-sab-guzar-jaaegii-altaf-hussain-hali-ghazals/0",
     ["control", "idiom"],
     "Plain consolation: good and bad will all pass; this boat will cross somehow. Tests whether "
     "simple Urdu stays simple in English."),
    ("meer-taqi-meer/aae-hain-miir-kaafir-ho-kar-khudaa-ke-ghar-men-mir-taqi-mir-ghazals/0",
     ["allusion", "irony", "takhallus"],
     "Mir comes to the house of God (mosque/Kaaba) as an infidel: forehead mark and sacred thread "
     "('zunnār'). Love's transgression as a trope. Needs cultural annotation."),
]


def main() -> None:
    by_id = {}
    for line in CORPUS.open(encoding="utf-8"):
        s = json.loads(line)
        by_id[s["id"]] = s

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for n, (sid, tags, note) in enumerate(TESTSET, 1):
            s = by_id[sid]
            f.write(json.dumps({
                "test_id": f"b{n:02d}",
                "sher_id": s["id"],
                "poet": s["poet"],
                "ur": s["ur"],
                "roman": s["roman"],
                "tags": tags,
                "nuance_note": note,
                "note_status": "draft",
            }, ensure_ascii=False) + "\n")
    print(f"wrote {len(TESTSET)} couplets to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
