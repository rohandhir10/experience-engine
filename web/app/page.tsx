import type { ReactNode } from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";
import { JsonLd } from "@/components/JsonLd";
import { webPageJsonLd, faqPageJsonLd } from "@/lib/schema";
import { homepageFaqs } from "@/lib/faqs";

export const metadata: Metadata = {
  title: "Webtoon localization that keeps the feeling",
  description: "Adapt webtoon and comic dialogue with context-aware rewrites, bubble-level review, optional speech-bubble redraw, and clear explanations for changes.",
  alternates: { canonical: "/" },
  openGraph: {
    title: "Castia — Webtoon localization that keeps the feeling",
    description: "Adapt webtoon and comic dialogue with context-aware rewrites, bubble-level review, optional speech-bubble redraw, and clear explanations for changes.",
    url: "/",
  },
};

const PAGE_UPDATED_DATE = "2026-10-25";
const HOMEPAGE_FAQS = homepageFaqs();

function ArrowUpRight() {
  return (
    <svg aria-hidden="true" viewBox="0 0 20 20" className="h-4 w-4" fill="none">
      <path d="M5 15 15 5M6 5h9v9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function StepNumber({ children }: { children: ReactNode }) {
  return (
    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-black/10 bg-white/70 font-mono text-[12px] text-ink/65 dark:border-white/10 dark:bg-white/[0.04] dark:text-white/65">
      {children}
    </span>
  );
}

export default function Home() {
  return (
    <main className="min-h-screen overflow-hidden bg-paper px-5 pb-16 pt-5 text-ink dark:bg-paper-dark dark:text-ink-dark sm:px-8 sm:pt-7">
      <JsonLd data={webPageJsonLd({
        path: "/",
        name: "Castia — Webtoon localization that keeps the feeling",
        description: "Adapt webtoon and comic dialogue with context-aware rewrites, bubble-level review, optional panel redraw, and clear explanations for each change.",
        updatedDate: PAGE_UPDATED_DATE,
      })} />
      <JsonLd data={faqPageJsonLd(HOMEPAGE_FAQS)} />

      <SiteHeader active="webtoons" />

      <section className="relative mx-auto grid w-full max-w-6xl items-center gap-12 pb-20 pt-16 sm:pb-24 sm:pt-24 lg:grid-cols-[1.03fr_0.97fr] lg:gap-10 lg:pt-28">
        <div className="relative z-10">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-black/[0.10] bg-white/60 px-3 py-1.5 text-[11px] font-medium tracking-[0.12em] text-ink/65 dark:border-white/10 dark:bg-white/[0.04] dark:text-white/65">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" />
            BUILT FOR WEBTOON DIALOGUE
          </div>
          <h1 className="max-w-2xl font-serif text-[2.7rem] leading-[1.04] tracking-[-0.045em] sm:text-6xl lg:text-[4.45rem]">
            Keep the story.
            <br />
            <span className="text-accent">Change the language.</span>
          </h1>
          <p className="mt-6 max-w-xl text-[15px] leading-7 text-ink/70 dark:text-white/68 sm:text-base">
            Localize webtoon dialogue without flattening the character behind it. Castia helps you move from panels to editable, context-aware rewrites—with the original text, adapted lines, and reasons for changes kept together.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link href="/comics" className="inline-flex min-h-12 items-center justify-center gap-2 rounded-full bg-accent px-6 text-[14px] font-medium text-white transition hover:brightness-110 active:scale-[0.98]">
              Open the webtoon workspace <ArrowUpRight />
            </Link>
            <Link href="/manga-webtoon-translation" className="inline-flex min-h-12 items-center justify-center rounded-full border border-black/15 px-6 text-[14px] font-medium transition hover:bg-black/[0.035] dark:border-white/15 dark:hover:bg-white/[0.05]">
              How localization works
            </Link>
          </div>
          <div className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-2 text-[12px] text-ink/58 dark:text-white/55">
            <span className="inline-flex items-center gap-2"><span className="text-accent">✓</span> Start without an account</span>
            <span className="inline-flex items-center gap-2"><span className="text-accent">✓</span> Review every line</span>
            <span className="inline-flex items-center gap-2"><span className="text-accent">✓</span> No fabricated quality scores</span>
          </div>
        </div>

        <div className="relative mx-auto w-full max-w-[560px]">
          <div aria-hidden="true" className="absolute -inset-8 rounded-[2.5rem] bg-accent/[0.08] blur-3xl" />
          <div className="relative overflow-hidden rounded-[1.65rem] border border-black/[0.12] bg-[#f7f2ee] p-3 shadow-[0_28px_90px_-42px_rgba(48,35,58,0.36)] dark:border-white/10 dark:bg-[#201d24] sm:p-4">
            <div className="flex items-center justify-between border-b border-black/10 px-2 pb-3 dark:border-white/10">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-[#d9a1a1]" />
                <span className="h-2 w-2 rounded-full bg-[#e4c58b]" />
                <span className="h-2 w-2 rounded-full bg-[#9bbba5]" />
                <span className="ml-2 text-[11px] font-medium tracking-wide text-ink/55 dark:text-white/55">CHAPTER REVIEW</span>
              </div>
              <span className="rounded-full border border-accent/20 bg-accent/[0.08] px-2.5 py-1 text-[10px] text-accent">Preview</span>
            </div>
            <div className="grid gap-3 py-3 sm:grid-cols-[0.82fr_1.18fr]">
              <div className="relative flex min-h-[270px] flex-col justify-between overflow-hidden rounded-xl bg-[#e8d8d5] p-4 dark:bg-[#40323d] sm:min-h-[340px]">
                <div className="absolute -right-9 top-7 h-40 w-40 rounded-full bg-[#c88c91]/50 blur-sm" />
                <div className="absolute bottom-[-22px] left-[-8px] h-52 w-40 -rotate-12 rounded-[45%_45%_12%_12%] bg-[#6e526a]" />
                <div className="absolute bottom-[-18px] right-[-18px] h-44 w-32 rotate-12 rounded-t-[48%] bg-[#9e737f]" />
                <div className="relative z-10 flex items-start justify-between">
                  <span className="rounded-full bg-white/75 px-2.5 py-1 text-[10px] font-medium text-[#493a49]">Panel 04</span>
                  <span className="text-[10px] tracking-[0.16em] text-[#493a49]/65">01 / 06</span>
                </div>
                <div className="relative z-10 mx-auto mb-3 max-w-[190px] rounded-[1.2rem] rounded-bl-sm border border-[#6e526a]/15 bg-[#fffaf5] px-4 py-3 text-center text-[12px] leading-5 text-[#473747] shadow-sm">
                  “帰ってきたんだ…こんなに時間が経ってから。”
                  <span className="absolute -bottom-2 left-4 h-3 w-3 rotate-45 border-b border-l border-[#6e526a]/15 bg-[#fffaf5]" />
                </div>
              </div>
              <div className="flex min-w-0 flex-col gap-3">
                <div className="rounded-xl border border-black/[0.09] bg-white/75 p-4 dark:border-white/10 dark:bg-white/[0.04]">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[10px] font-semibold tracking-[0.13em] text-ink/50 dark:text-white/50">ORIGINAL · JA</span>
                    <span className="text-[10px] text-ink/45 dark:text-white/45">Original · Japanese</span>
                  </div>
                  <p className="mt-3 text-[13px] leading-5 text-ink/80 dark:text-white/80">“You came back… after all this time?”</p>
                </div>
                <div className="rounded-xl border border-accent/25 bg-white p-4 dark:bg-[#29232e]">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[10px] font-semibold tracking-[0.13em] text-accent">LOCALIZED · EN</span>
                    <span className="rounded-full bg-accent/10 px-2 py-0.5 text-[10px] text-accent">Editable</span>
                  </div>
                  <p className="mt-3 font-serif text-[17px] leading-6 text-ink dark:text-white">“You actually came back… after all this time.”</p>
                  <p className="mt-3 border-t border-black/[0.08] pt-3 text-[11px] leading-5 text-ink/60 dark:border-white/10 dark:text-white/60">Illustrative example of tone-aware rewriting, not a live engine result.</p>
                </div>
                <div className="rounded-xl border border-black/[0.09] bg-white/55 p-3 dark:border-white/10 dark:bg-white/[0.025]">
                  <div className="flex items-center gap-2 text-[11px] font-medium text-ink/70 dark:text-white/70">
                    <svg viewBox="0 0 20 20" aria-hidden="true" className="h-4 w-4 text-accent" fill="none"><path d="M10 2.5 12 7.8l5.5 2.2-5.5 2.2-2 5.3-2-5.3L2.5 10l5.5-2.2L10 2.5Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /></svg>
                    Why the wording changes
                  </div>
                  <p className="mt-1.5 text-[11px] leading-5 text-ink/58 dark:text-white/55">“Actually” adds disbelief and hurt without spelling out what the character feels.</p>
                </div>
              </div>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-black/10 px-2 pt-3 text-[10px] text-ink/50 dark:border-white/10 dark:text-white/50">
              <span>Concept preview · sample copy</span>
              <span>Original → adapted → reason</span>
            </div>
          </div>
          <p className="mt-4 text-center text-[11px] text-ink/45 dark:text-white/45">A visual illustration of the review experience—not a screenshot of a live session.</p>
        </div>
      </section>

      <section className="mx-auto max-w-6xl border-y border-black/[0.09] py-7 dark:border-white/[0.09]">
        <div className="grid gap-6 sm:grid-cols-3 sm:gap-8">
          <div><p className="text-[11px] font-semibold tracking-[0.14em] text-accent">01 / CONTEXT</p><p className="mt-2 text-[14px] font-medium">Keep the character in the line</p><p className="mt-1.5 text-[12px] leading-5 text-ink/60 dark:text-white/58">Dialogue is reviewed as dialogue—not as a string of isolated words.</p></div>
          <div><p className="text-[11px] font-semibold tracking-[0.14em] text-accent">02 / CONTROL</p><p className="mt-2 text-[14px] font-medium">Keep the human in the loop</p><p className="mt-1.5 text-[12px] leading-5 text-ink/60 dark:text-white/58">Inspect detected text, edit it, and review the adaptation before you use it.</p></div>
          <div><p className="text-[11px] font-semibold tracking-[0.14em] text-accent">03 / CLARITY</p><p className="mt-2 text-[14px] font-medium">Know why a line changed</p><p className="mt-1.5 text-[12px] leading-5 text-ink/60 dark:text-white/58">See the original, the rewrite, and a plain-language explanation together.</p></div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl py-20 sm:py-24">
        <div className="max-w-2xl">
          <p className="text-[11px] font-semibold tracking-[0.16em] text-accent">A WORKFLOW, NOT A TEXT BOX</p>
          <h2 className="mt-4 font-serif text-3xl leading-tight tracking-[-0.03em] sm:text-4xl">From a chapter of panels to a reviewable localization.</h2>
          <p className="mt-4 text-[14px] leading-6 text-ink/65 dark:text-white/62">Start with the pages you have. Keep control of the text at every step, and know where the current beta still needs human attention.</p>
        </div>
        <div className="mt-10 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[
            { n: "01", title: "Upload panels", body: "Add panel images or chapter strips. Castia prepares the images into a reviewable sequence." },
            { n: "02", title: "Extract dialogue", body: "OCR detects text regions. Check and correct the extracted text before adapting." },
            { n: "03", title: "Adapt each bubble", body: "Run the adaptation workflow and review the rewritten dialogue alongside its explanation." },
            { n: "04", title: "Review & export", body: "Make your edits, optionally redraw supported speech bubbles, and export the chapter text." },
          ].map((step) => (
            <article key={step.n} className="rounded-2xl border border-black/[0.10] bg-white/45 p-5 dark:border-white/10 dark:bg-white/[0.025]">
              <StepNumber>{step.n}</StepNumber>
              <h3 className="mt-5 text-[15px] font-medium">{step.title}</h3>
              <p className="mt-2 text-[12px] leading-5 text-ink/62 dark:text-white/58">{step.body}</p>
            </article>
          ))}
        </div>
        <div className="mt-5 rounded-2xl border border-accent/20 bg-accent/[0.045] p-5 sm:flex sm:items-start sm:gap-4">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-accent/20 text-accent" aria-hidden="true">i</span>
          <div className="mt-3 sm:mt-0">
            <p className="text-[13px] font-medium">A transparent beta, with real limits</p>
            <p className="mt-1 text-[12px] leading-5 text-ink/65 dark:text-white/60">Current panel redraw supports speech-bubble text; sound effects embedded in artwork are not redrawn yet. OCR reading order can need correction, and persistent character memory is available when signed in but matches characters by exact name. Human review remains essential.</p>
            <Link href="/manga-webtoon-translation" className="mt-3 inline-flex items-center gap-1 text-[12px] font-medium text-accent hover:underline">Read the capability details <ArrowUpRight /></Link>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl pb-20">
        <div className="overflow-hidden rounded-[1.75rem] bg-[#29222f] px-6 py-10 text-white sm:px-10 sm:py-12 lg:flex lg:items-center lg:justify-between lg:gap-10">
          <div className="max-w-xl">
            <p className="text-[11px] font-semibold tracking-[0.16em] text-[#d4b5e9]">YOUR NEXT CHAPTER</p>
            <h2 className="mt-4 font-serif text-3xl leading-tight tracking-[-0.03em] sm:text-4xl">Try it on your own panels.</h2>
            <p className="mt-4 text-[14px] leading-6 text-white/70">Upload a chapter, inspect the extracted dialogue, and decide which rewrites deserve to stay. No need to commit to a black-box result.</p>
          </div>
          <div className="mt-7 flex shrink-0 flex-col gap-3 sm:flex-row lg:mt-0 lg:flex-col">
            <Link href="/comics" className="inline-flex min-h-12 items-center justify-center gap-2 rounded-full bg-white px-6 text-[14px] font-medium text-[#29222f] transition hover:bg-white/90">Launch workspace <ArrowUpRight /></Link>
            <Link href="/pricing" className="inline-flex min-h-12 items-center justify-center rounded-full border border-white/25 px-6 text-[14px] font-medium text-white transition hover:bg-white/[0.08]">See access & pricing</Link>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-3xl border-t border-black/[0.09] pt-14 dark:border-white/[0.09]">
        <p className="text-[11px] font-semibold tracking-[0.16em] text-accent">QUESTIONS, ANSWERED</p>
        <h2 className="mt-3 font-serif text-3xl tracking-[-0.03em]">Before you start</h2>
        <div className="mt-7 divide-y divide-black/10 dark:divide-white/10">
          {HOMEPAGE_FAQS.map((faq) => (
            <details key={faq.question} className="group py-4">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-[14px] font-medium marker:hidden">
                {faq.question}
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-black/10 text-ink/55 transition group-open:rotate-45 dark:border-white/10 dark:text-white/55" aria-hidden="true">+</span>
              </summary>
              <p className="max-w-2xl pt-3 pr-8 text-[13px] leading-6 text-ink/65 dark:text-white/62">{faq.answer}</p>
            </details>
          ))}
        </div>
        <p className="mt-7 text-[11px] text-ink/45 dark:text-white/45">Updated <time dateTime={PAGE_UPDATED_DATE}>{new Date(PAGE_UPDATED_DATE + "T00:00:00Z").toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric", timeZone: "UTC" })}</time></p>
      </section>

      <Footer />
    </main>
  );
}
