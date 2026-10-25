// Single source of truth for Castia's real FAQ content - shared by
// app/faq/page.tsx (the full list) and app/page.tsx (a curated subset in
// a homepage FAQ block). One array instead of two copies that could
// drift out of sync, since both places render this exact text into both
// visible HTML and FAQPage JSON-LD, and Google's structured-data
// guidelines (and basic honesty) require the two to match.
//
// Every answer here must stay true to what's actually shipped. No
// specific daily-limit numbers are quoted: both CASTIA_DAILY_LIMIT and
// CASTIA_API_DAILY_LIMIT are env-configurable (server/main.py), so a
// hardcoded figure here could silently drift out of sync with whatever a
// given deployment actually runs.
export type Faq = {
  question: string;
  answer: string;
  category: "Product" | "Pricing & access" | "Technical";
};

export const FAQS: Faq[] = [
  {
    category: "Product",
    question: "What does Castia do?",
    answer:
      "CASTIA helps adapt comic and webtoon dialogue while preserving character voice, emotional intent, and scene context. Each adapted line is shown with a plain-language reason for the creative choice.",
  },
  {
    category: "Product",
    question: "How is this different from Google Translate or a single AI prompt?",
    answer:
      "Every line goes through a three-stage \"Writers' Room\": a Translator produces one literal anchor translation, a Creative Adapter produces five differently-angled rewrites, and a Judge scores each rewrite against that anchor and picks a winner — writing down the specific reason it departs from a literal translation. A single translation call has no anchor to check itself against and no record of why a word choice changed.",
  },
  {
    category: "Product",
    question: "Which languages are supported?",
    answer:
      "English, Hindi, Japanese, Korean, Spanish, and Urdu, in any direction — adapt from any one of these into any other.",
  },
  {
    category: "Product",
    question: "What does CASTIA do for comics and webtoons?",
    answer:
      "Yes. Upload comic or webtoon panels to detect speech-bubble text, review the extracted dialogue, adapt lines with character and scene context in mind, and optionally redraw panels with the adapted text typeset in. Current limitations include sound-effect text over artwork not being redrawn and OCR reading order being imperfect for some layouts.",
  },
  {
    category: "Pricing & access",
    question: "Do I need an account?",
    answer:
      "No — a limited number of adaptations per day work with no account at all. Signing in with Google adds a history of your past adaptations and lets you star or collect results so they're there next time.",
  },
  {
    category: "Pricing & access",
    question: "How much does it cost?",
    answer:
      "Castia is free to use right now, for everyone. Paid tiers are listed on the pricing page as what's being built toward, but billing isn't live yet — nothing is charged today.",
  },
  {
    category: "Technical",
    question: "Is there an API?",
    answer:
      "Yes, currently in Beta: POST /v1/comics/adapt for comic panels, authenticated with an API key you generate from your dashboard settings, with a daily request limit per key.",
  },
  {
    category: "Technical",
    question: "What happens to the dialogue I submit?",
    answer:
      "Results are cached on the server, addressed by the content itself, so re-submitting the same text doesn't re-run the pipeline. If you're signed in and save a result, it's linked to your account so you can find it again; if you're not signed in, nothing is tied to an identity.",
  },
];

export const FAQ_CATEGORIES = ["Product", "Pricing & access", "Technical"] as const;

/** Looks up real Faq objects by their exact question string, in the
 * given order - shared by every page that renders a curated subset of
 * the full FAQ list, so each subset is a plain array of strings (easy to
 * read, easy to see what's included) rather than its own hand-copied
 * Faq objects that could drift from the canonical answer text. Throws
 * (via the non-null assertion) if a question doesn't exist - a typo'd
 * question here should fail the build, not silently render `undefined`.
 */
function faqsFor(questions: string[]): Faq[] {
  return questions.map((q) => FAQS.find((faq) => faq.question === q)!);
}

// The four questions a first-time visitor on "/" actually asks, one per
// real category except Technical (an API question is the wrong altitude
// for a chooser page a brand-new visitor lands on) - not a random slice,
// a deliberate pick of the highest-value four for someone who hasn't
// decided whether to use this at all yet.
export const HOMEPAGE_FAQ_QUESTIONS = [
  "What does Castia do?",
  "How is this different from Google Translate or a single AI prompt?",
  "Do I need an account?",
  "How much does it cost?",
];

export function homepageFaqs(): Faq[] {
  return faqsFor(HOMEPAGE_FAQ_QUESTIONS);
}

// /music-specific: someone already on the lyrics tool wants to know the
// mechanism and the language roster, not whether comics exist too.
export const MUSIC_FAQ_QUESTIONS = [
  "What does Castia do?",
  "How is this different from Google Translate or a single AI prompt?",
  "Do I need an account?",
  "How much does it cost?",
];

export function musicFaqs(): Faq[] {
  return faqsFor(MUSIC_FAQ_QUESTIONS);
}

// /comics-specific: swaps the language-roster question for the one a
// visitor already on the webtoons tool actually has (does this work for
// comics at all, and what does "Beta" really mean here).
export const COMICS_FAQ_QUESTIONS = [
  "What does Castia do?",
  "What does CASTIA do for comics and webtoons?",
  "How is this different from Google Translate or a single AI prompt?",
  "Do I need an account?",
];

export function comicsFaqs(): Faq[] {
  return faqsFor(COMICS_FAQ_QUESTIONS);
}
