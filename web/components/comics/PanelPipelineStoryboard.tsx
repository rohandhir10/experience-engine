/** The "what happens to a panel" explainer, redone as a visual storyboard
 * instead of five identical text blocks (ComicsPipelineDiagram's `dark={
 * false}` mode, which this replaces on /comics specifically - that
 * component still serves its original two callers unchanged, see its own
 * doc comment). Real feedback, not a hypothetical: five rows of title +
 * one-line description in a row read like a terms-of-service list, not a
 * product screenshot.
 *
 * Every illustration below is a diagram, honestly - abstracted mock art
 * built from the real mechanism (docs/WRITERS_ROOM_V1.md, engine/
 * comics_ocr.py, engine/comics_adapt.py), the same convention
 * app/page.tsx's MediumTile hover cards and InputScreen.tsx's demo
 * crossfade already use for "the actual UI, redrawn small" rather than a
 * captured screenshot standing in for one - PipelineDiagram.tsx's own
 * doc comment states the same reasoning for why a diagram is the honest
 * choice here: there's no single screen that shows OCR detection or the
 * Chapter DNA object directly, so a diagram is accurate where a
 * screenshot would have to fake one. The literal/adapted line in the
 * last card ("You are... late. Again." -> "You're late. Again.") is the
 * same example line as the Webtoons tile's own hover state on "/" - one
 * example reused, not two different ones implying two different real
 * results. */

import type { JSX } from "react";

const STEPS: { title: string; description: string; Art: () => JSX.Element }[] = [
  {
    title: "Panel upload",
    description: "One image per panel, dropped in in reading order.",
    Art: UploadArt,
  },
  {
    title: "OCR",
    description: "Google Cloud Vision reads each bubble's text and position.",
    Art: OcrArt,
  },
  {
    title: "Chapter DNA",
    description: "Genre, tone, and a cast voice profile for the whole chapter.",
    Art: DnaArt,
  },
  {
    title: "Writers' Room",
    description: "The same Translator → Adapter → Judge pipeline as music.",
    Art: WritersRoomArt,
  },
  {
    title: "Adapted script",
    description: "Literal, adapted line, and why — per panel.",
    Art: AdaptedScriptArt,
  },
];

export function PanelPipelineStoryboard() {
  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
      {STEPS.map((step, i) => (
        <div
          key={step.title}
          className="flex flex-col rounded-2xl border border-black/[0.12] bg-white p-5 shadow-[0_1px_2px_rgba(0,0,0,0.04)] dark:border-white/10 dark:bg-white/[0.03] dark:shadow-none"
        >
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent/10 text-[11px] font-medium text-accent">
              {i + 1}
            </span>
            <p className="text-[13px] font-medium text-ink dark:text-white/90">{step.title}</p>
          </div>
          <div className="mt-3 overflow-hidden rounded-xl border border-black/[0.10] bg-black/[0.015] dark:border-white/10 dark:bg-white/[0.02]">
            <step.Art />
          </div>
          <p className="mt-3 text-[11.5px] leading-relaxed text-ink/68 dark:text-white/62">
            {step.description}
          </p>
        </div>
      ))}
    </div>
  );
}

function UploadArt() {
  return (
    <svg viewBox="0 0 200 120" className="h-28 w-full sm:h-32" aria-hidden="true">
      <g transform="translate(66 18) rotate(-8)">
        <rect
          width="58"
          height="76"
          rx="6"
          className="fill-white stroke-black/10 dark:fill-white/[0.06] dark:stroke-white/10"
          strokeWidth="1.5"
        />
      </g>
      <g transform="translate(76 14) rotate(2)">
        <rect
          width="58"
          height="76"
          rx="6"
          className="fill-white stroke-black/10 dark:fill-white/[0.08] dark:stroke-white/10"
          strokeWidth="1.5"
        />
      </g>
      <g transform="translate(86 10) rotate(9)">
        <rect
          width="58"
          height="76"
          rx="6"
          className="fill-white stroke-accent/40 dark:fill-white/10 dark:stroke-accent/40"
          strokeWidth="1.5"
        />
        <circle cx="14" cy="14" r="10" className="fill-accent" />
        <text x="14" y="18.5" textAnchor="middle" className="fill-white text-[11px] font-medium">
          1
        </text>
      </g>
    </svg>
  );
}

/** Corner "detection reticle" brackets, not full rectangles - reads as a
 * live bounding-box overlay rather than a static frame, over a simple
 * duotone panel scene (two abstract silhouettes) standing in for actual
 * artwork, which this project won't fabricate (no licensed comic art to
 * show - see MockWindow.tsx's own doc comment for the same rule applied
 * to screenshots). */
function OcrArt() {
  const boxes = [
    { x: 18, y: 8, w: 76, h: 46 },
    { x: 104, y: 2, w: 80, h: 44 },
  ];
  return (
    <svg viewBox="0 0 200 120" className="h-28 w-full sm:h-32" aria-hidden="true">
      <rect width="200" height="120" className="fill-black/[0.02] dark:fill-white/[0.03]" />

      <circle cx="55" cy="82" r="16" className="fill-black/10 dark:fill-white/10" />
      <path d="M28 118 Q55 90 82 118 Z" className="fill-black/10 dark:fill-white/10" />
      <circle cx="142" cy="84" r="14" className="fill-black/10 dark:fill-white/10" />
      <path d="M118 118 Q142 96 166 118 Z" className="fill-black/10 dark:fill-white/10" />

      <g>
        <rect x="22" y="14" width="68" height="32" rx="10" className="fill-white dark:fill-white/90" />
        <path d="M44 46 L36 58 L56 46 Z" className="fill-white dark:fill-white/90" />
      </g>
      <g>
        <rect x="108" y="8" width="72" height="30" rx="10" className="fill-white dark:fill-white/90" />
        <path d="M128 38 L120 50 L142 38 Z" className="fill-white dark:fill-white/90" />
      </g>

      {boxes.map((b, i) => (
        <g key={i} className="text-accent" stroke="currentColor" strokeWidth="2.25" fill="none" strokeLinecap="round">
          <path d={`M${b.x} ${b.y + 11} L${b.x} ${b.y} L${b.x + 11} ${b.y}`} />
          <path d={`M${b.x + b.w - 11} ${b.y} L${b.x + b.w} ${b.y} L${b.x + b.w} ${b.y + 11}`} />
          <path d={`M${b.x} ${b.y + b.h - 11} L${b.x} ${b.y + b.h} L${b.x + 11} ${b.y + b.h}`} />
          <path d={`M${b.x + b.w - 11} ${b.y + b.h} L${b.x + b.w} ${b.y + b.h} L${b.x + b.w} ${b.y + b.h - 11}`} />
        </g>
      ))}
    </svg>
  );
}

function DnaArt() {
  return (
    <div className="flex h-28 w-full flex-col justify-center gap-[3px] px-4 font-mono text-[10.5px] leading-[1.55] text-ink/78 dark:text-white/78 sm:h-32">
      <div>{"{"}</div>
      <div className="pl-3">
        <span className="text-accent">"genre"</span>: "slice-of-life",
      </div>
      <div className="pl-3">
        <span className="text-accent">"tone"</span>: "wry, understated",
      </div>
      <div className="pl-3">
        <span className="text-accent">"cast"</span>: [
      </div>
      <div className="pl-6 truncate">
        {"{ "}
        <span className="text-accent">"name"</span>: "Mira", <span className="text-accent">"voice"</span>: "sarcastic"
        {" }"}
      </div>
      <div className="pl-3">]</div>
      <div>{"}"}</div>
    </div>
  );
}

function WritersRoomArt() {
  const nodes = ["Translator", "Adapter", "Judge"];
  return (
    <div className="flex h-28 w-full items-center justify-center gap-2 px-3 sm:h-32">
      {nodes.map((n, i) => (
        <div key={n} className="flex items-center gap-2">
          <div
            className={`rounded-lg border px-2.5 py-2 text-center text-[10px] font-medium ${
              i === 2
                ? "border-accent/40 bg-accent/[0.08] text-ink dark:text-white"
                : "border-black/10 bg-white text-ink/78 dark:border-white/10 dark:bg-white/5 dark:text-white/72"
            }`}
          >
            {n}
          </div>
          {i < nodes.length - 1 && <span className="text-ink/32 dark:text-white/32">→</span>}
        </div>
      ))}
    </div>
  );
}

function AdaptedScriptArt() {
  return (
    <div className="flex h-28 w-full flex-col justify-center gap-2.5 px-4 sm:h-32">
      <div>
        <span className="rounded border border-black/10 px-1.5 py-0.5 text-[8.5px] uppercase tracking-wide text-ink/62 dark:border-white/15 dark:text-white/62">
          Literal
        </span>
        <p className="mt-1 text-[10.5px] leading-snug text-ink/75 dark:text-white/68">
          "You are… late. Again."
        </p>
      </div>
      <div>
        <span className="rounded border border-accent/30 bg-accent/[0.08] px-1.5 py-0.5 text-[8.5px] uppercase tracking-wide text-accent">
          Castia
        </span>
        <p className="mt-1 text-[10.5px] font-medium leading-snug text-ink dark:text-white">
          "You're late. Again."
        </p>
      </div>
    </div>
  );
}
