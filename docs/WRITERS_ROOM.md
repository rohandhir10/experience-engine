# The Writers' Room — A Multi-Agent Reasoning Process for Emotional Recreation

**Not a translation pipeline. A creative room, modeled on Pixar's Braintrust:
candid, specialist, adversarial-but-not-hostile critique, with one person
in the room whose job is to make the final call and be able to defend it.**

Status: Reasoning-process design. No code, no infrastructure. This
document specifies how a set of specialist "agents" (each a distinct
expert lens an AI is prompted to reason as) draft, critique, and
recombine a single lyric line or section — and how a final Judge resolves
the room into one decision. It replaces the flat "generate candidates,
human edits" shape of Stage 4–5 in `PRODUCTION_WORKFLOW.md` with a
structured room process for the lines that matter most.

---

## 0. Why a room, and why Pixar specifically

Pixar's Braintrust works because of a specific, narrow discipline: a small
group of people with genuinely different expertise give a director candid,
specific feedback on what isn't working — but no one in the room except
the director can force a change. The director must sit with every
criticism, but the story stays one person's vision, not a committee's
average. Two things make this work that a naive "get more opinions" process
does not:

1. **The critics have different, non-overlapping expertise**, so their
   feedback doesn't just triplicate the same note — a story is examined
   from genuinely different angles (character psychology, pacing, comedy,
   craft) rather than getting the same "I liked it / I didn't" three times.
2. **Committee-by-vote is explicitly rejected.** Braintrust feedback is
   information the director must confront, not a ballot that decides the
   outcome. Averaging opinions produces bland, focus-grouped work — the
   opposite of what "emotional recreation, not accuracy" requires.

This design imports both properties directly: the room below has agents
with deliberately disjoint expertise (§2), and a Judge (§7) whose job is
synthesis and final judgment, not vote-counting.

### 0.1 What "emotional recreation, not linguistic accuracy" changes about the room

A translation-company version of this process would have every agent
implicitly optimizing toward the same target: fidelity to the source
words. This room has no such shared target. Each agent optimizes toward a
*different* thing a native listener experiences — meaning, feeling,
cultural memory, musicality, dramatic function, psychological truth — and
those things genuinely conflict with each other on real lines. The room's
value is not in resolving that conflict quietly; it's in making the
conflict visible and specific enough that the Judge can make a real
creative decision instead of a compromise nobody chose.

---

## 1. Shared Context: What Every Agent Starts From

Every agent in the room receives the same starting material — never the
raw source text alone, and never a literal translation as a silent
default framing:

- The original line/section (source language).
- The **Song DNA** for the whole song (see `SONG_DNA.md`) — the artistic
  profile built before any re-expression begins: emotional arc, imagery,
  recurring motifs, ambiguity, symbolism, vulnerability, rhythm,
  repetition, narrative function, lyrical density, poetic style, and the
  songwriter's inferred intention. This replaces a narrower literal-
  meaning briefing with the actual craft brief every agent below reasons
  from — the room is analyzing what the song is built to make someone
  feel, not what its words say (`SONG_DNA.md` §0).
- **Room memory** (§8): decisions already made earlier in this same song —
  established motifs, voice, tone — so later sections aren't relitigated
  from zero.

No agent sees another agent's output before the round structure (§6)
explicitly allows it. This is the same discipline as separate writers
pitching before groupthink sets in: independence first, cross-talk second,
by design.

---

## 2. The Room Roster

Two tiers, matching how a real writers' room actually divides labor: some
people are there to pitch lines, others are there to protect a specific
truth the pitchers are prone to losing. Collapsing this distinction (asking
everyone to both draft and critique everything) produces a mushier process
where nobody's expertise is actually load-bearing.

### 2.1 Generative agents (pitch candidate lines)

#### Translator
- **Core question:** "What does this line actually say, and have we kept
  or knowingly departed from it?"
- **Contributes:** a literal-anchor candidate — not meant to win, meant to
  exist as the floor everyone else is allowed to depart from *deliberately*
  rather than by accident.
- **Systematic blind spot:** will defend precision even where precision
  costs the entire emotional point; has no native mechanism for knowing
  when literal accuracy is actively the wrong goal.
- **Built to catch:** every other agent drifting so far from the source
  that the line stops being a rendering of *this* line at all.

#### Poet
- **Core question:** "What is the most powerful way to say this as
  literary language — image, metaphor, sound, economy?"
- **Contributes:** a literary candidate, optimized for language quality on
  its own terms, independent of pop-song convention.
- **Systematic blind spot:** can produce something beautiful but too
  written — too dense or too literary to land the way a sung line lands on
  first hearing.
- **Built to catch:** flat, prosaic "translation-ese" from the Translator;
  naturalistic-but-inert phrasing from the Native Speaker that's authentic
  but has no craft in it.

#### Songwriter
- **Core question:** "Does this work as something sung — does it scan,
  does it hook, does it survive being heard once at tempo rather than read
  twice?"
- **Contributes:** a candidate optimized for singability, rhythm, and hook
  quality specifically, using pop-lyric convention (repetition, contrast,
  economical phrasing) as craft, not as cliché.
- **Systematic blind spot:** will flatten nuance or specificity for the
  sake of a catchy, simple line; left unchecked, converges toward generic
  pop-lyric phrasing.
- **Built to catch:** the Poet writing something gorgeous on the page that
  is unsingable or metrically wrong; the Translator producing a literal
  line that doesn't scan at all.

### 2.2 Diagnostic agents (critique, flag, and propose targeted fixes — not full rewrites)

#### Native Speaker
- **Core question:** "Would someone who actually grew up feeling this
  language ever say it this way — does this feel authentic, or does it
  feel translated?"
- **Contributes:** a gut authenticity verdict per candidate, plus (where
  possible) a specific word/phrase-level fix — but not a full competing
  draft; this agent's authority is intuitive, not constructive.
- **Systematic blind spot:** often can't articulate *why* something feels
  wrong beyond "it just doesn't," which makes this agent's feedback hard to
  act on precisely — and it carries no mechanism for catching subtler
  cultural-history or psychological errors that don't register as
  "unnatural."
- **Built to catch:** the Translator's over-literal phrasing that no one
  would actually say; the Cultural Historian being overly textbook about
  something that's actually just common, unremarkable slang.

#### Cultural Historian
- **Core question:** "What specific cultural, historical, generational, or
  religious weight does this line carry for a listener who shares that
  background — and did we keep it, deliberately drop it, or lose it
  without noticing?"
- **Contributes:** an annotation of cultural load per candidate, flagging
  anything quietly stripped out, plus a note on whether that loss was a
  deliberate creative choice made elsewhere in the room or an accident.
- **Systematic blind spot:** tends toward academic thoroughness — will
  argue for explanatory weight or precision that can kill the line's
  emotional immediacy; can over-intellectualize what should stay felt, not
  explained.
- **Built to catch:** the Poet or Songwriter unknowingly stripping cultural
  weight from a phrase simply because they didn't know it was there; the
  Psychologist misreading a line as revealing individual psychology when
  it's actually a well-worn cultural convention (and vice versa — see
  §5 on this exact conflict).

#### Film Critic
- **Core question:** "What is this line doing dramatically, right now, in
  the arc of the whole song — is this a setup, a release, an escalation —
  and is the emotional volume right for that role?"
- **Contributes:** a structural/pacing annotation: whether a candidate
  under- or over-plays its dramatic moment, whether it contradicts a setup
  or payoff established elsewhere in the song (via room memory, §8).
- **Systematic blind spot:** can push for a more "cinematic," dramatically
  legible reading than the song's actual tone calls for — Pixar's own
  discipline of restraint (not over-explaining a feeling) cuts against this
  agent's instinct to make every beat maximally clear.
- **Built to catch:** every other agent solving a line in isolation without
  checking whether their choice serves — or quietly breaks — the song's
  larger emotional shape.

#### Psychologist
- **Core question:** "What is the speaker actually feeling, specifically —
  not 'sad' or 'happy,' but the precise emotional logic (grief laced with
  relief, longing that's really denial) — and does this candidate carry
  that precision or flatten it?"
- **Contributes:** an emotional-specificity annotation per candidate,
  flagging generic emotional language and proposing more precise emotional
  framing where the room has drifted toward the vague.
- **Systematic blind spot:** can over-explain interior psychology that a
  good lyric deliberately leaves implicit — part of a line's power is
  often the space it leaves for the listener to feel the psychology rather
  than be told it; this agent can push toward a neatness real emotional
  life, and good lyric writing, resists.
- **Built to catch:** the Songwriter choosing a catchy but emotionally
  implausible phrase; the Translator or Cultural Historian settling for
  emotionally generic language when the actual feeling is more specific or
  more conflicted than "sad."

### 2.3 The blind-spot matrix, stated once for clarity

| Agent | Its blind spot | Who is built to catch it |
|---|---|---|
| Translator | Defends literal accuracy past the point it serves the line | Poet, Songwriter, Native Speaker |
| Poet | Too literary/dense to land when heard once | Songwriter, Native Speaker |
| Songwriter | Flattens nuance for catchiness, drifts generic | Poet, Psychologist, Cultural Historian |
| Native Speaker | Can't always explain *why*, misses subtler cultural/psych errors | Cultural Historian, Psychologist |
| Cultural Historian | Over-intellectualizes, kills immediacy with explanation | Poet, Film Critic |
| Film Critic | Pushes for over-legible drama, under-values restraint | Psychologist, Poet |
| Psychologist | Over-explains what should stay implicit | Film Critic, Poet |

No agent's blind spot is caught by itself. This table is the actual
argument for why the room needs all seven roles rather than three or four
— each removal leaves a specific, named failure mode with no one left to
catch it.

---

## 3. Round Structure

### Round 0 — Context distribution
All seven agents receive the shared context (§1) simultaneously. No
agent has seen any other agent's output yet.

### Round 1 — Independent generation
Translator, Poet, and Songwriter each independently produce **one**
candidate line (not several — forcing a single best pitch per agent keeps
each agent's position clear and arguable, rather than hedging across
options). Each candidate is tagged with which part of the Experience
Note's emotional core it leans into hardest.

### Round 2 — Independent diagnosis
Native Speaker, Cultural Historian, Film Critic, and Psychologist each
independently review **all three** Round 1 candidates — not just one —
and produce a structured critique per candidate:

```
{
  candidate_id,
  verdict: strong | workable | fails,
  strength: "...",       # what this candidate gets right, from this
                          # agent's specific lens
  failure: "...",        # what it gets wrong, from this agent's lens only
                          # — an agent does not comment outside its
                          # expertise (the Psychologist doesn't weigh in
                          # on scansion)
  suggested_fix: "..." | null   # a targeted word/phrase change if one
                                 # exists; null if the issue is structural
                                 # and can't be patched at word level
}
```

These four diagnoses are produced in parallel, with no agent seeing the
others' critiques yet — the same independence discipline as Round 1,
applied to criticism instead of generation, so that (for example) the
Psychologist's read isn't quietly anchored by having already seen the
Cultural Historian's.

### Round 3 — Cross-critique and rebuttal (one pass only)

This is the round the room exists for: every agent now sees everyone
else's Round 1/2 output and gets exactly one rebuttal turn.

- **Generative agents** may respond to diagnostic critiques aimed at their
  candidate: concede, defend, or propose a one-line revision that
  addresses the specific critique without abandoning their candidate's
  core approach.
- **Diagnostic agents** may also critique *each other's* critiques when
  their expertise genuinely conflicts — this is where, for example, the
  Cultural Historian and Psychologist may directly disagree about whether
  a line reflects a cultural convention or an individual's specific
  feeling (worked in §5). This disagreement is not resolved in this
  round — it is sharpened and handed to the Judge as-is.

One rebuttal per critique received, no further back-and-forth — this cap
exists specifically to prevent the room from spiraling into an unbounded
argument instead of producing a decision-ready transcript.

### Round 4 — Recombination pass

Given the critique transcript, the generative agents (or, practically,
whichever generative agent's candidate is closest to workable) each get one
chance to produce a **revised candidate** that deliberately incorporates
specific, fixable feedback — e.g., the Poet's imagery grafted onto the
Songwriter's meter, with the Psychologist's more precise emotional word
substituted in. This is a genuine rewrite pass, not a selection — new
candidates can appear here that didn't exist in Round 1.

### Round 5 — The Judge

The Judge (§7) receives everything: the Experience Note, all Round 1 and
Round 4 candidates, the full Round 2/3 critique and rebuttal transcript,
and any unresolved disagreement flags — and produces one final line plus a
rationale.

---

## 4. Why Independence Is Enforced Structurally, Not Just Requested

If every agent saw every other agent's output from the start, the room
would converge fast — and converge toward whichever opinion was voiced
first or most confidently, not toward the best synthesis of genuinely
different expertise. The round structure above (generate blind → diagnose
blind → then and only then cross-critique) exists specifically to
guarantee at least two independent passes before any agent has a chance to
anchor on another's framing. This costs an extra round of latency and is
worth it every time — the entire value of a multi-expert room over a
single strong model prompted five different ways is that the experts
genuinely didn't see each other's answers first.

---

## 5. Disagreement as a First-Class Output, Not Noise to Resolve

The room will sometimes produce a genuine, irreducible conflict between two
specialists — this is a feature of the design, not a bug to engineer away.
The canonical example: the Cultural Historian reads a line as an
unremarkable cultural convention (a stock phrase of grief in the source
culture) while the Psychologist reads the same line as revealing something
specific and individual about this speaker. These are not the same claim,
and they lead to different translations — a conventional phrase can be
rendered with a conventional English equivalent; an individually specific
feeling needs specific, non-clichéd English language.

The room does not average these two readings into a vague middle ground.
It hands the Judge both readings, explicitly labeled as conflicting, plus
each agent's one rebuttal to the other, and the Judge has to decide which
reading is right for this line — a real creative call, not a statistics
problem. This mirrors the `disagreement_flags` field on `EmotionNode` in
`EXPERIENCE_GRAPH.md` §7.1: disagreement between independent expert reads
is itself evidence about how genuinely ambiguous or context-dependent a
line is, and destroying that signal by forcing early consensus would make
the room worse, not more efficient.

---

## 6. Room Memory Across a Song

The room does not process a song as isolated, independently-litigated
lines. It proceeds section by section (verse, then chorus, then bridge...)
in order, and every section's final Judge decision is added to a running
**room memory**: established voice, motifs already rendered a certain way,
tonal choices already made. Later sections inherit this context
automatically — the Cultural Historian doesn't re-argue a convention
already settled in verse one; the Film Critic checks new candidates against
payoffs the room already committed to setting up. This is the same
consistency requirement `AURA_ARCHITECTURE.md`'s Long-Horizon Memory module
(LHM) exists to solve, scoped here specifically to one room's working
session on one song, not the cross-work memory LHM handles at the
production-pipeline level.

---

## 7. The Judge

### 7.1 What the Judge is not

Not a vote-counter, not an averager, not another agent whose opinion gets
blended proportionally with the other seven's. The Judge's role is
structurally different: it is the only role in the room that makes a
binding decision, and the only role required to produce a rationale
explaining what it did and did not take from the room — the Pixar-director
discipline of confronting all the feedback without being obligated to
adopt any particular piece of it.

### 7.2 Decision doctrine — veto conditions vs. weighted priorities

Two categories of input, handled completely differently:

**Veto conditions (disqualifying, non-negotiable, checked first):**
- **Native Speaker verdict of "fails"** on authenticity — if no native
  speaker would ever feel this the way the line intends, the candidate is
  disqualified regardless of how well it scores on every other dimension.
  This is the room's hard floor against producing something that reads as
  translated.
- **Factual/propositional inversion** flagged by the Translator (who did
  what to whom has been reversed or lost, not merely re-expressed) — a
  candidate can depart enormously from literal wording, but it cannot
  invert the underlying fact of the line. This is the same principle as
  `BCC` (Back-Translation & Consistency Checker) in `AURA_ARCHITECTURE.md`
  §7.2: emotional license is not license to get the basic facts backwards.

**Weighted priorities (used to choose among surviving candidates, in this
order, matching the "emotional recreation over accuracy" mission stated at
the top of this document):**

1. **Emotional truth and specificity** (Psychologist) — the ceiling this
   room optimizes for; a technically flawless line that flattens the
   actual feeling into something generic has failed at the one thing that
   matters most.
2. **Narrative fit** (Film Critic) — does it serve this exact moment in
   the song's arc, not just work as a standalone line.
3. **Cultural integrity** (Cultural Historian) — preserved, or knowingly
   and deliberately transformed — never accidentally lost.
4. **Poetic/aesthetic craft** (Poet).
5. **Singability and hook quality** (Songwriter).
6. **Literal proximity to the source** (Translator) — present as the
   lowest-weighted craft consideration, not a floor (the floor is the veto
   in 7.2, not this ranking) — a reminder that this room is explicitly not
   optimizing for this, per the mission the room was designed against.

### 7.3 Required output: the Judge's rationale

The Judge never simply outputs a final line. It outputs:

```
{
  final_line: "...",
  sources_used: [ {agent, contribution} ],   # what was taken from whom
  vetoes_applied: [ ... ] | none,
  priority_tradeoffs_made: "...",             # e.g. "chose emotional
                                                # specificity over the
                                                # Songwriter's catchier
                                                # phrasing because the
                                                # Psychologist's read of
                                                # ambivalence was more
                                                # load-bearing here"
  disagreements_overruled: [ {agents, disagreement, ruling, why} ]
}
```

This is the room's equivalent of `SelectionRecord` in
`AURA_ARCHITECTURE.md` §7.3 — the deliverable is not just a line, it's an
auditable creative decision, so that a human creative lead reviewing the
room's output (Stage 5 of `PRODUCTION_WORKFLOW.md`) can see exactly what
was weighed and overrule the Judge with full context, rather than having to
re-derive the tradeoff from scratch.

---

## 8. Worked Example

**Source line (illustrative):** a Korean lyric expressing a stock phrase
of resigned longing, roughly "I suppose that's just how it is" — but sung
at the emotional climax of the song, after a verse about someone who
never came back.

- **Translator's candidate:** *"I guess that's just how it goes."*
  (Literal, deliberately unremarkable — the anchor.)
- **Poet's candidate:** *"So this, then, is the shape grief settles into."*
- **Songwriter's candidate:** *"Guess this is just my life now."*

**Diagnostic pass:**
- **Native Speaker:** Translator's line — *workable*, feels natural but
  flat for a climax. Poet's line — *fails*, "no one would say this out
  loud, it reads as written, not felt." Songwriter's — *strong*,
  colloquial and real.
- **Cultural Historian:** flags that the source phrase is a well-known
  *conventional* expression of resignation in the source culture — not
  unusual or literary in the original at all — so the Poet's ornate
  rendering actually *overstates* the original's register.
- **Psychologist:** disagrees in part — notes that while the *phrase* is
  conventional, its placement here, right after the verse about someone
  who never returned, means the convention is being used ironically,
  almost defensively, to avoid saying the actual devastation directly. The
  flatness is the point; a competent English rendering has to preserve
  *that* the speaker is downplaying, not just that the phrase itself is
  common.
- **Film Critic:** flags that this is the song's emotional climax
  structurally, and both the Translator's and Songwriter's lines, while
  natural, may *underplay* the moment the arc has been building toward —
  though notes this could be intentional (the whole point may be
  anticlimax-as-devastation, matching the Psychologist's read).

**Round 3 disagreement, explicit:** Cultural Historian says "this is just
a common phrase, don't overweight it." Psychologist says "the commonness
is being used as a shield, that's the actual emotional content, and it
matters where in the song it lands." Neither is wrong about the source;
they disagree about which fact is load-bearing for the English line. This
is handed to the Judge unresolved.

**Round 4 recombination:** Songwriter revises to: *"I guess that's just my
life now"* → *"Guess that's life, I'm fine"* — keeping the flat,
conventional, almost-too-casual register the Cultural Historian identified,
while the deliberate "I'm fine" (not present literally in the source)
operationalizes the Psychologist's read of defensive downplaying, in
natural, singable English.

**Judge's ruling:** selects the Round 4 recombination. Rationale: "Native
Speaker veto cleared (line reads as something a person would actually say).
No factual inversion (Translator's anchor confirms the core proposition —
resigned acceptance — is intact). Weighted priorities: emotional
specificity (Psychologist) prioritized over the Cultural Historian's
'don't overweight the phrase' read, because the Film Critic's structural
flag — this is the climax — makes the *ironic flatness* the actual
dramatic content of the moment, not incidental phrasing; the Cultural
Historian's caution was valid input but is overruled here, explicitly,
because narrative placement changes what the convention is doing. Songwriter's
craft wins the final wording over the Poet's, because Native Speaker
correctly identified the Poet's version as unfelt at exactly the moment
authenticity matters most."

---

## 9. Failure Modes of the Room Itself

- **Judge deference to the loudest or most articulate agent.** The
  Psychologist and Cultural Historian, being the most verbose critics, can
  crowd out the Native Speaker's harder-to-articulate-but-often-correct gut
  read if the Judge isn't explicitly weighting verdict strength over
  argument length. The veto structure (§7.2) exists specifically to protect
  the Native Speaker's authority from being outtalked.
- **Premature convergence** if independence (§4) isn't actually enforced in
  practice — a room where agents are run sequentially and each sees prior
  output "just to save a round" quietly becomes a single-pass pipeline
  wearing seven hats, losing the entire value of the design.
- **Over-restraint vs. over-explanation, unresolved by design.** The Film
  Critic and Psychologist push toward legibility; the Poet and Cultural
  Historian's better instincts push toward restraint. The room does not
  resolve this tension in general — it resolves it per line, via the
  Judge, and a Judge that always sides with legibility (or always with
  restraint) has failed to actually use the room and should be flagged for
  recalibration.
- **Critique fatigue at production scale.** A full seven-agent, five-round
  process per line is not meant to run on every line of every song daily
  (see `PRODUCTION_WORKFLOW.md` cadence discussion) — it is the right
  process for a song's highest-stakes lines (hooks, climaxes, the specific
  lines the Stage 1 brief identified as the reason this song was chosen at
  all). Running it uniformly on throwaway lines wastes the room's cost on
  moments that don't need it.

---

## 10. Integration with the Production Workflow

This room replaces the flat "AI generates candidates, human edits" shape of
Stages 4–5 in `PRODUCTION_WORKFLOW.md` specifically for the lines the
Stage 1 brief flags as mission-critical — the emotionally/culturally dense
lines that are the actual reason a song was chosen. For lower-stakes lines
in the same song, a lighter version of Round 1 (generative agents only,
skip full diagnostic/cross-critique) remains appropriate, to keep daily
cadence realistic. The human creative lead in Stage 5 receives the Judge's
full rationale (§7.3), not just a final line — their job becomes reviewing
and, where warranted, overruling an auditable decision, rather than
generating a decision from raw candidates themselves.

---

## Appendix: Roster at a Glance

| Role | Tier | Optimizes for | Vetoes? |
|---|---|---|---|
| Translator | Generative | Literal anchor / no accidental drift | Yes — factual inversion |
| Poet | Generative | Literary craft, image, sound | No |
| Songwriter | Generative | Singability, hook, rhythm | No |
| Native Speaker | Diagnostic | Authenticity, gut feel | Yes — "no one would say this" |
| Cultural Historian | Diagnostic | Cultural/historical weight | No |
| Film Critic | Diagnostic | Narrative arc, dramatic pacing | No |
| Psychologist | Diagnostic | Emotional truth and specificity | No |
| **Judge** | Synthesizer | Final decision + auditable rationale | Applies vetoes, resolves disagreement |

*End of document.*
