# Korean benchmark corpus

What to collect before Korean can be called supported. The corpus itself
is not in the repo — lyrics are copyrighted, and `benchmark/.gitignore`
excludes run data. This is the spec for building it locally.

## Size and the held-out split

**12 songs minimum**, split before any prompt work:

- **8 tuning songs** — used while iterating on the profile.
- **4 held-out songs** — never looked at until the final run. The
  pre-registered criterion (`docs/WRITERS_ROOM_V1.md` §9.5) requires
  replication on songs never used to tune a prompt, and that only means
  anything if the split happens first.

## Coverage the 12 must hit

The Korean profile makes specific claims. Each needs at least one song
that would expose it if the claim is wrong:

| Must cover | Why | Songs |
|---|---|---|
| Ballad with a climactic outpouring | The profile says restraint is the norm *except* here. A corpus of only restrained songs would never catch an over-restrained ballad. | 2 |
| Idol pop with heavy English code-mixing | Tests whether English hooks are treated as native register rather than as code-switching for effect. | 2 |
| Hip-hop verse with dense end rhyme | Tests the "rhyme is a borrowed device here" claim. | 1 |
| Trot | Retro/sentimental register that reads differently to younger listeners; tests genre identification. | 1 |
| Ideophone-heavy lyric (반짝반짝, 두근두근) | The largest artistic gap the audit found. Needs its own coverage. | 2 |
| Speech-level shift mid-song (존댓말 → 반말) | Tests the compensation machinery on the feature English most completely erases. | 1 |
| Song using 한 or 정 substantively | Tests the cultural-anchor disposition logic. | 1 |
| Digits or numerals in the lyric | Tests the Sino-Korean counting fix. | 1 |
| Sparse, restrained lyric | The counterweight case: adaptation floor must not push it into over-writing. | 1 |

## Baselines to collect per song

Per `benchmark/systems.py`, CASTIA and the two single-prompt baselines run
automatically. Two need manual collection into
`benchmark/manual/<song_id>/`:

- **Official English lyrics** where the label released them — the
  strongest available human baseline, and common for K-pop.
- **Fan translations** from a lyric site, as the equivalent of the
  Bollynook/FilmyQuotes comparison used for Hindi.

Google Translate runs automatically but should be spot-checked, since
its Korean output is a genuinely strong MT baseline — better than its
Hindi output — so this is a harder comparison than the Hindi benchmark.

## Reviewers

**3 minimum, and the qualification bar matters more than the count.**

Required:
- **Genuinely bilingual**, not heritage-familiar. The specific failure to
  catch is over-explaining — an English version that names a feeling the
  Korean reached through an image. A reviewer who reads Korean slowly
  will rate the explained version *higher* because it is easier, which
  inverts the measurement.
- **Fluent in the genre.** Trot and idol pop have opposite registers; a
  reviewer who only knows K-pop will misjudge a trot adaptation.
- **Not recruited from people invested in the project.** The earlier
  informal check (a friend and a family member) is not a substitute for
  this, and its result should not be counted.

Ideal additions, if reachable: someone who writes or translates lyrics
professionally, and at least one reviewer over 40 for the trot and
ballad material, where generational register differs sharply.

## What "production ready" means for Korean

All four conditions, not a subset:

1. Beats Google Translate and single-prompt GPT/Claude on **artistic
   fidelity** across the corpus.
2. Holds that result on the 4 held-out songs.
3. No song trips the adaptation floor (`engine/verify.py`) — i.e. it is
   not passing by quietly reverting to literal translation.
4. Native reviewers confirm the ideophone and speech-level handling
   specifically, since those are the two claims the profile makes most
   strongly and the two an English-only reader cannot check.
