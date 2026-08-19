import { NextRequest } from "next/server";
import { engineFetchAsUser } from "@/lib/engineFetch";

export async function DELETE(_request: NextRequest, props: { params: Promise<{ keyId: string }> }) {
  const params = await props.params;
  return engineFetchAsUser(`/api/me/api-keys/${encodeURIComponent(params.keyId)}`, {
    method: "DELETE",
  });
}
