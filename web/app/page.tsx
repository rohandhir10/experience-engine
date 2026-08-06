"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";
import { ScrollReveal } from "@/components/ScrollReveal";
import { readMediumPreference } from "@/lib/mediumPreference";

// "/" is now a neutral medium chooser, not the music workflow directly.
// Music and Webtoons are framed as equals here (same tile size, same
// visual weight) rather than a flagship-plus-experiment - the music
// workflow itself lives at /music (moved from here, unchanged; see
// app/music/page.tsx), and /comics is the webtoons workflow, now
// reachable from a real entry point instead of only by typing the URL.
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
// Skips the chooser entirely for a returning visitor: if
// lib/mediumPreference.ts has a remembered medium (written by /music,
// /comics, or the header's MediumSwitcher on every real arrival there),
// this redirects straight there instead of rendering the tiles. Nothing
// renders until that one-time check resolves, so a returning visitor
// never sees the chooser flash before being sent onward - the tradeoff
// is a blank first frame for a brand-new visitor instead, which is the
// cheaper flash of the two since it only ever happens once per browser.
export default function Home() {
  const router = useRouter();
  const [showChooser, setShowChooser] = useState(false);

  useEffect(() => {
    const preference = readMediumPreference();
    if (preference) {
      router.replace(preference === "music" ? "/music" : "/comics");
      return;
    }
    setShowChooser(true);
  }, [router]);

  if (!showChooser) {
    return null;
  }

  return (
    <main className="min-h-screen bg-paper-dark px-6 pb-28 pt-8 sm:px-10">
      <SiteHeader active="home" forceDark />

      <div className="mx-auto mt-16 flex w-full max-w-3xl flex-col items-center text-center sm:mt-20">
        <h1 className="animate-fade-up text-[2.1rem] font-semibold leading-[1.15] tracking-tight text-white sm:text-[2.6rem]">
          Adapt the feeling.
          <br />
          Not just the words.
        </h1>
        <p
          className="animate-fade-up mt-4 max-w-md text-[14px] text-white/40"
          style={{ animationDelay: "80ms" }}
        >
          Choose what you're adapting.
        </p>
      </div>

      <div
        className="animate-fade-up mx-auto mt-12 grid w-full max-w-3xl grid-cols-1 gap-5 sm:grid-cols-2"
        style={{ animationDelay: "120ms" }}
      >
        <MediumTile
          href="/music"
          title="Music"
          tagline="Adapt song lyrics — not translation, a rewrite that still means it."
        >
          <Image
            src="/screenshots/comparison-card.png"
            alt="A real CASTIA result: the literal reading next to the adapted line, with a plain-language reason for the change"
            width={672}
            height={637}
            className="w-full rounded-lg border border-white/10"
          />
        </MediumTile>

        <MediumTile
          href="/comics"
          title="Webtoons"
          badge="Beta"
          tagline="Adapt comic and webtoon dialogue, panel by panel."
        >
          <div className="flex h-full flex-col justify-center gap-3 rounded-lg border border-white/10 bg-white/[0.03] p-5">
            <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
              <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 shrink-0 fill-white/30">
                <path d="M4 4h16v12H7l-3 3V4z" />
              </svg>
              <span className="truncate text-[11px] text-white/35">panel-07.png</span>
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
        <p className="text-center text-[11px] uppercase tracking-[0.18em] text-white/30">
          Why not just paste it into a translator?
        </p>
        <h2 className="mt-3 text-center font-serif text-[1.6rem] leading-[1.25] text-white sm:text-[1.9rem]">
          One draft, no check, no explanation.
          <br />
          That's what everything else ships.
        </h2>
        <p className="mx-auto mt-4 max-w-lg text-center text-[13.5px] leading-relaxed text-white/45">
          Google Translate, DeepL, and a single AI prompt are all built to
          produce one fluent pass and stop. This is what a real result
          looks like once something actually checks that pass — a live
          screenshot of the product, not a mockup:
        </p>

        <div className="mx-auto mt-8 max-w-lg overflow-hidden rounded-2xl border border-white/10">
          <Image
            src="/screenshots/comparison-card.png"
            alt="A real Castia result: the literal reading next to the adapted line, with a plain-language reason for the change written underneath"
            width={672}
            height={637}
            className="w-full"
          />
        </div>
        <p className="mt-3 text-center text-[12px] text-white/30">
          A real adaptation, straight from the product — the reasoning
          underneath is the Judge's own, not decoration.
        </p>

        <p className="mx-auto mt-10 max-w-lg text-center text-[13.5px] leading-relaxed text-white/45">
          What makes that possible, mechanically — real, documented
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

        <p className="mt-5 text-center text-[12.5px] leading-relaxed text-white/35">
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
        <p className="text-center text-[11px] uppercase tracking-[0.18em] text-white/30">
          How it actually works
        </p>
        <h2 className="mt-3 text-center font-serif text-[1.6rem] leading-[1.25] text-white sm:text-[1.9rem]">
          A real Writers' Room, not one prompt.
        </h2>

        <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <PipelineStep
            n="1"
            title="Translator"
            body="One literal, anchor translation — the floor everything else is checked against."
          />
          <PipelineStep
            n="2"
            title="Creative Adapter"
            body="Five differently-angled rewrites, each taking a real liberty with phrasing, idiom, or rhythm."
          />
          <PipelineStep
            n="3"
            title="Judge"
            body="Scores every rewrite against the anchor, picks a winner, and writes down the real reason it departs from literal."
          />
        </div>

        <p className="mt-6 text-center text-[13px] text-white/40">
          <Link href="/how-it-works" className="underline decoration-white/20 underline-offset-4 hover:text-white/70">
            See the full pipeline, including comics
          </Link>
        </p>
      </ScrollReveal>

      <ScrollReveal className="mx-auto mt-20 w-full max-w-2xl sm:mt-24" delayMs={80}>
        <div className="rounded-2xl bg-[#181310] p-8 text-center sm:p-12">
          <p className="font-serif text-[1.35rem] leading-[1.35] text-white sm:text-[1.6rem]">
            Every AI has an opinion about your lyrics.
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

function PipelineStep({ n, title, body }: { n: string; title: string; body: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
      <span className="flex h-6 w-6 items-center justify-center rounded-full border border-white/15 text-[11px] text-white/40">
        {n}
      </span>
      <h3 className="mt-3 font-serif text-[1.05rem] text-white">{title}</h3>
      <p className="mt-1.5 text-[13px] leading-relaxed text-white/45">{body}</p>
    </div>
  );
}

function MediumTile({
  href,
  title,
  tagline,
  badge,
  children,
}: {
  href: string;
  title: string;
  tagline: string;
  badge?: string;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className="group flex flex-col rounded-2xl border border-white/10 bg-white/[0.03] p-5 text-left transition hover:border-white/20 hover:bg-white/[0.05]"
    >
      <div className="overflow-hidden rounded-lg">{children}</div>
      <div className="mt-4 flex items-center gap-2">
        <h2 className="font-serif text-[1.15rem] text-white">{title}</h2>
        {badge && (
          <span className="rounded-full bg-white/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-white/40">
            {badge}
          </span>
        )}
      </div>
      <p className="mt-1.5 text-[13px] leading-relaxed text-white/40">{tagline}</p>
    </Link>
  );
}
