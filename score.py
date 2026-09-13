#!/usr/bin/env python3
"""
Score predictions with the OFFICIAL BFCL v2 AST checker, then join every failure
against the translation-damage label for that item.

That join is the paper's central table: it splits the Hindi accuracy drop into
"the model got it wrong" and "the benchmark made it unwinnable".

  python score.py out/preds/*.jsonl
"""
import glob, json, os, re, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "bfcl_checker"))
os.chdir(os.path.join(HERE, "bfcl_checker"))
from checker import ast_checker
from ast_parse_py import ast_parse
os.chdir(HERE)

CATS = ["simple", "multiple", "parallel", "parallel_multiple"]


def load(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def extract_call(text):
    """Pull the [func(...)] block out of a chat model's reply."""
    if not text:
        return None
    t = text.strip()
    t = re.sub(r"^```(?:python|json)?|```$", "", t, flags=re.M).strip()
    m = re.search(r"\[[^\[\]]*\([\s\S]*?\)[\s\S]*?\]", t)
    return m.group(0) if m else (t if t.startswith("[") else None)


def main(paths):
    funcs, answers, damage = {}, {}, {}
    for cat in CATS:
        for r in load(f"data/en_v2/BFCL_v2_live_{cat}.json"):
            funcs[r["id"]] = r["function"]
        for r in load(f"data/en_v2/possible_answer/BFCL_v2_live_{cat}.json"):
            answers[r["id"]] = r["ground_truth"]
    for r in load("out/bfcl_hi_damage.jsonl"):
        damage[r["id"]] = r["item_damage"]

    results = defaultdict(lambda: defaultdict(list))
    for p in paths:
        for rec in load(p):
            tid, cond = rec["id"], rec["condition"]
            if tid not in answers:
                continue
            ok, why = False, "no_output"
            call = extract_call(rec.get("raw_response"))
            if call:
                try:
                    parsed = ast_parse(call)
                    out = ast_checker(funcs[tid], parsed, answers[tid],
                                      "Python", "live_" + rec["category"], rec["model"])
                    ok = bool(out.get("valid"))
                    why = "correct" if ok else out.get("error_type", "wrong")
                except Exception as e:
                    why = f"unparseable:{type(e).__name__}"
            results[(rec["model"], cond)][rec["category"]].append(
                {"id": tid, "correct": ok, "why": why, "damage": damage.get(tid, "unknown")})

    print("ACCURACY BY CONDITION (official BFCL AST checker)\n")
    print(f"{'model':34s} {'cond':10s} {'n':>5s} {'acc':>7s}")
    for (model, cond), cats in sorted(results.items()):
        rows = [r for v in cats.values() for r in v]
        acc = 100 * sum(r["correct"] for r in rows) / max(1, len(rows))
        print(f"{model[:34]:34s} {cond:10s} {len(rows):5d} {acc:6.1f}%")

    print("\n\nTHE KEY TABLE -- accuracy split by whether translation damaged the item")
    print("(clean = our scan found the answer still reachable from the prompt)\n")
    for (model, cond), cats in sorted(results.items()):
        rows = [r for v in cats.values() for r in v]
        if cond == "en":
            continue
        buckets = defaultdict(list)
        for r in rows:
            buckets["clean" if r["damage"] == "none" else r["damage"]].append(r["correct"])
        print(f"  {model[:30]} [{cond}]")
        for k in ["clean", "T1_back_transliteration", "T3_schema_recoverable", "T2_untraceable"]:
            v = buckets.get(k, [])
            if v:
                print(f"    {k:28s} n={len(v):5d}  acc={100*sum(v)/len(v):5.1f}%")
        print()

    os.makedirs("out", exist_ok=True)
    with open("out/scored.jsonl", "w", encoding="utf-8") as f:
        for (model, cond), cats in results.items():
            for cat, rows in cats.items():
                for r in rows:
                    f.write(json.dumps({"model": model, "condition": cond,
                                        "category": cat, **r}, ensure_ascii=False) + "\n")
    print("per-item results written to out/scored.jsonl")


if __name__ == "__main__":
    args = sys.argv[1:] or glob.glob("out/preds/*.jsonl")
    if not args:
        raise SystemExit("no prediction files found -- run run_eval.py first")
    main(args)
