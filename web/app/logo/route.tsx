import { ImageResponse } from "next/og";

export const runtime = "edge";

// A larger square brand mark for contexts a 32px favicon is too small
// for - currently just Organization JSON-LD's `logo` field (root
// layout.tsx), which Google's structured-data guidance recommends be at
// least 112x112. Same real rendered mark as icon.tsx/apple-icon.tsx, one
// asset instead of three near-duplicate route-handler files.
export async function GET() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#181310",
          color: "#ededec",
          fontSize: 280,
          fontFamily: "Georgia, serif",
        }}
      >
        C
      </div>
    ),
    { width: 512, height: 512 }
  );
}
