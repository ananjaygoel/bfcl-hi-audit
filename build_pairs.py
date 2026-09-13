"""
Pair BFCL-Hi (nvidia/BFCL-Hi, GCP-translated) with the exact English BFCL v2 Live
revision its function schemas match (gorilla-llm HF rev 1726e89933), then scan for
ground-truth evidence that translation removed from the prompt.

Core check ("unrecoverable argument"):
  A ground-truth string argument value appears verbatim in the English prompt
  but does NOT appear in the Hindi prompt. In that case the AST checker demands a
  string the Hindi prompt no longer contains, so the item is unscoreable by
  construction -- any model failure on it is a benchmark artifact, not a model error.
"""
import json, os, re, unicodedata
from collections import defaultdict

CATS = ["simple", "multiple", "parallel", "parallel_multiple"]
HI_DIR, EN_DIR = "data/hi", "data/en_v2"


def load(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def user_text(rec):
    q = rec["question"]
    while isinstance(q, list) and q and isinstance(q[0], list):
        q = q[0]
    return " ".join(t.get("content", "") for t in q if t.get("role") == "user")


def gt_values(ans_rec):
    """Yield (func_name, param, value) for every ground-truth leaf value."""
    out = []
    for call in ans_rec.get("ground_truth", []):
        for fname, params in call.items():
            for p, vals in params.items():
                vals = vals if isinstance(vals, list) else [vals]
                for v in vals:
                    out.append((fname, p, v))
    return out


def norm(s):
    s = unicodedata.normalize("NFKC", str(s)).lower()
    return re.sub(r"\s+", " ", s).strip()


def present(value, text):
    """Is this string value recoverable from the text?"""
    v, t = norm(value), norm(text)
    if not v or v in ("", "none", "null"):
        return True
    if v in t:
        return True
    # allow separator variants: slashes, dashes, underscores, dots
    loose = re.sub(r"[\s/_\-.,]+", "", v)
    if loose and loose in re.sub(r"[\s/_\-.,]+", "", t):
        return True
    return False


def main():
    rows, stats = [], defaultdict(int)
    for cat in CATS:
        hi = {r["id"]: r for r in load(f"{HI_DIR}/BFCL_v2_live_{cat}.json")}
        en = {r["id"]: r for r in load(f"{EN_DIR}/BFCL_v2_live_{cat}.json")}
        ans = {r["id"]: r for r in load(f"{EN_DIR}/possible_answer/BFCL_v2_live_{cat}.json")}
        for i, h in hi.items():
            if i not in en or i not in ans:
                continue
            et, ht = user_text(en[i]), user_text(h)
            broken, checked = [], 0
            for fname, p, v in gt_values(ans[i]):
                if not isinstance(v, str) or not v.strip():
                    continue
                checked += 1
                if present(v, et) and not present(v, ht):
                    broken.append({"function": fname, "param": p, "required_value": v})
            rows.append({
                "id": i, "category": cat,
                "prompt_en": et, "prompt_hi": ht,
                "n_string_args_checked": checked,
                "n_args_lost_in_translation": len(broken),
                "lost_args": broken,
                "unrecoverable": bool(broken),
            })
            stats[cat + "_total"] += 1
            if broken:
                stats[cat + "_unrecoverable"] += 1

    os.makedirs("out", exist_ok=True)
    with open("out/bfcl_hi_pairs.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    tot = len(rows)
    bad = sum(1 for r in rows if r["unrecoverable"])
    print(f"paired items: {tot}")
    print(f"items with >=1 ground-truth string argument destroyed by translation: "
          f"{bad} ({100*bad/tot:.1f}%)")
    print()
    for cat in CATS:
        t, b = stats[cat + "_total"], stats[cat + "_unrecoverable"]
        if t:
            print(f"  {cat:20s} {b:4d}/{t:4d}  ({100*b/t:5.1f}%)")


if __name__ == "__main__":
    main()
