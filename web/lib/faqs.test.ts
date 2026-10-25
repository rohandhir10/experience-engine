import { describe, expect, it } from "vitest";
import {
  FAQS,
  HOMEPAGE_FAQ_QUESTIONS,
  COMICS_FAQ_QUESTIONS,
  homepageFaqs,
  comicsFaqs,
  type Faq,
} from "./faqs";

// One shared block per active curated subset keeps homepage and comics FAQ
// content tied to the canonical source, without retaining obsolete music UI.
const SUBSETS: { name: string; questions: string[]; fn: () => Faq[] }[] = [
  { name: "homepageFaqs", questions: HOMEPAGE_FAQ_QUESTIONS, fn: homepageFaqs },
  { name: "comicsFaqs", questions: COMICS_FAQ_QUESTIONS, fn: comicsFaqs },
];

describe.each(SUBSETS)("$name", ({ questions, fn }) => {
  it("returns real Faq objects from the shared FAQS array, not copies with drifted text", () => {
    const result = fn();
    expect(result).toHaveLength(questions.length);
    for (const faq of result) {
      const canonical = FAQS.find((f) => f.question === faq.question);
      expect(canonical).toBeDefined();
      expect(faq.answer).toBe(canonical!.answer);
    }
  });

  it("resolves every named question to a real entry, so a typo'd question fails loudly", () => {
    // The subset function itself would throw (a non-null assertion on
    // find()) rather than silently render undefined - this confirms
    // that today, right now, every listed question actually exists.
    for (const question of questions) {
      expect(FAQS.some((f) => f.question === question)).toBe(true);
    }
  });

  it("preserves the declared order, not FAQS's own order", () => {
    expect(fn().map((f) => f.question)).toEqual(questions);
  });

  it("has no duplicate questions", () => {
    expect(new Set(questions).size).toBe(questions.length);
  });
});

describe("the curated subsets", () => {
  it("all share the anchor question every visitor asks first", () => {
    for (const { questions } of SUBSETS) {
      expect(questions).toContain("What does Castia do?");
    }
  });

  it("are each genuinely different from one another, not the same four questions relabeled", () => {
    const [home, comics] = SUBSETS.map((s) => s.questions.join("|"));
    expect(home).not.toBe(comics);
  });
});
