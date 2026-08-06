# Multimodal visual context for comics adaptation — design (not yet built)

Status: **design only, nothing in this document is implemented**. Saved
separately from `docs/CAPABILITY_MATRIX.md` on purpose — that file
documents shipped, verified work only, and this isn't that yet.

## The gap this addresses

Today, comics adaptation (`engine/comics_adapt.py`) is entirely
text-only: the Translator, Creative Adapter, and Judge see a bubble's
`source_text` and nothing else. A human localizer looks at the panel —
the character's expression, the scene's power dynamic, what's visually
happening — and lets that flavor the line. Castia currently can't, no
matter how good the text-only reasoning is.

## What already exists and can be reused directly

The hard infrastructure is already built and proven, just never wired
into the adaptation path:

- `engine/llm_client.py`'s `LLMClient.complete_json_with_image()` and
  the `image_data_url` parameter on `complete_json()` already work for
  both providers — OpenAI's `image_url` content block and Anthropic's
  base64 media-type block are both implemented and covered by tests.
- `create_vision_client()` already builds a client pinned to a
  vision-capable model (`config.VISION_MODEL`), kept separate from the
  main text model so the two can be tuned/priced independently.
- `engine/comics_vision.py::read_panel` already sends a real panel
  image through this path today (gated by `CASTIA_VISION_READING`) and
  gets back reliable structured JSON (`Reading` objects with
  `text`/`kind`/`speaker`) — direct, in-this-codebase evidence against
  the generic worry that "adding an image destabilizes strict JSON
  schemas." It doesn't have to.
- Client-side panel resizing before upload already exists (task #12,
  this session) — the image sent to OCR is already downscaled, not the
  raw source file. The same resized asset can be reused here instead of
  re-fetching or re-encoding a full-resolution image.

## What's actually missing

1. **The image doesn't survive to the adaptation stage.**
   `BubbleInput`/`ChapterInput` (`engine/models.py`) carry only
   `{id, source_text, voice}`. By the time a bubble reaches
   `adapt_chapter`, the panel image is already gone — the frontend's
   `panelToChapterBubbles` (`web/lib/comics-types.ts`) never sends it.
   This needs a real schema change, not a prompt change.

2. **`/api/comics/adapt/start` is JSON, not multipart.** Unlike
   `/api/comics/redraw` (already multipart), the adapt-start endpoint
   takes a JSON body. Inlining base64 images for a 30-80 panel chapter
   in that body is tens of megabytes — a real payload-size problem for
   Vercel's proxy route (`web/app/api/comics/adapt/start/route.ts`),
   not just a style preference.

3. **Nobody has decided which Writers' Room stage(s) actually need the
   image.** This is the real cost/latency lever, and it's a legitimate
   concern from the product-discussion critique this design responds
   to — but it's a design choice to make deliberately, not an inherent
   cost of "the model can see the panel."

## Recommended scope — phased, not all at once

### Phase 1 — smallest testable slice (Judge only)

Add an optional image to `BubbleInput`. Wire it into **only the
Judge's final ruling call** (`prompts.py::judge_final_prompt`), not the
Translator, not the Creative Adapter, not judge triage.

Reasoning: the Judge is already synthesizing across candidates and
making the one genuinely creative call in the room — it's the stage
that benefits from "what's actually happening in this panel," not the
stages generating raw candidates. This keeps the worst-case cost
multiplier at roughly 1-2 vision calls per bubble (final ruling, plus
an occasional corrective retry) instead of 3-8 if every stage got the
image.

Gate behind a new flag, `CASTIA_VISION_TRANSLATION` (default off) —
same opt-in pattern `CASTIA_VISION_READING` already established for
the OCR-reading pass. Two separate flags on purpose: reading quality
and translation quality are different bets with different cost
profiles: an operator should be able to enable one without the other.

Prompt scope must be narrow and specific, to blunt the real
hallucination/over-interpretation risk: ask the Judge to describe only
what's directly relevant to how *this line* should be delivered (tone,
physical state, power dynamic between speakers), not an open-ended
scene description — the more open the ask, the more room for the model
to invent visual "meaning" that isn't there.

Encode the image once per bubble, not once per call — the same
`image_data_url` string gets reused across judge_triage → judge_final
→ corrective_retry for that bubble, not re-encoded/re-sent on each.

### Phase 2 — frontend/API plumbing

Switch the adapt-start flow to actually send panel images: reuse the
existing client-side resize (task #12) rather than the raw source
file, and redesign the request as multipart (mirroring `/api/comics/redraw`'s
existing shape) rather than inlining base64 into a JSON body. This is
the more invasive half of the work — real API contract changes, not
just engine-side wiring — and should be scoped and reviewed on its
own.

### Phase 3 — only if Phase 1+2 prove worth the cost

Extend to the Creative Adapter too, if real usage shows the Judge-only
scope isn't enough. Not scoped further here — deliberately deferred
until there's real signal from Phase 1/2 to decide with.

## Answering the four risks raised in product discussion

- **Cost/latency.** Real, but the "exponential" framing overstated it —
  it's a linear multiplier per call, and Judge-only scoping plus
  encode-once-per-bubble bounds it well below the naive worst case
  (every stage, every retry, full-resolution image).
- **Hallucination / prompt distraction.** Real, unavoidable in the
  general case — mitigated, not eliminated, by a narrowly scoped
  prompt asking for delivery-relevant description only.
- **Reading order / bubble-to-character correlation.** The reading-
  order half is a real, already-disclosed limitation
  (`comics_ocr.py`'s own docstring). The bubble-correlation half
  doesn't actually apply to this design as scoped — Phase 1 sends one
  full panel image to the Judge for tone/context on one bubble already
  identified by OCR, not a request to correlate which text region
  belongs to which character.
- **Structured-output schema instability.** `comics_vision.py::read_panel`
  is direct, already-shipped evidence in this exact codebase that a
  vision call and a strict JSON schema coexist reliably here — this
  isn't a hypothetical risk to guess at, there's already a working
  precedent to build the same way from.

## Testing / verification constraints (disclosed up front)

Same discipline `comics_vision.py`'s own docstring already applies to
itself: the request/response plumbing, prompt construction, and
schema handling can be fully unit-tested with a mocked vision client
(no real API calls, no real image content) — the same pattern already
used throughout this codebase's engine tests. **Real output quality —
whether the Judge's visual read actually improves an adaptation — is
not verifiable in a sandbox with no real vision-API credentials and no
real manga/webtoon content.** That verification has to happen against
a real deployment with real chapters, not here.

## Rough cost/latency shape (qualitative, not a firm estimate)

Vision tokens are more expensive than text tokens per call, and vision
inference typically has higher latency than text-only inference for
the same provider/model — both true in general, not specific to this
architecture. The actual per-chapter cost delta depends on real
pricing at the time this is built and the final resolution/detail
level chosen for the resized image, neither of which is worth
guessing at precisely here. Treat this as "materially more expensive
per bubble that gets a vision call, bounded by Phase 1's Judge-only
scope" rather than a specific number.
