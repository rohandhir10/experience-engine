import { NextRequest } from "next/server";
import { engineFetchAsUser } from "@/lib/engineFetch";

export async function PATCH(request: NextRequest, props: { params: Promise<{ collectionId: string }> }) {
  const params = await props.params;
  const body = await request.json().catch(() => ({}));
  return engineFetchAsUser(
    `/api/me/collections/${encodeURIComponent(params.collectionId)}`,
    { method: "PATCH", body: { name: String(body.name ?? "") } }
  );
}

export async function DELETE(
  _request: NextRequest,
  props: { params: Promise<{ collectionId: string }> }
) {
  const params = await props.params;
  return engineFetchAsUser(
    `/api/me/collections/${encodeURIComponent(params.collectionId)}`,
    { method: "DELETE" }
  );
}
