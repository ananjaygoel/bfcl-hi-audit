"""
Measure, for each language condition, how many ground-truth string arguments the
AST checker demands are actually *present in the prompt the model sees*.

This is a property of the benchmark, not of any model: it is an upper bound on
achievable exact-match accuracy before a single token is generated.
"""
import json, re, unicodedata
from collections import defaultdict

CATS = ["simple", "multiple", "parallel", "parallel_multiple"]


def load(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def user_text(rec):
    q = rec["question"]
    while isinstance(q, list) and q and isinstance(q[0], list):
        q = q[0]
    return " ".join(t.get("content", "") for t in q if t.get("role") == "user")


def norm(s):
    s = unicodedata.normalize("NFKC", str(s)).lower()
    return re.sub(r"[\s/_\-.,]+", "", s)


def present(v, t):
    v, t = norm(v), norm(t)
    return (not v) or v in t


def gt_strings(ans):
    out = set()
    for call in ans.get("ground_truth", []):
        for _, params in call.items():
            for _, vals in params.items():
                for x in (vals if isinstance(vals, list) else [vals]):
                    if isinstance(x, str) and len(x.strip()) > 1:
                        out.add(x.strip())
    return out


def main():
    hing = {r["id"]: r for r in load("out/bfcl_hinglish.jsonl")}
    agg = defaultdict(lambda: {"args_ok": 0, "args": 0, "items_ok": 0, "items": 0})
    per_cat = defaultdict(lambda: defaultdict(lambda: [0, 0]))

    for cat in CATS:
        en = {r["id"]: r for r in load(f"data/en_v2/BFCL_v2_live_{cat}.json")}
        hi = {r["id"]: r for r in load(f"data/hi/BFCL_v2_live_{cat}.json")}
        ans = {r["id"]: r for r in load(f"data/en_v2/possible_answer/BFCL_v2_live_{cat}.json")}
        for i, a in ans.items():
            if i not in en or i not in hi or i not in hing:
                continue
            vals = gt_strings(a)
            if not vals:
                continue
            texts = {"English": user_text(en[i]),
                     "Hindi (Devanagari)": user_text(hi[i]),
                     "Hinglish (Roman)": hing[i]["question"][0]["content"]}
            for cond, txt in texts.items():
                ok = sum(1 for v in vals if present(v, txt))
                agg[cond]["args_ok"] += ok
                agg[cond]["args"] += len(vals)
                agg[cond]["items"] += 1
                full = (ok == len(vals))
                agg[cond]["items_ok"] += full
                per_cat[cat][cond][0] += full
                per_cat[cat][cond][1] += 1

    print("CEILING ON EXACT-MATCH ACCURACY (share of items where every required")
    print("English string argument is visible in the prompt the model receives)\n")
    print(f"{'condition':22s} {'items fully recoverable':>24s} {'required args present':>22s}")
    for cond in ["English", "Hindi (Devanagari)", "Hinglish (Roman)"]:
        d = agg[cond]
        print(f"{cond:22s} {d['items_ok']:6d}/{d['items']:<5d} ({100*d['items_ok']/d['items']:5.1f}%)"
              f"  {d['args_ok']:6d}/{d['args']:<5d} ({100*d['args_ok']/d['args']:5.1f}%)")

    print("\nBY CATEGORY (items fully recoverable)")
    print(f"{'category':22s} {'English':>10s} {'Hindi':>10s} {'Hinglish':>10s}")
    for cat in CATS:
        cells = []
        for cond in ["English", "Hindi (Devanagari)", "Hinglish (Roman)"]:
            ok, n = per_cat[cat][cond]
            cells.append(f"{100*ok/n:9.1f}%" if n else "        -")
        print(f"{cat:22s} " + " ".join(cells))


if __name__ == "__main__":
    main()
