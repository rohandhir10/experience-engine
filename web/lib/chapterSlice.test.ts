import { describe, expect, it } from "vitest";
import { SLICE_ASPECT_THRESHOLD, SLICE_MIN_HEIGHT_PX, planChapterSlices } from "./chapterSlice";

describe("planChapterSlices", () => {
  it("leaves a normal single page alone", () => {
    expect(planChapterSlices(1200, 1800)).toEqual({ shouldSlice: false, sliceHeight: 1800, count: 1 });
  });

  it("leaves an extra-tall single page (a real spread) alone - ratio alone isn't enough", () => {
    // 1:2.5 is taller than typical but nowhere near a whole chapter.
    expect(planChapterSlices(1000, 2500).shouldSlice).toBe(false);
  });

  it("does not trip on a narrow-but-short image just because the ratio is high", () => {
    // Aspect ratio 10 but well under SLICE_MIN_HEIGHT_PX - a banner crop, not a chapter.
    expect(planChapterSlices(100, 1000).shouldSlice).toBe(false);
  });

  it("slices a real unsliced whole-chapter strip", () => {
    const plan = planChapterSlices(800, 24000);
    expect(plan.shouldSlice).toBe(true);
    expect(plan.count).toBeGreaterThan(1);
  });

  it("produces slices close to a normal page's aspect ratio", () => {
    const { sliceHeight } = planChapterSlices(800, 24000);
    expect(sliceHeight / 800).toBeCloseTo(1.4, 1);
  });

  it("covers the whole strip - count * sliceHeight is never less than the original height", () => {
    const { sliceHeight, count } = planChapterSlices(800, 24000);
    expect(sliceHeight * count).toBeGreaterThanOrEqual(24000);
  });

  it("is a no-op for a zero-dimension image rather than dividing by zero", () => {
    expect(planChapterSlices(0, 0)).toEqual({ shouldSlice: false, sliceHeight: 0, count: 1 });
  });

  it("sits right at the documented thresholds", () => {
    expect(SLICE_ASPECT_THRESHOLD).toBeGreaterThan(1);
    expect(SLICE_MIN_HEIGHT_PX).toBeGreaterThan(0);
  });

  it("does not slice exactly at the aspect threshold boundary (strictly greater required)", () => {
    const width = 1000;
    const height = width * SLICE_ASPECT_THRESHOLD;
    expect(planChapterSlices(width, height).shouldSlice).toBe(false);
  });

  it("slices just past the aspect threshold, given enough absolute height", () => {
    const width = 1000;
    const height = width * SLICE_ASPECT_THRESHOLD + 1000;
    expect(planChapterSlices(width, Math.max(height, SLICE_MIN_HEIGHT_PX + 1)).shouldSlice).toBe(true);
  });
});
