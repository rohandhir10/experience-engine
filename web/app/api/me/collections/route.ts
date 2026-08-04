import { NextRequest } from "next/server";
import { engineFetchAsUser } from "@/lib/engineFetch";

export async function GET() {
  return engineFetchAsUser("/api/me/collections");
}

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  return engineFetchAsUser("/api/me/collections", {
    method: "POST",
    body: { name: String(body.name ?? "") },
  });
}
