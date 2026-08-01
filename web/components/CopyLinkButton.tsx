"use client";

import { useState } from "react";

export function CopyLinkButton({ resultId }: { resultId: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    const url = `${window.location.origin}/s/${resultId}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // Clipboard access denied - nothing to recover, the link is still
      // visible in the address bar once the user is on /s/[id].
    }
  }

  return (
    <button
      onClick={handleCopy}
      className="text-[13px] text-ink/45 transition hover:text-ink/70 dark:text-ink-dark/45 dark:hover:text-ink-dark/70"
    >
      {copied ? "Copied" : "Share"}
    </button>
  );
}
