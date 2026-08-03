import { DashboardStub } from "@/components/DashboardStub";

export const metadata = { title: "AURA — Favorites" };

export default function FavoritesPage() {
  return (
    <DashboardStub
      active="favorites"
      title="Favorites"
      message="A place for the adaptations you're proudest of. Favoriting needs an account to know whose favorites they are, so this is empty until sign-in is live."
    />
  );
}
