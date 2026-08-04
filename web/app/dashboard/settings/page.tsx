import { DashboardStub } from "@/components/DashboardStub";

export const metadata = { title: "CASTIA — Settings" };

export default function SettingsPage() {
  return (
    <DashboardStub
      active="settings"
      title="Settings"
      message="Nothing to configure yet — there's no account, so there are no preferences stored anywhere to change."
    />
  );
}
