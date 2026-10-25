# BFCL-Hi audit: how much of the Hindi tool-calling gap is the benchmark?

[BFCL-Hi](https://huggingface.co/datasets/nvidia/BFCL-Hi) is NVIDIA's Hindi
version of the Berkeley Function Calling Leaderboard (BFCL). It was machine
translated and, by its own description, not human evaluated. Models score
lower on it than on English BFCL, and that gap is usually read as a model
weakness in Hindi.

This project asks a narrower question: **how much of that gap comes from the
translation itself?** BFCL grades function calls by exact match against an
English answer key. When translation turns `"Los Angeles"` into
`"लॉस एंजिल्स"`, a model can only score by guessing the original English
spelling. That tests romanisation, not tool use.

The pipeline:

1. **Pairs** every BFCL-Hi item with the exact English revision it was
   translated from (BFCL v2 Live, gorilla commit `1726e89933`, whose function
   schemas match BFCL-Hi 258/258 on `simple`).
2. **Labels translation damage** for each item by checking whether each
   required string argument in the answer key can still be found in the Hindi
   prompt.
3. **Builds a Hinglish condition** (Roman script, code-mixed, with English
   proper nouns restored), the way many Hindi speakers actually type.
4. **Runs and scores models** on all three conditions (English, Hindi,
   Hinglish) using BFCL's own prompts and the official BFCL v2 AST checker,
   so results line up with the published leaderboard.

## Findings so far (no model calls needed)

These come from the automated analysis. A manual check of a 160-item sample
is in progress in `bfcl_audit_workbook.xlsx`, so treat them as script
estimates until it is finished.

**Upper bound on exact-match accuracy.** This is the share of items where
every required English string argument is visible in the prompt the model
receives (`python compare_conditions.py`):

| Condition | Items fully recoverable | Required args present |
|---|---|---|
| English | 375 / 1214 (30.9%) | 1631 / 2956 (55.2%) |
| Hindi (Devanagari) | 96 / 1214 (7.9%) | 369 / 2956 (12.5%) |
| Hinglish (Roman) | 267 / 1214 (22.0%) | 1271 / 2956 (43.0%) |

Script choice alone moves the upper bound from 7.9% to 22.0%.

**Damage labels across all 1,335 items** (`out/bfcl_hi_damage.jsonl`):

| Label | Items | Meaning |
|---|---|---|
| `T1_back_transliteration` | 692 (51.8%) | the model must recover the English spelling from Devanagari |
| `T2_untraceable` | 92 (6.9%) | the required value has no trace left in the Hindi prompt |
| `T3_schema_recoverable` | 44 (3.3%) | the value can be recovered from the function schema |
| `none` | 507 (38.0%) | no required string was lost |

Two other issues found while pairing:

- Some BFCL Live prompts were already non-English (for example Chinese or
  Vietnamese) and were translated into Hindi anyway, sometimes changing the
  value the answer key expects.
- BFCL-Hi is frozen on BFCL v2. Only 162 of 258 `simple` schemas still match
  the current English BFCL, so the Hindi and English leaderboards are not
  measuring the same benchmark.

## Repository layout

| Path | What it is |
|---|---|
| `data/en_v2/` | English BFCL v2 Live at gorilla commit `1726e89933` |
| `data/en/` | English BFCL v3 Live, for the version-drift comparison |
| `data/hi/` | NVIDIA's BFCL-Hi, unmodified (CC-BY-4.0) |
| `out/bfcl_hi_damage.jsonl` | Per-item damage labels |
| `out/hinglish_bfcl/` | The Hinglish condition in drop-in BFCL format, with English answer keys |
| `bfcl_checker/` | The official BFCL v2 AST checker, from gorilla commit `30124c4399` |
| `build_pairs.py`, `classify_v2.py` | Pair the corpora and label translation damage |
| `make_hinglish.py` | Build the Hinglish condition |
| `compare_conditions.py` | Recoverability upper bounds for all three conditions |
| `run_eval.py` | Query a model on one condition (resumable, rate-limited) |
| `score.py` | Score with the official checker and join failures to damage labels |
| `bfcl_audit_workbook.xlsx` | Manual audit sheets: Hindi damage check and Hinglish naturalness check |

## Reproduce the analysis (no API key)

```bash
python build_pairs.py         # pair English and Hindi, find lost arguments
python classify_v2.py         # label each loss
python compare_conditions.py  # recoverability upper bounds
```

## Run models

The runner is built for free API tiers: it rate-limits itself, backs off on
HTTP 429, and resumes where it stopped. Groq is the default because
`openai/gpt-oss-120b` is one of the models NVIDIA reported on BFCL-Hi, so the
English and Hindi numbers can be compared with a published figure.

```bash
export GROQ_API_KEY=...
python run_eval.py --provider groq --model openai/gpt-oss-120b --condition en
python run_eval.py --provider groq --model openai/gpt-oss-120b --condition hi
python run_eval.py --provider groq --model openai/gpt-oss-120b --condition hinglish
python score.py
```

Add `--limit 5` for a quick check first. All three conditions together are
4,005 calls, which takes several days on Groq's free tier; `--limit 150` per
category gives about 1,300 calls. `--provider gemini` (Google AI Studio) and
`--provider openrouter` also work.

`score.py` prints accuracy per condition, then Hindi accuracy split by damage
label. The key test: if the overall Hindi gap is large but the gap on
`none`-labelled items is small, most of the reported gap comes from the
benchmark rather than the model.

## Attribution

- BFCL-Hi: NVIDIA Corporation, CC-BY-4.0 (Kamath et al., arXiv:2508.19831).
- BFCL data and the AST checker in `bfcl_checker/`: Apache-2.0 (Patil et al.,
  ICML 2025, [gorilla](https://github.com/ShishirPatil/gorilla)). See
  `bfcl_checker/LICENSE`.
