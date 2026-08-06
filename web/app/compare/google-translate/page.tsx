import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";
import { JsonLd } from "@/components/JsonLd";
import { BreadcrumbNav } from "@/components/BreadcrumbNav";
import { SourceList } from "@/components/SourceList";
import { ScreenshotSlot } from "@/components/ScreenshotSlot";
import Link from "next/link";
import { contentByPath } from "@/lib/content";
import { breadcrumbJsonLd, articleJsonLd } from "@/lib/schema";

const entry = contentByPath("/compare/google-translate")!;

export const metadata = {
  title: entry.title,
  description: entry.description,
  alternates: { canonical: entry.path },
};

const SOURCES = [
  {
    name: "Wu et al., \"Google's Neural Machine Translation System\" (2016), Google Research / arXiv",
    url: "https://arxiv.org/abs/1609.08144",
    note: "Google's own technical description of the model behind Translate",
  },
  {
    name: "Callison-Burch, Osborne & Koehn, \"Re-evaluating the Role of BLEU in Machine Translation Research\" (EACL 2006)",
    url: "https://aclanthology.org/E06-1032/",
    note: "on why automated MT metrics diverge from human judgment of translation quality",
  },
  {
    name: "Low, P., \"Singable Translations of Songs\" (2003), Perspectives: Studies in Translatology",
    url: "https://www.tandfonline.com/doi/abs/10.1080/0907676X.2003.9961466",
    note: "the \"Pentathlon Principle\" for lyric translation - singability, sense, naturalness, rhythm, rhyme",
  },
];

export default function CompareGoogleTranslatePage() {
  const breadcrumb = breadcrumbJsonLd([
    { name: "Home", path: "/" },
    { name: "Compare", path: "/compare/google-translate" },
    { name: "Google Translate" },
  ]);
  const article = articleJsonLd({
    path: entry.path,
    headline: entry.title,
    description: entry.description,
    publishedDate: entry.publishedDate,
    updatedDate: entry.updatedDate,
    citations: SOURCES,
  });

  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <JsonLd data={breadcrumb} />
      <JsonLd data={article} />
      <div className="mx-auto max-w-3xl">
        <SiteHeader />

        <div className="mt-10">
          <BreadcrumbNav items={[{ name: "Home", path: "/" }, { name: "Compare", path: "/compare/google-translate" }, { name: "Google Translate" }]} />
          <h1 className="mt-3 font-serif text-3xl text-ink dark:text-ink-dark sm:text-4xl">
            Castia vs. Google Translate.
          </h1>
          <p className="mt-4 max-w-prose text-[15px] leading-relaxed text-ink/55 dark:text-ink-dark/55">
            Google Translate is genuinely excellent at what it's built for.
            The honest comparison isn't "which is better" - it's which job
            each one is doing.
          </p>
        </div>

        <section className="mt-12">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            What Google Translate actually does
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            Google's own published research describes Translate's engine as
            a neural machine translation (NMT) system - a deep encoder-decoder
            network trained to produce one fluent, accurate translation of
            the text it's given. That's a single-pass job: read the source,
            decode the most probable target-language sentence, and return
            it. There's no documented step where the system drafts several
            differently-angled versions of a line and scores them against
            each other before picking one - the architecture isn't designed
            to do that, because sentence-level fluency and accuracy is the
            problem it's solving.
          </p>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            For most translation needs - reading a menu, understanding an
            email, getting the gist of a foreign-language article - that's
            exactly the right tool, and a fast, free, extremely
            well-engineered one.
          </p>
        </section>

        <section className="mt-12">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            Where a single accurate pass isn't the same job
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            A song lyric or a character's line of dialogue has constraints a
            menu item doesn't: rhyme, rhythm, singability, idiom, a
            character's established voice. Translation researcher Peter
            Low's "Pentathlon Principle" names five demands a singable lyric
            translation has to balance at once - singability, sense,
            naturalness, rhythm, and rhyme - and argues that treating literal
            semantic accuracy as the only priority actively produces worse
            lyric translations, not better ones. A model optimized purely for
            translation accuracy has no mechanism for making that tradeoff on
            purpose.
          </p>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            This is also where automated translation-quality metrics run
            into their own well-documented limits: Callison-Burch et al.'s
            EACL 2006 paper on BLEU (the standard automated MT metric) shows
            that a higher BLEU score doesn't reliably track a better
            human-judged translation, precisely because BLEU rewards
            closeness to one reference wording, not whether a
            differently-worded line captures the same feeling better.
            Castia's Judge stage exists for the same reason a metric like
            BLEU falls short here: it scores rewrites against what the line
            actually says (the Translator's literal anchor), not against
            surface closeness to any single wording.
          </p>
        </section>

        <section className="mt-12">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            Side by side
          </h2>
          <div className="mt-5 overflow-x-auto rounded-2xl border border-black/[0.06] dark:border-white/[0.07]">
            <table className="w-full min-w-[480px] text-left text-[13px]">
              <thead>
                <tr className="border-b border-black/[0.06] dark:border-white/[0.07]">
                  <th className="p-4 font-medium text-ink/50 dark:text-ink-dark/50"> </th>
                  <th className="p-4 font-medium text-ink dark:text-ink-dark">Google Translate</th>
                  <th className="p-4 font-medium text-ink dark:text-ink-dark">Castia</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-black/[0.06] dark:divide-white/[0.07]">
                {[
                  ["Best for", "Fast, literal, general-purpose translation", "Song lyrics and comic dialogue that need to keep their feeling"],
                  ["How many drafts per line", "One", "Six (one literal anchor + five creative rewrites)"],
                  ["Verification step", "Not documented", "A Judge scores every rewrite against the literal anchor"],
                  ["Explains its changes", "No", "Every departure from literal ships with a stated reason"],
                  ["Handles speech-bubble OCR & redraw", "No", "Yes (Beta)"],
                ].map(([label, gt, castia]) => (
                  <tr key={label}>
                    <td className="p-4 text-ink/50 dark:text-ink-dark/50">{label}</td>
                    <td className="p-4 text-ink/70 dark:text-ink-dark/70">{gt}</td>
                    <td className="p-4 text-ink/70 dark:text-ink-dark/70">{castia}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="mt-14">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            Same line, run through both
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            One source line, the same input, run through Google Translate and
            through Castia. Unedited output, side by side.
          </p>
          <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <ScreenshotSlot label="Google Translate" path="/screenshots/compare/google-translate.png" />
            <ScreenshotSlot label="Castia" path="/screenshots/compare/google-translate-castia.png" />
          </div>
        </section>

        <div className="mt-14 rounded-2xl bg-[#181310] p-8 text-center sm:p-10">
          <p className="font-serif text-xl text-white sm:text-2xl">
            See it on a real lyric.
          </p>
          <p className="mt-2 max-w-md mx-auto text-[13px] leading-relaxed text-white/50">
            Paste a verse and get the literal anchor, five rewrites, and the
            Judge's reasoning side by side.
          </p>
          <Link
            href="/music"
            className="mt-6 inline-block rounded-full bg-white px-6 py-2.5 text-[13px] font-medium text-black transition active:scale-[0.97]"
          >
            Try it on a lyric
          </Link>
        </div>

        <p className="mt-8 max-w-prose text-[13px] leading-relaxed text-ink/45 dark:text-ink-dark/45">
          Also see{" "}
          <Link href="/compare/deepl" className="underline decoration-ink/20 underline-offset-4">
            Castia vs. DeepL
          </Link>{" "}
          and{" "}
          <Link href="/compare/chatgpt-prompt" className="underline decoration-ink/20 underline-offset-4">
            Castia vs. a single ChatGPT prompt
          </Link>
          .
        </p>

        <SourceList sources={SOURCES} />

        <Footer />
      </div>
    </main>
  );
}
