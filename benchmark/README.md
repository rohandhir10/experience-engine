# AURA blind benchmark

The evidence machine: runs AURA against real alternatives on identical
songs, blinds everything, collects bilingual reviewer ratings, and
produces a report with actual significance tests. Independent of the
engine — imports it, never modifies it.

## Systems compared

| System | How it runs |
|---|---|
| `aura` | The full engine (Song DNA + V1 Writers' Room) |
| `gpt_single` | One well-written prompt to the same OpenAI model AURA uses — the ablation that isolates AURA's *process* from its model |
| `claude_single` | The same single prompt to Anthropic's model (skipped if no `ANTHROPIC_API_KEY`) |
| `google_translate` | Machine-translation floor via deep-translator's free endpoint; falls back to a manual file if the endpoint is unavailable |
| `bollynook`, `filmyquotes` | No APIs exist; paste their published translations into `benchmark/manual/<song_id>/<system>.txt` (sections separated by blank lines). Missing file = skipped for that song, never faked |

## The three stages

```bash
# 1. Generate outputs (needs OPENAI_API_KEY)
python -m benchmark.cli run --corpus examples --run-id pilot_1

# 2. Build blinded packets, one per reviewer
python -m benchmark.cli blind --run-id pilot_1 --corpus examples \
    --reviewers priya rohan amit

# 3. Reviewers return ratings_*.json files -> drop them into
#    benchmark/runs/pilot_1/ratings/ and:
python -m benchmark.cli report --run-id pilot_1
```

Stage 1 is resumable — already-stored outputs are reused, so a failed
system can be retried without re-paying for the others.

## How the blind works

- Every output is normalized (`normalize.py`): section headers, quotes,
  markdown, and whitespace differences are stripped so typography can't
  identify a system.
- Each reviewer gets an independently shuffled order per song, labeled
  Version A/B/C… The only place letters map to systems is
  `runs/<id>/blind/key.json` — **never send that file to anyone**.
- `tests/test_benchmark.py` asserts no packet ever contains a system
  name. The whole `runs/` directory is gitignored, key included.
- Reviewer packets are self-contained HTML: send the file over
  WhatsApp/email, the reviewer rates in their browser, presses Finish,
  and sends back the JSON it downloads. No server, no accounts.

## What reviewers score (1–5 each, per version, plus one best-overall pick per song)

- Faithful to the original's artistry
- Reads like real English, not a translation
- Carries the same feeling as the original
- Clear and easy to read

This rubric is deliberately NOT the engine's internal five dimensions —
reviewers judge as listeners, not as auditors of AURA's own criteria.

## The report

`report.md` contains mean ratings per system per dimension, best-overall
shares, and AURA-vs-each-baseline paired differences tested with a
two-sided sign-flip permutation test on matched (reviewer × song) pairs —
assumption-light and honest at small n. It also states its own
limitations (sample size, recruited reviewers, missing baselines) because
evidence that survives scrutiny beats a bigger number that doesn't.

**Pre-registered success criterion** (docs/WRITERS_ROOM_V1.md §9.5): AURA
must beat Google Translate, Bollynook, FilmyQuotes, and single-prompt
GPT/Claude on artistic fidelity specifically, replicated on held-out
songs never used to tune a prompt. A pilot with 2–3 songs and 2–3
reviewers is a signal, not that proof.
