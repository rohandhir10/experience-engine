import { TARGET_LANGUAGES } from "@/lib/languages";

/** "Adapt into" — the one control that actually changes which direction a
 * submission runs. Defaults to English (today's original, only-ever-
 * supported direction); picking anything else switches to the reverse
 * (English source -> that language) — see engine/models.py's
 * SUPPORTED_TARGET_LANGUAGES for exactly which pairings exist. */
export function TargetLanguageSelect({
  value,
  onChange,
  dark = false,
}: {
  value: string;
  onChange: (value: string) => void;
  dark?: boolean;
}) {
  return (
    <label className="inline-flex items-center gap-2 text-[13px]">
      <span className={dark ? "text-white/40" : "text-ink/40 dark:text-ink-dark/40"}>
        Adapt into
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={
          dark
            ? "rounded-full border border-white/15 bg-white/[0.04] px-3 py-1.5 text-white outline-none transition focus:border-white/30"
            : "rounded-full border border-black/[0.08] bg-white/70 px-3 py-1.5 text-ink outline-none transition focus:border-black/20 dark:border-white/[0.08] dark:bg-white/[0.03] dark:text-ink-dark"
        }
      >
        {TARGET_LANGUAGES.map((lang) => (
          <option key={lang} value={lang}>
            {lang}
          </option>
        ))}
      </select>
    </label>
  );
}
