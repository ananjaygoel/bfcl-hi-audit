"""
Build the Hinglish (Roman-script, code-mixed) condition of BFCL.

Two stages, both deterministic and reproducible -- no model calls.

STAGE 1  Romanise the Devanagari with Hindi schwa deletion.
  Sanskrit transliterators keep the inherent 'a' on every consonant, so
  "आप कर सकते हैं" comes out "Apa kara sakate haiM". Hindi deletes those schwas.
  We delete word-final schwa and the penultimate medial schwa, then map the
  scheme's long-vowel capitals onto the doubled spellings people actually type.

STAGE 2  Restore English spans.
  Real Hinglish keeps proper nouns and technical terms in Latin script -- people
  type "Joel Zwick", not "jol zvik". BFCL-Hi transliterated them into Devanagari.
  For every ground-truth string value we locate its Devanagari span in the Hindi
  prompt by romanised consonant-skeleton match and splice the original English
  token back in.

This makes Hinglish the condition where the grader's required strings are
*visible in Latin script*, which is why we expect it to outscore Devanagari Hindi
on an AST checker that demands exact English matches.
"""
import json, re, unicodedata
from difflib import SequenceMatcher
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

CATS = ["simple", "multiple", "parallel", "parallel_multiple"]
CONS = "bcdfghjklmnpqrstvwxyz"

# scheme capitals / digraphs -> informal spellings people actually type
VOWEL_MAP = [("R^i", "ri"), ("A", "aa"), ("I", "ee"), ("U", "oo"), ("M", "n"),
             ("H", "h"), ("~N", "n"), ("~n", "n"), (".n", "n"), (".m", "n"),
             ("oa", "o"), ("Ch", "chh"), (".D", "r"), (".d", "r"), ("ph", "f"),
             ("|", "."), ("\u0964", ".")]
RETRO = str.maketrans({"T": "t", "D": "d", "N": "n", "S": "s", "L": "l", "R": "r"})


def _deschwa(word):
    """Delete Hindi schwas the transliterator kept."""
    w = word
    # penultimate medial schwa, long words only: sakate -> sakte, apane -> apne.
    # Short words keep it ("rahaa" must not become "rhaa", "bataa" not "btaa").
    if len(w) >= 6:
        w = re.sub(rf"([{CONS}]{{1,2}})a([{CONS}]{{1,2}})(e|i|ee|o|aa)$", r"\1\2\3", w)
    # word-final schwa: aapa -> aap, eka -> ek  (keep 2-letter words: ka, na, se)
    if len(w) >= 3 and w.endswith("a") and w[-2] in CONS:
        w = w[:-1]
    return w


def romanise(text):
    out = []
    for chunk in re.split(r"(\s+)", text):
        if not chunk.strip():
            out.append(chunk)
            continue
        if not re.search(r"[\u0900-\u097F]", chunk):
            out.append(chunk)                       # already Latin / digits: leave alone
            continue
        r = transliterate(chunk, sanscript.DEVANAGARI, sanscript.OPTITRANS)
        for a, b in VOWEL_MAP:
            r = r.replace(a, b)
        r = r.translate(RETRO)
        r = re.sub(r"\.(?=[A-Za-z])", "", r)        # strip scheme markers: hoo.n -> hoon
        r = re.sub(r"[\u0900-\u097F]", "", r)       # drop any residue the scheme missed
        lead = re.match(r"^\W*", r).group(0)
        tail = re.search(r"\W*$", r).group(0)
        core = r[len(lead):len(r) - len(tail) if tail else None]
        out.append(lead + _deschwa(core.lower()) + tail)
    return re.sub(r"\s+", " ", "".join(out)).strip()


# ---------- stage 2: English restoration ----------
FOLD = str.maketrans({"z": "j", "w": "v", "c": "k", "q": "k", "x": "k", "f": "p"})


def skel(s):
    s = unicodedata.normalize("NFKD", str(s)).lower()
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z0-9]", "", s).translate(FOLD)
    s = re.sub(r"([a-z])\1+", r"\1", s)
    return re.sub(r"[aeiou]", "", s)


def similar(a, b):
    sa, sb = skel(a), skel(b)
    if not sa or not sb:
        return 0.0
    if sa == sb or (len(sa) > 2 and (sa in sb or sb in sa)):
        return 1.0
    return SequenceMatcher(None, sa, sb).ratio()


SKIP = re.compile(r"^[\d\s\-:/.,]+$")


def restore_english(hinglish, english_values):
    """Splice original English tokens back over their romanised Hindi counterparts."""
    toks = hinglish.split(" ")
    used = set()
    for val in sorted(english_values, key=lambda v: -len(v)):
        # never splice dates, times or bare numbers: the digits already survived
        # translation intact, and overwriting them corrupts the prompt.
        if SKIP.match(val):
            continue
        words = [w for w in re.split(r"[\s,]+", val) if len(w) > 1]
        if not words:
            continue
        n = len(words)
        best, best_i = 0.75, None
        for i in range(len(toks) - n + 1):
            if any(j in used for j in range(i, i + n)):
                continue
            win = toks[i:i + n]
            # every English word must match its own token, so a value cannot eat
            # an unrelated neighbouring word ("aap sosalito" != "Sausalito, CA").
            if not all(similar(win[k], words[k]) >= 0.6 for k in range(n)):
                continue
            sc = similar(" ".join(win), val)
            if sc > best:
                best, best_i = sc, i
        if best_i is not None:
            punct = re.search(r"\W*$", toks[best_i + n - 1]).group(0)
            toks[best_i] = val + punct
            for j in range(best_i + 1, best_i + n):
                toks[j] = ""
            used.update(range(best_i, best_i + n))
    return re.sub(r"\s+", " ", " ".join(t for t in toks if t)).strip()


def user_text(rec):
    q = rec["question"]
    while isinstance(q, list) and q and isinstance(q[0], list):
        q = q[0]
    return " ".join(t.get("content", "") for t in q if t.get("role") == "user")


def gt_strings(ans):
    out = set()
    for call in ans.get("ground_truth", []):
        for _, params in call.items():
            for _, vals in params.items():
                for v in (vals if isinstance(vals, list) else [vals]):
                    if isinstance(v, str) and len(v.strip()) > 1:
                        out.add(v.strip())
    return out


def main():
    made = 0
    with open("out/bfcl_hinglish.jsonl", "w", encoding="utf-8") as fout:
        for cat in CATS:
            hi = [json.loads(l) for l in open(f"data/hi/BFCL_v2_live_{cat}.json", encoding="utf-8") if l.strip()]
            ans = {r["id"]: r for r in (json.loads(l) for l in
                   open(f"data/en_v2/possible_answer/BFCL_v2_live_{cat}.json", encoding="utf-8") if l.strip())}
            for rec in hi:
                hi_txt = user_text(rec)
                rom = romanise(hi_txt)
                hing = restore_english(rom, gt_strings(ans.get(rec["id"], {})))
                new = json.loads(json.dumps(rec, ensure_ascii=False))
                new["question"] = [{"role": "user", "content": hing}]
                new["_hindi_source"] = hi_txt
                new["_romanised_only"] = rom
                new["category"] = cat
                fout.write(json.dumps(new, ensure_ascii=False) + "\n")
                made += 1
    print("hinglish items written:", made)


if __name__ == "__main__":
    main()
