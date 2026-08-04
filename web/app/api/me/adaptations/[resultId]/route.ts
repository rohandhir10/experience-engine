import { NextRequest } from "next/server";
import { engineFetchAsUser } from "@/lib/engineFetch";

// One history entry's save state, for the result page's controls.
export async function GET(
  _request: NextRequest,
  { params }: { params: { resultId: string } }
) {
  return engineFetchAsUser(
    `/api/me/adaptations/${encodeURIComponent(params.resultId)}`
  );
}
