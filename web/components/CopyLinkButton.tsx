"use client";

import { useState } from "react";

// basePath defaults to "/s" (the song share page); comics passes
// "/comics/s" for its own read-only chapter viewer - same component,
// same clipboard/label behavior, just a different destination.
export function CopyLinkButton({
  resultId,
  basePath = "/s",
}: {
  resultId: string;
  basePath?: string;
}) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    const url = `${window.location.origin}${basePath}/${resultId}`;
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
      className="text-[13px] text-ink/65 transition hover:text-ink/78 dark:text-ink-dark/65 dark:hover:text-ink-dark/78"
    >
      {copied ? "Copied" : "Share"}
    </button>
  );
}
