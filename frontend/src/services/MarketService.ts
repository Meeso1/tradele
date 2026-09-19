import { apiGet } from "../api/client";
import type { MarketStateResponseDto, PriceHistoryRangeDto } from "../api/dto";
import {
  mapPricesToQuotes,
  mapStatesToCandles,
  mapStatesToDailyChanges,
} from "../api/mappers";
import type { Candle, PriceChange, SymbolQuote, Timeframe } from "../types";

/**
 * How one UI timeframe maps onto the `/market/prices` endpoint: which
 * trailing window to fetch, and how many hourly states aggregate into one
 * candle. Ranges the backend has no `range` shortcut for use `startDaysAgo`.
 */
interface TimeframeSpec {
  readonly label: string;
  readonly interval: string;
  /** Backend `range` shortcut; exclusive with `startDaysAgo`. */
  readonly range?: PriceHistoryRangeDto;
  /** Trailing window in days, resolved against the client clock. */
  readonly startDaysAgo?: number;
  readonly bucketHours: number;
}

const TIMEFRAME_SPECS: readonly TimeframeSpec[] = [
  { label: "1D", interval: "1h", range: "day", bucketHours: 1 },
  { label: "1W", interval: "6h", range: "week", bucketHours: 6 },
  { label: "1M", interval: "1D", range: "month", bucketHours: 24 },
  { label: "3M", interval: "1D", startDaysAgo: 90, bucketHours: 24 },
  { label: "1Y", interval: "1W", range: "year", bucketHours: 24 * 7 },
];

/** Identity-stable list - hooks key off these objects, so never remap it. */
const TIMEFRAMES: readonly Timeframe[] = TIMEFRAME_SPECS.map(({ label, interval }) => ({
  label,
  interval,
}));

/**
 * The timeframe whose window everything "current" is derived from: quotes,
 * daily changes, last prices and the default chart all come from this single
 * fetch. The trailing week reliably contains the most recent trading
 * session, which a narrower window (or the latest clock hour) would not
 * whenever the market is closed.
 */
const SNAPSHOT_LABEL = "1W";

/**
 * Market data backed by the `/market/prices` endpoint.
 */
export class MarketService {
  /**
   * Hourly states per timeframe window, shared for the session. Promises are
   * memoized (not results), so a range switched away from and back awaits the
   * request already in progress instead of restarting it, and loaded windows
   * resolve from memory. Failed fetches evict themselves, so retries work.
   */
  private statesByLabel = new Map<string, Promise<MarketStateResponseDto[]>>();

  /** Current quotes for every tradable symbol (latest hour with prices). */
  async getQuotes(): Promise<SymbolQuote[]> {
    const latest = latestPricedState(await this.getStates(SNAPSHOT_LABEL));
    return latest == null ? [] : mapPricesToQuotes(latest);
  }

  /** Timeframe options for the quote-detail chart. */
  listTimeframes(): readonly Timeframe[] {
    return TIMEFRAMES;
  }

  /** Candle series for the selected timeframe, aggregated from hourly states. */
  async getCandles(quote: SymbolQuote, timeframe: Timeframe): Promise<Candle[]> {
    const spec = specFor(timeframe.label);
    const states = await this.getStates(spec.label);
    return mapStatesToCandles(states, quote.symbol, spec.bucketHours);
  }

  /** Daily change per symbol over the most recent trading day in the snapshot. */
  async getDailyChanges(): Promise<Record<string, PriceChange>> {
    return mapStatesToDailyChanges(await this.getStates(SNAPSHOT_LABEL));
  }

  /** Latest close per symbol, for valuing portfolio holdings. */
  async getLatestPrices(): Promise<Record<string, number>> {
    const latest = latestPricedState(await this.getStates(SNAPSHOT_LABEL));
    if (latest == null) return {};
    return Object.fromEntries(
      Object.values(latest.prices).map((price) => [price.symbol, price.close]),
    );
  }

  /**
   * Start fetching every timeframe window in parallel (fire-and-forget), so
   * switching timeframes later resolves from memory or an in-flight request
   * instead of waiting on a fresh fetch. Errors surface when a window is
   * actually awaited, not here.
   */
  prefetchTimeframes(): void {
    for (const spec of TIMEFRAME_SPECS) {
      this.getStates(spec.label).catch(() => undefined);
    }
  }

  private getStates(label: string): Promise<MarketStateResponseDto[]> {
    const cached = this.statesByLabel.get(label);
    if (cached != null) return cached;

    const spec = specFor(label);
    const promise = apiGet<MarketStateResponseDto[]>(
      `/market/prices${specQuery(spec)}`,
    ).catch((cause: unknown) => {
      this.statesByLabel.delete(label);
      throw cause;
    });
    this.statesByLabel.set(label, promise);
    return promise;
  }
}

function specFor(label: string): TimeframeSpec {
  return TIMEFRAME_SPECS.find((candidate) => candidate.label === label) ?? TIMEFRAME_SPECS[1];
}

/** The newest state that actually has prices, or null when none do. */
function latestPricedState(
  states: readonly MarketStateResponseDto[],
): MarketStateResponseDto | null {
  for (let index = states.length - 1; index >= 0; index--) {
    if (states[index].market_open) return states[index];
  }
  return null;
}

function specQuery(spec: TimeframeSpec): string {
  if (spec.range != null) return `?range=${spec.range}`;
  const start = new Date(Date.now() - (spec.startDaysAgo ?? 0) * 86_400_000);
  return `?start=${start.toISOString()}`;
}

export const marketService = new MarketService();
