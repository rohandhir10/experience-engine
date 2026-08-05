import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";
import { JsonLd } from "@/components/JsonLd";
import Link from "next/link";

export const metadata = {
  title: "FAQ",
  description:
    "Answers about how Castia adapts lyrics and comic dialogue, which languages it supports, pricing, the API, and how it differs from translation.",
  alternates: { canonical: "/faq" },
};

// Every answer here must stay true to what's actually shipped - this
// page's JSON-LD below repeats these exact strings, and Google's
// structured-data guidelines (and basic honesty) require visible and
// markup content to match. No specific daily-limit numbers are quoted:
// both CASTIA_DAILY_LIMIT and CASTIA_API_DAILY_LIMIT are env-configurable
// (server/main.py), so a hardcoded figure here could silently drift out
// of sync with whatever a given deployment actually runs.
const FAQS: { question: string; answer: string }[] = [
  {
    question: "What does Castia do?",
    answer:
      "Castia rewrites song lyrics and comic/webtoon dialogue so they read the way someone who already understands the source would say it — not a literal, word-for-word translation. Every adapted line is shown next to its literal reading and a plain-language reason for the change.",
  },
  {
    question: "How is this different from Google Translate or a single AI prompt?",
    answer:
      "Every line goes through a three-stage \"Writers' Room\": a Translator produces one literal anchor translation, a Creative Adapter produces five differently-angled rewrites, and a Judge scores each rewrite against that anchor and picks a winner — writing down the specific reason it departs from a literal translation. A single translation call has no anchor to check itself against and no record of why a word choice changed.",
  },
  {
    question: "Which languages are supported?",
    answer:
      "English, Hindi, Japanese, Korean, Spanish, and Urdu, in any direction — adapt from any one of these into any other.",
  },
  {
    question: "Does this work for comics and webtoons too?",
    answer:
      "Yes, currently in Beta. Upload comic panels, and Google Cloud Vision OCRs each speech bubble's text and position; the same Writers' Room pipeline adapts the dialogue. An optional redraw step can inpaint the original lettering out of a panel and typeset the adapted line back in. Beta means it doesn't yet have the music tool's save/collections/share-link features.",
  },
  {
    question: "Do I need an account?",
    answer:
      "No — a limited number of adaptations per day work with no account at all. Signing in with Google adds a history of your past adaptations and lets you star or collect results so they're there next time.",
  },
  {
    question: "How much does it cost?",
    answer:
      "Castia is free to use right now, for everyone. Paid tiers are listed on the pricing page as what's being built toward, but billing isn't live yet — nothing is charged today.",
  },
  {
    question: "Is there an API?",
    answer:
      "Yes, currently in Beta: POST /v1/adapt for lyrics and POST /v1/comics/adapt for comic panels, authenticated with an API key you generate from your dashboard settings, with a daily request limit per key.",
  },
  {
    question: "What happens to the lyrics or dialogue I submit?",
    answer:
      "Results are cached on the server, addressed by the content itself, so re-submitting the same text doesn't re-run the pipeline. If you're signed in and save a result, it's linked to your account so you can find it again; if you're not signed in, nothing is tied to an identity.",
  },
];

export default function FaqPage() {
  const faqJsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: FAQS.map((faq) => ({
      "@type": "Question",
      name: faq.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: faq.answer,
      },
    })),
  };

  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <JsonLd data={faqJsonLd} />
      <div className="mx-auto max-w-3xl">
        <SiteHeader />

        <div className="mt-10">
          <h1 className="font-serif text-3xl text-ink dark:text-ink-dark sm:text-4xl">
            Frequently asked questions.
          </h1>
          <p className="mt-4 max-w-prose text-[15px] leading-relaxed text-ink/55 dark:text-ink-dark/55">
            For the full pipeline explanation, see{" "}
            <Link href="/how-it-works" className="underline decoration-ink/20 underline-offset-4">
              how it works
            </Link>
            .
          </p>
        </div>

        <div className="mt-12 space-y-8">
          {FAQS.map((faq) => (
            <div key={faq.question} className="border-b border-black/[0.06] pb-8 dark:border-white/[0.07]">
              <h2 className="font-serif text-lg text-ink dark:text-ink-dark">
                {faq.question}
              </h2>
              <p className="mt-2.5 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
                {faq.answer}
              </p>
            </div>
          ))}
        </div>

        <Footer />
      </div>
    </main>
  );
}
