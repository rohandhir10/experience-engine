# CASTIA capability matrix

A verified audit of what the engine actually does, per supported language,
against the craft dimensions that determine adaptation quality. Every cell
is checked against the implementation directly — file, module, or
function named — never estimated. Update this file whenever a phase adds,
removes, or changes a capability; treat it as the source of truth for
"what does CASTIA actually do" ahead of any prose description elsewhere.

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
  language section's, correlated (Spearman) across a whole song. CASTIA
  only has a G2P tool for English (the CMU dictionary), so the
  cross-language comparison isn't reproducible honestly — adapted
  instead to a same-language comparison CASTIA can actually make: the
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
  `tests/test_verify.py`). Not corpus-benchmarked against CASTIA's own
  output at scale — the paper's own singable-vs-non-singable averages are
  a reference point, not a validation of CASTIA specifically.

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
  test corpus yet confirms it actually catches real cases. Had a real bug
  from when it was first added until this was noticed while editing
  adjacent text: two of its `{target_language}` placeholders were missing
  their f-string prefix, so the Judge had been receiving the literal,
  unsubstituted string `"{target_language}"` in this gate's instructions
  the whole time, rather than the actual target language name.
- **Authenticity gate, extended to connotation** (same function):
  previously only asked "would a native speaker actually say this,"
  which checks structural naturalness but not whether a word's actual
  emotional charge survived. Added after a real production output
  translated Korean "땡" (a game-show wrong-answer buzzer) as English
  "ding" (which reads as success/approval) — structurally defensible,
  denotationally similar, but backwards in what a listener actually
  feels. The gate now explicitly asks whether an interjection/sound-word/
  slang term's polarity (mocking vs. celebratory, rejection vs.
  affirmation) matches the source, not just its literal meaning. **Tier
  0** — same caveats as above.
- **Burden of Change: specific/loaded words protected, not just
  structural devices** (same function): the deviation ledger's existing
  language protected "a repeated phrase, a rhetorical question, a working
  image" from being dropped with a weak justification like "sounds
  smoother." Added after real production outputs showed the same
  weak-justification failure applied to single word choices too —
  "consumo" (consumption, an extraction/exploitation metaphor central to
  the song) rendered as generic "use"; "sobra" (scraps/refuse, implying
  discarded worthlessness) rendered as generic "left" — both structurally
  fine, both quietly dropping the specific charge the source word was
  chosen for. Now requires the same real, specific justification (rhythm,
  rhyme, genuine unnaturalness) that dropping a repeated phrase already
  did. **Tier 0** — same caveats as above; no test corpus confirms this
  actually changes real output, since verifying it requires rerunning
  real songs through the full pipeline post-deploy, not something a unit
  test can check.
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

## Translator literal anchor: repetition preservation — detail

- **`AGENT_BRIEFS["translator"]`** (`engine/prompts.py`): the Translator's
  literal anchor is the floor everything else in the Writers' Room diffs
  against (the Creative Adapter, the Judge's Burden of Change ledger) —
  if it's wrong, nothing downstream can recover the truth. A real
  production run on a long, highly repetitive qawwali section (a chanted
  refrain repeated many times, two couplets each repeated twice) showed
  the anchor mentioning every image once but collapsing all the
  repetition to a single occurrence — a summary, not a transcription.
  The Creative Adapter's constraint #7 already protects its OWN output
  from exactly this; the Translator had no equivalent instruction for
  its own anchor. Added one: render every line in order, including exact
  repeats at the same count the source uses. **Tier 0** — prompt text
  only, no deterministic check confirms a shipped anchor actually
  preserved every repeat; a corpus-scale check would need to compare
  line counts between source and anchor programmatically, which nothing
  does today.
- **Benchmark coverage:** none beyond the golden-prompt hash test
  confirming the instruction is present in the rendered prompt
  (`tests/test_golden_prompts.py`). No test corpus confirms this
  actually changes real output — verifying that requires rerunning real
  songs through the deployed pipeline, not something a unit test can
  check.

## Generation token-budget scaling + shipped-line completeness check — detail

Found via a real production resubmission of the same Kun Faya Kun section
that exposed the repetition-preservation gap above, this time Hindi →
Japanese: the Translator's literal anchor correctly preserved every
repeat (that fix held), but the shipped Japanese Castia output was ~20
characters — one couplet's gist — against the anchor's 800+ characters
of correctly-repeated content. The entire sacred "Kun Fayakun" refrain
and a full stanza were silently dropped. The why-sentence description
only covered the tiny surviving change and gave no indication of the
scale of what was missing.

- **Root cause (`engine/writers_room_v1.py`):** `_generate`'s Creative
  Adapter call generates all 5 full candidates in one LLM response under
  a flat `max_tokens=4000`, regardless of source section length. A long,
  highly repetitive section that must preserve its repetition (per the
  fix above) needs meaningfully more output tokens than a short one;
  the Judge's own `judge_triage`/`judge_final` calls had the same flat-
  `max_tokens=3000` problem, needing to carry both the final line's own
  content and a Burden of Change ledger entry per candidate.
  `engine/llm_client.py`'s `complete_json` retries once on invalid JSON,
  but has no `finish_reason` check and no length-sanity check anywhere —
  a token-budget-truncated response can still "succeed" by producing a
  syntactically valid, drastically shorter retry, with nothing
  downstream ever told this happened.
- **Fix 1 — scale the budget instead of guessing a flat constant:**
  `_content_max_tokens(source_text, num_outputs, overhead_per_output,
  floor)` estimates ~2 characters per token (deliberately generous —
  accurate for token-dense CJK output, oversized for Latin-script
  output, since the failure being guarded against is truncation, not
  wasted budget) and multiplies by how many full outputs the call must
  produce. Applied to `translator` (1 output), `creative_adapter` (5
  outputs), and a `_judge_max_tokens(source_text, num_candidates)`
  variant (1 output, but overhead grows with candidate count) for
  `judge_triage`, `judge_final`, the schema-validation retry, and the
  corrective retry path. **Tier 1** in the narrow sense that the scaling
  itself is deterministic arithmetic, not LLM judgment — but whether a
  larger budget actually prevents truncation for any given real model
  response is not something a unit test can confirm; no test corpus
  exists proving this changes real output.
- **Fix 2 — a deterministic safeguard for when it happens anyway
  (`engine/verify.py`):** a new `completeness` `Finding`, severity
  `"error"`, comparing the shipped `final_line`'s character length
  against the MEDIAN length of that section's own `creative_adapter`
  candidates (`_creative_candidate_median_length`) — deliberately NOT
  compared against the Translator's anchor, which in every real example
  seen is written in English regardless of target language (confirmed:
  `AGENT_BRIEFS["translator"]` and `generation_prompt_v1` never instruct
  the Translator in what language to write its anchor), so a legitimately
  dense target script could look short next to an English anchor without
  being incomplete. Comparing same-script siblings instead avoids that
  false-positive class. Fires when the shipped line is under 35% of its
  siblings' median length, and only when that median itself is at least
  40 characters (too-short siblings make the ratio meaningless noise,
  not signal). Because it is `severity="error"`, it automatically
  triggers `engine/pipeline.py`'s existing
  `retry_section_with_finding` corrective-retry mechanism — no new
  wiring needed there. Note that retry re-runs only the Judge against
  the existing candidates (it does not regenerate the Creative Adapter's
  candidates), so this check is a genuine safety net against
  truncation in the Judge's own final-line synthesis; Fix 1 above is
  what actually prevents the candidates themselves from being truncated
  in the first place.
- **Benchmark coverage:** `tests/test_writers_room_v1.py` unit-tests
  `_content_max_tokens`/`_judge_max_tokens` as pure functions (grows with
  source length, grows with output/candidate count, floors correctly).
  `tests/test_verify.py` unit-tests the completeness `Finding` directly
  (flags a severely truncated line, stays quiet on a line close to its
  siblings' length, stays quiet when siblings are too short to compare
  meaningfully). No golden-prompt hash changed — this touched token
  budgets and a new deterministic check, not prompt text. No test corpus
  confirms either fix changes real output from the deployed pipeline —
  that requires the user resubmitting real songs, same as every other
  Tier 0 fix in this document.

## Multi-line repeated block (couplet/verse/stanza) preservation — detail

Found on the same real production resubmission that validated the
token-budget fix above (Kun Faya Kun, Hindi → Japanese): the refrain now
rendered in full, but two OTHER couplets that the source repeats twice
each (a verse and a bridge) were shipped only once each in the final
Japanese line. Constraint #7 (`AGENT_BRIEFS["creative_adapter"]`), the
Judge's `artistic_fidelity` dimension text, and the Judge's Burden of
Change mechanical paragraph (all in `engine/prompts.py`) previously only
named a repeated "phrase" or "line" — the model was reading a two-line
couplet as two individually droppable lines rather than one repeated
unit, and collapsing it down to one occurrence without logging it as a
deviation.

- **Fix:** all three locations now explicitly name repeated multi-line
  blocks ("a couplet, verse, or stanza the source restates verbatim")
  alongside single repeated phrases/lines, with the same burden-of-proof
  standard — dropping a repeat count on a multi-line block needs a real,
  specific justification tied to one of the five scored dimensions, same
  as any other deviation. Deliberately generic (no hardcoded song,
  language, or repeat count), so it applies to every language pair, not
  just Hindi → Japanese.
- **Tier 0** — prompt text only. No test corpus confirms this actually
  changes real output; verifying that requires the user resubmitting
  real songs through the deployed pipeline.
- **Benchmark coverage:** `tests/test_golden_prompts.py`'s
  `creative_adapter`/`judge_triage`/`judge_final` hashes updated with a
  changelog comment recording the change.

## Auto source-language detection on paste — detail

Previously, adapting into any target other than English required the
user to manually pick the source language from a second dropdown before
submitting — an extra click that also risked a wrong manual pick if the
user didn't know or misremembered which of the six roster languages the
pasted text was actually in.

- **`web/lib/detectLanguage.ts`** (new): a pure, deterministic,
  client-side heuristic — no LLM call, no network round trip, runs on
  every keystroke. Scoped ONLY to the six languages in
  `LANGUAGES`/`engine/models.py::SUPPORTED_LANGUAGES`, not general-
  purpose language ID: a Unicode script match unambiguously identifies
  Hindi (Devanagari), Urdu (Perso-Arabic), Korean (Hangul), or Japanese
  (Kana/Han) among this roster, since no other roster language shares
  those scripts. Latin-script text is disambiguated between English and
  Spanish only (the only two Latin-script languages in the roster) via
  an accented-character/inverted-punctuation check first, falling back
  to a stopword vote. Declines (returns `null`) rather than guessing when
  the signal is too thin — under 8 characters, no script majority, or
  Latin-script text with no Spanish marker and an even/absent stopword
  vote — leaving the field at its previous value rather than a
  confident-looking wrong guess.
- **Wiring (`web/components/InputScreen.tsx`, `web/app/dashboard/page.tsx`):**
  runs on every textarea change (and on a YouTube-imported draft) and
  pre-fills the "From" selector, but ONLY until the user manually touches
  that dropdown themselves — a `sourceLanguageTouched` flag stops
  auto-detection from fighting a deliberate manual choice. The user can
  always override the guess; a wrong detection costs one click, same as
  before this feature existed, never a silent misrouted request, since
  `source_language` is validated server-side regardless of how it was
  set.
- **Tier 1** — the detection itself is deterministic, measured script/
  stopword matching, not LLM judgment. What's still Tier 0-flavored is
  the stopword lists themselves: a reasonably common but non-exhaustive
  hand-picked set for each language, not a corpus-derived frequency
  table, so genuinely short or atypical Latin-script lyrics can still
  come back `null` (declined) rather than misidentified — the safer
  failure mode of the two.
- **Benchmark coverage:** manually verified via a standalone Node script
  against one real sample per roster language (Hindi, Urdu, Korean,
  Japanese, Spanish, English) plus two deliberately thin/ambiguous inputs
  expected to decline — all matched. No automated test suite exists for
  the `web/` package yet (no Jest/Vitest configured, `next lint` has
  never been initialized in this repo), so this has real coverage but not
  a coverage the CI can enforce today — a gap worth closing generally,
  not specific to this feature.

## Law 1 (No Invention) is English-only — non-English false positive fix — detail

Found while investigating a real production output (Kun Faya Kun, Hindi →
Japanese) where "Maula" (a specific Sufi/devotional address term) was
shipped as generic "神" (kami, plain "god/deity") with no deviation
logged and no mention in the why-sentence — an apparent unaudited
semantic flattening. Tracing why `engine/verify.py`'s existing Law 1
check hadn't already caught this exposed a much bigger, pre-existing bug:

- **The bug:** Law 1 diffs the Translator's literal anchor against
  `final_line`, word by word (`_changed_final_words`/`_tokens`). The
  anchor is always written in English regardless of `target_language`
  (confirmed: neither `AGENT_BRIEFS["translator"]` nor
  `generation_prompt_v1` ever instruct it otherwise). `_tokens()`'s regex
  IS Unicode-aware (it correctly tokenizes Japanese/Hindi/Korean/Urdu
  text) — but diffing English anchor tokens against non-English final
  tokens finds near-zero overlap by construction, not because nothing was
  preserved. In practice this meant Law 1 flagged virtually the ENTIRE
  final line as an unlogged, unjustified change on every single
  non-English adaptation — a permanent false alarm, not a real signal.
  Confirmed directly: diffing an English anchor against a genuinely
  faithful Japanese line produces a single `('replace', 0, N, 0, M)`
  opcode — 100% "changed," 0% ledger coverage — regardless of quality.
  Because this finding is `severity="error"`, it was also auto-triggering
  `engine/pipeline.py`'s corrective retry (an extra live Judge call) on
  every non-English section, and corrupting `computed_invention_penalty`
  (which is partly derived from this same false-zero coverage) for every
  non-English result's audit trail. This is the "likely out-of-scope"
  gap flagged in this document's history around the completeness-check
  work above, now confirmed as actively harmful rather than merely inert.
- **Fix:** Law 1's word-diff block now only runs when
  `target_language == "English"`. For every other target, it emits one
  `severity="warning"` informational finding instead, explicitly saying
  coverage was not computed for this section and that
  `ledger_coverage`/`computed_invention_penalty` should not be read as a
  real measurement here. The ledger-integrity and tautology checks
  (`fragment_adapted`/`fragment_original` substring containment,
  tautological-justification detection) are untouched and still run for
  every language — they check deviations against the anchor/final text
  directly via substring matching, not cross-script word diffing, so
  they were never affected by this bug.
- **Not yet fixed:** the "Maula" → "神" flattening itself is still a real,
  live quality question (a specific devotional address term rendered as
  a generic word for deity, unlogged) — this fix makes the audit trail
  honest about not being able to check that automatically for non-English
  targets; it doesn't add a new script-agnostic way to catch this class
  of loss. That would need either a bilingual/semantic comparison (not
  simple token diffing) or an LLM-judged check, neither of which exists
  today.
- **Benchmark coverage:** `tests/test_verify.py` adds direct tests: a
  genuinely faithful non-English line no longer gets a false Law 1 error,
  gets exactly one informational warning instead, and the English-target
  path still flags real unaudited invention (guarding against the fix
  swallowing the check it exists to protect).

## Poetic register field: short-label requirement + display fallback — detail

Same production run surfaced a second, unrelated display bug: Song DNA's
`poetic_register` came back as a full descriptive sentence with its own
reasoning ("The song uses a Persianized Urdu register, with vocabulary
choices such as 'maula' and 'rangreza' that suggest a devotional and
emotionally resonant tone.") instead of a short label.
`web/components/LoreStoryline.tsx` interpolates this field verbatim into
a fixed template ("This song moves in a {X} register, and this section
carries a thread of {Y}."), so the sentence-length value produced
garbled, doubled-up prose in the shipped UI.

- **`engine/prompts.py` (`SONG_DNA_SYSTEM`):** now explicitly requires
  `poetic_register` to be a short label (a handful of words, e.g. "sacred
  and devotional," "Persianized Urdu devotional register"), never a full
  sentence or one that explains its own reasoning, and says where that
  reasoning belongs instead (per-section analysis, `songwriter_intention`).
  **Tier 0** — prompt text only; no test corpus confirms the model
  actually complies every time.
- **`web/components/LoreStoryline.tsx` (defensive fallback):** a new
  `isShortLabel()` client-side guard (≤8 words, no sentence punctuation)
  decides which of two already-correct-content templates to render — the
  normal interpolated sentence for a short label, or the value standing
  as its own sentence (its own period, if any, preserved) followed by the
  dominant-feeling clause, if the guard fails. This is belt-and-suspenders
  on top of the prompt fix: even after tightening the instruction, a model
  can still occasionally return a longer value, and the display should
  degrade gracefully rather than mangle it.
- **Benchmark coverage:** `tests/test_golden_prompts.py`'s `song_dna` hash
  updated with a changelog comment. No test suite exists for the `web/`
  package (see the auto-detect section above for the same gap) — `tsc
  --noEmit` and `next build` both pass clean, which is compile-time
  coverage, not behavioral coverage, for the new branch in
  `LoreStoryline.tsx`.

## Call-and-response / setup-and-twist block preservation — detail

Found on the first reggaeton test (Spanish → Hindi, a genre and register
distinct from every real production run tested before this — non-
devotional, urban vernacular, code-switched slang): the source restates
the same setup twice ("Pa' un VIP... Say Cheese... que sonrían las que
ya **les metí**" / "En un VIP... Say Cheese... que sonrían las que ya se
**olvidaron de mí**") — a call-and-response device landing on a
deliberately different final line each time (bravado curdling into "they
forgot about me"). The literal anchor correctly preserved both. The
shipped Hindi line kept only the first occurrence, dropping the second —
and with it the song's actual punchline — with nothing in the
why-sentence disclosing it.

- **Root cause:** the multi-line-block fix above (constraint #7 etc.)
  protects a block the source "restates **verbatim**." A call-and-
  response block is NOT verbatim — it diverges deliberately on its own
  ending — so the instruction as written didn't cover it, and the model
  read the second occurrence as droppable precisely because it wasn't an
  exact repeat.
- **Fix:** constraint #7, the Judge's `artistic_fidelity` dimension text,
  and the Judge's Burden of Change mechanical paragraph all now
  explicitly protect a call-and-response/setup-and-twist block (same
  lead-in restated, a different final line each time) with the same
  burden-of-proof standard as a verbatim repeat — explicitly framed as a
  WORSE loss to drop, not a smaller one, since the contrast between the
  two landings is the device's entire point. Generic across genre and
  language, not scoped to reggaeton or Spanish.
- **Tier 0** — prompt text only; no test corpus confirms this changes
  real output. This is now the third real-production iteration on the
  same underlying class of bug (verbatim single-line → verbatim
  multi-line block → non-verbatim call-and-response block); a fourth
  real song could plausibly surface a fourth variant this instruction
  still doesn't cover (e.g. a repeated block with a varied MIDDLE line
  rather than a varied ending) — worth watching for specifically.
- **Benchmark coverage:** `tests/test_golden_prompts.py`'s
  `creative_adapter`/`judge_triage`/`judge_final` hashes updated with a
  changelog comment.

## Async engine runs: /api/adapt/start + job polling — detail

Every real test in this document so far has been 1-2 sections, because a
full multi-section song was silently impossible to run from the deployed
web app: `web/app/api/adapt/route.ts` sets `maxDuration = 60` with a 55s
client-side abort — Vercel's Hobby-plan ceiling — but `engine/pipeline.py`
`run_engine` processes sections strictly sequentially in one HTTP request,
and each section runs 3-7 of its own sequential LLM calls (Song DNA once,
then per section: Translator, Creative Adapter, Judge triage, up to 3
specialists, Judge final). A 6-8 section song is 20-50+ sequential LLM
calls in a single request — minutes, not seconds — and the token-budget
scaling added earlier in this document (to fix a truncation bug) makes
every individual call slower too, tightening this ceiling further. The
old blocking endpoint made "adapt a whole song" and "keep individual
calls uncut" work against each other.

- **`server/main.py`:** `/api/adapt` is unchanged (still useful for short
  songs, local dev, or anything not bound by a serverless timeout). Its
  validation and actual engine-running logic were extracted into shared
  helpers (`_validate_adapt_request`, `_build_song`, `_run_adaptation`) so
  the new endpoints can't drift from what `/api/adapt` already does.
  `POST /api/adapt/start` runs the same cache/fuzzy-match/quota checks
  synchronously (fast — a cache hit or fuzzy match returns
  `{"status": "done", "result": ...}` immediately, same as before), but
  for a genuine cache miss it starts the actual engine run on a
  `threading.Thread` and returns `{"status": "pending", "job_id": ...}`
  right away. This works without an external job queue because the
  Railway process is a long-lived container, not a serverless function —
  the background thread simply outlives the HTTP request that started
  it. `GET /api/adapt/jobs/{job_id}` is a fast in-memory dict lookup
  returning `{"status": "pending"|"running"|"done"|"error", "result":
  ..., "error": ...}`.
- **Job storage** (`server/jobs.py`): originally an in-memory
  `dict[str, _Job]`, single-instance only. Superseded by the scalability
  pass below — see "Scalability audit" for why and what replaced it
  (Postgres-backed when `DATABASE_URL` is set, in-memory fallback
  otherwise, matching `server/cache.py`'s existing backend-split
  convention).
- **`web/app/api/adapt/start/route.ts`, `web/app/api/adapt/jobs/[jobId]/
  route.ts`** (new): thin proxies, neither needs `/api/adapt/route.ts`'s
  `maxDuration`/`AbortController` handling since both return almost
  instantly regardless of how long the underlying engine run takes.
- **`web/lib/useAdaptSubmit.ts`:** now POSTs to `/api/adapt/start` and, if
  the response is `"pending"`, polls `/api/adapt/jobs/[jobId]` every
  2.5s for up to 10 minutes before giving up with a friendly timeout
  message — the same sessionStorage-stash-then-navigate flow as before
  once a result (cached or job-completed) is in hand.
- **Tier 1** — this is infrastructure, not a model-behavior claim; the
  job lifecycle itself is deterministic and unit-tested
  (`tests/test_server_jobs.py`, mocking `_run_adaptation` so no real LLM
  calls are made). What's NOT yet verified is a real, live full-song run
  end-to-end against the deployed Railway/Vercel pair — that needs the
  user to actually try a multi-section song against the live site.
- **Benchmark coverage:** `tests/test_server_jobs.py` (new, 9 tests):
  cache-hit and fuzzy-match short-circuits create no job; a job
  transitions pending → running → done with the right result; `LLMError`
  becomes the same friendly message `/api/adapt` already used (raw
  exception text never reaches the client); `RuntimeError` is surfaced
  verbatim (a configuration failure, same as `/api/adapt`); a genuinely
  unexpected exception in the background thread still resolves the job
  to `"error"` rather than leaving a poller waiting forever; an unknown
  `job_id` is a 404; input validation matches `/api/adapt`; the quota is
  still enforced. `tsc --noEmit` and `next build` both pass clean for the
  two new frontend routes and `useAdaptSubmit.ts`'s rewrite.

## Scalability audit — detail

A deliberate pass over the whole project (not triggered by a specific
real-song test, unlike almost everything else in this document) asking
"what breaks first under real concurrent load or a growing dataset,"
prompted by the async-job work above having just added a THIRD piece of
in-memory, single-instance state (`_jobs`) alongside an existing one
(`_daily_runs`). Six findings, ranked by actual impact; the first four
are fixed here, the last two are documented, not touched.

1. **In-memory job store (`_jobs`).** Single-process only — a poll
   landing on a different process/instance than the one that started the
   background thread gets a 404 for a job that's still running elsewhere.
   The sharpest of the six, since it's the newest piece of state and the
   one most directly in the way of ever running more than one Railway
   worker.
2. **In-memory daily quota (`_daily_runs`).** Same disease — resets on
   restart, and can't be enforced consistently across more than one
   instance (a burst split across two processes could each independently
   believe they're the day's first request for that IP).
3. **`cache.py::find_similar()`'s full-row over-fetch.** The fuzzy-match
   scan pulled the ENTIRE `result_json` (every section/candidate/ruling
   the song ever computed) into memory for every row matching the
   language pair, just to compare `normalized_text` in a loop — cost
   grows linearly with the whole cached-songs table's size, on every
   single cache-miss request, even though only the eventual winner's
   payload is ever needed.
4. **Unbounded background threads.** Nothing capped how many engine runs
   could be mid-flight at once — a burst of concurrent submissions would
   spawn a thread each and all hit the LLM provider simultaneously,
   risking provider-side rate-limit failures across every concurrent job,
   not just the newest one.
5. **No explicit DB connection pool sizing.** `server/db.py` used
   SQLAlchemy's bare defaults — not wrong, just implicit.
6. **Schema managed by `create_all()` + hand-patched `ALTER TABLE IF NOT
   EXISTS` calls, not a real migration tool.** Already flagged twice in
   `server/db.py`'s own comments as "proving it does not scale past one."
   The largest, riskiest item here — introducing Alembic (or similar)
   is a real infra decision (migration history, rollback story,
   deployment ordering) that deserves its own conversation, not a fixup
   bundled into a broader pass. Documented, not touched.

**Fixes for 1-5:**

- **`server/jobs.py`** (new): same backend split as `server/cache.py` —
  `DATABASE_URL` set → Postgres (`server/db_models.py::AdaptationJob`),
  so job status is visible to whichever process/instance a poll lands
  on; not set (local dev, tests) → an in-memory dict, since there's
  exactly one process and nothing to share state with. `server/main.py`'s
  `_run_job`/`adapt_start`/`adapt_job_status` now call this module
  (`create`/`set_running`/`set_done`/`set_error`/`get`) instead of
  touching a raw dict directly.
- **`server/quota.py`** (new): same split for the daily cap —
  `DATABASE_URL` set → an atomic `INSERT ... ON CONFLICT DO UPDATE ...
  RETURNING count` against `server/db_models.py::DailyQuotaUsage`, so a
  burst of concurrent requests across more than one process can't each
  read the same stale count and both believe they're under the limit (a
  plain SELECT-then-UPDATE can't give that guarantee); not set → an
  in-memory dict, exactly as before this module existed.
- **`server/cache.py::find_similar()`**: rewritten as two passes — fetch
  only `(id, normalized_text)` for the similarity scan, then fetch the
  ONE winning row's full `result_json` only if a match clears the
  threshold. Behavior is unchanged; the DB round-trip's cost no longer
  scales with the size of the whole cache table's payloads.
- **`server/main.py::MAX_CONCURRENT_RUNS`** (new, `CASTIA_MAX_CONCURRENT_
  RUNS` env var, default 4): a `threading.Semaphore` around the actual
  engine run, so at most N background jobs run at once regardless of how
  many `/api/adapt/start` requests arrive simultaneously — the rest
  queue behind the semaphore rather than all hitting the LLM provider at
  once. The number itself is a starting guess, not a measured ceiling.
- **`server/db.py`**: explicit `pool_size`/`max_overflow` (via
  `CASTIA_DB_POOL_SIZE`/`CASTIA_DB_MAX_OVERFLOW`, defaulting to 10/10)
  instead of SQLAlchemy's implicit defaults — documented as bounded by
  whatever Railway's managed Postgres plan actually allows; raising this
  past the plan's real connection ceiling just moves the failure from
  "pool exhausted" to "Postgres refused the connection."

**What this does NOT fix, and why:**

- **The O(n) scan itself is still O(n)** — `find_similar()` is cheaper
  per row now, but still a full Python-side scan over every row in the
  language pair. Fine at today's scale; would need a real similarity
  index (e.g. Postgres `pg_trgm`) if the cached-songs table ever grows
  large enough to make even the lightweight scan slow — `cache.py`'s own
  docstring already flagged this as "worth revisiting," unchanged by
  this pass.
- **No connection reuse across requests in `engine/llm_client.py`** — a
  fresh `openai.OpenAI` client (and its own `httpx` connection pool) was
  constructed on every `create_default_client()` call, i.e. twice per
  adaptation request. FIXED in a follow-up pass (see "Scalability
  follow-through" below): provider SDK clients are now cached and shared
  across wrapper instances.
- **Multi-worker/multi-instance Docker deployment itself** — fixes 1-2
  above remove the state-sharing blocker, but the Dockerfile still runs a
  single `uvicorn` process with no `--workers` flag. Actually turning on
  more than one worker/instance is a deliberate deployment change (cost,
  and needs a smoke test against real Postgres) — this pass makes it
  *safe* to do, it doesn't do it.
- **No edge-level rate limiting or abuse protection** (WAF, IP
  reputation, bot filtering) in front of the API — the per-IP daily quota
  is a cost guard, not abuse protection; this is unrelated to throughput
  scaling and out of scope for this pass.
- **Alembic / real migrations** — see finding 6 above. FIXED in a
  follow-up pass (see "Scalability follow-through" below).

## Scalability follow-through: migrations, connection reuse, web tests — detail

The follow-up pass closing three items the audit above left documented
rather than fixed.

- **Alembic migrations (`server/alembic.ini`, `server/migrations/`)**:
  the schema is no longer managed by bare `create_all()` + hand-patched
  `ALTER TABLE IF NOT EXISTS` (a pattern `server/db.py`'s own comments
  had twice flagged as not scaling past one change). Startup now runs
  `server/db.py::migrate_to_head()` — programmatic
  `alembic upgrade head` — instead of `create_all()`. The baseline
  revision (`0001_baseline`) deliberately delegates to
  `Base.metadata.create_all(checkfirst=True)` so it is safe from BOTH
  starting states with no manual `alembic stamp` step: a fresh database
  gets every table, the already-deployed Railway database gets a no-op
  plus the version row. The tradeoff (a baseline that reads live
  metadata instead of freezing the schema in the file) is stated in the
  revision's docstring, with the rule going forward: every change AFTER
  the baseline must be a real, frozen, reviewed migration
  (`alembic -c server/alembic.ini revision --autogenerate -m "..."`),
  never another metadata delegation. `_patch_known_schema_drift()` still
  runs after migration during the transition (idempotent, now guarded to
  Postgres only). Verified end-to-end against sqlite file databases in
  both starting states — fresh and pre-existing — plus the CLI
  (`alembic current`); NOT yet executed against live Postgres, same
  disclosure as the audit above.
- **Shared provider SDK clients (`engine/llm_client.py`)**: `openai.
  OpenAI`/`anthropic.Anthropic` instances (each owning an httpx
  connection pool) are now cached in a module-level dict keyed by
  everything that changes the constructed client (provider, api key,
  timeout, retries, transport), and shared across `LLMClient` wrapper
  instances — keep-alive connections finally get reused across requests
  and background jobs instead of every request building two fresh pools.
  The wrappers themselves stay per-request: `call_log` is per-instance
  cost accounting and must not be shared. Covered by three new tests in
  `tests/test_llm_client.py` (same config → same SDK client, different
  transport config → different client, different api key → different
  client).
- **First web test harness (`web/vitest.config.mts`, `npm test`)**: the
  web package finally has runnable behavioral tests instead of
  tsc/next-build-only verification. Scope today: pure logic in `lib/` —
  12 tests for `detectLanguage` (every roster script, Latin-script
  English/Spanish disambiguation, and the decline cases including an
  unmapped script). Component tests (jsdom + testing-library) remain
  unbuilt — worth adding when a component regression actually bites.

**Tier 1** — every fix here is deterministic infrastructure, not a
model-behavior claim. **Verification gap, disclosed honestly**: this
sandbox has no live Postgres instance and no `DATABASE_URL`, so the new
DB-backed paths (`AdaptationJob`, `DailyQuotaUsage`, the atomic UPSERT)
are verified by (a) a SQLite schema smoke test
(`tests/test_db_models.py`) confirming the models themselves are sound,
and (b) compiling the UPSERT statement against the real Postgres SQL
dialect to catch syntax errors — but NOT by actually executing it against
a running Postgres. The in-memory fallback paths (what every test in
this session actually ran against, since no `DATABASE_URL` is set here)
are fully exercised by `tests/test_jobs.py` and `tests/test_quota.py`.
Confirming the Postgres path end-to-end needs a real deploy with
`DATABASE_URL` set, which only the user can do from here.

**Benchmark coverage:** `tests/test_jobs.py` (7 tests, in-memory backend:
create/get/status-transitions/errors/pruning), `tests/test_quota.py` (3
tests, in-memory backend: allow-up-to-limit-then-block, independent IPs,
disabled quota), `tests/test_db_models.py` (+4: `AdaptationJob` defaults
and updates, `DailyQuotaUsage` keying), `tests/test_cache.py` (unchanged,
all still passing against the rewritten `find_similar()`). 415 tests
total, all passing.

## Accounts: Auth.js + Google, per-user history — detail

The largest remaining product gap before this: the `User`/`Adaptation`/
`Collection` models had existed since the schema was first written, and
the dashboard had history/favorites/collections pages, but there was no
way to know *whose* history was whose — `server/db.py`'s docstring left
the provider choice (Clerk vs. NextAuth) explicitly open and deliberately
shipped no sessions/tokens table. Resolved in favor of **Auth.js
(NextAuth v5) with Google**, self-hosted, no per-user vendor fee.

- **Identity split (the key design decision).** Auth.js runs with the
  **JWT session strategy and no database adapter**. That matters: an
  adapter would have given Auth.js its own `users`/`accounts`/`sessions`
  tables, duplicating the user store in exactly the way `server/db.py`'s
  docstring warned about ("NextAuth's Postgres adapter expects its own
  exact table shapes"). Instead the session lives entirely in the signed
  JWT cookie, and the Python side (`server/accounts.py`) stays the sole
  owner of user rows. On first sign-in the Auth.js `jwt` callback POSTs
  to the engine's `/api/users/sync`, which upserts the user and returns
  `{id, plan}`; that id is stashed in the token as `castiaUserId` and
  travels with every subsequent request.
- **Trust model (`server/main.py`).** The engine API is a separate
  service on Railway — it never sees the Google sign-in, so it cannot
  verify a user id on its own. `CASTIA_INTERNAL_API_SECRET` is a shared
  secret known only to the Next.js server (the party that *did* verify
  the sign-in). `_authed_user_id()` honors a forwarded `X-Castia-User-Id`
  **only** when paired with the correct `X-Castia-Internal-Secret`;
  otherwise it returns `None` and the request proceeds anonymously.
  A browser calling the engine directly with a forged user-id header
  therefore writes nothing — covered by an explicit test
  (`test_forwarded_user_id_is_ignored_without_the_secret`). The account
  endpoints (`/api/users/sync`, `/api/me/adaptations`) hard-require the
  secret: 401 on mismatch, 503 when unconfigured.
- **History is an enhancement, never a gate.** `_record_history()`
  catches and logs its own failures so a history write can never break
  an adaptation. Anonymous users get identical behavior to before
  accounts existed. Cache hits and fuzzy-match hits also record history
  (the row records "this user asked for this song," not "this user paid
  for the compute"), and one row per (user, result) is deduped —
  resubmitting the same song is a repeat view, not a second entry. The
  `song_key`/`version` columns stay reserved for deliberate reruns after
  engine changes, which nothing exposes yet.
- **Degradation, stated honestly.** No `DATABASE_URL` → `accounts.py`
  returns `None`/`[]` and records nothing, rather than pretending with
  in-memory storage that would fake a durability the feature doesn't
  have. No `AUTH_SECRET`/`AUTH_GOOGLE_ID` → `/sign-in` renders the
  original "accounts aren't live yet" copy plus a deployment note,
  instead of a button that fails at click time. No
  `CASTIA_INTERNAL_API_SECRET` → sign-in still works, history silently
  doesn't record.
- **Frontend:** `web/auth.ts` (config + sync callback),
  `app/api/auth/[...nextauth]/route.ts` (handlers),
  `app/api/me/adaptations/route.ts` (history proxy), `app/sign-in/
  page.tsx` (server component; real Google sign-in / signed-in state /
  sign-out as server actions), `components/RecentAdaptations.tsx`
  (dashboard list, replacing the "once accounts are live" placeholder),
  and identity forwarding in `app/api/adapt/start/route.ts`.
  `components/SiteHeader.tsx` deliberately does NOT branch on session —
  it renders from both server and client trees (`InputScreen.tsx` is
  `"use client"`), so reading the session there needs a broader refactor;
  `/sign-in` shows the signed-in state instead.
- **New env vars** — documented in the new `.env.example` (engine) and
  `web/.env.example` (Next.js), with `.env`/`.env*.local` added to
  `.gitignore` (previously absent, and now carrying real secrets):
  `AUTH_SECRET`, `AUTH_GOOGLE_ID`, `AUTH_GOOGLE_SECRET`,
  `CASTIA_INTERNAL_API_SECRET` (must match on both services).
- **Tier 1** — deterministic application code, no model behavior.
  **Verification gap, disclosed:** `tests/test_accounts.py` (12 tests)
  runs against a real sqlite-file database via `DATABASE_URL`, so the
  actual `accounts.py` DB paths and endpoint gating are genuinely
  exercised — but the **Google OAuth round-trip itself has never been
  executed**, in any environment. It needs real Google credentials and a
  browser, which this sandbox has neither of. `tsc --noEmit` and
  `next build` pass, which proves the wiring compiles and the routes
  register, not that a real sign-in completes.
- **Not built:** billing/Stripe and account deletion — each is its own
  feature on top of this foundation, not part of it. (Favorites and
  collections shipped separately — see below.)

## Favorites — detail

The first feature built on top of accounts. The `is_favorite` column had
existed since the schema was written but nothing ever wrote to it.

- **`server/accounts.py::set_favorite`** — the authorization boundary is
  the query itself: `user_id` is part of the `filter_by`, so a user
  flipping someone else's row is indistinguishable from flipping a row
  that doesn't exist. Both return `False` → 404. There is no separate
  ownership check that could drift from the lookup. Covered by
  `test_one_user_cannot_favorite_another_users_row`, which asserts both
  that B's attempt fails *and* that A's row is untouched.
- **`list_adaptations(favorites_only=...)`** filters in SQL, not by
  trimming the returned list — so `limit` means "50 favorites", not
  "however many of the 50 newest adaptations happened to be starred".
- **`POST /api/me/adaptations/{result_id}/favorite`** (engine) →
  `web/app/api/me/adaptations/[resultId]/favorite/route.ts` (proxy).
  The proxy only proves *who* is asking; it never checks ownership,
  because the engine's query already does.
- **`web/lib/favorites.ts::applyFavorite`** — the optimistic list
  transform, deliberately extracted from the component as a pure
  function so its three real cases are testable without a DOM
  (7 tests): optimistic flip, rollback after a failed write, and
  dropping a row that no longer belongs on the Favorites page. That last
  case only fires *after* the write succeeds — a failed unstar leaves
  the row visible to retry rather than vanishing on a write that never
  landed.
- **`components/RecentAdaptations.tsx`** gained the star and a
  `favoritesOnly` prop, so the dashboard's history list and the
  Favorites page are one component rather than two that can drift.
  `app/dashboard/favorites/page.tsx` is no longer a `DashboardStub`.
- **`components/DashboardSidebar.tsx`** now tracks a `LIVE_SECTIONS` set
  instead of tagging every non-active row "Soon" — that badge was
  becoming a lie as features land one at a time, and this keeps it
  truthful without needing to remember to edit the component's JSX each
  time.
- **Tier 1**, same verification gap as accounts: 7 new backend tests run
  against a real sqlite-file `DATABASE_URL` and 7 new frontend tests
  cover the list transform, but **no favorite has ever been toggled
  through a browser** — that needs the Google OAuth round-trip, which
  still has never been executed anywhere.

## Collections — detail

Grouping adaptations by artist/language/mood. The `Collection` and
`CollectionAdaptation` models had existed since the schema was written
with nothing reading or writing them.

- **The two-sided ownership check is the real difference from
  favorites.** Favorites had one object to authorize; a membership write
  joins *two*, and each must independently belong to the caller.
  `set_collection_membership` does two `user_id`-scoped lookups (the
  collection, then the adaptation) and returns `False` unless both hit.
  Checking only the collection would let someone file **another user's
  adaptation** into their own collection; checking only the adaptation
  would let them file **their own adaptation into someone else's**
  collection. Both directions are tested by name
  (`test_cannot_file_another_users_adaptation_into_your_collection`,
  `test_cannot_file_your_adaptation_into_another_users_collection`) —
  a single-sided check would pass one and fail the other, which is
  exactly why both exist.
- **`list_adaptations(collection_id=...)`** joins through `Collection`
  with a redundant `Collection.user_id == uid` filter. Redundant for
  well-formed data (the `Adaptation.user_id` filter already constrains
  it), deliberate anyway: it's what makes "someone else's collection id"
  return empty *independent of* that other filter, rather than relying
  on two constraints happening to agree.
- **Deletion keeps the adaptations.** A collection is a grouping, not
  ownership — `delete_collection` removes the join rows explicitly
  (rather than trusting the relationship cascade, since orphaned join
  rows are the silent failure) and never touches `adaptations`. Tested
  both ways: the song survives, the join row doesn't.
- **Membership writes are idempotent.** Adding something already in, or
  removing something that never was, both succeed — the caller asked for
  a state and that state holds. This keeps an optimistic UI that
  double-fires from surfacing a spurious error.
- **Endpoints:** `GET/POST /api/me/collections`,
  `PATCH/DELETE /api/me/collections/{id}`,
  `POST /api/me/collections/{id}/adaptations/{result_id}`, plus
  `?collection_id=` on the adaptations listing. A malformed
  (non-UUID) collection id renders as the same 404 a valid-but-not-yours
  id gets, so probing with garbage reveals nothing that probing with a
  well-formed guess wouldn't.
- **`web/lib/engineFetch.ts`** (new): the `/api/me/*` proxy routes had
  the same seven lines of session/secret/forward/handle-error three
  times over; extracted once collections would have made it six.
  `/api/me/adaptations` deliberately stays the exception — it answers
  `200` with `signedIn:false` for anonymous visitors instead of `401`,
  because the dashboard renders a sign-in prompt from that response.
- **`web/lib/collections.ts`** — pure list transforms (rename, remove,
  prepend, `adjustCount`), tested without a DOM like `lib/favorites.ts`.
  `adjustCount` clamps at zero: an optimistic membership toggle that
  drove a count negative would be rendering a confident lie about state
  we only think we know.
- **`components/CollectionsManager.tsx`** — list/create/rename/delete
  plus a detail view with an "add from your history" picker. Creation is
  deliberately **not** optimistic (the id comes from the server, and a
  placeholder id would make that row's own rename/delete buttons target
  something nonexistent); everything else is, with rollback.
- **Tier 1**, same verification gap as accounts and favorites: 13 new
  backend tests against a real sqlite-file `DATABASE_URL`, 12 new
  frontend tests for the transforms — but **no collection has ever been
  created through a browser**, since the whole surface sits behind a
  Google sign-in that has still never been executed anywhere.
- **Filing from the history list** (closing the gap this section
  originally shipped with — previously a song could only be filed from
  inside a collection's detail view, so the flow was "go to the
  collection, then add" rather than the natural "see a song, file it"):
  every row in `RecentAdaptations` now has an "Add to…" menu listing the
  user's collections with checkmarks.
  - `list_adaptations` carries `collectionIds` per entry, so the menu
    opens already knowing its own state. That's **one extra grouped
    query for the whole page**, not one per row — the N+1 this would
    otherwise obviously be. No `user_id` filter is needed on that query
    (and none is applied): the adaptation ids feeding it came out of a
    query already scoped to the user, so any join row pointing at one is
    necessarily theirs. `test_membership_ids_do_not_leak_across_users`
    pins that reasoning with two users who adapted the same song.
  - `lib/collections.ts::applyMembership` is the pure transform, deduped
    on add so a double-click can't produce a duplicate id that would
    then need two removes to clear.
  - The menu is hidden entirely when the user has no collections, rather
    than opening onto an empty list with nothing to do.
  - `HistoryEntry` moved to its own `lib/history.ts` — it had outgrown
    living inside `lib/favorites.ts` once collections and the component
    all needed it.
- **Filing (and starring) from the result page** (`components/
  SaveControls.tsx`, in `ResultScreen`'s header) — the surface where
  someone actually decides a song is worth keeping. This one is not
  simply the history list's menu moved: the result page can show a song
  the viewer **has no history row for at all** (someone else's shared
  `/s/<id>` link, or their own from before they signed in), and both
  favorites and collections hang off that row.
  - **`accounts.save_adaptation`** creates the missing row on demand.
    It requires the result to exist in `cached_results`, so it can't be
    used to fill the history table with rows pointing at ids that were
    never computed (`test_cannot_save_a_result_that_was_never_computed`).
    Idempotent.
  - **The save fires on ACTION, never on page view.** Opening a link
    someone sent you is not a decision to keep it — auto-saving every
    viewed share link would quietly turn "history" into "browsing
    history" and make the dashboard useless. Starring or filing is the
    intent signal.
  - **`accounts.get_adaptation`** returns one entry's save state so the
    controls render correctly on load. It and `list_adaptations` now
    share `_entry_dict`, so the two can't drift into disagreeing about
    what a history entry looks like.
  - **Renders nothing when signed out or unconfigured.** An inert star
    on a public share page is worse than no star. Same reasoning excludes
    `/s/demo`, whose result isn't a real cached adaptation — a star that
    always fails and flips back would be worse than its absence.
- **Creating a collection from inside the menu**
  (`components/CollectionMenu.tsx`) — extracted as a shared component
  once the popover was about to be a third near-identical copy of the
  same markup (history list, result page).
  - **Fixes a real first-use dead end.** Both menus previously hid
    themselves when the user had no collections — which is exactly the
    moment they most need to make one. A new user could not discover
    collections from the surfaces where filing actually happens; they
    had to already know to visit `/dashboard/collections`. The menu now
    always renders, with "＋ New collection" in it.
  - **Creating files the song immediately.** The reason to create a
    collection at that moment is the song in front of you, so making
    the user create it and then click it again would be pure busywork.
    On the result page this chains correctly through `ensureSaved`, so
    creating a collection from someone else's shared link saves the
    song, creates the collection, and files it in one action.
  - A failed create keeps the typed name and the form open with an
    inline error, rather than silently discarding what was written.
- **Still not built:** renaming or deleting a collection from these
  menus (that stays on `/dashboard/collections`, where there's room for
  a confirm step), and any notion of sharing a collection.

## Homepage/marketing: removed the single-culture showcase — detail

The homepage's first impression (a showcase card rendered directly below
the input form, unprompted) was a real, honestly-labeled production run
— but it happened to be the ONLY comparison entry that has ever been
generated (`lib/comparison-data.ts`), and that entry is a Hindi/Punjabi
song shown in Devanagari script. With no second example to balance it,
the homepage's actual visual identity was "a Hindi-lyrics tool," which
is the opposite of what a six-language, any-direction tool should
communicate.

- **Root cause, stated plainly:** this isn't a copy problem, it's a
  single-data-point problem. `comparison-data.ts`'s own docstring
  requires every entry to be a real benchmark run
  (`benchmark/cli.py run --corpus examples`), never hand-typed — so
  fabricating a second example in, say, Korean or Spanish to "balance"
  the homepage would violate the same non-fabrication discipline this
  entire project has enforced from the start. The honest fix available
  without running the engine (no API keys/network in this sandbox) is
  to stop giving the one real example outsized, unprompted weight, not
  to invent a fake second one.
- **`components/InputScreen.tsx`:** the showcase card is replaced with a
  language-matrix strip (every entry in `LANGUAGES`, rendered as plain
  chips) plus a link to `/compare`, which still hosts the one real
  example — clearly labeled there, not surfaced as the homepage's
  identity. Nothing is asserted about output quality in the new strip;
  it states supported languages only, which is verifiably true from
  `engine/models.py::SUPPORTED_LANGUAGES`.
- **`lib/languages.ts`:** `LANGUAGES` reordered alphabetically after
  English (was Hindi-first, arbitrarily). An arbitrary non-alphabetical
  order reads as a ranking; alphabetical asserts nothing about any
  language's priority. `sourceHintFor`'s copy follows the same order.
- **`app/compare/page.tsx`:** added one explicit line naming the full
  supported roster, so the single Hindi/Punjabi entry reads as "the one
  benchmark run completed so far," not as the scope of the tool.
- **Left alone, deliberately:** `/s/demo` (`lib/demo-data.ts`) is also a
  real captured Hindi example, but it's reached only by an explicit
  click ("See an example first"), and its default view shows the
  English *adapted* output — the Devanagari original is behind a
  "Show original" toggle, off by default. Low signal, and replacing it
  would have the same fabrication problem as the homepage card did.
- **Tier 1** — this is presentation/copy, not a model-behavior claim.
  No new tests needed (nothing here is logic); verified via `tsc`/
  `next build` (both clean) and a manual read of the rendered strip's
  copy against `engine/models.py::SUPPORTED_LANGUAGES` for accuracy.
- **What this does NOT fix:** the project still has exactly one
  fully-benchmarked comparison example, in one language pair. The
  underlying gap — no Korean, Spanish, Japanese, or Urdu example has
  ever been run through `benchmark/cli.py` — is unchanged; this only
  stops that gap from reading as a design decision on the homepage.
  Closing it for real needs `OPENAI_API_KEY` and the benchmark CLI run
  against real songs in those languages, which is real future work, not
  something this pass could responsibly simulate.

## Demo page framing: mechanism, not a taste statement — detail

Follow-up to the homepage fix above, on a related but distinct problem:
even after removing the unprompted homepage showcase, the one link that
DOES lead to a real example (`/s/demo`) still shows a specific romantic
Bollywood ballad with no framing at all — a visitor who isn't drawn to
that kind of song reasonably reads it as "this is the kind of song this
tool is for," when what it actually is is the only fully-captured
production run in the project (`lib/demo-data.ts`), shown because it's
real, not because it's representative of any genre, mood, or language.

Same constraint as before: replacing the song isn't available without
fabricating one (a different genre/language demo would need a full
literal/adapted/why/deviations capture this sandbox has no API access to
generate), so the fix is framing, not content.

- **`components/InputScreen.tsx`:** the homepage link renamed "See an
  example first" → "See how it works" — sets the expectation that
  what's behind it is a mechanism demonstration, not a taste preview.
- **`components/ResultScreen.tsx`:** a one-line banner shown only when
  `result.id === "demo"` (`demoResult.id` is exactly `"demo"`, confirmed
  against `lib/demo-data.ts`), stating plainly that this is one real
  example illustrating how the engine works, with a link back to `/#
  lyrics` to try any song. Never shown for a real user's own result —
  only for this specific hardcoded id.
- **Tier 1** — presentation only, no logic changed. Verified via `tsc`/
  `next build` (clean) and confirming the id match by reading
  `lib/demo-data.ts` directly rather than assuming it.
- **Still open:** the actual content gap is unchanged — there is still
  no real example in any genre other than a Hindi romantic ballad, or in
  any language other than Hindi. This framing keeps that gap from being
  silently read as a design choice; it doesn't close it. Closing it for
  real means running the benchmark CLI against real songs spanning more
  genres and languages, which needs API access this sandbox doesn't have.

## Removed the /compare page, added a Use Cases section — detail

A structural follow-up to the two homepage-framing fixes above, prompted
by a direct suggestion: replace the single-example proof page with a
features/use-cases section, and remove `/compare` entirely rather than
keep reframing around its one example.

- **Why this is a better fix than the previous two, not just a
  different one:** every earlier fix in this area (removing the
  homepage showcase, reordering languages, framing the demo page) was
  still built around the fact that the project has exactly one real
  benchmark example, in one language. A use-case section sidesteps that
  constraint entirely — "here is who this is for and what it's for" is a
  claim that doesn't depend on which language or genre a real example
  happens to be in, unlike "here is output, judge it," which needed
  examples spanning the whole matrix to be honest. Pairing a new
  features section WITH the old `/compare` page would have recreated the
  identical single-example problem this whole pass exists to fix, just
  with an added section next to it — hence removing the page rather than
  keeping both.
- **Removed:** `app/compare/page.tsx`, `components/
  SystemComparisonCard.tsx`, `lib/comparison-data.ts` (the "GATE Google
  Translate / GPT single-prompt / CASTIA" three-way comparison view built
  around the one Hindi/Punjabi benchmark entry). `benchmark/cli.py` and
  `benchmark/README.md` are untouched — the benchmark tooling itself is
  still real and still useful for internal quality checks; it's the
  public-facing page built on top of one of its outputs that's gone.
- **`components/SiteHeader.tsx`:** the "Examples" nav link (→ `/compare`)
  replaced with "Use Cases" (→ `/#features`, an in-page anchor on the
  homepage). The `active` prop's type dropped `"compare"` since nothing
  sets it anymore.
- **`components/InputScreen.tsx`:** a `USE_CASES` section (four cards:
  understanding a song in an unfamiliar language, adapting lyrics for a
  cover/performance, studying a song's craft via the literal/adapted/why
  breakdown, sharing music across a language gap). Each claim is scoped
  to what the product actually does — literal-vs-adapted-vs-why,
  singability, Song DNA's imagery/repetition/arc — not a claim about who
  currently uses it or for what, since no such adoption data exists to
  make that claim honestly.
- **Tier 1** — presentation/copy, no logic. Verified via `tsc --noEmit`
  (after clearing a stale `.next/types` cache that referenced the
  deleted route) and `next build` (confirms `/compare` no longer appears
  in the route list) — both clean.
- **What this does NOT change:** the underlying gap from the last two
  entries is still there — there is still no real benchmark example
  outside one Hindi/Punjabi song. This fix makes that gap irrelevant to
  the homepage's honesty (nothing there depends on an example anymore),
  it doesn't close the gap itself. If a public comparison page is wanted
  again later, it should launch with more than one language's worth of
  real benchmark runs, not the same single entry re-presented.

## "How it works" visual redesign — detail

A direct follow-up on a visual note: the four-card `USE_CASES` grid from
the previous entry was plain, uniform bordered boxes with a heading and
a paragraph — the generic pattern that reads as templated/AI-generated
regardless of what the copy says, and nothing like the image-forward,
asymmetric card layout of the reference shown (a Framer-style marketing
page: large varied-width cards, each mostly a product visual with
minimal text).

- **The constraint that shaped this, same as the last two entries:** the
  reference's cards are real product screenshots. CASTIA has no
  screenshot library, and this sandbox has no way to generate new ones
  that would themselves need to be captured, reviewed, and kept in sync
  with the real UI. The honest substitute is `components/MockWindow.tsx`
  — a small fake app-window frame (traffic-light dots + a label) around
  an ABSTRACT, illustrative diagram of a real mechanism: bars standing
  in for text, pills standing in for language pairs, never real
  screenshots and never invented lyrics. This is a real design pattern
  used across marketing sites specifically because it makes a narrower,
  more honest claim than a screenshot ("this is the shape of the
  mechanism") without asserting "this is literally what the product
  renders pixel-for-pixel," which would need to be kept true over time.
- **Content shown is still constrained to real, verifiable facts,** not
  decoration for its own sake: the language-pair chips (Hindi→Spanish,
  Korean→English, Japanese→Urdu) are real supported pairs, the "why"
  callout text ("the line repeats three times in the source — it
  repeats three times here too") is the actual repetition-preservation
  behavior fixed earlier in this document, not invented copy.
- **Asymmetric grid, not a uniform one** (`sm:col-span-4/2/3/3` across a
  `grid-cols-6` base) — deliberately varied card widths, since a row of
  identically-sized boxes is a large part of what read as templated in
  the first place; varied widths read as designed intent.
- **Renamed the language-chip strip above this section** ("Six
  languages, one engine") to avoid duplicating the new "Any language,
  either direction" feature card's heading — same information, appearing
  once as a quick roster confirmation near the input, once as a fuller
  claim inside the features grid.
- **Tier 1** — presentation only, no logic or copy claims changed beyond
  the rename above. Verified three ways: `tsc --noEmit` and `next build`
  (both clean), and — because this is a purely visual change that static
  checks can't evaluate — an actual rendered screenshot via a local
  `next start` + Playwright/Chromium (both pre-installed in this
  sandbox), confirming the asymmetric layout, the mockup windows, and
  the corrected (non-duplicated) headings all render as intended before
  shipping. This is the first UI-only change in this document verified
  by actually looking at it rather than by build/test output alone.

## /alternate-homepage: a real screenshot pipeline — detail

A second homepage layout (not linked from primary nav — reachable only
by URL), built against a Cartesia-style visual reference: a colored
hero banner with a floating product screenshot, a tabbed feature
showcase, a "trusted by" strip, a flow diagram, and a closing CTA. The
explicit ask this time was to use real screenshots rather than another
round of abstract diagrams — a genuinely different, larger undertaking
than the `MockWindow` approach two entries up, since it means the
images have to come from somewhere real and stay honest as the UI
changes.

- **`web/scripts/capture-screenshots.mjs`** (new): boots a real
  `next start` server on a scratch port, drives it with Playwright
  (Chromium pre-installed in this sandbox), and captures three PNGs into
  `public/screenshots/`: the homepage hero (headline through the paste
  box), the language-chip strip, and one full literal/adapted/why
  comparison card from `/s/demo` — the same real captured example used
  elsewhere in this document, not a new fabrication. Targeted via a
  handful of inert `data-screenshot="..."` attributes added to
  `InputScreen.tsx` and `ComparisonCard.tsx` specifically for this
  script to select reliably, instead of depending on CSS classes that
  change with every redesign.
- **Real maintenance cost, stated plainly, not glossed over:** these
  PNGs are a snapshot. Nothing re-generates them automatically when
  `InputScreen.tsx` or `ComparisonCard.tsx` changes visually — the script
  has to be re-run by hand and the new PNGs committed. This is the same
  kind of drift risk any hand-maintained screenshot library has, and
  it's a real one: it's easy to ship a redesign and forget the
  screenshots on this page now show a stale version of the product.
  Worth wiring into CI (fail if a screenshot's source component changed
  more recently than the image) if this page is kept around, not done
  here.
- **One deliberate exception to "real screenshots only":** the "Keep
  what you find" section (favorites/collections) is a small illustrative
  diagram — star + pills — not a screenshot, for the same reason
  `MockWindow` exists: this script has no way to authenticate, so a real
  screenshot of that feature would show a signed-out prompt, which is
  accurate but communicates nothing about the feature. Diagrammed
  instead of faked.
- **Also honest by omission:** no "trusted by" customer-logo strip (no
  real customers to name) — replaced with a row of verifiable facts
  about the product itself (language count, the logged-change
  discipline, the literal-reading floor). No fabricated research
  citations or hiring banner from the reference, since neither is true
  of this project.
- **`web/components/PipelineDiagram.tsx`** (new): a plain HTML/CSS
  diagram of the real Writers' Room stages (`docs/WRITERS_ROOM_V1.md`) —
  Source → Translator → Creative Adapter → Judge → Verified output.
  There's no UI surface that shows this pipeline directly (it's entirely
  server-side), so a diagram is the accurate way to show it, not a
  screenshot standing in for one.
- **`web/components/UseCaseTabs.tsx`** (new): the one interactive,
  non-static piece — three tabs (Fans / Singers & covers / Language
  learners) that switch a caption under the SAME shared screenshot,
  deliberately not a different image per tab. There is exactly one real
  captured comparison example; pretending each audience gets its own
  visual would recreate the single-example problem the rest of this
  homepage work exists to avoid. What's honest to switch is who a real
  feature is useful for, not which picture illustrates it.
- **Tier 1** — presentation, no logic. Verified the same three ways as
  the previous visual entry: `tsc --noEmit` and `next build` (both
  clean, confirms the route registers), and an actual rendered
  screenshot of the finished page via local `next start` + Playwright —
  not just trusting that the JSX compiles into something that looks
  right.
- **`playwright` added as a devDependency** (`^1.56.1`, browser download
  skipped via `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD` since Chromium is
  already provided) so `scripts/capture-screenshots.mjs` is runnable via
  plain `npm`/`node` rather than depending on a global install outside
  the project.

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

## Main homepage: dropping the "AI wrapper" look — detail

Direct feedback on the real production homepage (`components/InputScreen.tsx`,
not `/alternate-homepage`): the page read as a generic "Silicon Valley AI
Startup" template rather than a tool built for musicians and songwriters,
for four concrete reasons — the color palette, the vocabulary, the card
chrome, and the YouTube-import framing. Addressed each directly rather
than restyling on top of the same structure.

- **Color palette — the highest-leverage change, made systemic rather
  than homepage-local.** `tailwind.config.ts`'s `paper.dark` moved from
  `#0b0b0c` (the same near-black every dark-mode AI tool defaults to) to
  a warm brown-black (`#181310`), and `accent.DEFAULT` moved from
  `#5b5bd6` (indigo/purple — the single most recognizable "AI startup"
  tell named in the feedback) to a terracotta/copper (`#b8562e`). Both
  are Tailwind theme tokens, so every `bg-accent`/`text-accent` and
  `dark:bg-paper-dark` usage site-wide picked up the new colors
  automatically — this was not a one-page patch. Two hardcoded (non-token)
  instances of the old purple would NOT have been caught by that alone
  and were fixed by hand: `ComparisonCard.tsx`'s "CASTIA" pill (dropped a
  `boxShadow` neon-glow effect entirely, not just recolored it — a
  blurred halo is itself part of the visual language being removed), and
  `/alternate-homepage`'s hero gradient (updated for consistency, though
  that page was outside this request's stated scope).
- **Vocabulary — removed the specific machine-centric phrases named in
  the feedback**, all in `InputScreen.tsx`: "Six languages, one engine"
  → "Six languages, any direction" (also let the now-removed redundant
  feature card below be dropped without losing the concept); "Nothing
  shifts without a specific, checkable reason" / "logged with a reason"
  → "with a plain-language note for every place it departs from it — not
  a black-box rewrite you have to take on faith"; "Reviewed before
  anything runs — never piped straight into the engine" → "Paste a link
  and the captions come back as reviewable sections — read them over,
  fix anything, then adapt. Nothing goes out the door unread." Same
  underlying claims (a reason is attached to every real change; YouTube
  captions are reviewed, not auto-run), reworded away from data-pipeline/
  audit-log framing.
- **Card chrome and abstraction, removed rather than restyled.** The
  `MockWindow` macOS-traffic-light frame and the abstract grey/accent bar
  placeholders (the exact two things called out as "AI landing page"
  tropes) are gone from this page's feature cards. `MockWindow.tsx`
  itself is untouched and still used by `/alternate-homepage` (out of
  this request's scope), so it wasn't deleted, just stopped being used
  here. In its place: the "Every real change, with a reason" card now
  shows the real `comparison-card.png` screenshot (already captured for
  `/alternate-homepage`, so no new fabrication), and the redundant "Any
  language, either direction" card was dropped outright — it duplicated
  the language-chip strip already above it, and cutting it also reduces
  the card-count/density that read as a trendy bento grid.
- **Real Dashboard screenshots, per the explicit ask** ("the screenshots
  i wanted on the main homepage were of the dashboard"). Read
  `app/dashboard/page.tsx` in full first to check whether an honest,
  unauthenticated screenshot was even possible: the sidebar, header,
  language pickers, textarea, and submit button all render fully
  regardless of auth state — only the nested `<RecentAdaptations />`
  shows a sign-in prompt, and only for its own section. Two inert
  `data-screenshot` markers were added (`dashboard-workspace` on the
  sidebar+workspace wrapper, `dashboard-recent-boundary` on the Recent
  Adaptations wrapper) so `scripts/capture-screenshots.mjs` can compute a
  `clip` region via `boundingBox()` math that crops out everything from
  Recent Adaptations downward — no fabricated signed-in state, no
  invented UI. The "Keep what you find" feature card now shows this real
  `dashboard-workspace.png` in place of its old illustrative star/pill
  mockup.
- **What this does NOT do:** it does not add real album art or artist
  references, which the feedback also suggested ("real album art or
  artist references"). There is no real album art this project has
  rights to use and no real artist endorsements — inventing either would
  violate the same non-fabrication discipline this whole document is
  built on. The "lean into the music, not the machine" goal from that
  feedback is pursued instead through the warm/organic color change, the
  vocabulary change, and real product screenshots in place of abstract
  UI diagrams.
- **Tier 1** — presentation and copy only, no logic changed. Verified:
  `tsc --noEmit` and `rm -rf .next && next build` (both clean), the full
  suite (`npx vitest run`, 33 tests; `python -m pytest -q`, 460 tests,
  neither touched by this change but re-run to confirm nothing broke),
  and — because color/layout/copy changes are exactly what static checks
  can't judge — a real `next start` + Playwright screenshot of the
  finished homepage, reviewed by looking at it, including one visual bug
  caught and fixed this way: the "Imports straight from YouTube" card
  initially rendered with a large blank area because CSS grid was
  stretching it to match its taller sibling card's height (`items-start`
  added to the grid to fix it).

## /comics: panel-by-panel script workspace scaffold — detail

The first piece of a deliberate second product surface (`CASTIA Comics`,
alongside `CASTIA Music`), on the strategy that both front ends can share
one headless Reasoning Engine and one "literal / adapted / why" value
proposition, just with a different input mechanism and review UI per
medium. Explicitly NOT linked from primary nav or the marketing
homepage — same convention as `/alternate-homepage` — because the
project's non-fabrication discipline means the homepage can't pitch a
Comics workspace with real screenshots until there's a real, working
tool to screenshot. This entry is that tool's functional foundation
only: file upload and a panel-review workspace, no OCR, no comics
Reasoning Engine integration.

- **`app/comics/page.tsx`** (new): page-level state holding the
  uploaded panel list and the stage (upload vs. review) that follows
  from whether it's empty. A banner states outright, in the UI itself,
  that OCR and the adaptation engine aren't wired up yet — the same
  honesty pattern `DashboardStub.tsx` uses for unbuilt dashboard
  sections, applied to a whole new page rather than one sidebar item.
- **`components/comics/PanelUploader.tsx`** (new): drag-and-drop plus
  two file-picker buttons (`Choose files`, `Choose a folder` via the
  non-standard-but-universally-supported `webkitdirectory` attribute).
  **Known limitation, stated in the component's own comment:** a folder
  dropped directly onto the page is not read recursively — browsers
  expose a dropped folder's contents through an async directory-entry
  API, not as plain `File` objects, and that's real additional work not
  done here. Drag-and-drop accepts individual image files; a folder's
  contents come in via the picker button instead. Both paths converge
  on the same `onFilesSelected(File[])` callback.
- **`components/comics/PanelWorkspace.tsx`** (new): the panel-by-panel
  review UI — a thumbnail rail to jump between panels, the active
  panel's real (unmodified) image on one side, and three plain text
  fields on the other (Extracted text / Adapted text / Why). **These
  are user-typed fields, not model output** — there is no OCR run
  against these images and no comics-specific engine endpoint yet, so
  labeling this any other way would be exactly the kind of fabricated
  "processing" state the main-homepage redesign (previous entry) just
  spent an entire pass removing. No bounding-box overlay around
  extracted text either, for the same reason: there's no OCR result to
  draw a box around yet.
- **`lib/naturalSort.ts`** (new) + **`lib/comics-types.ts`** (new):
  chapter-slice files are almost always named as a numeric sequence
  (`panel-2.jpg`, `panel-10.jpg`), which a plain string sort orders
  wrong (`panel-10` before `panel-2`); `naturalCompare` splits each name
  into alternating text/number runs and compares number runs
  numerically. `comics-types.ts` holds the `ComicPanel` shape and a
  `panelsToCsv` helper for the export button — a real, working CSV
  export (panel number, file name, extracted/adapted text, why) built
  from whatever the user has actually typed in, not placeholder data.
- **Images never leave the browser tab.** Each upload becomes a
  `URL.createObjectURL` blob reference held only in page state — there
  is no upload endpoint, no storage, nothing server-side yet. Reloading
  the page loses the session; this is a scaffold, not a persisted
  workspace.
- **Tier 1** — pure frontend scaffolding, no engine logic. Verified:
  `tsc --noEmit` and `next build` (both clean, confirms the route
  registers), new unit tests for `naturalCompare` and `panelsToCsv`
  (5 new tests, 38 total in `npx vitest run`, up from 33), the existing
  460-test Python suite re-run to confirm this frontend-only change
  didn't touch it, and a real `next start` + Playwright run that
  actually uploaded three deliberately-out-of-order test images and
  confirmed both the visual layout and the natural-sort ordering
  (`panel-1.png` → `panel-2.png` → `panel-10.png`, read back from the
  rendered "Panel 1 of 3 · panel-1.png" header) before calling this
  done.

## /comics OCR integration: real Tesseract, not a stub — detail

The first real backend piece of the Comics workspace, following directly
from the previous entry's scaffold. Chose Tesseract over a hosted OCR API
(Google Vision / AWS Textract / Azure) specifically because it's open
source, deterministic, needs no API key or per-call billing to wire up,
and runs as a plain system binary in the same Docker image the engine
already ships in — no new secret, no new vendor account, no new async
webhook flow, just one `apt-get install`. The tradeoff, stated plainly:
Tesseract is trained on printed/scanned prose, not stylized comic
lettering, so accuracy on real chapter art will often be worse than a
purpose-built comics-OCR API would give. That tradeoff is worth it for a
scaffold; revisit if real usage shows Tesseract's accuracy is the actual
bottleneck.

- **`engine/comics_ocr.py`** (new): `extract_text_regions(image_bytes,
  language)` decodes the image with Pillow, runs
  `pytesseract.image_to_data`, and groups Tesseract's per-word output by
  `(block_num, par_num)` into regions — in practice usually one region
  per speech bubble or caption box, since that's what Tesseract's own
  page-segmentation already separated. Each region carries a pixel-space
  bounding box and an averaged per-word confidence. `OcrError` is raised
  (never a fabricated/placeholder result) when pytesseract isn't
  installed, the image can't be decoded, or Tesseract itself fails.
- **Two limitations disclosed in both the module docstring and the
  actual API response, not just code comments:** (1) only English OCR
  data (`tesseract-ocr-eng`) is installed — requesting `language="Hindi"`
  etc. raises `OcrError` naming exactly which system package is missing,
  rather than silently falling back to English; the other five
  languages' data packages are a real, scoped follow-up, not done here.
  (2) When at least half of a panel's detected regions score below a
  60/100 Tesseract confidence — routine for stylized lettering — the
  response includes a `warning` string the frontend surfaces verbatim,
  the same "tell the human plainly" discipline `engine/youtube_ingest.py`
  established for auto-generated captions.
- **`server/main.py`'s `POST /api/comics/ocr`** (new): a plain `def`
  (not `async def`) FastAPI route taking a multipart image + language
  field, reading the upload via `image.file.read()` rather than
  `UploadFile`'s async `.read()` specifically so it runs in FastAPI's
  threadpool like every other endpoint here and needs no new
  pytest-asyncio dependency just to unit-test. A 15MB size cap
  (`CASTIA_MAX_IMAGE_BYTES`) rejects anything clearly wrong before it ever
  reaches Tesseract.
- **`web/app/api/comics/ocr/route.ts`** (new): proxies to the above,
  same shape as `app/api/youtube-draft/route.ts` — re-packages the
  incoming multipart form into a fresh one for the upstream `fetch`
  rather than piping the raw request body, with the same
  timeout/abort/error-shape handling as every other engine-proxy route.
- **Frontend wiring:** `lib/comicsOcr.ts`'s `runPanelOcr` posts the
  panel's real `File` (now kept on `ComicPanel` itself, not just its
  blob preview URL) to that route.
  `components/comics/PanelWorkspace.tsx` gained a "Run OCR" button, a
  bounding-box overlay drawn in percentage coordinates (region pixel /
  the image's own natural size, captured via the `<img>`'s `onLoad`) so
  boxes stay aligned regardless of the image's rendered width, and
  surfaces the OCR warning/error text directly. **OCR only ever
  pre-fills the "Extracted text" field when it's empty** — it never
  overwrites text a human has already reviewed or typed, the same
  never-overwrite-a-human-edit discipline as
  `InputScreen.tsx`'s YouTube-draft handling.
- **Dockerfile**: added `apt-get install tesseract-ocr` (pulling in
  `tesseract-ocr-eng` as its own dependency) before the pip install
  step, plus `python-multipart`/`Pillow`/`pytesseract` added to
  `requirements.txt` — this is a real new system dependency for
  production, not just a local sandbox convenience, called out here so
  it isn't missed on the next deploy.
- **Tier 1** — real deterministic OCR, but explicitly imperfect on the
  actual target content (comic lettering), which is why every result
  carries its own confidence and warning rather than presenting as
  ground truth. Verified: 6 new `tests/test_comics_ocr.py` tests
  (region-grouping logic against synthetic Tesseract-shaped data, plus
  one real end-to-end Tesseract run against a generated test image,
  skipped only if `tesseract` isn't on PATH) and 3 new
  `tests/test_server.py` tests for the endpoint (469 Python tests
  total, up from 460), `tsc --noEmit`/`next build` clean, and a real
  three-process manual run (uvicorn + `next start` + Playwright) that
  uploaded a synthetic two-speech-bubble test panel, clicked "Run OCR,"
  and confirmed a real Tesseract result came back: one bubble's text
  correctly extracted and boxed, the other bubble missed entirely by
  Tesseract on this synthetic font, and the low-confidence warning
  correctly shown — a genuinely imperfect but genuinely real result,
  not a mocked success path.

## Deterministic repeated-line-preservation check — detail

User-reported: shipped songs sometimes skip lines that repeat in the
source. This is the same failure class as the "Multi-line repeated block
(couplet/verse/stanza) preservation" and "Translator literal anchor:
repetition preservation" entries above — both of those fixes were
**prompt text only** (Tier 0), explicitly disclosed at the time as having
"no deterministic check confirms a shipped anchor actually preserved
every repeat." This closes that specific gap with a real, code-level
check rather than another prompt tweak.

- **`engine/verify.py::_check_repeated_line_preservation`** (new): counts
  verbatim-duplicate lines in the literal anchor (`Counter` over
  normalized lines). If the anchor has at least
  `MIN_REPEATED_LINES_FOR_CHECK` (2) extra repeated occurrences beyond
  each line's first, and the shipped section's line count is at or below
  the anchor's DEDUPLICATED line count, that's flagged as an
  `error`-severity finding under a new law tag ("Law 3 — Compression
  Floor (repetition)"). Because it's `severity="error"`, it automatically
  feeds `engine/pipeline.py`'s existing corrective-retry mechanism
  (`section.errors` -> `retry_section_with_finding`) — no new pipeline
  wiring needed, same as the completeness check two entries up.
- **Deliberately does NOT try to match wording between anchor and final.**
  CASTIA adapts, not translates — recurrence.py's own docstring states the
  whole point of a source-side refrain is that it "earns a differently-
  worded English line each time." Matching exact repeated wording in the
  shipped text would false-positive on every legitimately-reworded
  repeat. Instead this checks a cruder but reliable structural proxy:
  a "drop every repeat, ship the gist once" rewrite can only ever produce
  at most as many lines as the anchor's distinct (deduplicated) line
  count — so a shipped line count at or below that number is diagnostic
  of the failure regardless of what words were actually used.
  `MIN_REPEATED_LINES_FOR_CHECK = 2` (not 1) keeps a single incidental
  duplicate short line — two unrelated lines that happen to read
  identically, not a deliberate refrain/couplet device — from
  manufacturing a requirement the anchor's repetition doesn't clearly
  establish; that borderline case is left to the existing, coarser
  `LINE_COLLAPSE_RATIO` check.
- **What this does NOT fix, stated plainly, same discipline as every
  other entry here:** `retry_section_with_finding` only re-runs the
  Judge against the Creative Adapter's EXISTING candidates — it does not
  regenerate them. If every one of the 5 candidates already dropped the
  repeat (the Creative Adapter itself collapsed it, not just the Judge's
  final pick), re-judging among already-flawed candidates cannot recover
  the missing repeat; this check will still catch and report the failure
  in that case, but the automatic corrective pass won't fix it, and it
  will surface in production logs as an unresolved verify warning the
  same way any other post-retry residual error does. Also unchanged: no
  test corpus confirms this changes real deployed output beyond what the
  unit tests below establish — that requires the user resubmitting real
  songs, same caveat as every fix in this document.
- **Tier 1** — the check itself is deterministic string/count logic, not
  LLM judgment; whether it actually catches every real instance of this
  failure in production, and whether the corrective retry actually fixes
  what it catches, isn't something a unit test can confirm.
- **Benchmark coverage:** 3 new `tests/test_verify.py` tests — a
  repeated couplet shipped once is flagged; the same couplet shipped
  twice with DIFFERENT wording each time (a legitimate adaptation) is
  not flagged; a single incidental repeated line below the threshold is
  not flagged. 472 Python tests total, up from 469.

## Resolving the retry limitation: a computed prompt hint + a real regeneration escalation — detail

Direct follow-up closing the gap the previous entry disclosed but didn't
fix: `retry_section_with_finding` only ever re-judges the EXISTING
candidate pool, so if every one of the 5 Creative Adapter candidates
already dropped a repeat, no amount of re-judging can recover it. Two
changes, one preventative and one corrective.

- **Preventative — `engine/prompts.py::_repeated_source_lines_note`
  (new):** rather than trusting the Creative Adapter to notice AND
  count a source repeat while also holding constraint #7's abstract
  rule in mind, this computes the exact count deterministically (a
  `Counter` over the source's own lines) and hands it to
  `creative_adapter_prompt` as a concrete fact — e.g. `'hold me now'
  appears 2 times` — appended to the user prompt. Returns `""` (no
  change at all) when the source has no verbatim-repeated line, which
  is why `tests/test_golden_prompts.py`'s `creative_adapter` hash did
  NOT need updating: its fixture source is a single line with nothing
  to repeat, so the prompt stays byte-identical for that case — a
  concrete instance of the note's design goal, not just a claim about
  it. A repeated multi-line couplet reports as two separate per-line
  counts (one per line of the couplet), since the note doesn't need to
  understand "couplet" as a unit — it just states each line's own
  verbatim count, which is the same granularity
  `verify.py::repeated_lines_preserved` (below) checks on the receiving
  end.
- **Corrective — `engine/pipeline.py`'s regeneration escalation
  (new):** `_apply_corrective_pass` now routes a dropped-repeat finding
  (`Law 3 — Compression Floor (repetition)`) to one of two paths,
  decided by a new `_all_creative_candidates_drop_a_repeat` check: if at
  least one of the section's existing Creative Adapter candidates
  already preserves the repeat, the existing `retry_section_with_finding`
  re-judge is still the right, cheaper fix (the Judge just picked the
  wrong option). Only when EVERY candidate has already dropped it does
  it escalate to `writers_room_v1.regenerate_creative_adapter_candidates`
  — a fresh Creative Adapter generation call (Translator's anchor is
  deliberately NOT re-run; it already preserves repeats correctly) with
  explicit feedback about what was dropped — followed by a full
  re-judge of the new combined pool via the newly-extracted
  `writers_room_v1.judge_candidates` (the triage/specialist/final-ruling
  half of `run_section`, factored out specifically so this new path
  doesn't duplicate that logic). Bounded to exactly one regeneration +
  one re-judge per flagged section, same discipline as the plain
  re-judge path — it does not loop.
- **`engine/verify.py::repeated_lines_preserved`** (new): the Finding-
  producing `_check_repeated_line_preservation` refactored to expose a
  plain boolean underneath, so `pipeline.py` can test individual
  candidates (anchor vs. one candidate's text) BEFORE a Judge ruling
  exists — the Finding-producing version only ever checked the anchor
  against the single already-shipped final line, which is one level too
  coarse for "did ANY candidate preserve this."
- **What this does NOT guarantee, stated plainly:** the prompt hint is
  still Tier 0 (it's a stronger, computed instruction, not a guarantee
  the model follows it) — the regeneration escalation is the actual
  backstop for when it doesn't. And the regeneration escalation is
  itself bounded to one attempt: if the REGENERATED 5 candidates also
  all drop the repeat, this pass ships the Judge's pick from that
  (still-flawed) second pool rather than looping indefinitely — the
  same "surface it, don't infinitely retry" discipline the rest of the
  corrective-pass system uses. No test corpus confirms either change
  moves the needle on real deployed output beyond what the unit tests
  below establish — that requires the user resubmitting real songs,
  same caveat as every fix in this document.
- **Tier 1** for the routing logic and the computed line-repeat counts
  (both deterministic); **Tier 0** for whether the model actually
  produces a better result when prompted with them — no different from
  every other prompt-text mitigation in this document's repetition
  entries.
- **Benchmark coverage:** 6 new `tests/test_prompts.py` tests for
  `_repeated_source_lines_note` (no note without repetition; a repeated
  line reported; a repeated couplet reported as two per-line counts;
  case-insensitive matching; the note appears in/is absent from the
  real `creative_adapter_prompt` output as expected) and 4 new
  `tests/test_pipeline_regeneration.py` tests using a fake LLM client
  that branches on the real `stage=` argument every call site already
  passes (not prompt-text parsing) — confirming the escalation actually
  fires and produces a repeat-preserving final line when every original
  candidate dropped it, confirming the plain flag-off run still ships
  the dropped version uncorrected, and two direct unit tests of
  `_all_creative_candidates_drop_a_repeat`'s two false cases (one
  preserving candidate already exists; no real repetition to escalate
  on). 482 Python tests total, up from 472.

## Switch to Google Cloud Vision — detail

Direct follow-up on real product direction: the target content for
/comics is Japanese manga, Chinese manhua, and Spanish/French indie
comics, on top of CASTIA's existing Hindi/Korean/Urdu roster. The
Tesseract-based scaffold from two entries up made that untenable — it
needs a system-level language pack installed per script AND a language
picked by the user before every OCR run (Tesseract can't reliably guess
script on its own), which is exactly the friction a walk-up-and-use,
international product shouldn't have. Replaced Tesseract with Google
Cloud Vision, which auto-detects script/language per block of text and
needs no per-language setup.

- **`engine/comics_ocr.py`** (rewritten, not just extended): calls
  Cloud Vision's `DOCUMENT_TEXT_DETECTION` feature directly over HTTPS
  with a plain API key (`GOOGLE_CLOUD_VISION_API_KEY`) via `httpx`
  (already a dependency) — deliberately NOT the `google-cloud-vision`
  SDK, which authenticates via a service-account JSON credential file.
  A single env var is a much better fit for how Railway (this engine's
  actual deployment target) manages secrets than shipping/mounting a
  JSON key file would be. `extract_text_regions` keeps the exact same
  return shape as the Tesseract version (`regions`/`full_text`/
  `warning`/`image_width`/`image_height`, each region a `bbox` of
  `{x, y, width, height}` plus a 0-100 `confidence`) specifically so
  `server/main.py`'s endpoint, `web/app/api/comics/ocr/route.ts`, and
  `components/comics/PanelWorkspace.tsx`'s bounding-box overlay needed
  NO changes at all — only the module producing that shape changed.
  Vision's confidence is natively 0-1; scaled ×100 to match the old
  API's percentage scale rather than changing every consumer's
  assumption.
- **`language` is now optional and non-gating everywhere it's
  threaded through** (`server/main.py`'s endpoint, `lib/comicsOcr.ts`,
  the Next.js proxy route) — the whole point of this switch is that
  nobody has to pick one. It survives only as an optional
  `imageContext.languageHints` bias (`_LANGUAGE_HINTS`, CASTIA language
  name -> BCP-47 code) for the rare case a caller already knows the
  language; an unrecognized or absent value sends no hint at all rather
  than raising, unlike the old Tesseract version's `OcrError` on an
  unsupported language.
- **Real cost/dependency tradeoff, stated plainly:** this moves panel
  OCR from a free, local, no-network-dependency binary to a paid,
  metered, external API call — every `/api/comics/ocr` request now
  costs money and requires network egress to `vision.googleapis.com`
  from wherever the engine is deployed. `GOOGLE_CLOUD_VISION_API_KEY`
  unset raises `OcrError` with a clear message (verified: a real manual
  request against a locally-running engine with no key set returned a
  clean HTTP 400 with that exact message, not a crash or a silent
  fallback) — this was NOT a hypothetical checked only by a mock in
  this round.
- **Dockerfile reverted**: the `apt-get install tesseract-ocr
  tesseract-ocr-kor` step from two entries up is gone — Cloud Vision
  needs no system package. `requirements.txt`'s `Pillow`/`pytesseract`
  entries removed likewise (nothing else in the codebase used PIL or
  pytesseract).
- **What this does NOT fix, stated plainly:** Cloud Vision is trained
  on general documents and photographed text, not comic lettering
  specifically — stylized fonts, outlined sound-effect text, and
  speech-bubble-curved text can still come back wrong regardless of
  provider; every region still carries its own confidence and a
  low-confidence warning for exactly this reason, unchanged from the
  Tesseract version. Reading order is still a plain top-to-bottom,
  left-to-right sort of detected blocks, not a real reading-order guess
  (right-to-left scripts, Z-pattern multi-bubble panels). No test
  corpus confirms real accuracy on actual manga/manhua/webtoon art —
  every test in this entry mocks the Cloud Vision HTTP response rather
  than calling the real API, since no `GOOGLE_CLOUD_VISION_API_KEY`
  exists in this sandbox; that first real call is the user's to make
  once the key is configured on the actual deployment.
- **Tier 1** for the request/response parsing and routing logic (all
  deterministic); the OCR ACCURACY itself is an external vendor's
  black box, same epistemic status any third-party API call has in
  this document — measured by its own returned confidence, not
  independently verified against ground truth here.
- **Benchmark coverage:** `tests/test_comics_ocr.py` rewritten from
  scratch (12 tests, up from 6) — `_block_text`/`_bounding_box` unit
  tests against synthetic Vision-shaped block dicts, a missing-API-key
  test, a full successful-parse test (confidence scaling, bbox
  collapsing, multi-block text joining), a majority-low-confidence
  warning test, a no-text-detected test, an HTTP-error-status test, a
  Vision-reported-error test, and two language-hint tests (a known
  language sends the hint, an unknown/absent one sends none) — all via
  a monkeypatched `httpx.post`, no real network call. 488 Python tests
  total, up from 482.

## Cloud Vision auth: API key → service account — detail

Direct follow-up, before the API-key version above was ever deployed
with a real key: switched auth from a plain API key to a GCP service-
account credential, on explicit request. A service account is the more
auditable, more scopeable, more rotatable pattern for server-to-server
GCP auth — a leaked API key is usable by anyone until manually revoked;
a service account's credential can be scoped to exactly one API surface
and rotated/disabled from IAM without touching anything else. The
tradeoff is real setup cost, disclosed to the user directly: a GCP
project, billing, the Vision API enabled, a service account with a
role attached, and a JSON key generated and delivered to this
deployment — vs. one string for the API-key version.

- **`engine/comics_ocr.py::_access_token`** (new): reads
  `GOOGLE_CLOUD_VISION_CREDENTIALS_JSON` (base64-encoded service-account
  JSON — Railway env vars are single-line strings, not files, so the
  downloaded key can't be mounted directly), decodes and parses it,
  builds a `google.oauth2.service_account.Credentials` scoped to
  `cloud-vision`, and calls `.refresh()` to exchange it for a real
  OAuth access token used as an `Authorization: Bearer` header on the
  Vision request — replacing the previous version's `?key=` query
  parameter entirely. Uses `google-auth` directly (new dependency,
  `requirements.txt`) rather than the full `google-cloud-vision` SDK,
  since the actual Vision call still goes through `httpx` exactly as
  before — only the auth step needed a real library, not the request
  itself.
- **Deliberately NOT cached across calls**, stated plainly as a real
  cost rather than glossed over: every OCR request now does a full
  OAuth token-exchange round-trip to Google in addition to the Vision
  API call itself, because a cached token needs a thread-safe refresh-
  before-expiry mechanism to stay correct under concurrent requests —
  real complexity not worth taking on for this scaffold's request
  volume yet. A legitimate follow-up optimization if/when panel volume
  makes the extra round-trip's latency worth removing.
- **Every failure mode raises `OcrError` with a specific, actionable
  message** rather than a generic auth failure: the env var missing,
  the value not valid base64, the decoded value not valid JSON, and
  the JSON not resembling a real service-account key (missing
  `private_key`/`client_email`/`token_uri`) are all distinguished.
  Verified end-to-end, not just unit-tested: a real manual request
  against a locally-running engine with the env var unset returned a
  clean HTTP 400 naming exactly `GOOGLE_CLOUD_VISION_CREDENTIALS_JSON`
  as the missing piece, not a stack trace.
- **A real, disclosed environment quirk hit while developing this**
  (not a code bug, a sandbox dependency-resolution issue): this
  sandbox's system-installed `cryptography` package (Debian-packaged)
  was missing its `cffi` binding, which crashed on
  `from google.oauth2 import service_account` with an unrelated-looking
  Rust panic (`pyo3_runtime.PanicException`, `No module named
  '_cffi_backend'`) rather than a normal ImportError. Fixed locally by
  installing `cffi`/`cryptography` via pip. `requirements.txt`'s
  `cryptography` (pulled in transitively by `google-auth`) should
  install cleanly in a fresh container (this engine's actual Railway
  deployment target, per the Dockerfile) since there's no competing
  system package there to conflict with — flagged here in case the
  same class of error ever surfaces in another environment.
- **What GCP console setup this needs, not automatable from here**: a
  project with billing enabled, the Cloud Vision API turned on, a
  service account, and a JSON key generated and base64-encoded into
  Railway's env vars. No tool in this session can create GCP resources
  or trigger a Railway deploy — both remain the user's to do.
- **Tier 1** for the credential-parsing/token-exchange logic itself
  (deterministic given a real key); **Tier 0** in the sense that no
  real OAuth exchange or real Vision call has been exercised in this
  sandbox — every test here mocks `google.oauth2.service_account.
  Credentials` and `httpx.post` rather than performing a real exchange,
  since no real service-account key exists in this environment. That
  first real end-to-end call is still the user's to make once the key
  is live on the actual deployment.
- **Benchmark coverage:** `tests/test_comics_ocr.py` grew to 17 tests
  (up from 12) — the 12 request/response-parsing tests now stub
  `_access_token` directly (a fake token string) rather than an API
  key env var, plus 5 new tests dedicated to `_access_token` itself:
  missing env var, non-base64 value, base64-but-not-JSON value, a
  structurally invalid service-account dict, and a valid path returning
  the refreshed token (mocking `Credentials.from_service_account_info`,
  not a real signed JWT/OAuth exchange). 493 Python tests total, up
  from 488.

## Comics: bubble reading-order fix — detail

First real end-to-end confirmation that OCR works: the user ran a real
manhwa (Korean webtoon) speech-bubble panel through the deployed engine
and Cloud Vision correctly read the dialogue, word-for-word, including
proper handling of a real-world artifact (Korean's agglutinative
grammar inserting extra spaces between a noun and its particle -
`공주님 을` instead of `공주님을` - flagged as a known, cosmetic OCR
quirk, not a content error, left as-is for the human review step to
absorb rather than adding an unrequested cleanup pass).

That success surfaced the next real gap, scoped directly out of it: to
wire panels into the actual Reasoning Engine (Song DNA -> Translator ->
Creative Adapter -> Judge, reusing the existing Writers' Room machinery
with a new "Chapter DNA" equivalent providing chapter-level context),
bubble reading order has to be correct FIRST — Cloud Vision returns
detected regions sorted by plain top-to-bottom/left-to-right position
(engine/comics_ocr.py's own docstring already disclosed this), which is
wrong for manga's right-to-left reading and not guaranteed correct for
any multi-bubble panel whose real reading order isn't simple geometry.
Nothing existed to let a human fix that before this entry.

- **`components/comics/PanelWorkspace.tsx`**: each detected region's
  bounding-box overlay now carries a numbered badge (reading-order
  position), and a new "Reading order" list below the image shows every
  region's text with ↑/↓ buttons to reorder it — the badges on the
  image and the list stay in sync since both render from the same
  `ocrRegions` array. Only shown when a panel has more than one region
  (a single-bubble panel has no order to fix). An explicit "Apply this
  order to Extracted text" button rewrites the extracted-text field
  from the corrected order — deliberately NOT automatic on every
  reorder, so moving a region around never silently overwrites text a
  human has already started editing; the overwrite only happens on an
  explicit click, the same opt-in-only-when-intentional discipline
  "Run OCR" itself already follows (pre-fills an empty field, never a
  populated one).
- **No backend changes** — this is pure client-side array reordering
  (`ComicPanel.ocrRegions`, already a plain array on existing state);
  nothing new needed from `engine/comics_ocr.py` or the API route.
- **What this does NOT solve yet**: it fixes the ORDER of already-
  detected regions: it does not detect a missed bubble, split a
  wrongly-merged one, or auto-correct anything — a human still has to
  look at the panel and decide the right order. This is also just the
  first item on the scoped chapter-level-context roadmap (see the
  previous conversation turn's scoping breakdown, not yet its own
  document) — Chapter DNA generation, per-character voice/honorific
  tracking, and the actual `/api/comics/adapt` endpoint are still not
  built.
- **Tier 1** — pure UI state manipulation, no LLM judgment involved.
  Verified with a real Playwright run (mocking only the `/api/comics/
  ocr` network response, since no real Vision credential exists in this
  sandbox, to supply two regions in a deliberately wrong order): the
  numbered badges and list started in the wrong order, clicking ↓
  correctly swapped both the list AND the image overlay's badges
  together, and "Apply this order" correctly rewrote Extracted text in
  the corrected order — confirmed by reading the actual rendered
  screenshots and the field's value, not just that the code compiled.
  `tsc --noEmit`/`next build` clean; existing 38-test web suite and
  493-test Python suite both re-run and still green (this change didn't
  touch Python at all).

## Comics: chapter-level source-language capture — detail

Item #2 of the chapter-level-context roadmap scoped out after the
bubble reading-order fix above: capturing what language a chapter is
actually in, which the eventual `/api/comics/adapt` call will need to
run the Translator correctly, and which the old Tesseract setup had no
way to provide at all (a human had to pick a language before every
single OCR run; see the "Switch to Google Cloud Vision" entry).

- **`engine/comics_ocr.py::_detected_languages`** (new): reads Vision's
  own page-level script/language detection
  (`page.property.detectedLanguages`), sorted most-confident first, and
  adds a `detected_languages` field to `extract_text_regions`'s return
  shape: `[{"language_code", "language_name", "confidence"}]`.
  `language_name` uses a new `_LANGUAGE_NAMES` map — deliberately
  broader than CASTIA's current 6-language roster (adds French, Chinese
  Simplified/Traditional) since real target content for /comics
  includes languages CASTIA doesn't adapt yet; an unrecognized BCP-47 code
  is still reported (as `language_name: null`) rather than hidden, so a
  human reviewing a chapter isn't told nothing just because there's no
  engine profile for what Vision found.
- **`lib/chapterLanguage.ts::guessChapterLanguage`** (new): a plain
  majority vote over every OCR'd panel's own top-detected language —
  deliberately not a real chapter-level analysis. A chapter genuinely
  mixing two languages (a loanword-heavy line, a bilingual gag) still
  only ever reports one winner; stated as a known limitation, not
  hidden. Returns `null` when no panel has been OCR'd yet — never
  fabricates a guess from zero evidence.
- **`app/comics/page.tsx`**: shows the guessed language as a small
  badge next to the panel count ("Detected language: Korean (2 of 3
  OCR'd panels)") — the singular-panel case omits the fraction
  ("Detected language: Korean") since "1 of 1" adds nothing. Every
  panel's `detectedLanguages` is stored on `ComicPanel` from its own
  `runPanelOcr` call; the aggregation itself is pure derived state
  (`guessChapterLanguage(panels)`), not stored separately, so it's
  always in sync with whatever panels have been OCR'd so far as more
  panels run.
- **What this does NOT do yet**: this only DISPLAYS the guess — nothing
  reads it back into an actual language selector, and it isn't yet
  threaded into any adaptation call (there is no `/api/comics/adapt`
  yet; see the chapter-level-context roadmap). It's also not
  correctable by the human if Vision's guess is wrong, unlike the
  bubble reading-order fix two entries up, which the human can actually
  edit — a real gap for a future pass, not addressed here.
- **Tier 1** for the aggregation logic itself (deterministic majority
  vote); the underlying language DETECTION is Cloud Vision's own,
  unverified black box, same epistemic status as every other Vision
  output in this document.
- **Benchmark coverage:** 4 new `tests/test_comics_ocr.py` tests
  (most-confident-first ordering, an unrecognized code reporting a null
  name, `_detected_languages` ignoring entries with no language code,
  and handling a page with no `property` key at all — 497 Python tests
  total, up from 493) and 6 new `lib/chapterLanguage.test.ts` tests (no
  OCR'd panels yet, a single panel's language, a real majority vote
  across panels, only reading each panel's own top-ranked detection
  rather than taking a max across all of them, an unrecognized
  language's raw code, and empty-detection panels being excluded from
  the vote — 44 web tests total, up from 38). Verified end-to-end with
  a real Playwright run (mocking only the OCR network response) that
  uploaded two panels, ran OCR on both with a mocked Korean detection,
  and confirmed the exact banner text "Detected language: Korean (2 of
  2 OCR'd panels)" rendered — not just that the aggregation function
  passed in isolation.

## Chapter DNA schema + generation prompt — detail

Item #3 of the chapter-level-context roadmap: the Song DNA equivalent
for a chapter's worth of comic dialogue — what a human translator (or
the Creative Adapter, eventually) needs to know before touching any
single bubble. This is schema + prompt + a one-shot generation call
ONLY — nothing calls this yet from anywhere real (no `/api/comics/
adapt`, no wiring into `app/comics/page.tsx`); that's items #4/#5,
still not built.

- **`engine/models.py`** (new): `BubbleInput` (one speech bubble/caption
  box — `id`, `source_text`, optional `voice`) and `ChapterInput` (a
  chapter: `source_language`, `target_language`, optional
  `context_note`, a list of bubbles already in corrected reading order —
  see the bubble-reordering entry above, a real prerequisite, not just
  a nice-to-have). Mirrors `SectionInput`/`SongInput`'s shape
  deliberately, down to the same duplicate-id/empty-id validation
  `SongInput._validate_sections` already does for song sections.
  `ChapterDNA` (new): `artistic_thesis`, `genre_feel`, `tone`,
  `ongoing_plot_context`, and a `characters: list[CharacterVoice]`.
  Deliberately NOT a per-bubble array the way `SongDNA.sections` is
  per-section — that granularity belongs to the later per-bubble
  adaptation pass (#4), not this one-shot chapter-wide read.
- **`CharacterVoice`** (new): `name`, `voice_description` (diction/
  personality, scoped per character so two characters in one chapter
  are pushed to sound different from each other — the comics
  equivalent of `SectionResultV1`'s per-voice consistency rule, not a
  single work-wide style), `honorific_register` (this character's
  speech formality/register — Korean/Japanese honorific level, or the
  closest equivalent a language without grammaticalized honorifics
  still has — AT THE START of the chapter only), and `relationships`
  (free text, only what the dialogue actually supports).
  `honorific_register` is explicitly a SNAPSHOT, not a tracker: real
  honorific shifts across a conversation (a common, meaningful plot
  beat in Korean/Japanese dialogue) need their own mechanism through
  room memory, which is item #6 on the roadmap and does not exist yet
  — the field only captures where a character starts, and the prompt
  says so explicitly so the model doesn't try to encode a shift into a
  short label.
- **`engine/prompts.py::chapter_dna_prompt`** + **`CHAPTER_DNA_SYSTEM`**
  (new): mirrors `song_dna_prompt`/`SONG_DNA_SYSTEM`'s structure and
  discipline closely — "never discuss translation, never propose
  {target_language} wording," a required JSON shape with no omitted
  top-level keys, and an explicit "empty list is fine, don't invent a
  character/relationship the dialogue doesn't support" instruction
  (the comics equivalent of Song DNA's "use empty lists where a
  dimension genuinely doesn't apply").
- **`engine/chapter_dna.py::generate_chapter_dna`** (new): one LLM call,
  parsed via `ChapterDNA.model_validate`. Deliberately simpler than
  `generate_song_dna` — no `_fill_missing_sections`/
  `_duplicate_repeated_profiles` equivalent needed, since there's no
  per-bubble array to backfill. Same known bound as Song DNA, disclosed
  the same way: a very long chapter (many dozens of bubbles) risks the
  same silent-degradation-not-crash failure mode already documented
  there; no chunked analysis exists for either.
- **Tier 0** — prompt text and schema only; no test corpus or real
  chapter has been run through this yet, and no downstream consumer
  exists to judge whether the resulting `ChapterDNA` is actually useful
  once #4/#5 exist to use it.
- **Benchmark coverage:** 10 new `tests/test_chapter_dna.py` tests —
  model validation (empty bubble list rejected, duplicate/empty bubble
  ids rejected, `voice` defaults to unattributed), prompt content
  (every bubble present in reading order, `{target_language}`
  substituted correctly, `honorific_register`/`voice_description`
  covered, `context_note` included when given), and
  `generate_chapter_dna` itself (a valid fake response parses
  correctly; an empty `characters` list — the caption-only-chapter
  case — is accepted, not forced to fabricate a profile). 507 Python
  tests total, up from 497. No web changes this round.

## Wiring one bubble through the Writers' Room — detail

Item #4 of the chapter-level-context roadmap: the first proof that
ChapterDNA (previous entry) can actually drive a real adaptation, not
just sit there as an analysis nobody consumes. Still no `/api/comics/
adapt` and no frontend wiring — that's item #5, still not built; this
is engine-layer only, exercised so far by fake-client tests.

- **The core decision, stated plainly:** rather than duplicating
  `engine/prompts.py`'s ~500 lines of `SongDNA`-shaped prompt-building
  (`_song_dna_context` calls `dna.section(name)` and reads per-section
  motifs/ambiguities/symbols `ChapterDNA` has no equivalent of) to build
  a parallel comics-specific prompt layer for a proof of concept,
  `engine/comics_adapt.py::_bubble_song_dna` wraps one bubble + a
  chapter's `ChapterDNA` into a single-section `SongDNA` the existing
  Translator -> Creative Adapter -> Judge machinery already knows how
  to consume, completely unmodified. `tone` fills `poetic_register`
  (the same "rhetorical register, a handful of words" axis, just named
  differently per medium); `ongoing_plot_context` fills both
  `arc_shape` and `songwriter_intention`, since a single dramatic beat's
  "what's happening" and "why" collapse into the same answer, unlike a
  whole song's arc. The single `SectionProfile` is an HONESTLY NEUTRAL
  placeholder (`narrative_function`/`density` both say plainly "not
  analyzed yet" rather than inventing a per-bubble read Chapter DNA was
  never asked to produce) — the one exception is
  `emotional_arc_point.dominant_feeling`, filled with the chapter's real
  `tone` since that costs nothing and is directly known.
- **`adapt_bubble`** runs one bubble through `writers_room_v1.
  run_section` unchanged. **Voice consistency works correctly, for
  free**: `bubble.voice` threads through exactly the way
  `SectionInput.voice` already does for a song's duet/dialogue
  sections — no new code needed for two characters in the same chapter
  to be judged for consistency WITHIN each one's own voice, the same
  rule songs already have.
- **`adapt_chapter`** loops every bubble in order, carrying `RoomMemory`
  forward the same way `engine/pipeline.py::run_engine` does for song
  sections — `prior_rulings` (so a later bubble's Judge call sees
  earlier bubbles' rulings, verified directly: the second bubble's
  prompt literally contains the first bubble's section id and final
  line) and `compensations` (so a structural-trap decision, e.g. which
  English register carries a Korean speech-level distinction, made on
  bubble 1 is binding and visible in bubble 2's prompt — also verified
  directly, not assumed).
- **What this deliberately does NOT do, all disclosed rather than
  glossed over:** no batching (`adapt_chapter` is N sequential full
  Writers' Room runs — 3-7 LLM calls each, same per-unit cost a song
  section already has, just applied to much shorter dialogue units; a
  real chapter with dozens of bubbles means dozens of full room runs,
  the exact cost concern flagged when this roadmap was first scoped).
  No motif/ambiguity/symbol tracking (`ChapterDNA` has none of these
  concepts yet — the wrapped `SongDNA`'s `motifs`/`ambiguities`/
  `symbols` are always empty, never fabricated). No honorific-register
  tracking through room memory (item #6, still not built) — a
  character's `honorific_register` snapshot from Chapter DNA is never
  even read by this module yet, let alone updated as a chapter
  progresses; that wiring doesn't exist until #6.
- **Tier 1** for the wrapping/looping logic itself (deterministic,
  reuses existing, already-tested Writers' Room code unchanged); the
  adaptation OUTPUT's quality is exactly as unverified as any other
  fresh Writers' Room run in this document — no real chapter has been
  run through this yet, only fake-client tests.
- **Benchmark coverage:** 5 new `tests/test_comics_adapt.py` tests —
  `_bubble_song_dna`'s field mapping (direct unit test, confirms no
  fabricated per-bubble analysis leaks in), `adapt_bubble` running the
  full 3-call room and threading voice onto the ruling, `adapt_chapter`
  processing every bubble in order with the right voice per bubble, and
  two tests directly confirming cross-bubble continuity by inspecting
  the actual judge prompts sent for bubble 2 (containing bubble 1's
  section id/final line, and its compensation entry) rather than just
  trusting the room-memory object's internal state. 512 Python tests
  total, up from 507.

## /api/comics/adapt: the endpoint + frontend wiring — detail

Item #5 of the chapter-level-context roadmap — the point where this
stops being engine-layer-only code and becomes something clickable.
Wires `engine/chapter_dna.py` + `engine/comics_adapt.py` (previous two
entries) into a real HTTP endpoint and a real "Adapt chapter" button in
`/comics`.

- **`server/main.py::comics_adapt_endpoint`** (new `POST /api/comics/
  adapt`): takes `{source_language, target_language, panels: [{id,
  text}]}`, builds a `ChapterInput`, runs `generate_chapter_dna` then
  `adapt_chapter`, and returns `{chapter_dna, panels: [{id, literal,
  adapted_text, why}]}`. Reuses `server/mapping.py::_explain_why`/
  `_translator_text` directly rather than reimplementing the
  literal-line lookup or the plain-English "why" explanation — both
  were already generic across `SectionResultV1`, not song-specific.
  **A real scoping decision, stated plainly:** each PANEL is treated as
  one adaptation unit, not each individually-detected OCR region — a
  panel with several speech bubbles is adapted as one combined block of
  dialogue. Splitting to true per-bubble granularity is a further
  refinement, not done here (it would need per-panel bubble-to-bubble
  UI the current workspace doesn't have). No voice/character
  attribution either — nothing in the current UI tags a panel with a
  speaking character, so every bubble goes in with `voice=None`. This
  means Chapter DNA's per-character voice profiles get generated but
  the per-bubble voice-consistency machinery they'd otherwise drive
  (item #4's actual payoff) isn't exercised by real usage yet — only by
  the fake-client tests that explicitly set `voice`.
- **Deliberately synchronous**, same known limitation `/api/adapt`
  itself had before `/api/adapt/start` existed: a chapter with many
  panels means many sequential full Writers' Room runs, which can
  exceed a serverless function's timeout. Fine for the handful of
  panels this workspace is realistically used with today; a longer
  chapter needs the same async job-polling pattern already established
  for music, not built here. `web/app/api/comics/adapt/route.ts` mirrors
  `app/api/adapt/route.ts`'s 60s ceiling and abort-before-timeout
  handling exactly.
- **`lib/comicsAdapt.ts::adaptChapter`** + **`app/comics/page.tsx`**:
  new From/Into language selectors (reusing `TargetLanguageSelect`,
  same component `InputScreen.tsx` uses) and an "Adapt chapter" button.
  The "From" selector auto-fills from `guessChapterLanguage`'s detected-
  language guess the first time it resolves to one of CASTIA's 6
  supported languages, using the exact same "auto-detect until the
  human touches it" `sourceLanguageTouched` pattern `InputScreen.tsx`
  already established for a pasted song. On a successful adapt call,
  each panel's `adaptedText`/`why` fields are filled ONLY if still
  empty — never overwrites text a human already reviewed or typed by
  hand, the same discipline "Run OCR" already follows for
  `extractedText`.
- **Tier 1** for the wiring/request-shape logic (deterministic); the
  adaptation output itself carries the same Tier 0/unverified status
  every fresh Writers' Room run has in this document.
- **Benchmark coverage:** 4 new `tests/test_server.py` tests for the
  endpoint (returns chapter DNA + per-panel results; skips
  whitespace-only panels; rejects an all-empty-panel request with a
  400; reports an engine `LLMError` as a 502) — 516 Python tests total,
  up from 512. Verified end-to-end with a real three-process Playwright
  run (Next.js + mocked `/api/comics/ocr` and `/api/comics/adapt`
  network responses, since no real Vision/LLM credentials exist in
  this sandbox): uploaded a real panel, ran OCR, confirmed the "From"
  selector auto-filled to the detected language ("Korean"), clicked
  "Adapt chapter," confirmed the actual outgoing request carried the
  correct source/target languages and panel text, and confirmed the
  response correctly filled the "Adapted text" and "Why" fields in the
  UI — not just that the fetch call resolved.

## Honorific/speech-register tracking through room memory — detail

Item #6, the last item on the chapter-level-context roadmap and the one
flagged as hardest when this was first scoped: real honorific/speech-
register shifts across a conversation (Korean/Japanese speech levels,
tu/vous) are a common, meaningful plot beat — a character dropping
formality out of anger, or turning formal to address a superior. Until
now, `ChapterDNA.characters[].honorific_register` was only ever a
snapshot of where a character starts, read once and never updated (the
previous two entries said so explicitly).

- **The integration point, found rather than built from scratch:**
  `RoomMemory.summary_for_prompt()` already gets included, unmodified,
  in every stage's prompt (Translator, Creative Adapter, Judge triage
  and final) via each builder's existing `room_memory.summary_for_prompt()`
  call — that's how `compensations` already reaches every stage. Adding
  `RoomMemory.honorific_state: dict[str, str]` (character name -> current
  register) and rendering it in `summary_for_prompt()` meant **no prompt
  builder's function signature needed to change at all** — the new state
  is automatically visible everywhere `RoomMemory` already flows.
- **`engine/models.py::JudgeRuling.honorific_note`** (new, optional):
  the Judge's own report of a character's speech register AFTER ruling
  on a section. **Gated on `voice` being set**
  (`engine/prompts.py::_ruling_schema(profile, voice)`) — an
  unattributed/narrator section (most songs, most narration-only
  chapters) has no clear "whose register" question to ask, so the
  schema stays exactly as before for those. This is also why the
  Phase-1 byte-identical-prompt guarantee held: `tests/test_golden_prompts.py`'s
  fixture never sets `voice`, so its hash needed NO update — confirmed
  by running that suite, not assumed.
- **`engine/comics_adapt.py::adapt_chapter`**: seeds
  `room_memory.honorific_state` from `ChapterDNA.characters`' snapshot
  register at the start of a chapter, then after every bubble with a
  `voice` set, overwrites that character's entry with
  `result.ruling.honorific_note` when the Judge reported one — a real
  update, not an append, so a later section always sees the CURRENT
  register, not a growing history. An unattributed bubble neither reads
  nor writes this state.
- **Same mechanism works for songs too, not just comics** — a duet with
  a real mid-song formality shift (Hindi tu/aap, Korean speech levels)
  gets the identical benefit for free, since `RoomMemory`/`voice` are
  shared primitives, not comics-specific. Nothing about this entry is
  gated to `ChapterDNA` specifically.
- **What this does NOT do:** the Judge is ASKED to report a shift
  honestly rather than defaulting to the old listed register, but
  nothing verifies it actually does so accurately — this is Tier 0,
  same as any other Judge self-report in this document (the deviation
  ledger and dimension scores have the same status). No UI surfaces
  `honorific_note`/`honorific_state` anywhere yet — it's real backend
  state used by later prompts, not shown to the human reviewing a
  panel. And this is the LAST item on the chapter-level-context
  roadmap scoped at the start of this thread — everything from bubble
  reading order through here is now wired end to end, though real usage
  (a real chapter, a real API key, a human reviewing real output) still
  hasn't happened in this sandbox.
- **Tier 1** for the plumbing (deterministic: seed once, overwrite on a
  reported change, surface via existing `summary_for_prompt`); **Tier 0**
  for whether the Judge's self-reported shift is actually correct.
- **Benchmark coverage:** 4 new `tests/test_prompts.py` tests
  (`_ruling_schema` omits/includes the field based on `voice`;
  `judge_triage_prompt` end-to-end does the same; `RoomMemory.
  summary_for_prompt()` surfaces `honorific_state` into a real prompt)
  and 3 new `tests/test_comics_adapt.py` tests (`adapt_chapter` seeds
  the state from Chapter DNA and it reaches the first judge prompt; a
  reported shift correctly overwrites — not appends — the character's
  entry, verified by inspecting bubble 2's actual prompt text and
  confirming the OLD register no longer appears; an unattributed bubble
  neither reads nor writes the tracked state). 523 Python tests total,
  up from 516. No web changes this round — this is backend-only state.

## Voice/character selector — detail

- **What it is:** a free-text "Speaker" field in the comics panel
  workspace (`web/components/comics/PanelWorkspace.tsx`), one per panel,
  with native HTML `<datalist>` autocomplete built from every voice
  already typed elsewhere in the chapter — no fixed cast list, no extra
  dependency. Blank means unattributed (narration, unclear speaker),
  same as before this field existed.
- **Why it matters:** this is the human-facing control for machinery
  that was built but never actually driven by real UI interaction —
  `BubbleInput.voice` is what item #4 (Writers' Room wiring) and item #6
  (honorific tracking) both key off of. Before this, `voice` could only
  ever be set by a test fixture. Now a person tagging "Guard Captain" on
  panel 1 and panel 5 is what makes the Judge's per-character voice
  consistency and honorific-register tracking actually engage across
  those panels.
- **Threaded end to end:** `ComicPanel.voice` (web state, persisted
  through CSV export/import) → `adaptChapter()`'s panel payload →
  `ComicsPanelText.voice` (`server/main.py`) → `BubbleInput(voice=...)`
  fed to `adapt_chapter`. A panel with no speaker typed sends `voice:
  undefined`/`None` through every layer — the "never overwrite, blank is
  a valid state" behavior established for OCR pre-fill applies here too.
- **What this does NOT do:** there's no structured cast list or
  per-character metadata (age, relationship, honorific baseline) beyond
  the string name itself — `ChapterDNA.characters[].name` and this
  field are matched by exact string equality, so "Guard Captain" and
  "the guard captain" are different voices to the system. No dedicated
  cast-management UI; the datalist is the entire discoverability
  mechanism. Nothing validates a typed name against `ChapterDNA`'s
  character list, so a typo silently creates a new, unrelated voice
  bucket instead of erroring.
- **Verified two ways:** `tests/test_server.py::
  test_comics_adapt_endpoint_threads_voice_into_bubble_input` confirms
  the field survives the FastAPI boundary intact (a named panel keeps
  its string, an unnamed one stays `None`) — Tier 1, deterministic.
  Separately, a live Next.js production build was exercised in a real
  Chromium browser via Playwright: two real panel images uploaded,
  "Guard Captain" typed into panel 1's Speaker field, confirmed by
  reading the rendered screenshot; switching to panel 2 showed its own
  independent (empty) Speaker field; the `<datalist>` DOM was inspected
  directly and contained `<option value="Guard Captain">` reachable
  from panel 2 — the autocomplete genuinely offers names typed on other
  panels, not just the active one. This was a real rendered check, not
  an assumption from reading the code.
- **Tier 1** — this is UI plumbing and payload threading, fully
  deterministic; there's no Tier 0 judgment call in this feature itself
  (the honorific-tracking accuracy it feeds into is already tracked as
  Tier 0 in the entry above).
- **Benchmark coverage:** 1 new Python test (`tests/test_server.py`,
  524 total, up from 523), 1 new Vitest CSV-column test plus 2 fixture
  updates for the new required field (`web/lib/comics-types.test.ts`,
  `web/lib/chapterLanguage.test.ts` — 45 total, up from 44), confirmed
  clean `tsc --noEmit` and `next build`, and the live-browser Playwright
  pass described above.

## Medium-chooser split landing page — detail

- **What it is:** `/` is no longer the music workflow directly — it's a
  neutral chooser between two equal tiles, Music and Webtoons, each
  linking out to its own workspace (`/music`, moved verbatim from the
  old `app/page.tsx`; `/comics`, unchanged). Same tile size, same visual
  weight, deliberately not a flagship-plus-experiment layout — Webtoons
  carries a "Beta" badge (same visual convention as
  `DashboardSidebar.tsx`'s "Soon" pill) rather than being presented as
  equally mature, since it isn't: no save/collections/share-link, and
  `/api/comics/adapt` is still a synchronous call that can time out on a
  long chapter, unlike music's job/poll pattern
  (`/api/adapt/start` + `/api/adapt/jobs/[jobId]`).
- **What moved:** every `/#lyrics` anchor link across the app
  (`SiteHeader`'s "Get Started", `ResultScreen`'s "Try any song", the
  sign-in page's CTA, `alternate-homepage`'s two CTAs) now points at
  `/music#lyrics`, since that textarea no longer lives at `/`.
  `app/comics/page.tsx`'s own top comment was updated to stop claiming
  it's reachable "only by URL" — it now has a real entry point.
- **What this does NOT do:** no "remember last medium" mechanism yet
  (every visit to `/` shows the chooser, even for someone who always
  picks the same tile) and no in-workspace switcher to hop between
  `/music` and `/comics` without going back through `/` — both were
  scoped in conversation as the next increment, deliberately not bundled
  into this pass. The dashboard (`/dashboard`) is still music-only and
  untouched; whether it gets the same split treatment is an open
  question, not decided here. Webtoons' tile proof-point is a small
  honest mock of the panel-upload UI, not a real captured screenshot —
  no real end-to-end chapter run (real API keys, a human reviewing real
  output) has happened in this sandbox to crop one from.
- **Tier 1** — this is routing and static layout, fully deterministic;
  no model-quality claim is made or changed by this entry.
  **Verified live:** production build (`next build`) succeeded with `/`
  now a 2.2 kB static page (down from carrying the full input screen);
  a real Chromium/Playwright pass loaded `/` at desktop and mobile
  widths, confirmed both tiles render side-by-side on desktop and stack
  on mobile, and confirmed clicking each tile actually navigates to
  `/music` and `/comics` respectively with their existing content
  intact — read back from the rendered screenshots, not assumed from
  the code.
- **Benchmark coverage:** no new automated tests — this is a pure
  routing/JSX move with nothing new to unit-test; `tsc --noEmit`, all
  524 Python tests, and all 45 Vitest tests stayed green throughout.

## Medium switcher (header) — detail

- **What it is:** a small Music/Webtoons pill in `SiteHeader`, shown only
  on `/music` and `/comics` (via a new `active="music" | "webtoons"`
  value), that lets someone hop directly between the two workspaces
  without going back through `/`. Clicking the inactive side writes
  `localStorage["castia-last-medium"]` and navigates. Extracted into its
  own client component (`MediumSwitcher.tsx`) rather than making
  `SiteHeader` itself interactive, for the same reason Sign In doesn't
  branch on session there today: `SiteHeader` renders from both server
  and client trees, and every page that doesn't pass the new `active`
  value (`/`, `/pricing`, `/sign-in`, all of `/dashboard`) is completely
  unaffected — no new client-side code ships to them.
- **Bug fix bundled in:** `InputScreen.tsx` was still passing
  `active="home"` after last round's move to `/music`, and
  `SiteHeader`'s "Use Cases" link still pointed at `/#features` instead
  of `/music#features` — both are stale from that move and are fixed
  here, not new behavior.
- **What this does NOT do:** `/` still doesn't read
  `castia-last-medium` yet — visiting `/` always shows the chooser
  regardless of what this switcher has written. That read/redirect side
  was explicitly scoped as a separate next step. No switcher appears
  anywhere in `/dashboard` (still music-only, untouched, same open
  question as last round).
- **Tier 1** — deterministic routing/state, no model-quality claim.
  **Verified live:** real Chromium/Playwright pass on the production
  build — clicked Webtoons from `/music`, confirmed navigation to
  `/comics` AND read `localStorage.getItem("castia-last-medium")` back as
  `"webtoons"` (not just clicked-and-assumed); clicked Music from
  `/comics`, confirmed the reverse. Screenshots of the header on both
  pages confirm correct active-state highlighting and correct theming
  (dark pill on `/music`, light pill on `/comics`) in each context.
- **Benchmark coverage:** no new automated tests (routing + a DOM
  interaction, no new pure logic to unit test); `tsc --noEmit`, all 524
  Python tests, and all 45 Vitest tests stayed green.

## "/" remembers your last medium — detail

- **What it is:** `/` now checks `lib/mediumPreference.ts`'s stored
  value on mount and, if set, redirects straight to `/music` or
  `/comics` instead of rendering the chooser — closing the gap flagged
  at the end of the last two rounds. The preference is written on every
  real arrival at either workspace: a mount-effect in `/music` and
  `/comics` themselves (covers a tile click, a direct URL/bookmark, or
  the header switcher's own navigation), not just the switcher's click
  handler (which also writes it, redundantly but harmlessly, right
  before it navigates).
- **The flash tradeoff, decided:** the last scope flagged this as an
  open call - accept a one-frame chooser flash, or add a pre-hydration
  script to avoid it entirely. Landed on a third, simpler option: `/`
  renders nothing until its one-time localStorage check resolves. A
  *returning* visitor never sees the chooser at all (blank frame →
  redirect); a *brand-new* visitor sees a blank frame → chooser, which
  only ever happens once per browser. No inline pre-hydration script
  needed.
- **What this does NOT do:** doesn't touch account/server state at all
  — confirmed dead ends the same way `web/auth.ts`'s no-DB-adapter
  design already does for this class of low-stakes preference. A
  cleared localStorage (private browsing, a different browser) always
  falls back to showing the chooser again, by design, not as a bug.
- **Tier 1** — deterministic, no model-quality claim. **Verified live:**
  a full Chromium/Playwright pass exercised all five real states, not
  assumed from the code: (1) a fresh browser context shows the chooser
  at `/`; (2) visiting `/comics` stores `"webtoons"`; (3) revisiting `/`
  afterward redirects straight to `/comics` with no chooser shown; (4)
  switching to Music via the header then revisiting `/` redirects to
  `/music`; (5) clearing localStorage makes the chooser reappear at
  `/`. Screenshots confirm the chooser's own rendering is unchanged when
  it does show.
- **Benchmark coverage:** 3 new Vitest unit tests for
  `lib/mediumPreference.ts` (round-trips a written value, returns
  `null` before anything's written, ignores a garbage stored value) —
  48 Vitest tests total, up from 45, using a minimal in-memory
  `localStorage` stub rather than pulling in jsdom (this harness is
  deliberately jsdom-free today per `vitest.config.mts`'s own comment).
  `tsc --noEmit`, `next build`, and all 524 Python tests stayed green
  and are unaffected (this round is web-only).

## Comics persistence — detail

- **What it is:** the real blocker flagged when the dashboard-split scope
  was written — comics had zero server-side persistence, so "split the
  dashboard by medium" would have had nothing on the Webtoons side to
  show. This closes that gap, mirroring the music side's existing
  mechanisms rather than inventing new ones:
  - **A real, content-addressed, shareable id** — `cache.comics_content_id()`
    (server/cache.py), hashing a chapter's ordered panel texts + language
    pair, always folding in a literal `"comics"` tag so a chapter and a
    song can never collide even sharing the same flat `get()`/`set()`
    id space. `/api/comics/adapt` now checks this id before running the
    engine (a byte-identical resubmission is a cache hit, not a re-run,
    same as `/api/adapt`) and returns it as `id` in the response.
  - **A read side**: `GET /api/comics/adapt/{result_id}` (server/main.py),
    mirroring `GET /api/adapt/{result_id}` exactly.
  - **A share page**: `/comics/s/[id]` (app/comics/s/[id]/page.tsx) —
    the comics equivalent of `/s/[id]`, deliberately simpler (no
    sessionStorage fast path, no original-image toggle, no YouTube sync —
    just literal/adapted/why per panel, since that's all the persisted
    payload carries) with the same honest dead-link state for an unknown
    id. The comics workspace (`app/comics/page.tsx`) shows a `CopyLinkButton`
    (now generalized with a `basePath` prop rather than duplicated) once
    an adapt call succeeds, cleared again on any edit that would make the
    persisted link stale (a panel added/removed, or a fresh adapt run).
  - **History**: `Adaptation.medium` (server/db_models.py, migration
    `0002_add_adaptation_medium.py` — the first real frozen migration
    after the baseline, adding a Postgres column with a `"music"` server
    default so every pre-existing row backfills correctly, since nothing
    before this column could have meant anything else). `accounts.record_adaptation()`
    takes a `medium` parameter (default `"music"`); `comics_adapt_endpoint`
    passes `"webtoons"` for a signed-in user, via the same `_authed_user_id`/
    internal-secret trust model `/api/adapt` already uses.
    `app/api/comics/adapt/route.ts` gained the same `identityHeaders()`
    forwarding `/api/adapt/start/route.ts` already had.
- **What this does NOT do:** no dashboard UI change at all — Recent
  Adaptations, Favorites, and Collections still only ever show music
  history; `medium` is now a real, queryable field on every row, but
  nothing reads it yet on the dashboard side (that's the next scoped
  step). The comics adapt call is still synchronous (no job/poll
  pattern), so persistence doesn't fix the long-chapter timeout risk,
  it just means whatever DID complete is now durable and linkable. The
  share page doesn't show panel images (never stored) or chapter-DNA
  character list — just the artistic thesis/genre/tone line plus each
  panel's literal/adapted/why.
- **Tier 1** — deterministic storage/routing, no model-quality claim.
  **Verified live:** a full Chromium/Playwright pass against the
  production build with `/api/comics/adapt` mocked (no real LLM calls in
  this sandbox) confirmed the Share button appears after a successful
  adapt call using the response's real `id`; navigating directly to
  `/comics/s/test-chapter-id-123` (mocked GET) rendered the persisted
  chapter DNA line and panel card correctly; navigating to an unknown id
  showed the honest dead-link state — all three read back from rendered
  screenshots, not assumed from the code.
- **Benchmark coverage:** 4 new `tests/test_cache.py` tests
  (`comics_content_id` differs by panel order, differs by language pair,
  is deterministic, never collides with a song's `content_id` on
  identical text); 2 new `tests/test_accounts.py` tests (`medium`
  defaults to `"music"`, accepts `"webtoons"` explicitly); 5 new
  `tests/test_server.py` tests (`comics_adapt_endpoint` returns a real
  persisted `id`; a repeat submission is a genuine cache hit, verified by
  counting `generate_chapter_dna` calls across two identical requests,
  not just comparing output; history is recorded with `medium="webtoons"`
  for a signed-in user; `GET /api/comics/adapt/{id}` round-trips a
  persisted result and 404s for an unknown one) — 535 Python tests
  total, up from 524. `tsc --noEmit`, `next build`, and all 48 Vitest
  tests stayed green.

## Backend medium filter for history — detail

- **What it is:** `accounts.list_adaptations()` gains an optional
  `medium` parameter ("music" | "webtoons"), filtering in SQL the same
  way `favorites_only`/`collection_id` already do. `server/main.py`'s
  `GET /api/me/adaptations` accepts the same `medium` query param and
  passes it straight through. `medium=None` (the default, and what
  every existing caller still gets) returns both mediums in one
  combined, newest-first list — a deliberate choice, not a placeholder:
  dashboard history is meant to read as one timeline, not two lists a
  caller has to merge, per the "one product, not two products glued
  together" framing this whole thread has been building toward.
- **What this does NOT do:** nothing in the Next.js layer forwards this
  param yet (`app/api/me/adaptations/route.ts` still only forwards
  `favoritesOnly`/`collectionId`), `lib/history.ts::HistoryEntry` still
  doesn't type `medium` on the frontend, and `RecentAdaptations.tsx`
  still renders every row as if it were music (hardcoded `/s/` link,
  assumes a `hook` line exists) — a real comics entry would render
  wrong today if one ever reached this component. That per-row
  rendering fix is the next scoped step, deliberately not bundled here
  since this round is backend-only, mirroring how the medium column
  itself landed separately from any UI last round.
- **Tier 1** — deterministic SQL filtering, no model-quality claim.
- **Benchmark coverage:** 1 new `tests/test_accounts.py` test
  (`list_adaptations` with `medium="music"`, `medium="webtoons"`, and
  unset all return the correct rows against the same two-row fixture) —
  536 Python tests total, up from 535. No endpoint-level test added for
  `GET /api/me/adaptations` itself, consistent with `favorites_only`/
  `collection_id`'s existing coverage, which is also only exercised at
  the `accounts.py` level, not re-tested through the FastAPI route.

## Frontend threading for the medium filter — detail

- **What it is:** the frontend catches up to last round's backend-only
  `medium` filter. `app/api/me/adaptations/route.ts` forwards an
  optional `?medium=` straight through (omitted by every caller today,
  same as before). `HistoryEntry` (`lib/history.ts`) now types `medium`.
  `RecentAdaptations.tsx` accepts an optional `medium` prop (no UI
  control passes it yet - this is the plumbing, not the filter chip)
  and, more importantly, its per-row rendering is now genuinely
  mixed-list-safe: a new `lib/historyEntryDisplay.ts` resolves each
  row's label and href from its own `medium` — a webtoons row links to
  `/comics/s/[id]` and shows "Adapted chapter" (there's no hook line to
  show; the comics wire shape never produces one), a music row keeps
  its long-standing `/s/[id]` + hook-or-"Untitled adaptation" behavior.
  The two generic copy strings that said "songs" (`"a history of the
  songs you adapt"`, `"the first song you adapt will show up here"`)
  were also genuinely wrong now that this list can contain both — reworded
  medium-neutral.
- **What this does NOT do:** no visible filter control anywhere — the
  `medium` prop exists so a future one has something to call, but
  nothing calls it yet. `app/dashboard/page.tsx` itself is still
  Music-only and untouched, same open question as every prior round.
- **Tier 1** — deterministic rendering/routing logic, no model-quality
  claim. **Verified live:** a Chromium/Playwright pass against the
  production build with `/api/me/adaptations` mocked to return one
  music row and one webtoons row together confirmed (via each row's
  actual rendered `href` attribute, not just a screenshot) that the
  music row points at `/s/song-xyz` and the webtoons row at
  `/comics/s/chapter-abc`, with "Adapted chapter" reading naturally
  alongside a real hook line rather than looking broken or blank.
- **Benchmark coverage:** extracted the label/href resolution into
  `lib/historyEntryDisplay.ts` specifically so it could get real Vitest
  coverage rather than only being checked by eye in the browser — 4 new
  tests (music entry keeps its hook + `/s/` link; music entry with no
  hook falls back to "Untitled adaptation"; webtoons entry links to
  `/comics/s/` with "Adapted chapter"; the fallback is hook-first, not
  medium-first, documented in case a webtoons hook ever exists) plus 2
  existing fixture files (`favorites.test.ts`, `collections.test.ts`)
  updated for the now-required `medium` field — 52 Vitest tests total,
  up from 48. `tsc --noEmit`, `next build`, and all 536 Python tests
  stayed green (Python side untouched this round).

## Product rename: AURA → CASTIA

- **What it is:** a full-codebase rename from AURA to Castia (domain:
  `usecastia.com`, to be booked separately). 76 files touched via three
  ordered case-sensitive passes (`AURA`→`CASTIA`, `Aura`→`Castia`,
  `aura`→`castia`), covering: the visible brand everywhere (`Logo.tsx`,
  page titles/metadata, marketing copy, dashboard/comics UI strings),
  every code comment and doc (`docs/*.md`, `README.md`,
  `docs/AURA_ARCHITECTURE.md` → `docs/CASTIA_ARCHITECTURE.md`), the 17
  `AURA_*` environment variables (`AURA_INTERNAL_API_SECRET`,
  `AURA_ENGINE_API_URL`, etc. → `CASTIA_*`), the two internal HTTP
  headers (`X-Aura-User-Id`/`X-Aura-Internal-Secret` →
  `X-Castia-User-Id`/`X-Castia-Internal-Secret`), the NextAuth session
  field (`auraUserId` → `castiaUserId`), client-side storage keys
  (`aura-last-medium`, `aura-result-*`, the CSV export filename), the
  benchmark system identifier (`AuraSystem`/`"aura"` →
  `CastiaSystem`/`"castia"`), and both `package.json`/`package-lock.json`
  package names.
- **One deliberate exception, NOT renamed:** the per-section wire-shape
  field that carries the adapted line itself —
  `SectionComparison.aura` (`web/lib/types.ts`), `section.aura`
  (`ComparisonCard.tsx`), the `aura` parameter/dict-key in
  `server/mapping.py`, and the matching test fixtures
  (`tests/test_mapping.py`, `tests/test_server.py`'s two JSON fixture
  lines) all still say `aura`. This field is embedded in
  `cached_results.result_json` for every song ever adapted; renaming it
  would have silently broken every already-shared `/s/[id]` link and
  every already-cached result the moment this deployed (the frontend
  would read a `castia` key that doesn't exist in old cached JSON and
  render a blank adapted line) — a real data-corruption risk for zero
  user-visible benefit, since nobody sees this JSON key name directly.
  The *visible* label built from this field (the "Aura" badge on
  `ComparisonCard`) was still renamed to "Castia" — only the underlying
  data key stayed put.
- **What this does NOT do:** does not touch the actual deployed
  Railway/Vercel environment variables — those still need the newly-named
  `CASTIA_*` vars added (with the same values) on both platforms before
  or immediately after this deploys, or the app breaks (this was an
  explicit, confirmed tradeoff, not an oversight — the alternative was
  leaving all 17 env vars as `AURA_*` forever). Does not regenerate the
  static marketing screenshots (`web/public/screenshots/*.png`) — those
  are baked pixel images from a real past run and still visibly show
  "AURA" in the captured UI; regenerating them needs
  `web/scripts/capture-screenshots.mjs` run against a live instance, not
  a text rename. Does not rename the GitHub repository itself
  (`experience-engine`) or touch anything outside this rename's file
  list.
- **Tier 1** — mechanical text substitution, no model-quality claim.
  **Verified:** a scripted before/after diff confirmed only the intended
  wire-field exception remains lowercase-`aura` anywhere in the
  codebase; all 536 Python tests and all 52 Vitest tests pass unchanged;
  `tsc --noEmit` and `next build` are clean; a live Chromium pass against
  the production build confirmed the header logo, page titles, the
  comics workspace heading, and the demo result page's section label all
  read "CASTIA"/"Castia" correctly, while the demo result's adapted-line
  *text itself* still rendered correctly (proving the kept `aura` field
  still round-trips end to end despite everything around it being
  renamed).
- **Benchmark coverage:** no new tests written (this is a rename, not
  new behavior) — existing coverage (536 + 52) serves as the regression
  check, and it stayed green throughout.

## Public API (v1) — detail

- **What it is:** the first real, callable public API — `POST /v1/adapt`
  and `POST /v1/comics/adapt`, gated by a real API key
  (`Authorization: Bearer <key>`) instead of a signed-in session. Both
  are thin wrappers: `_adapt_or_serve_cached`/`_comics_adapt_or_serve_cached`
  were extracted out of `/api/adapt`/`/api/comics/adapt` so the exact
  same cache-hit/fuzzy-hit/engine-run/history-recording logic runs for
  both the browser and API-key callers — no new engine behavior, no
  drift risk between the two paths. Keys are issued/listed/revoked from
  a real dashboard page (`/dashboard/settings`, no longer a
  `DashboardStub`) backed by `server/api_keys.py` and two new tables
  (`ApiKey`, `ApiKeyUsage`, migration `0003_add_api_keys.py`). Only a
  key's hash is ever stored; the raw value is shown to the human exactly
  once, at creation, in the settings page itself. Rate limiting is a new
  per-key daily dimension (`CASTIA_API_DAILY_LIMIT`, default 1000/day),
  deliberately separate from the existing per-IP `CASTIA_DAILY_LIMIT` —
  an API caller is identified by its key, not by an IP that many
  legitimate calls could share. The stale "API — Soon" badges in
  `SiteHeader` and `DashboardSidebar` were updated to "Beta" and now
  link to the settings page, since the API genuinely exists now.
- **A real, pre-existing bug found and fixed along the way, unrelated to
  this feature:** `migrate_to_head()` crashed with "duplicate column:
  medium" on any genuinely fresh database (confirmed on the
  already-pushed code from before this round, with zero API-key
  involvement) — `0001_baseline.py`'s `create_all(checkfirst=True)`
  builds every table from CURRENT model definitions, so a fresh database
  already got `medium` from the baseline, and `0002`'s unconditional
  `ADD COLUMN` collided with it. Never surfaced on Railway's real
  database (that table predates the migration system, so `checkfirst`
  skips it there), but would have broken any brand-new environment setup
  outright. Fixed by making `0002` and `0003` each check-before-act
  (existence-guarded), matching the `IF NOT EXISTS` pattern
  `server/db.py::_patch_known_schema_drift` already used for this exact
  class of problem — verified by actually running `migrate_to_head()`
  against both a fresh database and a simulated pre-existing one, not
  assumed from reading the code.
- **What this does NOT do:** no async job/poll pattern for `/v1/*` yet —
  a long comics chapter can still time out synchronously, same known,
  disclosed limitation the browser-facing comics endpoint has. No
  published API docs page (the settings page shows the request shape
  inline, but there's no dedicated reference). No billing/metering tied
  to a plan tier — `CASTIA_API_DAILY_LIMIT` is a flat global default for
  every key, not yet plan-aware even though `User.plan` already has
  `creator`/`studio`/`enterprise` tiers defined. No CORS opened up for
  browser-based third-party callers — this is a server-to-server API
  today.
- **Tier 1** — deterministic auth/rate-limiting/routing logic, no
  model-quality claim (the underlying adaptation quality is whatever the
  existing engine already provides, unchanged by this round).
  **Verified:** 566 Python tests (13 new: key issuance/resolution/
  revocation/rate-limiting in `tests/test_api_keys.py`; `/v1/adapt` and
  `/v1/comics/adapt` success/auth-failure/rate-limit/history-recording,
  and explicit proof the per-IP browser quota does NOT gate an API-key
  caller, in `tests/test_v1_api.py`; 2 new migration regression tests in
  `tests/test_migrations.py` that would have caught the pre-existing bug
  above) plus a live Chromium/Playwright pass against the production
  build confirming key creation shows the raw value with a copy button,
  revocation immediately updates the list UI, and the header/sidebar
  badges read "Beta" and link correctly.
- **Benchmark coverage:** 553 → 566 Python tests; 52 Vitest tests
  unchanged (no new pure-logic module on the frontend this round — the
  settings page is a real component, verified live instead). `tsc
  --noEmit` and `next build` clean.

## Comics image redraw/typesetting (Scope B) — detail

- **What it is:** the first real image-editing capability this project
  has ever had — `engine/comics_redraw.py::redraw_panel` erases the
  original text out of a speech-bubble region and draws the adapted
  line back in its place, via a new `POST /api/comics/redraw` endpoint.
  Pipeline: estimate each region's text color from the original pixels
  (a heuristic — darkest-cluster sampling, assumes dark text on a
  lighter bubble), inpaint every region at once with OpenCV's classical
  Telea algorithm (`cv2.inpaint`), then word-wrap and font-size-fit the
  adapted line into each region and draw it in the estimated color,
  using one bundled font (Liberation Sans, SIL-OFL licensed, shipped in
  `engine/assets/fonts/` — verified the plain `python:3.11-slim` base
  image ships no fonts at all, so relying on a system font would have
  broken at deploy time, not just looked wrong). `regions` is
  JSON-encoded (multipart can't carry nested JSON) — the same
  `{x,y,width,height}` bbox shape `/api/comics/ocr` already produces,
  paired with whatever adapted text the caller supplies.
- **Honest scope, disclosed in the module's own docstring:** SPEECH
  BUBBLES ONLY — SFX text integrated into busy artwork is explicitly
  not attempted (inpainting a jagged, textured background is a much
  harder problem than a bubble's usually-plain interior, and attempting
  it silently would produce a visibly broken smudge). The font never
  matches the original comic's lettering — that was flagged as
  aspirational marketing copy when this was scoped, and still isn't a
  real capability. No persistence/caching/share-link — unlike
  `/api/comics/adapt`, this is a pure synchronous transform; redrawing
  the same panel twice re-runs the whole pipeline both times.
- **Real visual verification, not just unit tests:** built two synthetic
  test panels (no real webtoon panel images exist in this repo to test
  against — itself a disclosed coverage gap) and actually looked at the
  rendered output. A plain-white bubble case came out genuinely clean —
  original text fully gone, no visible artifact, adapted text
  word-wrapped and centered correctly. A harder synthetic case (a
  gradient-shaded bubble, the disclosed hard case) held up better than
  expected — a faint discontinuity is visible on close inspection where
  the original text was, but nothing close to the "visibly broken
  smudge" the scope predicted for non-uniform backgrounds. Both
  screenshots were reviewed by eye before writing this entry, not
  assumed correct from the code.
- **Dependency verification:** added `opencv-python-headless` and
  `numpy` to `requirements.txt`. Could NOT do a real end-to-end Docker
  build to confirm the deployed image imports `cv2` cleanly — this
  sandbox's network policy blocks Docker Hub's CDN outright (confirmed
  via the proxy's own status endpoint, not a guess), so `docker build`
  against the real `Dockerfile` failed at the base-image pull step, not
  something to route around. Fell back to the strongest verification
  available: `ldd` on the installed wheel's compiled extension shows
  every dependency is either bundled directly inside the package
  (`opencv_python_headless.libs/`) or a base-glibc/libstdc++ library
  present on any minimal Debian image (`libc`, `libstdc++`, `libz`,
  `libm`, `libpthread`, `libdl`, `libgcc_s`) — no `libGL`/`libglib`/
  `libSM`/X11 reference anywhere. Strong static evidence the Dockerfile
  needs no changes, genuinely checked rather than assumed, but not the
  same as a live build+run — the next real Railway deploy is the actual
  confirmation.
- **A real design fork, asked rather than silently picked:** whether to
  inpaint with a simple border-color heuristic fill (no new dependency)
  or real OpenCV inpainting (this dependency addition). Chose real
  inpainting, per direction.
- **What this does NOT do:** no frontend UI wiring at all yet — the
  comics workspace (`app/comics/page.tsx`) has no button or flow that
  calls this endpoint; it's backend-only this round, same as how the
  public API's backend landed before its dashboard UI did. No
  validation that a bbox region is actually a bubble versus SFX/other
  art — the caller is trusted to only send genuine bubble regions. No
  testing against a single real manga/webtoon panel — every visual
  check used a synthetic stand-in image.
- **Tier 0 for redraw quality** (a heuristic pipeline whose real-world
  performance on actual stylized comic art is genuinely unverified — the
  synthetic tests prove the mechanism works, not that it looks good on
  real lettering); **Tier 1** for the plumbing (deterministic
  clamping/wrapping/fitting logic, endpoint validation).
- **Benchmark coverage:** 16 new `tests/test_comics_redraw.py` tests
  (bbox clamping, text wrapping/font-fitting including the
  never-crashes-on-an-impossible-fit case, text-color estimation
  including the no-dark-pixels fallback, and full-pipeline tests
  proving the target region's pixels actually change while everything
  outside every region stays byte-identical) plus 6 new
  `tests/test_server.py` endpoint tests (base64 PNG response,
  malformed-JSON/missing-field/empty-region-list rejection, oversized
  image rejection, a genuine redraw failure surfacing as a 400) — 588
  Python tests total, up from 566.

## Comics redraw — frontend wiring — detail

- **What it is:** the comics panel workspace (`components/comics/
  PanelWorkspace.tsx`) now has a real "Redraw" section — one editable
  text box per detected OCR region, a "Redraw panel" button, and the
  composited result shown inline with a download link. New
  `lib/comicsRedraw.ts` (the `/api/comics/redraw` client call plus
  `resolveRedrawRegionText`, a pure function deciding what each box
  shows) and a new Next.js proxy route
  (`app/api/comics/redraw/route.ts`), same multipart-repackaging
  pattern as the existing OCR proxy.
- **The real design fork this round, resolved by asking rather than
  guessing:** `ComicPanel.adaptedText` is one string for the WHOLE
  panel (adaptation isn't per-bubble yet — a pre-existing, disclosed
  limitation), but a panel can have several detected OCR regions.
  There's no real mapping from one adapted paragraph to "which of 3
  bubbles." Two honest options existed: gate the feature to
  single-region panels only, or let a human fill in per-region text by
  hand for multi-region panels. Chose the latter — it's the same UI
  shape either way (a single-region panel just has one box, pre-filled
  from the existing `adaptedText`), it doesn't hard-block the common
  multi-bubble case, and it's the exact UI real per-bubble adaptation
  would need anyway once that eventually gets built, rather than a gate
  that would need tearing out later.
- **The actual rule, real and tested:** a region's box defaults to the
  panel's whole `adaptedText` ONLY when there's exactly one detected
  region (the one case the mapping is unambiguous); a multi-region
  panel's boxes start blank, never auto-split from the one adapted
  block. Only regions with non-empty text get sent to
  `/api/comics/redraw` — a human can redraw just the one bubble they've
  filled in, leaving others untouched, rather than being forced to fill
  in every region before redrawing any of it.
- **What this does NOT do:** no persistence of the redrawn result
  (matches the backend's own scope — a fresh redraw re-runs the whole
  pipeline, there's no id to fetch a past result by) and no CSV export
  of it either. No indication in the UI of which regions are
  bubbles vs. SFX — same caveat as the backend, the human is trusted to
  only fill in genuine bubble regions.
- **Tier 1** — deterministic UI/data-flow logic; the underlying redraw
  quality is whatever Scope B's own entry above already discloses
  (Tier 0).
  **Verified live:** a Chromium/Playwright pass against the production
  build with `/api/comics/ocr` and `/api/comics/redraw` both mocked —
  uploaded a panel, ran (mocked) OCR returning two regions, confirmed
  both redraw text boxes started genuinely blank (not silently
  pre-filled with a guess), typed text into only the second region,
  clicked "Redraw panel," and inspected the ACTUAL multipart payload
  sent to the endpoint — confirmed only region 2's bbox+text was
  included, region 1 correctly omitted — then confirmed the composited
  result image and download link both rendered. This was checked by
  reading the real captured request body and the rendered screenshot,
  not assumed from the code.
- **Benchmark coverage:** 6 new Vitest tests for
  `resolveRedrawRegionText` (single-region default-fill, multi-region
  never-guesses, human override wins, per-region independence, an
  explicit cleared-to-empty override sticking rather than silently
  repopulating, and the no-OCR-yet case) — 58 Vitest tests total, up
  from 52. `tsc --noEmit` and `next build` clean. 588 Python tests
  unchanged (backend untouched this round).

## Landing page: architecture diagrams + scroll motion — detail

- **What it is:** the first slice of the "premium landing page" redesign
  brief — the parts that were honestly buildable without fabricating
  capabilities (see the earlier conversation's pushback on the original
  brief's morphing-video hero, fake audio waveform switcher, invented
  ROI math, and working-looking cURL example for a dead endpoint — none
  of that shipped; this entry is only the real, honest pieces).
  - `components/ScrollReveal.tsx` — real scroll-triggered motion via
    IntersectionObserver, distinct from the pre-existing
    `.animate-fade-up` CSS class (which only ever plays once at mount,
    so content below the fold had already finished "animating" long
    before a scrolling visitor reached it — not a scroll reveal at all,
    just a page-load stagger). Fires once per section, respects
    `prefers-reduced-motion` the same way `AmbientGlow`'s drift
    animations already do.
  - `components/PipelineDiagramDark.tsx` (new, for `/music`) and
    `components/ComicsPipelineDiagram.tsx` (new, for `/comics`) — honest,
    dark, Vercel/Stripe-style architecture diagrams of the REAL
    pipelines. Music: Source lyrics → Translator → Creative Adapter →
    Judge → Verified output. Comics: Panel upload → OCR → Chapter DNA →
    Writers' Room → Adapted script — deliberately NOT the original
    brief's "OCR & Vision Agent → Adversarial Translation Pipeline →
    Typesetting Agent," which named two mechanisms that don't exist
    (there's no adversarial step, and typesetting/redraw is a separate,
    optional feature per-panel, not something every chapter runs
    through). The existing theme-adaptive `components/
    PipelineDiagram.tsx` (still used on `/alternate-homepage`) was left
    untouched rather than converted to dark-only, so that page doesn't
    break.
  - A new `.animate-travel-dot` CSS keyframe — a glowing dot traveling
    each diagram's connecting line, looping. Purely decorative
    "active engine" motion, explicitly documented in both diagram
    components as NOT a claim about real per-request telemetry —
    nothing here is wired to an actual request.
  - `/music`'s "How it works" section gained a new "Under the hood"
    block (the dark diagram, wrapped in `ScrollReveal`) below the
    existing feature cards. `/comics`' empty state (before any panels
    are uploaded) gained a matching dark "Under the hood" card —
    deliberately dark even though the rest of that page is light-themed,
    the same "a technical section can break the page's own theme for
    weight" pattern `PipelineDiagramDark` already established on
    `/music`.
- **What this does NOT do:** no hero-section rebuild yet (still the
  existing literal/adapted/why screenshot, not restyled), no
  glassmorphism/blur pass beyond what already existed, no persona-split
  toggle, no value-anchoring/ROI section, no API code-sample section —
  all deferred pieces from the original brief, not started this round.
- **Tier 1** — this is presentation/motion, no model-quality claim.
  **Verified live:** a real Chromium/Playwright pass scrolled to each
  new section on the production build and confirmed (via rendered
  screenshots, not assumed) that both diagrams render with correct
  stage labels and connecting-dot styling, and that `ScrollReveal`
  actually fires (opacity/translate resolved to visible) once scrolled
  into view rather than being invisible or still mid-transition.
- **Benchmark coverage:** no new automated tests — this is presentation
  layer with no non-trivial pure logic to unit test (`ScrollReveal`'s
  IntersectionObserver behavior isn't practically unit-testable in this
  project's jsdom-free Vitest harness); `tsc --noEmit`, `next build`,
  all 588 Python tests, and all 58 Vitest tests stayed green throughout.

### Hero section rework (`/music`)

- **What this builds:** `InputScreen.tsx`'s hero now renders as a two-column
  layout at `lg` breakpoints and wider (`components/InputScreen.tsx`) — the
  headline, language picker, and lyric form on the left, and the real
  literal/adapted/why comparison screenshot (a genuine captured render, not
  a mockup — see `ComparisonCard.tsx` and `scripts/capture-screenshots.mjs`)
  on the right with a neutral (non-accent-colored) glow behind it, so the
  page's one piece of real proof is visible without scrolling instead of
  only appearing several cards down in "How it works." Below `lg`, it
  collapses to the original single centered column with the screenshot
  underneath, unchanged. The now-duplicate first "How it works" card
  (same screenshot) was removed, leaving that grid with 2 cards.
- **Bug fixed alongside this:** `scripts/capture-screenshots.mjs` was the
  one file the earlier AURA→Castia rename missed (its `.mjs` extension
  wasn't in that rename's file-scan patterns). It referenced the old
  `AURA_ENGINE_API_URL` env var and captured the hero/language-chip
  screenshots against `/`, which used to be `InputScreen`'s route but is
  now the music-vs-webtoons chooser (`InputScreen` moved to `/music`).
  Fixed both, then re-ran the script against a real build to regenerate
  `hero.png`, `language-chips.png`, `comparison-card.png`, and
  `dashboard-workspace.png` — the previous `comparison-card.png` still
  had "AURA" baked into its pixels from before the rename, which the
  hero rework made far more visually prominent.
- **What this does NOT do:** no glassmorphism/blur pass, no
  value-anchoring/ROI section, no API code-sample section — still
  deferred (persona-split toggle below is now done).
- **Tier 1** — presentation only, no model-quality claim.
  **Verified live:** `tsc --noEmit`, `next build` (clean, `/music` at
  5.31 kB), and all 58 Vitest tests stayed green. A real Chromium/
  Playwright pass against a production build captured and visually
  confirmed desktop (1440px), tablet (800px), and mobile (390px)
  renders — correct two-column layout above `lg`, correct single-column
  stacking below it, and the regenerated screenshot correctly reading
  "CASTIA" instead of the stale "AURA."
- **Benchmark coverage:** no new automated tests — this is presentation
  layout with no non-trivial pure logic to unit test.

### Persona-split toggle (`/music`)

- **What this builds:** a two-option pill toggle ("Adapting a song I love" /
  "Adapting my own lyrics") above the hero headline in `InputScreen.tsx`,
  swapping only the headline copy between a fan framing ("Adapt the
  feeling. Not just the words.") and a creator/songwriter framing ("Adapt
  your lyrics. Keep what makes them yours."). Chosen deliberately over
  "Individual vs. Team/Label," which would have implied seat management or
  catalog features that don't exist in this product yet — Fans vs.
  Creators is the one split that's true of what's already shipped, since
  the tool already serves both identically with no gating.
- **What stays untouched:** the language-aware line below the headline
  (`sourceHintFor`, real functional copy about which languages/direction
  are supported) does not change with persona — it's information, not
  framing. The pipeline, form, submit flow, and everything below the hero
  are identical regardless of which persona is selected; nothing is
  gated or reordered.
- **What this does NOT do:** the choice isn't persisted (no localStorage,
  no cookie) — it's presentation state for this page view only, since
  there's no real per-persona backend behavior to remember yet. No
  A/B measurement is wired up; this is copy, not an experiment.
- **Tier 1** — presentation only, no model-quality claim.
  **Verified live:** `tsc --noEmit`, `next build`, all 58 Vitest tests
  green. A real Chromium/Playwright pass against the production build
  clicked both toggle states and confirmed (via `innerText`, then via
  rendered screenshots) that the headline actually swaps and swaps back,
  and that the longer creator headline doesn't clip or overlap the
  language hint below it.
- **Benchmark coverage:** no new automated tests — a static copy lookup
  keyed by two string literals, with the actual click behavior confirmed
  live above.

### SEO + GEO foundation (marketing pages, metadata, structured data)

- **What this builds:**
  - `lib/seo.ts` — `SITE_URL` (`https://usecastia.com`, decided domain,
    wired in ahead of DNS/deploy the same way you address an envelope
    before the recipient moves in), `absoluteUrl`.
  - Root `layout.tsx`: `metadataBase`, a title template (`%s | Castia`)
    so every page gets a unique, non-duplicate `<title>` instead of all
    inheriting one generic string, default OG/Twitter card metadata, and
    two site-wide JSON-LD blocks — `Organization` (name, url, logo) and
    `SoftwareApplication` (real category/description, an `Offer` for the
    Free tier's actual $0 price). Deliberately no `aggregateRating` (no
    real reviews exist) and no priced `Offer` for the Creator tier
    (billing isn't live per `/pricing`) — schema states only what's true.
  - `app/opengraph-image.tsx` — a real image rendered via `next/og`
    `ImageResponse` at request time from the site's own brand colors
    (`tailwind.config.ts`), not a fabricated mockup or AI-generated
    graphic. `app/apple-icon.tsx` and `app/logo/route.tsx` (512×512, for
    the Organization schema's `logo` field) follow the same pattern.
    `app/icon.tsx`'s mark was fixed from a stale "A" to "C" — a rename
    leftover.
  - `app/robots.ts` — allows `*` plus explicit rules for GPTBot,
    ChatGPT-User, Google-Extended, PerplexityBot, ClaudeBot, anthropic-ai,
    CCBot (the actual mechanism behind being citable by AI answer
    engines is these crawlers being able to fetch the site at all);
    disallows `/dashboard`, `/api`, `/sign-in`. `app/sitemap.ts` lists
    only real indexable routes.
  - `public/llms.txt` — a plain-markdown site summary per the emerging
    llms.txt convention, written for LLM/answer-engine consumption:
    what Castia is, the real pipeline, key pages, and explicit
    "notes for citation" disclosing Beta/early-access status honestly
    rather than letting a citing model overstate maturity.
  - Per-route metadata: `app/music/layout.tsx`, `app/comics/layout.tsx`
    (real descriptions, canonical URLs), `app/dashboard/layout.tsx`
    (`noindex` — private, personalized, no SEO value), `/sign-in` and
    `/alternate-homepage` (`noindex`), `/pricing` (canonical added).
  - Two new real content pages: `/faq` (real Q&A, `FAQPage` JSON-LD
    whose entries are copied verbatim from the visible text — no hidden
    markup) and `/how-it-works` (long-form Translator → Creative Adapter
    → Judge explanation for both music and comics, reusing the existing
    `PipelineDiagramDark`/`ComicsPipelineDiagram` components).
  - `components/Footer.tsx` — real internal links only (Music, Webtoons,
    How it works, FAQ, Pricing, API), added to every marketing page
    (`/`, `/music`, `/comics`, `/pricing`, `/faq`, `/how-it-works`) but
    not `/dashboard/*` or `/sign-in`.
- **What this does NOT do:** no fabricated reviews/ratings, no priced
  offer for a tier that isn't billed yet, no invented traffic/ranking
  claims anywhere in this round's content or schema. No blog, no
  location/local-business schema (not applicable), no hreflang
  (single-locale site today).
- **Tier 1** — this is discoverability infrastructure, no model-quality
  claim. **Verified live:** `tsc --noEmit`, `next build` (all new routes
  compiled: `/faq`, `/how-it-works`, `/robots.txt`, `/sitemap.xml`,
  `/opengraph-image`, `/logo`, `/apple-icon`), all 58 Vitest and all 588
  Python tests green. A real Chromium/Playwright pass against the
  production build confirmed: per-page `<title>`/canonical tags resolve
  correctly (checked via raw HTML, e.g. `/faq` → `FAQ | Castia` +
  `canonical href="https://usecastia.com/faq"`), exactly 3 JSON-LD
  `<script>` tags render on `/faq` (Organization, SoftwareApplication,
  FAQPage) with content matching the page's visible text, and both new
  pages plus the Footer on `/`, `/music`, and `/comics` render correctly
  (screenshots reviewed, not assumed).
- **Benchmark coverage:** no new automated tests — this is metadata/
  markup/content with no non-trivial pure logic; correctness was
  verified live instead (build succeeding + raw-HTML/JSON-LD inspection
  + rendered screenshots).

### Comics OCR latency pass (token cache, upload downscale, batch runs)

Three independent causes of "OCR is slow," fixed together. None of them
changes OCR *quality* — this is purely about the time and payload spent
getting the same result.

- **Cached OAuth token** (`engine/comics_ocr.py`). Every OCR call used to
  perform a full service-account token exchange with Google *before* the
  Vision call — the previous code said so in its own comment ("a real,
  deferred optimization, not an oversight"). Now cached module-level,
  keyed by a SHA-256 of the credential env var so rotating the key
  invalidates the cache rather than serving a token minted from the old
  one, refreshed 5 minutes before stated expiry, and refreshed while
  holding the lock so a cold cache produces one exchange rather than a
  thundering herd of identical ones. Falls back to a 55-minute TTL when
  the credentials object reports no expiry; a naive `expiry` datetime is
  pinned to UTC (which is what google-auth actually returns) rather than
  read as local time.
- **Client-side downscale before upload** (`web/lib/imageDownscale.ts`,
  wired into `lib/comicsOcr.ts`). Panels are downscaled to a 2000px long
  edge and re-encoded as JPEG before upload. **Critically**, the returned
  bboxes are scaled back into the ORIGINAL image's pixel space
  (`rescaleRegions`) — `PanelWorkspace.tsx` positions its overlay by
  dividing bbox by the *displayed original's* `naturalWidth`, and the
  redraw action sends the *original* file with those same boxes, so
  returning boxes measured on a smaller image would have silently
  misaligned the overlay and made redraw inpaint over artwork. Returns
  the untouched original whenever resizing isn't possible (no
  `createImageBitmap`, unreadable image, failed encode) or wouldn't help
  (already small; re-encode came out larger than the source) — an
  optimization that can fail a request outright would be a bug.
- **Batch "Run OCR on all panels"** (`web/lib/concurrency.ts`, wired into
  `app/comics/page.tsx`). OCR was previously one manual button click per
  panel, each a full sequential round trip — a 30-panel chapter meant 30
  clicks and 30 serial waits. Now one action runs the unread panels 4 at
  a time, via a shared-cursor worker pool (not fixed chunks, so one slow
  panel doesn't stall three idle workers). Never rejects: a failing panel
  records its own error and the rest of the batch continues. Skips panels
  already read rather than re-sending them — each Vision call is real and
  metered, and re-running would discard OCR text a human may have edited.
- **What this does NOT do:** does not change OCR accuracy, does not
  address Cloud Vision's known weakness on stylized comic lettering, and
  does not add speaker identification or dialogue-vs-SFX classification
  (all of which need a vision-LLM pass — deliberately scoped as separate
  future work, since it *adds* latency rather than removing it).
- **Tier 1** — deterministic infrastructure, no model-quality claim.
  **Verified live, end to end:** a real Chromium/Playwright run against a
  production build, with the engine proxy pointed at a local stand-in
  that recorded exactly what the browser uploaded, confirmed a 3000×2200
  PNG (3.33 MB) arriving as a 2000×1467 JPEG (779 KB) — a 77% payload
  reduction — while the rendered region overlay read `left: 25%`
  (= 750/3000), proving the bbox was mapped back into original-image
  coordinates rather than left in the downscaled space (an un-rescaled
  box would have read 16.67%). All three panels dispatched within 26 ms
  of one click, confirming real concurrency rather than serial runs. An
  earlier attempt with flat synthetic white panels correctly did *not*
  downscale — PNG compressed them below the JPEG re-encode, tripping the
  "don't make it bigger" guard — which is why the check was redone with
  realistically-compressible art.
- **Benchmark coverage:** 21 new tests (12 Vitest for the downscale/
  rescale maths including a round-trip pixel-accuracy invariant, 9 Vitest
  for the concurrency pool, 7 pytest for the token cache). The token-cache
  tests were falsified before being trusted: with the cache path disabled,
  8 concurrent callers produced 8 separate exchanges instead of 1 and the
  suite failed as intended. Full suite green — 79 Vitest, 595 pytest,
  `tsc --noEmit` and `next build` clean.

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
