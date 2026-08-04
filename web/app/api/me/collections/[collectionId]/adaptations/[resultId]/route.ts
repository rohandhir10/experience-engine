import { NextRequest } from "next/server";
import { engineFetchAsUser } from "@/lib/engineFetch";

// Add/remove one adaptation to/from one collection. Ownership of BOTH is
// enforced upstream (server/accounts.py::set_collection_membership), so
// this route only proves who is asking.
export async function POST(
  request: NextRequest,
  { params }: { params: { collectionId: string; resultId: string } }
) {
  const body = await request.json().catch(() => ({}));
  return engineFetchAsUser(
    `/api/me/collections/${encodeURIComponent(params.collectionId)}/adaptations/${encodeURIComponent(params.resultId)}`,
    { method: "POST", body: { member: Boolean(body.member) } }
  );
}
