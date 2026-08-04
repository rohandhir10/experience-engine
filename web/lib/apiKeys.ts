/** One row of a user's API keys, as returned by /api/me/api-keys
 * (server/api_keys.py::list_keys) - never the raw key or its hash, only
 * a short prefix, same one-time-reveal convention GitHub/Stripe use. */
export type ApiKeyEntry = {
  id: string;
  name: string;
  prefix: string;
  createdAt: string;
  lastUsedAt: string | null;
  revokedAt: string | null;
};

/** The one-time creation response - has the raw key, which nothing else
 * in this app ever receives again after this single response. */
export type CreatedApiKey = ApiKeyEntry & { key: string };
