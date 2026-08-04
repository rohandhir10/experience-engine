export type AdaptedPanel = {
  id: string;
  literal: string;
  adaptedText: string;
  why: string;
};

export type ChapterAdaptResult = {
  panels: AdaptedPanel[];
};

export class AdaptRequestError extends Error {}

// Calls app/api/comics/adapt/route.ts, which proxies to server/main.py's
// /api/comics/adapt (engine/chapter_dna.py + engine/comics_adapt.py) -
// the first call in this workspace that actually adapts dialogue rather
// than just extracting or displaying it. Each PANEL is sent as one
// adaptation unit; a panel with several speech bubbles is adapted as
// one combined block, not split further - see that route's comments.
// `voice`, when set, becomes BubbleInput.voice server-side - the thing
// that actually drives per-character voice consistency and honorific-
// register tracking (engine/comics_adapt.py); omitted, a panel is
// adapted unattributed, same as before this field existed.
export async function adaptChapter(
  panels: { id: string; text: string; voice?: string }[],
  sourceLanguage: string,
  targetLanguage: string
): Promise<ChapterAdaptResult> {
  const res = await fetch("/api/comics/adapt", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      source_language: sourceLanguage,
      target_language: targetLanguage,
      panels,
    }),
  });
  const body = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new AdaptRequestError(body.error || body.detail || "Adapting this chapter failed.");
  }

  return {
    panels: (body.panels ?? []).map(
      (panel: { id: string; literal: string; adapted_text: string; why: string }) => ({
        id: panel.id,
        literal: panel.literal,
        adaptedText: panel.adapted_text,
        why: panel.why,
      })
    ),
  };
}
