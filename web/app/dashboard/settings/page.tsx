import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { DashboardSidebar } from "@/components/DashboardSidebar";
import { ApiKeysManager } from "@/components/ApiKeysManager";
import { AccountDataControls } from "@/components/AccountDataControls";

export const metadata = { title: "CASTIA — Settings" };

// No longer a DashboardStub for API keys - the public API
// (server/main.py's /v1/* routes) is real now. Still nothing else to
// configure here (no other account preferences exist yet).
export default function SettingsPage() {
  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <div className="mx-auto max-w-5xl">
        <SiteHeader />

        <div className="mt-10 flex flex-col gap-10 sm:flex-row">
          <DashboardSidebar active="settings" />

          <div className="min-w-0 flex-1">
            <h1 className="font-serif text-2xl text-ink dark:text-ink-dark sm:text-[1.75rem]">
              API Keys
            </h1>
            <p className="mt-2 max-w-prose text-[13px] leading-relaxed text-ink/62 dark:text-ink-dark/62">
              For server-to-server calls to the public API — pass a key as{" "}
              <code className="rounded bg-black/[0.05] px-1 py-0.5 dark:bg-white/10">
                Authorization: Bearer &lt;key&gt;
              </code>{" "}
              against <code className="rounded bg-black/[0.05] px-1 py-0.5 dark:bg-white/10">/v1/adapt</code>{" "}
              or <code className="rounded bg-black/[0.05] px-1 py-0.5 dark:bg-white/10">/v1/comics/adapt</code>.
              Same engine, same request/response shape as the dashboard's own
              adapt flow — just gated by a key instead of a signed-in session.
              Full request/response shapes, rate limits, and examples on the{" "}
              <Link href="/docs/api" className="underline decoration-ink/20 underline-offset-4">
                API reference
              </Link>
              .
            </p>
            <ApiKeysManager />
            <AccountDataControls />
          </div>
        </div>
      </div>
    </main>
  );
}
