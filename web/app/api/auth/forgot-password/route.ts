import type { NextRequest } from "next/server";
import { engineFetchAnonymous } from "@/lib/engineFetch";

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  return engineFetchAnonymous("/api/auth/forgot-password", { method: "POST", body });
}
