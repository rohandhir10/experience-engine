import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";
import { PipelineDiagramDark } from "@/components/PipelineDiagramDark";
import { ComicsPipelineDiagram } from "@/components/ComicsPipelineDiagram";
import Link from "next/link";

export const metadata = {
  title: "How it works",
  description:
    "The real Writers' Room pipeline behind Castia: a literal Translator anchor, five Creative Adapter rewrites, and a Judge that scores against the anchor and logs every real change with a reason — for both music and comics.",
  alternates: { canonical: "/how-it-works" },
};

export default function HowItWorksPage() {
  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <div className="mx-auto max-w-3xl">
        <SiteHeader />

        <div className="mt-10">
          <h1 className="font-serif text-3xl text-ink dark:text-ink-dark sm:text-4xl">
            A real Writers' Room, not one prompt.
          </h1>
          <p className="mt-4 max-w-prose text-[15px] leading-relaxed text-ink/55 dark:text-ink-dark/55">
            Castia doesn't ask a single model to translate a line and call
            it done. Every line — whether it's a song lyric or a comic
            panel's dialogue — goes through the same three-stage pipeline,
            and every departure from a literal translation ships with a
            plain-language reason instead of a silent rewrite.
          </p>
        </div>

        <div className="mt-12 space-y-6">
          <Step
            n="1"
            title="Translator"
            body="Produces one literal, anchor translation of the source line. This isn't shown as the final output — it's the floor everything else is checked against, so a later rewrite can be judged against what the line actually says, not just what it might mean."
          />
          <Step
            n="2"
            title="Creative Adapter"
            body="Produces five differently-angled creative rewrites of the same line, each taking a different liberty with phrasing, idiom, or rhythm — never five copies of the same idea."
          />
          <Step
            n="3"
            title="Judge"
            body="Scores each of the five rewrites against the Translator's literal anchor and against each other, picks a winner, and writes down the specific, real reason it departs from a literal translation. If none of the five earns a genuine improvement, the literal anchor ships instead of a manufactured difference."
          />
        </div>

        <div className="mt-16 rounded-2xl bg-[#181310] p-8 sm:p-10">
          <p className="text-[12px] uppercase tracking-[0.15em] text-white/25">Music</p>
          <h2 className="mt-3 max-w-lg font-serif text-[1.5rem] leading-[1.25] text-white sm:text-[1.7rem]">
            Source lyrics in, verified output out.
          </h2>
          <div className="mt-8">
            <PipelineDiagramDark />
          </div>
        </div>

        <div className="mt-8 rounded-2xl bg-[#141a2b] p-8 sm:p-10">
          <p className="text-[12px] uppercase tracking-[0.15em] text-white/25">
            Webtoons &amp; comics (Beta)
          </p>
          <h2 className="mt-3 max-w-lg font-serif text-[1.5rem] leading-[1.25] text-white sm:text-[1.7rem]">
            Real OCR, then the identical Writers' Room.
          </h2>
          <p className="mt-3 max-w-xl text-[13px] leading-relaxed text-white/40">
            A chapter's panels go through Google Cloud Vision OCR, then
            Chapter DNA (a cast/tone profile for the whole chapter), then
            the same Translator → Creative Adapter → Judge pipeline the
            music side uses — not a separate, lesser engine.
          </p>
          <div className="mt-8">
            <ComicsPipelineDiagram />
          </div>
        </div>

        <p className="mt-12 max-w-prose text-[14px] leading-relaxed text-ink/50 dark:text-ink-dark/50">
          Try it on a real result first —{" "}
          <Link href="/s/demo" className="underline decoration-ink/20 underline-offset-4">
            see the worked example
          </Link>{" "}
          or read the{" "}
          <Link href="/faq" className="underline decoration-ink/20 underline-offset-4">
            FAQ
          </Link>
          .
        </p>

        <Footer />
      </div>
    </main>
  );
}

function Step({ n, title, body }: { n: string; title: string; body: string }) {
  return (
    <div className="flex gap-5">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-black/10 font-serif text-[13px] text-ink/50 dark:border-white/10 dark:text-ink-dark/50">
        {n}
      </div>
      <div>
        <h3 className="font-serif text-lg text-ink dark:text-ink-dark">{title}</h3>
        <p className="mt-1.5 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
          {body}
        </p>
      </div>
    </div>
  );
}
