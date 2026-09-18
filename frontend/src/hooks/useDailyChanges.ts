import { useMemo } from "react";

import { marketService } from "../services/MarketService";
import type { PriceChange, SymbolQuote } from "../types";

/**
 * Daily change per symbol, derived from the same seeded 1-day series the
 * quote chart uses (see MarketService TODO).
 */
export function useDailyChanges(
  quotes: readonly SymbolQuote[],
): Readonly<Record<string, PriceChange>> {
  return useMemo(
    () =>
      Object.fromEntries(quotes.map((quote) => [quote.symbol, marketService.dailyChange(quote)])),
    [quotes],
  );
}
