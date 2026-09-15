import type {
  Candle,
  HistoryDay,
  Holding,
  NewOrder,
  OpenOrder,
  OrderQuantity,
  SymbolQuote,
} from "../types";

/* -------------------------------------------------------------------------- */
/* Seeded random generators (ported from the design mockup so charts look     */
/* identical on every load).                                                  */
/* -------------------------------------------------------------------------- */

function rng(seed: number): () => number {
  let state = (seed >>> 0) || 1;
  return () => {
    state = (state * 1664525 + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

export function genOHLC(
  count: number,
  startPrice: number,
  volatility: number,
  seed: number,
): Candle[] {
  const random = rng(seed);
  let price = startPrice;
  const candles: Candle[] = [];
  for (let index = 0; index < count; index++) {
    const open = price;
    const drift = (random() - 0.45) * volatility;
    let close = open + drift;
    if (close < 6) close = 6 + random() * 4;
    const high = Math.max(open, close) + random() * volatility * 0.7;
    const low = Math.min(open, close) - random() * volatility * 0.7;
    price = close;
    candles.push({ open, high, low, close });
  }
  return candles;
}

export function genWalk(
  count: number,
  startPrice: number,
  volatility: number,
  seed: number,
): number[] {
  const random = rng(seed);
  let price = startPrice;
  const series = [price];
  for (let index = 1; index < count; index++) {
    price = price + (random() - 0.42) * volatility;
    series.push(price);
  }
  return series;
}

function hashSymbol(symbol: string): number {
  let hash = 0;
  for (const char of symbol) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return hash;
}

/** Rescale a generated series so its last close matches the quoted price. */
function rescaleCandles(candles: Candle[], targetClose: number): Candle[] {
  const factor = targetClose / candles[candles.length - 1].close;
  return candles.map((candle) => ({
    open: candle.open * factor,
    high: candle.high * factor,
    low: candle.low * factor,
    close: candle.close * factor,
  }));
}

/* -------------------------------------------------------------------------- */
/* Market                                                                      */
/* -------------------------------------------------------------------------- */

/** The current game day number, e.g. day 128 of the game. */
export const DAY_NUMBER = 128;

export const QUOTES: SymbolQuote[] = [
  { symbol: "HLIX", price: 142.3, changeAbs: 3.34, changePct: 2.4 },
  { symbol: "VOLT", price: 91.2, changeAbs: -1.1, changePct: -1.2 },
  { symbol: "NMBS", price: 60.86, changeAbs: 0.36, changePct: 0.6 },
  { symbol: "ORCA", price: 51.3, changeAbs: -1.65, changePct: -3.1 },
];

export interface Timeframe {
  readonly label: string;
  /** Candle interval shown under the label. */
  readonly interval: string;
  readonly points: number;
  /** Fractional drift from the current price the series starts at. */
  readonly drift: number;
  /** Per-candle volatility as a fraction of price. */
  readonly volPct: number;
  readonly seed: number;
}

export const TIMEFRAMES: Timeframe[] = [
  { label: "1D", interval: "1h", points: 24, drift: 0.01, volPct: 0.004, seed: 7 },
  { label: "1W", interval: "6h", points: 28, drift: 0.03, volPct: 0.008, seed: 13 },
  { label: "1M", interval: "1D", points: 30, drift: 0.06, volPct: 0.012, seed: 29 },
  { label: "3M", interval: "1D", points: 40, drift: 0.1, volPct: 0.016, seed: 41 },
  { label: "1Y", interval: "1W", points: 52, drift: 0.18, volPct: 0.024, seed: 67 },
];

export function candlesFor(quote: SymbolQuote, timeframe: Timeframe): Candle[] {
  const startPrice = quote.price * (1 - timeframe.drift);
  const volatility = quote.price * timeframe.volPct;
  const seed = timeframe.seed + hashSymbol(quote.symbol);
  return rescaleCandles(genOHLC(timeframe.points, startPrice, volatility, seed), quote.price);
}

/* -------------------------------------------------------------------------- */
/* Portfolio                                                                   */
/* -------------------------------------------------------------------------- */

export const PORTFOLIO_VALUE = 41764;
export const CASH = 18940;
export const BUYING_POWER = CASH;
export const SINCE_SUBMIT = { abs: 1240, pct: 3.06 };

export interface PortfolioRange {
  readonly label: string;
  readonly points: number;
  readonly volPct: number;
  readonly seed: number;
  readonly changeAbs: number;
  readonly changePct: number;
  readonly note: string;
}

export const PORTFOLIO_RANGES: PortfolioRange[] = [
  { label: "1W", points: 28, volPct: 0.004, seed: 101, changeAbs: 820, changePct: 2.0, note: "past week" },
  { label: "1M", points: 36, volPct: 0.008, seed: 17, changeAbs: 3180, changePct: 8.2, note: "past month" },
  { label: "3M", points: 44, volPct: 0.012, seed: 23, changeAbs: 5410, changePct: 14.9, note: "past 3 months" },
  { label: "1Y", points: 52, volPct: 0.02, seed: 37, changeAbs: 9870, changePct: 30.9, note: "past year" },
  { label: "ALL", points: 64, volPct: 0.03, seed: 53, changeAbs: 14220, changePct: 51.6, note: "all time" },
];

/** Walk ending exactly at PORTFOLIO_VALUE. */
export function seriesFor(range: PortfolioRange): number[] {
  const walk = genWalk(range.points, PORTFOLIO_VALUE * 0.8, PORTFOLIO_VALUE * range.volPct, range.seed);
  const delta = PORTFOLIO_VALUE - walk[walk.length - 1];
  return walk.map((point) => point + delta);
}

export const HOLDINGS: Holding[] = [
  { symbol: "HLIX", shares: 60, lastPrice: 142.3 },
  { symbol: "VOLT", shares: 40, lastPrice: 91.2 },
  { symbol: "ORCA", shares: 25, lastPrice: 51.3 },
];

/** Shares currently held for a symbol (0 if none). */
export function heldShares(symbol: string): number {
  const holding = HOLDINGS.find((candidate) => candidate.symbol === symbol);
  return holding?.shares ?? 0;
}

/**
 * Best-effort share count for a quantity (used by client-side warnings only -
 * authoritative conversion happens on the backend). Null if the symbol has no
 * quote to convert a dollar value with.
 */
export function estimateShares(quantity: OrderQuantity, symbol: string): number | null {
  if ("shares" in quantity) return quantity.shares;
  const quote = QUOTES.find((candidate) => candidate.symbol === symbol);
  return quote != null ? quantity.value / quote.price : null;
}

/* -------------------------------------------------------------------------- */
/* Orders                                                                      */
/* -------------------------------------------------------------------------- */

export const INITIAL_OPEN_ORDERS: OpenOrder[] = [
  { id: "oo-1", side: "buy", type: "limit", symbol: "NMBS", quantity: { shares: 30 }, price: 61.0 },
  { id: "oo-2", side: "sell", type: "stop", symbol: "HLIX", quantity: { shares: 60 }, price: 132.0 },
];

export const INITIAL_NEW_ORDERS: NewOrder[] = [
  { id: "nt-1", side: "buy", type: "limit", symbol: "VOLT", quantity: { shares: 20 }, price: 86.5 },
  { id: "nt-2", side: "sell", type: "limit", symbol: "ORCA", quantity: { shares: 30 }, price: 52.0 },
];

/* -------------------------------------------------------------------------- */
/* History - trades grouped by the day they were closed                        */
/* -------------------------------------------------------------------------- */

export const HISTORY: HistoryDay[] = [
  {
    date: "Sep 11",
    orders: [
      {
        id: "h-1",
        status: "filled",
        label: "BUY 60 HLIX @ 128.40",
        details: {
          status: "filled",
          title: "Limit buy · HLIX",
          reason: null,
          fields: [
            { label: "Type", value: "Limit buy" },
            { label: "Symbol", value: "HLIX" },
            { label: "Requested", value: "60 shares" },
            { label: "Limit price", value: "$128.40" },
            { label: "Fill price", value: "$128.12" },
            { label: "Filled at", value: "11:00 · Sep 11" },
          ],
        },
      },
      {
        id: "h-2",
        status: "filled",
        label: "SELL 20 ORCA @ 53.10",
        details: {
          status: "filled",
          title: "Market sell · ORCA",
          reason: null,
          fields: [
            { label: "Type", value: "Market sell" },
            { label: "Symbol", value: "ORCA" },
            { label: "Requested", value: "20 shares" },
            { label: "Fill price", value: "$53.10" },
            { label: "Filled at", value: "14:00 · Sep 11" },
          ],
        },
      },
      {
        id: "h-3",
        status: "cancelled",
        label: "LIMIT BUY 15 KLP",
        details: {
          status: "cancelled",
          title: "Limit buy · KLP",
          reason: "You cancelled this open order before the day was settled.",
          fields: [
            { label: "Type", value: "Limit buy" },
            { label: "Symbol", value: "KLP" },
            { label: "Requested", value: "15 shares" },
            { label: "Limit price", value: "$19.20" },
            { label: "Status", value: "Cancelled" },
          ],
        },
      },
    ],
  },
  {
    date: "Sep 10",
    orders: [
      {
        id: "h-4",
        status: "no_funds",
        label: "STOP SELL 40 VOLT",
        details: {
          status: "no_funds",
          title: "Stop sell · VOLT",
          reason:
            "A limit sell in the same set already sold these shares, so nothing was left for the stop sell to close.",
          fields: [
            { label: "Type", value: "Stop sell" },
            { label: "Symbol", value: "VOLT" },
            { label: "Requested", value: "40 shares" },
            { label: "Stop price", value: "$84.00" },
            { label: "Trigger", value: "12:00 · Sep 10" },
          ],
        },
      },
      {
        id: "h-5",
        status: "delisted",
        label: "LIMIT BUY 50 ASTR",
        details: {
          status: "delisted",
          title: "Limit buy · ASTR",
          reason: "ASTR stopped trading (merger) before this order could fill.",
          fields: [
            { label: "Type", value: "Limit buy" },
            { label: "Symbol", value: "ASTR" },
            { label: "Requested", value: "50 shares" },
            { label: "Limit price", value: "$12.00" },
            { label: "Closed at", value: "18:00 · Sep 10" },
          ],
        },
      },
    ],
  },
  {
    date: "Sep 9",
    orders: [
      {
        id: "h-6",
        status: "error",
        label: "MARKET BUY 25 NMBS",
        details: {
          status: "error",
          title: "Market buy · NMBS",
          reason: "Execution failed due to a technical error — nothing was charged.",
          fields: [
            { label: "Type", value: "Market buy" },
            { label: "Symbol", value: "NMBS" },
            { label: "Requested", value: "25 shares" },
            { label: "Status", value: "Error" },
            { label: "Closed at", value: "21:00 · Sep 9" },
          ],
        },
      },
    ],
  },
];
