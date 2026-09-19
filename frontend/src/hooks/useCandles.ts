import { useAsync } from "./useAsync";
import { marketService } from "../services/MarketService";
import type { Candle, SymbolQuote, Timeframe } from "../types";

/** Candle series for the selected quote + timeframe. Previous data is
 * cleared while loading - the chart renders its own cached series under a
 * loading overlay instead. */
export function useCandles(quote: SymbolQuote, timeframe: Timeframe) {
  return useAsync<Candle[]>(
    () => marketService.getCandles(quote, timeframe),
    [quote, timeframe],
    { keepPreviousData: false },
  );
}
