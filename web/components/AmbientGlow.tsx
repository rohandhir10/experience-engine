// Quiet, continuous motion so the page doesn't go dead the moment the
// entrance animations finish — two soft, slow-drifting blurred fields,
// low enough opacity that they read as depth, not decoration you notice.
// Neutral ink tone only, deliberately - the accent color is reserved for
// interactive states (focus rings, the toggle, the section-divider arrow)
// and never used as background decoration.
export function AmbientGlow() {
  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden"
    >
      <div className="animate-drift-a absolute -left-1/4 -top-1/4 h-[60vh] w-[60vh] rounded-full bg-ink/[0.035] blur-3xl dark:bg-ink-dark/[0.05]" />
      <div className="animate-drift-b absolute -right-1/4 top-1/3 h-[50vh] w-[50vh] rounded-full bg-ink/[0.025] blur-3xl dark:bg-ink-dark/[0.035]" />
    </div>
  );
}
