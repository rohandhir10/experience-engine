"use client";

import { initializePaddle, type Paddle } from "@paddle/paddle-js";

// NEXT_PUBLIC_* vars are inlined at build time and safe to ship to the
// browser (Paddle's client-side token is meant for exactly this, unlike
// a server-side API key) - this project has no real Paddle account yet,
// so these are unset until one exists; every function below degrades
// to a clear error rather than a broken checkout call when they are.
const CLIENT_TOKEN = process.env.NEXT_PUBLIC_PADDLE_CLIENT_TOKEN;
const ENVIRONMENT = (process.env.NEXT_PUBLIC_PADDLE_ENVIRONMENT as
  | "sandbox"
  | "production"
  | undefined) ?? "sandbox";

export function isPaddleConfigured(): boolean {
  return Boolean(CLIENT_TOKEN);
}

let paddleInstance: Paddle | undefined;

async function getPaddle(): Promise<Paddle> {
  if (!CLIENT_TOKEN) {
    throw new Error("Checkout isn't configured on this deployment yet.");
  }
  if (paddleInstance) return paddleInstance;
  const instance = await initializePaddle({ environment: ENVIRONMENT, token: CLIENT_TOKEN });
  if (!instance) {
    throw new Error("Could not load the checkout. Try again in a moment.");
  }
  paddleInstance = instance;
  return instance;
}

/** Opens a Paddle overlay checkout for one price - `userId` rides in
 * customData, which is the only reliable way to attach the resulting
 * transaction back to a Castia account (server/paddle.py's webhook
 * handler reads it back out of data.custom_data.user_id; there is no
 * other field on a Paddle transaction that identifies our own user). */
export async function openCheckout(priceId: string, userId: string): Promise<void> {
  const paddle = await getPaddle();
  paddle.Checkout.open({
    items: [{ priceId, quantity: 1 }],
    customData: { user_id: userId },
  });
}
