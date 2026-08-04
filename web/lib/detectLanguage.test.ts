import { describe, expect, it } from "vitest";
import { detectSourceLanguage } from "./detectLanguage";

// Mirrors the manual Node-script verification this feature originally
// shipped with (one real sample per roster language plus decline cases),
// now enforced by CI-runnable tests instead of a one-off terminal check.

describe("script-based detection", () => {
  it("detects Hindi from Devanagari", () => {
    expect(detectSourceLanguage("रंगरेज़ा रंग मेरा तन मेरा मन")).toBe("Hindi");
  });

  it("detects Urdu from Perso-Arabic script", () => {
    expect(detectSourceLanguage("کن فایکون کن فایکون")).toBe("Urdu");
  });

  it("detects Korean from Hangul", () => {
    expect(detectSourceLanguage("보고 싶다 이렇게 말하니까 더 보고 싶다")).toBe("Korean");
  });

  it("detects Japanese from kana/kanji", () => {
    expect(detectSourceLanguage("染め師よ、私の体と心を染めて")).toBe("Japanese");
  });

  it("is not fooled by a few transliterated Latin words inside Hangul", () => {
    expect(detectSourceLanguage("보고 싶다 friend 보고 싶다 보고 싶다")).toBe("Korean");
  });
});

describe("Latin-script disambiguation (English vs Spanish only)", () => {
  it("detects Spanish from an accent marker alone", () => {
    expect(detectSourceLanguage("Tití me preguntó si tengo muchas novias")).toBe("Spanish");
  });

  it("detects Spanish from stopwords without any accents", () => {
    expect(
      detectSourceLanguage("Cuando la vida te da sorpresas, sorpresas te da la vida")
    ).toBe("Spanish");
  });

  it("detects English from stopwords", () => {
    expect(detectSourceLanguage("I keep the drawer locked and I never open it")).toBe(
      "English"
    );
  });
});

describe("declining instead of guessing", () => {
  it("returns null for text below the minimum length", () => {
    expect(detectSourceLanguage("hey")).toBeNull();
  });

  it("returns null for Latin text with no stopword signal either way", () => {
    expect(detectSourceLanguage("asdf qwer zxcv uiop")).toBeNull();
  });

  it("returns null for empty and whitespace-only input", () => {
    expect(detectSourceLanguage("")).toBeNull();
    expect(detectSourceLanguage("   \n  ")).toBeNull();
  });

  it("returns null for an unmapped script rather than misidentifying it", () => {
    // Cyrillic is not in the roster - Russian must not come back as any
    // of the six supported languages.
    expect(detectSourceLanguage("я помню чудное мгновенье передо мной")).toBeNull();
  });
});
