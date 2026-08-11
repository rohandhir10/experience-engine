import type { PanelAdaptStatus } from "@/lib/comics-types";

/** The small per-panel indicator shown on both thumbnail rails
 * (PanelOrderGrid, PanelWorkspace's own rail) - the fix for a real gap:
 * during a whole-chapter adapt run, neither rail gave any signal for
 * which panels were actually finished versus still pending, so a user
 * reviewing one panel while the job filled in another had no way to tell
 * at a glance. "done" always shows a checkmark, regardless of whether a
 * job is currently running (a panel finished by a PREVIOUS run, or by
 * hand-typing, is just as done). "partial" only renders while a job is
 * actually running - a spinner communicates "still working"; showing the
 * same spinner after the job settled would be a lie, and a static dot
 * for hand-filled-partway state add noise for every panel a user hasn't
 * gotten to yet instead of only the ones genuinely mid-flight. */
export function PanelStatusBadge({
  status,
  adapting,
}: {
  status: PanelAdaptStatus;
  adapting: boolean;
}) {
  if (status === "done") {
    return (
      <span
        aria-label="Adapted"
        title="This panel's adaptation is filled in"
        className="flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500 text-[9px] font-bold leading-none text-white"
      >
        ✓
      </span>
    );
  }
  if (status === "partial" && adapting) {
    return (
      <span
        aria-label="Adapting"
        title="Still adapting this panel"
        className="h-3 w-3 animate-spin rounded-full border-2 border-amber-400 border-t-transparent"
      />
    );
  }
  return null;
}
