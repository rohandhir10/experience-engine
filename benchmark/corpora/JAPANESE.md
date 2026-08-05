# Japanese benchmark corpus

What to collect before Japanese can be called supported. The corpus
itself is not in the repo — lyrics are copyrighted, and
`benchmark/.gitignore` excludes collected corpora. This is the spec for
building it locally, and the companion to `KOREAN.md`.

Every row in the coverage table below exists because the Japanese
language profile (`engine/language_profile.py`, resolved via
`resolve_profile("ja")`) makes a specific claim. A corpus that cannot
falsify a claim cannot support it either.

## Size and the held-out split

**12 songs minimum**, split before any prompt work:

- **8 tuning songs** — used while iterating on the profile.
- **4 held-out songs** — never looked at until the final run. The
  pre-registered criterion (`docs/WRITERS_ROOM_V1.md` §9.5) requires
  replication on songs never used to tune a prompt, and that only means
  anything if the split happens first.

One song can satisfy several rows below, which is how 12 songs cover 12
criteria. Do not stretch a song to claim a row it only weakly exhibits —
a criterion covered by a song that barely demonstrates it is worse than
an honestly missing row, because it looks covered in the report.

## Coverage the 12 must hit

| Must cover | The profile claim it tests | Songs |
|---|---|---|
| Lyric that reaches feeling through an image, season or physical detail, never naming it | The profile calls this "the most important calibration for Japanese, and the one an English-trained model gets wrong by default" — rendering 桜 falling as a statement about grief is explanation, not translation. Without this the central claim is untested. | 2 |
| Enka (演歌) | The profile says enka is openly direct — an explicit *exception* to Japanese restraint. A corpus of only understated songs would never catch restraint wrongly imposed on a song that states its feeling outright. | 2 |
| J-pop ballad that breaks into a direct climactic chorus | The other stated exception. Tests that the engine matches the source's strategy rather than a stereotype of Japanese restraint. | 1 |
| City pop | "Urbane and often melancholy under a bright surface" — the opposite emotional strategy to enka. Tests genre identification, not just genre naming. | 1 |
| Vocaloid / net music | Dense, fast, syllable-packed writing is the idiom. Tests mora grounding under extreme density, where a comfortable English line cannot fit. | 1 |
| A lyric running several lines with no stated subject | The largest structural trap listed. English forces a subject; supplying the wrong one silently invents a narrative, and the source's refusal to specify may itself be the effect. | 2 |
| A distinctive first-person pronoun (僕 / 俺 / あたし / わたくし) | Characterization, not grammar — English "I" erases it completely. Tests whether the loss is at least noted. | 1 |
| Sentence-final particles carrying stance (ね / よ / な / かな / わ) | Untranslatable as words, and they vanish silently. Tests whether their loss is flagged rather than ignored. | 1 |
| Script used as register — a native word in katakana, or hiragana where kanji is normal | The profile calls script choice tonal. English has no direct equivalent, so the only correct behaviour is to flag it. | 1 |
| Seasonal reference / kigo used substantively | Tests `symbol_calibration` in the *negative* direction: these are commonplaces within the tradition, and marking them as culturally specific mis-routes the Cultural Historian. A false positive here is the failure. | 1 |
| A song using 切ない or 懐かしい as a load-bearing word | Both are in the anchor lexicon with `target_recognizability: none`. Tests the cultural-anchor disposition logic on words English genuinely lacks. | 1 |
| J-pop or hip-hop using deliberate end rhyme | The profile says rhyme is a consciously borrowed English device here and should read as borrowed. Tests that its presence is not mistaken for native form — and that its *absence* elsewhere is not read as formlessness. | 1 |

## Baselines to collect per song

Per `benchmark/systems.py`, Castia and the two single-prompt baselines
run automatically. Two need manual collection into
`benchmark/manual/<song_id>/`:

- **Official English lyrics** where the label released them — common for
  anime tie-up songs with international releases, rarer for enka.
- **Fan translations** from a lyric site, the equivalent of the
  Bollynook/FilmyQuotes comparison used for Hindi.

Google Translate runs automatically. Spot-check it: its Japanese output
is a strong MT baseline, and — as with Korean — this makes for a harder
comparison than the Hindi benchmark, not an easier one.

## Reviewers

**3 minimum, and the qualification bar matters more than the count.**

Required:

- **Genuinely bilingual**, not heritage-familiar. The specific failure to
  catch is over-explaining: an English version that names a feeling the
  Japanese reached through an image. A reviewer reading Japanese slowly
  will rate the explained version *higher* because it is easier to
  parse, which inverts the measurement.
- **Fluent in the genre.** Enka and Vocaloid have opposite registers and
  opposite audiences; a reviewer who only knows anime tie-up songs will
  misjudge an enka adaptation as overwrought when it is accurate.
- **Able to read script choice as tone.** A reviewer who does not notice
  that a word was written in katakana cannot judge whether losing that
  mattered.

## Where to put it

The corpus lives outside the repo. `benchmark/.gitignore` excludes
`corpora/*.json`, so a collected corpus placed here stays local:

```
benchmark/corpora/ja_pilot/     # local only, never committed
  001_<slug>.json
  ...
```

Check it before spending money on a run:

```bash
python -m benchmark.cli validate --corpus benchmark/corpora/ja_pilot
```

That reports malformed files, fragments, and — the one that actually
bites — a song whose text is not in the script its `source_language`
claims, which is how a mislabelled or already-translated file gets into
a corpus unnoticed.
