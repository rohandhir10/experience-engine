# Writers' Room V1 — Minimal-Agent Architecture

**Priority: prove the core hypothesis as fast as possible, not build the
most sophisticated room possible. This is the default pipeline going
forward; the full seven-agent room in `WRITERS_ROOM.md` remains available
as an opt-in "maximum sophistication" mode, not deleted.**

---

## 1. What changes from the original design

| Change | Original (`WRITERS_ROOM.md`) | V1 |
|---|---|---|
| Poet + Songwriter | Two independent generative agents | Merged into one **Creative Adapter** |
| Film Critic | Independent diagnostic agent | **Removed entirely** |
| Native Speaker, Cultural Historian, Psychologist | Always invoked, every section | **On-demand specialist consultants**, invoked only when the Judge decides they're needed |
| Default agents in play | 7 | **3** (Translator, Creative Adapter, Judge) |
| Rounds | 5 (generate → diagnose → cross-critique → recombine → judge) | **2–3** (generate → judge triage → [specialist consult →] judge final) |

### 1.1 Why the Film Critic can be cut without losing its function, not just its cost

The Film Critic's whole job was checking a candidate against the song's
narrative arc — but that information (`narrative_function`,
`relation_to_adjacent`) already lives in the Song DNA as structured data,
computed once per song, for free. The Judge can read that field directly
instead of paying for a dedicated agent to re-derive and restate it. This
is a genuine architectural simplification, not just a corner cut: the
Film Critic's *analysis* survives in Song DNA; only its *redundant LLM
call* is removed.

### 1.2 Why Poet + Songwriter merge without losing as much as it looks like

The original room used two independent agents specifically so their
disagreement (literary elegance vs. singability) would surface as a real
tension the room could see. Merging them loses that built-in check. V1
compensates two ways: the merged **Creative Adapter** is explicitly
instructed to name which craft it prioritized and why when the two pull
against each other (so the tradeoff is at least visible, even if
unchallenged), and it reports a **confidence score** — low confidence
specifically because it couldn't reconcile the two crafts is one of the
signals that routes the section to a specialist (§3). This doesn't fully
replace having two independent voices, and that gap is named honestly in
the tradeoffs table (§6), not hidden.

### 1.3 Why the three specialists become on-demand, not removed

Native Speaker, Cultural Historian, and Psychologist are the room's most
expensive habit in the original design: they review *every* candidate on
*every* section, whether or not their expertise is actually load-bearing
for that specific line. V1's premise is that most lines in most songs
don't need all three lenses — a plainly-stated, culturally-unloaded,
unambiguous line doesn't need a Cultural Historian's review any more than
a simple sentence needs a copy editor checking for hidden Latin puns. The
lines that *do* need it should still get it — the goal is precision in
when specialists are called, not fewer total safety checks on the lines
that matter.

---

## 2. Default Pipeline

```
Translator ──┐
             ├──► Judge (triage) ──► ready to rule? ──yes──► final ruling
Creative     │                           │
Adapter ─────┘                           no
                                          │
                                          ▼
                              Judge names which specialist(s)
                              (cultural_historian / native_speaker /
                               psychologist) — 0 to 3 of them
                                          │
                                          ▼
                              Specialist(s) consulted, one call each
                                          │
                                          ▼
                              Judge (final) ──► final ruling
```

Two generative calls always happen. The Judge's first call is both a
*possible final ruling* and a *triage decision* in one shot — if it's
confident, the section is done in three calls total; if not, it names
exactly which specialists it needs and why, they're consulted, and the
Judge rules a second time with their input.

---

## 3. The Routing Mechanism

Routing decides whether Cultural Historian, Native Speaker, and/or
Psychologist get invoked for a given section. Two design commitments
matter here:

1. **The Judge makes the actual decision, every time** — this isn't a
   pre-filter that silently skips the Judge's judgment; it's information
   handed to the Judge so it isn't guessing blind.
2. **Most of that information costs nothing extra to compute** — it's
   either already sitting in the Song DNA (built once per song, not
   re-derived per section) or is a field the generative agents report as
   part of the call the pipeline was already making. Only the fourth
   signal below requires the Judge's own judgment, because it's the one
   signal nothing else can compute for it.

### The four signals

1. **Confidence.** Translator and Creative Adapter each self-report a
   confidence score (0–1) and, if below 0.7, an `uncertainty_type`
   (`cultural` / `authenticity` / `emotional` / `none`) naming *what kind*
   of uncertainty they have. This maps directly to which specialist is
   relevant — cultural uncertainty routes toward the Cultural Historian,
   authenticity uncertainty toward the Native Speaker, emotional
   uncertainty toward the Psychologist. Free: it's just two extra fields
   in a JSON response the pipeline was already requesting.

2. **Cultural density.** Read directly from the Song DNA: does this
   section contain any symbol with `register: culturally_specific`? Song
   DNA is built once per song; checking this per section costs nothing.

3. **Ambiguity.** Read directly from the Song DNA: does this section have
   an ambiguity item where `is_the_ambiguity_the_point` is true? Same
   free-lookup logic — this is exactly the kind of line where an AI
   "helpfully" resolving an intentional ambiguity is a real risk, and the
   Psychologist is who's positioned to catch that.

4. **Conflicting interpretations.** This is the one signal that can't be
   computed for free — it requires actually reading both candidates and
   judging whether they imply meaningfully different emotional readings
   of the line, not just different wording of the same reading. This is
   the Judge's own call, made as part of its triage pass, not a
   precomputed flag. It's the reason the Judge's first call is a triage
   decision and not just a rubber stamp on precomputed signals.

Signals 1–3 are computed in plain code from data the pipeline already
has, with zero additional LLM calls — a deterministic pre-check the Judge
receives as input text alongside the two candidates. Signal 4 lives
entirely inside the Judge's own reasoning during that same call. Either
way, the routing decision itself never costs a dedicated LLM call; it
rides along on calls the pipeline makes regardless.

### What the Judge does with all this

Given the candidates, the precomputed signals, and the room memory,
the Judge either rules immediately (most sections, expected) or names
specifically which of the three specialists it needs and why — never
"call everyone to be safe." A specialist named without a stated reason
is a signal the routing logic itself needs recalibrating (see §6, and
the failure-mode note in §5).

---

## 4. Specialist Consultation, When It Happens

An invoked specialist reviews exactly the two candidates already on the
table (no re-generation), from its own lens only — same discipline as
the original room's diagnostic agents (`WRITERS_ROOM.md` §2.2): a
verdict, a strength, a failure, and an optional targeted fix, nothing
outside its expertise. 0 to 3 specialists may be invoked per section;
each is one additional call. The Judge's second (final) call then has
the specialist critiques available and must rule — no second triage,
no infinite loop.

---

## 5. What This Room No Longer Catches, Stated Plainly

- **No independent literary-vs-singable tension.** A merged Creative
  Adapter can settle for "good enough at both" without a second voice
  ever pushing back — the confidence/uncertainty self-report is a weaker
  substitute for genuine disagreement between two independent specialists.
- **No blanket authenticity/cultural/psychological review.** A line that
  trips none of the four signals gets no specialist review at all. If the
  routing logic has a blind spot (a cultural issue Song DNA didn't flag,
  an authenticity problem neither agent was uncertain about), it goes
  through unreviewed. The original room's redundancy was partly waste,
  but redundancy is also what catches the thing nobody expected to need
  catching.
- **No standing narrative-arc adversary.** The Judge checks Song DNA's
  `narrative_function` field itself now — a data lookup, not a second
  opinion. If Song DNA's own narrative-function tagging is wrong for a
  section, there's no independent Film Critic left to catch that it's
  wrong, only the same pipeline that produced the tag in the first place.

None of these are hidden costs — they're the explicit trade being made
for speed, stated up front so a later quality regression can be traced
to one of these three gaps specifically instead of being a mystery.

---

## 6. Comparison: Original Room vs. V1

Numbers below are **per section**, for a typical 4-section song, and are
relative/order-of-magnitude — exact dollar cost depends on current model
pricing and per-call token counts, which vary by song complexity.

| Dimension | Original room (`WRITERS_ROOM.md`) | V1 minimal |
|---|---|---|
| **LLM calls / section** | 16 (3 generate + 4 diagnose + 7 cross-critique + 1 recombine + 1 judge) | **3 typical** (2 generate + 1 judge-rules-immediately); **~6–7 worst case** (2 generate + 1 judge-triage + up to 3 specialists + 1 judge-final) |
| **LLM calls / 4-section song** (incl. 1 shared Song DNA call) | ~65 | **~13–29**, depending on how often specialists trigger |
| **Relative API cost** | Baseline | Roughly **3–5x cheaper** on call count alone; likely more, since the original room's cross-critique round replays the entire growing candidate+critique transcript on every one of its 7 calls — V1's calls carry much smaller, mostly-fixed-size payloads |
| **Relative latency** | Baseline (5 sequential rounds/section; ~16 calls, several of them fanning out per-agent) | **Best case ~5x faster** (3 calls vs. 16); **worst case still ~2-3x faster** (~6-7 calls vs. 16), and the common case should be close to best case for songs without heavy cultural/ambiguity load |
| **Maintainability** | 7 distinct agent prompts, a 5-round orchestrator, growing transcript payloads to reason about, 16 JSON-parse points/section to debug | **3 core prompts** (Translator, Creative Adapter, Judge) + 3 conditionally-invoked specialist prompts (reused, not new); routing logic is plain Python, unit-testable with zero LLM calls; far fewer places a malformed response can break the section |
| **Observability** | Full transcript always produced, but expensive to produce | **Which specialists actually get invoked, and why, becomes a first-class metric** — tracking specialist-invocation rate per song/language is itself useful signal for whether V1's routing is well-tuned, something the original room's "always call everyone" design has no equivalent insight into |
| **Expected quality ceiling** | Higher — full adversarial coverage from 7 lenses on every line, maximum chance of catching subtle issues | Lower ceiling by construction (§5) — the bet is that most of the value came from the specific lines where a signal actually fires, not from blanket coverage |
| **Expected quality on the specific lines that matter most** | High, but no differently prioritized than any other line | **Should be comparable** — Song DNA's cultural-density and ambiguity flags specifically target the highest-stakes lines (the same criteria `PRODUCTION_WORKFLOW.md` §1 uses to select songs in the first place), so the specialists still get invoked where the mission actually lives |

**Net read:** V1 trades blanket redundancy for targeted precision, at
roughly a third to a fifth of the cost and latency. That trade is
defensible specifically *because* the routing signals are aimed at the
same culturally/emotionally dense content the whole project exists to
serve — if V1 performs comparably to the full room in the feasibility
experiment (`FEASIBILITY_EXPERIMENT.md`), that's strong evidence the full
room's exhaustiveness wasn't where the value was coming from. If it
doesn't, the three named gaps in §5 are exactly where to look first.

---

## 7. What Stays Identical to the Original Design

- The Judge's **veto structure** (Native Speaker authenticity veto,
  factual-inversion veto) is unchanged.
- The Judge's **auditable rationale** requirement is unchanged, though its
  contents grew (§8) — every ruling still lets a human reviewer
  (`PRODUCTION_WORKFLOW.md` Stage 5) audit and override it.
- **Room memory** across sections (`WRITERS_ROOM.md` §8) is unchanged.
- Song DNA remains the shared context every agent works from
  (`SONG_DNA.md`).
- The **priority order itself was rewritten** — see §8. "Emotional truth
  and specificity" is no longer the top priority; it has been replaced.

---

## 8. Redesign: Artistic Fidelity Over Emotional Truth

**Cause.** Running V1 against a real song (a Hindi duet, "Agar Tum Saath
Ho") surfaced a systematic failure mode: the Creative Adapter was
over-writing, and the Judge rewarded expressive, well-crafted English even
when that expressiveness was *invented* rather than *inferred* from the
original. "Emotional truth and specificity" as the top-priority criterion
turned out to reward confident invention as readily as it rewarded
faithful reconstruction — a fluent, evocative line and an evocative but
fabricated one can look identical to a scoring criterion that only asks
"does this feel emotionally true," without also asking "is this feeling
actually licensed by the source."

**The fix is a philosophy change, not a patch.** The top priority is no
longer emotional truth. It is **artistic fidelity**, defined by six
constraints, checked on every candidate before anything else is weighed:

1. **Preserve the songwriter's intention** — write what the line is
   actually doing, not a more impressive idea of what it could be doing.
2. **Preserve ambiguity** whenever the original is ambiguous — a
   deliberately unresolved line must stay unresolved in English too.
3. **Never introduce imagery, metaphor, or symbol** that cannot reasonably
   be inferred from the source line and the Song DNA.
4. **Never intensify emotion** beyond what's present in the source — a
   quietly sad line does not become a devastated one.
5. **Never simplify complexity** the original holds — a line doing two
   things at once must keep doing both.
6. **Never explain what the songwriter intentionally left implicit** — if
   the original trusts the listener to feel something unstated, the
   English rendering must trust the listener the same way.

**Actively penalized**, regardless of how well-written the result reads:
invented metaphors, invented imagery, over-explained emotion, AI-sounding
poetic language, ornate English, unnecessary adjectives. These are treated
as fidelity failures in this room's philosophy, not neutral style
preferences — each one replaces something the songwriter actually did with
a more impressive-sounding invention.

**New priority order** (replacing the old one in full):

`(0) artistic fidelity — the six constraints above, checked first, on
every candidate → (1) narrative fit against the song's arc (Song DNA's
narrative_function) → (2) cultural integrity → (3) restraint and
economy — rewarding the candidate that says the least necessary in the
most natural English, not the one that sounds most impressively "poetic"
→ (4) singability/hook quality → (5) literal proximity to the source,
lowest priority, a tiebreaker only.`

### 8.1 Creative Adapter: 8-10 distinct candidates, not one

The Creative Adapter now produces **8 to 10 candidates per section in a
single call**, not one. "Distinct" is defined narrowly on purpose:
differing in economy, syntax, register, and word choice — *not* differing
in how much imagery or emotional intensity they add. Every one of the
8-10 must independently satisfy all six fidelity constraints; the room
does not accept one "safe, faithful" candidate hedged against several
"inventive" ones, because that would just relocate the over-writing
problem from the Judge's selection into the candidate pool's composition.
Each candidate carries a `style_label` (e.g. "spare and plainspoken",
"held-back understatement", "closer to source syntax") so the Judge and
any human reviewer can tell the variants apart.

This does not change V1's call-count economics (§6): Creative Adapter is
still one LLM call regardless of how many candidates it returns, so the
best/worst-case call counts in §6 are unaffected by this redesign — only
the token size of the generation and Judge calls grows, since there is
more to generate and more to compare.

### 8.2 The Judge's evaluation now produces a structured fidelity record

Every ruling now includes:

- `fidelity_checks` — all six constraints, each explicitly marked
  satisfied or not for the *winning* candidate, with a one-line note.
- `violations_found` — specific penalties applied to specific rejected
  candidates (e.g. `{"candidate_id": ..., "violation_type":
  "invented_imagery", "detail": "..."}`), so a human reviewer can see not
  just what won but *why the others lost*, in the same auditable spirit as
  the rest of this room's design.

This is a genuine scoring change, not just a stricter tone in the prompt:
a candidate that reads beautifully but fails constraint 3 (invented
imagery) should now lose to a plainer candidate that doesn't, and the
Judge is required to say so explicitly rather than let good writing paper
over an invention.

### 8.3 What this trades away, stated plainly

Per this document's own discipline (§5): favoring restraint over
expressiveness risks under-serving songs where the original genuinely *is*
vivid or intense — a candidate that matches real source intensity should
not be penalized for being intense, only one that adds intensity the
source doesn't have. The six constraints are checked against the source
and Song DNA, not against a flat "always be plain" rule, but this
distinction is a genuinely harder judgment call than the old, simpler
"does this feel emotionally true" criterion, and is worth watching for
false-positive over-correction (flattening a line that was actually
supposed to be vivid) as this gets tested against more real songs.

---

## 9. Redesign: The Burden of Change

**Cause.** A benchmark against two existing Bollywood/Punjabi lyric
translation sites (Bollynook, FilmyQuotes) identified a second-order
failure mode §8's redesign didn't fully close: the Judge still sometimes
rewarded a candidate for beautiful, expressive English even when that
expressiveness came from invented emphasis, shifted imagery, or a subtly
altered intention. §8 penalized specific bad behaviors (invented imagery,
over-explanation) as one dimension among several. It did not require every
individual deviation from the source to justify itself. A candidate could
rack up several small, each-individually-defensible-sounding embellishments
and still win, because nothing forced a fragment-by-fragment accounting of
what changed and why.

**The reframe.** The Judge's core test is no longer "which candidate is
most beautiful" or even "which best satisfies artistic fidelity" as a
holistic vibe check. It is:

> **If the original lyricist had written this song in English, would they
> recognize this as their own work?**

The mission is not to improve the songwriter. It is to recreate their
experience. Every word that differs from the original carries a burden of
proof — the engine must be able to name why a specific change was
necessary, or it must not make that change.

### 9.1 The deviation ledger, replacing the old holistic checklist

§8's `fidelity_checks` (a six-item satisfied/not-satisfied checklist) and
`violations_found` (a list of penalties on losing candidates) are **both
removed**, merged into one stricter mechanism: for the winning candidate,
the Judge diffs it against the Translator's literal anchor and produces a
`Deviation` entry for every fragment that differs meaningfully — the
original wording, the adapted wording, and a specific justification tied
to one of five scored dimensions (§9.2). **If a fragment's deviation has no
real justification, it does not ship — the Judge reverts it to the more
literal wording before finalizing `final_line`.** This is the actual
mechanical difference between a "burden of proof" and a score: a score
can be outvoted by other scores; a burden of proof is either met or the
change doesn't happen. An empty or near-empty deviation list is the
*expected*, healthy result for a well-behaved candidate, not a sign the
Judge did too little work.

### 9.2 The scoring dimensions, and why the originally-proposed list was cut down

Two **gates** (pass/fail, unchanged from §7.2/§8): Literal Accuracy (no
factual inversion) and Authenticity (the Native Speaker veto).

Five **scored dimensions**, replacing the old six-constraint checklist and
the original priority order in full:

1. **Artistic Fidelity** — would the lyricist recognize this as their own
   intention, ambiguity, and restraint? This deliberately absorbs what
   would otherwise be separate "emotional fidelity," "meaning
   preservation," "preservation of ambiguity," and "preservation of
   restraint" dimensions — scoring those separately double-counts the same
   underlying signal and makes the rubric harder to weight honestly.
2. **Genre Authenticity** — does this read as a real lyric in the source's
   genre/tradition (Song DNA's `genre_feel`/`style`), not generic "poetic
   English"?
3. **Natural English** (schema id: `natural_target_language`, since the
   engine's target language is a parameter, not a constant) — fluent, unstilted English, independent of
   fidelity. A faithful candidate can still read clunky; this is scored
   separately so that failure mode is visible on its own.
4. **Voice Consistency** — coherent with the established narrator/
   character voice and prior decisions already made this song (room
   memory).
5. **Singability & Rhythm** — merged, not separate: for a sung lyric,
   "does it scan" and "does it perform" are practically one judgment, and
   splitting them into two numbers just produces two scores that move
   together.

`Rhythm` as an independent top-level dimension and `Preservation of
Ambiguity`/`Preservation of Restraint` as independent top-level dimensions
were both proposed and both cut for the reasons above — they remain real
considerations, just folded into Artistic Fidelity and Singability &
Rhythm respectively rather than scored a second time.

### 9.3 Creative Adapter: five philosophies, not eight-to-ten styles

§8's 8-10 anonymous style variants are replaced by **exactly five named
adaptation philosophies**, one candidate each:

- **maximum_fidelity** — the most literal rendering that still reads as
  real English. The floor, made presentable.
- **native_english_lyricist** — reads exactly like a songwriter in this
  genre would write from scratch, bound by the same constraints.
- **performance_first** — prioritizes breath, hook, and momentum among
  otherwise equally faithful options.
- **emotion_first** — prioritizes landing the *source's own* emotional
  beat with maximum precision — not more intensely, more precisely.
- **genre_first** — prioritizes matching Song DNA's genre/style
  conventions as closely as possible.

Every philosophy remains fully bound by the burden of change and the six
non-invention constraints from §8 — they differ in which fidelity-
compatible dimension they prioritize when a real tradeoff exists, never in
how much license to invent they get. If two philosophies would converge on
identical wording for a given line, the Creative Adapter is instructed to
say so honestly rather than manufacture artificial variety.

### 9.4 What changes for the specialists

Cultural Historian, Native Speaker, and Psychologist are not removed, but
their job sharpens: under §8 they gave generic critique per candidate;
under this redesign they exist specifically to **arbitrate contested
entries in the deviation ledger** — is this specific deviation justified,
or is it an invention wearing a justification's clothes. This is a
narrower, more falsifiable question than "critique this candidate," and it
is what the routing signals (§3) and the Judge's triage decision should be
consulting them about going forward.

### 9.5 Evaluation: a blind, five-way benchmark

This redesign is only as good as its evidence. The benchmark to run:

**Corpus.** Songs with existing entries on both Bollynook and FilmyQuotes,
so there's a real, not constructed, comparison point — Agar Tum Saath Ho
and Sadda Haq both qualify; a real benchmark needs 10-15 songs across
emotional registers before the result generalizes.

**Systems, blind, per song:** (1) Google Translate — the raw MT floor;
(2) Bollynook; (3) FilmyQuotes; (4) single-prompt GPT/Claude — "translate
preserving emotional impact," one shot, no room — the ablation
`FEASIBILITY_EXPERIMENT.md` §5.4 always intended to run once V1 existed;
(5) CASTIA (V1, burden-of-change Judge); (6) *optional* — a human literary
adaptation, sourced separately, evaluated diagnostically rather than as a
pass/fail bar.

**Method.** Bilingual reviewers see the original plus all candidates,
unlabeled, order randomized. With five systems instead of two, reviewers
**rank** rather than pick a binary winner (ranking yields usable pairwise
data via Bradley-Terry aggregation; a forced single choice across five
options discards information). Reviewers also score each candidate on the
five dimensions in §9.2, not just an overall preference — this is what
turns the result into "CASTIA wins on X, loses on Y" instead of a single
undifferentiated win/loss.

**Success criterion.** CASTIA's average rank on **Artistic Fidelity
specifically** must beat Google Translate, Bollynook, FilmyQuotes, and
single-prompt GPT/Claude, replicated on held-out songs never used to tune
a prompt. Comparison against a human literary adaptation is diagnostic
only — a different, harder bar, not a gate this stage needs to clear.

### 9.6 Singability & Rhythm: from opinion to a deterministic baseline

Until now, `singability_rhythm` was a pure LLM judgment with nothing
underneath it — the Judge stated a score, but no number anywhere in the
pipeline had actually been counted. `engine/rhythm.py` fixes that for
English output: it computes a real syllable count per candidate using the
CMU Pronouncing Dictionary (`pronouncing` package), falling back to a
vowel-cluster heuristic for words the dictionary doesn't know (slang,
names, transliterations). When the source text is itself Latin-script
(e.g. romanized Hindi/Punjabi), a rough `source_syllable_estimate` is also
computed as a reference point for how much a candidate compresses or
expands the line — never a hard target, since English and the source
language don't map syllable-for-syllable. Devanagari and other non-Latin
source scripts get `None` rather than a fabricated number.

Both the Translator's and Creative Adapter's candidates carry a
`syllable_count` field, computed in code before either Judge prompt runs.
The Judge is told explicitly that this number is real, not a guess, and
should ground `singability_rhythm` in it rather than an unverified
opinion. This doesn't make singability fully objective — "does this scan
well when sung" is still a judgment call — but it removes the worst
failure mode, where the Judge could assert a rhythm score with nothing
underneath it at all.

### 9.7 Verifying the constitution instead of trusting it

Everything in §9 was, until recently, enforced by prompt text alone: the
Judge was *asked* to log every deviation and *asked* to score its own
`invention_penalty`. Both are self-reports from the model under audit.

`engine/verify.py` (see `docs/ENGINE.md`) now checks those self-reports
deterministically, with no LLM in the loop: it diffs the shipped line
against the Translator's literal anchor and measures what fraction of the
real change the deviation ledger actually accounts for, catches ledger
entries citing text that exists in neither the anchor nor the final line,
flags emotion words / intensifiers / explanatory connectives the anchor
never used, checks motif renderings for consistency across sections, and
computes an independent invention penalty to compare against the Judge's
own. Any run — including runs already stored on disk — can be audited
retroactively, and a non-zero exit code lets it gate a pipeline.

This is the difference between "our engine follows a constitution" as a
marketing claim and as a checkable property. It cannot judge whether a
justification is *good* — only whether the audit trail is complete,
honest, and free of the mechanical failures the laws name.

**The asymmetry, and its correction.** Everything the Burden of Change
introduced — the deviation ledger, the invention penalty, the restraint
checks — exists to stop the engine *over-writing*, which was the real
failure it was built to fix. But that made the whole scoring apparatus
one-directional: a run that shipped the Translator's literal anchor
verbatim passed every check with a perfect score. Optimized against, the
safest way to satisfy the constitution was to stop adapting altogether —
i.e. to become a translator, the one thing CASTIA exists not to be.

The verifier therefore carries an **adaptation floor** as the opposing
signal, reported as *adaptation distance* beside the invention penalty.
It is deliberately a song-level check rather than a per-line quota:
one section legitimately matching the anchor is exactly what §9's "an
empty deviations list is a GOOD sign" describes, while a whole song
matching it means the room did nothing. A per-line minimum would be
gameable by manufacturing deviations — precisely the behavior the
Burden of Change was written to prevent. Restraint and adaptation are
both now measured, and neither can be maximized by abandoning the other.

Alongside this, `JudgeRuling` gained `invention_penalty`: an aggregate 0-1
score across every candidate reviewed (not just the winner), for how much
of the deviation ledger leaned on weak, "sounds better"-style
justifications rather than a specific, defensible reason. This is separate
from the per-deviation `justification` fields in §9.1 — it exists so a
human auditing a ruling has one number to scan before reading the full
ledger, as a signal for when a ruling's deviations deserve closer
scrutiny.

*End of document.*
