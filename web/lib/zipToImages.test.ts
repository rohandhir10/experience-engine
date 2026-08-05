import JSZip from "jszip";
import { describe, expect, it } from "vitest";
import { ZipConversionError, zipToImageFiles } from "./zipToImages";

async function makeZip(entries: Record<string, string>): Promise<File> {
  const zip = new JSZip();
  for (const [name, content] of Object.entries(entries)) {
    zip.file(name, content);
  }
  const blob = await zip.generateAsync({ type: "blob" });
  return new File([blob], "chapter.zip", { type: "application/zip" });
}

describe("zipToImageFiles", () => {
  it("extracts only image entries, ignoring anything else in the zip", async () => {
    const zipFile = await makeZip({
      "001.png": "fake png bytes",
      "002.jpg": "fake jpg bytes",
      "readme.txt": "not an image",
    });
    const files = await zipToImageFiles(zipFile);
    expect(files.map((f) => f.name).sort()).toEqual(["001.png", "002.jpg"]);
    expect(files.find((f) => f.name === "001.png")?.type).toBe("image/png");
    expect(files.find((f) => f.name === "002.jpg")?.type).toBe("image/jpeg");
  });

  it("flattens folder structure inside the zip to each entry's own file name", async () => {
    const zipFile = await makeZip({ "chapter-1/panel-01.webp": "fake webp bytes" });
    const files = await zipToImageFiles(zipFile);
    expect(files.map((f) => f.name)).toEqual(["panel-01.webp"]);
  });

  it("skips macOS junk entries (__MACOSX/, dotfiles) rather than treating them as panels", async () => {
    const zipFile = await makeZip({
      "001.png": "real",
      "__MACOSX/001.png": "resource fork junk",
      ".DS_Store": "junk",
    });
    const files = await zipToImageFiles(zipFile);
    expect(files.map((f) => f.name)).toEqual(["001.png"]);
  });

  it("throws ZipConversionError when the zip has no images at all", async () => {
    const zipFile = await makeZip({ "readme.txt": "no images here" });
    await expect(zipToImageFiles(zipFile)).rejects.toThrow(ZipConversionError);
  });

  it("throws ZipConversionError for a file that isn't actually a zip", async () => {
    const notAZip = new File(["not a zip"], "chapter.zip", { type: "application/zip" });
    await expect(zipToImageFiles(notAZip)).rejects.toThrow(ZipConversionError);
  });
});
