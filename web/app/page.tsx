"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";
import { ScrollReveal } from "@/components/ScrollReveal";
import { readMediumPreference, type Medium } from "@/lib/mediumPreference";

// "/" is a neutral medium chooser, not the music workflow directly - the
// music workflow itself lives at /music (moved from here, unchanged; see
// app/music/page.tsx), and /comics is the webtoons workflow, now
// reachable from a real entry point instead of only by typing the URL.
// Music and Webtoons are meant to read as two applications of the same
// underlying tool ("creative work" - a lyric or a line of dialogue),
// not a flagship-plus-experiment: same tile size, same visual weight
// (neither tile carries a real screenshot the other doesn't have -
// both get the same abstracted mock-UI treatment), and the headline
// deliberately doesn't reuse either workspace's own tagline.
//
// Deliberately does NOT carry the "How it works" feature grid, the
// language-chip row, or the "See how it works" demo link that live on
// /music today - those are music-specific proof, and putting them on a
// screen meant to present two equal choices would silently tilt it
// toward music by sheer weight of content.
//
// Webtoons carries a "Beta" pill (DashboardSidebar.tsx's "Soon" pill is
// the precedent - same honesty convention, different word because this
// one IS reachable and working, just not yet at full parity: save/
// collections/share-link and the background-job adapt call all work
// the same way music's do now, but sound-effect text over artwork
// isn't redrawn (speech bubbles only) and OCR reading order is a plain
// guess without a configured text detector. Remove the pill only once
// those actually close - see docs/CAPABILITY_MATRIX.md for what's
// tracked as done.
//
// No longer auto-redirects a returning visitor straight to /music or
// /comics - it used to, and the real cost turned out to be worse than
// the convenience: there was then no way back to this page at all short
// of clearing localStorage, since the site's own logo links here and
// "here" would just bounce you straight back out. The remembered
// medium (lib/mediumPreference.ts) still does something real: it's
// used below to label whichever tile you used last, rather than
// silently deciding for you every time.
export default function Home() {
  const [lastMedium, setLastMedium] = useState<Medium | null>(null);

  useEffect(() => {
    setLastMedium(readMediumPreference());
  }, []);

  return (
    <main className="min-h-screen bg-paper-dark px-6 pb-28 pt-8 sm:px-10">
      <SiteHeader active="home" forceDark />

      <div className="mx-auto mt-16 flex w-full max-w-3xl flex-col items-center text-center sm:mt-20">
        <h1 className="animate-fade-up font-serif text-[2.1rem] leading-[1.15] tracking-tight text-white sm:text-[2.6rem]">
          The words are the{" "}
          <span className="relative inline-block whitespace-nowrap">
            easy part
            <svg
              viewBox="0 0 200 20"
              preserveAspectRatio="none"
              aria-hidden="true"
              className="pointer-events-none absolute -bottom-1.5 left-0 h-3 w-full"
            >
              <path
                d="M2 11 Q 50 2, 100 9 T 198 7"
                fill="none"
                strokeWidth="3"
                strokeLinecap="round"
                pathLength="200"
                className="stroke-accent animate-draw-underline"
              />
            </svg>
          </span>
          .
        </h1>
        <p
          className="animate-fade-up mt-4 max-w-md text-[14px] text-white/40"
          style={{ animationDelay: "80ms" }}
        >
          Song lyrics or comic dialogue — Castia keeps the feeling a literal
          pass throws away. Choose what you're adapting.
        </p>
      </div>

      <div
        className="animate-fade-up mx-auto mt-12 grid w-full max-w-3xl grid-cols-1 gap-5 sm:grid-cols-2"
        style={{ animationDelay: "120ms" }}
      >
        <MediumTile
          href="/music"
          title="Music"
          tagline="Rewrite song lyrics across six languages so they still hit the way the original does."
          continuing={lastMedium === "music"}
        >
          <div className="flex h-full flex-col justify-center gap-3 rounded-lg border border-white/10 bg-white/[0.03] p-5">
            {/* Hovering crossfades the literal reading into the adapted
                line - a real, small demonstration of the mechanism
                itself, not decoration for its own sake. */}
            <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
              <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 shrink-0 fill-white/30">
                <path d="M9 18V5l12-2v13M9 18a3 3 0 11-6 0 3 3 0 016 0zm12-2a3 3 0 11-6 0 3 3 0 016 0z" fill="none" stroke="currentColor" strokeWidth="1.6" />
              </svg>
              <span className="relative flex-1 overflow-hidden">
                <span className="block truncate text-[11px] text-white/35 transition-opacity duration-300 group-hover:opacity-0">
                  Tera hone laga hoon…
                </span>
                <span className="absolute inset-0 block truncate text-[11px] text-accent opacity-0 transition-opacity duration-300 group-hover:opacity-100">
                  Slowly, I'm becoming yours
                </span>
              </span>
            </div>
            <p className="text-[12px] leading-relaxed text-white/40">
              Paste a lyric or import a YouTube link — see the literal
              reading, the adapted line, and why it changed, side by side.
            </p>
          </div>
        </MediumTile>

        <MediumTile
          href="/comics"
          title="Webtoons"
          badge="Beta"
          tagline="Adapt comic and webtoon dialogue, panel by panel."
          continuing={lastMedium === "webtoons"}
        >
          <div className="flex h-full flex-col justify-center gap-3 rounded-lg border border-white/10 bg-white/[0.03] p-5">
            <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
              <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 shrink-0 fill-white/30">
                <path d="M4 4h16v12H7l-3 3V4z" />
              </svg>
              <span className="relative flex-1 overflow-hidden">
                <span className="block truncate text-[11px] text-white/35 transition-opacity duration-300 group-hover:opacity-0">
                  panel-07.png
                </span>
                <span className="absolute inset-0 block truncate text-[11px] text-accent opacity-0 transition-opacity duration-300 group-hover:opacity-100">
                  "You're late. Again."
                </span>
              </span>
            </div>
            <p className="text-[12px] leading-relaxed text-white/40">
              Upload panel images, review the extracted dialogue, then adapt it —
              a starting draft you read before anything ships, same as every
              language pair here.
            </p>
          </div>
        </MediumTile>
      </div>

      <ScrollReveal className="mx-auto mt-20 w-full max-w-3xl border-t border-white/[0.06] pt-16 sm:mt-24 sm:pt-20">
        <h2 className="text-center font-serif text-[1.6rem] leading-[1.25] text-white sm:text-[1.9rem]">
          Every other tool ships whatever its first draft happened to be.
        </h2>
        <p className="mx-auto mt-4 max-w-lg text-center text-[13.5px] leading-relaxed text-white/45">
          Google Translate, DeepL, and a single AI prompt are all built to
          produce one fluent pass and stop there. Real, documented
          differences, not a marketing claim:
        </p>

        <div className="mt-8 overflow-x-auto rounded-2xl border border-white/10 bg-white/[0.02]">
          <table className="w-full min-w-[560px] text-left text-[13px]">
            <thead>
              <tr className="border-b border-white/10">
                <th className="p-4 font-medium text-white/35"> </th>
                <th className="p-4 font-medium text-white/50">Google Translate</th>
                <th className="p-4 font-medium text-white/50">DeepL</th>
                <th className="p-4 font-medium text-white/50">A single AI prompt</th>
                <th className="p-4 font-medium text-white">Castia</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/10">
              {[
                ["Drafts per line", "One", "One", "One", "Six — one literal anchor + five creative rewrites"],
                ["Verification step", "Not documented", "Not documented", "No mechanism", "A Judge scores every rewrite against the anchor"],
                ["Explains its changes", "No", "No", "No", "Every departure ships with a stated reason"],
                ["Falls back to literal if nothing earns its keep", "No mechanism", "No mechanism", "No mechanism", "Yes"],
              ].map(([label, gt, dl, gpt, castia]) => (
                <tr key={label}>
                  <td className="p-4 align-top text-white/40">{label}</td>
                  <td className="p-4 align-top text-white/55">{gt}</td>
                  <td className="p-4 align-top text-white/55">{dl}</td>
                  <td className="p-4 align-top text-white/55">{gpt}</td>
                  <td className="p-4 align-top font-medium text-white">{castia}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="mt-6 text-center">
          <Link
            href="/s/demo"
            className="text-[13px] text-white/70 underline decoration-white/25 underline-offset-4 transition hover:text-white"
          >
            See a real song result, line by line →
          </Link>
        </p>

        <p className="mt-3 text-center text-[12.5px] leading-relaxed text-white/35">
          The full mechanism, sourced:{" "}
          <Link href="/compare/google-translate" className="underline decoration-white/20 underline-offset-4 hover:text-white/60">
            vs. Google Translate
          </Link>
          {" · "}
          <Link href="/compare/deepl" className="underline decoration-white/20 underline-offset-4 hover:text-white/60">
            vs. DeepL
          </Link>
          {" · "}
          <Link href="/compare/chatgpt-prompt" className="underline decoration-white/20 underline-offset-4 hover:text-white/60">
            vs. a single ChatGPT prompt
          </Link>
        </p>
      </ScrollReveal>

      <ScrollReveal className="mx-auto mt-20 w-full max-w-3xl border-t border-white/[0.06] pt-16 sm:mt-24 sm:pt-20" delayMs={80}>
        <h2 className="text-center font-serif text-[1.6rem] leading-[1.25] text-white sm:text-[1.9rem]">
          Three roles, one line: a translator, a room of writers, an editor.
        </h2>

        <HomePipelineFlow />

        <p className="mt-6 text-center text-[13px] text-white/40">
          <Link href="/how-it-works" className="underline decoration-white/20 underline-offset-4 hover:text-white/70">
            See the full pipeline, including comics
          </Link>
        </p>
      </ScrollReveal>

      <ScrollReveal className="mx-auto mt-20 w-full max-w-2xl sm:mt-24" delayMs={80}>
        <div className="rounded-2xl bg-[#181310] p-8 text-center sm:p-12">
          <p className="font-serif text-[1.35rem] leading-[1.35] text-white sm:text-[1.6rem]">
            Every AI has an opinion about your words.
            <br />
            Only one writes down why.
          </p>
          <p className="mx-auto mt-4 max-w-md text-[13px] leading-relaxed text-white/45">
            No invented details, no unexplained rewrites — a change that
            can't justify itself against the literal reading gets reverted
            before it ships, not just flagged.
          </p>
        </div>
      </ScrollReveal>

      <Footer dark />
    </main>
  );
}

// Same chip-and-arrow visual language as CompareDiagram (/compare/*) and
// CandidateDiagram (/how-it-works), restyled for this page's forced-dark
// shell - ties the homepage into the rest of the site's design system
// instead of three identical bordered cards repeating the "equal-weight
// feature grid" shape every other section on this page already avoids.
function HomePipelineFlow() {
  return (
    <div className="mt-10 flex flex-col items-center gap-2.5 sm:flex-row sm:justify-center sm:gap-2.5">
      <FlowChip title="Translator" body="One literal anchor" />
      <FlowArrow />
      <FlowChip title="5 rewrites" body="Different angles, same line" />
      <FlowArrow />
      <FlowChip title="Judge" body="Scores, picks, states why" accent />
      <FlowArrow />
      <FlowChip title="Output" body="A line you can trust" dim />
    </div>
  );
}

function FlowChip({
  title,
  body,
  accent,
  dim,
}: {
  title: string;
  body: string;
  accent?: boolean;
  dim?: boolean;
}) {
  return (
    <div
      className={`w-full max-w-[220px] rounded-xl border px-4 py-3 text-center sm:max-w-[160px] ${
        accent ? "border-accent/40 bg-accent/[0.08]" : dim ? "border-white/[0.06] bg-white/[0.015]" : "border-white/10 bg-white/[0.02]"
      }`}
    >
      <p className={`font-serif text-[13.5px] ${accent ? "text-white" : dim ? "text-white/50" : "text-white/85"}`}>
        {title}
      </p>
      <p className={`mt-1 text-[11px] leading-snug ${dim ? "text-white/30" : "text-white/40"}`}>{body}</p>
    </div>
  );
}

function FlowArrow() {
  return (
    <span className="text-white/20 rotate-90 sm:rotate-0" aria-hidden="true">
      →
    </span>
  );
}

function MediumTile({
  href,
  title,
  tagline,
  badge,
  continuing,
  children,
}: {
  href: string;
  title: string;
  tagline: string;
  badge?: string;
  // True when lib/mediumPreference.ts's stored value matches this tile -
  // the one thing the remembered preference still does now that "/"
  // no longer auto-redirects on it (see this file's top comment): a
  // quiet "pick up where you left off" label, not a decision made for
  // you.
  continuing?: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className="group flex flex-col rounded-2xl border border-white/10 bg-white/[0.03] p-5 text-left transition-all duration-300 hover:-translate-y-1 hover:border-white/20 hover:bg-white/[0.05] hover:shadow-[0_24px_48px_-24px_rgba(0,0,0,0.6)]"
    >
      <div className="overflow-hidden rounded-lg">{children}</div>
      <div className="mt-4 flex items-center gap-2">
        <h2 className="font-serif text-[1.15rem] text-white">{title}</h2>
        {badge && (
          <span className="rounded-full bg-white/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-white/40">
            {badge}
          </span>
        )}
        {continuing && (
          <span className="text-[11px] text-white/30">— continue where you left off</span>
        )}
      </div>
      <p className="mt-1.5 text-[13px] leading-relaxed text-white/40">{tagline}</p>
    </Link>
  );
}
