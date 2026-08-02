import type { ComparisonSection, ComparisonSystemId } from "@/lib/comparison-data";
import { SYSTEM_LABELS } from "@/lib/comparison-data";

const ORDER: ComparisonSystemId[] = ["google_translate", "gpt_single", "aura"];

function SystemBlock({
  systemId,
  text,
  emphasize,
}: {
  systemId: ComparisonSystemId;
  text: string | undefined;
  emphasize: boolean;
}) {
  return (
    <div
      className={
        emphasize
          ? "rounded-xl border border-accent/20 bg-accent/[0.04] px-5 py-5 dark:border-accent/25"
          : "px-5 py-5"
      }
    >
      <p
        className={
          emphasize
            ? "text-[11px] font-semibold uppercase tracking-[0.15em] text-accent"
            : "text-[11px] font-medium uppercase tracking-[0.15em] text-ink/35 dark:text-ink-dark/35"
        }
      >
        {SYSTEM_LABELS[systemId]}
      </p>
      {text ? (
        <p
          className={
            emphasize
              ? "mt-3 max-w-prose whitespace-pre-line font-serif text-[18px] leading-relaxed text-ink dark:text-ink-dark sm:text-[20px]"
              : "mt-3 max-w-prose whitespace-pre-line text-[15px] leading-relaxed text-ink/55 dark:text-ink-dark/55"
          }
        >
          {text}
        </p>
      ) : (
        <p className="mt-3 text-[14px] italic leading-relaxed text-ink/30 dark:text-ink-dark/30">
          Not yet generated — see benchmark/README.md to produce a real run.
        </p>
      )}
    </div>
  );
}

export function SystemComparisonCard({
  section,
  index,
}: {
  section: ComparisonSection;
  index: number;
}) {
  return (
    <div
      className="animate-fade-up rounded-2xl border border-black/[0.06] px-7 py-8 dark:border-white/[0.07] sm:px-10 sm:py-10"
      style={{ animationDelay: `${index * 90}ms` }}
    >
      <div className="border-b border-black/[0.05] pb-6 dark:border-white/[0.05]">
        <p className="text-[11px] font-medium uppercase tracking-[0.15em] text-ink/30 dark:text-ink-dark/30">
          Original
        </p>
        <p className="mt-3 max-w-prose whitespace-pre-line text-[15px] leading-relaxed text-ink/45 dark:text-ink-dark/45">
          {section.source}
        </p>
      </div>

      <div className="mt-2 divide-y divide-black/[0.05] dark:divide-white/[0.05]">
        {ORDER.map((systemId) => (
          <SystemBlock
            key={systemId}
            systemId={systemId}
            text={section.systems[systemId]}
            emphasize={systemId === "aura"}
          />
        ))}
      </div>
    </div>
  );
}
