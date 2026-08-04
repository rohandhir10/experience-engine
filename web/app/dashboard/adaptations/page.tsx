import { DashboardStub } from "@/components/DashboardStub";

export const metadata = { title: "CASTIA — Adaptations" };

export default function AdaptationsPage() {
  return (
    <DashboardStub
      active="adaptations"
      title="Adaptations"
      message="Every song adapted through CASTIA is already saved so repeats don't re-run the AI — but that history isn't linked to anyone yet, since there's no sign-in. Once accounts exist, everything you adapt will show up here automatically, searchable and filterable by language."
    />
  );
}
