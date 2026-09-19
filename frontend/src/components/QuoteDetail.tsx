import { useEffect, useRef, useState } from "react";

import { useCandles } from "../hooks/useCandles";
import { marketService } from "../services/MarketService";
import type { Candle, SymbolQuote } from "../types";
import { formatSignedPercent, formatSignedUsd, formatUsd } from "../utils/format";
import { CandleChart } from "./CandleChart";
import { ChartPlaceholder } from "./ChartPlaceholder";
import { StatusNote } from "./StatusNote";
import styles from "./QuoteDetail.module.css";

/** Below this many candles a window is considered too sparse to plot. */
const MIN_CANDLES = 8;

interface QuoteDetailProps {
  quote: SymbolQuote;
}

/**
 * Selected-symbol header, candlestick chart, and timeframe chips. The change
 * next to the price is the displayed period's change: the first candle's
 * open vs. the last candle's close, so it follows the selected timeframe.
 *
 * The initial (default) timeframe widens automatically while its window has
 * too little data (e.g. the market has been closed), held on a plain loading
 * note so intermediate ranges never flash. A manually chosen timeframe is
 * never overridden - a sparse window shows the placeholder instead. While a
 * range loads, the previously shown chart stays visible under a blurred
 * overlay with a spinner.
 */
export function QuoteDetail({ quote }: QuoteDetailProps) {
  const timeframes = marketService.listTimeframes();
  const [selectedLabel, setSelectedLabel] = useState(timeframes[1].label);
  const [userChose, setUserChose] = useState(false);
  // Loaded series per symbol+timeframe, so revisiting a range renders
  // instantly; plus the last chart shown, so a first-time range load can
  // keep the previous chart visible under the loading overlay.
  const seriesByKey = useRef(new Map<string, Candle[]>());
  const lastShownRef = useRef<{ symbol: string; series: Candle[] } | null>(null);

  const timeframe =
    timeframes.find((candidate) => candidate.label === selectedLabel) ?? timeframes[1];
  const candles = useCandles(quote, timeframe);

  const series = candles.data;
  const loading = candles.loading && candles.error == null;
  const hasWider = timeframes.indexOf(timeframe) < timeframes.length - 1;
  const autoWidening =
    !userChose && hasWider && (loading || (series != null && series.length < MIN_CANDLES));

  // Auto-widen the initial timeframe while its window is too sparse.
  useEffect(() => {
    if (userChose || series == null || series.length >= MIN_CANDLES) return;
    const wider = timeframes[timeframes.indexOf(timeframe) + 1];
    if (wider != null) setSelectedLabel(wider.label);
  }, [series, timeframes, timeframe, userChose]);

  useEffect(() => {
    if (series == null) return;
    seriesByKey.current.set(`${quote.symbol}:${timeframe.label}`, series);
    lastShownRef.current = { symbol: quote.symbol, series };
  }, [series, quote.symbol, timeframe.label]);

  const cachedSeries = seriesByKey.current.get(`${quote.symbol}:${selectedLabel}`) ?? null;
  const lastShown =
    lastShownRef.current?.symbol === quote.symbol ? lastShownRef.current.series : null;
  const shownSeries = series ?? cachedSeries ?? lastShown;
  const displaySeries = autoWidening ? null : shownSeries;
  const periodStart = displaySeries?.[0];
  const periodEnd = displaySeries?.[displaySeries.length - 1];
  const changeAbs =
    periodStart != null && periodEnd != null
      ? periodEnd.close - periodStart.open
      : quote.changeAbs;
  const changePct =
    periodStart != null && periodEnd != null && periodStart.open !== 0
      ? ((periodEnd.close - periodStart.open) / periodStart.open) * 100
      : quote.changePct;
  const quoteUp = changeAbs >= 0;

  return (
    <section>
      <div className={styles.quoteRow}>
        <div>
          <div className={styles.quoteSymbol}>{quote.symbol}</div>
          <div className={styles.quotePrice}>{formatUsd(quote.price)}</div>
        </div>
        <div className={styles.quoteChange}>
          <div className={`${styles.changeAbs} ${quoteUp ? styles.up : styles.down}`}>
            {formatSignedUsd(changeAbs, 2)}
          </div>
          <div className={`${styles.changePct} ${quoteUp ? styles.up : styles.down}`}>
            {formatSignedPercent(changePct, 2)}
          </div>
        </div>
      </div>

      <div className={styles.chart}>
        {candles.error != null ? (
          <StatusNote tone="error" message={candles.error} onRetry={candles.reload} />
        ) : autoWidening ? (
          <StatusNote tone="loading" />
        ) : shownSeries == null ? (
          <StatusNote tone="loading" />
        ) : shownSeries.length < MIN_CANDLES ? (
          <ChartPlaceholder message="No price data for this range" />
        ) : (
          <div className={styles.chartFrame}>
            <CandleChart data={shownSeries} />
            {loading && (
              <div className={styles.loadingOverlay} role="status" aria-label="Loading chart">
                <span className={styles.spinner} />
              </div>
            )}
          </div>
        )}
      </div>

      <div className={styles.timeframes}>
        {timeframes.map((timeframeOption) => (
          <button
            key={timeframeOption.label}
            type="button"
            className={timeframeOption.label === selectedLabel ? styles.tfActive : styles.tf}
            onClick={() => {
              setUserChose(true);
              setSelectedLabel(timeframeOption.label);
            }}
          >
            <div className={styles.tfLabel}>{timeframeOption.label}</div>
            <div className={styles.tfInterval}>{timeframeOption.interval}</div>
          </button>
        ))}
      </div>
    </section>
  );
}
