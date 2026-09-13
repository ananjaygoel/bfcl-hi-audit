# BFCL-Hi audit — how to run the experiments

Everything here runs on a free API tier. No paid inference is needed.

## What is in this bundle

| Path | What it is |
|---|---|
| `data/en_v2/` | English BFCL v2 Live, at gorilla commit `1726e89933` — the revision whose function schemas match BFCL-Hi exactly (258/258 on `simple`) |
| `data/hi/` | NVIDIA's BFCL-Hi, unmodified (`nvidia/BFCL-Hi`, CC-BY-4.0) |
| `out/hinglish_bfcl/` | The Hinglish condition, drop-in BFCL format, with the English answer keys |
| `bfcl_checker/` | The official BFCL v2 AST checker, fetched from gorilla commit `30124c4399` |
| `run_eval.py` | Queries a model across the three conditions |
| `score.py` | Scores with the official checker and joins failures to the damage labels |
| `build_pairs.py`, `classify_v2.py` | Pair the corpora and label translation damage |
| `make_hinglish.py` | Builds the Hinglish condition |
| `compare_conditions.py` | Recoverability ceilings, no model calls needed |

## Step 1 — get a key

Groq is the recommended provider: its free limits are published, and
`openai/gpt-oss-120b` is one of the models NVIDIA reported on BFCL-Hi, so your
English and Hindi numbers are directly comparable to their table.

```bash
export GROQ_API_KEY=your_key_here
```

Google AI Studio (`--provider gemini`) and OpenRouter also work.

## Step 2 — run the three conditions

```bash
python run_eval.py --provider groq --model openai/gpt-oss-120b --condition en
python run_eval.py --provider groq --model openai/gpt-oss-120b --condition hi
python run_eval.py --provider groq --model openai/gpt-oss-120b --condition hinglish
```

Start small to confirm your key works before committing quota:

```bash
python run_eval.py --provider groq --model openai/gpt-oss-120b --condition hi --limit 5
```

**Quota planning.** All four categories are 1,335 items, so all three conditions
are 4,005 calls. Groq's published free limit on `openai/gpt-oss-120b` is 1,000
requests a day, and a token ceiling usually binds before the request count does.
So expect this to span several days. The runner is resumable — rerun the same
command and it skips what it already has. If you would rather finish in one day,
use `--limit 150` per category, which gives roughly 1,300 calls across all three
conditions and is still a large enough sample for the paper.

`--rpm` defaults to 25, just under Groq's 30/minute. Lower it if you see 429s.

## Step 3 — score

```bash
python score.py
```

This prints accuracy per condition, then the table the paper is built on:
Hindi accuracy split by whether our scan found the item damaged by translation.

The prediction that matters: on items labelled `clean`, the Hindi and English
scores should be close. If the overall Hindi gap is large but the clean-item gap
is small, the reported multilingual gap is mostly a benchmark artifact rather
than a model limitation.

## Step 4 — a second model

Run at least one more model so the finding is not about a single system. Any
free model works; `llama-3.1-8b-instant` on Groq has the highest daily ceiling.

```bash
python run_eval.py --provider groq --model llama-3.1-8b-instant --condition hi
```

## Reproducing the no-cost analysis

These need no API key at all:

```bash
python build_pairs.py        # pair English and Hindi, find lost arguments
python classify_v2.py        # label each loss
python compare_conditions.py # recoverability ceilings for all three conditions
```

## Attribution

BFCL-Hi is CC-BY-4.0, NVIDIA Corporation (Kamath et al., arXiv:2508.19831).
BFCL is Apache-2.0 (Patil et al., ICML 2025). Both must be cited in the paper.
