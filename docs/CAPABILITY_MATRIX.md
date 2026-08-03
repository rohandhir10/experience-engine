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
repeat (that fix held), but the shipped Japanese Aura output was ~20
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
- **`server/main.py::MAX_CONCURRENT_RUNS`** (new, `AURA_MAX_CONCURRENT_
  RUNS` env var, default 4): a `threading.Semaphore` around the actual
  engine run, so at most N background jobs run at once regardless of how
  many `/api/adapt/start` requests arrive simultaneously — the rest
  queue behind the semaphore rather than all hitting the LLM provider at
  once. The number itself is a starting guess, not a measured ceiling.
- **`server/db.py`**: explicit `pool_size`/`max_overflow` (via
  `AURA_DB_POOL_SIZE`/`AURA_DB_MAX_OVERFLOW`, defaulting to 10/10)
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
  fresh `openai.OpenAI` client (and its own `httpx` connection pool) is
  constructed on every `create_default_client()` call, i.e. twice per
  adaptation request. Under high concurrency this multiplies socket/file-
  descriptor usage instead of reusing keep-alive connections across
  requests. Not fixed here — would need a shared, thread-safe client
  instance rather than the current per-request construction, and that's
  a real behavior change to code this session didn't otherwise touch.
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
- **Alembic / real migrations** — see finding 6 above.

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
