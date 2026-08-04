import { NextRequest } from "next/server";
import { engineFetchAsUser } from "@/lib/engineFetch";

export async function PATCH(
  request: NextRequest,
  { params }: { params: { collectionId: string } }
) {
  const body = await request.json().catch(() => ({}));
  return engineFetchAsUser(
    `/api/me/collections/${encodeURIComponent(params.collectionId)}`,
    { method: "PATCH", body: { name: String(body.name ?? "") } }
  );
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: { collectionId: string } }
) {
  return engineFetchAsUser(
    `/api/me/collections/${encodeURIComponent(params.collectionId)}`,
    { method: "DELETE" }
  );
}
