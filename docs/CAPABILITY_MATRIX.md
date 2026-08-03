# AURA capability matrix

A verified audit of what the engine actually does, per supported language,
against the craft dimensions that determine adaptation quality. Every cell
is checked against the implementation directly — file, module, or
function named — never estimated. Update this file whenever a phase adds,
removes, or changes a capability; treat it as the source of truth for
"what does AURA actually do" ahead of any prose description elsewhere.

Supported languages (fixed roster, per the scope freeze): Hindi (`hi`),
Korean (`ko`), Japanese (`ja`), Spanish (`es`) — as source languages, all
adapting into English. The scope was later extended to the reverse
direction too (English -> any of the same four; see
`engine/models.py::SUPPORTED_TARGET_LANGUAGES`), but that direction is
**not** covered by the matrix below: every row here is either measured
against the shipped **English** output specifically (stress, rhyme,
singability — all CMU-Pronouncing-Dictionary-backed, English-only tools)
or describes source-side understanding of one of these four languages.
None of it transfers to a Hindi/Korean/Japanese/Spanish *output* — those
checks are deliberately skipped rather than run against a script/language
they were never built for (`engine/verify.py` gates them on
`target_language == "English"`). The reverse direction today gets the
same prompt-level craft (Song DNA, Writers' Room, Burden of Change) but
none of the deterministic rhythm/rhyme verification; a real capability
audit for it is future work once each target language has its own
prosody tooling, not a one-line addition to this table.

## Status legend

- **Full** — deterministic, tested, consumed by generation or verification.
- **Partial** — real and consumed, but incomplete, conditional, or
  covering only part of the claim (see notes).
- **Not implemented** — no code produces this; described in prose only
  (Tier 0), or absent entirely.

## Matrix

| Dimension | Hindi | Korean | Japanese | Spanish |
|---|---|---|---|---|
| Phoneme support | Not impl. | Not impl. | Not impl. | Not impl. |
| Syllable/mora support | Full | Full | Partial | Full |
| Stress support | Partial (Phase 3A) | Partial (Phase 3A) | Partial (Phase 3A) | Partial (Phase 3A) |
| Rhyme detection | Partial (Phase 3B) | Partial (Phase 3B) | Partial (Phase 3B) | Partial (Phase 3B) |
| Meter | Not impl. | Not impl. | Not impl. | Not impl. |
| Hook/chorus handling | Partial | Partial | Partial | Partial |
| Chorus variation | Not impl. | Not impl. | Not impl. | Not impl. |
| Repetition | Partial | Partial | Partial | Partial |
| Genre routing | Not impl. | Not impl. | Not impl. | Not impl. |
| Cultural symbolism | Partial (5 terms) | Partial (9 terms) | Partial (7 terms) | Partial (5 terms) |
| Idiom handling | Not impl. | Not impl. | Not impl. | Not impl. |
| Register | Partial | Partial | Partial (script-as-register uncaptured) | Partial |
| Register shifts (as device) | Not impl. | Not impl. | Not impl. | Not impl. |
| Singability | Partial | Partial | Partial (weaker: grounding can degrade to None) | Partial |
| Emotional fidelity verification | Partial (anchor-only) | Partial (anchor-only) | Partial (anchor-only) | Partial (anchor-only) |

Ten of fifteen rows are identical across all four languages by
construction — they live in shared pipeline code (`verify.py`,
`models.py`, `song_dna.py`), not per-language profiles. That is accurate,
not an audit shortcut.

## Stress support (Phase 3A) — detail

- **Mechanism:** `engine/rhythm.py::stress_pattern_word` /
  `stress_pattern_line` (raw CMU-dictionary stress, per language-agnostic
  English output text) + `engine/verify.py::_stress_pattern_for_clash_detection`
  (forces `FUNCTION_WORDS` to unstressed, correcting a real bug found
  during Phase 3 testing: CMU marks isolated monosyllabic function words
  as stressed in citation form, which is not how they behave in
  connected speech).
- **Tier:** 1 for words in the CMU dictionary; unresolved (`x`) for
  out-of-dictionary words, never guessed.
- **Consumer:** `verify.py`'s "Stress check" finding (clash: 3+
  consecutive stressed syllables; lapse: 5+ consecutive unstressed),
  both warning-severity, both disclosed as provisional general-English-
  prosody thresholds, not corpus-calibrated per genre.
- **Applies identically across all four source languages**, because it
  measures the shipped **English** output only — there is no source-side
  stress baseline for any of the four languages (that remains Not
  Implemented on the source side for all of them).
- **Benchmark coverage:** unit-tested (`tests/test_rhythm.py`,
  `tests/test_verify.py`), including a regression test for the function-
  word bug found while testing against real Ghalib output during this
  phase. Not corpus-benchmarked.

## Rhyme detection (Phase 3B) — detail

- **Mechanism:** `engine/rhyme.py::rhyming_part_word` /
  `end_rhyme_scheme` / `rhyme_density`, using `pronouncing.rhymes()` /
  `rhyming_part()` (pronunciation-based, not spelling-based — "fire"/
  "higher" rhyme, "though"/"through" do not, despite what the spelling
  suggests).
- **Tier:** 1 for resolvable end words; `None` (not 0.0) when too few
  words are resolvable — reported as unmeasured, not as an absence of
  rhyme.
- **Consumer:** `SectionVerification.rhyme_density`, reported in
  `verify.py`'s summary. Deliberately **never** turned into a pass/fail
  Finding — what counts as "enough" rhyme varies by language (Hindi film
  couplets expect dense rhyme; the Japanese profile explicitly documents
  that traditional verse does not rhyme at all) and no corpus exists yet
  to calibrate a threshold per language/genre.
- **Benchmark coverage:** unit-tested (`tests/test_rhyme.py`,
  `tests/test_verify.py`). Not corpus-benchmarked.

## Phoneme repetition similarity — detail

- **Mechanism:** `engine/rhyme.py::phoneme_distinct2` /
  `phoneme_repetition_similarity`, adapted from Kim, Watanabe, Goto & Nam,
  "A Computational Evaluation Framework for Singable Lyric Translation"
  (ISMIR 2023)'s Sim_pho. Their metric compares a source-language
  section's phoneme-bigram diversity (distinct-2) against the target-
  language section's, correlated (Spearman) across a whole song. AURA
  only has a G2P tool for English (the CMU dictionary), so the
  cross-language comparison isn't reproducible honestly — adapted
  instead to a same-language comparison AURA can actually make: the
  Translator's literal anchor vs. the Judge's shipped final line, both
  English. Asks a related but distinct question from the paper's
  original: not "does the target preserve the source's repetition
  pattern" but "did adapting away from the literal anchor distort the
  repetition pattern a faithful rendering would have had."
- **Tier:** 1 (computed) when at least 3 sections have a CMU-resolvable
  phoneme count on both sides; `None` otherwise — never computed from
  too little data and reported as if it meant something.
- **Consumer:** `VerificationReport.phoneme_repetition_similarity`
  (song-level, not per-section), reported in `verify.py`'s summary.
  Deliberately never turned into a pass/fail Finding — same reasoning as
  rhyme_density, and the paper itself doesn't establish a hard threshold
  either, only that singable translations correlate higher on average
  than non-singable ones across a large corpus.
- **English-target only** — same gate as Stress/Rhyme/Singability, for
  the same reason (CMU dictionary).
- **Benchmark coverage:** unit-tested (`tests/test_rhyme.py`,
  `tests/test_verify.py`). Not corpus-benchmarked against AURA's own
  output at scale — the paper's own singable-vs-non-singable averages are
  a reference point, not a validation of AURA specifically.

## Poetic register + Tonal Coherence gate + Phrase-end sustainability — detail

Added when the reverse direction (English -> Hindi/Korean/Japanese/
Spanish/Urdu) and direct pairs (e.g. Hindi -> Korean) made it clear that
hardcoding specific cultural mappings ("Sufi -> Flamenco") would break on
the next genre or language pair fed in. All three are typology-agnostic
by design — none names a specific language or culture in code.

- **`poetic_register`** (`SongDNA.poetic_register`, `engine/prompts.py`'s
  Song DNA extraction): the song's rhetorical/spiritual register (sacred-
  devotional, street-vernacular, melodramatic, elegiac, etc.), distinct
  from `genre_feel` (musical genre). **Tier 0** — an LLM classification,
  not a measured value; there is no controlled vocabulary or corpus
  behind it. The Creative Adapter is instructed (constraint 9,
  `AGENT_BRIEFS["creative_adapter"]`) to match this register using the
  *target* language's own equivalent tradition, never an untranslated
  source-culture term — but nothing verifies that it actually did.
- **Tonal Coherence gate** (`engine/prompts.py::_judge_gates_and_dimensions`,
  third gate alongside Literal Accuracy and Authenticity): asks the Judge
  to disqualify a candidate whose surviving image reads as unintentionally
  grotesque or literal in the target language (the general form of "a
  raven eating flesh reads as horror, not devotion"). **Tier 0** — pure
  LLM judgment, prompt text only, no deterministic check backs it, and no
  test corpus yet confirms it actually catches real cases.
- **Phrase-end sustainability** (`engine/rhythm.py::phrase_end_sustainability`,
  `verify.py`'s "Phrase-end sustainability check"): **Tier 1**, actually
  measured — whether a shipped line's last word ends in a sound a singer
  can hold (vowel/nasal/liquid) or an unreleased stop consonant.
  Script-based, not source-language-based: supports Latin-script output
  (any target written in the Latin alphabet), Hangul (Korean, via
  algorithmic syllable-block decomposition + standard coda
  neutralization — real, textbook phonology, not a heuristic), and
  Devanagari (Hindi, via `engine/g2p_hi.py`'s schwa-deletion heuristic —
  see that module for the algorithm; validated against known-correct
  words कमल/करवट/नमक/एक but disclosed as a heuristic approximation with
  known exception classes, not a definitive solution), and — partially —
  Perso-Arabic (Urdu, via `engine/g2p_ur.py`). Unlike Stress/Rhyme above,
  this is NOT gated to `target_language == "English"` — it runs for any
  script it supports, regardless of the target language's name.
  **Urdu specifically stays partial by design, not by omission**: a word
  ending in an unambiguous long vowel, nasal, or liquid letter resolves
  with no diacritic needed, but a word ending in a bare stop/affricate
  consonant (`URDU_CLOSED_STOPS`) returns `None` rather than "closed" —
  because Urdu's izafat construction (an unwritten "-e-" vowel joining
  two nouns/adjectives — dast-e-tanha, kitab-e-zindagi — extremely
  common in exactly the ghazal/qawwali register this engine targets) can
  make that word actually sung open, and real lyrics almost never mark
  the diacritic that would settle it. Only an explicit sukun (or another
  disambiguating diacritic) resolves the stop-consonant case. This is
  not a smaller version of the Hindi problem — it is the same "don't
  guess a missing short vowel" discipline applied to the one letter
  class where guessing would flip the answer.
- **Benchmark coverage:** unit-tested (`tests/test_rhythm.py`'s Hangul
  cases hand-verified against known Korean words; `tests/test_g2p_hi.py`'s
  Hindi cases against known-correct words; `tests/test_g2p_ur.py`'s Urdu
  cases, including the izafat-ambiguity decline path; `tests/test_verify.py`).
  Not corpus-benchmarked; the Tier 0 pieces have no benchmark that could
  even measure them yet.

## Urdu source grounding — detail

Urdu was added late (full open language matrix + Urdu, source and
target), after the four-language matrix above was frozen — it is not a
fifth column in that table, which is scoped to the original phase. This
section documents what exists for it instead.

- **`engine/grounding/urdu.py::count_urdu`** — syllable counting for
  Perso-Arabic script. Urdu is an **abjad**, not an abugida like
  Devanagari: short vowels are optional diacritics (i'raab) that
  ordinary written Urdu — including virtually all real pasted lyrics —
  omits entirely. Without them there is no deterministic way to recover
  which consonant clusters carry a vowel; guessing would produce a count
  that looks exact and is fabricated. **Tier 1, but gated**: the counter
  only runs when a text's letters are, on average, at least half marked
  with explicit diacritics (`_MIN_DIACRITIC_DENSITY`) — the one case
  that genuinely is deterministic, the same algorithm used for
  fully-voweled Arabic. Ordinary undiacritized Urdu returns `None`,
  honestly, rather than approximating. `engine/g2p_ur.py`'s phrase-end
  coda (see "Phrase-end sustainability" above) applies the same
  discipline but resolves more real, undiacritized text than this
  counter does — it only needs to rule out an ambiguous ending on one
  word, not vocalize a whole line. In practice this means: a diwan or
  religious text pasted with full tashkil gets a real syllable count; a
  pasted song lyric almost always gets `None` here even though its last
  line may still get a real phrase-end answer.
- **`engine/profiles/urdu.json`** — genre traditions (ghazal couplet
  independence, radif/qafiya rhyme-refrain, qawwali's repetition-driven
  structure), the register axis (Persian/Arabic-derived literary diction
  vs. everyday Hindustani — the mirror image of Hindi's own axis),
  classical symbol calibration (moth/flame, wine/tavern/saqi, the
  deliberate sacred-vs-worldly ambiguity of *ishq*), and a five-term
  anchor lexicon (junoon, wisal, hijr, rind, saqi). **Tier 0** — authored
  from established literary-historical knowledge of the ghazal
  tradition, not from a corpus or native-speaker review; treat it with
  the same caution as any other profile's authored content.
- **Benchmark coverage:** unit-tested (`tests/test_grounding.py`'s Urdu
  cases, hand-traced against known-correct diacritized words before the
  code was written, same discipline as the Hindi/Hangul counters).
  Not corpus-benchmarked, and the profile's authored content has no
  native-speaker review yet.

## Deliberately deferred out of Phase 3

- **Genre-aware calibration (originally "Phase 3C").** Building a
  configurable-threshold mechanism now, with no genre-labeled corpus to
  calibrate it against, would ship an abstraction nobody consumes — the
  same reasoning that gated the `evidence_tier` field on Phase 2 existing
  first. Deferred until real corpus data exists.
- **Chorus-with-variation.** Real, common gap (a chorus repeating with
  one changed line has no structural representation — only exact-verbatim
  `repeats` and Phase 1's recurring-ending detection exist). Deferred
  because it requires new schema and orchestration, not a quick win like
  stress/rhyme.
- **Cross-language emotional fidelity verification.** Still the deepest
  open gap in the system — `verify.py` checks the shipped English only
  against the Translator's own anchor, never against the actual source
  text. Assigned to the research roadmap, not the engineering one: it
  requires bilingual NLI/back-translation (Tier 2 at best) or a
  fundamentally different verification approach, not a deterministic fix
  in the shape of Phases 1-3.
