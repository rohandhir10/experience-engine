# CASTIA blind benchmark

The evidence machine: runs CASTIA against real alternatives on identical
songs, blinds everything, collects bilingual reviewer ratings, and
produces a report with actual significance tests. Independent of the
engine — imports it, never modifies it.

## Systems compared

| System | How it runs |
|---|---|
| `castia` | The full engine (Song DNA + V1 Writers' Room) |
| `gpt_single` | One well-written prompt to the same OpenAI model CASTIA uses — the ablation that isolates CASTIA's *process* from its model |
| `claude_single` | The same single prompt to Anthropic's model (skipped if no `ANTHROPIC_API_KEY`) |
| `google_translate` | Machine-translation floor via deep-translator's free endpoint; falls back to a manual file if the endpoint is unavailable |
| `bollynook`, `filmyquotes` | No APIs exist; paste their published translations into `benchmark/manual/<song_id>/<system>.txt` (sections separated by blank lines). Missing file = skipped for that song, never faked |

## What counts as corpus material

`load_corpus` reads every `*.json` in the corpus directory except the
stems listed in that directory's `.benchmarkignore`. Not everything
useful to keep around is evidence:

| Excluded from `examples/` | Why |
|---|---|
| `sample_song` | The CLI's documented example fixture (README.md, `engine/cli.py`, docs/ENGINE.md). Synthetic English, self-described as "not a real production input" — it would dilute every mean in the report. |
| `sadda_haq_single_line` | A one-section fragment. Too little to rate a system on, and the paired tests would weight it the same as a full ten-section song. |

Both files stay where they are; only their corpus membership changed.

**Known limitation of the current corpus:** the four remaining songs are
all Hindi/Urdu/Punjabi. A result from `examples/` is evidence about that
language family, not about the six-language roster. Japanese, Korean and
Spanish songs are needed before any claim can be made about them — see
`corpora/KOREAN.md` for the collection spec.

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
reviewers judge as listeners, not as auditors of CASTIA's own criteria.

## The report

`report.md` contains mean ratings per system per dimension, best-overall
shares, and CASTIA-vs-each-baseline paired differences tested with a
two-sided sign-flip permutation test on matched (reviewer × song) pairs —
assumption-light and honest at small n. It also states its own
limitations (sample size, recruited reviewers, missing baselines) because
evidence that survives scrutiny beats a bigger number that doesn't.

**Pre-registered success criterion** (docs/WRITERS_ROOM_V1.md §9.5): CASTIA
must beat Google Translate, Bollynook, FilmyQuotes, and single-prompt
GPT/Claude on artistic fidelity specifically, replicated on held-out
songs never used to tune a prompt. A pilot with 2–3 songs and 2–3
reviewers is a signal, not that proof.

## Feeding real data into the public /compare page

`web/lib/comparison-data.ts` is the public-facing comparison shown at
`/compare` — a lighter-weight consumer of stage 1 than the full blind
pipeline above (no blinding, no reviewers, just the raw outputs side by
side for visitors to read). To add or update an entry with real data:

```bash
# Stage 1 only — no blind packets, no reviewers needed for this page.
python -m benchmark.cli run --corpus examples --run-id comparison_1
```

This writes `benchmark/runs/comparison_1/outputs/<song_id>/<system>.json`
per system that succeeded (`castia`, `gpt_single`, `google_translate` —
`claude_single` isn't shown on this page). Copy each system's `sections`
text into the matching `ComparisonEntry` in `comparison-data.ts` by hand —
there's no automated sync, on purpose: a human should look at what got
generated before it goes on a public page, the same discipline the rest
of this project applies everywhere else. Leave a system's field absent
(not an empty string) if it produced nothing; the page renders that
honestly as "not yet generated" rather than blank or faked.
