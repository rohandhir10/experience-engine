import { describe, expect, it } from "vitest";
import {
  buildDraftFromFile,
  groupIntoSectionsWithTiming,
  LyricsImportError,
  parseLrc,
  parseSrt,
} from "./lyricsImport";

describe("parseLrc", () => {
  it("parses [mm:ss.xx]text lines into start-timestamped segments", () => {
    const lrc = "[00:14.20]First line\n[00:16.90]Second line";
    expect(parseLrc(lrc)).toEqual([
      { text: "First line", start: 14.2, end: 14.2 },
      { text: "Second line", start: 16.9, end: 16.9 },
    ]);
  });

  it("skips metadata tags, not just blank lines", () => {
    const lrc = "[ar:Some Artist]\n[ti:Some Title]\n[00:01.00]Real line";
    expect(parseLrc(lrc)).toEqual([{ text: "Real line", start: 1, end: 1 }]);
  });

  it("expands a line with several timestamps (repeated chorus) into one segment per timestamp", () => {
    const lrc = "[00:10.00][00:40.00]Chorus line";
    expect(parseLrc(lrc)).toEqual([
      { text: "Chorus line", start: 10, end: 10 },
      { text: "Chorus line", start: 40, end: 40 },
    ]);
  });

  it("sorts by timestamp even if the file lists lines out of order", () => {
    const lrc = "[00:20.00]Second\n[00:05.00]First";
    expect(parseLrc(lrc).map((s) => s.text)).toEqual(["First", "Second"]);
  });
});

describe("parseSrt", () => {
  it("parses numbered cue blocks into start/end-timestamped segments", () => {
    const srt = [
      "1",
      "00:00:14,200 --> 00:00:16,900",
      "First line of lyrics",
      "",
      "2",
      "00:00:20,000 --> 00:00:22,500",
      "Second line",
    ].join("\n");
    expect(parseSrt(srt)).toEqual([
      { text: "First line of lyrics", start: 14.2, end: 16.9 },
      { text: "Second line", start: 20, end: 22.5 },
    ]);
  });

  it("joins a multi-line cue and strips simple markup tags", () => {
    const srt = ["1", "00:00:01,000 --> 00:00:03,000", "<i>Line one</i>", "Line two"].join("\n");
    expect(parseSrt(srt)).toEqual([{ text: "Line one\nLine two", start: 1, end: 3 }]);
  });
});

describe("groupIntoSectionsWithTiming", () => {
  it("splits on a gap at or above the threshold, keeping tighter runs together", () => {
    const segments = [
      { text: "a", start: 0, end: 1 },
      { text: "b", start: 1.5, end: 2 }, // gap 0.5s from previous end - same block
      { text: "c", start: 6, end: 7 }, // gap 4s - new block (>= 3.0 default)
    ];
    const blocks = groupIntoSectionsWithTiming(segments);
    expect(blocks).toEqual([
      { text: "a\nb", start: 0, end: 2 },
      { text: "c", start: 6, end: 7 },
    ]);
  });

  it("returns nothing for no segments", () => {
    expect(groupIntoSectionsWithTiming([])).toEqual([]);
  });
});

describe("buildDraftFromFile", () => {
  it("builds the same {draftText, sections, warning} shape YouTube import produces", () => {
    const lrc = "[00:00.00]Verse line one\n[00:01.00]Verse line two\n[00:10.00]Chorus line";
    const draft = buildDraftFromFile("song.lrc", lrc);
    expect(draft.draftText).toBe("Verse line one\nVerse line two\n\nChorus line");
    expect(draft.sections).toEqual([
      { start: 0, end: 1 },
      { start: 10, end: 10 },
    ]);
    expect(draft.warning).toMatch(/timing-gap guess/);
  });

  it("doesn't split every line into its own section on realistic verse-line spacing", () => {
    // Found by testing against a real sample: LRC gives no duration, so
    // parseLrc sets end = start, and groupIntoSectionsWithTiming's
    // default 3.0s threshold (right for SRT/YouTube-caption timing) was
    // already exceeded by ordinary sung lines 3.5s apart - splitting
    // every single line into its own "section" and defeating the point
    // of grouping at all. LRC uses a wider, dedicated threshold instead.
    const lrc = "[00:00.00]First verse line one\n[00:03.50]First verse line two\n[00:15.00]Chorus line";
    const draft = buildDraftFromFile("song.lrc", lrc);
    expect(draft.draftText).toBe("First verse line one\nFirst verse line two\n\nChorus line");
    expect(draft.sections).toEqual([
      { start: 0, end: 3.5 },
      { start: 15, end: 15 },
    ]);
  });

  it("routes by file extension, not just content shape", () => {
    const srt = ["1", "00:00:01,000 --> 00:00:02,000", "Only line"].join("\n");
    const draft = buildDraftFromFile("song.srt", srt);
    expect(draft.sections).toEqual([{ start: 1, end: 2 }]);
  });

  it("throws LyricsImportError instead of returning an empty draft when nothing parses", () => {
    expect(() => buildDraftFromFile("song.lrc", "[ar:no real lines here]")).toThrow(
      LyricsImportError
    );
  });
});
