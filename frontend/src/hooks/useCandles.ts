import { useAsync } from "./useAsync";
import { marketService } from "../services/MarketService";
import type { Candle, SymbolQuote, Timeframe } from "../types";

/** Candle series for the selected quote + timeframe. */
export function useCandles(quote: SymbolQuote, timeframe: Timeframe) {
  return useAsync<Candle[]>(
    () => marketService.getCandles(quote, timeframe),
    [quote, timeframe],
  );
}
