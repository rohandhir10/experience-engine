// Parses .lrc and .srt files into the same shape YouTube import already
// produces (engine/youtube_ingest.py's TranscriptSegment ->
// group_into_sections_with_timing -> build_web_draft), so this plugs into
// the exact same review-then-submit flow (InputScreen.tsx) and the same
// server-side "attach per-section timing" logic (server/main.py) instead
// of inventing a second pipeline. There's no video to sync playback to
// here, so the resulting draft never carries a videoId - only text and
// per-section start/end seconds.

export type TimedSegment = { text: string; start: number; end: number };
export type TimedBlock = { text: string; start: number; end: number };
export type TimedDraft = {
  draftText: string;
  sections: { start: number; end: number }[];
  warning: string;
};

// Mirrors engine/youtube_ingest.py's DEFAULT_GAP_THRESHOLD_SECONDS exactly
// - same "silence this long is probably a verse/chorus boundary" guess.
// Used as-is for SRT, whose cues carry real start/end times shaped like
// YouTube's captions (near-continuous through a verse, a real pause at a
// section break).
const DEFAULT_GAP_THRESHOLD_SECONDS = 3.0;

// LRC gives no duration, only an instant per line, so parseLrc sets
// end = start and this measures the gap between one line's timestamp and
// the next directly - and plain sung lines are routinely 3-5+ seconds
// apart even within the same verse (found by testing against a real
// four-line sample: consecutive verse lines 3.5s apart already exceeded
// DEFAULT_GAP_THRESHOLD_SECONDS, splitting every single line into its
// own section). A higher threshold, specific to this zero-duration
// shape, is still a guess - just one tuned to what LRC actually gives,
// not to caption-stream timing it doesn't share.
const LRC_GAP_THRESHOLD_SECONDS = 7.0;

/** Same grouping heuristic as engine/youtube_ingest.py's
 * group_into_sections_with_timing: a gap of gapThresholdSeconds or more
 * between one segment's end and the next segment's start is treated as a
 * section break. Kept as a direct line-for-line port (not re-derived)
 * so the two implementations can't quietly drift apart. */
export function groupIntoSectionsWithTiming(
  segments: TimedSegment[],
  gapThresholdSeconds: number = DEFAULT_GAP_THRESHOLD_SECONDS
): TimedBlock[] {
  if (segments.length === 0) return [];

  const blocks: TimedSegment[][] = [[segments[0]]];
  let prevEnd = segments[0].end;

  for (let i = 1; i < segments.length; i++) {
    const segment = segments[i];
    const gap = segment.start - prevEnd;
    if (gap >= gapThresholdSeconds) blocks.push([]);
    blocks[blocks.length - 1].push(segment);
    prevEnd = segment.end;
  }

  return blocks.map((block) => ({
    text: block.map((s) => s.text).join("\n"),
    start: block[0].start,
    end: block[block.length - 1].end,
  }));
}

const LRC_TIMESTAMP_RE = /\[(\d{1,2}):(\d{2})(?:[.:](\d{1,3}))?\]/g;
// Metadata tags ([ar:Artist], [ti:Title], [by:...], [offset:...], ...) -
// not a timestamp, not a lyric line, must not be parsed as either.
const LRC_METADATA_RE = /^\[[a-zA-Z#]+:.*\]$/;

/** Parses standard LRC ([mm:ss.xx]text per line, optionally several
 * timestamp tags on one line for a repeated chorus). LRC gives no
 * duration, only a start instant per line - `end` is set equal to
 * `start` so groupIntoSectionsWithTiming's gap check measures the true
 * silence between one line's timestamp and the next, the same signal
 * the YouTube caption-gap heuristic uses, not an invented duration. */
export function parseLrc(text: string): TimedSegment[] {
  const segments: TimedSegment[] = [];

  for (const rawLine of text.split(/\r\n|\r|\n/)) {
    const line = rawLine.trim();
    if (!line || LRC_METADATA_RE.test(line)) continue;

    const timestamps: number[] = [];
    let match: RegExpExecArray | null;
    LRC_TIMESTAMP_RE.lastIndex = 0;
    let lastIndex = 0;
    while ((match = LRC_TIMESTAMP_RE.exec(line))) {
      const minutes = Number(match[1]);
      const seconds = Number(match[2]);
      const fraction = match[3] ? Number(`0.${match[3]}`) : 0;
      timestamps.push(minutes * 60 + seconds + fraction);
      lastIndex = LRC_TIMESTAMP_RE.lastIndex;
    }
    if (!timestamps.length) continue;

    const lyricText = line.slice(lastIndex).trim();
    if (!lyricText) continue;

    for (const start of timestamps) {
      segments.push({ text: lyricText, start, end: start });
    }
  }

  return segments.sort((a, b) => a.start - b.start);
}

const SRT_TIME_RE = /(\d{2}):(\d{2}):(\d{2})[,.](\d{3})/;
const SRT_CUE_RE = new RegExp(`${SRT_TIME_RE.source}\\s*-->\\s*${SRT_TIME_RE.source}`);

function srtTimeToSeconds(h: string, m: string, s: string, ms: string): number {
  return Number(h) * 3600 + Number(m) * 60 + Number(s) + Number(ms) / 1000;
}

/** Parses SRT: numbered blocks of an index line, a `HH:MM:SS,mmm -->
 * HH:MM:SS,mmm` timing line, then one or more text lines. Strips simple
 * `<i>`/`<b>`-style markup tags SRT sometimes carries for styling -
 * they're not part of the lyric. */
export function parseSrt(text: string): TimedSegment[] {
  const segments: TimedSegment[] = [];
  const blocks = text.split(/\r?\n\r?\n+/);

  for (const block of blocks) {
    const lines = block.split(/\r?\n/).map((l) => l.trim());
    const cueLineIndex = lines.findIndex((l) => SRT_CUE_RE.test(l));
    if (cueLineIndex === -1) continue;

    const cueMatch = lines[cueLineIndex].match(SRT_CUE_RE);
    if (!cueMatch) continue;
    const start = srtTimeToSeconds(cueMatch[1], cueMatch[2], cueMatch[3], cueMatch[4]);
    const end = srtTimeToSeconds(cueMatch[5], cueMatch[6], cueMatch[7], cueMatch[8]);

    const lyricText = lines
      .slice(cueLineIndex + 1)
      .join("\n")
      .replace(/<[^>]+>/g, "")
      .trim();
    if (!lyricText) continue;

    segments.push({ text: lyricText, start, end });
  }

  return segments;
}

export class LyricsImportError extends Error {}

/** Builds the same {draftText, sections, warning} shape YouTube import
 * produces (server/main.py's /api/youtube-draft response), so
 * InputScreen.tsx's existing review-then-submit flow needs no branching
 * on where the timing came from. */
export function buildDraftFromFile(fileName: string, text: string): TimedDraft {
  const isSrt = fileName.toLowerCase().endsWith(".srt");
  const segments = isSrt ? parseSrt(text) : parseLrc(text);

  if (!segments.length) {
    throw new LyricsImportError(
      isSrt
        ? "No timed cues found in this .srt file."
        : "No timestamped lines found in this .lrc file."
    );
  }

  const blocks = groupIntoSectionsWithTiming(
    segments,
    isSrt ? DEFAULT_GAP_THRESHOLD_SECONDS : LRC_GAP_THRESHOLD_SECONDS
  );

  return {
    draftText: blocks.map((b) => b.text).join("\n\n"),
    sections: blocks.map((b) => ({ start: b.start, end: b.end })),
    warning:
      "Section breaks here are a timing-gap guess, not real verse/chorus structure.",
  };
}
