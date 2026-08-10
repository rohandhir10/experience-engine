import { engineFetchAsUser } from "@/lib/engineFetch";

// Proxies to server/main.py's /api/me/export - the "right of access"
// web/app/privacy states as real practice. Returns the account's own
// data as JSON for the browser to save as a file; credential material
// (password hash, API key hashes) is excluded engine-side, see
// server/accounts.py::export_account_data.
export async function GET() {
  return engineFetchAsUser("/api/me/export");
}
