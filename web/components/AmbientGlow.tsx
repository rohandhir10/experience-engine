// Quiet, continuous motion so the page doesn't go dead the moment the
// entrance animations finish — two soft, slow-drifting blurred fields,
// low enough opacity that they read as depth, not decoration you notice.
export function AmbientGlow() {
  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden"
    >
      <div className="animate-drift-a absolute -left-1/4 -top-1/4 h-[60vh] w-[60vh] rounded-full bg-accent/[0.07] blur-3xl dark:bg-accent/[0.10]" />
      <div className="animate-drift-b absolute -right-1/4 top-1/3 h-[50vh] w-[50vh] rounded-full bg-accent/[0.05] blur-3xl dark:bg-accent/[0.08]" />
    </div>
  );
}
