import type { Candle, SymbolQuote, Timeframe } from "../types";

/**
 * Deterministic (seeded) chart-series generators, ported from the design
 * mockup so visuals stay stable across loads.
 *
 * Used as data sources by `MarketService` and `PortfolioService` - see the
 * TODOs there for the endpoints that will replace this module.
 *
 * Nothing outside `src/services/` and `src/hooks/` may import from here.
 */

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

function genOHLC(
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

function genWalk(
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
/* Candle history (no historical-prices endpoint yet)                          */
/* -------------------------------------------------------------------------- */

interface MockTimeframeSpec extends Timeframe {
  /** Fractional drift from the current price the series starts at. */
  readonly drift: number;
  /** Per-candle volatility as a fraction of price. */
  readonly volPct: number;
  readonly seed: number;
}

export const TIMEFRAMES: MockTimeframeSpec[] = [
  { label: "1D", interval: "1h", points: 24, drift: 0.01, volPct: 0.004, seed: 7 },
  { label: "1W", interval: "6h", points: 28, drift: 0.03, volPct: 0.008, seed: 13 },
  { label: "1M", interval: "1D", points: 30, drift: 0.06, volPct: 0.012, seed: 29 },
  { label: "3M", interval: "1D", points: 40, drift: 0.1, volPct: 0.016, seed: 41 },
  { label: "1Y", interval: "1W", points: 52, drift: 0.18, volPct: 0.024, seed: 67 },
];

export function candlesFor(quote: SymbolQuote, timeframe: MockTimeframeSpec): Candle[] {
  const startPrice = quote.price * (1 - timeframe.drift);
  const volatility = quote.price * timeframe.volPct;
  const seed = timeframe.seed + hashSymbol(quote.symbol);
  return rescaleCandles(genOHLC(timeframe.points, startPrice, volatility, seed), quote.price);
}

/* -------------------------------------------------------------------------- */
/* Portfolio value history (no portfolio-history endpoint yet)                 */
/* -------------------------------------------------------------------------- */

export const SINCE_SUBMIT = { abs: 1240, pct: 3.06 };

export interface PortfolioRange {
  readonly label: string;
  readonly points: number;
  readonly volPct: number;
  readonly seed: number;
  /** Total change the generated series should span across the range. */
  readonly changeAbs: number;
  readonly note: string;
}

export const PORTFOLIO_RANGES: PortfolioRange[] = [
  { label: "1W", points: 28, volPct: 0.004, seed: 101, changeAbs: 820, note: "past week" },
  { label: "1M", points: 36, volPct: 0.008, seed: 17, changeAbs: 3180, note: "past month" },
  { label: "3M", points: 44, volPct: 0.012, seed: 23, changeAbs: 5410, note: "past 3 months" },
  { label: "1Y", points: 52, volPct: 0.02, seed: 37, changeAbs: 9870, note: "past year" },
  { label: "ALL", points: 64, volPct: 0.03, seed: 53, changeAbs: 14220, note: "all time" },
];

/** Walk that starts near `endValue - range.changeAbs` and ends at `endValue`. */
export function seriesFor(range: PortfolioRange, endValue: number): number[] {
  const safeEnd = Math.max(endValue, 0);
  const walk = genWalk(range.points, 0, safeEnd * range.volPct, range.seed);
  const startValue = Math.max(0, safeEnd - range.changeAbs);
  const driftPerStep = (safeEnd - startValue) / (walk.length - 1);
  const series = walk.map((point, index) => startValue + point + driftPerStep * index);
  // Recentre so the walk ends exactly at the current portfolio value.
  const offset = safeEnd - series[series.length - 1];
  return series.map((point) => Math.max(0, point + offset));
}
