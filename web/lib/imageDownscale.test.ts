import { describe, expect, it } from "vitest";
import { OCR_MAX_EDGE_PX, rescaleRegions, targetSize } from "./imageDownscale";
import type { OcrRegion } from "./comics-types";

function region(x: number, y: number, width: number, height: number): OcrRegion {
  return { text: "hi", confidence: 90, bbox: { x, y, width, height } };
}

describe("targetSize", () => {
  it("leaves an image already under the ceiling completely alone", () => {
    expect(targetSize(800, 600)).toEqual({ width: 800, height: 600, ratio: 1 });
  });

  it("never upscales a small panel", () => {
    const { ratio } = targetSize(100, 50);
    expect(ratio).toBe(1);
  });

  it("scales by the LONG edge, so neither dimension exceeds the ceiling", () => {
    const { width, height } = targetSize(6000, 3000, 2000);
    expect(Math.max(width, height)).toBe(2000);
    expect(width).toBe(2000);
    expect(height).toBe(1000);
  });

  it("scales by height when the image is taller than it is wide (webtoon strips)", () => {
    const { width, height } = targetSize(1000, 8000, 2000);
    expect(Math.max(width, height)).toBe(2000);
    expect(height).toBe(2000);
    expect(width).toBe(250);
  });

  it("preserves aspect ratio", () => {
    const { width, height } = targetSize(4000, 2500, 2000);
    expect(width / height).toBeCloseTo(4000 / 2500, 5);
  });

  it("treats a zero-dimension image as a no-op rather than dividing by zero", () => {
    expect(targetSize(0, 0)).toEqual({ width: 0, height: 0, ratio: 1 });
  });

  it("has a ceiling generous enough for dense lettering", () => {
    expect(OCR_MAX_EDGE_PX).toBeGreaterThanOrEqual(1500);
  });
});

describe("rescaleRegions", () => {
  it("returns regions untouched when nothing was downscaled", () => {
    const regions = [region(10, 20, 30, 40)];
    expect(rescaleRegions(regions, 1)).toBe(regions);
  });

  it("maps a box measured on the downscaled image back to original pixels", () => {
    // A 4000px-wide panel downscaled to 2000px is scale 2 coming back.
    const [scaled] = rescaleRegions([region(100, 50, 200, 80)], 2);
    expect(scaled.bbox).toEqual({ x: 200, y: 100, width: 400, height: 160 });
  });

  it("keeps the region's text and confidence intact", () => {
    const [scaled] = rescaleRegions([region(10, 10, 10, 10)], 2);
    expect(scaled.text).toBe("hi");
    expect(scaled.confidence).toBe(90);
  });

  it("rounds to whole pixels, matching the integer bbox the engine returns", () => {
    const [scaled] = rescaleRegions([region(33, 33, 33, 33)], 1.5);
    expect(Object.values(scaled.bbox).every(Number.isInteger)).toBe(true);
  });

  it("round-trips a box through downscale and back to within a pixel", () => {
    // The real invariant: a box drawn around text at (1200,900) in a
    // 4000px original must come back pointing at that same text, or the
    // overlay sits in the wrong place and redraw inpaints over artwork.
    const originalBox = { x: 1200, y: 900, width: 600, height: 240 };
    const { ratio } = targetSize(4000, 3000, 2000);

    const asSeenByOcr = region(
      Math.round(originalBox.x * ratio),
      Math.round(originalBox.y * ratio),
      Math.round(originalBox.width * ratio),
      Math.round(originalBox.height * ratio)
    );
    const [back] = rescaleRegions([asSeenByOcr], 1 / ratio);

    expect(Math.abs(back.bbox.x - originalBox.x)).toBeLessThanOrEqual(1);
    expect(Math.abs(back.bbox.y - originalBox.y)).toBeLessThanOrEqual(1);
    expect(Math.abs(back.bbox.width - originalBox.width)).toBeLessThanOrEqual(1);
    expect(Math.abs(back.bbox.height - originalBox.height)).toBeLessThanOrEqual(1);
  });
});
