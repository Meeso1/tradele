import type { Holding, OrderQuantity } from "../types";

/** Shares currently held for a symbol (0 if none). */
export function heldShares(holdings: readonly Holding[], symbol: string): number {
  return holdings.find((candidate) => candidate.symbol === symbol)?.shares ?? 0;
}

/**
 * Best-effort share count for a quantity (used by client-side warnings only -
 * authoritative conversion happens on the backend). Null when converting a
 * dollar value without a known price.
 */
export function estimateShares(quantity: OrderQuantity, price: number | undefined): number | null {
  if ("shares" in quantity) return quantity.shares;
  return price != null && price > 0 ? quantity.value / price : null;
}

/**
 * Best-effort dollar cost of an order (used by client-side warnings only).
 * Null when a share quantity can't be converted without a known price.
 */
export function estimateCost(quantity: OrderQuantity, price: number | undefined): number | null {
  if ("value" in quantity) return quantity.value;
  return price != null && price > 0 ? quantity.shares * price : null;
}
