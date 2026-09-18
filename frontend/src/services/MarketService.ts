import { apiGet } from "../api/client";
import type { PricesResponseDto } from "../api/dto";
import { mapPricesToQuotes } from "../api/mappers";
import { TIMEFRAMES, candlesFor } from "../mock/data";
import type { Candle, PriceChange, SymbolQuote, Timeframe } from "../types";

/**
 * Market data backed by the `/market/prices` endpoint.
 */
export class MarketService {
  /** Current hourly quotes for every tradable symbol. */
  async getQuotes(): Promise<SymbolQuote[]> {
    const dto = await apiGet<PricesResponseDto>("/market/prices");
    return mapPricesToQuotes(dto);
  }

  /** Timeframe options for the quote-detail chart. */
  listTimeframes(): readonly Timeframe[] {
    return TIMEFRAMES;
  }

  /**
   * Candle series for the selected timeframe.
   *
   * TODO: `/market/prices` has no historical variant yet (see
   * `app/routers/market.py`) - return real candles once it exists; the
   * current data comes from the seeded generators in `mock/data.ts`.
   */
  async getCandles(quote: SymbolQuote, timeframe: Timeframe): Promise<Candle[]> {
    const spec =
      TIMEFRAMES.find((candidate) => candidate.label === timeframe.label) ?? TIMEFRAMES[1];
    return candlesFor(quote, spec);
  }

  /**
   * Daily change for a quote (first open → last close of the 1-day series).
   *
   * TODO: the API exposes no daily-change data (see `app/routers/market.py`)
   * - use real daily bars once they exist; the current series comes from
   * the seeded generators in `mock/data.ts`, the same source the quote
   * chart uses.
   */
  dailyChange(quote: SymbolQuote): PriceChange {
    const daySpec =
      TIMEFRAMES.find((candidate) => candidate.label === "1D") ?? TIMEFRAMES[0];
    const daySeries = candlesFor(quote, daySpec);
    const open = daySeries[0].open;
    const close = daySeries[daySeries.length - 1].close;
    const abs = close - open;
    return { abs, pct: open !== 0 ? (abs / open) * 100 : 0 };
  }
}

export const marketService = new MarketService();
