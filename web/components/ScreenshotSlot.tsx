/** Empty-state placeholder for a real screenshot that hasn't been dropped
 * in yet. Renders a dashed frame with the exact path it's waiting on, so
 * swapping in the real file later is a one-line change (replace this with
 * <Image src={path} .../>) rather than a guess at what was intended. Never
 * render a fabricated screenshot here - an honest gap beats a fake image. */
export function ScreenshotSlot({
  label,
  path,
}: {
  label: string;
  path: string;
}) {
  return (
    <div className="flex aspect-[4/3] flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-black/15 bg-black/[0.02] p-4 text-center dark:border-white/15 dark:bg-white/[0.02]">
      <span className="text-[11px] font-medium uppercase tracking-wide text-ink/40 dark:text-ink-dark/40">
        {label}
      </span>
      <span className="text-[11px] text-ink/30 dark:text-ink-dark/30">
        Screenshot pending
      </span>
      <code className="mt-1 rounded bg-black/[0.04] px-1.5 py-0.5 text-[10px] text-ink/35 dark:bg-white/[0.06] dark:text-ink-dark/40">
        {path}
      </code>
    </div>
  );
}
