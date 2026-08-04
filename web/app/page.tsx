"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
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
// one IS reachable and working, just not yet at feature parity: no
// save/collections/share-link, and the adapt call is still synchronous).
// Remove the pill only once that parity gap actually closes - see
// docs/CAPABILITY_MATRIX.md for what's tracked as done.
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
            alt="A real AURA result: the literal reading next to the adapted line, with a plain-language reason for the change"
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
    </main>
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
