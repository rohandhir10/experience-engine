/** Renders the real external sources a blog/compare page cites, matching
 * the same list passed into that page's Article JSON-LD `citation` field
 * (lib/schema.ts) - visible and structured data must agree on what's
 * actually cited, not just claim it in markup. Every entry here must be
 * a source that was actually looked up, never invented. */
export function SourceList({ sources }: { sources: { name: string; url: string; note?: string }[] }) {
  return (
    <div className="mt-14 border-t border-black/[0.10] pt-8 dark:border-white/[0.11]">
      <h2 className="text-[12px] uppercase tracking-[0.1em] text-ink/40 dark:text-ink-dark/40">
        Sources
      </h2>
      <ul className="mt-4 space-y-2.5">
        {sources.map((s) => (
          <li key={s.url} className="text-[13px] leading-relaxed text-ink/55 dark:text-ink-dark/55">
            <a
              href={s.url}
              target="_blank"
              rel="noopener noreferrer nofollow"
              className="underline decoration-ink/20 underline-offset-4 hover:text-ink/80 dark:hover:text-ink-dark/80"
            >
              {s.name}
            </a>
            {s.note && <span className="text-ink/40 dark:text-ink-dark/40"> — {s.note}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}
