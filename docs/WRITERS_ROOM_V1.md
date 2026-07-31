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
  factual-inversion veto) and **weighted priority order** (emotional
  truth > narrative fit > cultural integrity > poetic craft > singability
  > literal accuracy) are unchanged — V1 simplifies who's in the room, not
  what the room is optimizing for.
- The Judge's **auditable rationale** (`sources_used`,
  `vetoes_applied`, `priority_tradeoffs_made`, `disagreements_overruled`)
  is still required on every ruling, so a human reviewer
  (`PRODUCTION_WORKFLOW.md` Stage 5) can still audit and override it.
- **Room memory** across sections (`WRITERS_ROOM.md` §8) is unchanged.
- Song DNA remains the shared context every agent works from
  (`SONG_DNA.md`) — nothing here changes what's being optimized for, only
  how cheaply the room gets to a decision.

*End of document.*
