# AURA Feasibility Experiment

**Hypothesis test, not product design.**
**Question:** Can an AI consistently generate lyric translations that
bilingual speakers judge as emotionally closer to the original than
conventional translations?

Status: Pre-registered experiment design. No Experience Graph, no
multi-module pipeline, no infrastructure. The goal here is a single
falsifiable answer, obtained as cheaply as possible, before any further
investment in the architecture in `AURA_ARCHITECTURE.md` /
`EXPERIENCE_GRAPH.md` is justified.

---

## 0. Framing

Before this experiment, "AURA works" is an untested belief resting on two
separate claims bundled together:

1. An LLM, prompted correctly, can identify the emotional/cultural
   *function* of a lyric line as distinct from its literal content.
2. Re-generating from that functional understanding produces output that
   bilingual humans actually experience as more emotionally faithful — not
   just more fluent, not just better poetry, specifically *closer to what
   the original made a native speaker feel.*

Claim 2 is the one that matters and the one this experiment isolates.
Claim 1 is necessary but not sufficient — an LLM could correctly identify
"this line expresses grief masked as nostalgia" and still fail to produce
target-language text that reproduces that effect for a reader. The
experiment below is designed to test claim 2 directly, using the cheapest
mechanism that could plausibly deliver claim 1 (a two-prompt pipeline, §5),
rather than building the machinery to guarantee claim 1 first.

If this experiment fails, the correct conclusion is *not* "add more
architecture" — it's "the core mechanism doesn't work, and no amount of
scaffolding around it will fix that." That is the actual value of running
it small, first.

---

## 1. The Experiment

### 1.1 Design

A **blinded, paired-preference experiment**, the standard design for "is A
better than B" questions where the thing being judged is subjective and
holistic (this is the same design family used for MT quality evaluation —
WMT human evaluation campaigns — and for RLHF preference data collection).

- **Unit of analysis:** one short lyric excerpt (a couplet or single verse,
  not a full song — see §3.2 for why).
- **Conditions (2, not 3):**
  - **Condition A — Conventional:** an existing literal/professional
    translation of the excerpt, or output of a standard MT system
    (DeepL/Google Translate) if no professional translation exists.
  - **Condition B — AURA-prototype:** output of the minimal two-stage
    prototype in §5.
- **Judges see:** the original-language excerpt (text, and audio if
  available — see §3.4) plus both candidate translations, **unlabeled and
  order-randomized**, and are not told which system produced which.
- **Task given to judges:** two separate ratings per excerpt (not one
  conflated rating — see §1.3 for why this split matters):
  1. *Forced-choice preference*: "Which translation makes you feel closer
     to what you feel reading/hearing the original?" (A / B / no
     difference).
  2. *Independent fluency rating* of each candidate on its own (1–5,
     "how natural is this as writing in the target language, ignoring the
     original entirely").

### 1.2 Independent and dependent variables

- **Independent variable:** which system produced the candidate (A vs. B).
- **Primary dependent variable:** forced-choice emotional-closeness
  preference.
- **Secondary dependent variable:** fluency rating (control variable, not
  outcome — see below).

### 1.3 Why fluency is measured separately

The single biggest confound in this experiment is that a more fluent
translation will often *also* be preferred as "more emotionally faithful"
even if the judge is actually just responding to writing quality, not
emotional fidelity. If Condition B wins on preference but also wins on
fluency by a similar margin, the experiment has **not** shown what the
hypothesis claims — it has shown "AURA writes more fluently," a much
weaker and less interesting result. The experiment is only informative if
we can distinguish these two outcomes, so fluency is collected
independently and used as a covariate in analysis (§4.3), not folded into
the main question.

### 1.4 What this experiment deliberately does not test

- Whether AURA works across many language pairs (tested on one pair only,
  see §3.1).
- Whether AURA works on long-form lyrics/full songs (tested on short
  excerpts only, see §3.2).
- Whether AURA's advantage, if any, comes from the "experience
  decomposition" step specifically vs. just being a stronger underlying
  model prompted more carefully (addressed by an ablation, §5.4, run only
  if the main result is positive — no reason to pay for it otherwise).

---

## 2. The Evaluation Process

### 2.1 Judges

- **Who:** bilingual adults, native or near-native in the source language
  (so they can authentically access what the original *feels like*), fluent
  in the target language (so they can read the candidates without a second
  translation layer getting in the way).
- **Why bilingual, not monolingual-with-a-gloss:** a monolingual judge
  reading a literal gloss of the original plus two target-language
  candidates is judging "which of these reads better," not "which is
  closer to what I'd feel reading the original" — the entire hypothesis is
  about a felt comparison a monolingual judge structurally cannot make.
- **How many:** minimum 20 judges (§4.1 justifies this from a power
  calculation), each rating a subset of excerpts so no judge sees more than
  ~15 items (fatigue control) — achieved via a partial rotation design
  (each excerpt rated by at least 8 different judges).
- **Recruitment:** does not need to be scaled/production infrastructure —
  a paid panel (e.g. Prolific, filtered by self-reported bilingual fluency
  plus a short screening translation task to verify fluency) is sufficient
  for a first pass.

### 2.2 Blinding protocol

- Candidates relabeled `Translation 1` / `Translation 2` per excerpt, with
  A/B assignment to slot 1/2 randomized independently per excerpt (not a
  fixed mapping) so judges cannot learn a pattern across items.
- Judges are not told an AI is involved at all in this round — framed
  neutrally as "comparing two translations" — to avoid AI-halo or
  AI-skepticism bias contaminating the preference judgment.
- The person analyzing results is blind to which system is A/B until after
  the preference data is collected and locked (standard pre-registration
  discipline — prevents post hoc rationalization of which excerpts to
  include).

### 2.3 What judges are explicitly NOT asked

Judges are not asked "which is a more accurate translation" — accuracy in
the literal sense is not the thing under test and asking it would bias
attention toward literal fidelity, undermining the whole point. The only
framing is felt emotional closeness.

### 2.4 Qualitative capture

After the forced choice, judges may optionally leave a one-line free-text
note ("felt too formal," "lost the bitterness in the last line"). Not
scored, but essential for diagnosing *why* a result came out the way it
did — a pure win-rate number with no qualitative trace will not tell you
what to fix if the hypothesis fails narrowly.

---

## 3. The Data We Need

### 3.1 Language pair: pick exactly one to start

**Recommendation: Korean → English.**

Rationale for constraining to one pair, and for this specific pair:

- K-pop/K-ballad lyrics have (a) a large, motivated, genuinely bilingual
  judge pool available via paid panels, (b) well-documented cases where
  literal/fan translations are criticized specifically for losing
  emotional/cultural nuance (han, jeong — concepts with no direct English
  analog), giving a real, not synthetic, gap for AURA to close, and (c)
  existing conventional translations (official subtitle translations, fan
  translation communities) to use as Condition A without commissioning new
  ones.
- Testing on one pair first is a deliberate scope cut: the hypothesis as
  stated ("can an AI consistently...") is really a family of per-language-
  pair hypotheses, and conflating them in a first experiment means a
  negative result would be uninterpretable — you wouldn't know if the
  *mechanism* failed or if you'd picked a bad language pair. Isolate one
  pair, get a clean answer, then decide whether to replicate on a second,
  structurally different pair (e.g. Spanish → English, a much smaller
  cultural/linguistic distance) as a generalization check.

### 3.2 Excerpt selection, not full songs

- **Unit:** single couplets or short verses (2–4 lines), not full songs.
- **Why:** a full song entangles many separate emotional beats, formal
  constraints (rhyme, meter, singability), and structural narrative arc —
  exactly the kind of complexity `AURA_ARCHITECTURE.md`'s full pipeline
  exists to handle, and exactly what this experiment is explicitly *not*
  trying to test yet. A short excerpt isolates a single emotional/cultural
  unit, which is the smallest thing the hypothesis can be checked against
  without confounding the result with formal/structural performance.
- **Count:** 24 excerpts. Enough for a meaningful sample (§4.1) without
  requiring a large commissioning/licensing effort. Selected to span a
  deliberate range: some carrying clear culturally-specific affect concepts
  (the "hard" cases AURA should have most advantage on), some more
  universal/archetypal emotional content (a harder test — does AURA still
  help, or only on the obviously culture-bound cases?).
- **Sourcing:** published, rights-cleared lyrics where a conventional
  translation already exists publicly (official or reputable fan
  translation) — avoids both licensing risk and the cost of commissioning
  fresh professional translations for Condition A.

### 3.3 What must be recorded per excerpt

`{excerpt_id, source_text, source_language, existing_conventional_translation,
conventional_translation_source (official/fan/MT), context_note (song title,
narrative context of the line if not self-contained)}` — the context note
matters because a couplet ripped from a song can be genuinely ambiguous
without knowing who's speaking to whom; judges should get the same minimal
context both candidates were generated with, so neither system is
unfairly deprived of information the other had.

### 3.4 Audio (optional, second-priority)

If time/rights permit, include a short audio clip of the original
performance alongside text for judges rating the *source* side — lyric
emotional effect is frequently carried partly by melody/delivery, and a
text-only original may under-represent the "real" felt experience judges
are supposed to be calibrating against. Treated as an enhancement, not a
blocker: the experiment is still meaningful text-only, just noisier.

---

## 4. Success Metrics

### 4.1 Sample size and power

With 24 excerpts × 8 judges each = 192 paired judgments (minimum, before
attrition), a binomial test against the null of 50% (no preference) has
adequate power (>80%) to detect a true preference rate of ~60% at α=0.05 —
a modest, not extreme, effect size. This is deliberately chosen to be a
*low bar to clear statistically* but a *meaningful bar substantively*: a
60% preference rate, if real and replicated, is a strong enough signal to
justify further investment; anything weaker is not worth building on top
of yet.

### 4.2 Primary success criterion (pre-registered, decided before data
collection)

> **AURA's prototype (Condition B) must be preferred over the conventional
> translation (Condition A) in ≥ 60% of judgments, aggregated across
> excerpts and judges, with a binomial test p < 0.05, AND this result must
> hold on a held-out second batch of excerpts not used for any prompt
> iteration during prototype development.**

The held-out replication clause exists specifically to prevent the
common failure mode of an experiment "succeeding" only because the
prototype's prompts were iteratively tuned against the same items being
used to evaluate it.

### 4.3 Secondary analysis: disentangling fluency from emotional fidelity

- Compute the correlation between fluency-rating difference (B − A) and
  preference direction, per excerpt.
- **If preference for B is well explained by fluency difference alone**
  (e.g. B wins preference only on excerpts where B also has a
  substantially higher fluency score, and shows no advantage on excerpts
  where fluency scores are matched) — the result should be reported as
  "AURA produces more fluent output," not as support for the emotional-
  fidelity hypothesis. This is a stricter bar than the primary criterion
  and is the actual test of whether the *mechanism* (functional
  decomposition, not just a capable LLM) is doing the work.

### 4.4 Failure / falsification criteria (defined in advance)

The hypothesis should be treated as **not supported** by this experiment if
any of:

- Preference rate is not significantly different from 50%.
- Preference rate clears 60% but the fluency-confound check (§4.3) shows
  the effect is fully explained by fluency, not emotional closeness.
- The result does not replicate on the held-out batch.
- Inter-rater agreement (Krippendorff's α or simple pairwise agreement) on
  the preference task is so low (e.g. < 0.2) that "preference" isn't
  measuring a coherent shared judgment at all — in that case the result is
  inconclusive, not negative, and the instrument (task design/judge
  recruitment) needs fixing before the hypothesis itself can be evaluated.

---

## 5. The Smallest Prototype Capable of Proving the Hypothesis

No Experience Graph. No multi-module pipeline. No persistent memory, no
orchestration layer, no model abstraction layer. Just enough mechanism to
test whether *functional decomposition before re-expression* beats
*direct generation*, because that is the specific mechanism the hypothesis
is about.

### 5.1 Two LLM calls, one script

**Call 1 — Decomposition prompt** (a single structured prompt, not a graph):
given the source excerpt and its context note, ask the model to produce a
short structured note — not the full Experience Graph schema, a minimal
subset of it, specifically:

```
{
  literal_gist: "...",              # one sentence, plain meaning
  emotional_core: "...",            # what the line makes a native
                                     # speaker feel, in their own terms —
                                     # explicitly allowed to use
                                     # untranslatable source-culture affect
                                     # words if that's the honest answer
  cultural_notes: "...",            # anything culturally load-bearing,
                                     # or "none" if archetypal
  what_must_survive: "..."          # one sentence: if only one thing
                                     # about this line's effect can be
                                     # preserved, what is it
}
```

**Call 2 — Re-expression prompt:** given *only* this structured note (not
the source text) plus a target-language instruction ("write a short line
in English that produces this same felt effect for a reader — you do not
need to preserve the literal content, do not translate word for word"),
generate the candidate.

This mirrors the architectural principle from `AURA_ARCHITECTURE.md` (no
direct source→target path) in its smallest possible form: two prompts, a
hard boundary between them, no shared context that would let the model
silently fall back to literal translation in call 2.

### 5.2 What is deliberately left out, and why that's fine for this test

- **No knowledge base, no LHM, no consistency memory** — irrelevant at the
  single-couplet unit of analysis (§3.2); consistency across a whole song
  only matters once you're testing full songs, which this experiment
  isn't.
- **No multi-candidate generation + selection** — the experiment needs one
  candidate per condition per excerpt, generated once and frozen before
  judging, matching how Condition A (an existing translation) is also a
  single frozen artifact. Adding a selection step would make Condition B
  an unfair comparison (best-of-N vs. one-shot) and would also conflate
  "does decomposition help" with "does having more shots help," muddying
  the exact question being asked.
- **No evaluation modules (EEE/BCC)** — the human judges *are* the
  evaluator in this experiment; building automated evaluation before
  knowing whether the underlying generation mechanism works at all would
  be optimizing a metric for a hypothesis not yet confirmed to be real.

### 5.3 Effort estimate

This is a few hours of prompt-writing plus a script that loops over 24
excerpts calling an LLM twice each — not a build project. That is the
point: if the hypothesis is going to be worth a real architecture, it
should show a signal from the cheapest possible version of the mechanism
first.

### 5.4 Optional ablation (only run if §4.2's primary criterion is met)

To check the result is attributable to *decomposition*, not just
*a good model*: add a **Condition C — direct-prompt baseline**, same
underlying model as Condition B, single prompt ("translate this lyric
preserving its emotional impact, not literally"), no structured
intermediate note. If B beats C on the same preference task, that's
evidence the two-stage decomposition step specifically is doing work, not
just "LLMs are good at this if you ask nicely" — the actual claim
underlying the entire AURA architecture. This ablation is explicitly
deferred until after a positive primary result, since there's no reason to
spend judge-hours on it if the base hypothesis doesn't clear its bar at
all.

---

## 6. Decision Rule After the Experiment

- **Primary criterion met, fluency confound ruled out, ablation (if run)
  favors B:** proceed to invest in the fuller architecture
  (`AURA_ARCHITECTURE.md`) — the core mechanism is validated on the
  smallest unit; the rest of the system exists to extend it to full songs,
  multiple language pairs, and long-horizon consistency.
- **Primary criterion met but fluency confound not ruled out, or ablation
  fails:** the underlying model may already be capable of this without
  AURA's specific mechanism — worth a cheaper follow-up (better prompting
  alone) before committing to the full architecture.
- **Primary criterion not met, or fails to replicate:** treat the core
  hypothesis as unsupported at current model capability. Re-test
  periodically as underlying models improve (this is explicitly a
  capability-gated hypothesis, not a permanently closed question) rather
  than building architecture speculatively ahead of evidence.

*End of document.*
