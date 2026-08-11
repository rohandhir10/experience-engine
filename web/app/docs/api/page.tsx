import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";
import { JsonLd } from "@/components/JsonLd";
import { BreadcrumbNav } from "@/components/BreadcrumbNav";
import Link from "next/link";
import { contentByPath } from "@/lib/content";
import { LANGUAGES } from "@/lib/languages";
import { breadcrumbJsonLd, articleJsonLd } from "@/lib/schema";

const entry = contentByPath("/docs/api")!;

export const metadata = {
  title: entry.title,
  description: entry.description,
  alternates: { canonical: entry.path },
};

const ADAPT_REQUEST = `curl https://api.usecastia.com/v1/adapt \\
  -H "Authorization: Bearer castia_sk_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "text": "Tera hone laga hoon...",
    "source_language": "Hindi",
    "target_language": "English"
  }'`;

const ADAPT_RESPONSE = `{
  "id": "a1b2c3d4...",
  "hook": "Slowly becoming yours...",
  "sourceLanguage": "Hindi",
  "targetLanguage": "English",
  "sections": [
    {
      "id": "section-1",
      "literal": "I am slowly becoming yours",
      "aura": "Slowly, I'm becoming yours",
      "why": "Kept the confession's exact meaning; reordered only for natural English stress."
    }
  ],
  "original": [{ "id": "section-1", "text": "Tera hone laga hoon..." }],
  "phonemeRepetitionSimilarity": 0.82,
  "poeticRegister": "romantic, plainspoken"
}`;

const COMICS_REQUEST = `curl https://api.usecastia.com/v1/comics/adapt \\
  -H "Authorization: Bearer castia_sk_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "source_language": "Japanese",
    "target_language": "English",
    "panels": [
      { "id": "p1-b1", "text": "遅いよ、また", "voice": "Aiko" },
      { "id": "p1-b2", "text": "渋滞だったんだ", "voice": "Kenji" }
    ]
  }'`;

const COMICS_RESPONSE = `{
  "chapter_dna": {
    "artistic_thesis": "...",
    "genre_feel": "slice-of-life romance",
    "tone": "wry, affectionate",
    "ongoing_plot_context": "...",
    "characters": [
      { "name": "Aiko", "voice_description": "...", "honorific_register": "casual (plain form)", "relationships": ["Kenji: childhood friend"] }
    ]
  },
  "panels": [
    {
      "id": "p1-b1",
      "literal": "You're late. Again.",
      "adapted_text": "You're late. Again.",
      "why": "No rewrite earned its keep over the literal reading here."
    },
    {
      "id": "p1-b2",
      "literal": "It was traffic congestion.",
      "adapted_text": "Traffic. I swear.",
      "why": "Shortened to match a spoken excuse's rhythm; \\"I swear\\" carries Kenji's established defensive tone."
    }
  ]
}`;

export default function ApiDocsPage() {
  const breadcrumb = breadcrumbJsonLd([
    { name: "Home", path: "/" },
    { name: "API reference" },
  ]);
  const article = articleJsonLd({
    path: entry.path,
    headline: entry.title,
    description: entry.description,
    publishedDate: entry.publishedDate,
    updatedDate: entry.updatedDate,
  });

  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <JsonLd data={breadcrumb} />
      <JsonLd data={article} />
      <div className="mx-auto max-w-3xl">
        <SiteHeader />

        <div className="mt-10">
          <BreadcrumbNav items={[{ name: "Home", path: "/" }, { name: "API reference" }]} />
          <h1 className="mt-3 font-serif text-3xl text-ink dark:text-ink-dark sm:text-4xl">
            API reference.
          </h1>
          <p className="mt-4 max-w-prose text-[15px] leading-relaxed text-ink/55 dark:text-ink-dark/55">
            Two endpoints, both requiring an API key: <code className="rounded bg-black/[0.05] px-1.5 py-0.5 text-[13px] dark:bg-white/10">POST /v1/adapt</code> for
            song lyrics and <code className="rounded bg-black/[0.05] px-1.5 py-0.5 text-[13px] dark:bg-white/10">POST /v1/comics/adapt</code> for
            comic/webtoon dialogue. Both run the identical Translator → Creative
            Adapter → Judge pipeline the product itself uses — see{" "}
            <Link href="/how-it-works" className="underline decoration-ink/20 underline-offset-4">
              how it works
            </Link>{" "}
            for the mechanism. Currently Beta: both endpoints are functional and
            gated by real per-key quotas, but there's no published SDK and
            requests are synchronous only (more on that below).
          </p>
        </div>

        <section className="mt-14">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            Authentication
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            Pass your key as a bearer token: <code className="rounded bg-black/[0.05] px-1.5 py-0.5 text-[13px] dark:bg-white/10">Authorization: Bearer castia_sk_...</code>.
            Generate one from{" "}
            <Link href="/dashboard/settings" className="underline decoration-ink/20 underline-offset-4">
              your dashboard settings
            </Link>{" "}
            — the raw key is shown exactly once at creation and never again,
            only its prefix is stored for you to recognize it by afterward.
            A missing or invalid key returns <code className="rounded bg-black/[0.05] px-1.5 py-0.5 text-[13px] dark:bg-white/10">401</code>.
          </p>
        </section>

        <section className="mt-14">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            Rate limits
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            Each key has a daily request cap, checked and incremented
            atomically per request — 1,000 requests/day by default, though
            this is an environment-configurable setting on the server, so
            treat it as a starting point rather than a hard guarantee for
            every deployment. Exceeding it returns <code className="rounded bg-black/[0.05] px-1.5 py-0.5 text-[13px] dark:bg-white/10">429</code> with
            the actual configured limit stated in the error message. A cache
            hit — the identical text and language pair submitted before —
            still counts against the limit, but doesn't re-run the pipeline.
          </p>
        </section>

        <section className="mt-14">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            Errors
          </h2>
          <div className="mt-4 overflow-x-auto rounded-2xl border border-black/[0.10] dark:border-white/[0.11]">
            <table className="w-full min-w-[420px] text-left text-[13px]">
              <thead>
                <tr className="border-b border-black/[0.10] dark:border-white/[0.11]">
                  <th className="p-4 font-medium text-ink/50 dark:text-ink-dark/50">Status</th>
                  <th className="p-4 font-medium text-ink dark:text-ink-dark">Meaning</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-black/[0.10] dark:divide-white/[0.11]">
                {[
                  ["400", "Bad request - e.g. an unsupported language, or source and target set to the same language"],
                  ["401", "Missing or invalid API key"],
                  ["429", "Daily request limit exceeded for this key"],
                  ["500", "Something failed inside the pipeline itself - safe to retry"],
                ].map(([code, meaning]) => (
                  <tr key={code}>
                    <td className="p-4 align-top font-mono text-ink/70 dark:text-ink-dark/70">{code}</td>
                    <td className="p-4 align-top text-ink/60 dark:text-ink-dark/60">{meaning}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 max-w-prose text-[13px] leading-relaxed text-ink/50 dark:text-ink-dark/50">
            Every error body has the same shape: <code className="rounded bg-black/[0.05] px-1 py-0.5 text-[12px] dark:bg-white/10">{`{ "detail": "..." }`}</code>,
            with a specific, human-readable message - never a bare status code
            with nothing else.
          </p>
        </section>

        <section className="mt-14 border-t border-black/[0.10] pt-10 dark:border-white/[0.11]">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            POST /v1/adapt
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            Adapts a song lyric. <code className="rounded bg-black/[0.05] px-1.5 py-0.5 text-[13px] dark:bg-white/10">text</code> is
            the only required field — <code className="rounded bg-black/[0.05] px-1.5 py-0.5 text-[13px] dark:bg-white/10">target_language</code> defaults
            to English, and <code className="rounded bg-black/[0.05] px-1.5 py-0.5 text-[13px] dark:bg-white/10">source_language</code> is
            only required when the target isn't English (auto-detect only
            covers the "anything → English" direction). Supported languages,
            either side of a direction:{" "}
            {LANGUAGES.join(", ")}.
          </p>
          <CodeBlock label="Request">{ADAPT_REQUEST}</CodeBlock>
          <CodeBlock label="Response (200)">{ADAPT_RESPONSE}</CodeBlock>
        </section>

        <section className="mt-14 border-t border-black/[0.10] pt-10 dark:border-white/[0.11]">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            POST /v1/comics/adapt
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            Adapts a chapter's worth of comic/webtoon dialogue at once.{" "}
            <code className="rounded bg-black/[0.05] px-1.5 py-0.5 text-[13px] dark:bg-white/10">panels</code> is
            a flat list of speech-bubble entries, not literally one per
            panel — a panel with three bubbles sends three entries. Naming
            a speaker in <code className="rounded bg-black/[0.05] px-1.5 py-0.5 text-[13px] dark:bg-white/10">voice</code> drives
            per-character voice and honorific-register consistency across
            the chapter; an unattributed bubble still adapts, it just
            doesn't get that benefit. A Chapter DNA profile — cast, tone,
            and the chapter's dramatic context — is built automatically and
            returned alongside the per-bubble results, same as the product
            UI shows.
          </p>
          <CodeBlock label="Request">{COMICS_REQUEST}</CodeBlock>
          <CodeBlock label="Response (200)">{COMICS_RESPONSE}</CodeBlock>
        </section>

        <section className="mt-14 border-t border-black/[0.10] pt-10 dark:border-white/[0.11]">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            Known limitations
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            Both endpoints are synchronous — the request blocks until the
            full pipeline finishes, with no job/poll pattern yet for API
            callers (the browser-facing app has one internally; it isn't
            exposed on <code className="rounded bg-black/[0.05] px-1.5 py-0.5 text-[13px] dark:bg-white/10">/v1/*</code> yet).
            A short lyric or a few panels finishes well within a typical
            client timeout; a long multi-section song or a large chapter can
            take minutes, so set your HTTP client's timeout generously or
            keep individual requests small until an async job endpoint
            ships here too.
          </p>
        </section>

        <p className="mt-14 max-w-prose text-[13px] leading-relaxed text-ink/45 dark:text-ink-dark/45">
          See the full pipeline mechanics on{" "}
          <Link href="/how-it-works" className="underline decoration-ink/20 underline-offset-4">
            how it works
          </Link>
          , or general questions on the{" "}
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

function CodeBlock({ label, children }: { label: string; children: string }) {
  return (
    <div className="mt-4">
      <p className="text-[11px] uppercase tracking-[0.1em] text-ink/35 dark:text-ink-dark/35">
        {label}
      </p>
      <pre className="mt-2 overflow-x-auto rounded-xl border border-black/[0.10] bg-black/[0.03] p-4 text-[12.5px] leading-relaxed text-ink/75 dark:border-white/[0.11] dark:bg-white/[0.03] dark:text-ink-dark/75">
        <code>{children}</code>
      </pre>
    </div>
  );
}
