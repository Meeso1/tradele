import type { OrderQuantity, OrderType } from "../types";

const MINUS = "\u2212"; // true minus sign, as in the design mockup

/** "$142.30" / "$1,730.00" - exact dollars and cents. */
export function formatUsd(value: number, decimals = 2): string {
  return `$${value.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}`;
}

/** "$41,764" - rounded to whole dollars, grouped. */
export function formatWholeUsd(value: number): string {
  return `$${Math.round(value).toLocaleString("en-US")}`;
}

/** "+$3.34" / "−$124" - signed, whole dollars by default. */
export function formatSignedUsd(value: number, decimals = 0): string {
  const sign = value >= 0 ? "+" : MINUS;
  return `${sign}$${Math.abs(value).toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}`;
}

/** "+2.4%" / "−3.5%" */
export function formatSignedPercent(value: number, decimals = 1): string {
  const sign = value >= 0 ? "+" : MINUS;
  return `${sign}${Math.abs(value).toFixed(decimals)}%`;
}

/** "30" / "34.1" - share counts, hiding a trailing ".0". */
export function formatShares(shares: number): string {
  return Number.isInteger(shares) ? String(shares) : shares.toFixed(1);
}

/** "LIMIT" / "STOP" / "MARKET" */
export function orderTypeLabel(type: OrderType): string {
  return type.toUpperCase();
}

/** "30 sh @ $61.00" / "$1,750 at market" - quantity as the user specified it. */
export function orderQtyLabel(quantity: OrderQuantity, price?: number): string {
  const quantityText =
    "shares" in quantity ? `${formatShares(quantity.shares)} sh` : formatWholeUsd(quantity.value);
  return price != null ? `${quantityText} @ ${formatUsd(price)}` : `${quantityText} at market`;
}
