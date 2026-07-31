# Song DNA

**The artistic profile of a song, built before any re-expression begins.
Not what the words say — what the song is built to make someone feel, and
by what specific craft it does that.**

Status: Central representation specification. Supersedes the per-line
"Experience Note" as the primary shared context every Writers' Room agent
(`WRITERS_ROOM.md`) works from. No translation vocabulary appears in this
document by design.

---

## 0. The premise

A lyric line is not a sentence that happens to rhyme. Its job is not to
convey information — a songwriter almost never needs a line to *tell* you
something; they need it to *do* something to you while you're listening.
Analyzing a song for translation asks "what does this line mean." Analyzing
a song as a songwriter asks a completely different question: **what is
this song built out of, and how does each part of that construction make
someone feel a specific thing at a specific moment?**

Song DNA is the answer to that second question, captured once per song,
before a single word of English is written. Every other agent in
`WRITERS_ROOM.md` — Translator, Poet, Songwriter, Native Speaker, Cultural
Historian, Film Critic, Psychologist, and the Judge — reads from this
document instead of the source lyric directly. This is the same
architectural discipline as the no-direct-path principle in
`AURA_ARCHITECTURE.md`, applied to craft instead of to language: no agent
re-expresses from the raw lyric, because the raw lyric is not the thing
that needs to survive. The DNA is.

### 0.1 Why twelve dimensions, and why these

Each dimension below answers a question a songwriter actually asks while
writing or revising a song — not a linguistic category imposed from
outside. A song can be perfect on every dimension of literal meaning and
still fail completely as a song if its emotional arc is flattened, its
central image is dropped, or its vulnerability is over-explained into
sentimentality. These twelve are the load-bearing craft elements; losing
any one of them while "translating perfectly" produces a technically
accurate, artistically dead result — which is the exact failure this
document exists to prevent.

---

## 1. Structure of the Song DNA Document

Three layers, because artistic effect operates at three different scales
simultaneously, and collapsing them loses information a songwriter would
never lose:

1. **Whole-Song DNA** — the song's single artistic thesis: what it is
   fundamentally trying to make a listener feel, stated once, in one
   sentence, the way a songwriter could tell you what a song is "about"
   emotionally in ten seconds.
2. **Section DNA** — one profile per song section (verse, pre-chorus,
   chorus, bridge, outro), scored across all twelve dimensions *for that
   section specifically*, because a verse and its chorus are almost always
   doing structurally different emotional work and should never be
   analyzed as if they're the same kind of material.
3. **Device Ledger** — a cross-cutting catalog of specific recurring
   elements (motifs, image systems, repetition patterns) that live *across*
   sections rather than inside any one of them, because a song's most
   powerful devices are usually the ones that connect its parts, not the
   parts themselves.

```
SongDNA
├── whole_song: { artistic_thesis, genre_feel, overall_arc_shape,
│                 songwriter_intention }
├── sections: [ SectionDNA, SectionDNA, ... ]   # ordered, verse → outro
└── device_ledger: { motifs: [...], image_systems: [...],
                      repetition_patterns: [...] }
```

---

## 2. Emotional Arc

**What it captures.** The shape of feeling across the song's timeline —
not a single mood label for the whole song, but a trajectory: where it
starts, where it turns, where it peaks, where (or whether) it resolves.

**Representation.** An ordered sequence, one entry per section, of
`{valence, intensity, dominant_feeling}`, plus explicit **turn points** —
the specific moment(s) the song's emotional direction changes, each
annotated with *what causes the turn* (a new piece of information, a
repeated line landing differently the second time, a key/tempo change if
known). Also a single `arc_shape` label at the whole-song level: e.g.
*ascending catharsis*, *slow resignation*, *oscillating ambivalence*,
*plateau* (deliberately static — the point is that nothing changes),
*false resolution then collapse*.

**Why it matters.** A translation can get every individual line's emotion
right and still fail the song if the *order and shape* of the feeling is
wrong — a song that earns its catharsis in the final chorus needs to still
feel earned there, not arrive early or never arrive. This is the single
dimension every other agent in the room checks their work against first:
whatever a line does locally, it has to also serve this shape.

---

## 3. Imagery

**What it captures.** The concrete, sensory pictures a song uses to make a
feeling physical instead of stating it — the practice of showing instead
of telling that is close to the whole craft of lyric writing. A line that
says "I miss you" is doing almost no work compared to a line that shows a
specific, physical trace of absence.

**Representation.** Per section, a catalog of `{image, sensory_channel
(visual/tactile/auditory/kinesthetic), what_it_stands_in_for}` — the last
field is the actual point: an image is cataloged by the feeling it's
carrying, not just described.

**Why it matters.** Images are frequently the *actual* emotional payload of
a line — more than any explicit statement of feeling in the same song. A
re-expression that keeps a line's stated emotion but drops its image has
usually thrown away the thing doing the real work and kept the least
important part.

---

## 4. Recurring Motifs

**What it captures.** An element — an object, phrase, or image — that
returns more than once across the song, and, critically, *means something
slightly different each time it returns* because of what's happened in
between. This is frequently a song's actual architecture: the skeleton
everything else hangs on.

**Representation.** A motif ledger entry per recurring element:
`{motif, first_occurrence, each_later_occurrence: [{section, how_meaning_
shifted}], resolves_or_breaks_at_end: bool + how}`. The "breaks the pattern
at the end" case is worth flagging explicitly — a very common and powerful
songwriting move is to repeat a line exactly for most of the song and then
change one word the last time it appears; that single change is often
where the song's whole meaning lands.

**Why it matters.** Motif is content that must survive as a *thread*, not
as isolated occurrences — re-expressing each occurrence well but
independently, without tracking that they're the same motif evolving, can
produce three good lines that no longer add up to the device the
songwriter built.

---

## 5. Ambiguity

**What it captures.** Places the songwriter left genuinely open on
purpose — is this about a lover or about death, about faith or about
another person entirely — distinguished sharply from a line that's simply
underspecified by accident. Some of the most enduring lyrics work precisely
*because* they never resolve which reading is correct.

**Representation.** Per flagged element: `{ambiguous_element,
competing_readings: [...], is_the_ambiguity_the_point: bool}`. The last
field is a judgment call, not a formality — it determines whether the
re-expression's job is to preserve the openness (keep both readings alive)
or whether the vagueness is actually a gap that needs a real interpretive
choice made.

**Why it matters.** Resolving a deliberate ambiguity into one clear meaning
— even a well-written one — is a craft failure, not an improvement. This
field exists specifically so no downstream agent "helpfully" clarifies
something the songwriter left open on purpose.

---

## 6. Symbolism

**What it captures.** Meaning layered onto an image or object that goes
beyond its literal, concrete presence — distinct from plain imagery (§3)
in that a symbol is doing conceptual work (a cage isn't just a cage, it's
entrapment) rather than purely sensory work.

**Representation.** `{symbol, concrete_form, symbolic_meaning, register:
archetypal | culturally_specific | invented_for_this_song}`. The register
field matters for the same reason it mattered in the Experience Graph's
`symbol_class` (`EXPERIENCE_GRAPH.md` §9.2): an archetypal symbol survives
almost any re-expression; an invented-for-this-song symbol only survives if
whoever re-expresses it knows it's *this song's* invention and treats it
with the same specific weight throughout, not as generic imagery.

**Why it matters.** Symbolism is where a song's meaning compounds beyond
what any single line states — losing a symbol's register (treating an
invented, personal symbol as generic decoration) flattens exactly the kind
of specificity that makes one song different from every other song using
similar imagery.

---

## 7. Vulnerability

**What it captures.** The degree and kind of emotional exposure a lyric
risks — what is actually being admitted, and at what cost to whoever is
"speaking" the song. Vulnerability is often the actual currency the best
songwriting trades in: a specific, costly admission lands harder than any
amount of polished imagery around it.

**Representation.** Per section (or per line, for the most load-bearing
moments): `{what_is_admitted, directness: stated_plainly | deflected_
through_humor | buried_in_imagery | undercut_by_irony, felt_cost: how
raw/risky this admission reads}`. The `directness` field matters
specifically because a huge amount of songwriting craft lives in *how*
something vulnerable is said, not just that it's said — burying a
confession behind a joke or an image is frequently the more powerful move,
not a weaker one.

**Why it matters.** A re-expression can accidentally destroy vulnerability
in two opposite directions: over-explaining a buried admission until it's
stated too plainly (killing the tension between what's said and what's
felt), or under-selling a plainly stated admission until it reads as vague.
This field is what lets the room check that the *manner* of exposure, not
just its content, survived.

---

## 8. Rhythm

**What it captures.** The prosodic, musical shape of the lyric as it's
actually delivered — where lines rush, where they stretch, where the
phrasing pushes ahead of or lags behind the beat — and what emotional work
that rhythmic choice is doing.

**Representation.** Per line (for sections where rhythm is load-bearing):
a scansion note plus `rhythmic_function` — e.g. *"this line crowds twice
as many syllables as the rest of the verse, mimicking breathlessness"* or
*"this line holds a single word over four beats, forcing the listener to
sit in it."*

**Why it matters.** Rhythm frequently *is* the emotional effect, not a
container for it — a rushed line about panic and a held, spacious line
about the same literal content produce entirely different felt
experiences. Re-expression that preserves meaning but inverts a song's
rhythmic character (turning a held, spare line into a busy, rushed one to
fit more words) breaks the thing that was actually doing the emotional
work.

---

## 9. Repetition

**What it captures.** Structural repetition — the same word, phrase, or
line structure recurring for emphasis, hypnotic effect, or hook
construction — distinct from motif (§4), which is about *content*
returning and evolving. Repetition here is about *form*: exact
recurrence, near-recurrence with one word changed, anaphora (the same
opening across lines), refrain structure.

**Representation.** `{repeated_element, occurrences, exact_or_varied,
craft_function: hook | hypnosis | insistence | incantation | contrast}`.

**Why it matters.** A refrain that changes one word each time it returns is
an extremely common and deliberate device — collapsing all its
occurrences into "the same line, said a few times" and re-expressing them
identically erases the exact mechanism that made the refrain build instead
of just repeat.

---

## 10. Narrative Function

**What it captures.** What job each section is doing in the song's overall
structure — not what it says, what it's *for*: setup, escalation, the
hook/thesis statement, the turn, the release, the comedown.

**Representation.** Per section: `{function: setup | escalation | hook |
turn | release | resolution | anti-resolution, relation_to_adjacent_
sections: how it depends on or sets up neighboring sections}`.

**Why it matters.** A chorus that functions as a release after a
constrained, held-back verse needs to still feel like release relative to
that verse — evaluating a chorus's re-expression in isolation, without its
structural relationship to what came before it, can produce a chorus that's
well-written but no longer does its actual job in the song's shape.

---

## 11. Lyrical Density

**What it captures.** How much is packed into each line or bar — spare
and spacious (a handful of words carrying enormous weight, real silence
around them) versus dense and maximalist (rapid, packed, information-rich
phrasing). This is a felt-pacing quality, independent of literal content.

**Representation.** Per section: a density rating (sparse / moderate /
dense) plus a short qualitative note — e.g. *"this verse holds one image
per line and nothing else; the space is the point"* vs. *"this section is
deliberately breathless, packing multiple images per line to mirror
racing thoughts."*

**Why it matters.** Density is itself part of the emotional effect, not
just a stylistic accident — turning a sparse, spacious verse into a denser
English rendering (often a real risk, since re-expression can require more
words than the original used) changes the felt pacing of the song even if
every individual meaning is preserved.

---

## 12. Poetic Style

**What it captures.** The songwriter's characteristic voice at the level
of language itself: diction (plain/vernacular vs. elevated/literary),
rhyme approach (perfect rhyme, slant rhyme, no rhyme at all), syntax
habits (fragments vs. full clauses, inverted vs. plain word order), and any
signature verbal tics specific to this songwriter or this song.

**Representation.** `{diction_register, rhyme_type, syntax_tendency,
signature_devices}`.

**Why it matters.** This is the dimension that keeps a re-expression from
sounding generically "poetic" instead of sounding like *this* song — a
songwriter who never uses a perfect rhyme and writes almost entirely in
plain vernacular fragments has a voice that a lushly rhymed, syntactically
ornate English rendering will betray, however pretty the result is on its
own.

---

## 13. Songwriter Intention

**What it captures.** The synthesizing, highest-level layer: a stated
hypothesis, built from evidence in the other eleven dimensions, about
*why* the song is built the way it is — why this ambiguity was left open,
why this word instead of an easier synonym, what specific effect on a
listener each major craft choice seems built to produce. This is
explicitly a hypothesis, not a biographical fact about the songwriter —
it is inferred from the text's craft evidence, not from outside knowledge
about who wrote it or why.

**Representation.** A short synthesizing statement per major craft
decision, each citing which of the other eleven fields the inference is
drawn from — e.g. *"the chorus repeats with one word changed at the end
(§9 Repetition) precisely where the emotional arc turns (§2); the
intention appears to be making the listener feel the change land in the
same breath as the words that carried it unchanged the whole song."* This
is the field every other agent in the room ultimately answers to: it is
the closest thing to "what is this song trying to do," stated as plainly
as the twelve dimensions can support.

**Why it matters.** Without a synthesizing intention statement, the other
eleven dimensions remain a pile of correct observations with no stated
throughline — this is the field that turns analysis into a usable creative
brief, the same way a director's read of a scene turns a shot list into a
scene that means something.

---

## 14. Worked Example

Illustrative verse–chorus (original, written for this document):

> **Verse:**
> She keeps his letters in a locked drawer,
> the way you keep a wound you won't let heal.
>
> **Pre-chorus:**
> Every night she turns the key,
> just to feel it hurt again.
>
> **Chorus:**
> And still she keeps the drawer locked tight —
> not because she's forgotten,
> but because she's afraid of what forgetting means.
>
> **Bridge:**
> Tonight, for the first time,
> she leaves it open.

**Whole-Song DNA**
- `artistic_thesis`: "Holding onto pain can be its own form of loyalty —
  and letting go doesn't mean the loss mattered less."
- `arc_shape`: slow ambivalence resolving into a single, quiet release.
- `songwriter_intention`: the song spends three sections justifying an act
  of self-harm (deliberately reopening a wound nightly) as devotion, so
  that the final section's small, unremarked action — leaving the drawer
  open — lands as the actual emotional turn, without needing to state that
  it's a turn at all.

**Section DNA (selected fields)**

| Section | Emotional arc | Vulnerability | Density | Narrative function |
|---|---|---|---|---|
| Verse | low intensity, guarded | buried in imagery (wound as metaphor, not stated feeling) | sparse — one image, no elaboration | setup |
| Pre-chorus | rising, compulsive | stated plainly ("just to feel it hurt again" — an admission of the compulsion itself) | sparse | escalation |
| Chorus | held, defensive | undercut by rationalization ("not because... but because...") — the most vulnerable line in the song, delivered as a justification rather than a confession | moderate | hook/thesis |
| Bridge | sudden release | plainly stated action, zero explanation | sparsest section in the song — four words fewer than any other line | resolution |

**Device Ledger**
- **Motif** (`the locked drawer`): occurs in verse (locked, guarded),
  chorus (locked, now explicitly defended/rationalized), bridge (unlocked
  — the pattern breaks). `resolves_or_breaks_at_end`: breaks, and the break
  *is* the song's meaning.
- **Repetition**: "locked" recurs verse→chorus unchanged, then is
  deliberately absent in the bridge — an omission functioning as the
  payoff of a repetition pattern, not a new repetition itself.
- **Symbolism**: the wound (§6) is archetypal (register:
  `archetypal` — needs little cultural translation); the locked drawer is
  this song's own invented symbol (register: `invented_for_this_song`) and
  must be tracked as specifically *this song's* device, not treated as
  generic imagery.

This single page is what every Writers' Room agent receives before
touching a single line — the Psychologist already knows the chorus is the
most vulnerable moment and *why* it's disguised as rationalization; the
Film Critic already knows the bridge's job is release and that its power
comes partly from being the sparsest, shortest section in the song; the
Songwriter already knows not to over-explain the bridge, because the
source doesn't either.

---

## 15. How This Feeds the Room

`WRITERS_ROOM.md` §1 originally specified a per-line Experience Note as the
room's shared starting context. Song DNA replaces that as the *primary*
shared context, built once per song before any section is drafted:

- The **whole-song DNA** (thesis, arc shape, intention) is given to every
  agent before Round 1 of every section — this is what lets the Film
  Critic check a single chorus line against the song's actual shape, not
  just against its immediate neighbors.
- The relevant **section DNA** is the direct working brief for that
  section's Round 1 generation — replacing the narrower "literal gist /
  emotional core" note with the fuller craft profile above.
- The **device ledger** is consulted every time a line touches a
  recurring motif, image system, or repetition pattern, so no section is
  drafted or judged without knowing it's part of a longer thread.
- The Judge's rationale (`WRITERS_ROOM.md` §7.3) now cites Song DNA fields
  directly — "chose X over Y because the bridge's job (§10, resolution) is
  to be the sparsest section (§11), and Y reintroduces imagery density the
  DNA marks as deliberately absent here."

---

## 16. Failure Modes

- **Analyzing sections in isolation.** Building each section's DNA without
  cross-referencing the device ledger produces technically correct
  per-section analysis that misses exactly the connective devices (motif
  evolution, repetition payoffs) that make a song more than its parts —
  the device ledger must be built and consulted *across* sections, not
  derived from summing section-level notes after the fact.
- **Confusing ambiguity with vagueness.** Flagging every underspecified
  line as "deliberate ambiguity" (§5) to avoid making an interpretive call
  produces a DNA that's useless as a creative brief — the
  `is_the_ambiguity_the_point` judgment has to be a real, arguable claim,
  not a hedge.
- **Treating vulnerability as a synonym for sadness.** Vulnerability (§7)
  is about exposure and cost, not valence — a triumphant, angry, or
  celebratory line can be just as vulnerable (or just as guarded) as a sad
  one; scoring this dimension as "how sad is this" collapses it into
  something the emotional arc (§2) already covers, wasting the dimension.
- **Symbol register drift.** Marking a song's invented, specific symbol as
  `archetypal` because it resembles a common image (a locked drawer isn't
  a rare image type) loses exactly the specificity that makes it *this*
  song's device rather than generic imagery — register should be judged by
  how the song treats the symbol, not by how common the image is in
  general.

---

## 17. Future Improvements

- **Cross-song DNA comparison** — once multiple songs by the same artist
  or in the same tradition have been profiled, compare their Song DNAs to
  detect a songwriter's or genre's characteristic patterns (a signature
  motif type, a habitual arc shape), feeding back into faster, more
  confident analysis on new songs from a known source.
- **Confidence and disagreement on DNA judgments themselves** — several
  fields here (ambiguity's `is_the_ambiguity_the_point`, symbolism's
  `register`, intention's whole premise) are genuine interpretive calls
  that could reasonably be disputed; a future version could carry the same
  confidence/disagreement machinery specified for the Experience Graph
  (`EXPERIENCE_GRAPH.md` §7) rather than presenting every field as settled.
- **Section-boundary sensitivity** — the current model assumes clean
  verse/chorus/bridge boundaries; songs that blur or subvert conventional
  structure (no clear chorus, a single continuously-developing verse) need
  a boundary-detection step ahead of Section DNA construction that this
  document does not yet specify.

*End of document.*
