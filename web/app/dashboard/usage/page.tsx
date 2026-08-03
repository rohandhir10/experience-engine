import { DashboardStub } from "@/components/DashboardStub";

export const metadata = { title: "AURA — Usage" };

export default function UsagePage() {
  return (
    <DashboardStub
      active="usage"
      title="Usage"
      message="There's already a daily limit behind the scenes to keep costs sane, but it's tracked anonymously per visitor, not tied to an account — so there's nothing personal to show you yet. Once accounts exist, this becomes a simple count: adaptations this month against your plan's limit."
    />
  );
}
