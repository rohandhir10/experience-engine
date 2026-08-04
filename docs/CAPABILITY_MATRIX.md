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
  `{id, plan}`; that id is stashed in the token as `auraUserId` and
  travels with every subsequent request.
- **Trust model (`server/main.py`).** The engine API is a separate
  service on Railway — it never sees the Google sign-in, so it cannot
  verify a user id on its own. `AURA_INTERNAL_API_SECRET` is a shared
  secret known only to the Next.js server (the party that *did* verify
  the sign-in). `_authed_user_id()` honors a forwarded `X-Aura-User-Id`
  **only** when paired with the correct `X-Aura-Internal-Secret`;
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
  `AURA_INTERNAL_API_SECRET` → sign-in still works, history silently
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
  `AURA_INTERNAL_API_SECRET` (must match on both services).
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
  Translate / GPT single-prompt / AURA" three-way comparison view built
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
  reference's cards are real product screenshots. AURA has no
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
  and were fixed by hand: `ComparisonCard.tsx`'s "AURA" pill (dropped a
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

The first piece of a deliberate second product surface (`AURA Comics`,
alongside `AURA Music`), on the strategy that both front ends can share
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
