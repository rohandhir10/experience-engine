import type { DeviationFragment } from "./types";

export type HighlightSegment =
  | { type: "text"; text: string }
  | { type: "deviation"; text: string; deviation: DeviationFragment };

// Splits the shipped AURA line into plain-text and deviation segments, so
// only the phrases the Judge's ledger actually names get an interactive
// underline. A deviation whose fragmentAdapted isn't found verbatim in the
// text is dropped, not guessed at a position - the ledger is LLM-authored
// and isn't guaranteed to echo the fragment byte-for-byte against the
// final shipped line. Overlapping matches keep only the earliest.
export function splitByDeviations(
  text: string,
  deviations: DeviationFragment[] | undefined
): HighlightSegment[] {
  if (!deviations || deviations.length === 0) {
    return [{ type: "text", text }];
  }

  type Match = { start: number; end: number; deviation: DeviationFragment };
  const matches: Match[] = [];
  for (const deviation of deviations) {
    if (!deviation.fragmentAdapted) continue;
    const start = text.indexOf(deviation.fragmentAdapted);
    if (start === -1) continue;
    matches.push({ start, end: start + deviation.fragmentAdapted.length, deviation });
  }
  matches.sort((a, b) => a.start - b.start);

  const nonOverlapping: Match[] = [];
  let lastEnd = -1;
  for (const match of matches) {
    if (match.start >= lastEnd) {
      nonOverlapping.push(match);
      lastEnd = match.end;
    }
  }

  const segments: HighlightSegment[] = [];
  let cursor = 0;
  for (const match of nonOverlapping) {
    if (match.start > cursor) {
      segments.push({ type: "text", text: text.slice(cursor, match.start) });
    }
    segments.push({ type: "deviation", text: match.deviation.fragmentAdapted, deviation: match.deviation });
    cursor = match.end;
  }
  if (cursor < text.length) {
    segments.push({ type: "text", text: text.slice(cursor) });
  }
  return segments;
}
