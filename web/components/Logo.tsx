/** `force` overrides theme-reactive coloring for contexts that commit to
 * one background regardless of system theme (e.g. the dark marketing
 * hero) — without it, Logo follows light/dark mode as usual. */
export function Logo({ force }: { force?: "light" }) {
  if (force === "light") {
    return (
      <span className="text-sm font-medium tracking-[0.2em] text-white/70">
        AURA
      </span>
    );
  }
  return (
    <span className="text-sm font-medium tracking-[0.2em] text-ink/60 dark:text-ink-dark/60">
      AURA
    </span>
  );
}
