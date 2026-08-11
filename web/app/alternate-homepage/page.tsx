import Image from "next/image";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { UseCaseTabs } from "@/components/UseCaseTabs";
import { PipelineDiagram } from "@/components/PipelineDiagram";
import { LANGUAGES } from "@/lib/languages";

export const metadata = {
  title: "Castia — an alternate layout",
  description: "A visual-forward homepage layout, built around real product screenshots.",
  robots: { index: false, follow: false },
};

// A second homepage layout (not linked from primary nav), built to test
// a more visual, image-forward structure against the existing
// text-forward one (app/page.tsx). Every screenshot on this page is a
// real render of the real app — see scripts/capture-screenshots.mjs,
// which targets a handful of inert `data-screenshot="..."` attributes
// added to InputScreen.tsx/ComparisonCard.tsx for exactly this purpose.
// Nothing here is an AI-generated mockup image or a fabricated UI state.
// The one exception is the "Keep what you find" section near the
// bottom, which is a small illustrative diagram (star + pills), not a
// screenshot — a real screenshot of that feature would show a
// signed-out prompt (this page can't authenticate), which would be
// accurate but not informative, so it's diagrammed instead, labeled
// honestly rather than passed off as a captured UI state.
export default function AlternateHomepage() {
  return (
    <main className="min-h-screen bg-paper px-6 pb-28 pt-8 dark:bg-paper-dark sm:px-10">
      <div className="mx-auto max-w-5xl">
        <SiteHeader active="home" />
      </div>

      {/* Hero: a colored panel (Cartesia's product-announcement banner,
          adapted) with the real homepage screenshot floating inside it -
          the actual UI, not a rendering of it. */}
      <div className="mx-auto mt-10 max-w-5xl">
        <div
          className="overflow-hidden rounded-3xl px-8 pb-0 pt-12 text-center sm:px-16 sm:pt-16"
          style={{ background: "linear-gradient(160deg, #b8562e 0%, #6b2f16 100%)" }}
        >
          <h1 className="font-serif text-[2rem] leading-[1.2] text-white sm:text-[2.6rem]">
            Adapt the feeling.
            <br />
            Not just the words.
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-[15px] leading-relaxed text-white/78">
            Six languages, any direction. Every real change logged with a reason —
            not a translation you have to take on faith.
          </p>
          <div className="mt-7 flex items-center justify-center gap-3">
            <Link
              href="/music#lyrics"
              className="rounded-full bg-white px-6 py-2.5 text-[14px] font-medium text-black transition active:scale-[0.97]"
            >
              Try CASTIA
            </Link>
            <Link
              href="/sign-in"
              className="rounded-full border border-white/25 px-6 py-2.5 text-[14px] font-medium text-white transition hover:bg-white/10"
            >
              Sign in
            </Link>
          </div>

          <div className="mx-auto mt-10 max-w-2xl translate-y-8">
            <div className="overflow-hidden rounded-t-2xl border border-b-0 border-white/10 shadow-2xl">
              <Image
                src="/screenshots/hero.png"
                alt="CASTIA's paste-lyrics screen: language picker, YouTube import toggle, and the adaptation box"
                width={672}
                height={680}
                className="w-full"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Intro, 2-col — mirrors the reference's short mission statement
          block directly under the hero banner. */}
      <div className="mx-auto mt-24 max-w-5xl grid gap-8 sm:grid-cols-2">
        <h2 className="font-serif text-[1.6rem] leading-[1.3] text-ink dark:text-ink-dark">
          Built to keep what a song is actually doing,
          <span className="text-accent"> not just what it says.</span>
        </h2>
        <p className="text-[14px] leading-relaxed text-ink/78 dark:text-ink-dark/78">
          Most translation tools optimize for word-for-word accuracy and lose
          everything that made the song worth adapting — the repetition, the
          restraint, the specific image the writer chose on purpose. CASTIA
          keeps a literal reading as the floor, then earns every real
          departure from it with a reason you can actually check.
        </p>
      </div>

      {/* Big screenshot showcase, tabbed by audience — the reference's
          "frontier research, deployed in every conversation" section. */}
      <div className="mx-auto mt-20 max-w-5xl rounded-3xl bg-black/[0.02] p-8 dark:bg-white/[0.02] sm:p-12">
        <p className="text-[12px] uppercase tracking-[0.15em] text-ink/68 dark:text-ink-dark/68">
          One engine, several reasons to use it
        </p>
        <div className="mt-8 grid gap-10 sm:grid-cols-2 sm:items-center">
          <UseCaseTabs />
          <div className="overflow-hidden rounded-xl border border-black/[0.12] shadow-lg dark:border-white/[0.12]">
            <Image
              src="/screenshots/comparison-card.png"
              alt="A real CASTIA result: the literal reading next to the adapted line, with a plain-language reason for the change"
              width={672}
              height={637}
              className="w-full"
            />
          </div>
        </div>
      </div>

      {/* Real-facts row, replacing the reference's "trusted by" customer
          logos - there is no adoption data to show honestly, so this
          states verifiable facts about the product instead of implying
          a customer base that doesn't exist. */}
      <div className="mx-auto mt-16 max-w-5xl">
        <div className="flex flex-wrap items-center justify-center gap-3 rounded-2xl border border-black/[0.10] bg-black/[0.015] px-6 py-5 dark:border-white/[0.10] dark:bg-white/[0.015]">
          {[
            "6 languages, any direction",
            "Every change logged with a reason",
            "A literal reading, always kept",
          ].map((fact) => (
            <span
              key={fact}
              className="rounded-full border border-black/[0.12] px-3 py-1 text-[12px] text-ink/68 dark:border-white/[0.12] dark:text-ink-dark/68"
            >
              {fact}
            </span>
          ))}
        </div>
      </div>

      {/* Architecture — a real diagram of the actual multi-agent
          pipeline, since there's no UI surface that shows this directly
          for a screenshot to capture honestly. */}
      <div className="mx-auto mt-24 max-w-5xl">
        <h2 className="max-w-lg font-serif text-[1.6rem] leading-[1.3] text-ink dark:text-ink-dark">
          Not one model guessing.
          <br />A room that has to agree.
        </h2>
        <p className="mt-3 max-w-xl text-[14px] leading-relaxed text-ink/78 dark:text-ink-dark/78">
          A literal translation is generated first and never discarded — every
          later step is checked against it, not just asked to "sound better."
        </p>
        <div className="mt-8">
          <PipelineDiagram />
        </div>
      </div>

      {/* Evidence discipline — the thing that actually differentiates
          the audit trail from a plausible-sounding LLM claim. */}
      <div className="mx-auto mt-24 max-w-5xl grid gap-8 sm:grid-cols-2 sm:items-center">
        <div>
          <p className="text-[12px] uppercase tracking-[0.15em] text-accent">Evidence, not vibes</p>
          <h2 className="mt-3 font-serif text-[1.6rem] leading-[1.3] text-ink dark:text-ink-dark">
            Every claim is checked in code, not just asked of the model.
          </h2>
        </div>
        <p className="text-[14px] leading-relaxed text-ink/78 dark:text-ink-dark/78">
          A deterministic pass compares the shipped line against the literal
          anchor: is every real change accounted for, is the reason given for
          it real, does a repeated line actually still repeat. Nothing here
          is self-graded by the same model being checked.
        </p>
      </div>

      {/* Keep what you find — diagrammed the same honest way the
          primary homepage's MockWindow cards are, not screenshotted:
          this page can't authenticate, so a real screenshot would show
          a signed-out prompt rather than the feature itself. */}
      <div className="mx-auto mt-24 max-w-5xl rounded-3xl bg-black/[0.02] p-8 dark:bg-white/[0.02] sm:p-12">
        <div className="grid gap-8 sm:grid-cols-2 sm:items-center">
          <div>
            <h2 className="font-serif text-[1.6rem] leading-[1.3] text-ink dark:text-ink-dark">
              Keep what you find.
            </h2>
            <p className="mt-3 max-w-md text-[14px] leading-relaxed text-ink/78 dark:text-ink-dark/78">
              Star a result or file it into a collection — it's there next
              time, tied to your account, not lost in a chat history.
            </p>
          </div>
          <div className="rounded-xl border border-black/[0.12] bg-white/70 p-5 dark:border-white/[0.12] dark:bg-white/[0.03]">
            <div className="flex items-center gap-3">
              <svg viewBox="0 0 24 24" className="h-4 w-4 shrink-0 fill-accent" aria-hidden="true">
                <path d="M12 3.5l2.6 5.3 5.9.85-4.25 4.15 1 5.85L12 16.9l-5.25 2.75 1-5.85L3.5 9.65l5.9-.85z" />
              </svg>
              <div className="flex flex-wrap gap-1.5">
                <span className="rounded-full border border-black/[0.12] px-2 py-0.5 text-[11px] text-ink/68 dark:border-white/[0.12] dark:text-ink-dark/68">
                  Hindi Rock
                </span>
                <span className="rounded-full border border-black/[0.12] px-2 py-0.5 text-[11px] text-ink/68 dark:border-white/[0.12] dark:text-ink-dark/68">
                  Covers
                </span>
              </div>
            </div>
            <p className="mt-3 text-[11px] text-ink/68 dark:text-ink-dark/68">
              {LANGUAGES.length} languages supported, any pairing.
            </p>
          </div>
        </div>
      </div>

      {/* Final CTA split. */}
      <div className="mx-auto mt-24 max-w-5xl rounded-3xl border border-black/[0.12] p-10 text-center dark:border-white/[0.12] sm:p-14">
        <h2 className="font-serif text-[1.8rem] text-ink dark:text-ink-dark">
          Your song starts here.
        </h2>
        <div className="mt-6 flex items-center justify-center gap-3">
          <Link
            href="/music#lyrics"
            className="rounded-full bg-ink px-7 py-3 text-[14px] font-medium text-paper transition active:scale-[0.97] dark:bg-ink-dark dark:text-paper-dark"
          >
            Adapt a song
          </Link>
          <Link
            href="/sign-in"
            className="rounded-full border border-black/10 px-7 py-3 text-[14px] text-ink/78 transition hover:text-ink dark:border-white/10 dark:text-ink-dark/78 dark:hover:text-ink-dark"
          >
            Sign in
          </Link>
        </div>
      </div>

      <footer className="mx-auto mt-20 max-w-5xl border-t border-black/[0.10] pt-8 text-center text-[12px] text-ink/68 dark:border-white/[0.10] dark:text-ink-dark/68">
        <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
          <Link href="/" className="hover:text-ink/72 dark:hover:text-ink-dark/72">
            Home
          </Link>
          <Link href="/pricing" className="hover:text-ink/72 dark:hover:text-ink-dark/72">
            Pricing
          </Link>
          <Link href="/sign-in" className="hover:text-ink/72 dark:hover:text-ink-dark/72">
            Sign in
          </Link>
          <Link href="/dashboard" className="hover:text-ink/72 dark:hover:text-ink-dark/72">
            Dashboard
          </Link>
        </div>
      </footer>
    </main>
  );
}
