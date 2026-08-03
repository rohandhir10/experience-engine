import { DashboardStub } from "@/components/DashboardStub";

export const metadata = { title: "AURA — Collections" };

export default function CollectionsPage() {
  return (
    <DashboardStub
      active="collections"
      title="Collections"
      message="Group your adaptations however makes sense — by language, by artist, by mood. Collections need an account to belong to, so there's nothing to show until sign-in is live."
    />
  );
}
