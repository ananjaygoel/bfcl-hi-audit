#!/usr/bin/env python3
"""
Run a model over BFCL in three language conditions: English, Hindi, Hinglish.

Uses BFCL's own prompting format (DEFAULT_SYSTEM_PROMPT + USER_PROMPT_FOR_CHAT_MODEL)
so results are comparable with the published leaderboard rather than a private
reimplementation.

Built for free tiers: it rate-limits itself, backs off on 429, and is resumable --
rerun the same command tomorrow and it picks up where the daily cap stopped it.

  export GROQ_API_KEY=...
  python run_eval.py --provider groq --model openai/gpt-oss-120b --condition en
  python run_eval.py --provider groq --model openai/gpt-oss-120b --condition hi
  python run_eval.py --provider groq --model openai/gpt-oss-120b --condition hinglish
"""
import argparse, json, os, sys, time, urllib.error, urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "bfcl_checker"))
from model_handler.constant import DEFAULT_SYSTEM_PROMPT, USER_PROMPT_FOR_CHAT_MODEL

CATS = ["simple", "multiple", "parallel", "parallel_multiple"]
PROVIDERS = {
    "groq": ("https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/models", "GEMINI_API_KEY"),
}


def load(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def user_text(rec):
    q = rec["question"]
    while isinstance(q, list) and q and isinstance(q[0], list):
        q = q[0]
    return " ".join(t.get("content", "") for t in q if t.get("role") == "user")


def items(condition, cat):
    """Return (id, question_text, function_list) for one condition and category."""
    if condition == "en":
        recs = load(f"data/en_v2/BFCL_v2_live_{cat}.json")
    elif condition == "hi":
        recs = load(f"data/hi/BFCL_v2_live_{cat}.json")
    elif condition == "hinglish":
        recs = load(f"out/hinglish_bfcl/BFCL_v2_live_{cat}.json")
    else:
        raise SystemExit(f"unknown condition: {condition}")
    return [(r["id"], user_text(r), r["function"]) for r in recs]


def build_messages(question, functions):
    user = USER_PROMPT_FOR_CHAT_MODEL.format(
        language_specific_hint="", functions=json.dumps(functions, ensure_ascii=False))
    return [{"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": user + "\n\n" + question}]


def post(url, payload, headers, timeout=90):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def call_model(provider, model, messages, key):
    if provider == "gemini":
        url = f"{PROVIDERS['gemini'][0]}/{model}:generateContent?key={key}"
        payload = {
            "system_instruction": {"parts": [{"text": messages[0]["content"]}]},
            "contents": [{"role": "user", "parts": [{"text": messages[1]["content"]}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 1024},
        }
        d = post(url, payload, {})
        return d["candidates"][0]["content"]["parts"][0]["text"]
    url = PROVIDERS[provider][0]
    payload = {"model": model, "messages": messages, "temperature": 0, "max_tokens": 1024}
    d = post(url, payload, {"Authorization": f"Bearer {key}"})
    return d["choices"][0]["message"]["content"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", required=True, choices=list(PROVIDERS))
    ap.add_argument("--model", required=True)
    ap.add_argument("--condition", required=True, choices=["en", "hi", "hinglish"])
    ap.add_argument("--categories", default=",".join(CATS))
    ap.add_argument("--limit", type=int, default=0, help="per category; 0 = all")
    ap.add_argument("--rpm", type=float, default=25, help="requests per minute cap")
    ap.add_argument("--outdir", default="out/preds")
    args = ap.parse_args()

    key = os.environ.get(PROVIDERS[args.provider][1])
    if not key:
        raise SystemExit(f"set {PROVIDERS[args.provider][1]} in your environment first")

    os.makedirs(args.outdir, exist_ok=True)
    tag = f"{args.model.replace('/', '_')}__{args.condition}"
    path = os.path.join(args.outdir, f"{tag}.jsonl")
    done = {json.loads(l)["id"] for l in open(path, encoding="utf-8")} if os.path.exists(path) else set()
    if done:
        print(f"resuming: {len(done)} already done in {path}")

    gap, todo = 60.0 / args.rpm, []
    for cat in args.categories.split(","):
        rows = items(args.condition, cat)
        if args.limit:
            rows = rows[:args.limit]
        todo += [(cat, *r) for r in rows if r[0] not in done]
    print(f"{len(todo)} items to run [{args.condition}] on {args.model}")

    n_ok = n_err = 0
    with open(path, "a", encoding="utf-8") as out:
        for k, (cat, tid, q, fns) in enumerate(todo, 1):
            t0 = time.time()
            text, err, delay = None, None, 4
            for attempt in range(6):
                try:
                    text = call_model(args.provider, args.model, build_messages(q, fns), key)
                    break
                except urllib.error.HTTPError as e:
                    body = e.read().decode()[:200]
                    if e.code in (429, 500, 502, 503, 529):
                        if e.code == 429 and attempt >= 3:
                            err = f"rate limited: {body}"
                            break
                        time.sleep(delay)
                        delay *= 2
                        continue
                    err = f"HTTP {e.code}: {body}"
                    break
                except Exception as e:
                    err = f"{type(e).__name__}: {e}"
                    time.sleep(delay)
                    delay *= 2
            rec = {"id": tid, "category": cat, "condition": args.condition,
                   "model": args.model, "question": q,
                   "raw_response": text, "error": err}
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out.flush()
            n_ok += text is not None
            n_err += err is not None
            if k % 25 == 0 or k == len(todo):
                print(f"  {k}/{len(todo)}  ok={n_ok} err={n_err}", flush=True)
            if err and "rate limited" in err:
                print("  hit the daily cap -- stopping. Rerun tomorrow to resume.")
                break
            time.sleep(max(0.0, gap - (time.time() - t0)))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
