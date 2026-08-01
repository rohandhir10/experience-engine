import type { ExperienceResult } from "./types";

// Placeholder result standing in for a real backend call. The API route
// (app/api/adapt/route.ts) is the seam where that gets wired up later —
// nothing here is meant to be the final data source.
export const sampleResult: ExperienceResult = {
  hook:
    "This isn't simply a love song. It's about trying to hold on to someone " +
    "while quietly accepting that love cannot stop life from being cruel.",
  sourceLanguage: "Hindi",
  sections: [
    {
      id: "verse_1",
      literal:
        "Pause for a moment, let my heart settle. How can I stop you? " +
        "Every sorrow coming my way slips away as I fill my eyes with you. " +
        "I speak to you without words. If you're with me, if you're here with me.",
      aura:
        "Stay — one breath, steady this heart.\n" +
        "How do I hold you here?\n" +
        "Every grief that finds me, gone.\n" +
        "Eyes full of you.\n" +
        "No words. Just you.\n" +
        "If you're here.\n" +
        "If you're here.",
      why:
        "The first version reads like a sentence someone translated. This " +
        "one reads like something someone would actually say — and it says " +
        "the same plea twice, the way she really does, instead of smoothing " +
        "it into two different lines.",
    },
    {
      id: "verse_2",
      literal:
        "In your world that flows like rivers and streams, my world exists " +
        "in your desires. I become part of your habits if you're with me.",
      aura:
        "Your world runs like rivers.\n" +
        "Mine lives inside your wanting.\n" +
        "I become your habit.\n" +
        "If you're here.",
      why:
        "The explaining is gone. The images are just placed next to each " +
        "other and left to do the work, the way the original does.",
    },
    {
      id: "chorus",
      literal:
        "In your dreams lies buried unease, truths of the heart deceived by " +
        "speech, whether you're here or gone, life's sting stays the same, " +
        "if you stay with me, if you stay with me.",
      aura:
        "Your eyes hold dreams brimmed with bitterness.\n" +
        "Words often lie about what the heart really feels.\n" +
        "Does it matter if you're with me or not?\n" +
        "Life was cruel. It still is.",
      why:
        "This is where the song turns. The first version still sounds " +
        "hopeful here. This one lets the coldness actually land — because " +
        "that's the point of this line, not comfort.",
    },
  ],
  original: [
    {
      id: "verse_1",
      text:
        "पल-भर ठहर जाओ, दिल ये सँभल जाए\nकैसे तुम्हें रोका करूँ?\n" +
        "मेरी तरफ़ आता हर ग़म फिसल जाए\nआँखों में तुम को भरूँ\n" +
        "बिन बोले बातें तुम से करूँ\n'गर तुम साथ हो\nअगर तुम साथ हो",
    },
    {
      id: "verse_2",
      text:
        "बेहती रेहती नेहर नदियाँ सी तेरी दुनिया में\nमेरी दुनिया है तेरी चाहतों में\n" +
        "मैं ढल जाती हूँ तेरी आदतों में\n'गर तुम साथ हो",
    },
    {
      id: "chorus",
      text:
        "तेरी नज़रों में है तेरे सपने\nतेरे सपनों में है नाराज़ी\n" +
        "मुझे लगता है के बातें दिल की\nहोती लफ़्ज़ों की धोखेबाज़ी\n" +
        "तुम साथ हो, या ना हो, क्या फर्क है?\nबेदर्द थी ज़िन्दगी, बेदर्द है\n" +
        "अगर तुम साथ हो\nअगर तुम साथ हो",
    },
  ],
};
