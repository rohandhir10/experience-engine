"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

/** Real scroll-triggered motion, distinct from the existing
 * `.animate-fade-up` CSS class - that one plays once at mount (a
 * page-load stagger), so content below the fold has already finished
 * animating by the time a scrolling visitor actually reaches it. This
 * uses IntersectionObserver to fade a section up as it *enters* the
 * viewport, whenever that happens. Fires once (`triggerOnce`) rather
 * than re-animating every time a section scrolls in and out - a
 * repeating fade on every re-entry reads as jittery, not premium.
 * Respects prefers-reduced-motion the same way AmbientGlow's own
 * animations already do - renders fully visible immediately, no
 * animation at all. */
export function ScrollReveal({
  children,
  className,
  delayMs = 0,
}: {
  children: ReactNode;
  className?: string;
  delayMs?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    if (
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      setRevealed(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setRevealed(true);
          observer.disconnect();
        }
      },
      { threshold: 0.15 }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={`transition-all duration-700 ease-[cubic-bezier(0.16,1,0.3,1)] ${
        revealed ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0"
      } ${className ?? ""}`}
      style={{ transitionDelay: revealed ? `${delayMs}ms` : "0ms" }}
    >
      {children}
    </div>
  );
}
