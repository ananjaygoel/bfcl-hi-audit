"""
Improved classifier. Two fixes over v1:

 1. Fuzzy back-transliteration matching. v1 required an exact consonant-skeleton
    substring match, which failed on stray matras the transliterator leaves behind
    (e.g. "न्यूयॉर्क" -> "nyUyaॉrka"). We now strip non-ASCII residue and match each
    token of the required value independently with a similarity threshold.

 2. Schema recovery. If a required value appears in the English function schema
    (enum, default, parameter name, or description), the model can recover it from
    the tool definition even when the Hindi prompt lost it. Those items are still
    answerable, so they must not be counted as unreachable.

Resulting labels per damaged argument:
  T1_back_transliteration  value survives in Devanagari; exact English string still demanded
  T3_schema_recoverable    value absent from prompt but present in the English schema
  T2_untraceable           value absent from both; English ground truth unreachable
"""
import json, re, unicodedata
from collections import Counter
from difflib import SequenceMatcher
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

FOLD = str.maketrans({"z": "j", "w": "v", "c": "k", "q": "k", "x": "k", "f": "p"})


def ascii_fold(s):
    s = unicodedata.normalize("NFKD", str(s)).lower()
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z0-9 ]", " ", s)          # drops untransliterated Devanagari residue
    s = s.translate(FOLD)
    s = re.sub(r"([a-z])\1+", r"\1", s)
    return re.sub(r"\s+", " ", s).strip()


def devoweled(s):
    return re.sub(r"[aeiou]", "", s)


def roman_tokens(text):
    r = ascii_fold(transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS))
    return [t for t in r.split() if t]


def token_found(tok, hay_tokens):
    """Is this romanised token present in the Hindi prompt, allowing spelling drift?"""
    t = devoweled(ascii_fold(tok))
    if len(t) < 2:
        return True                                   # too short to judge; do not penalise
    for h in hay_tokens:
        hd = devoweled(h)
        if not hd:
            continue
        if t in hd or hd in t:
            return True
        if SequenceMatcher(None, t, hd).ratio() >= 0.72:
            return True
    return False


def schema_blob(rec):
    return ascii_fold(json.dumps(rec.get("function", []), ensure_ascii=False))


def main():
    rows = [json.loads(l) for l in open("out/bfcl_hi_pairs.jsonl", encoding="utf-8")]
    hi_fn = {}
    for cat in ["simple", "multiple", "parallel", "parallel_multiple"]:
        for r in (json.loads(l) for l in
                  open(f"data/hi/BFCL_v2_live_{cat}.json", encoding="utf-8") if l.strip()):
            hi_fn[r["id"]] = r

    arg_tally, ex = Counter(), {"T1": [], "T2": [], "T3": []}
    for r in rows:
        toks = roman_tokens(r["prompt_hi"])
        sch = schema_blob(hi_fn.get(r["id"], {}))
        for a in r["lost_args"]:
            v = a["required_value"]
            words = [w for w in ascii_fold(v).split() if len(w) > 1]
            if words and all(token_found(w, toks) for w in words):
                lab = "T1_back_transliteration"
            elif ascii_fold(v) and ascii_fold(v) in sch:
                lab = "T3_schema_recoverable"
            else:
                lab = "T2_untraceable"
            a["damage_type"] = lab
            arg_tally[lab] += 1
            k = lab.split("_")[0]
            if len(ex[k]) < 6:
                ex[k].append((r["id"], v, r["prompt_en"][:80], r["prompt_hi"][:80]))
        types = {a["damage_type"] for a in r["lost_args"]}
        r["item_damage"] = ("T2_untraceable" if "T2_untraceable" in types
                            else "T3_schema_recoverable" if "T3_schema_recoverable" in types
                            else "T1_back_transliteration" if types else "none")

    with open("out/bfcl_hi_damage.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    n = len(rows)
    it = Counter(r["item_damage"] for r in rows)
    print(f"paired items: {n}\n")
    print("ITEM-LEVEL")
    for k in ["none", "T1_back_transliteration", "T3_schema_recoverable", "T2_untraceable"]:
        print(f"  {k:28s} {it[k]:5d}  ({100*it[k]/n:5.1f}%)")
    print("\nBY CATEGORY (T2 = English ground truth unreachable from Hindi prompt)")
    for cat in ["simple", "multiple", "parallel", "parallel_multiple"]:
        sub = [r for r in rows if r["category"] == cat]
        bad = sum(1 for r in sub if r["item_damage"] == "T2_untraceable")
        print(f"  {cat:20s} {bad:4d}/{len(sub):4d}  ({100*bad/len(sub):5.1f}%)")
    print("\nSAMPLES")
    for k in ["T1", "T3", "T2"]:
        print(f"\n [{k}]")
        for i, v, e, h in ex[k][:3]:
            print(f"   {i}  needs={v!r}")
            print(f"     EN: {e}")
            print(f"     HI: {h}")


if __name__ == "__main__":
    main()
