import Link from "next/link";
import type { ExperienceResult } from "@/lib/types";
import { ENGINE_API_URL } from "@/lib/api";
import { Logo } from "@/components/Logo";
import { ResultScreen } from "@/components/ResultScreen";

async function getResult(id: string): Promise<ExperienceResult | null> {
  try {
    const res = await fetch(`${ENGINE_API_URL}/api/adapt/${id}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function SharedResultPage({
  params,
}: {
  params: { id: string };
}) {
  const result = await getResult(params.id);

  if (!result) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
        <div className="fixed left-6 top-6 sm:left-10 sm:top-10">
          <Logo />
        </div>
        <p className="font-serif text-2xl text-ink dark:text-ink-dark">
          This link doesn't lead anywhere anymore.
        </p>
        <p className="mt-3 text-[15px] text-ink/50 dark:text-ink-dark/50">
          The song it pointed to may not have been experienced yet on this
          engine.
        </p>
        <Link
          href="/"
          className="mt-8 rounded-full bg-ink px-8 py-3 text-[14px] font-medium text-paper transition active:scale-[0.97] dark:bg-ink-dark dark:text-paper-dark"
        >
          Experience a song
        </Link>
      </main>
    );
  }

  return <ResultScreen result={result} />;
}
