import { LANGUAGES } from "@/lib/languages";

/** A single "X language" dropdown, reused for both "Adapt into" (target)
 * and, once a non-English target is chosen, "From" (source) — see
 * InputScreen.tsx. `options` lets the caller exclude whichever language
 * is already picked on the other side (source and target can't match,
 * per server/main.py's validation). */
export function TargetLanguageSelect({
  value,
  onChange,
  label = "Adapt into",
  options = LANGUAGES,
  dark = false,
}: {
  value: string;
  onChange: (value: string) => void;
  label?: string;
  options?: readonly string[];
  dark?: boolean;
}) {
  return (
    <label className="inline-flex items-center gap-2 text-[13px]">
      <span className={dark ? "text-white/62" : "text-ink/62 dark:text-ink-dark/62"}>
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={
          dark
            ? "rounded-full border border-white/15 bg-white/[0.04] px-3 py-1.5 text-white outline-none transition focus:border-white/30"
            : "rounded-full border border-black/[0.12] bg-white/70 px-3 py-1.5 text-ink outline-none transition focus:border-black/20 dark:border-white/[0.12] dark:bg-white/[0.03] dark:text-ink-dark"
        }
      >
        {options.map((lang) => (
          <option key={lang} value={lang}>
            {lang}
          </option>
        ))}
      </select>
    </label>
  );
}
