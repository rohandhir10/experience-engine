// Chapter slices are almost always named with a numeric sequence
// ("panel-2.jpg" before "panel-10.jpg") that plain string sort gets
// wrong (a plain sort puts "panel-10.jpg" before "panel-2.jpg"). Splits
// each name into alternating text/number runs and compares number runs
// numerically, text runs as strings.
export function naturalCompare(a: string, b: string): number {
  const chunk = /(\d+)|(\D+)/g;
  const aParts = a.match(chunk) ?? [];
  const bParts = b.match(chunk) ?? [];
  const len = Math.max(aParts.length, bParts.length);
  for (let i = 0; i < len; i++) {
    const aPart = aParts[i] ?? "";
    const bPart = bParts[i] ?? "";
    if (aPart === bPart) continue;
    const aNum = /^\d+$/.test(aPart) ? Number(aPart) : null;
    const bNum = /^\d+$/.test(bPart) ? Number(bPart) : null;
    if (aNum !== null && bNum !== null) {
      if (aNum !== bNum) return aNum - bNum;
      continue;
    }
    return aPart < bPart ? -1 : 1;
  }
  return 0;
}
