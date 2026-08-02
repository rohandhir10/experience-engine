# AURA V2 — Multilingual Design

Extends the existing engine. Nothing here replaces Song DNA, the Writers'
Room, the Burden of Change constitution, the Judge, the five dimensions,
the five adaptation philosophies, the deviation ledger, motif memory,
voice consistency, or deterministic grounding. Every change is additive,
and Phase 1 is provably behavior-neutral.

## 0. The asymmetry that decides the whole design

Read the code before designing against it:

- `source_language` appears in **one** prompt — `prompts.py:91`, the Song
  DNA call — as a free-text string. The Translator, Creative Adapter,
  Judge, and all three specialists never receive it. All source-language
  reasoning is implicit in the model's read of the source text.
- `target_language` is threaded through every prompt, every room
  function, the pipeline, and the scoring enum
  (`natural_target_language`). It also has **deterministic tooling**
  behind it: `rhythm.py` counts English syllables via CMUdict, and
  `verify.py` checks the target text against English word lists
  (`EMOTION_WORDS`, `INTENSIFIERS`, `EXPLANATORY_CONNECTIVES`).

Therefore:

| Direction | What it costs |
|---|---|
| **More source languages** (Japanese → English) | Prompt *knowledge*: what the tradition is, what traps the grammar sets. Plus optional source-side grounding. No tooling rewrite. |
| **More target languages** (English → Japanese) | Rebuilds `rhythm.py`'s counter, invalidates every word list in `verify.py`, and needs a native-speaker reviewer pool for the new target. |

**V2 = many sources → English. Target expansion is V3.** The rest of this
document assumes that split. Where a decision differs for target
expansion, it says so.

## 1. Song DNA

**The schema does not change. No new fields.** What changes is prompt
guidance for four fields that cannot be filled well without knowing the
tradition.

Language-agnostic (unchanged, no profile input):
`artistic_thesis`, `arc_shape`, `turn_points`, `emotional_arc_point`,
`narrative_function`, `density`, `imagery` (image / sensory_channel /
stands_in_for), `motifs`, `repetition_patterns`, `ambiguities`,
`vulnerability.what_is_admitted` / `felt_cost`. These describe craft, not
language. A river standing in for time is a river standing in for time in
any language.

Needs language-specific reasoning:

- **`genre_feel`** — "ghazal", "enka", "trot", "qasida", "romancero" are
  not interchangeable with "ballad". Without tradition vocabulary the
  model defaults to Anglo-American genre labels and the Judge then scores
  `genre_authenticity` against the wrong tradition.
- **`style.rhyme_type`** — rhyme is a structural property of the
  language: Arabic classical monorhyme (*qāfiya*), Japanese verse largely
  non-rhyming, Russian morphologically rich rhyme, Spanish assonant rhyme
  as a first-class form. Free string today, which is the right shape; it
  just needs guidance.
- **`style.diction_register`** — register axes differ in kind, not
  degree: Hindi's Sanskritized ↔ Persianized spectrum, Korean honorific
  levels, Japanese keigo/plain.
- **`symbols.symbol_register`** — the enum values stay
  (`archetypal | culturally_specific | invented_for_this_song`), but the
  *boundary between them moves per culture*. Cherry blossom is archetypal
  **within** Japanese and culturally-specific **to** an English reader.
  Without calibration the model classifies against an implicit
  English-reader default, which mis-routes the Cultural Historian.

One calibration note, not a schema change: `vulnerability.directness`
values are universal *categories*, but "stated plainly" sits at a
different baseline in Hindi film lyric than in Japanese verse. The
profile calibrates the baseline; it never adds enum values.

## 2. Writers' Room

**Agent roster unchanged. `SPECIALIST_AGENTS` stays the same three.**
Per-language specialists are explicitly rejected: they multiply agents ×
languages and destroy the minimal-room cost model that V1 exists to
prove.

- **Translator** — prompt structure identical; brief gains
  profile-supplied *structural traps*. These are real and currently
  invisible: Japanese omits subjects (the Translator silently invents
  one instead of flagging it as inferred); Korean honorifics encode a
  relationship English pronouns drop entirely; Hindi's tu/tum/aap;
  Russian verbal aspect; Arabic dual and gendered forms. Naming them
  turns a silent invention into a declared inference.
- **Creative Adapter** — the five philosophies stay **exactly** as they
  are. `native_english_lyricist` is correctly target-side and needs no
  change while the target is English. What it gains is source-tradition
  context it must not flatten.
- **Specialists** — the Cultural Historian's brief receives the profile's
  tradition knowledge. The Native Speaker is target-side; unaffected by
  source expansion (and becomes the critical agent in V3).
- **Routing** (`routing.py`) — the mapping stays. One optional addition:
  a per-profile `cultural_density_baseline`, because a raw count of
  culturally-specific symbols means different things in a tradition
  that is symbol-dense by default (Arabic, Japanese) versus one that
  isn't. Defaults to current behavior when absent.

## 3. Burden of Change

**The six laws' text does not change in any language.** They govern the
relationship between the literal anchor and the adaptation — a
relationship that has no language.

Universal, zero profile input: **Law 1** (No Invention), **Law 2**
(Preserve Artistic Identity), **Law 5** (Ambiguity Lock), **Law 6**
(Minimum Change), and both gates (Literal Accuracy, Authenticity).

Identical rule, per-language *calibration*:

- **Law 3, Compression Floor.** The rule already contains the seam:
  connectives required for *grammaticality* are exempt; connectives that
  only explain an implicit relationship are not. Which is which depends
  entirely on the source: Japanese and Korean drop subjects and carry
  relations in particles, so English must add scaffolding merely to
  parse; Hindi drops copulas; Arabic coordinates with *wa-* where
  English would subordinate. The profile supplies what this specific
  language forces English to add.
- **Law 4, Restraint Ceiling.** "Don't add emotion words the source
  doesn't have" is universal. But the source's *own* baseline directness
  is a tradition property — Hindi film lyric is conventionally more
  emotionally direct than Japanese verse. Rendering Hindi at Japanese
  restraint under-translates; the reverse inflates. The profile states
  the baseline so the ceiling is measured from the right floor.
- **The pun exception** (constitution §wordplay) — identical rule; the
  profile flags whether the language is pun-dense (Japanese
  *kakekotoba*, Arabic *jinās*), which changes how often it fires.

## 4. Judge

**All five dimensions stay. No new dimensions, no removals.**

- `natural_target_language` — target-side. Completely unaffected by
  source expansion. (Already correctly renamed away from
  `natural_english` in the V1 freeze.)
- `voice_consistency` — unaffected.
- `artistic_fidelity` — dimension unchanged; needs source-tradition
  awareness to know what "the lyricist's own restraint" looks like there.
- `genre_authenticity` — **most affected.** It asks whether the output
  reads as real work in the source's genre/tradition. That is
  unanswerable without tradition vocabulary. Profile-injected.
- `singability_rhythm` — affected on the **source side only** (§5).
  Target-side grounding is unchanged while the target is English.

Should the Judge understand source poetic traditions? Yes — delivered as
profile-injected context in the existing prompt, not as a new dimension
and not as a new agent. The Judge already receives `genre_feel`; the
profile gives it the vocabulary to reason about that value instead of
pattern-matching it to the nearest English genre.

## 5. Deterministic grounding

Current state: `rhythm.py` counts English syllables (CMUdict via
`pronouncing`, vowel-cluster fallback). `source_syllable_estimate()`
returns **None** for any non-Latin script rather than fabricating a
number — that honesty is the foundation to build on.

Target side (English): unchanged, correct, keep.

Source side, per language:

- **Hindi / Punjabi (Devanagari)** — currently None. Devanagari is an
  abugida: syllables ≈ consonant clusters + independent vowels, adjusted
  for *virama* (्, suppressing the inherent vowel) and **schwa deletion**
  (rule-governed in Hindi: word-final and certain medial schwas drop).
  Fully deterministic. Medium effort, high accuracy. **Biggest immediate
  win** — it is the current production language and it has no grounding
  at all today.
- **Korean (Hangul)** — the easiest non-Latin language by a wide margin.
  Each Hangul syllable block *is* one syllable by construction; count
  code points in U+AC00–U+D7A3. Near-trivial, near-perfect.
- **Japanese** — not syllables, **morae**. ん, っ, and the long-vowel ー
  each count as a full mora; small ゃゅょ (*yōon*) combine with the
  preceding kana into one. きょう = 2 morae from 3 characters. Purely
  deterministic **from kana**. Kanji require readings — a morphological
  analyzer (fugashi/MeCab) or supplied furigana. Without a reading,
  return None rather than guess.
- **Russian** — syllable count = vowel count; trivially deterministic
  from the small Cyrillic vowel set. But the artistically load-bearing
  unit is **stress**: Russian verse is syllabo-tonic, and stress is
  lexical, not derivable from spelling. Ship vowel-count syllables
  immediately; treat stress as a separate later signal requiring a
  dictionary.
- **Spanish** — rule-governed but genuinely tricky: **synalepha** (vowels
  merging across word boundaries — *la alma* is 2 syllables, not 3),
  diphthong/hiatus rules, and the verse convention adjusting length by
  final-word stress (agudo +1, esdrújulo −1). Deterministic, no
  dictionary needed. Medium effort.
- **Arabic** — two hard blockers. Short vowels are usually unwritten, so
  syllable count is not recoverable from undiacritized text without
  morphological analysis. And classical Arabic poetry is not
  syllable-counted at all: it is quantitative meter (*ʿarūḍ*), long/short
  patterns across 16 canonical *buḥūr*. Syllable count is the **wrong
  unit**. Require diacritized (*mushakkal*) input, or return None. Do not
  fake it.

Design: `rhythm.py`'s public interface stays. Add a per-language counter
registry behind it, and carry a **unit label** alongside the number so
the Judge never compares morae to syllables as though they were the same
quantity. The Judge prompt already accepts `source_syllables: int | None`
— extend it to carry the unit. The existing honesty rule stands
everywhere: **None is always allowed; fabrication never is.** Note also
that the source figure was always a loose reference point rather than a
target; across scripts it is looser still, and the prompt must keep
saying so.

## 6. Cultural Anchors

The engine must choose, per culturally dense term, one of four
dispositions:

| Disposition | When |
|---|---|
| `preserve` | Load-bearing **and** already current in the target (*saudade*, *hygge*), or it is the work's own title/hook |
| `preserve_with_gloss` | Load-bearing, not current in the target, and a light gloss fits the rhythmic slot |
| `adapt` | The density is real but a target-language equivalent carries the load |
| `translate_plainly` | The density is incidental at this occurrence |

This is not new machinery — it generalizes a rule the constitution
already contains (the narrow title-word exception: untranslated only if
it is the work's own hook **and** a gloss fits without breaking the
Compression Floor). V2 supplies the missing input: how recognizable the
term already is in the target.

Inputs, all of which already exist or are cheap:

1. **Load-bearing?** — Song DNA already answers this (`artistic_thesis`,
   `symbol_register: culturally_specific`, title/hook position).
2. **Target recognizability** — from the profile's anchor lexicon: a
   small, high-precision, per-language list (*saudade*, *duende*,
   *hygge*, *wabi-sabi*, *mono no aware*, *pasoori*, *jugaad*, *han*),
   each rated for existing currency in the target. A hint source, never
   the decision-maker.
3. **Rhythmic fit** — already computable from `rhythm.py`.
4. **Consistency** — a recurring anchor must be handled identically every
   time, which **Law 5 already enforces** through `motif_renderings`.

One additive field: `JudgeRuling.cultural_anchors: list[AnchorDecision]`
(term, disposition, rationale), defaulting empty — the same pattern as
`motif_renderings`. That makes the decision auditable, and lets
`verify.py` check cross-section anchor consistency exactly as it already
checks motif renderings.

## 7. Language Profiles

A profile contains **only what is genuinely unique to that language**.
Anything universal stays in the shared prompts.

```
LanguageProfile
├── code, name, scripts
├── Song DNA guidance (the four fields from §1)
│   ├── genre_traditions
│   ├── register_axis
│   ├── rhyme_convention
│   └── symbol_calibration        # archetypal WITHIN vs specific TO
├── structural_traps: [str]       # Translator: omitted subjects, honorifics, aspect
├── constitution calibration
│   ├── grammatical_scaffolding_note   # Law 3: what English must add to parse
│   └── emotional_baseline             # Law 4: this tradition's default directness
├── grounding_unit                # syllables | morae | blocks | None
├── anchor_lexicon: [CulturalAnchorEntry]   # term, meaning, target_recognizability
└── cultural_density_baseline     # routing: what counts as unusually dense here
```

**Integration without touching control flow** — the mechanism already
exists in the codebase twice:

- `agent_brief()` already does `.replace("{target_language}", ...)`.
  Extend with `{structural_traps}`, `{genre_traditions}`, etc.
- `_voice_line()` already returns `""` when voice is None, keeping
  single-voice prompts byte-identical. Profile blocks do the same.

Resolution: `SongInput` gains one optional field,
`source_language_code: str | None`. Resolve profile from it; fall back to
matching the existing `source_language` string; fall back to a **neutral
default profile whose every field is empty**. The default renders every
placeholder to `""`, which reproduces today's prompts exactly — that is
the no-regression guarantee, and it is testable byte-for-byte.

## 8. Engineering

**New files**

- `engine/language_profile.py` — the model, the registry,
  `resolve_profile()`, and the neutral default.
- `engine/profiles/*.json` — one per language. **Data, not code**, so a
  linguist can edit a profile without touching Python.
- `engine/grounding/` — per-language counters (`devanagari.py`,
  `hangul.py`, `kana.py`, `cyrillic.py`, `spanish.py`), registered
  behind `rhythm.py`'s existing interface.

**Modified (all additive)**

- `engine/prompts.py` — profile parameter on the builders; new
  placeholders that render empty by default. No prompt is restructured.
- `engine/rhythm.py` — counter registry; the English path is untouched.
- `engine/models.py` — `SongInput.source_language_code` (optional);
  `JudgeRuling.cultural_anchors` (optional, defaults empty).
- `engine/pipeline.py` — resolve the profile once, pass it down (~5
  lines).
- `engine/writers_room_v1.py` — thread the profile parameter, mechanically
  identical to how `voice` was threaded.
- `engine/verify.py` — add cross-section cultural-anchor consistency.
  Its word lists stay English **and stay correct** while the target is
  English; they become target-keyed only in V3.

**Untouched**

`song_dna.py` control flow, `llm_client.py`, `config.py`, `cli.py`,
`text_ingest.py`, `youtube_ingest.py`, all of `server/`, all of `web/`,
all of `benchmark/` except its corpora — and, critically, the six
constitution laws, the five dimensions, the five philosophies, and
`SPECIALIST_AGENTS`.

**Testing**

- **Golden-prompt regression** — snapshot every prompt string for a
  fixture song under the default profile and assert byte-identical after
  the refactor. This single test is what makes Phase 1 safe.
- Per-profile prompt tests: profile content present when set, absent
  when not.
- Grounding tests with hand-verified counts per language (きょう = 2
  morae; 한국어 = 3 blocks; Devanagari with virama and schwa deletion;
  Spanish synalepha).
- Profile completeness: every registered profile has all required fields
  non-empty.
- **The blind benchmark is the quality gate.** A language ships only
  after beating Google Translate / single-prompt GPT / single-prompt
  Claude on its own per-language corpus with its own bilingual
  reviewers.

**Configuration** — profiles load from `engine/profiles/` at import, with
an `AURA_PROFILE_DIR` override so a profile can be iterated without a
code change.

## 9. Product rollout

**One language at a time. Not all at once.** Three reasons, in order of
weight: the benchmark is the gate and each language needs its own
bilingual reviewer pool (you cannot recruit six simultaneously); a bad
language damages the trusted-fidelity brand that *is* the moat; and
per-language failure modes are invisible without per-language evaluation.

| # | Language | Why here |
|---|---|---|
| 1 | **Hindi/Urdu/Punjabi** | Already the de facto language — formalizing it as a profile is the strongest possible regression test of the profile system itself. Existing corpus, existing reviewer access, zero new artistic risk. Also unlocks Devanagari grounding, which is missing today. |
| 2 | **Korean** | Best value-to-effort of any new language: grounding is near-trivial (Hangul blocks), the K-pop market has enormous existing demand for English lyric translation, and the reviewer pool is large and reachable. |
| 3 | **Spanish** | Largest speaker base; syllable rules are documented and dictionary-free; easiest reviewer recruitment; Latin script means parts of the existing path already work. |
| 4 | **Japanese** | Artistically the domain where AURA *should* shine most (restraint, implication, omitted subjects) — and where failure is most invisible to a non-speaker. Mora counting is clean for kana; kanji readings add a real dependency. |
| 5 | **Russian** | Syllables trivial, but the load-bearing unit is stress, which needs a dictionary. Strong verse tradition sets a high artistic bar. |
| 6 | **Arabic** | Deliberately last. Undiacritized text blocks deterministic grounding, and classical meter means syllable count is the wrong unit entirely. Highest combined technical and artistic risk. |

## 10. Risks

| Language | Biggest technical | Biggest artistic | Biggest evaluation |
|---|---|---|---|
| Hindi/Urdu/Punjabi | Schwa deletion rules; code-switching mid-line (Sadda Haq) | Sanskritized ↔ Persianized register carries meaning English flattens | Reviewers must be genuinely bilingual, not heritage-familiar |
| Korean | Almost none — Hangul is clean | Honorifics encode relationships English pronouns erase | Distinguishing "good English lyric" from "faithful to the Korean" |
| Spanish | Synalepha and stress-based verse-length adjustment | Enormous regional variation — which Spanish? | Reviewers may disagree by region, not on quality |
| Japanese | Kanji readings require a morphological analyzer | Restraint and omitted subjects: the model will over-explain by default | Non-speakers cannot detect over-explanation; needs strict reviewers |
| Russian | Lexical stress needs a dictionary | Syllabo-tonic meter is load-bearing and unpreservable in English | Small reviewer pool with strong, divergent verse opinions |
| Arabic | Undiacritized text defeats grounding; diglossia (MSA vs dialect) | ʿarūḍ meter and classical allusion density | Classical-form expertise is rare and expensive |

## Migration roadmap

> **Status: Phase 1 complete; Phase 2 profiles built, benchmark gate not
> yet cleared.**
>
> Shipped: `engine/language_profile.py`, `engine/grounding/` (Devanagari
> with schwa deletion, Hangul, Spanish with synalepha, Japanese morae
> with kanji readings), profiles for **Hindi, Korean, Spanish, and
> Japanese**, `SongInput.source_language_code`,
> `JudgeRuling.cultural_anchors` (now actually requested from the Judge,
> but only when the source language has an anchor lexicon, so neutral
> prompts stay byte-identical), the cultural-anchor consistency check in
> `engine/verify.py`, and `tests/test_golden_prompts.py`.
>
> **Not yet done, and required before any language is considered
> launched:** each profile must clear its own blind benchmark run
> (`benchmark/`) against Google Translate and single-prompt GPT/Claude,
> with that language's own bilingual reviewers. The Korean and Spanish
> profiles are written from linguistic principle and are untested against
> real songs. Treat them as drafts for review by a native speaker, not as
> validated.
>
> Japanese was pulled forward out of Phase 3 on request. Russian and
> Arabic, and separately target-language expansion, remain as described
> below.

**Phase 1 — behavior-neutral scaffolding.** Ship the profile system with
a neutral default that changes nothing, proven by byte-identical
golden-prompt tests. Add `source_language_code` and
`JudgeRuling.cultural_anchors` (both optional, defaulting to today's
behavior). Add Devanagari and Hangul source grounding — pure additions,
since both return None today. **No language behaves differently at the
end of Phase 1.** Risk: near zero.

**Phase 2 — language profiles, one at a time.** Hindi first, as the
regression proof: its benchmark scores must not drop relative to the
pre-profile baseline. Then Korean, then Spanish. Each language ships only
after clearing the blind benchmark against Google Translate and
single-prompt GPT/Claude on its own corpus with its own reviewers.

**Phase 3 — full multilingual, and the target-side problem.** Japanese,
Russian, Arabic as source languages, each with its grounding strategy.
Separately and explicitly: **target-language expansion (English → X) is
a different project.** It requires rebuilding `rhythm.py`'s target
counter per language, re-deriving every word list in `verify.py` per
target, and recruiting native-speaker reviewers *of the target*. Treat it
as V3 with its own design pass, not as a continuation of V2.

Throughout: AURA exists to preserve artistic experience, not to translate
words. Every addition above serves that principle by giving the existing
machinery the tradition-specific knowledge it needs to apply the same
constitution correctly in more places — not by loosening it.
