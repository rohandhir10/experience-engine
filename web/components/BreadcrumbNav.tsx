import Link from "next/link";

/** Small visible breadcrumb trail to match the BreadcrumbList JSON-LD
 * (lib/schema.ts::breadcrumbJsonLd) every editorial page emits - Google's
 * structured-data guidelines require the two to agree, and a visible
 * trail is also just useful wayfinding on pages a search result or an AI
 * answer might land someone on directly, skipping the homepage. */
export function BreadcrumbNav({ items }: { items: { name: string; path?: string }[] }) {
  return (
    <nav className="flex flex-wrap items-center gap-1.5 text-[12px] text-ink/35 dark:text-ink-dark/35">
      {items.map((item, index) => (
        <span key={item.name} className="flex items-center gap-1.5">
          {index > 0 && <span aria-hidden="true">/</span>}
          {item.path ? (
            <Link href={item.path} className="transition hover:text-ink/60 dark:hover:text-ink-dark/60">
              {item.name}
            </Link>
          ) : (
            <span>{item.name}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
