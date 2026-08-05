import { ImageResponse } from "next/og";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// A real, rendered brand image (next/og draws this at request time from
// the same colors/type as the rest of the site - tailwind.config.ts's
// paper-dark/ink-dark/accent), not a fabricated product screenshot or an
// AI-generated mockup. Shared as the default OG/Twitter card for every
// page that doesn't set its own; individual pages can still override via
// their own opengraph-image file if a page-specific one is ever needed.
export default function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "80px",
          background: "#181310",
          fontFamily: "Georgia, serif",
        }}
      >
        <div
          style={{
            fontSize: 28,
            letterSpacing: 6,
            color: "#b8562e",
            textTransform: "uppercase",
          }}
        >
          Castia
        </div>
        <div
          style={{
            marginTop: 28,
            display: "flex",
            flexDirection: "column",
            fontSize: 64,
            lineHeight: 1.15,
            color: "#ededec",
            maxWidth: 900,
          }}
        >
          <div>Adapt the feeling.</div>
          <div>Not just the words.</div>
        </div>
        <div
          style={{
            marginTop: 32,
            fontSize: 26,
            color: "rgba(237,237,236,0.55)",
            fontFamily: "-apple-system, sans-serif",
          }}
        >
          Lyric &amp; dialogue adaptation across six languages
        </div>
      </div>
    ),
    { ...size }
  );
}
