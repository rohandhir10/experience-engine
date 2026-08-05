/** One row of a user's credit ledger, as returned by /api/me/credits
 * (server/credits.py::list_transactions). `amount` is signed: positive
 * for a grant (purchase, subscription renewal, refund), negative for a
 * debit (one adaptation's cost) - see server/db_models.py's
 * CreditTransaction docstring. */
export type CreditTransaction = {
  id: string;
  amount: number;
  reason: "purchase" | "subscription_renewal" | "adaptation" | "refund";
  reference: string | null;
  balanceAfter: number;
  createdAt: string;
};

export type CreditsResponse = {
  balance: number | null;
  transactions: CreditTransaction[];
};
