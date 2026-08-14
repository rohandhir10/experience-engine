"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";
import { ScrollReveal } from "@/components/ScrollReveal";
import { JsonLd } from "@/components/JsonLd";
import { readMediumPreference, type Medium } from "@/lib/mediumPreference";
import { FOUNDER_NAME } from "@/lib/seo";
import { webPageJsonLd, faqPageJsonLd } from "@/lib/schema";
import { homepageFaqs } from "@/lib/faqs";

// The last day this page's actual visible content changed - bumped by
// hand alongside a real edit, same discipline lib/content.ts's registry
// uses for editorial pages (see that file's own comment). "/" isn't in
// that registry (it's a static route in sitemap.ts, not editorial
// content with its own history), so this is its own single source for
// the one thing that needs a real date: the dateModified this page's own
// WebPage JSON-LD states below, and the "Updated" line rendered near the
// FAQ section. Never auto-generated from build time - that would be a
// fresh "Updated today" on every deploy regardless of whether anything
// actually changed, which is the exact dishonesty this convention exists
// to avoid.
const PAGE_UPDATED_DATE = "2026-08-11";

const HOMEPAGE_FAQS = homepageFaqs();

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
// The "Beta" pill that used to sit on the Webtoons tile is gone (real
// feedback that it read as clutter across the nav/tiles/sidebar) - the
// gaps it disclosed haven't closed (sound-effect text over artwork
// still isn't redrawn, speech bubbles only, and OCR reading order is
// still a plain guess without a configured text detector - see
// docs/CAPABILITY_MATRIX.md for what's tracked as done), they're just
// not flagged with a badge here anymore. Full disclosure still lives in
// prose on /manga-webtoon-translation and in /comics' own meta
// description (app/comics/layout.tsx).
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
    <main className="min-h-screen bg-paper px-6 pb-28 pt-8 dark:bg-paper-dark sm:px-10">
      <JsonLd data={webPageJsonLd({
        path: "/",
        name: "Castia — Adapt the feeling, not just the words",
        description:
          "Castia rewrites song lyrics and comic dialogue across six languages through a three-stage Writers' Room, with every change shipped alongside a plain-language reason.",
        updatedDate: PAGE_UPDATED_DATE,
      })} />
      <JsonLd data={faqPageJsonLd(HOMEPAGE_FAQS)} />

      <SiteHeader active="home" />

      <div className="mx-auto mt-16 flex w-full max-w-3xl flex-col items-center text-center sm:mt-20">
        <h1 className="animate-fade-up font-serif text-[2.1rem] leading-[1.15] tracking-tight text-ink dark:text-white sm:text-[2.6rem]">
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
        {/* Short and human, not the old four-sentence mechanism dump -
            real feedback that the hero read as descriptive/salesy rather
            than a simple line. The full "what does Castia do" answer
            still exists for search results and AI-generated summaries:
            it's the JSON-LD description just above (webPageJsonLd call
            at the top of this file), which was always the structural
            source for that job, not this paragraph - and the mechanism
            itself (Writers' Room stages, literal anchor, Judge) is still
            explained in full one scroll down in "How does the Writers'
            Room actually work?". Nothing here got deleted from the page,
            just un-front-loaded from the first thing a visitor reads. */}
        <p
          className="animate-fade-up mt-4 max-w-md text-[14px] leading-relaxed text-ink/72 dark:text-white/62"
          style={{ animationDelay: "80ms" }}
        >
          Not a literal translation — a rewrite that still sounds like you.
          Choose what you're adapting below.
        </p>
        {/* A real byline (linking to the one page with a real Person bio -
            app/about/page.tsx) plus a real, hand-bumped edit date - see
            PAGE_UPDATED_DATE above for why this is never build-time. No
            photo: one doesn't exist, and a stock/generated one would be
            exactly the kind of fabricated credential this codebase's own
            no-fabrication discipline (docs/CAPABILITY_MATRIX.md) rules
            out. */}
        <p
          className="animate-fade-up mt-3 text-[11.5px] text-ink/68 dark:text-white/62"
          style={{ animationDelay: "100ms" }}
        >
          Built by{" "}
          <Link href="/about" className="underline decoration-ink/15 underline-offset-4 hover:text-ink/72 dark:decoration-white/20 dark:hover:text-white/72">
            {FOUNDER_NAME}
          </Link>
          {" · "}Updated{" "}
          <time dateTime={PAGE_UPDATED_DATE}>
            {new Date(PAGE_UPDATED_DATE + "T00:00:00Z").toLocaleDateString("en-US", {
              month: "long",
              day: "numeric",
              year: "numeric",
              timeZone: "UTC",
            })}
          </time>
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
          <div className="flex h-full flex-col justify-center gap-3 rounded-lg border border-black/[0.10] bg-black/[0.015] p-5 dark:border-white/10 dark:bg-white/[0.03]">
            {/* Hovering crossfades the literal reading into the adapted
                line - a real, small demonstration of the mechanism
                itself, not decoration for its own sake. */}
            <div className="flex items-center gap-2 rounded-lg border border-black/[0.10] bg-black/[0.015] px-3 py-2 dark:border-white/10 dark:bg-white/[0.03]">
              <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 shrink-0 fill-ink/30 dark:fill-white/30">
                <path d="M9 18V5l12-2v13M9 18a3 3 0 11-6 0 3 3 0 016 0zm12-2a3 3 0 11-6 0 3 3 0 016 0z" fill="none" stroke="currentColor" strokeWidth="1.6" />
              </svg>
              <span className="relative flex-1 overflow-hidden">
                <span className="block truncate text-[11px] text-ink/75 transition-opacity duration-300 group-hover:opacity-0 dark:text-white/68">
                  Tera hone laga hoon…
                </span>
                <span className="absolute inset-0 block truncate text-[11px] text-accent opacity-0 transition-opacity duration-300 group-hover:opacity-100">
                  Slowly, I'm becoming yours
                </span>
              </span>
            </div>
            <p className="text-[12px] leading-relaxed text-ink/68 dark:text-white/62">
              Paste a lyric or import a YouTube link — see the literal
              reading, the adapted line, and why it changed, side by side.
            </p>
          </div>
        </MediumTile>

        <MediumTile
          href="/comics"
          title="Webtoons"
          tagline="Adapt comic and webtoon dialogue, panel by panel."
          continuing={lastMedium === "webtoons"}
        >
          <div className="flex h-full flex-col justify-center gap-3 rounded-lg border border-black/[0.10] bg-black/[0.015] p-5 dark:border-white/10 dark:bg-white/[0.03]">
            <div className="flex items-center gap-2 rounded-lg border border-black/[0.10] bg-black/[0.015] px-3 py-2 dark:border-white/10 dark:bg-white/[0.03]">
              <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 shrink-0 fill-ink/30 dark:fill-white/30">
                <path d="M4 4h16v12H7l-3 3V4z" />
              </svg>
              <span className="relative flex-1 overflow-hidden">
                <span className="block truncate text-[11px] text-ink/75 transition-opacity duration-300 group-hover:opacity-0 dark:text-white/68">
                  panel-07.png
                </span>
                <span className="absolute inset-0 block truncate text-[11px] text-accent opacity-0 transition-opacity duration-300 group-hover:opacity-100">
                  "You're late. Again."
                </span>
              </span>
            </div>
            <p className="text-[12px] leading-relaxed text-ink/68 dark:text-white/62">
              Upload panel images and review the extracted dialogue before
              you adapt it — same as every language pair here.
            </p>
          </div>
        </MediumTile>
      </div>

      <ScrollReveal className="mx-auto mt-20 w-full max-w-3xl border-t border-black/[0.10] pt-16 dark:border-white/[0.10] sm:mt-24 sm:pt-20">
        <h2 className="text-center font-serif text-[1.6rem] leading-[1.25] text-ink dark:text-white sm:text-[1.9rem]">
          How is this different from Google Translate or a single AI prompt?
        </h2>
        <p className="mx-auto mt-4 max-w-lg text-center text-[13.5px] leading-relaxed text-ink/78 dark:text-white/75">
          They're all built to produce one fluent pass and stop there —
          Castia isn't. Real, documented differences, not a marketing claim:
        </p>

        <div className="mt-8 overflow-x-auto rounded-2xl border border-black/[0.12] bg-black/[0.01] dark:border-white/10 dark:bg-white/[0.02]">
          <table className="w-full min-w-[560px] text-left text-[13px]">
            <thead>
              <tr className="border-b border-black/[0.12] dark:border-white/10">
                <th className="p-4 font-medium text-ink/62 dark:text-white/68"> </th>
                <th className="p-4 font-medium text-ink/78 dark:text-white/68">Google Translate</th>
                <th className="p-4 font-medium text-ink/78 dark:text-white/68">DeepL</th>
                <th className="p-4 font-medium text-ink/78 dark:text-white/68">A single AI prompt</th>
                <th className="p-4 font-medium text-ink dark:text-white">Castia</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-black/[0.12] dark:divide-white/10">
              {[
                ["Drafts per line", "One", "One", "One", "Six — one literal anchor + five creative rewrites"],
                ["Verification step", "Not documented", "Not documented", "No mechanism", "A Judge scores every rewrite against the anchor"],
                ["Explains its changes", "No", "No", "No", "Every departure ships with a stated reason"],
                ["Falls back to literal if nothing earns its keep", "No mechanism", "No mechanism", "No mechanism", "Yes"],
              ].map(([label, gt, dl, gpt, castia]) => (
                <tr key={label}>
                  <td className="p-4 align-top text-ink/75 dark:text-white/62">{label}</td>
                  <td className="p-4 align-top text-ink/72 dark:text-white/78">{gt}</td>
                  <td className="p-4 align-top text-ink/72 dark:text-white/78">{dl}</td>
                  <td className="p-4 align-top text-ink/72 dark:text-white/78">{gpt}</td>
                  <td className="p-4 align-top font-medium text-ink dark:text-white">{castia}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="mt-6 text-center">
          <Link
            href="/s/demo"
            className="text-[13px] text-ink/80 underline decoration-ink/25 underline-offset-4 transition hover:text-ink dark:text-white/78 dark:decoration-white/25 dark:hover:text-white"
          >
            See a real song result, line by line →
          </Link>
        </p>

        <p className="mt-3 text-center text-[12.5px] leading-relaxed text-ink/62 dark:text-white/68">
          The full mechanism, sourced:{" "}
          <Link href="/compare/google-translate" className="underline decoration-ink/15 underline-offset-4 hover:text-ink/72 dark:decoration-white/20 dark:hover:text-white/72">
            vs. Google Translate
          </Link>
          {" · "}
          <Link href="/compare/deepl" className="underline decoration-ink/15 underline-offset-4 hover:text-ink/72 dark:decoration-white/20 dark:hover:text-white/72">
            vs. DeepL
          </Link>
          {" · "}
          <Link href="/compare/chatgpt-prompt" className="underline decoration-ink/15 underline-offset-4 hover:text-ink/72 dark:decoration-white/20 dark:hover:text-white/72">
            vs. a single ChatGPT prompt
          </Link>
        </p>
      </ScrollReveal>

      <ScrollReveal className="mx-auto mt-20 w-full max-w-3xl border-t border-black/[0.10] pt-16 dark:border-white/[0.10] sm:mt-24 sm:pt-20" delayMs={80}>
        <h2 className="text-center font-serif text-[1.6rem] leading-[1.25] text-ink dark:text-white sm:text-[1.9rem]">
          How does the Writers' Room actually work?
        </h2>
        <p className="mx-auto mt-4 max-w-lg text-center text-[13.5px] leading-relaxed text-ink/78 dark:text-white/75">
          Three roles, one line: a translator, a room of writers, an editor.
        </p>

        <HomePipelineFlow />

        <p className="mt-6 text-center text-[13px] text-ink/68 dark:text-white/62">
          <Link href="/how-it-works" className="underline decoration-ink/20 underline-offset-4 hover:text-ink/78 dark:decoration-white/20 dark:hover:text-white/78">
            See the full pipeline, including comics
          </Link>
        </p>
      </ScrollReveal>

      <ScrollReveal className="mx-auto mt-20 w-full max-w-2xl sm:mt-24" delayMs={80}>
        {/* dark:border-white/[0.12], not dark:border-transparent - this
            card's dark background (#181310) is the exact same hex as the
            page's own dark-mode background (paper-dark in tailwind.config.ts),
            confirmed via computed styles, not just eyeballed - with no
            border, the card was completely invisible as a distinct
            element in dark mode, just text floating on the page. */}
        <div className="rounded-2xl border border-black/[0.10] bg-black/[0.02] p-8 text-center dark:border dark:border-white/[0.12] dark:bg-[#181310] sm:p-12">
          <p className="font-serif text-[1.35rem] leading-[1.35] text-ink dark:text-white sm:text-[1.6rem]">
            Every AI has an opinion about your words.
            <br />
            Only one writes down why.
          </p>
          <p className="mx-auto mt-4 max-w-md text-[13px] leading-relaxed text-ink/78 dark:text-white/75">
            No invented details, no unexplained rewrites — a change that
            can't justify itself against the literal reading gets reverted
            before it ships, not just flagged.
          </p>
        </div>
      </ScrollReveal>

      <ScrollReveal className="mx-auto mt-20 w-full max-w-2xl border-t border-black/[0.10] pt-16 dark:border-white/[0.10] sm:mt-24 sm:pt-20" delayMs={80}>
        <h2 className="text-center font-serif text-[1.6rem] leading-[1.25] text-ink dark:text-white sm:text-[1.9rem]">
          Common questions
        </h2>
        <div className="mt-8 space-y-6">
          {HOMEPAGE_FAQS.map((faq) => (
            <div key={faq.question} className="border-b border-black/[0.10] pb-6 dark:border-white/[0.10]">
              <h3 className="font-serif text-[15px] text-ink dark:text-white">{faq.question}</h3>
              <p className="mt-2 text-[13px] leading-relaxed text-ink/78 dark:text-white/75">{faq.answer}</p>
            </div>
          ))}
        </div>
        <p className="mt-6 text-center text-[13px] text-ink/68 dark:text-white/62">
          <Link href="/faq" className="underline decoration-ink/20 underline-offset-4 hover:text-ink/78 dark:decoration-white/20 dark:hover:text-white/78">
            See all FAQs
          </Link>
          {" · "}
          <Link href="/pricing" className="underline decoration-ink/20 underline-offset-4 hover:text-ink/78 dark:decoration-white/20 dark:hover:text-white/78">
            See pricing
          </Link>
        </p>
      </ScrollReveal>

      <Footer />
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
        accent
          ? "border-accent/40 bg-accent/[0.08]"
          : dim
            ? "border-black/[0.09] bg-black/[0.01] dark:border-white/[0.10] dark:bg-white/[0.015]"
            : "border-black/[0.12] bg-black/[0.015] dark:border-white/10 dark:bg-white/[0.02]"
      }`}
    >
      <p className={`font-serif text-[13.5px] ${accent ? "text-ink dark:text-white" : dim ? "text-ink/78 dark:text-white/68" : "text-ink/85 dark:text-white/85"}`}>
        {title}
      </p>
      <p className={`mt-1 text-[11px] leading-snug ${dim ? "text-ink/62 dark:text-white/58" : "text-ink/75 dark:text-white/62"}`}>{body}</p>
    </div>
  );
}

function FlowArrow() {
  return (
    <span className="rotate-90 text-ink/38 dark:text-white/32 sm:rotate-0" aria-hidden="true">
      →
    </span>
  );
}

function MediumTile({
  href,
  title,
  tagline,
  continuing,
  children,
}: {
  href: string;
  title: string;
  tagline: string;
  // True when lib/mediumPreference.ts's stored value matches this tile -
  // the one thing the remembered preference still does now that "/"
  // no longer auto-redirects on it (see this file's top comment): a
  // quiet "pick up where you left off" label, not a decision made for
  // you.
  continuing?: boolean;
  children: React.ReactNode;
}) {
  return (
    // Resting state stays neutral - both tiles are meant to read as
    // equal choices (see this file's top comment), so an accent fill
    // at rest would tilt one over the other by nothing more than paint
    // order. The accent shows up on hover instead: it's the one moment
    // the two tiles ARE asymmetric (you're about to click exactly one
    // of them), so that's when the color that means "go" belongs.
    <Link
      href={href}
      className="group flex flex-col rounded-2xl border border-black/[0.12] bg-black/[0.015] p-5 text-left transition-all duration-300 hover:-translate-y-1 hover:border-accent/40 hover:bg-black/[0.03] hover:shadow-[0_24px_48px_-24px_rgba(184,86,46,0.18)] dark:border-white/10 dark:bg-white/[0.03] dark:hover:border-accent/50 dark:hover:bg-white/[0.05] dark:hover:shadow-[0_24px_48px_-24px_rgba(184,86,46,0.35)]"
    >
      <div className="overflow-hidden rounded-lg">{children}</div>
      <div className="mt-4 flex items-center gap-2">
        <h2 className="font-serif text-[1.15rem] text-ink dark:text-white">{title}</h2>
        {continuing && (
          <span className="text-[11px] text-ink/62 dark:text-white/65">— continue where you left off</span>
        )}
      </div>
      <p className="mt-1.5 text-[13px] leading-relaxed text-ink/68 dark:text-white/62">{tagline}</p>
    </Link>
  );
}
