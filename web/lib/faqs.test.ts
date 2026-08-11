import { describe, expect, it } from "vitest";
import { FAQS, HOMEPAGE_FAQ_QUESTIONS, homepageFaqs } from "./faqs";

describe("homepageFaqs", () => {
  it("returns real Faq objects from the shared FAQS array, not copies with drifted text", () => {
    const result = homepageFaqs();
    expect(result).toHaveLength(HOMEPAGE_FAQ_QUESTIONS.length);
    for (const faq of result) {
      const canonical = FAQS.find((f) => f.question === faq.question);
      expect(canonical).toBeDefined();
      expect(faq.answer).toBe(canonical!.answer);
    }
  });

  it("resolves every question it names to a real entry, so a typo'd question fails loudly", () => {
    // homepageFaqs() would throw (non-null assertion on find()) rather
    // than silently render undefined - this just confirms that today,
    // right now, every listed question actually exists.
    for (const question of HOMEPAGE_FAQ_QUESTIONS) {
      expect(FAQS.some((f) => f.question === question)).toBe(true);
    }
  });

  it("preserves the order HOMEPAGE_FAQ_QUESTIONS declares, not FAQS's own order", () => {
    const result = homepageFaqs();
    expect(result.map((f) => f.question)).toEqual(HOMEPAGE_FAQ_QUESTIONS);
  });
});
