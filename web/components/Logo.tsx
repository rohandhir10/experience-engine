/** `force` overrides theme-reactive coloring for contexts that commit to
 * one background regardless of system theme (e.g. the dark marketing
 * hero) — without it, Logo follows light/dark mode as usual. */
export function Logo({ force }: { force?: "light" }) {
  if (force === "light") {
    return (
      <span className="text-sm font-medium tracking-[0.2em] text-white/78">
        CASTIA
      </span>
    );
  }
  return (
    <span className="text-sm font-medium tracking-[0.2em] text-ink/72 dark:text-ink-dark/72">
      CASTIA
    </span>
  );
}
