import { DashboardStub } from "@/components/DashboardStub";

export const metadata = { title: "CASTIA — Billing" };

export default function BillingPage() {
  return (
    <DashboardStub
      active="billing"
      title="Billing"
      message="Billing isn't live yet — no Stripe account connected, and no accounts to bill."
      secondaryLink={{ href: "/pricing", label: "See the plans this is being built toward" }}
    />
  );
}
