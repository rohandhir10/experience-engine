# Production Workflow — Emotionally Translated Lyric Videos

**Internal engine, not a public product. Goal: one exceptional video a day,
across Hindi, Japanese, Korean, Arabic, Russian, Spanish → English.**

Status: Operating workflow design. No code, no infrastructure — this is
the editorial/production process a small creative team runs, with AI doing
specific drafting work inside it and humans holding every quality and
judgment gate.

---

## 0. The decision that has to be made before Stage 1 exists

This channel publishes to YouTube. "Internal tool" describes who *runs*
the pipeline, not who *sees* the output — the moment a video is published,
it's public, and everything downstream of that (rights, Content ID,
takedowns) is a real constraint on what "song selection" is even allowed to
mean. This has to be decided once, up front, because it determines whether
Stage 1 is "pick any song we love" or "pick from a cleared catalog":

- **Option A — Licensed instrumental/backing tracks + original vocal
  performance rights**, or original visuals over a properly licensed sync.
  Slowest to start, safest long-term, and it's the only option compatible
  with a real ad-revenue business later.
- **Option B — Publish over the original master and accept Content ID.**
  Most rights holders monetize-and-allow rather than take down lyric-style
  fan content, but "accept" has to be a deliberate choice, not a default —
  it means some videos will get claimed, occasionally muted or blocked in
  some territories, and the channel does not fully own its own monetization
  on day one.
- **Option C — Start on public-domain or explicitly CC-licensed songs and
  independent/emerging artists who want the exposure**, proving the format
  and the workflow before touching major-label catalog at all.

**Recommendation:** start on Option C for the first 2–3 weeks purely to
de-risk and pressure-test the *workflow* (this document) without a legal
variable in the mix, then move deliberately into Option B for the songs
that actually need to be made (the culturally rich, emotionally loaded
ones the mission is actually about), with a standing relationship (even
informal) with the artist/label wherever the channel wants to make one of
their songs a signature video. This is a call only you can make, but the
workflow below assumes *some* answer has been chosen before Stage 1 begins,
because Stage 1's selection criteria depend on it.

---

## 1. Song Selection

**Purpose.** Choose the one song that best proves the mission on a given
day — not the most popular song, the song where the gap between "what a
literal translation gives you" and "what a native speaker actually feels"
is largest. That gap *is* the product.

**Who does it.** A rotating "language desk" — one native/bilingual person
per target language (can be a part-time contractor, does not need to be
full-time) proposes 2–3 candidates a week from their language; the creative
lead makes the final call across all six.

**Selection criteria (in order of importance):**
1. **Emotional/cultural distinctiveness** — does this song carry a feeling
   or concept that genuinely resists literal translation (han in Korean,
   saudade-adjacent longing in Russian romanticism, a specific Bollywood
   emotional convention, a classical Arabic poetic device, Japanese mono no
   aware, a Spanish-language machismo/romantic trope)? If a song translates
   fine literally, it's not a good use of a production day.
2. **Existing translation gap** — check what's already out there (fan
   subtitles, official lyric videos). If the existing English versions are
   flat or literal, that's the opportunity. If a beautiful English
   rendering already exists and is popular, skip it — no reason to compete
   with something already good.
3. **Crossover potential** — does the song have *any* existing English-
   speaking audience awareness (K-pop/Bollywood crossover fans, film
   soundtrack recognition, viral moment) to seed initial discovery, without
   this being the primary criterion (the mission is emotional fidelity, not
   chasing trends).
4. **Rights feasibility** under whichever option was chosen in §0.

**Cadence.** Run this as a **weekly batch**, not a daily scramble: pick 5–7
songs a week ahead of time. Decoupling selection from the daily production
deadline is what protects criterion 1 from being quietly replaced by
"whatever's easiest to clear this morning."

**Output:** a one-page brief per selected song — title, artist, source
language, the specific emotional/cultural thing this video needs to
capture, and why a literal translation would fail it. This brief is the
north star every later stage gets checked against.

---

## 2. Rights Clearance

**Purpose.** Confirm the specific song is actually usable under the Stage
0 policy before any creative work is spent on it — creative effort is the
expensive resource here, not clearance-checking.

**Who does it.** Whoever owns rights logistics (can be the creative lead
initially, a dedicated ops contractor once volume justifies it).

**Output:** a cleared audio asset (or explicit "proceed and accept Content
ID" decision, logged) attached to the Stage 1 brief. If a song fails
clearance, it goes back to the weekly shortlist as a candidate for a
different rights path, not discarded — some of the best songs for this
mission (deeply culturally specific ones) may be from artists worth
building a direct relationship with specifically because they're hard to
clear generically.

---

## 3. Source Understanding Pass

**Purpose.** Before a single English word is written, establish — line by
line — what the original is actually doing: literal meaning, emotional
core, cultural load, and what has to survive no matter what changes. This
is the step that makes everything after it "emotional re-expression"
instead of "translation with extra steps," and it is the one stage where a
human native speaker is non-negotiable, not optional.

**Who does it.** The language-desk native speaker for that song's language,
working *with* AI, not replaced by it: AI drafts a structured understanding
pass for every line (literal gist, emotional core, cultural context, what
must survive — the same shape of note validated in the feasibility
experiment design), and the native speaker corrects it. AI will
systematically miss or flatten register, dialect, generational slang,
irony, and culturally loaded connotation that a native speaker catches
immediately — this review is where quality is actually won or lost for the
hardest, most-worth-doing songs.

**Time budget.** 20–30 minutes per song for an experienced reviewer,
correcting an AI-generated first pass rather than writing one from
scratch — this is what makes daily cadence realistic at all.

**Output:** a reviewed, line-by-line understanding sheet for the whole
song, signed off by the native reviewer.

---

## 4. Emotional Re-Expression (English Draft)

**Purpose.** Generate English lines from the understanding sheet — never
from the original lyric text directly. Multiple candidates per line, not
one, because there is rarely a single correct emotional rendering.

**Who does it.** AI generates; nobody signs off yet — this stage produces
raw material for Stage 5, not a finished product.

**What "good" means here**, stated explicitly so drafts can be judged
against something concrete:
- Reads as something a native English speaker would actually write or say,
  not as translated language.
- Matches the line's role in the song (a hook line needs to hit like a
  hook; a bridge's quiet devastation should stay quiet).
- Roughly matches the original line's pacing/length, since this has to sit
  on screen in sync with the music, not just read well on a page.

**Output:** 3–5 candidate English lines per original line, tagged with
which part of the emotional core each candidate leans into (useful for
Stage 5 — makes tradeoffs visible instead of having to be re-derived by
reading each candidate cold).

---

## 5. Creative Selection & Line Editing

**Purpose.** This is the single highest-leverage human gate in the whole
pipeline, and the one that actually determines whether the channel is
"the best" or merely "pretty good." A person with taste picks, edits, and
stitches candidates into one coherent English lyric for the whole song.

**Who does it.** The creative lead (you, initially — this is the role that
should not be delegated early, because it's where the brand's quality bar
actually lives and gets calibrated. Delegate it only once there's a written
style guide, built from your own decisions, precise enough for someone else
to apply consistently).

**What this stage does that Stage 4 cannot:**
- **Whole-song coherence** — a consistent voice across the song, motifs
  introduced early paid off consistently later, no line that's individually
  good but breaks the song's emotional arc.
- **The final tradeoff calls** Stage 4 can only flag, not make — literal
  accuracy vs. emotional truth, elegance vs. clarity, when to lean into an
  English idiom vs. when to let something sit slightly unfamiliar because
  that unfamiliarity *is* the point (an "untranslatable" concept rendered
  with a little productive friction can be more honest than smoothing it
  into a false English equivalent).
- **Deciding on the channel's signature move, if any** — e.g., an
  occasional one-line on-screen annotation for a genuinely untranslatable
  concept ("This word has no direct English equivalent — it means...").
  Used sparingly, this can become the thing viewers specifically associate
  with the channel; used on every video, it becomes a crutch and a tell
  that the English line itself didn't work.

**Time budget.** 45–60 minutes per song. This is deliberately the longest
human stage in the pipeline — protect it, don't compress it to hit a
deadline.

**Output:** the final English lyric script, one line per original line,
ready for timing.

---

## 6. Timing & Sync

**Purpose.** Attach a start/end timestamp to every finalized English line
so it appears on screen in sync with the song.

**Who does it.** AI-assisted alignment against the original vocal track
(forced alignment tooling gives a first-pass timing), corrected by a human
for on-screen readability — sung timing and comfortable reading timing are
not the same thing; a line that's sung in 1.5 seconds may need to sit on
screen for 2.5 for a reader to actually take it in, especially for longer
English renderings of shorter-sounding original lines.

**Output:** a timed lyric track — line, start time, end time.

---

## 7. Visual Direction

**Purpose.** The visual treatment should reflect the *emotional register*
of the specific song, not be a single generic template applied to
everything — a grief-coded ballad and a defiant anthem should not look and
move the same way, even on the same channel.

**Who does it.** A visual producer role (can be the same person wearing a
different hat early on), working from a **flexible template system**: a
consistent brand frame (channel identity, typography family, title-card
style) with a small set of *variable* parameters per song — color
palette, background motion/footage tone, pacing of visual cuts — chosen to
match the Stage 3 emotional brief.

**Why a template system, not fully bespoke direction per video.** Fully
custom visual direction for every video is not sustainable at daily
cadence and risks becoming the bottleneck instead of Stage 5. A well-built
template system gives enough variation to avoid feeling generic while
keeping this stage fast — this is the right place in the pipeline to trade
some bespoke-ness for throughput, precisely because it isn't where the
channel's actual differentiation lives (the English lyric is).

**Output:** a chosen visual style + assets for this specific song.

---

## 8. Video Assembly

**Purpose.** Combine the timed lyric track, the audio, and the visual
assets into one finished video file, plus branded intro/outro and any
Stage 5 annotation callouts.

**Who does it.** Visual producer, using the template system from Stage 7 —
this stage should be mechanical once Stages 3–7 are done well; if it isn't,
that's a signal the template system needs more investment, not that this
stage needs more manual craft per video.

**Output:** rendered video file, ready for review.

---

## 9. Quality Review Gate

**Purpose.** A final check against the Stage 1 brief before anything goes
out, run by someone other than whoever did Stage 5 — a second set of eyes
catches what the person closest to a piece of work stops seeing.

**Checklist:**
- Does this still feel like the emotional/cultural thing the Stage 1 brief
  identified, or did something get smoothed away in editing?
- Sync accuracy — does every line land and clear in time with the music?
- Any residual "translation-ese" — a line that's technically fine but
  reads like it was translated, not written?
- Brand/visual consistency with the template system.
- Rights sign-off from Stage 2 still attached.

**The cheapest, highest-signal version of this check**: before publishing,
show the finished video (or just the English lyric script) to one
bilingual native speaker who wasn't involved in making it, and ask one
question — "does this feel like experiencing the song, or like reading a
translation?" This is the same instrument validated in the feasibility
experiment, repurposed as an ongoing production QA step rather than a
one-time research measurement. If a native reviewer says "this reads like
a translation," that is a stop-ship signal, not a nitpick.

---

## 10. Metadata & Publishing Package

**Purpose.** The English title is often the hardest single piece of
writing in the whole video, and it's frequently under-invested relative to
the lyric itself: it's the one line seen before anyone commits to
watching, and it has to carry the emotional hook, not just describe the
song ("[Song] — English Lyrics" is a wasted title for a channel whose
entire premise is emotional fidelity).

**What gets produced per video:**
- **Title** — emotionally evocative, ideally drawn from the strongest line
  in the final English lyric, not a generic "translation" label.
- **Description** — brief cultural/emotional context (what this song means
  to native listeners, what the title phrase is drawing from) — this
  doubles as a differentiator from generic lyric-video channels and as
  genuine SEO value, since it's content nobody else is writing.
- **Thumbnail** — a still that signals feeling, not a generic karaoke-style
  lyric-video thumbnail.

---

## 11. Publish & Feedback Loop

**Purpose.** The comment section on a channel like this is a free,
continuously-running version of the bilingual-judge panel from the
feasibility experiment — native speakers will say, unprompted, whether a
line "hit different" or missed. Treat this as data, not just engagement.

**What to actually track per video, deliberately kept simple:**
- Retention/watch-time curve — where do people drop off (often points to a
  specific line or pacing problem, not the whole video).
- Native-speaker comments specifically — flag and log anything a bilingual
  commenter says about accuracy/feeling, positive or negative.
- Which song *categories* (per the Stage 1 criteria) actually perform, to
  refine selection criteria over time rather than guessing.

**Feed this back into a living style guide** — not a static document
written once, but one that accumulates specific rulings ("we decided X
type of line should always keep the original word with a gloss, not
translate it," "songs with Y emotional register get the slow-cut visual
treatment") as the team actually makes these calls. This is what lets
Stage 5 eventually be delegated without losing the quality bar: the guide
*is* the transferable form of your taste.

---

## 12. Cadence: Getting to "One a Day" Without Breaking Quality

**Do not start at daily cadence.** Start at 2–3 videos a week for the
first several weeks, specifically to let Stages 3–8 become fast and
reliable *before* committing to a publishing cadence the team has to hit
regardless of quality that day. A missed daily upload is recoverable; a
channel known for its emotional fidelity publishing something flat because
it had to ship today is not — the entire premise is quality, so cadence
must never be allowed to outrank it.

**How daily eventually becomes sustainable, once the workflow is proven:**
- Stage 1–2 (selection, clearance) run a week ahead in batches — never a
  same-day activity.
- Stage 3–4 (AI-assisted understanding + draft generation) can run the day
  before production, so Stage 5 always starts with material already in
  hand.
- Stage 5 (creative edit) stays human and stays time-boxed — this is the
  stage that determines whether daily cadence is actually achievable, since
  every other stage can be batched or templated around it.
- Stage 6–8 become increasingly templated/tool-assisted as the visual
  system and timing-alignment process mature — this is future engineering
  investment, not a Phase 1 requirement, and should only be built once the
  editorial workflow above has been run by hand enough times to know
  exactly what needs to be fast.

**Team shape for Phase 1** (roles, not necessarily distinct people):
- **Creative Lead** — you. Owns Stage 1 final calls and all of Stage 5.
  This is the job that defines the channel; do not outsource it early.
- **Language Desk** (one native/bilingual contact per target language) —
  part-time, feeds Stage 1 candidates and does Stage 3 review.
- **Visual/Production** — one person owning Stages 6–8 and the template
  system.
- **(Later) Community/Data** — someone watching Stage 11's feedback loop
  once volume makes that a real job rather than five minutes of glancing
  at comments.

---

## Summary: Stage-by-Stage at a Glance

| # | Stage | Human or AI-led | Time budget | The one thing this stage protects |
|---|---|---|---|---|
| 0 | Rights policy decision | Human (founder) | Once, up front | Whether the channel can legally exist as planned |
| 1 | Song selection | Human, AI-assisted shortlist | Weekly batch | Choosing songs where the mission actually matters |
| 2 | Rights clearance | Human | Per song, ahead of time | No wasted creative effort on unusable songs |
| 3 | Source understanding | Human review of AI draft | 20–30 min | Catching what AI flattens or misses culturally |
| 4 | English draft generation | AI-led | Minutes | Raw material with real range, not one guess |
| 5 | Creative selection & editing | Human | 45–60 min | The channel's actual quality bar |
| 6 | Timing & sync | AI-assisted, human-corrected | 10–15 min | Lines landing naturally with the music |
| 7 | Visual direction | Human, templated | 10–15 min | Emotional tone matching visually, without going generic |
| 8 | Video assembly | Templated/tool-assisted | Minutes | Consistent execution once upstream work is right |
| 9 | Quality review | Human, second reviewer | 15–20 min | Nothing ships that reads as "a translation" |
| 10 | Metadata & publishing package | Human | 15–20 min | The title/thumbnail actually carrying the feeling |
| 11 | Publish & feedback loop | Human, ongoing | Ongoing | The channel keeps getting better, not just more |

*End of document.*
