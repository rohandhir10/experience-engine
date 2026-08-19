import { NextRequest } from "next/server";
import { engineFetchAsUser } from "@/lib/engineFetch";

// One history entry's save state, for the result page's controls.
export async function GET(_request: NextRequest, props: { params: Promise<{ resultId: string }> }) {
  const params = await props.params;
  return engineFetchAsUser(
    `/api/me/adaptations/${encodeURIComponent(params.resultId)}`
  );
}
