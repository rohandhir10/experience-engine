"use client";

import { useEffect, useRef } from "react";

// Loose by design - the YouTube IFrame API ships no official TypeScript
// types, and this component only ever calls getCurrentTime()/destroy().
type YTPlayer = {
  getCurrentTime: () => number;
  destroy: () => void;
};

declare global {
  interface Window {
    YT?: { Player: new (el: HTMLElement, opts: Record<string, unknown>) => YTPlayer };
    onYouTubeIframeAPIReady?: () => void;
  }
}

let apiPromise: Promise<void> | null = null;

function loadYoutubeApi(): Promise<void> {
  if (typeof window === "undefined") return Promise.resolve();
  if (window.YT?.Player) return Promise.resolve();
  if (apiPromise) return apiPromise;
  apiPromise = new Promise((resolve) => {
    const previous = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => {
      previous?.();
      resolve();
    };
    const script = document.createElement("script");
    script.src = "https://www.youtube.com/iframe_api";
    document.body.appendChild(script);
  });
  return apiPromise;
}

/** Embeds the source video and reports playback position back to the
 * caller (ResultScreen), which matches it against each section's
 * start/end range to highlight whichever lyric is playing right now.
 * Polls getCurrentTime() on an interval - the IFrame API has no native
 * "time update" event, so this is the standard approach, same as most
 * synced-lyrics players built on this API. */
export function YoutubeSyncPlayer({
  videoId,
  onTimeUpdate,
}: {
  videoId: string;
  onTimeUpdate: (seconds: number) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const playerRef = useRef<YTPlayer | null>(null);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | undefined;
    let cancelled = false;

    loadYoutubeApi().then(() => {
      if (cancelled || !containerRef.current || !window.YT) return;
      playerRef.current = new window.YT.Player(containerRef.current, {
        videoId,
        playerVars: { rel: 0 },
      });
      interval = setInterval(() => {
        const player = playerRef.current;
        if (player && typeof player.getCurrentTime === "function") {
          try {
            onTimeUpdate(player.getCurrentTime());
          } catch {
            // Player not ready yet (still loading the video) - skip this tick.
          }
        }
      }, 400);
    });

    return () => {
      cancelled = true;
      if (interval) clearInterval(interval);
      playerRef.current?.destroy?.();
    };
    // Re-creating the player if onTimeUpdate's identity changes would tear
    // down and restart playback on every render - only videoId should do that.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [videoId]);

  return (
    <div className="overflow-hidden rounded-2xl border border-black/[0.06] dark:border-white/[0.07]">
      <div className="aspect-video w-full" ref={containerRef} />
    </div>
  );
}
